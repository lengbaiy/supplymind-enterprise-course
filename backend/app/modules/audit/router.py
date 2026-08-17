from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import require_role
from app.modules.audit.schemas import AuditEventView
from app.modules.audit.service import get_tenant_events
from app.schemas import Principal

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit", response_model=list[AuditEventView])
async def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_role("platform_admin", "org_admin")),
) -> list[AuditEventView]:
    events = await get_tenant_events(session, principal.tenant_id, limit)
    return [AuditEventView.model_validate(event) for event in events]
