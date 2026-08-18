"""Celery entry point. Long-running parsing, embedding and report tasks belong here."""
import asyncio
from hashlib import sha256 as sha256_digest

from celery import Celery
from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import Document, IngestionTask, Report, ReportExport
from app.modules.dashboards.service import refresh_supply_chain_dashboard
from app.services.ingestion import process_ingestion
from app.services.reports import render_pdf

celery_app = Celery("supplymind", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.task_routes = {"supplymind.*": {"queue": "analysis"}}


@celery_app.task(bind=True, name="supplymind.dashboards.refresh", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def refresh_dashboard(self, tenant_id: str, filters: dict[str, str | None] | None = None) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            await refresh_supply_chain_dashboard(session, tenant_id, filters)

    asyncio.run(run())
    return tenant_id


@celery_app.task(bind=True, name="supplymind.documents.ingest", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
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


@celery_app.task(bind=True, name="supplymind.reports.export_pdf", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def export_report_pdf(self, export_id: str) -> str:
    async def run() -> None:
        async with SessionLocal() as session:
            export = await session.scalar(select(ReportExport).where(ReportExport.id == export_id))
            if not export:
                return
            report = await session.scalar(select(Report).where(Report.id == export.report_id))
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
                    export.file_path = str(path)
                    export.checksum_sha256 = sha256_digest(path.read_bytes()).hexdigest()
                    export.status = "completed"
                    export.error_message = None
                except (OSError, RuntimeError, ValueError) as exc:
                    export.status = "failed"
                    export.error_message = str(exc)[:500]
            export.celery_task_id = self.request.id
            await session.commit()
    asyncio.run(run())
    return export_id
