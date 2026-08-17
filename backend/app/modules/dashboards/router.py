from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db import get_session
from app.dependencies import get_principal, require_role
from app.modules.dashboards.schemas import DashboardView
from app.modules.dashboards.service import get_supply_chain_dashboard
from app.schemas import Principal
from app.services.audit import audit

router = APIRouter(prefix="/api/v1", tags=["dashboards"])


@router.get("/dashboards/supply-chain", response_model=DashboardView)
async def supply_chain_dashboard(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_principal),
) -> dict:
    return await get_supply_chain_dashboard(session, principal.tenant_id)


@router.post("/dashboards/supply-chain/refresh", status_code=202)
async def refresh_supply_chain_dashboard(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_role("org_admin", "platform_admin")),
) -> dict[str, str]:
    if get_settings().ingestion_mode == "broker":
        from scripts.worker import celery_app

        task = celery_app.send_task("supplymind.dashboards.refresh", args=[principal.tenant_id])
        await audit(
            session,
            principal.tenant_id,
            principal.user_id,
            "dashboard.refresh_queued",
            "dashboard",
            None,
            {"task_id": task.id},
        )
        await session.commit()
        return {"status": "queued", "task_id": task.id}
    from app.modules.dashboards.service import refresh_supply_chain_dashboard as refresh

    await refresh(session, principal.tenant_id)
    await audit(session, principal.tenant_id, principal.user_id, "dashboard.refreshed", "dashboard")
    await session.commit()
    return {"status": "completed", "task_id": "eager"}
