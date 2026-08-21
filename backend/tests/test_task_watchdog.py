import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models import Base, IngestionTask
from app.services.task_watchdog import reconcile_stalled_tasks


def test_watchdog_requeues_stale_ingestion_once(tmp_path) -> None:
    async def run() -> None:
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'watchdog.db'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        created_at = datetime.now(UTC) - timedelta(minutes=30)
        async with sessions() as session:
            task = IngestionTask(
                tenant_id="tenant-watchdog",
                document_id="document-watchdog",
                task_key="watchdog-test-task",
                status="processing",
                attempts=1,
                max_attempts=3,
                created_at=created_at,
                updated_at=created_at,
            )
            session.add(task)
            await session.commit()
            retries = await reconcile_stalled_tasks(
                session,
                now=datetime.now(UTC),
                settings=Settings(
                    task_queued_timeout_seconds=60,
                    task_running_timeout_seconds=60,
                ),
            )
            restored = await session.scalar(select(IngestionTask).where(IngestionTask.id == task.id))
            assert restored is not None
            assert restored.status == "queued"
            assert "重新排队" in (restored.error_message or "")
            assert [retry.task_name for retry in retries] == ["supplymind.documents.ingest"]
        await engine.dispose()

    asyncio.run(run())
