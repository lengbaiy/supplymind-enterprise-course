from pathlib import Path

from fastapi.testclient import TestClient


def test_knowledge_base_upload_and_tenant_scope(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'knowledge.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    monkeypatch.setenv("SUPPLYMIND_INGESTION_MODE", "eager")
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


def test_duplicate_upload_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'duplicate.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@demo.local", "password": "ChangeMe123!", "organization_slug": "demo-factory"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        knowledge_base = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "幂等测试库"}).json()
        upload_url = f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents"
        first = client.post(upload_url, headers=headers, files={"file": ("same.txt", b"same content", "text/plain")})
        second = client.post(upload_url, headers=headers, files={"file": ("same.txt", b"same content", "text/plain")})
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] == second.json()["id"]
        assert client.get(f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents", headers=headers).json().__len__() == 1


def test_search_returns_citations_and_rejects_unknown_tenant_resource(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'search.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    monkeypatch.setenv("SUPPLYMIND_INGESTION_MODE", "eager")
    monkeypatch.setenv("SUPPLYMIND_EMBEDDING_BASE_URL", "https://embedding.test/v1")
    monkeypatch.setenv("SUPPLYMIND_EMBEDDING_MODEL", "test-embedding")
    monkeypatch.setenv("SUPPLYMIND_EMBEDDING_API_KEY", "test-key")
    from app.core.config import get_settings
    from app.services.llm import OpenAICompatibleClient

    async def fake_embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(OpenAICompatibleClient, "embed", fake_embed)
    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@demo.local", "password": "ChangeMe123!", "organization_slug": "demo-factory"
        })
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        knowledge_base = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": "检索验收库"}).json()
        upload = client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents",
            headers=headers,
            files={"file": ("metric.md", b"Production attainment is completed quantity divided by planned quantity.", "text/markdown")},
        )
        assert upload.status_code == 201
        search = client.post(
            f"/api/v1/knowledge-bases/{knowledge_base['id']}/search",
            headers=headers,
            json={"query": "production attainment", "limit": 3},
        )
        assert search.status_code == 200
        result = search.json()["results"][0]
        assert result["document_name"] == "metric.md"
        assert result["score"] == 1.0
        assert "location" in result
        denied = client.post(
            "/api/v1/knowledge-bases/not-owned-by-this-tenant/search",
            headers=headers,
            json={"query": "production", "limit": 3},
        )
        assert denied.status_code == 404
