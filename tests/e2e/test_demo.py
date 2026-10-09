import os
import socket
from urllib.parse import urlsplit

import pytest

from packages.agents.workflow import Workflow
from packages.core.models import RepositoryCreate, ScanCreate, Settings, SyntheticFixture, Target
from packages.core.report import report
from packages.core.service import Service
from packages.remediation.patches import DEMO, propose


@pytest.mark.e2e
async def test_discovery_validation_patch_and_regression(store):
    target = os.getenv("SHADOWLAB_TEST_TARGET")
    if not target:
        pytest.skip("Start the disposable demo and set SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001")
    store.save_settings(Settings(targets=[Target(url=target, authorized=True, approved=True, allow_loopback=True)],
                                 fixture=SyntheticFixture(), sandbox_mode="trusted-local", timeout_seconds=10,
                                 request_budget=150, requests_per_second=5, scan_timeout_seconds=180))
    service = Service(store)
    repo = service.add_repository(RepositoryCreate(path=str(DEMO)))
    scan = service.create_scan(ScanCreate(repository_id=repo["id"], dynamic=True, target=target, browser=True))
    await Workflow(store, scan["id"]).run()
    assert store.get("scan", scan["id"])["status"] == "completed"
    assert store.get("scan", scan["id"])["scanners"]["semgrep"]["status"] == "completed"
    findings = store.list("finding", scan["id"])
    for category in ("bola", "authentication", "exposure"):
        finding = next(f for f in findings if f["category"] == category)
        assert finding["state"] == "CONFIRMED", finding["validation"]
        assert finding["evidence"] and finding["sources"]
        assert finding["browser"]["status"] == "completed" and finding["browser"]["verdict"] == "CONFIRMED"
        patch = await propose(store, finding)
        assert patch["verification"]["passed"], patch["verification"]
        browser = patch["verification"]["browser"][category]
        assert browser["status"] == "completed" and browser["verdict"] == "NOT_REPRODUCED"
        assert browser["checks"] == finding["browser"]["checks"]
        assert patch["diff"].startswith("diff --git") and patch["review_required"] and not patch["merged"]
        assert store.get("finding", finding["id"])["state"] == "AWAITING_REVIEW"
        origin = urlsplit(patch["verification"]["target"])
        with socket.socket() as connection:
            assert connection.connect_ex((origin.hostname, origin.port)) != 0, "Patched demo must be cleaned up"
    assert "synthetic-not-a-real-key" not in report(store, scan["id"])
    assert "demo-alice" not in report(store, scan["id"], "json")
    assert "Browser authorization validation" in report(store, scan["id"])
    assert "record.ownerId !== user.id" not in (DEMO / "app/api/records/[id]/route.ts").read_text()
