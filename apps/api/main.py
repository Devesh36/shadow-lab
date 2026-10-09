import asyncio
import json
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse

from packages.core.auth import api_token
from packages.core.models import RepositoryCreate, ScanCreate, Settings, SettingsPatch
from packages.core.report import report
from packages.core.service import Service
from packages.db.store import Store
from packages.policies.engine import PolicyDenied


def create_app(store=None):
    store = store or Store()
    store.initialize()
    service = Service(store)
    token = api_token(store.data_dir)

    @asynccontextmanager
    async def lifespan(app):
        # Single-worker local application. Checkpoints remain inspectable after interruption;
        # runtime actions are never automatically replayed following a process restart.
        for scan in store.list("scan"):
            if scan["status"] in ("queued", "running"):
                store.put("scan", {"status": "interrupted", "stage": "interrupted"}, id=scan["id"])
        yield
        await service.close()

    app = FastAPI(title="ShadowLab", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.state.service = service
    patch_lock = asyncio.Lock()

    def authenticate(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Valid API bearer token required")
        supplied = (authorization or "").removeprefix("Bearer ")
        if not secrets.compare_digest(supplied, token):
            raise HTTPException(401, "Valid API bearer token required")

    protected = [Depends(authenticate)]

    def get(kind, id):
        doc = store.get(kind, id)
        if not doc:
            raise HTTPException(404, f"{kind.title()} not found")
        return doc

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/api/v1/repositories", dependencies=protected, status_code=201)
    def add_repository(request: RepositoryCreate):
        try:
            return service.add_repository(request)
        except (ValueError, OSError):
            raise HTTPException(422, "Repository must exist within the configured repository root") from None

    @app.get("/api/v1/repositories", dependencies=protected)
    def repositories():
        return store.list("repository")

    @app.post("/api/v1/scans", dependencies=protected, status_code=202)
    async def create_scan(request: ScanCreate):
        try:
            scan = service.create_scan(request)
            service.start(scan["id"])
            return scan
        except PolicyDenied as exc:
            raise HTTPException(403, str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.get("/api/v1/scans", dependencies=protected)
    def scans():
        return store.list("scan")

    @app.get("/api/v1/scans/{id}", dependencies=protected)
    def scan(id: str):
        return {**get("scan", id), "findings": store.list("finding", id)}

    @app.post("/api/v1/scans/{id}/cancel", dependencies=protected)
    async def cancel(id: str):
        get("scan", id)
        cancelled = service.cancel(id)
        if cancelled:
            await asyncio.gather(service.tasks[id], return_exceptions=True)
        return {"cancelled": cancelled, "scan": get("scan", id)}

    @app.get("/api/v1/scans/{id}/events", dependencies=protected)
    async def events(id: str):
        get("scan", id)

        async def stream():
            seen = set()
            while True:
                for event in store.list("event", id):
                    if event["id"] not in seen:
                        seen.add(event["id"])
                        yield f"id: {event['id']}\ndata: {json.dumps(event)}\n\n"
                if get("scan", id)["status"] not in ("running", "queued"):
                    yield "event: done\ndata: {}\n\n"
                    return
                yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/api/v1/findings", dependencies=protected)
    def findings(scan_id: str | None = None):
        return store.list("finding", scan_id)

    @app.get("/api/v1/findings/{id}", dependencies=protected)
    def finding(id: str):
        return get("finding", id)

    @app.post("/api/v1/findings/{id}/propose-fix", dependencies=protected)
    async def propose_fix(id: str):
        finding = get("finding", id)
        from packages.remediation.patches import propose
        try:
            if patch_lock.locked():
                raise HTTPException(409, "A patch verification is already running")
            async with patch_lock:
                return await propose(store, finding)
        except (ValueError, OSError) as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/api/v1/findings/{id}/screenshot", dependencies=protected)
    async def capture(id: str):
        finding = get("finding", id)
        if not finding["evidence"]:
            raise HTTPException(422, "No runtime evidence to capture")
        from uuid import uuid4
        from packages.execution.browser import screenshot_evidence
        screenshot_id = str(uuid4())
        folder = store.data_dir / "screenshots"
        folder.mkdir(exist_ok=True)
        try:
            await screenshot_evidence({"title": finding["title"], "evidence": finding["evidence"]},
                                      folder / f"{screenshot_id}.png")
        except Exception:
            raise HTTPException(503, "Chromium is unavailable; install Playwright Chromium or set SHADOWLAB_CHROMIUM_PATH") from None
        return store.put("screenshot", {"description": "Sanitized evidence rendering; not a target browser session"},
                         id=screenshot_id, parent_id=id)

    @app.get("/api/v1/evidence/{id}/screenshot", dependencies=protected)
    def screenshot(id: str):
        record = get("screenshot", id)
        return FileResponse(store.data_dir / "screenshots" / f"{record['id']}.png", media_type="image/png")

    @app.get("/api/v1/browser-evidence/{id}", dependencies=protected)
    def browser_screenshot(id: str):
        from uuid import UUID
        try:
            safe_id = str(UUID(id))
        except ValueError:
            raise HTTPException(404, "Browser artifact not found") from None
        get("browser-artifact", safe_id)
        path = store.data_dir / "browser-evidence" / f"{safe_id}.png"
        if not path.is_file():
            raise HTTPException(404, "Browser artifact file unavailable")
        return FileResponse(path, media_type="image/png")

    @app.get("/api/v1/findings/{id}/patch", dependencies=protected)
    def patch(id: str):
        get("finding", id)
        patches = store.list("patch", id)
        if not patches:
            raise HTTPException(404, "No proposed patch")
        return patches[-1]

    @app.get("/api/v1/reports/{scan_id}", dependencies=protected)
    def export_report(scan_id: str, format: Literal["markdown", "json"] = "markdown"):
        get("scan", scan_id)
        return PlainTextResponse(report(store, scan_id, format), media_type="application/json" if format == "json" else "text/markdown")

    @app.get("/api/v1/settings", dependencies=protected)
    def settings():
        value = store.settings().model_dump(mode="json")
        if value["fixture"]:
            value["fixture"] = {"endpoint": value["fixture"]["endpoint"], "owner_token": "[REDACTED]", "other_token": "[REDACTED]"}
        import os
        value["llm_key_configured"] = bool(os.getenv("SHADOWLAB_LLM_API_KEY"))
        return value

    @app.patch("/api/v1/settings", dependencies=protected)
    def update_settings(request: SettingsPatch):
        values = {**store.settings().model_dump(), **request.model_dump(exclude_unset=True)}
        try:
            store.save_settings(Settings.model_validate(values))
        except ValueError:
            raise HTTPException(422, "Invalid settings") from None
        return settings()

    return app


app = create_app()
