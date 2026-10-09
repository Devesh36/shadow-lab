# Troubleshooting

## API disconnected

Start the API from the repository root with `uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`. The web proxy reads `.shadowlab/api-token` relative to the web directory or uses `SHADOWLAB_API_TOKEN`. A different data directory requires `SHADOWLAB_TOKEN_FILE` on the web server. Environment configuration must be present when starting both processes. Never print tokens in logs or browser configuration.

## Target rejected

Set the exact origin, authorization, and execution approval. Dynamic mode must be `trusted-local`; loopback requires the explicit per-target exception. Ports are part of the scope. Private networks, metadata, redirects, ambiguous DNS, unsafe paths, and exhausted budgets are denied. Use operator cancellation to stop a running scan; permission changes take effect on new scans.

## Inconclusive authorization tests

The owner must return a JSON resource with `id` and `ownerId`. BOLA also requires a second successful baseline with a different `ownerId`. Supply `fixture.endpoint`, `fixture.other_endpoint`, and two distinct synthetic bearer tokens through the authenticated settings API. These are fixture contracts. Cookie/session testing is supported only through the fixed trusted demo browser adapter. A generic 200 page or a missing fixture cannot confirm authorization bypass.

## Patch refused

Only the shipped, checksum-verified demo and its three supported defects can be patched automatically. Confirm the demo npm dependencies are installed. A modified source or package manifest requires manual review, not automatic checksum updates. Inspect the persisted patch verification result and proposed diff. Worktrees remain below `.shadowlab/patches`; delete an artifact directory only after its review and after ensuring no fixture process remains. No patch has been merged.

## Semgrep, OSV, or Chromium unavailable

Run `uv sync --locked`; Semgrep is a required locked dependency. The adapter writes Semgrep state inside `SHADOWLAB_DATA_DIR`, so read-only home directories are supported. Local rules avoid registry access. OSV is optional: install with `bash scripts/install-osv.sh` and allow `api.osv.dev`. Dependency resolution and call analysis are disabled. A failed scanner is not a clean result. Chromium can be installed with `uv run playwright install chromium` or selected with `SHADOWLAB_CHROMIUM_PATH`; the evidence renderer never accesses the target network. The demo browser adapter requires its production UI/assets (developer HMR and query routes are intentionally unsupported), exact `127.0.0.1` origin and default fixtures. Increase the saved request/time budget explicitly for asset and identity checks; it never increases permissions automatically. Look at the browser coverage status and sanitized error type. Unsupported setup, timeouts, blocked requests, or inconsistent identity/control results are inconclusive. No proxy credentials are passed to Chromium.

## Cloud proxy CA and Docker builds

On this managed cloud, image downloads work, but package requests from Docker build containers need the provided CA. The Dockerfiles accept an optional public certificate as the `custom-ca` BuildKit secret and install it into the system trust store. TLS verification stays enabled. For example, create a temporary Compose override outside the checkout:

```yaml
services:
  api:
    build:
      secrets: [custom-ca]
  web:
    build:
      secrets: [custom-ca]
  demo:
    build:
      secrets: [custom-ca]
secrets:
  custom-ca:
    file: /usr/local/share/ca-certificates/environment-proxy-ca.crt
```

Then use `docker compose -f docker-compose.yml -f /tmp/shadowlab-ca.yml up --build`. Supply only the environment's authorized CA, never credential files. On a read-only home directory set `BUILDX_CONFIG=/workspace/.cache/buildx`, `UV_CACHE_DIR=/workspace/.cache/uv`, and `npm_config_cache=/workspace/.cache/npm`. The native setup helper already configures its caches.

## Database migrations and concurrency

`uv run alembic upgrade head` and initialization are repeatable. The baseline migration can adopt the exact early local schema, but refuses incompatible tables. Prefer PostgreSQL for Docker; SQLite is a useful local default. One API worker owns scan tasks. Multiple API workers, distributed scheduling, automatic checkpoint replay, and multi-user deployments are unsupported.

## Ports already occupied

Stop only the ShadowLab services you started. The startup helper treats a failing child as a failure and cleans up its process groups. Docker validation can use a temporary override with alternate published host ports; container tests still target port 3001 in their shared loopback namespace.
