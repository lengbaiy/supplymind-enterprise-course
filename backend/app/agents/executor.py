import json
from datetime import UTC, date, datetime
from decimal import Decimal
from time import perf_counter

from sqlalchemy import select

from app.agents.graph import AgentServices, build_enterprise_graph
from app.agents.runtime import RuntimeContainer
from app.agents.state import SupplyMindState
from app.core.config import get_settings
from app.db import SessionLocal, set_tenant_context
from app.mcp_runtime.client import MCPClientManager
from app.mcp_runtime.security import issue_tool_context
from app.memory.service import MemoryPolicyError, MemoryService
from app.models import (
    AgentStep,
    AnalysisRun,
    ConversationMessage,
    Membership,
    Report,
)
from app.observability import (
    AGENT_FALLBACKS,
    AGENT_RUNS,
    AGENT_SUBAGENT_DURATION,
    MODEL_TOKENS,
    configure_telemetry,
    genai_span,
)
from app.schemas import Principal
from app.services.events import append_event
from app.services.llm import ModelResponseError, OpenAICompatibleClient
from app.services.reports import render_markdown


def normalize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class EnterpriseAnalysisExecutor:
    def __init__(self, client: OpenAICompatibleClient | None = None) -> None:
        self.client = client or OpenAICompatibleClient()
        self.mcp = MCPClientManager()

    async def _emit(self, run_id: str, tenant_id: str, event_type: str, payload: dict) -> None:
        async with SessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            run = await session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == run_id, AnalysisRun.tenant_id == tenant_id
                )
            )
            if run:
                await append_event(session, run, event_type, payload)

    async def execute(self, run_id: str) -> None:
        configure_telemetry("supplymind-worker")
        async with SessionLocal() as session:
            run = await session.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id))
            if not run:
                return
            await set_tenant_context(session, run.tenant_id)
            run.status = "running"
            run.started_at = run.started_at or datetime.now(UTC)
            run.attempts += 1
            from app.models import Conversation

            conversation = await session.scalar(
                select(Conversation).where(Conversation.id == run.conversation_id)
            )
            if not conversation:
                run.status = "failed"
                run.error_message = "Conversation not found"
                await session.commit()
                return
            membership = await session.scalar(
                select(Membership).where(
                    Membership.organization_id == run.tenant_id,
                    Membership.user_id == conversation.created_by,
                    Membership.is_active.is_(True),
                )
            )
            if not membership:
                run.status = "failed"
                run.error_message = "Analysis owner has no active organization membership"
                await session.commit()
                return
            principal = Principal(
                user_id=conversation.created_by,
                tenant_id=run.tenant_id,
                role=membership.role,
            )
            run.checkpoint_thread_id = f"{run.tenant_id}:{principal.user_id}:{run.conversation_id}"
            await session.commit()

        await self._emit(
            run_id,
            principal.tenant_id,
            "step_started",
            {"step": "context_loader", "message": "正在恢复会话与长期记忆"},
        )
        memories: list[dict] = []
        async with SessionLocal() as session:
            await set_tenant_context(session, principal.tenant_id)
            memory_service = MemoryService()
            if await memory_service.enabled(session, principal.tenant_id, principal.user_id):
                memories = [
                    {
                        "id": item.id,
                        "category": item.category,
                        "key": item.memory_key,
                        "content": item.content,
                    }
                    for item in await memory_service.list(
                        session, principal.tenant_id, principal.user_id
                    )
                ]
        await self._emit(
            run_id,
            principal.tenant_id,
            "memory_loaded",
            {"count": len(memories), "namespace": "tenant/user"},
        )

        async def route(question: str):
            try:
                selected, confidence = await self.client.route_question(question)
            except (ModelResponseError, RuntimeError):
                selected, confidence = "hybrid", 0.5
                AGENT_FALLBACKS.labels("router", "hybrid").inc()
                await self._emit(
                    run_id,
                    principal.tenant_id,
                    "degraded",
                    {"stage": "router", "fallback": "hybrid"},
                )
            await self._emit(
                run_id,
                principal.tenant_id,
                "route_selected",
                {"route": selected, "confidence": confidence},
            )
            return selected, confidence

        async def run_subagent(name: str, state: SupplyMindState) -> dict:
            started = perf_counter()
            await self._emit(
                run_id,
                principal.tenant_id,
                "subagent_started",
                {"agent": name},
            )
            with genai_span("agent.subagent", {"gen_ai.agent.name": name}):
                if name == "data_analysis":
                    result = await self._run_data_subagent(run_id, principal, state)
                elif name == "knowledge_research":
                    result = await self._run_knowledge_subagent(run_id, principal, state)
                else:
                    result = {"error": "unsupported_subagent"}
            subagent_status = "completed" if "error" not in result else "failed"
            AGENT_SUBAGENT_DURATION.labels(name, subagent_status).observe(
                perf_counter() - started
            )
            await self._emit(
                run_id,
                principal.tenant_id,
                "subagent_completed",
                {"agent": name, "status": subagent_status},
            )
            return result

        async def synthesize(state: SupplyMindState) -> dict:
            data = next(
                (
                    item
                    for item in state.get("subagent_results", [])
                    if item["agent"] == "data_analysis"
                ),
                {},
            )
            knowledge = next(
                (
                    item
                    for item in state.get("subagent_results", [])
                    if item["agent"] == "knowledge_research"
                ),
                {},
            )
            rows = data.get("rows", [])
            citations = knowledge.get("citations", [])
            answer_plan = await self.client.answer_question(
                state["question"],
                rows,
                citations,
                [item["content"] for item in state.get("memories", [])],
                data.get("planner_insight", ""),
            )
            prompt = (
                "请基于以下已验证证据，用中文直接回答供应链问题。不得补充证据之外的事实。\n"
                f"问题：{state['question']}\n"
                f"数据：{json.dumps(rows[:50], ensure_ascii=False, default=str)}\n"
                f"知识依据：{json.dumps(citations[:8], ensure_ascii=False, default=str)}"
            )
            streamed = ""
            buffer = ""
            try:
                async for token in self.client.stream_text(prompt):
                    streamed += token
                    buffer += token
                    if len(buffer) >= 40:
                        await self._emit(
                            run_id,
                            principal.tenant_id,
                            "token",
                            {"text": buffer},
                        )
                        buffer = ""
                if buffer:
                    await self._emit(run_id, principal.tenant_id, "token", {"text": buffer})
            except (ModelResponseError, RuntimeError):
                streamed = answer_plan.direct_answer
                AGENT_FALLBACKS.labels("token_stream", "structured_answer").inc()
                await self._emit(
                    run_id,
                    principal.tenant_id,
                    "degraded",
                    {"stage": "token_stream", "fallback": "structured_answer"},
                )
            payload = answer_plan.model_dump()
            payload["direct_answer"] = streamed.strip() or answer_plan.direct_answer
            model_name = (
                get_settings().ai_answer_model or get_settings().chat_model or "unknown"
            )
            MODEL_TOKENS.labels(model_name, "output").inc(
                max(1, len(payload["direct_answer"]) // 4)
            )
            payload["rows"] = rows
            payload["citations"] = citations
            payload["sql"] = data.get("sql")
            payload["chart"] = data.get("chart", {"type": "table"})
            return payload

        async def verify(state: SupplyMindState):
            answer = state.get("answer") or {}
            if not answer.get("direct_answer"):
                return False, "答案缺少直接回答", "synthesize"
            if not answer.get("rows") and not answer.get("citations"):
                return False, "没有可验证证据", "synthesize"
            return True, None, None

        local_runtime = RuntimeContainer()
        try:
            await local_runtime.start()
            graph = build_enterprise_graph(
                AgentServices(
                    route=route,
                    run_subagent=run_subagent,
                    synthesize=synthesize,
                    verify=verify,
                ),
                checkpointer=local_runtime.checkpointer,
                store=local_runtime.store,
            )
            with genai_span(
                "agent.graph",
                {
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.agent.name": "supplymind-root",
                    "supplymind.graph.version": run.graph_version,
                },
            ):
                state = await graph.ainvoke(
                    {
                        "tenant_id": principal.tenant_id,
                        "user_id": principal.user_id,
                        "role": principal.role,
                        "run_id": run_id,
                        "conversation_id": run.conversation_id,
                        "question": run.question,
                        "data_source_id": run.data_source_id,
                        "knowledge_base_id": run.knowledge_base_id or "",
                        "memories": memories,
                    },
                    config={"configurable": {"thread_id": run.checkpoint_thread_id}},
                )
            if state.get("__interrupt__"):
                await self._persist_waiting_approval(run_id, principal.tenant_id)
                return
            if not state.get("verified") or not state.get("completed"):
                raise RuntimeError(
                    state.get("verification_error") or "Agent answer failed verification"
                )
            await self._persist_success(run_id, principal, state)
        except Exception as exc:
            await self._persist_failure(run_id, principal.tenant_id, exc)
            raise
        finally:
            await local_runtime.stop()

    async def _persist_waiting_approval(self, run_id: str, tenant_id: str) -> None:
        async with SessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            run = await session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == run_id, AnalysisRun.tenant_id == tenant_id
                )
            )
            if not run:
                return
            run.status = "waiting_approval"
            await session.commit()
            await append_event(
                session,
                run,
                "approval_required",
                {"run_id": run.id, "checkpoint_thread_id": run.checkpoint_thread_id},
            )

    async def _run_data_subagent(
        self, run_id: str, principal: Principal, state: SupplyMindState
    ) -> dict:
        context_token = issue_tool_context(principal)
        connection = {
            "transport": "streamable_http",
            "endpoint": get_settings().mcp_internal_url,
        }
        schema_result = await self.mcp.call(
            "schema.lookup",
            {"context_token": context_token, "data_source_id": state["data_source_id"]},
            **connection,
        )
        await self._emit(
            run_id,
            principal.tenant_id,
            "handoff",
            {"from": "data_analysis", "to": "sql_planner"},
        )
        plan = await self.client.plan_sql(state["question"], schema_result.get("tables", []))
        query_result = await self.mcp.call(
            "sql.query",
            {
                "context_token": context_token,
                "data_source_id": state["data_source_id"],
                "sql": plan["sql"],
            },
            **connection,
        )
        rows = [
            {key: normalize_value(value) for key, value in row.items()}
            for row in query_result.get("rows", [])
        ]
        chart_result = await self.mcp.call(
            "chart.render",
            {"context_token": context_token, "rows": rows},
            **connection,
        )
        await self._emit(
            run_id,
            principal.tenant_id,
            "tool_result",
            {
                "tool": "sql.query",
                "row_count": len(rows),
                "tables": query_result.get("tables", []),
            },
        )
        return {
            "sql": query_result.get("sql"),
            "rows": rows,
            "tables": query_result.get("tables", []),
            "planner_insight": plan["insight"],
            "chart": chart_result.get("spec", {"type": "table"}),
        }

    async def _run_knowledge_subagent(
        self, run_id: str, principal: Principal, state: SupplyMindState
    ) -> dict:
        result = await self.mcp.call(
            "knowledge.search",
            {
                "context_token": issue_tool_context(principal),
                "knowledge_base_id": state["knowledge_base_id"],
                "query": state["question"],
                "limit": get_settings().rag_rerank_top_k,
            },
            transport="streamable_http",
            endpoint=get_settings().mcp_internal_url,
        )
        for stage in result.get("trace", []):
            await self._emit(run_id, principal.tenant_id, "retrieval_stage", stage)
        if result.get("degraded"):
            await self._emit(
                run_id,
                principal.tenant_id,
                "degraded",
                {"stage": "advanced_rag", "warnings": result.get("warnings", [])},
            )
        citations = result.get("results", [])
        await self._emit(
            run_id,
            principal.tenant_id,
            "tool_result",
            {"tool": "knowledge.search", "result_count": len(citations)},
        )
        return {"citations": citations, "retrieval_trace": result.get("trace", [])}

    async def _persist_success(
        self, run_id: str, principal: Principal, state: SupplyMindState
    ) -> None:
        async with SessionLocal() as session:
            await set_tenant_context(session, principal.tenant_id)
            run = await session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == run_id, AnalysisRun.tenant_id == principal.tenant_id
                )
            )
            if not run:
                return
            if run.status == "cancelled":
                return
            answer = state.get("answer") or {}
            run.route = state.get("route")
            run.sql = answer.get("sql")
            run.result = {
                "rows": answer.get("rows", []),
                "insight": answer.get("direct_answer"),
                "direct_answer": answer.get("direct_answer"),
                "insights": {
                    key: answer.get(key, [])
                    for key in ("facts", "risks", "recommendations", "assumptions", "limitations")
                },
                "chart": answer.get("chart", {"type": "table"}),
                "citations": answer.get("citations", []),
                "route": state.get("route"),
            }
            run.status = "completed"
            AGENT_RUNS.labels(state.get("route") or "unknown", "completed").inc()
            run.finished_at = datetime.now(UTC)
            run.error_message = None
            for item in state.get("trace", []):
                session.add(
                    AgentStep(
                        tenant_id=principal.tenant_id,
                        analysis_run_id=run.id,
                        name=item.get("node", "agent"),
                        status="completed" if item.get("verified", True) else "failed",
                        output=item,
                        model_version=get_settings().chat_model or "",
                        prompt_version=item.get("prompt_version", "enterprise-agent-v2"),
                    )
                )
            markdown, citations = render_markdown(run)
            report = Report(
                tenant_id=principal.tenant_id,
                analysis_run_id=run.id,
                title=f"供应链分析报告 · {run.question[:80]}",
                markdown=markdown,
                citations=citations,
                created_by=principal.user_id,
            )
            session.add(report)
            await session.flush()
            run.result["report_id"] = report.id
            session.add(
                ConversationMessage(
                    tenant_id=principal.tenant_id,
                    conversation_id=run.conversation_id,
                    role="assistant",
                    content=answer.get("direct_answer") or "分析已完成",
                    metadata_json={"analysis_run_id": run.id, "citations": citations},
                )
            )
            await session.commit()
            await set_tenant_context(session, principal.tenant_id)
            saved_memories = 0
            try:
                if await MemoryService().enabled(session, principal.tenant_id, principal.user_id):
                    candidates = await self.client.extract_memories(
                        run.question, answer.get("direct_answer") or ""
                    )
                    for candidate in candidates:
                        try:
                            await MemoryService().upsert(
                                session,
                                principal.tenant_id,
                                principal.user_id,
                                category=str(candidate.get("category", "")),
                                memory_key=str(candidate.get("memory_key", "")),
                                content=str(candidate.get("content", "")),
                                confidence=float(candidate.get("confidence", 0)),
                                source_run_id=run.id,
                            )
                            saved_memories += 1
                        except (MemoryPolicyError, TypeError, ValueError):
                            continue
                    await session.commit()
            except (ModelResponseError, RuntimeError):
                await session.rollback()
            await append_event(
                session,
                run,
                "memory_saved",
                {"count": saved_memories, "policy": "allowlist"},
            )
            await append_event(
                session,
                run,
                "completed",
                {
                    "run_id": run.id,
                    "sql": run.sql,
                    "result": run.result,
                    "report_id": report.id,
                    "route": run.route,
                },
            )

    async def _persist_failure(self, run_id: str, tenant_id: str, exc: Exception) -> None:
        async with SessionLocal() as session:
            await set_tenant_context(session, tenant_id)
            run = await session.scalar(
                select(AnalysisRun).where(
                    AnalysisRun.id == run_id, AnalysisRun.tenant_id == tenant_id
                )
            )
            if not run:
                return
            run.status = "failed"
            AGENT_RUNS.labels(run.route or "unknown", "failed").inc()
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)[:1000]
            await session.commit()
            await append_event(
                session,
                run,
                "failed",
                {"run_id": run.id, "message": "分析执行失败", "error_type": type(exc).__name__},
            )
