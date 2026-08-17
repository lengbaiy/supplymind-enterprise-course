from pathlib import Path

from fastapi.testclient import TestClient


def test_organization_summary_quota_and_permissions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'organization.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={
            "email": "admin@demo.local", "password": "ChangeMe123!", "organization_slug": "demo-factory"
        })
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        summary = client.get("/api/v1/organization", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["slug"] == "demo-factory"
        assert summary.json()["member_count"] >= 1
        assert summary.json()["quota"]["daily_analysis_runs"] == 100

        updated = client.patch("/api/v1/organization/quotas", headers=headers, json={
            "max_concurrent_analyses": 8,
            "daily_analysis_runs": 200,
            "max_document_size_mb": 20,
            "retention_days": 180,
        })
        assert updated.status_code == 200
        assert updated.json()["max_concurrent_analyses"] == 8

        matrix = client.get("/api/v1/organization/permissions", headers=headers)
        assert matrix.status_code == 200
        assert matrix.json()["roles"]["viewer"]["run_analysis"] is False
