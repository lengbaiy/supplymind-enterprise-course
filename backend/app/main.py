from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import router
from app.core.config import get_settings
from app.core.security import encrypt_secret, hash_password
from app.db import SessionLocal, engine, set_tenant_context
from app.models import Base, DataSource, Membership, Organization, User


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
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
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
app.include_router(router)
