import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document
from app.services.llm import OpenAICompatibleClient


class RetrievalError(RuntimeError):
    pass


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left or not right:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def search_knowledge(
    session: AsyncSession, tenant_id: str, knowledge_base_id: str, query: str, limit: int = 5
) -> list[dict]:
    vector = (await OpenAICompatibleClient().embed([query]))[0]
    rows = await session.execute(
        select(Chunk, Document)
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.tenant_id == tenant_id,
            Document.tenant_id == tenant_id,
            Document.knowledge_base_id == knowledge_base_id,
            Document.status == "completed",
        )
    )
    ranked = [
        (cosine_similarity(vector, chunk.embedding), chunk, document)
        for chunk, document in rows.all()
        if chunk.embedding
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "text": chunk.text,
            "score": round(score, 6),
            "document_id": document.id,
            "document_name": document.filename,
            "location": chunk.location,
            "chunk_id": chunk.id,
        }
        for score, chunk, document in ranked[:limit]
    ]
