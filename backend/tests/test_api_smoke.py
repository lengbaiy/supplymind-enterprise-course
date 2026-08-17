from pathlib import Path

from fastapi.testclient import TestClient


def test_seeded_user_can_log_in_and_read_dashboard(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SUPPLYMIND_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SUPPLYMIND_JWT_SECRET", "test-secret-that-is-long-enough-for-tests")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@demo.local",
                "password": "ChangeMe123!",
                "organization_slug": "demo-factory",
            },
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        dashboard = client.get(
            "/api/v1/dashboards/supply-chain", headers={"Authorization": f"Bearer {token}"}
        )
        assert dashboard.status_code == 200
        assert len(dashboard.json()["cards"]) == 4
