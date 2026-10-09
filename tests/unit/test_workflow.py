import asyncio
import sqlite3

from packages.agents.workflow import Workflow
from packages.core.models import RepositoryCreate, ScanCreate
from packages.core.service import Service


async def test_graph_transitions_persistence_and_static_states(store, monkeypatch):
    async def scanner(root):
        return {"status": "completed", "findings": []}
    monkeypatch.setattr("packages.agents.workflow.semgrep", scanner)
    monkeypatch.setattr("packages.agents.workflow.osv", scanner)
    service = Service(store)
    repository = service.add_repository(RepositoryCreate(path="examples/vulnerable-nextjs"))
    scan = service.create_scan(ScanCreate(repository_id=repository["id"]))
    await Workflow(store, scan["id"]).run()
    assert store.get("scan", scan["id"])["status"] == "completed"
    assert [e["stage"] for e in store.list("event", scan["id"])] == ["reconnaissance", "hypotheses", "planning", "validation", "reporting"]
    findings = store.list("finding", scan["id"])
    assert len(findings) >= 3
    assert all(f["state"] == "INCONCLUSIVE" and not f["evidence"] for f in findings)
    from packages.db.store import Store
    reopened = Store(str(store.engine.url))
    assert reopened.get("scan", scan["id"])["status"] == "completed"
    with sqlite3.connect(store.data_dir / "checkpoints.db") as db:
        assert db.execute("select count(*) from checkpoints").fetchone()[0] >= 5


async def test_scan_cancellation(store, monkeypatch):
    started = asyncio.Event()
    async def recon(self, state):
        started.set()
        await asyncio.Event().wait()
    monkeypatch.setattr(Workflow, "recon", recon)
    service = Service(store)
    repository = service.add_repository(RepositoryCreate(path="examples/vulnerable-nextjs"))
    scan = service.create_scan(ScanCreate(repository_id=repository["id"]))
    service.start(scan["id"])
    await asyncio.wait_for(started.wait(), 2)
    assert service.cancel(scan["id"])
    await service.tasks[scan["id"]]
    assert store.get("scan", scan["id"])["status"] == "cancelled"


async def test_cancellation_before_first_task_step(store):
    service = Service(store)
    repository = service.add_repository(RepositoryCreate(path="examples/vulnerable-nextjs"))
    scan = service.create_scan(ScanCreate(repository_id=repository["id"]))
    service.start(scan["id"])
    assert service.cancel(scan["id"])
    await asyncio.gather(service.tasks[scan["id"]], return_exceptions=True)
    assert store.get("scan", scan["id"])["status"] == "cancelled"
    assert not store.list("execution", scan["id"])
