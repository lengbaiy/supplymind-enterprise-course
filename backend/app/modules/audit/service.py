from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent
from app.modules.audit.repository import list_events


async def get_tenant_events(session: AsyncSession, tenant_id: str, limit: int = 100) -> list[AuditEvent]:
    return await list_events(session, tenant_id, limit)
