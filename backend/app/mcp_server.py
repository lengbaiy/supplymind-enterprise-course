"""SupplyMind's standards-compliant MCP Server."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.core.config import get_settings
from app.core.sql_guard import validate_read_only_sql
from app.db import SessionLocal, set_tenant_context
from app.mcp_runtime.security import verify_tool_context
from app.models import AgentApproval, DataSource, Report
from app.rag.retrieval import AdvancedRetriever
from app.services.datasource import execute_guarded_query, synchronize_schema

mcp = FastMCP("SupplyMind Enterprise Tools", host="0.0.0.0", port=8001)


@mcp.tool(name="schema.lookup", description="Read an approved tenant datasource schema")
async def schema_lookup(context_token: str, data_source_id: str) -> dict:
    principal = verify_tool_context(context_token)
    async with SessionLocal() as session:
        await set_tenant_context(session, principal.tenant_id)
        source = await session.scalar(
            select(DataSource).where(
                DataSource.id == data_source_id,
                DataSource.tenant_id == principal.tenant_id,
            )
        )
        if not source:
            raise ValueError("Data source not found")
        schema = await synchronize_schema(source)
        return {"tables": schema.tables}


@mcp.tool(name="sql.query", description="Execute SQL after SupplyMind's mandatory read-only guard")
async def sql_query(context_token: str, data_source_id: str, sql: str) -> dict:
    principal = verify_tool_context(context_token)
    if principal.role not in {"analyst", "org_admin", "platform_admin"}:
        raise PermissionError("Role cannot query data")
    async with SessionLocal() as session:
        await set_tenant_context(session, principal.tenant_id)
        source = await session.scalar(
            select(DataSource).where(
                DataSource.id == data_source_id,
                DataSource.tenant_id == principal.tenant_id,
            )
        )
        if not source:
            raise ValueError("Data source not found")
        guarded = validate_read_only_sql(
            sql, set(source.allowed_tables), get_settings().sql_max_rows
        )
        _, rows = await execute_guarded_query(source, guarded.sql)
        return {"sql": guarded.sql, "tables": guarded.tables, "rows": rows}


@mcp.tool(name="knowledge.search", description="Run SupplyMind's Advanced RAG retrieval pipeline")
async def knowledge_search(
    context_token: str, knowledge_base_id: str, query: str, limit: int = 8
) -> dict:
    principal = verify_tool_context(context_token)
    async with SessionLocal() as session:
        await set_tenant_context(session, principal.tenant_id)
        result = await AdvancedRetriever().search(
            session, principal.tenant_id, knowledge_base_id, query, limit
        )
        return {
            "results": result.results,
            "trace": result.trace,
            "degraded": result.degraded,
            "warnings": result.warnings,
        }


@mcp.tool(name="chart.render", description="Build a safe chart specification from query rows")
async def chart_render(context_token: str, rows: list[dict]) -> dict:
    verify_tool_context(context_token)
    if not rows:
        return {"spec": {"type": "table"}}
    fields = list(rows[0])
    numeric = next(
        (field for field, value in rows[0].items() if isinstance(value, (int, float))),
        fields[-1],
    )
    return {"spec": {"type": "bar", "x": fields[0], "y": numeric}}


@mcp.tool(
    name="report.export", description="Request a report export; execution requires human approval"
)
async def report_export(context_token: str, report_id: str, format: str = "pdf") -> dict:
    principal = verify_tool_context(context_token)
    if format != "pdf":
        raise ValueError("Only PDF export is supported")
    async with SessionLocal() as session:
        await set_tenant_context(session, principal.tenant_id)
        report = await session.scalar(
            select(Report).where(
                Report.id == report_id,
                Report.tenant_id == principal.tenant_id,
            )
        )
        if not report:
            raise ValueError("Report not found")
        approval = AgentApproval(
            tenant_id=principal.tenant_id,
            analysis_run_id=report.analysis_run_id,
            tool_name="report.export",
            side_effect="export",
            request_payload={"report_id": report_id, "format": format},
            requested_by=principal.user_id,
        )
        session.add(approval)
        await session.commit()
        await session.refresh(approval)
    return {
        "approval_id": approval.id,
        "report_id": report_id,
        "format": format,
        "status": "approval_required",
        "side_effect": "export",
        "requested_by": principal.user_id,
    }
