# Validation evidence

The current browser increment is documented below, including exact commands, sanitized artifacts, corrections, and scope. The first section preserves the original V1 results.

## Original V1 validation

Executed in the onboarding workspace on 2026-10-09. These results describe this instance, not a published snapshot or a fresh-task restoration.

| Check | Observed result |
| --- | --- |
| Final automated suite with live native demo and dashboard | **35 passed, 1 skipped** in 49.07 seconds |
| PostgreSQL focused integration, while the test database was running | **2 passed**; document persistence survived a new connection |
| Earlier full suite with PostgreSQL enabled | **34 passed** before two additional policy/cancellation regressions were added |
| Real Semgrep integration | Unsafe SQL fixture detected at the expected source line; scanner completed |
| Next.js web and demo production builds | Both passed with Next.js **16.4.0** and React **19.3.0** |
| Frontend TypeScript and Python Ruff | Passed |
| Demo E2E | Authentication bypass, BOLA, and sensitive-field exposure reproduced; all three template patches passed original validation and positive owner regressions |
| Browser E2E | Registered a repository, started and observed its own new scan, displayed source routes and inconclusive static findings, checked browser errors and mobile overflow |
| Actual OSV-Scanner 2.6.0 | Both final npm locks scanned successfully; **0 known advisories returned** |
| Native setup/start helpers | Executed from the documented directories; API and web proxy health requests returned `ok` |
| Docker images and services | Built with TLS verification and the provided cloud CA; non-root services started successfully |
| Docker functional smoke through ingress | PostgreSQL scan completed, all four demo categories confirmed, ownership patch verified with **5 checks**, report exported, and dashboard proxy returned `ok` |
| Playwright evidence renderer | Sanitized evidence rendered with scripts and network disabled |
| Trusted demo checksums | Reviewed source manifest matched the files used for verification |

The final suite skipped only the PostgreSQL-specific test because its temporary test container had been cleaned up. PostgreSQL was independently verified earlier and in the composed functional scan. LLM unit tests used a mock provider; no hosted provider call was made. A live ZAP daemon was not tested.

The final suite included bounded compressed-response rejection and cancellation before the first task step. Earlier failures exposed scanner home-directory permissions, a report-context redaction issue, and browser synchronization ambiguities; those were corrected and affected checks passed on rerun. Dependency scanning exposed advisories in the initially chosen framework version; both applications were upgraded and their final locks rescanned successfully.

This cloud uses Docker's `vfs` storage driver, so build layers consume much more physical disk than image summaries suggest. Temporary build caches and validation containers were cleaned up after collecting results. The native application and retained `.venv`, npm dependencies, and standalone builds remain available. Docker's application network is internal; a fixed, credential-free ingress proxy publishes loopback ports.

Artifacts from real scans and reports are in the ignored `.shadowlab` directory. They contain historical scan results, not seeded dashboard telemetry. A successful patch still requires review and has not been merged. General repository patches, hostile-code VM workers, active ZAP scanning, and browser identity testing are not implemented in this V1.

Reusable `install_script` and `start_skill` contents, plus the `api.osv.dev` network requirement, were saved to the environment draft. Saving does not publish it. The user must review/save the settings and publish the environment; restoration in a new task has not been tested.

## Browser identity increment (2026-10-09)

The original checkout was on unborn branch `work`, with all 95 V1 files untracked. Baseline commit `7544bd6` preserved them before creating `feature/browser-identity-validation`. No checkout reset/replacement, push, merge, external deployment, release publication, credential rotation, or managed network permission change was performed. The earlier V1 results above remain historical evidence.

This increment adds only the checksum-reviewed demo UI/session adapter, fixed browser cases, integration into findings/patches/reports, and their regression coverage. It enables no arbitrary repository execution. Compose is a trusted development runtime, not a verified VM-grade boundary. Each patch uses its own disposable worktree; final developer approval stays explicit.

### Final results

| Check | Passed | Failed | Skipped / blocked |
| --- | --- | --- | --- |
| Final full pytest suite, with native demo/dashboard and PostgreSQL | **60** in **193.76 s** | **0** | **0 / 0** |
| Python Ruff, frontend TypeScript, shell syntax, Git whitespace | All passed | 0 | 0 |
| Next.js web and demo production builds | Both passed | 0 final failures | 0 |
| Native complete scan and three browser patches | All passed | 0 | 0 |
| Compose current-source/PostgreSQL scan and three browser patches | All passed | 0 | 0 |
| Real native API finding reads / authenticated PNGs / redacted report | All passed | 0 | 0 |

The original skipped test was `test_postgres_persistence_if_configured`: its temporary PostgreSQL instance had been removed. This increment provided a temporary database and `SHADOWLAB_TEST_POSTGRES_URL`, so that test **passed** and the complete suite had **no skips**. The browser/dashboard E2E prerequisites were supplied too. Expected negative cases assert blocked/unsupported/timeout/inconclusive outcomes; they count as passing regression tests, not blocked work. No requested check remains blocked.

After validation, the extra native fixture/API, temporary PostgreSQL container, and `shadowlab-browser-check` services/volumes were removed after collecting sanitized evidence. The validation images/cache were also cleaned to restore space; original V1 data and native dependencies/builds were preserved. The main native application was restarted with the final source. Re-running PostgreSQL coverage requires starting the documented temporary database again; omitting its environment variable will skip that optional test again.

### Real observed cases

Both native SQLite and Compose/PostgreSQL runs reproduced the baseline and passed all three disposable template verifications:

| Case | Vulnerable UI/network observations | Patched observations | Combined patch checks |
| --- | --- | --- | --- |
| Authentication bypass | Alice **200** and anonymous **200**, both identifying `alice-record`; Bob authenticated control **200** | Alice **200**, anonymous **401**, Bob authenticated control **200** | **7 passed** |
| Object authorization | Alice→Alice **200**, Bob→Bob **200**, Bob→Alice **200**, Alice→Bob **200**, anonymous→Alice **401** | Owner actions **200**, both cross-user actions **403**, anonymous **401** | **10 passed** |
| Sensitive fields | Alice/Bob own profiles **200**, correct profile IDs, `apiKey` and `passwordHash` nonempty with values redacted; anonymous **401** | Both own profiles **200**, sensitive fields absent; anonymous **401** | **6 passed** |

There are **11 protected UI assertions** per complete browser baseline, each preceded by a fresh server identity probe and checked against the rendered response projection. An isolated baseline consumed **50 requests**, including assets/session checks, within its 150-request budget. The patches repeat identical scenario labels and assertions. Combined patch counts include the original HTTP test plus two positive owner checks, and exclude setup/assets and identity probes.

The authentication template enforces login and permits both authenticated accounts to read `/api/unprotected`'s shared synthetic fixture. Ownership denial is checked on `/api/records/[id]` using the ownership template. Each template fixes its own case in a separate copy; these results do not establish app-wide authorization or a combined patch. Profile testing supports only the current account endpoint, not arbitrary profile-selector workflows.

### Prerequisites and exact native commands

Run from `/workspace/shadow-lab`. Python 3.12+, locked uv dependencies, Node 22+, installed demo/web npm dependencies, Linux process groups, Git, and Chromium are required. This workspace used `/usr/bin/chromium`; `SHADOWLAB_CHROMIUM_PATH` can select it explicitly. CI installs Playwright Chromium with `uv run playwright install --with-deps chromium`. Start only the authorized demo and dashboard. No real account or credential is required.

```bash
bash scripts/setup.sh
bash scripts/start.sh
.venv/bin/ruff check packages apps/api tests scripts
npm --prefix apps/web run typecheck
npm --prefix apps/web run build -- --webpack
npm --prefix examples/vulnerable-nextjs run build -- --webpack
.venv/bin/python scripts/validate-browser-demo.py \
  --target http://127.0.0.1:3001 --authorize --approve \
  --output .shadowlab/browser-validation/native-final
```

Setup/install and startup prerequisites were retained from the V1 workspace. Both production builds were actually rerun in this increment. Chromium reached the demo only through the fixed intercepting adapter, with direct browser connections blocked by a dead loopback proxy. Browser scan budgets explicitly used 150 requests, 5 requests/second, 10-second request timeouts, and a 180-second scan deadline. Patch verification inherited those caps and used a tighter 120-second total build/readiness/HTTP/browser deadline. Default operator settings were preserved; the helper wrote separate run state.

Start a temporary PostgreSQL instance using the existing synthetic lab database credential:

```bash
docker run -d --name shadowlab-browser-pg --user postgres \
  -e POSTGRES_USER=shadowlab -e POSTGRES_PASSWORD=shadowlab-local \
  -e POSTGRES_DB=shadowlab -p 127.0.0.1:55432:5432 postgres:17-alpine
SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001 \
SHADOWLAB_TEST_DASHBOARD=http://127.0.0.1:3000 \
SHADOWLAB_TEST_POSTGRES_URL=postgresql+psycopg://shadowlab:shadowlab-local@127.0.0.1:55432/shadowlab \
  .venv/bin/pytest -q
```

### Compose commands and scope

Images for `api`, `demo`, `web`, and `ingress` were built with the optional managed-cloud public CA described in [troubleshooting](troubleshooting.md), with TLS verification enabled. The API image now includes system Chromium and combines its large dependencies in one layer to fit this cloud's `vfs` driver. API `init: true` reaps browser subprocesses. Runtime checks retained non-root UID 10001, read-only roots, dropped capabilities, no-new-privileges, internal lab networking, **1 GiB memory / 256 process / 2 CPU** API caps, and no Docker socket or host credentials.

Validation used project `shadowlab-browser-check` and a temporary port override: loopback host ports **3300/8800/3301** mapped to web/API/demo **3000/8000/3001**. To test the latest cancellation/assertion changes without another large image layer, the current `packages`, `apps/api`, and `scripts` were copied to `/tmp/shadowlab-browser-current` with ordinary source-read permissions, then mounted read-only at their matching `/app` locations using `/tmp/shadowlab-browser-source.yml`. The executable source copies matched the checkout; these are trusted source mounts, with no credentials or unrelated host directories. The image build and this current-source functional test are distinct checks.

The Compose calls reused the existing operator API token in process environment, without printing or rotating it. Exact wrapper used for each command:

```python
import os
from pathlib import Path
os.environ['SHADOWLAB_API_TOKEN'] = Path('.shadowlab/api-token').read_text().strip()
os.environ['BUILDX_CONFIG'] = '/workspace/.cache/buildx'
os.execvp('docker', ['docker', 'compose', '-p', 'shadowlab-browser-check',
    '-f', 'docker-compose.yml', '-f', '/tmp/shadowlab-browser-ca.yml',
    'build', 'api'])
```

Repeat its `build` arguments with `demo web ingress`; then use the same wrapper with these exact arguments for startup and the actual browser/patch run:

```text
compose -p shadowlab-browser-check -f docker-compose.yml
  -f /tmp/shadowlab-browser-ports.yml -f /tmp/shadowlab-browser-source.yml
  up -d --no-build
compose -p shadowlab-browser-check -f docker-compose.yml
  -f /tmp/shadowlab-browser-ports.yml -f /tmp/shadowlab-browser-source.yml
  exec -T api sh -c 'SHADOWLAB_TEST_POSTGRES_URL="$SHADOWLAB_DATABASE_URL" /app/.venv/bin/python scripts/validate-browser-demo.py --target http://127.0.0.1:3001 --authorize --approve --output /data/browser-validation'
```

The operator target remains the same authorized local demo in the shared loopback namespace. PostgreSQL persisted the real scan/findings/patches. The API and dashboard proxy both returned healthy responses through ingress. The Docker run confirmed all three cases and passed all three patched browser workflows within the existing resource caps. OSV/provider/ZAP traffic was excluded from this focused script; no wider scanning or external provider access was added.

### Sanitized evidence and review paths

- Native scan **`ca25be22-18aa-443d-9e5c-50ad45205d70`**: `.shadowlab/browser-validation/native-final/report.json`, `report.md`, and `results.json`.
- Native per-case JSON receipts and safe UI PNGs: `.shadowlab/browser-validation/native-final/browser-evidence/`.
- Native reviewable disposable patches: `.shadowlab/browser-validation/native-final/patches/*/worktree/`; each report names the exact worktree. Each is `AWAITING_REVIEW`, `review_required=true`, `merged=false`.
- Compose/PostgreSQL scan **`0baea27a-b7a4-4ad3-babd-c65244fbdfdc`**: `.shadowlab/browser-validation/docker-report.json`, `docker-report.md`, `docker-results.json`, and `docker-guard-evidence/` copied from `/data/browser-validation-guard`.
- API retrieval checks saved `.shadowlab/browser-validation/api-authentication.png`, `api-bola.png`, and `api-exposure.png`. A temporary native API on port 8012 used the validation DB/data directory and reused the existing API token. Three real finding reads and authenticated PNG retrievals passed; unauthenticated retrieval returned **401** and JSON reports excluded synthetic credentials and sensitive values. Visual inspection of the profile PNG showed only identity/status/field names, with no sensitive values.
- Logs: `.shadowlab/browser-validation/full-suite.log`, `identity-tests.log`, `demo-tests.log`, `event-cancellation.log`, `retry-test.log`, `frontend-build.log`, `docker-api-build.log`, `docker-app-build.log`, `native-final.log`, and `docker-browser-run.log`, and `docker-browser-final.log`, and `docker-final-guard.log`.

No HAR, browser trace, raw DOM, storage state, cookie header, bearer credential, or sensitive response value was saved. Artifact directories are ignored by Git; source, tests, docs, and the trusted fixture manifest form the reviewable feature patch. The earlier failed native run remains historical evidence in `native/`; `native-final/` is the complete successful run.

### Failures found and corrected

The initial route callback accepted Playwright's optional second argument as its identity default; the runner now binds each context using a single-argument handler. Disposable production builds initially inherited `NODE_ENV=development`, which caused Next prerender failure; browser verification now builds/starts in production with a minimal environment and the trusted Node directory in `PATH`. A full build exhausted disk under Docker `vfs`, also interrupting one frontend build; the API layer structure was reduced, only this validation's caches/image were cleared, and both affected builds passed on rerun. A timeout-retry assertion initially raced React rendering under concurrent builds; it now waits for the exact network response projection and the live-browser test uses a declared 10-second request/UI deadline. Event-only cancellation was wrapped by LangGraph as `NodeCancelledError`; the graph now preserves the operator cancellation verdict while still treating unrelated node cancellation as failure. Focused regressions passed after each correction.

Intentional negative tests verify unsupported Chromium setup, exhausted budgets, compressed/oversized responses, timeout failure, stale identities, and out-of-scope redirects. Their expected outcomes are **blocked/timeout/unsupported and INCONCLUSIVE**, with cleanup, rather than a finding or passed patch. A teardown error also invalidates completed browser results and keeps a patch unverified; a targeted fault-injection regression checks that cleanup failure cannot pass. Scan deadline failure now marks active browser findings inconclusive instead of leaving them testing. Native and Compose browser contexts and patched fixture processes terminate after their workflows; patch worktrees and sanitized receipts remain for review.

The scans were executed with the feature increment uncommitted, so their source commit field names the preserved baseline. The reviewed fixture checksums and final feature-branch diff identify the tested source changes.
