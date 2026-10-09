"""Launch only the reviewed, packaged demo; never execute the user's working directory."""
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

PROJECT = Path(__file__).resolve().parents[2]
INVENTORY = Path(__file__).with_name("bundle-files.json")


def home():
    return Path(os.getenv("SHADOWLAB_HOME") or
                str(Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local/share")) / "shadowlab")).expanduser().resolve()


def bundled_workspace(base, source=PROJECT):
    files = json.loads(INVENTORY.read_text())
    digest = hashlib.sha256()
    for name in files:
        path = source / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink():
            raise ValueError("Invalid bundled asset")
        digest.update(name.encode() + b"\0" + path.read_bytes())
    destination = base / "bundles" / digest.hexdigest()[:20]
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in files:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # Keep cached builds, but restore reviewed source if a previous demo changed it.
        if not target.exists() or target.read_bytes() != (source / name).read_bytes():
            shutil.copyfile(source / name, target)
    shutil.copyfile(INVENTORY, destination / "packages/core/bundle-files.json")
    return destination


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def child_environment():
    # Preserve platform and managed transport trust, without inheriting application credentials.
    names = {"PATH", "HOME", "TMPDIR", "TEMP", "LANG", "LC_ALL", "SYSTEMROOT",
             "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
             "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
             "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS", "npm_config_cafile", "SHADOWLAB_CHROMIUM_PATH"}
    env = {key: value for key, value in os.environ.items() if key in names}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    return env


class DemoRuntime:
    def __init__(self, output=print, base=None):
        self.output = output
        self.base = Path(base) if base else home()
        self.processes = []
        self.client = None
        self.run_dir = None
        self.web_url = None

    def launch(self, command, cwd, env, log):
        with log.open("ab") as stream:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=stream,
                                       start_new_session=True)
        self.processes.append(process)
        return process

    def build(self, workspace, env):
        import fcntl
        with (workspace / ".setup-lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another console is preparing this demo; try again when it finishes") from None
            ready = workspace / ".ready"
            if ready.exists():
                return
            self.output("First demo: installing locked Node dependencies and building the local apps.")
            self.output("This may take a few minutes. Ctrl+C cancels setup.")
            for folder in ("apps/web", "examples/vulnerable-nextjs"):
                app = workspace / folder
                for args in (["npm", "ci", "--no-audit", "--no-fund"],
                             ["npm", "run", "build", "--", "--webpack"]):
                    process = self.launch(args, app, env, self.run_dir / "setup.log")
                    try:
                        status = process.wait(timeout=600)
                    except subprocess.TimeoutExpired:
                        raise TimeoutError("Demo setup exceeded its time limit") from None
                    if status:
                        raise ValueError(f"Demo setup failed; inspect {self.run_dir / 'setup.log'}")
            ready.touch()

    def start(self):
        if os.name != "posix":
            raise ValueError("The guided launcher requires macOS or Linux")
        for tool in ("node", "npm", "git"):
            if not shutil.which(tool):
                raise ValueError(f"Install {tool} before choosing Demo (Node.js 22 or newer)")
        version = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if version.returncode or int(version.stdout.lstrip("v").split(".")[0]) < 22:
            raise ValueError("Install Node.js 22 or newer before choosing Demo")
        self.base.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Workspace copying/builds are private, independent of the current directory.
        self.run_dir = self.base / "runs" / uuid4().hex
        self.run_dir.mkdir(parents=True, mode=0o700)
        workspace = bundled_workspace(self.base)
        env = child_environment()
        env["npm_config_cache"] = str(self.base / "cache/npm")
        env["SHADOWLAB_DATA_DIR"] = str(self.run_dir)
        self.build(workspace, env)
        api_port, web_port, demo_port = free_port(), free_port(), free_port()
        if len({api_port, web_port, demo_port}) != 3:
            raise ValueError("Could not reserve distinct local ports; try Demo again")
        token = secrets.token_urlsafe(32)
        token_file = self.run_dir / "api-token"
        with os.fdopen(os.open(token_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as file:
            file.write(token)
        api_url = f"http://127.0.0.1:{api_port}"
        self.web_url = f"http://127.0.0.1:{web_port}"
        env.update(SHADOWLAB_REPOSITORY_ROOT=str(workspace), PYTHONPATH=str(workspace),
                   SHADOWLAB_TOKEN_FILE=str(token_file), SHADOWLAB_API_URL=api_url,
                   SHADOWLAB_DEMO_ORIGIN=f"http://127.0.0.1:{demo_port}")
        self.launch([sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1",
                     "--port", str(api_port), "--timeout-graceful-shutdown", "1"],
                    workspace, env, self.run_dir / "api.log")
        for folder, port, log in (("apps/web", web_port, "web.log"),
                                  ("examples/vulnerable-nextjs", demo_port, "demo.log")):
            self.launch(["node", ".next/standalone/server.js"], workspace / folder,
                        {**env, "HOSTNAME": "127.0.0.1", "PORT": str(port)}, self.run_dir / log)
        self.client = httpx.Client(base_url=api_url, headers={"Authorization": f"Bearer {token}"},
                                   timeout=180, trust_env=False, follow_redirects=False)
        deadline = time.monotonic() + 45
        with httpx.Client(timeout=2, trust_env=False, follow_redirects=False) as probe:
            while time.monotonic() < deadline:
                if any(process.poll() is not None for process in self.processes[-3:]):
                    raise ValueError(f"A demo service exited; inspect logs in {self.run_dir}")
                try:
                    urls = [api_url + "/api/v1/health", self.web_url + "/api/v1/health",
                            env["SHADOWLAB_DEMO_ORIGIN"] + "/api/session"]
                    if all(probe.get(url).status_code == 200 for url in urls):
                        self.output(f"Local workspace: {self.web_url}/app")
                        self.output(f"Private demo records and logs: {self.run_dir}")
                        return self
                except httpx.HTTPError:
                    pass
                time.sleep(0.25)
        raise TimeoutError(f"Demo services did not become ready; inspect {self.run_dir}")

    def request(self, method, path, **kwargs):
        response = self.client.request(method, "/api/v1" + path, **kwargs)
        if response.status_code >= 400:
            # Do not print server response bodies which might contain sensitive values.
            raise ValueError(f"Demo request failed (HTTP {response.status_code}); inspect the local logs")
        return response

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
        for process in reversed(self.processes):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in self.processes:
            try:
                # Let the API cancel in-flight browser/patch tasks and run their cleanup handlers.
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
        self.processes.clear()
