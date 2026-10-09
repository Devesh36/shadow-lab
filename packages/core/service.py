import asyncio
from pathlib import Path
import os

from packages.agents.workflow import Workflow
from packages.core.models import RepositoryCreate, ScanCreate
from packages.policies.engine import PolicyDenied, origin


class Service:
    def __init__(self, store):
        self.store = store
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancellations: dict[str, asyncio.Event] = {}
        self.demo_settings = {}

    def add_repository(self, request: RepositoryCreate):
        allowed = Path(os.getenv("SHADOWLAB_REPOSITORY_ROOT", ".")).resolve()
        raw = Path(request.path).expanduser()
        path = (allowed / raw).resolve(strict=True) if not raw.is_absolute() else raw.resolve(strict=True)
        if not path.is_dir() or not path.is_relative_to(allowed):
            raise ValueError("Repository must be a directory below SHADOWLAB_REPOSITORY_ROOT")
        for repo in self.store.list("repository"):
            if repo["path"] == str(path):
                return repo
        return self.store.put("repository", {"path": str(path), "name": request.name or path.name})

    def create_scan(self, request: ScanCreate, settings=None):
        repo = self.store.get("repository", request.repository_id)
        if not repo:
            raise ValueError("Repository does not exist")
        if request.browser and not request.dynamic:
            raise ValueError("Browser validation requires a dynamic trusted-demo scan")
        if request.dynamic:
            if not request.target:
                raise ValueError("Dynamic scans require a target")
            settings = settings or self.store.settings()
            target_origin = origin(str(request.target))
            target = next((t for t in settings.targets if origin(str(t.url)) == target_origin), None)
            if not target or not target.authorized or not target.approved:
                raise PolicyDenied("Authorize and approve the exact target origin in Settings first")
            if settings.sandbox_mode != "trusted-local":
                raise PolicyDenied("Dynamic scans require trusted-local mode")
            if request.browser:
                from packages.execution.demo_browser import require_demo
                require_demo(Path(repo["path"]), settings, str(request.target))
        if sum(not task.done() for task in self.tasks.values()) >= 2:
            raise ValueError("At most two concurrent scans are supported")
        return self.store.put("scan", {**request.model_dump(mode="json"), "status": "queued", "stage": "queued"})

    def start(self, scan_id):
        cancellation = asyncio.Event()
        self.cancellations[scan_id] = cancellation
        task = asyncio.create_task(Workflow(self.store, scan_id, cancellation, self.demo_settings.get(scan_id)).run())
        self.tasks[scan_id] = task
        task.add_done_callback(lambda _: self.cancellations.pop(scan_id, None))
        task.add_done_callback(lambda _: self.demo_settings.pop(scan_id, None))

    def create_demo(self, browser=False):
        from packages.core.demo_scope import demo_settings
        from packages.execution.demo_browser import DEMO, require_demo
        settings = demo_settings(os.getenv("SHADOWLAB_DEMO_ORIGIN", "http://127.0.0.1:3001"))
        target = str(settings.targets[0].url)
        require_demo(DEMO, settings, target)
        repo = self.add_repository(RepositoryCreate(path=str(DEMO), name="ShadowLab synthetic demo"))
        scan = self.create_scan(ScanCreate(repository_id=repo["id"], target=target, dynamic=True, browser=browser), settings)
        self.store.put("scan", {"demo": True}, id=scan["id"])
        self.demo_settings[scan["id"]] = settings
        self.start(scan["id"])
        return self.store.get("scan", scan["id"])

    def cancel(self, scan_id):
        task = self.tasks.get(scan_id)
        if task and not task.done():
            self.cancellations[scan_id].set()
            # A task cancelled before its first coroutine step cannot run its handler.
            if self.store.get("scan", scan_id)["status"] == "queued":
                self.store.put("scan", {"status": "cancelled", "stage": "cancelled"}, id=scan_id)
                self.store.event(scan_id, "cancelled", "Scan cancelled before execution")
            task.cancel()
            return True
        return False

    async def close(self):
        tasks = [t for t in self.tasks.values() if not t.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
