# ShadowLab

Local-first application security investigations with source analysis, scoped runtime tests, inspectable evidence, and reviewed fixes.

ShadowLab is a working V1 vertical slice. It parses Next.js routes, runs local Semgrep rules, builds hypotheses in a persistent LangGraph workflow, tests explicitly approved applications, stores findings in PostgreSQL or SQLite, and proposes verified patches for its shipped synthetic demo. A rule-based investigation works without an LLM key; LiteLLM can optionally prioritize its typed hypotheses.

## Start locally

Prerequisites: Linux, Python 3.12+, uv, Node.js 22+, npm, and Git. Other operating systems can run the Python/web tools, but process-group cleanup and the startup helper currently target Linux.

```bash
git clone https://github.com/Devesh36/shadow-lab.git
cd shadow-lab
bash scripts/setup.sh
bash scripts/start.sh
```

The helper starts the API on port 8000, dashboard on port 3000, and disposable demo on port 3001, bound to loopback. Stop the helper with Ctrl+C to stop all three. In development, replace each Next.js production start with `npm run dev -- --webpack` in its app directory and run the API with `uv run uvicorn apps.api.main:app --reload`.

Local persistence defaults to `.shadowlab/shadowlab.db`. `SHADOWLAB_DATABASE_URL` selects PostgreSQL; `SHADOWLAB_DATA_DIR` holds checkpoints, patches, and sanitized screenshots. A random API bearer token is generated in `.shadowlab/api-token` with mode 0600. The dashboard uses a server-side proxy; it never sends that token to the browser. The API exposes OpenAPI at `/docs`; protected operations require the token. This is a single-user, local dashboard. Public hosting requires an authenticated reverse proxy and a different deployment design.

## Docker development with PostgreSQL

Docker Engine and Compose are required. Generate the local API token securely, then build and start:

```bash
cp .env.example .env
python scripts/compose-init.py
docker compose up --build
```

The helper fills only an absent or empty API token and preserves other values. Compose persists PostgreSQL and API artifacts in named volumes. Its fixed `shadowlab-local` database password is a synthetic local lab credential; the database is not published to the host. Services run without privileges, capabilities, host credentials, or a Docker socket. The internal lab network restricts outbound traffic. A fixed nginx ingress proxy publishes loopback-only ports and forwards to these services; only this credential-free proxy joins an external bridge. Shared lab networking keeps dynamic requests on an exact loopback origin; it is not tenant isolation. Compose runs only the reviewed, shipped applications. It does **not** provide a security boundary for arbitrary untrusted repositories.

For this managed cloud's TLS inspection, Docker builds need its provided CA through the optional `custom-ca` BuildKit secret. See [troubleshooting](docs/troubleshooting.md). Never disable TLS verification.

## Reproduce the demo

1. Start the three services above.
2. In **Repositories**, register `examples/vulnerable-nextjs` (`/app/examples/vulnerable-nextjs` in Docker).
3. In **Settings**, enter `http://127.0.0.1:3001`, explicitly authorize the application, approve bounded execution, allow loopback, and select the synthetic demo fixtures. Save.
4. In **Scan workspace**, select that repository, enter the same target, and run an investigation.
5. Inspect the real execution evidence in **Findings**. The demo demonstrates broken object authorization, missing authentication, sensitive response fields, and missing defense-in-depth headers.
6. For ownership, authentication, or exposure, select **Propose & verify fix**. ShadowLab snapshots the trusted fixture into a disposable Git repository and creates a separate worktree. It applies a minimal fix, generates a typed regression plan, starts the patched fixture, reruns the original test, checks both owners retain access, and stops the fixture.
7. Inspect the diff and verification result. Successful patches enter `AWAITING_REVIEW`; they are never merged or deployed. Export a Markdown report from the workspace.

All identities, tokens, and data in the demo are synthetic. [Intentional defects](examples/vulnerable-nextjs/README.md) are documented. Automatic patch verification refuses any change to the trusted demo manifest until reviewed. General repositories get analysis and suggested remediation, not automatic code execution or unverified claims of a fix.

The same workflow is available through the CLI:

```bash
uv run shadowlab init
uv run shadowlab analyze ./examples/vulnerable-nextjs
uv run shadowlab scan --repository examples/vulnerable-nextjs \
  --target http://127.0.0.1:3001 --authorize --approve --demo-fixtures
uv run shadowlab findings
uv run shadowlab report --format markdown
uv run shadowlab doctor
```

`--authorize` and `--approve` explicitly grant testing permission for that origin. `--demo-fixtures` permits loopback and selects the shipped synthetic identities. Later scans can reuse saved permissions. Without a target, `scan` runs static analysis and labels its hypotheses `INCONCLUSIVE`. Custom synthetic identities and record paths can be configured through `PATCH /api/v1/settings`.

## Tests

```bash
uv run ruff check packages apps/api tests scripts
uv run pytest -q -m 'not e2e'
# With the demo running:
SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001 uv run pytest -q -m e2e
# Optional PostgreSQL persistence coverage:
SHADOWLAB_TEST_POSTGRES_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB uv run pytest -q tests/integration/test_api.py
npm --prefix apps/web run typecheck
npm --prefix apps/web run build -- --webpack
```

The E2E test verifies route discovery, real Semgrep completion, three confirmed vulnerabilities, three fixes, regression results, report redaction, unchanged demo sources, and terminated patch processes. Tests mock optional LLM calls and reject model attempts to create arbitrary actions. PostgreSQL and E2E tests are explicitly skipped without their prerequisites; CI supplies both. See [validation evidence](docs/validation.md) for the actual checks run in this workspace.

## Optional integrations

- **OSV-Scanner:** `bash scripts/install-osv.sh` installs pinned v2.6.0 with a verified SHA-256. Scans use lockfile plugins, disable dependency resolution and call analysis, and require `api.osv.dev`. Missing or denied access appears as `unavailable` or `failed`, never a clean dependency result. OSV was validated against both updated npm locks: neither returned known advisories in that run. The required domain is saved in the environment draft.
- **LLM:** Set `SHADOWLAB_LLM_API_KEY` in the server environment and enable prioritization in Settings. Use `openai/...`, `anthropic/...`, or LiteLLM-compatible local models with a base URL. One structured tool call selects existing hypotheses; it cannot create targets, commands, or override policy. Real hosted-provider calls have not been validated in this workspace. Source metadata is sent only when enabled.
- **Playwright:** `uv run playwright install chromium` or set `SHADOWLAB_CHROMIUM_PATH` to an installed Chromium. `POST /api/v1/findings/{id}/screenshot` renders sanitized HTTP evidence with scripts and networking disabled. Retrieve it through `/api/v1/evidence/{id}/screenshot`. This is an evidence capture tool, not browser-based exploitation.
- **ZAP:** `packages/scanners/zap.py` provides an operator-only passive alert adapter for an existing trusted daemon. ZAP active scanning and automatic crawling are not wired into the graph.

## Architecture and limits

`apps/api` serves the versioned API. `apps/web` is the Next.js dashboard. `packages/agents` owns the graph, `analyzers` source intelligence, `policies` authorization, `execution` bounded tools, `evidence` redaction, `db` persistence and migrations, and `remediation` patch verification. CLI and API share the same service and workflow.

The analyzer uses Tree-sitter for parsing and source positions, with framework-specific heuristic classification. It does not establish complete roles, middleware behavior, authorization data flows, or program-wide soundness. Findings require identifiable seeded resources and distinct owner baselines before BOLA confirmation. Exposure is based on nonempty sensitive field names; manual review still determines business impact. HTTP tests are non-destructive GETs only, with exact origins, pinned DNS, redirect rejection, private-address restrictions, and execution budgets.

Future work: VM-backed arbitrary-repository execution, generalized patch generation, browser identity workflows, deeper source/data-flow adapters, stronger multi-user auth/RBAC, provider integration tests, and CI pull-request delivery. Checkpoints are persisted for inspection; interrupted scans do not automatically replay actions after restart. The API supports one worker and at most two concurrent scans.

See [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [security policy](SECURITY.md), [troubleshooting](docs/troubleshooting.md), and [contributing](CONTRIBUTING.md). MIT licensed.
