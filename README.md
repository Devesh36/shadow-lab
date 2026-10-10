# ShadowLab

Local-first application security investigations with source analysis, scoped runtime tests, inspectable evidence, and reviewed fixes.

ShadowLab is a working V1 vertical slice. It parses Next.js routes, runs local Semgrep rules, builds hypotheses in a persistent LangGraph workflow, tests explicitly approved applications, validates the trusted local demo with isolated browser identities, stores findings in PostgreSQL or SQLite, and proposes verified patches for its shipped synthetic demo. A rule-based investigation works without an LLM key; LiteLLM can optionally prioritize its typed hypotheses.

## Quick start: install and choose Demo

On macOS or Linux, install from GitHub with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install --python 3.12 "git+https://github.com/Devesh36/shadow-lab.git@main"
shadow repl
```

Or use the custom Homebrew tap:

```bash
brew tap devesh36/shadowlab https://github.com/Devesh36/shadow-lab.git
brew install --HEAD devesh36/shadowlab/shadowlab
shadow repl
```

If `shadow` is not on your PATH after installation, run `uv tool update-shell` and reopen your terminal.

Type **`demo`** or **`1`** at `shadow>`. ShadowLab prepares its bundled synthetic application, starts three private loopback services, runs a real investigation, and opens the workspace. `shadow Repl` also works; `shadowlab` remains a compatibility alias. Git-based uv installation and the HEAD formula work without a PyPI package or stable release. Homebrew installation has not been tested on macOS in this Linux workspace; its formula is syntax-checked and has a native installation CI job.

For uv installs, first install **Node.js 22+, npm and Git**. Python 3.12+ is required; uv can provision it. Homebrew declares these runtime dependencies. First demo preparation requires internet access to fetch locked npm packages and may take several minutes. Later runs reuse the build. The guided launcher supports macOS/Linux; native macOS behavior has not been exercised here. On Windows, use a Linux environment such as WSL.

| Console command | Action |
| --- | --- |
| `demo` / `1` | Authorize bounded tests of the bundled synthetic local app and open its investigation |
| `demo browser` | Repeat with isolated anonymous/Alice/Bob browser sessions; Chromium is required |
| `project PATH` | Select a project for isolated source-only analysis; quote paths with spaces |
| `scan` / `routes` | Analyze the selected project / inspect discovered routes |
| `history` / `use NUMBER` | List the ten latest project scans / select one for findings and export |
| `findings` | Show the latest investigation's actual verdicts |
| `fix NUMBER` | Explicitly approve a disposable patch experiment for a supported finding; review remains required |
| `report` / `report json` | Export Markdown; JSON is available in project mode |
| `doctor` / `2` | Check local launcher prerequisites |
| `stop` | Stop local services, retaining saved evidence |
| `help` / `quit` | Show commands / close the console and stop its services |

The REPL executes fixed actions, never arbitrary shell or Python input. Every launch gets fresh ports, a private API token and separate SQLite state. It copies only an explicit bundle of reviewed files into `~/.local/share/shadowlab`; `SHADOWLAB_HOME` overrides this location. `runs/` contains reports, logs, evidence and disposable patch worktrees; `bundles/` contains reusable builds. It preserves the current working directory, source checkout and existing operator database/settings. Quit, EOF and Ctrl+C clean up its service processes; Ctrl+C during an investigation cancels it. Patches are never applied to the bundled source, merged or deployed.

Optional browser prerequisite (matching the shipped Playwright version):

```bash
uvx --from playwright==1.63.0 playwright install chromium
# Or point to an existing compatible system Chromium:
export SHADOWLAB_CHROMIUM_PATH=/absolute/path/to/chromium
```

Linux needs Chromium's system libraries; see Playwright's installation guidance. Missing/unsupported setup is shown as incomplete browser coverage. The default `demo` needs no browser installation or LLM key. For CLI updates, rerun the uv install with `--reinstall`, or use `brew upgrade --fetch-HEAD devesh36/shadowlab/shadowlab`.

## Analyze your own project in the console

```bash
cd /path/to/your-nextjs-project
shadow repl
```

At `shadow>`:

```text
project .
scan
routes
findings
history
report
report json
quit
```

Project sessions read source and run the installed local Semgrep rules. They never run project scripts, install dependencies, start your app, make target requests, call an LLM or apply patches. Findings remain `INCONCLUSIVE`; scanner failures and disabled dependency coverage are shown explicitly. This is Next.js heuristic analysis, not a complete security assessment.

The selected directory must be inside `SHADOWLAB_REPOSITORY_ROOT`, which defaults to the directory where you launched the console. From a parent directory, `project "Mixed Case Project"` preserves spaces and case. Project history and exports live in private `SHADOWLAB_HOME/projects/<path-hash>/` storage, separate from demo runs and the operator database. Reopening the same path restores its latest scan; `history` numbers are newest first and `use 2` selects the preceding scan. Exported source paths and findings should be reviewed before sharing.

Only one scan per project can run at a time. Ctrl+C stops the analysis worker and its scanner processes, records incomplete coverage, and lets you retry with `scan`. Failed scans stay visible in history and never inherit the previous scan's verdict. `stop` deselects the project but retains its history. `demo` switches back to the shipped synthetic app; `fix NUMBER` is available only there. The standalone CLI remains supported.

## Start from a checkout

Prerequisites: Linux, Python 3.12+, uv, Node.js 22+, npm, and Git. The original shell startup helper targets Linux; the guided REPL uses portable POSIX process groups.

```bash
git clone https://github.com/Devesh36/shadow-lab.git
cd shadow-lab
bash scripts/setup.sh
bash scripts/start.sh
```

The helper starts the API on port 8000, website on port 3000, and disposable demo on port 3001, bound to loopback. Open `http://127.0.0.1:3000` for the Next.js landing page, `/demo` for a guided investigation, or `/app` for the preserved workspace. Selecting **Start demo** explicitly authorizes only the bundled loopback fixture and uses per-scan settings without changing saved operator settings. Stop the helper with Ctrl+C to stop all three. In development, replace each Next.js production start with `npm run dev -- --webpack` in its app directory and run the API with `uv run uvicorn apps.api.main:app --reload`.

Local persistence defaults to `.shadowlab/shadowlab.db`. `SHADOWLAB_DATABASE_URL` selects PostgreSQL; `SHADOWLAB_DATA_DIR` holds checkpoints, patches, and sanitized screenshots. A random API bearer token is generated in `.shadowlab/api-token` with mode 0600. The dashboard uses a server-side proxy; it never sends that token to the browser. The API exposes OpenAPI at `/docs`; protected operations require the token. This is a single-user, local dashboard. Public hosting requires an authenticated reverse proxy and a different deployment design.

## Deploy the landing page on Vercel

Import this repository and select the branch containing `apps/landing`. Set **Root Directory to `apps/landing`**, framework **Next.js**, and build command **`npm run build`**. Leave the **Output Directory override disabled** so Vercel detects the Next.js output. Then select **Deploy**. No application environment variables or secrets are required.

This separate app exports the product website and a **Docs** page at `/docs/`, with uv/Homebrew setup, a guided REPL walkthrough, project analysis instructions, and nine sanitized screenshots from actual terminal recordings. Its demo links lead to local installation instructions; the API, dashboard, database and investigation engine stay in the local product. See [Vercel setup and local preview](docs/vercel.md).

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

For the simplest route, open `/demo` and select **Start demo**. The following manual workflow remains available at `/app`:

1. Start the three services above.
2. In **Repositories**, register `examples/vulnerable-nextjs` (`/app/examples/vulnerable-nextjs` in Docker).
3. In **Settings**, enter `http://127.0.0.1:3001`, explicitly authorize the application, approve bounded execution, allow loopback, and select the synthetic demo fixtures. Save.
4. In **Scan workspace**, select that repository and enter the same target.
5. Optionally enable **Validate the trusted local demo UI with three isolated browser identities** in Scan workspace. For the full browser workflow, explicitly save a request budget of 150 and scan timeout of 180 seconds through the settings API; the defaults remain unchanged. Chromium must be installed. Browser mode admits only the exact reviewed demo, default synthetic fixtures, and an approved `http://127.0.0.1:PORT` origin. Select **Run investigation**.
6. Inspect the real execution evidence in **Findings**. The demo demonstrates broken object authorization, missing authentication, sensitive response fields, and missing defense-in-depth headers.
7. For ownership, authentication, or exposure, select **Propose & verify fix**. ShadowLab snapshots the trusted fixture into a disposable Git repository and creates a separate worktree. It applies a minimal fix, generates a typed regression plan, starts the patched fixture, reruns the original test, checks both owners retain access, and stops the fixture. A browser-enabled scan repeats the same UI assertions with three fresh contexts against each disposable patch; incomplete browser verification cannot pass. The explicit **Propose & verify fix** action grants verification of that disposable copy; developer approval of its diff is still required.
8. Inspect the diff and verification result. Successful patches enter `AWAITING_REVIEW`; they are never merged or deployed. Export a Markdown report from the workspace.

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

## Browser identity validation

The small demo UI provides synthetic Alice/Bob login, logout, identity checks, record access, and profile access. Authentication uses an HttpOnly, SameSite cookie in a separate incognito context per identity; tokens are never injected into browser requests or saved in browser storage. Browser tests check `/api/session` and the visible identity **before each action**, then correlate the actual network response with the displayed safe projection. Two immutable seed records live only in the disposable demo's process. No production accounts, mutable customer data, or fixture-creation endpoints are used.

The fixed scenarios exercise both owners, both cross-user directions against those same records, and anonymous controls. Sensitive-field tests retain field names with redacted values. Screenshots show only the safe UI projection. There are no HARs, raw DOM dumps, traces, or saved session states. A browser failure, timeout, unsupported Chromium setup, denied request, or incomplete control yields `INCONCLUSIVE`, even when an earlier raw HTTP test reproduced the defect.

Chromium has a dead loopback proxy; intercepted requests are fulfilled through pinned HTTPX, never `route.continue()` or Playwright's direct HTTP client. Service workers and WebSockets are blocked. The adapter permits only fixed demo UI/assets, GET endpoints, and synthetic `/api/login` and `/api/logout` POSTs. All requests (including assets, cached assets, and identity checks) consume the existing scan cap and rate limit. Redirects, unexpected cookies, query routes, and other origins are denied. JSON/HTML responses are limited to 64 KiB, individual assets to 2 MiB, and total transferred bytes to 32 MiB. Existing request and scan deadlines and cancellation remain in force. Patch verification inherits the saved request/rate/time limits and caps its total deadline at 120 seconds.

Reproduce the entire scan and three reviewed-template patch verifications with separate validation state:

```bash
.venv/bin/python scripts/validate-browser-demo.py \
  --target http://127.0.0.1:3001 --authorize --approve \
  --output .shadowlab/browser-validation/native
```

This helper explicitly authorizes only that local demo, uses a 150-request/180-second scan budget, disables dependency scanning for this focused run, and preserves the operator's database/settings/token. Set `SHADOWLAB_TEST_POSTGRES_URL` to a **disposable** database to persist its state in PostgreSQL instead. The normal CLI accepts `shadowlab scan --browser` and the scan API accepts `"browser": true`; both use saved permissions and budgets. Static scans and custom repositories cannot enable browser execution.

Findings and exported Markdown/JSON reports include browser coverage status, verdict, per-action identity checks, sanitized responses, and evidence paths. Successful patches remain `AWAITING_REVIEW` with `review_required=true`, `merged=false`. Authenticated `GET /api/v1/browser-evidence/{artifact_id}` retrieves the sanitized PNG; the finding detail links to it. See [actual commands and results](docs/validation.md).

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
- **Playwright:** `uv run playwright install chromium` or set `SHADOWLAB_CHROMIUM_PATH` to an installed Chromium. `POST /api/v1/findings/{id}/screenshot` renders sanitized HTTP evidence with scripts and networking disabled. Retrieve it through `/api/v1/evidence/{id}/screenshot`. The separate `demo_browser.py` adapter implements only the reviewed local demo identity workflow described above.
- **ZAP:** `packages/scanners/zap.py` provides an operator-only passive alert adapter for an existing trusted daemon. ZAP active scanning and automatic crawling are not wired into the graph.

## Architecture and limits

`apps/api` serves the versioned API. `apps/web` serves the Next.js landing page, guided demo and existing dashboard at `/app`. `packages/agents` owns the graph, `analyzers` source intelligence, `policies` authorization, `execution` bounded tools, `evidence` redaction, `db` persistence and migrations, and `remediation` patch verification. CLI and API share the same service and workflow.

The analyzer uses Tree-sitter for parsing and source positions, with framework-specific heuristic classification. It does not establish complete roles, middleware behavior, authorization data flows, or program-wide soundness. Findings require identifiable seeded resources and distinct owner baselines before BOLA confirmation. Exposure is based on nonempty sensitive field names; manual review still determines business impact. General HTTP tests are non-destructive GETs only; the fixed demo browser adapter also permits synthetic login/logout POSTs, with exact origins, pinned DNS, redirect rejection, private-address restrictions, and execution budgets.

Future work: VM-backed arbitrary-repository execution, generalized patch generation, generalized browser identity adapters, deeper source/data-flow adapters, stronger multi-user auth/RBAC, provider integration tests, and CI pull-request delivery. Checkpoints are persisted for inspection; interrupted scans do not automatically replay actions after restart. The API supports one worker and at most two concurrent scans.

See [architecture](docs/architecture.md), [threat model](docs/threat-model.md), [security policy](SECURITY.md), [troubleshooting](docs/troubleshooting.md), and [contributing](CONTRIBUTING.md). MIT licensed.

Product milestones and the recurring regression loop are tracked in [the improvement roadmap](docs/roadmap.md).
