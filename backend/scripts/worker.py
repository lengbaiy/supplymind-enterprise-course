"""Celery entry point. Long-running parsing, embedding and report tasks belong here."""
import asyncio

from celery import Celery
from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.models import Document, IngestionTask
from app.services.ingestion import process_ingestion

celery_app = Celery("supplymind", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.task_routes = {"supplymind.*": {"queue": "analysis"}}


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
