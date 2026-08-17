from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardView(BaseModel):
    tenant_id: str
    dashboard_id: str
    name: str
    refreshed_at: datetime | None
    cache_status: str
    refresh_interval_seconds: int
    cards: list[dict[str, Any]]
    trend: list[dict[str, Any]]
