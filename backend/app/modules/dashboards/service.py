from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import Dashboard
from app.modules.dashboards.repository import get_dashboard, save_dashboard

DEFAULT_PAYLOAD: dict[str, Any] = {
    "cards": [
        {"label": "生产达成率", "value": "91.4%", "change": "+1.8%"},
        {"label": "缺料物料", "value": "12", "change": "-3"},
        {"label": "质量合格率", "value": "98.2%", "change": "+0.4%"},
        {"label": "订单准时交付", "value": "94.7%", "change": "+2.1%"},
    ],
    "trend": [
        {"month": "3月", "rate": 88.2},
        {"month": "4月", "rate": 89.6},
        {"month": "5月", "rate": 90.1},
        {"month": "6月", "rate": 91.4},
    ],
}


async def _redis_payload(key: str) -> dict[str, Any] | None:
    client = Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        value = await client.get(key)
        if value:
            import json

            return json.loads(value)
    except Exception:
        return None
    finally:
        await client.aclose()
    return None


async def _cache_payload(key: str, payload: dict[str, Any], ttl: int) -> None:
    client = Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
    try:
        import json

        await client.set(key, json.dumps(payload), ex=ttl)
    except Exception:
        return
    finally:
        await client.aclose()


async def get_supply_chain_dashboard(session: AsyncSession, tenant_id: str) -> dict[str, Any]:
    dashboard = await get_dashboard(session, tenant_id, "supply-chain")
    now = datetime.now(UTC)
    if not dashboard:
        dashboard = await save_dashboard(
            session,
            Dashboard(
                tenant_id=tenant_id,
                name="供应链运营大屏",
                slug="supply-chain",
                refresh_interval_seconds=300,
                cached_payload=DEFAULT_PAYLOAD,
                cached_at=now,
            ),
        )
        await session.commit()
    age = now - dashboard.cached_at if dashboard.cached_at else timedelta.max
    cache_key = f"supplymind:dashboard:{tenant_id}:{dashboard.slug}"
    cached = await _redis_payload(cache_key)
    if cached:
        payload = cached
        cache_status = "redis"
    elif age.total_seconds() <= dashboard.refresh_interval_seconds:
        payload = dashboard.cached_payload
        cache_status = "database"
    else:
        payload = dashboard.cached_payload or DEFAULT_PAYLOAD
        dashboard.cached_at = now
        await session.commit()
        await _cache_payload(cache_key, payload, dashboard.refresh_interval_seconds)
        cache_status = "refreshed"
    return {
        "tenant_id": tenant_id,
        "dashboard_id": dashboard.id,
        "name": dashboard.name,
        "refreshed_at": dashboard.cached_at,
        "cache_status": cache_status,
        "refresh_interval_seconds": dashboard.refresh_interval_seconds,
        **payload,
    }
