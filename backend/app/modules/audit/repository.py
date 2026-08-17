from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


async def list_events(session: AsyncSession, tenant_id: str, limit: int) -> list[AuditEvent]:
    result = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(limit)
    )
    return list(result)
