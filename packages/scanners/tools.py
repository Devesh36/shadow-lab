import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RULES = Path(__file__).with_name("rules.yml")


async def semgrep(root: Path):
    local = Path(sys.executable).with_name("semgrep")
    binary = shutil.which("semgrep") or (str(local) if local.is_file() else None)
    if not binary:
        return {"status": "unavailable", "findings": [], "reason": "Install the locked Python dependencies"}
    data = Path(os.getenv("SHADOWLAB_DATA_DIR", ".shadowlab")).resolve() / "semgrep"
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    scanner_env = {**os.environ, "SEMGREP_SETTINGS_FILE": str(data / "settings.yml"),
                   "SEMGREP_LOG_FILE": str(data / "semgrep.log")}
    try:
        result = await asyncio.to_thread(subprocess.run, [binary, "scan", "--config", str(RULES),
                                        "--json", "--metrics=off", "--disable-version-check",
                                        "--max-target-bytes=1000000", "--timeout=5", str(root)],
                                        capture_output=True, text=True, timeout=45, env=scanner_env)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "findings": [], "reason": "Semgrep exceeded its 45-second budget"}
    if result.returncode != 0:
        return {"status": "failed", "findings": [], "reason": "Semgrep failed; run doctor / scanner manually"}
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return {"status": "failed", "findings": [], "reason": "Semgrep did not return JSON"}
    findings = []
    for item in payload.get("results", [])[:100]:
        path = Path(item["path"]).resolve()
        if not path.is_relative_to(root):
            continue
        findings.append({"rule": item["check_id"], "file": str(path.relative_to(root)),
                         "line": item["start"]["line"], "message": item["extra"]["message"],
                         "severity": item["extra"]["severity"]})
    return {"status": "completed", "findings": findings, "errors": len(payload.get("errors", []))}


async def osv(root: Path):
    installed = Path(os.getenv("SHADOWLAB_DATA_DIR", ".shadowlab")) / "tools/osv-scanner"
    binary = shutil.which("osv-scanner") or (str(installed.resolve()) if installed.is_file() else None)
    if not binary:
        return {"status": "unavailable", "findings": [], "reason": "Optional OSV-Scanner binary is absent"}
    try:
        result = await asyncio.to_thread(subprocess.run,
                                    [binary, "scan", "source", "--no-resolve", "--no-call-analysis=go",
                                     "--no-call-analysis=rust", "--experimental-no-default-plugins",
                                     "--experimental-plugins=lockfile", "--config", str(RULES.with_name("osv.toml")),
                                     "--format=json", "-r", str(root)],
                                    capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "findings": [], "reason": "OSV exceeded its 45-second budget"}
    if result.returncode not in (0, 1):
        return {"status": "failed", "findings": [], "reason": "OSV scan failed; verify OSV network access"}
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return {"status": "failed", "findings": [], "reason": "OSV did not return JSON"}
    findings = []
    for group in payload.get("results", []):
        for package in group.get("packages", []):
            for vulnerability in package.get("vulnerabilities", []):
                findings.append({"id": vulnerability.get("id"), "package": package.get("package", {}),
                                 "summary": vulnerability.get("summary", "Known dependency vulnerability")})
    return {"status": "completed", "findings": findings[:100]}
