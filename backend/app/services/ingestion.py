from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Chunk, Document, IngestionTask
from app.services.knowledge import chunk_text, extract_text
from app.services.llm import OpenAICompatibleClient


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
        pieces = list(chunk_text(text))
        vectors = []
        settings = get_settings()
        if pieces and settings.embedding_base_url and settings.embedding_model and settings.embedding_api_key:
            vectors = await OpenAICompatibleClient().embed([piece[1] for piece in pieces])
        for index, (ordinal, value, location) in enumerate(pieces):
            location.update(metadata)
            session.add(Chunk(tenant_id=document.tenant_id, document_id=document.id, ordinal=ordinal, text=value, location=location, embedding=vectors[index] if vectors else None))
        document.status = "completed"
        task.status = "completed"
        task.error_message = None
    except Exception as exc:
        document.status = "failed"
        document.error_message = str(exc)
        task.status = "failed"
        task.error_message = str(exc)
        raise
