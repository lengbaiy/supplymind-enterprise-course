import json
from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.sql_guard import SQLGuardError, validate_read_only_sql
from app.models import AgentStep, AnalysisRun, Conversation, DataSource
from app.schemas import AnalysisRequest, Principal
from app.services.audit import audit
from app.services.datasource import DataSourceError, execute_guarded_query
from app.services.llm import ModelConfigurationError, ModelResponseError, OpenAICompatibleClient


class AnalysisService:
    def __init__(self, client: OpenAICompatibleClient | None = None) -> None:
        self.client = client or OpenAICompatibleClient()

    async def stream(
        self, session: AsyncSession, principal: Principal, request: AnalysisRequest
    ) -> AsyncGenerator[str, None]:
        source = await session.scalar(
            select(DataSource).where(
                DataSource.id == request.data_source_id, DataSource.tenant_id == principal.tenant_id
            )
        )
        if not source:
            yield self.event("failed", {"message": "Data source not found"})
            return
        conversation = Conversation(
            tenant_id=principal.tenant_id, title=request.question[:80], created_by=principal.user_id
        )
        session.add(conversation)
        await session.flush()
        run = AnalysisRun(
            tenant_id=principal.tenant_id,
            conversation_id=conversation.id,
            data_source_id=source.id,
            question=request.question,
            status="running",
        )
        session.add(run)
        await session.flush()
        yield self.event("queued", {"run_id": run.id})
        for step, message in (
            ("router", "Identifying analysis intent"),
            ("rag", "Retrieving manufacturing metric definitions"),
            ("schema", "Reading approved schema metadata"),
        ):
            session.add(AgentStep(tenant_id=principal.tenant_id, analysis_run_id=run.id, name=step, status="completed", output={"message": message}))
            yield self.event("step_started", {"step": step, "message": message})
        try:
            plan = await self.client.plan_sql(request.question, source.allowed_tables)
        except (ModelConfigurationError, ModelResponseError) as exc:
            run.status = "failed"
            await audit(session, principal.tenant_id, principal.user_id, "analysis.model_failed", "analysis_run", run.id, {"reason": str(exc)})
            await session.commit()
            yield self.event("failed", {"message": str(exc)})
            return
        candidate = plan["sql"]
        session.add(AgentStep(tenant_id=principal.tenant_id, analysis_run_id=run.id, name="sql_planner", status="completed", output=plan))
        yield self.event("sql_draft", {"sql": candidate})
        try:
            guarded = validate_read_only_sql(
                candidate, set(source.allowed_tables), get_settings().sql_max_rows
            )
        except SQLGuardError as exc:
            run.status = "failed"
            await audit(session, principal.tenant_id, principal.user_id, "analysis.blocked", "analysis_run", run.id, {"reason": str(exc)})
            await session.commit()
            yield self.event("failed", {"message": str(exc)})
            return
        try:
            _, rows = await execute_guarded_query(source, guarded.sql)
        except (DataSourceError, SQLAlchemyError) as exc:
            run.status = "failed"
            await audit(session, principal.tenant_id, principal.user_id, "analysis.query_failed", "analysis_run", run.id, {"reason": str(exc)})
            await session.commit()
            yield self.event("failed", {"message": "Read-only query execution failed"})
            return
        result = {"rows": rows, "insight": plan["insight"], "chart": self.chart_spec(rows), "citations": []}
        run.status = "completed"
        run.sql = guarded.sql
        run.result = result
        await audit(session, principal.tenant_id, principal.user_id, "analysis.executed", "analysis_run", run.id, {"tables": guarded.tables})
        await session.commit()
        yield self.event("tool_result", {"tables": guarded.tables, "row_count": len(result["rows"])})
        yield self.event("chart_ready", {"chart": result["chart"]})
        yield self.event("completed", {"run_id": run.id, "sql": guarded.sql, "result": result})

    @staticmethod
    def event(name: str, payload: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"

    @staticmethod
    def chart_spec(rows: list[dict]) -> dict:
        if not rows:
            return {"type": "table"}
        fields = list(rows[0])
        numeric = next((field for field, value in rows[0].items() if isinstance(value, (int, float))), None)
        return {"type": "bar", "x": fields[0], "y": numeric or fields[-1]}
