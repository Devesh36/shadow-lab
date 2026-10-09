import asyncio
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
from pathlib import Path
from uuid import uuid4

from packages.agents.workflow import classify
from packages.core.models import FindingState, Settings, SyntheticFixture, Target, TestPlan
from packages.execution.gateway import Gateway
from packages.policies.engine import PolicyEngine

PROJECT = Path(__file__).resolve().parents[2]
DEMO = PROJECT / "examples/vulnerable-nextjs"
MANIFEST = PROJECT / "infrastructure/sandbox/demo-manifest.json"
FIXES = {
    "bola": ("app/api/records/[id]/route.ts", "  // SHADOWLAB_FIX: ownership",
             "  if (record.ownerId !== user.id) return Response.json({ error: 'Forbidden' }, { status: 403 });"),
    "authentication": ("app/api/unprotected/route.ts", "  // SHADOWLAB_FIX: authentication",
                       "  const user = requireAuth(request);\n  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 });"),
    "exposure": ("app/api/profile/route.ts", "  return Response.json(profile);",
                 "  return Response.json({ id: profile.id, name: profile.name });"),
}


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, text=True,
                          capture_output=True, timeout=10).stdout


def snapshot_demo(destination: Path):
    manifest = json.loads(MANIFEST.read_text())
    for relative, expected in manifest.items():
        file = DEMO / relative
        if file.is_symlink() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise ValueError("Trusted demo has changed; refuse execution until its changes are reviewed")
    destination.mkdir(parents=True)
    for relative in manifest:
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEMO / relative, output)
    git(destination, "init", "-q")
    git(destination, "add", ".")
    git(destination, "-c", "user.name=ShadowLab", "-c", "user.email=shadowlab@localhost", "commit", "-qm", "Trusted synthetic fixture snapshot")


async def verify(worktree: Path, finding: dict, budget=30):
    binary = DEMO / "node_modules/next/dist/bin/next"
    if not binary.exists():
        raise ValueError("Install the demo with npm ci before proposing a verified fix")
    (worktree / "node_modules").symlink_to(DEMO / "node_modules", target_is_directory=True)
    with socket.socket() as allocator:
        allocator.bind(("127.0.0.1", 0))
        port = allocator.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    env = {"PATH": os.defpath, "NEXT_TELEMETRY_DISABLED": "1", "NODE_ENV": "development"}
    node = shutil.which("node")
    if not node:
        raise ValueError("Node.js is required for trusted demo regression verification")
    process = subprocess.Popen([node, str(binary), "dev", "--webpack", "--hostname", "127.0.0.1", "--port", str(port)],
                               cwd=worktree, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    settings = Settings(targets=[Target(url=origin, authorized=True, approved=True, allow_loopback=True)],
                        sandbox_mode="trusted-local", fixture=SyntheticFixture(), timeout_seconds=10,
                        request_budget=20, requests_per_second=5)
    gateway = Gateway(PolicyEngine(settings, origin), asyncio.Event())
    try:
        async with asyncio.timeout(budget):
            for _ in range(20):
                if process.poll() is not None:
                    raise ValueError("Patched trusted demo exited before readiness")
                try:
                    ready = await gateway.request(TestPlan(category="headers", path="/"))
                    if ready["status"] == 200:
                        break
                except (OSError, TimeoutError, __import__("httpx").HTTPError):
                    await asyncio.sleep(0.2)
            else:
                raise ValueError("Patched trusted demo failed readiness")
            evidence = [await gateway.request(TestPlan.model_validate(plan)) for plan in finding["plans"]]
            status, explanation = classify(finding["category"], evidence)
            # Always verify owners retain access, even after a sensitive-field projection.
            owner = await gateway.request(TestPlan(category="bola", path="/api/records/alice-record", identity="owner"))
            other_owned = await gateway.request(TestPlan(category="bola", path="/api/records/bob-record", identity="other"))
            passed = status == FindingState.NOT_REPRODUCED and owner["status"] == 200 and other_owned["status"] == 200
            return {"passed": passed, "validation": explanation, "original_test": evidence,
                    "owner_access": owner["status"], "other_owner_access": other_owned["status"],
                    "test_count": len(evidence) + 2, "target": origin}
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                await asyncio.to_thread(process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                await asyncio.to_thread(process.wait, timeout=5)


async def propose(store, finding):
    if finding["state"] not in (FindingState.CONFIRMED, FindingState.AWAITING_REVIEW, FindingState.FIX_PROPOSED):
        raise ValueError("Only confirmed findings can receive a patch proposal")
    scan = store.get("scan", finding["parent_id"])
    repo = store.get("repository", scan["repository_id"])
    if Path(repo["path"]).resolve() != DEMO.resolve() or finding["category"] not in FIXES:
        raise ValueError("Verified automatic patches currently support only the shipped trusted demo's ownership, authentication, and exposure defects")
    file, before, after = FIXES[finding["category"]]
    if not any(ref["file"] == file for ref in finding["sources"]):
        raise ValueError("Finding does not reference the supported source location")
    root = store.data_dir / "patches" / str(uuid4())
    snapshot = root / "snapshot"
    worktree = root / "worktree"
    await asyncio.to_thread(snapshot_demo, snapshot)
    await asyncio.to_thread(git, snapshot, "worktree", "add", "-q", "-b", "proposed-fix", str(worktree))
    source = worktree / file
    text = source.read_text()
    if text.count(before) != 1:
        raise ValueError("Expected trusted source pattern was not found exactly once")
    source.write_text(text.replace(before, after))
    regression = worktree / "shadowlab-regression.json"
    regression.write_text(json.dumps({"category": finding["category"], "plans": finding["plans"],
                                     "expected": "NOT_REPRODUCED; owner fixtures remain available"}, indent=2))
    store.put("finding", {"state": FindingState.FIX_PROPOSED}, id=finding["id"])
    try:
        result = await verify(worktree, finding)
    except Exception as exc:
        result = {"passed": False, "validation": "Verification failed: " + type(exc).__name__, "test_count": 0}
    # Omit unchanged context: unrelated source literals (including synthetic secrets)
    # should not be copied into evidence, patch previews, or exported reports.
    diff = await asyncio.to_thread(git, worktree, "diff", "--unified=0", "--", file)
    patch = store.put("patch", {"diff": diff, "regression_plan": json.loads(regression.read_text()),
                                "verification": result, "worktree": str(worktree),
                                "review_required": True, "merged": False}, parent_id=finding["id"])
    if result["passed"]:
        store.put("finding", {"state": FindingState.FIX_TESTED}, id=finding["id"])
        store.event(scan["id"], "remediation", "Regression verification passed", finding_id=finding["id"])
        store.put("finding", {"state": FindingState.AWAITING_REVIEW}, id=finding["id"])
    else:
        store.event(scan["id"], "remediation", "Patch remains unverified", finding_id=finding["id"])
    return patch
