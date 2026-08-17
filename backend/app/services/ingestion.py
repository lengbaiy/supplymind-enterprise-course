from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document, IngestionTask
from app.services.knowledge import chunk_text, extract_text


async def process_ingestion(session: AsyncSession, task: IngestionTask, document: Document) -> None:
    """Idempotently process a persisted document. Safe to call from API or Celery."""
    task.status = "processing"
    task.attempts += 1
    document.status = "processing"
    await session.flush()
    try:
        if not document.source_path:
            raise ValueError("Document source is unavailable")
        payload = Path(document.source_path).read_bytes()
        text, metadata = extract_text(document.filename, document.content_type, payload)
        await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
        for ordinal, value, location in chunk_text(text):
            location.update(metadata)
            session.add(Chunk(tenant_id=document.tenant_id, document_id=document.id, ordinal=ordinal, text=value, location=location))
        document.status = "completed"
        task.status = "completed"
        task.error_message = None
    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)
        task.status = "failed"
        task.error_message = str(exc)
        raise
