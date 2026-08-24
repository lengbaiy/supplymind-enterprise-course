"""Celery entry point. Long-running parsing, embedding and report tasks belong here."""

import asyncio
from datetime import UTC, datetime
from hashlib import sha256 as sha256_digest

from celery import Celery
from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import (
    DashboardRefreshTask,
    DataSource,
    DataSourceSyncTask,
    Document,
    EvaluationRun,
    IngestionTask,
    OutboxEvent,
    Report,
    ReportExport,
    SchemaSnapshot,
)
from app.modules.dashboards.service import refresh_supply_chain_dashboard
from app.services.datasource import synchronize_schema
from app.services.ingestion import process_ingestion
from app.services.reports import render_pdf
from app.services.storage import configured as storage_configured
from app.services.storage import put_file
from app.services.task_watchdog import RetryRequest, reconcile_stalled_tasks

celery_app = Celery("supplymind", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.task_routes = {"supplymind.*": {"queue": "analysis"}}
celery_app.conf.beat_schedule = {
    "reconcile-stalled-tasks": {
        "task": "supplymind.tasks.reconcile_stalled",
        "schedule": 60.0,
    },
    "dispatch-analysis-outbox": {
        "task": "supplymind.outbox.dispatch",
        "schedule": 2.0,
    },
}


@celery_app.task(
    bind=True,
    name="supplymind.analysis.execute",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def execute_analysis(self, run_id: str) -> str:
    from app.agents.executor import EnterpriseAnalysisExecutor

    asyncio.run(EnterpriseAnalysisExecutor().execute(run_id))
    return run_id


@celery_app.task(
    bind=True,
    name="supplymind.evaluations.run",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def execute_evaluation(self, evaluation_id: str) -> str:
    async def run() -> None:
        from app.evals.service import run_evaluation

        async with SessionLocal() as session:
            evaluation = await session.scalar(
                select(EvaluationRun).where(EvaluationRun.id == evaluation_id)
            )
            if not evaluation:
                return
            try:
                await run_evaluation(session, evaluation)
            except Exception as exc:
                await session.rollback()
                evaluation = await session.scalar(
                    select(EvaluationRun).where(EvaluationRun.id == evaluation_id)
                )
                if evaluation:
                    evaluation.status = "failed"
                    evaluation.failure_reason = str(exc)[:1000]
                    await session.commit()
                raise

    asyncio.run(run())
    return evaluation_id


@celery_app.task(name="supplymind.outbox.dispatch")
def dispatch_outbox() -> int:
    async def claim() -> list[tuple[str, str]]:
        async with SessionLocal() as session:
            query = (
                select(OutboxEvent)
                .where(
                    OutboxEvent.status == "pending",
                    OutboxEvent.available_at <= datetime.now(UTC),
                )
                .order_by(OutboxEvent.created_at)
                .limit(50)
            )
            if session.get_bind() is not None and session.get_bind().dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            events = list(await session.scalars(query))
            claimed: list[tuple[str, str]] = []
            for event in events:
                event.status = "processing"
                event.attempts += 1
                claimed.append((event.id, event.aggregate_id))
            await session.commit()
            return claimed

    async def finish(event_id: str, error: str | None = None) -> None:
        async with SessionLocal() as session:
            event = await session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
            if not event:
                return
            event.status = "failed" if error else "completed"
            event.error_message = error
            event.processed_at = datetime.now(UTC) if not error else None
            await session.commit()

    claimed = asyncio.run(claim())
    for event_id, run_id in claimed:
        try:
            celery_app.send_task("supplymind.analysis.execute", args=[run_id], queue="analysis")
            asyncio.run(finish(event_id))
        except Exception as exc:
            asyncio.run(finish(event_id, str(exc)[:500]))
    return len(claimed)


@celery_app.task(
    bind=True,
    name="supplymind.datasource.sync_schema",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def sync_datasource_schema(self, task_id: str) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            task = await session.scalar(
                select(DataSourceSyncTask).where(DataSourceSyncTask.id == task_id)
            )
            if not task:
                return
            source = await session.scalar(
                select(DataSource).where(
                    DataSource.id == task.data_source_id, DataSource.tenant_id == task.tenant_id
                )
            )
            if not source:
                task.status = "failed"
                task.error_message = "Data source not found"
                task.finished_at = datetime.now(UTC)
                await session.commit()
                return
            task.status = "running"
            task.attempts += 1
            task.started_at = datetime.now(UTC)
            task.finished_at = None
            source.status = "syncing"
            await session.commit()
            try:
                schema = await synchronize_schema(source)
                snapshot = SchemaSnapshot(
                    tenant_id=task.tenant_id,
                    data_source_id=source.id,
                    tables=schema.tables,
                    table_count=len(schema.tables),
                )
                session.add(snapshot)
                await session.flush()
                task.status = "completed"
                task.snapshot_id = snapshot.id
                task.finished_at = datetime.now(UTC)
                source.status = "active"
                source.last_synced_at = task.finished_at
            except Exception:
                task.status = "failed"
                task.error_message = "Schema synchronization failed"
                task.finished_at = datetime.now(UTC)
                source.status = "failed"
            await session.commit()

    asyncio.run(run())
    return task_id


@celery_app.task(
    bind=True,
    name="supplymind.dashboards.refresh",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def refresh_dashboard(
    self, tenant_id: str, filters: dict[str, str | None] | None = None, task_id: str | None = None
) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            task = (
                await session.scalar(
                    select(DashboardRefreshTask).where(
                        DashboardRefreshTask.id == task_id,
                        DashboardRefreshTask.tenant_id == tenant_id,
                    )
                )
                if task_id
                else None
            )
            if task:
                task.status = "running"
                task.attempts += 1
                task.started_at = datetime.now(UTC)
                task.finished_at = None
                task.celery_task_id = self.request.id
                await session.commit()
            try:
                await refresh_supply_chain_dashboard(session, tenant_id, filters)
                if task:
                    task.status = "completed"
                    task.finished_at = datetime.now(UTC)
            except Exception as exc:
                if task:
                    task.status = "failed"
                    task.error_message = str(exc)[:500]
                    task.finished_at = datetime.now(UTC)
                raise
            await session.commit()

    asyncio.run(run())
    return tenant_id


@celery_app.task(
    bind=True,
    name="supplymind.documents.ingest",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def ingest_document(self, task_id: str) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            task = await session.scalar(select(IngestionTask).where(IngestionTask.id == task_id))
            if not task:
                return
            document = await session.scalar(select(Document).where(Document.id == task.document_id))
            if not document:
                task.status = "failed"
                task.error_message = "Document not found"
            else:
                await process_ingestion(session, task, document)
            task.celery_task_id = self.request.id
            await session.commit()

    asyncio.run(run())
    return task_id


@celery_app.task(
    bind=True,
    name="supplymind.reports.export_pdf",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def export_report_pdf(self, export_id: str) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            export = await session.scalar(select(ReportExport).where(ReportExport.id == export_id))
            if not export:
                return
            report = await session.scalar(select(Report).where(Report.id == export.report_id))
            export.status = "running"
            export.attempts += 1
            export.started_at = datetime.now(UTC)
            export.finished_at = None
            export.celery_task_id = self.request.id
            await session.commit()
            if not report:
                export.status = "failed"
                export.error_message = "Report not found"
            else:
                try:
                    from pathlib import Path

                    directory = Path(get_settings().report_directory)
                    directory.mkdir(parents=True, exist_ok=True)
                    path = directory / f"{report.id}-{export.id}.pdf"
                    render_pdf(report.markdown, str(path))
                    object_key = f"{export.tenant_id}/reports/{report.id}/{export.id}.pdf"
                    put_file(str(path), object_key)
                    export.object_key = object_key
                    export.storage_backend = "s3" if storage_configured() else "local"
                    export.file_path = str(path) if export.storage_backend == "local" else None
                    export.checksum_sha256 = sha256_digest(path.read_bytes()).hexdigest()
                    export.status = "completed"
                    export.error_message = None
                except (OSError, RuntimeError, ValueError) as exc:
                    export.status = "failed"
                    export.error_message = str(exc)[:500]
            export.finished_at = datetime.now(UTC)
            await session.commit()

    asyncio.run(run())
    return export_id


@celery_app.task(name="supplymind.tasks.reconcile_stalled")
def reconcile_stalled() -> int:
    async def run() -> list[RetryRequest]:
        async with SessionLocal() as session:
            return await reconcile_stalled_tasks(session)

    retries = asyncio.run(run())
    for retry in retries:
        celery_app.send_task(retry.task_name, args=retry.args)
    return len(retries)
