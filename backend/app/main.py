from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import router
from app.core.config import get_settings
from app.core.security import encrypt_secret, hash_password
from app.db import SessionLocal, engine, set_tenant_context
from app.models import Base, DataSource, Membership, Organization, User
from app.modules.audit.router import router as audit_router
from app.observability import HTTP_REQUEST_DURATION, HTTP_REQUESTS


async def seed_demo_data() -> None:
    async with SessionLocal() as session:
        organization = await session.scalar(select(Organization).where(Organization.slug == "demo-factory"))
        if organization:
            return
        organization = Organization(slug="demo-factory", name="示范制造集团")
        user = User(email="admin@demo.local", display_name="课程管理员", password_hash=hash_password("ChangeMe123!"))
        session.add_all([organization, user])
        await session.flush()
        await set_tenant_context(session, organization.id)
        session.add(Membership(organization_id=organization.id, user_id=user.id, role="org_admin"))
        session.add(
            DataSource(
                tenant_id=organization.id,
                name="制造供应链演示库",
                engine="postgresql",
                host="demo-data",
                port=5432,
                database_name="manufacturing_demo",
                username="readonly_demo",
                encrypted_password=encrypt_secret("not-a-live-credential"),
                allowed_tables=["production_orders", "inventory_risk"],
            )
        )
        await session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_schema or settings.is_development:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    if settings.is_development:
        await seed_demo_data()
    yield
    await engine.dispose()


settings = get_settings()
app = FastAPI(title="SupplyMind API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    started = perf_counter()
    response = await call_next(request)
    route = getattr(request.scope.get("route"), "path", request.url.path)
    HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    HTTP_REQUEST_DURATION.labels(request.method, route).observe(perf_counter() - started)
    return response


app.include_router(router)
app.include_router(audit_router)
