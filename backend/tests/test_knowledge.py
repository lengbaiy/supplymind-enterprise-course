from pathlib import Path

from fastapi.testclient import TestClient


def test_knowledge_base_upload_and_tenant_scope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'knowledge.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@demo.local", "password": "ChangeMe123!", "organization_slug": "demo-factory"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "制造口径"})
        assert created.status_code == 201
        knowledge_base_id = created.json()["id"]
        uploaded = client.post(
            f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
            headers=headers,
            files={"file": ("rules.md", b"production_rate = completed / planned", "text/markdown")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["status"] == "completed"
        task = client.get(
            f"/api/v1/ingestion-tasks/{uploaded.json()['ingestion_task_id']}", headers=headers
        )
        assert task.status_code == 200
        assert task.json()["status"] == "completed"
        assert uploaded.json()["chunk_count"] == 1
        listed = client.get(f"/api/v1/knowledge-bases/{knowledge_base_id}/documents", headers=headers)
        assert listed.status_code == 200
        assert listed.json()[0]["filename"] == "rules.md"


def test_chunker_handles_overlap() -> None:
    from app.services.knowledge import chunk_text

    chunks = list(chunk_text("a" * 2500, size=1000, overlap=100))
    assert len(chunks) == 3
    assert chunks[1][2]["start"] == 900
