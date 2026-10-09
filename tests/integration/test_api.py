from fastapi.testclient import TestClient

from apps.api.main import create_app
from packages.core.auth import api_token


def test_api_auth_scope_settings_and_reports(store):
    headers = {"Authorization": f"Bearer {api_token(store.data_dir)}"}
    with TestClient(create_app(store)) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/repositories").status_code == 401
        assert client.patch("/api/v1/settings", json={"request_budget": 0}, headers=headers).status_code == 422
        assert client.post("/api/v1/repositories", json={"path": "/etc"}, headers=headers).status_code == 422
        repo = client.post("/api/v1/repositories", json={"path": "examples/vulnerable-nextjs"}, headers=headers)
        assert repo.status_code == 201
        denied = client.post("/api/v1/scans", json={"repository_id": repo.json()["id"], "dynamic": True,
                                                     "target": "http://127.0.0.1:3001"}, headers=headers)
        assert denied.status_code == 403
        settings = client.patch("/api/v1/settings", json={"fixture": {"owner_token": "test-alice", "other_token": "test-bob"}}, headers=headers)
        assert settings.status_code == 200 and settings.json()["fixture"]["owner_token"] == "[REDACTED]"
        assert client.get("/api/v1/findings/nonexistent", headers=headers).status_code == 404
        scan = store.put("scan", {"status": "completed", "stage": "completed"})
        store.event(scan["id"], "completed", "Done")
        report = client.get(f"/api/v1/reports/{scan['id']}", headers=headers)
        assert report.status_code == 200 and "ShadowLab security report" in report.text
        events = client.get(f"/api/v1/scans/{scan['id']}/events", headers=headers)
        assert "Done" in events.text and "event: done" in events.text
        assert client.post(f"/api/v1/scans/{scan['id']}/cancel", headers=headers).json()["cancelled"] is False


def test_postgres_persistence_if_configured(monkeypatch, tmp_path):
    import os
    import pytest
    from packages.db.store import Store
    url = os.getenv("SHADOWLAB_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set SHADOWLAB_TEST_POSTGRES_URL for PostgreSQL integration")
    monkeypatch.setenv("SHADOWLAB_DATA_DIR", str(tmp_path))
    db = Store(url)
    db.initialize()
    saved = db.put("integration-test", {"evidence": {"status": 403}, "state": "NOT_REPRODUCED"})
    db.engine.dispose()
    reopened = Store(url)
    assert reopened.get("integration-test", saved["id"])["evidence"]["status"] == 403
    reopened.engine.dispose()


def test_browser_evidence_requires_auth_and_persisted_artifact(store):
    from uuid import uuid4
    artifact = str(uuid4())
    folder = store.data_dir / 'browser-evidence'
    folder.mkdir()
    (folder / f'{artifact}.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    headers = {'Authorization': f'Bearer {api_token(store.data_dir)}'}
    with TestClient(create_app(store)) as client:
        assert client.get(f'/api/v1/browser-evidence/{artifact}').status_code == 401
        assert client.get(f'/api/v1/browser-evidence/{artifact}', headers=headers).status_code == 404
        store.put('browser-artifact', {'description': 'Sanitized projection'}, id=artifact)
        response = client.get(f'/api/v1/browser-evidence/{artifact}', headers=headers)
        assert response.status_code == 200 and response.headers['content-type'] == 'image/png'
        assert client.get('/api/v1/browser-evidence/invalid', headers=headers).status_code == 404
