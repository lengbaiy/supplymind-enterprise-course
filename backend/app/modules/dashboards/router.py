from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_principal
from app.modules.dashboards.schemas import DashboardView
from app.modules.dashboards.service import get_supply_chain_dashboard
from app.schemas import Principal

router = APIRouter(prefix="/api/v1", tags=["dashboards"])


@router.get("/dashboards/supply-chain", response_model=DashboardView)
async def supply_chain_dashboard(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(get_principal),
) -> dict:
    return await get_supply_chain_dashboard(session, principal.tenant_id)
