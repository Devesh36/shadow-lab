# Validation evidence

The browser identity and guided REPL/distribution increments are documented below, including exact commands, sanitized artifacts, corrections, and scope. The first section preserves the original V1 results.

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


## Guided REPL, installation and landing page increment (2026-10-09)

The implemented V1 and browser validation remain on `feature/browser-identity-validation`. The dashboard moved intact to `/app`; `/` is a Next.js landing page and `/demo` starts a guided investigation. The new `shadow repl` (`shadow Repl` also accepted) menu launches a checksum-reviewed, explicitly enumerated package bundle in private local state. It never runs a repository from the caller's working directory. The original `shadowlab` commands remain available.

Choosing Demo or selecting Start demo explicitly authorizes only the bundled loopback synthetic fixture. The authenticated demo API rejects missing/false approval, unexpected request fields and non-loopback origins. Each demo scan uses ephemeral settings with **150 requests, 5 requests/second, 10-second request deadline and 180-second scan deadline**. Saved operator settings remain unchanged; LLM and dependency-network calls are disabled for this guided run. Chromium is optional unless browser validation is selected. Existing policy, redaction, browser identity separation, redirect rejection and patch-review restrictions remain in force. Patch verification uses the same scoped demo limits, with its existing 120-second overall cap.

The launcher needs macOS/Linux, Python 3.12+, Node.js 22+, npm and Git. First preparation fetches frozen npm dependencies and production builds both apps; subsequent launches reuse that content-addressed bundle. Each launch gets three distinct IPv4 loopback ports, a fresh API token with mode 0600 and separate private SQLite state. Child services do not inherit the operator's database URL, API token, LLM key or cloud credentials. Managed proxy/CA settings are retained for dependency installation. Cleanup stops the owned service groups; the API lifespan now awaits cancelled patch tasks so their separate disposable process groups finish cleanup before the console reports completion. Reports and worktrees remain for review.

### Commands and observed results

All commands below ran in `/workspace/shadow-lab`, except the installed-package helper deliberately launches the console from a fresh temporary directory. `UV_CACHE_DIR=/workspace/.cache/uv` was set for uv commands. Evidence and dependency caches are ignored by Git.

```bash
uv sync --locked
.venv/bin/python scripts/update-bundle.py
.venv/bin/ruff check packages apps/api tests scripts
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack
npm --prefix apps/web run typecheck
uv build --wheel --out-dir .shadowlab/distribution
.venv/bin/python scripts/check-bundle.py .shadowlab/distribution/shadowlab-0.1.0-py3-none-any.whl

UV_TOOL_DIR=/workspace/shadow-lab/.shadowlab/uv-tools \
UV_TOOL_BIN_DIR=/workspace/shadow-lab/.shadowlab/uv-bin \
  uv tool install --reinstall --python 3.12 .shadowlab/distribution/shadowlab-0.1.0-py3-none-any.whl
SHADOWLAB_HOME=/workspace/shadow-lab/.shadowlab/repl-final \
  .venv/bin/python scripts/smoke-installed.py .shadowlab/uv-bin/shadow
SHADOWLAB_HOME=/workspace/shadow-lab/.shadowlab/repl-final \
  .venv/bin/python scripts/validate-repl-cancel.py .shadowlab/uv-bin/shadow
```

The smoke helper drives `demo`, `report`, `quit` through the installed CLI. It requires actual completed investigations and confirmed authentication/BOLA/exposure findings, checks report redaction, checks that caller state was untouched, and verifies **all three launched service ports are closed**. The cancellation helper uses pipes and sends SIGINT directly to the console after observing a live Node process in its disposable patch worktree; it requires the cancelled message, terminated patch process and all three service ports closed. Browser installation was also exercised by typing `demo browser` through the wheel-installed REPL with `SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium`.

For the full suite, the original native services were rebuilt/restarted with `bash scripts/start.sh`, and a disposable PostgreSQL instance was supplied:

```bash
docker run -d --name shadowlab-repl-pg --user postgres \
  -e POSTGRES_USER=shadowlab -e POSTGRES_PASSWORD=shadowlab-local \
  -e POSTGRES_DB=shadowlab -p 127.0.0.1:55432:5432 postgres:17-alpine
SHADOWLAB_TEST_POSTGRES_URL=postgresql+psycopg://shadowlab:shadowlab-local@127.0.0.1:55432/shadowlab \
SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001 \
SHADOWLAB_TEST_DASHBOARD=http://127.0.0.1:3000 \
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/pytest -q
```

The final suite passed **72 tests, 0 failed, 0 skipped** in **166.44 seconds** after the shutdown regression was added. Before that regression, it passed **71 tests, zero skipped**. The initial no-PostgreSQL unit/API run had **60 passed, 1 skipped, 9 deselected**; the skipped test was `test_postgres_persistence_if_configured`, the same optional database coverage described in the earlier increments. It passed once the disposable PostgreSQL service was supplied. Nothing was relabeled or silently removed to eliminate skips.

The existing full browser E2E cases rerun real UI actions for anonymous, Alice and Bob, then repeat identical assertions against all three demo patch templates. New tests cover installed-console startup outside the checkout, package isolation, stripping operator credentials, setup failure and interruption cleanup, stop/restart, EOF, active-scan cancellation, API approval/scope/settings preservation, pending patch cleanup, landing install tabs/copy, responsive layouts, real guided scan navigation, and backend-unavailable feedback. The existing context separation, logout/relogin, repeated browser runs, budget/deadline failures, unsupported Chromium and out-of-scope redirect regressions remain included.

### Docker and Homebrew checks

The managed local Docker daemon was checked with:

```bash
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
  -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock info --format '{{.ServerVersion}} {{.Driver}}'
BUILDX_CONFIG=/workspace/.cache/buildx docker build \
  --secret id=custom-ca,src=/usr/local/share/ca-certificates/environment-proxy-ca.crt \
  -f infrastructure/docker/web.Dockerfile -t shadowlab-landing-check .
docker run -d --name shadowlab-landing-web --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 \
  --memory 1g --cpus 2 --tmpfs /tmp:rw,nosuid,size=128m shadowlab-landing-check
docker exec shadowlab-landing-web node -e 'async function main(){for(const p of ["/","/demo","/app"]){const r=await fetch("http://127.0.0.1:3000"+p);const body=await r.text();console.log(p,r.status,body.includes("ShadowLab"));if(!r.ok||!body.includes("ShadowLab"))throw new Error("route failed");}}main().catch(e=>{console.error(e.name);process.exitCode=1})'
```

The daemon was Docker **28.4.0**, `vfs`. The web image built successfully with TLS verification enabled; the updated npm build step mounts the optional public CA only during installation, without retaining it in the image. The non-root `node` runtime had read-only root, no network egress, all capabilities dropped, no-new-privileges, 1 GiB memory, 256 processes and 2 CPUs. All three routes returned **200** with ShadowLab content. `docker compose config --quiet` also passed, with the existing token read into process environment without printing or rotating it. The prior complete Compose/API/PostgreSQL browser/patch results remain above; that entire stack was not rebuilt in this increment. Compose is still a trusted development runtime, **not VM-grade isolation for untrusted repositories**.

Homebrew is not installed in this Linux workspace. Ruby syntax was checked in a restricted temporary container after copying the public formula to `/tmp/shadowlab-formula-check/shadowlab.rb` with read permissions:

```bash
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 32 --memory 128m \
  --mount type=bind,src=/tmp/shadowlab-formula-check/shadowlab.rb,dst=/formula.rb,readonly \
  ruby:3.4-alpine ruby -c /formula.rb
```

Result: **Syntax OK**. The first direct workspace bind was unreadable to the nested container; retry used the readable temporary copy. Native `brew tap`, install, test and upgrade remain **not verified here**. `.github/workflows/homebrew.yml` adds a macOS HEAD installation/test job; configuration is not proof of a completed run. The unauthenticated GitHub repository page returned HTTP 200. No stable Homebrew release, PyPI publication, release publication or external site deployment was performed. The current repository acts as a custom tap; uv installs from its explicitly named feature branch.

### Evidence, corrections and limits

- `.shadowlab/repl-suite.log`: initial full run **69 passed, 1 failed**. The landing test read a response body after a full navigation; Chromium had discarded it. The corrected test correlates the resulting scan URL with an authenticated scan read instead. The focused rerun passed.
- `.shadowlab/repl-suite-final.log`: **71 passed, zero skipped** before adding the pending-patch shutdown regression.
- `.shadowlab/repl-suite-current.log`: final suite after the shutdown change, **72 passed, 0 failed, 0 skipped**.
- `.shadowlab/repl-final.log` and `repl-smoke-current.log`: real installed-package transcripts and service-port/redaction assertions. Latest smoke scan `74994caa-28bb-4bc4-a4ba-99900dc0da2a` is saved under `.shadowlab/repl-final/runs/4d5c3878ebf44296a926c1630f1623dd/`.
- `.shadowlab/repl-final/runs/b8744e5e7c324b1f9a4c526d54bba9d5/report-e281c151-b74c-4d8c-9a80-c31412c62852.md`: installed-wheel investigation with confirmed authentication/BOLA/exposure and header checks.
- `.shadowlab/repl-validation/runs/e31671ccb88344239c0df4f37c71cd7b/report-280384fe-5f5a-4930-a585-a47eeef90a3c.md`: first wheel-installed HTTP scan plus explicitly selected authentication patch. Patch verification passed **4 checks**; `review_required=true`, `merged=false`.
- `.shadowlab/repl-validation/runs/88680a2f4a464532ae434afe4d8a9005/report-f69e7101-8a8c-4605-a47a-8ea39932f1ea.md`: installed REPL browser investigation. Authentication/BOLA/exposure each completed with **3/5/3 UI assertions**, all confirmed; sanitized receipts and screenshots are in this run's `browser-evidence/`.
- `.shadowlab/repl-cancel.log`: initial cancellation probe failed because its cleanup assertion was not satisfied at the instant it checked; subsequent inspection found no remaining patch process. The probe now requires an actual Node patch process, rather than incidental Git setup, and the API explicitly awaits pending patch task cleanup.
- `.shadowlab/repl-patch-current.log`: latest wheel installed outside the checkout, actual demo scan plus authentication patch **passed 4 checks**, awaiting review. Its sanitized report is `.shadowlab/repl-final/runs/b48d10a68c514a039a914597b1ba049f/report-9f6eb3ca-353e-4689-982c-be0c6e931e85.md`.
- `.shadowlab/repl-cancel-final.log`: actual live patch cancellation **passed**, with **1 observed patch application process terminated and 3 local service ports closed**. Its private run is `.shadowlab/repl-final/runs/605d79baacb24b2782a50639b1e4bdcc/`. No cancelled experiment is reported as a verified patch.
- `.shadowlab/landing-desktop.png`, `landing-mobile.png`: actual browser screenshots, visually inspected. The terminal on the landing page is explicitly labeled an illustration.
- `.shadowlab/landing-docker-build.log`: current web image build; `.shadowlab/landing-runtime-final.log`: current native service startup.
- `.shadowlab/distribution/shadowlab-0.1.0-py3-none-any.whl`: tested distribution. All **67** enumerated runtime assets were present; no `.env`, private state, Git data, bytecode, `node_modules` or `.next` was included.

Only sanitized reports/receipts/screenshots are shareable evidence. Private run directories also contain mode-0600 API tokens and operational databases; never distribute a whole run directory. No cookie state, bearer token or sensitive response value is printed in the console or exported report. Git ignores all validation state. Optional missing tools and incomplete browser checks remain visible. macOS launcher/Homebrew installation, hosted provider calls and a publicly deployed landing page were not validated in this workspace. Arbitrary untrusted code execution, generalized remediation and wider scanning remain outside this increment.


### Published branch installation verification

Implementation commit `594f577` was pushed to `origin/feature/browser-identity-validation` under the user's earlier explicit push authorization. The remote ref matched the local commit. After the push, the advertised GitHub installation was actually rerun:

```bash
UV_CACHE_DIR=/workspace/.cache/uv \
UV_TOOL_DIR=/workspace/shadow-lab/.shadowlab/uv-tools \
UV_TOOL_BIN_DIR=/workspace/shadow-lab/.shadowlab/uv-bin \
  uv tool install --reinstall --python 3.12 \
  'git+https://github.com/Devesh36/shadow-lab.git@feature/browser-identity-validation'
SHADOWLAB_HOME=/workspace/shadow-lab/.shadowlab/repl-final \
  .venv/bin/python scripts/smoke-installed.py .shadowlab/uv-bin/shadow
```

Both installation and the real outside-checkout investigation **passed**. The remote-installed scan was `64e284d0-46aa-4c93-8878-15e806d5a451`, with confirmed authentication/BOLA/exposure/header findings and a sanitized report at `.shadowlab/repl-final/runs/b25e7f245d8c4322891fc8930f1bd512/report-64e284d0-46aa-4c93-8878-15e806d5a451.md`. Its three service ports were closed after exit. Transcripts: `.shadowlab/repl-github-install.log` and `.shadowlab/repl-github-smoke.log`.

`gh run list --repo Devesh36/shadow-lab --branch feature/browser-identity-validation --limit 3 --json databaseId,workflowName,status,conclusion,url` was **blocked with HTTP 403**. Remote CI status, including the macOS Homebrew job, could not be observed through this API; no network/security permissions were broadened. The native 72-test result and actual GitHub-installed demo are independently observed results.

Temporary web and PostgreSQL validation containers were removed after their checks. The native product services remain available on loopback: `/`, `/demo`, `/app`, and the dashboard proxy health route each returned **200** on port 3000. No release, package registry publication, merge or external deployment was performed.

## Landing-only Vercel increment — 2026-10-09

The user narrowed hosting to **the landing page only**. The deployment is the self-contained `apps/landing` Next.js static export. Vercel Root Directory is **`apps/landing`**, build command **`npm run build`**. **Correction on 2026-10-10: leave the Vercel Output Directory override disabled**; the original `out` override below caused a provider packaging failure despite the local static build passing. `out` remains the export directory for local/manual static hosting. No application environment variables, backend service, bindings, database, dashboard or scanner are part of this deployment. Demo links go to local installation instructions. Existing `apps/web`, `apps/api`, packages, trusted demo and local launchers have no source diff in this increment.

The proposed multi-service adapter/configuration and its tests were removed from the active patch after the scope correction. All of that provisional work was first archived and byte-verified under ignored `.shadowlab/vercel-proposal-backup/`, including the exact reversible tracked patch and 19 source/config files. Automatic approval review initially rejected an unbacked cleanup because it might discard uncommitted work; inspection and a verified archive resolved that concern, and the reversible cleanup succeeded. The checkout/branch was never reset or replaced. Its generated Python service environment was moved into the same private archive. Do not distribute that entire directory.

### Actual commands and prerequisites

The existing environment had Node.js **24.19.0**, npm **11.9.0**, Python **3.12**, project `.venv`, uv, system Chromium **`/usr/bin/chromium`**, and Docker **28.4.0**. A clean site installation/build needs only Node.js 22+ and npm; the browser helper additionally needs the project Python dependencies and compatible Chromium. The new app has a committed npm lockfile and its own minimal Next.js/React/icon dependencies, without Python or dashboard dependencies.

```bash
npm_config_cache=/workspace/.cache/npm npm --prefix apps/landing install --no-audit --no-fund
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
python3 -m http.server 3100 --bind 127.0.0.1 --directory apps/landing/out
# In another terminal:
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/validate-landing.py
npm --prefix apps/web run typecheck
.venv/bin/ruff check packages apps/api tests scripts
git diff --check
UV_CACHE_DIR=/workspace/.cache/uv uv build --wheel --out-dir .shadowlab/distribution
.venv/bin/python scripts/check-bundle.py .shadowlab/distribution/shadowlab-0.1.0-py3-none-any.whl
```

The first command generated the site lockfile. Vercel and the added CI check install that committed lock with `npm ci`; build and typecheck are added to the existing CI workflow. A successful local run is not evidence that remote CI ran.

The preserved native services were already running through `bash scripts/start.sh`: API 8000, website/dashboard 3000, trusted demo 3001. PostgreSQL was a disposable container created for this validation, using only synthetic credentials:

```bash
docker run -d --name shadowlab-vercel-pg --user postgres \
  -e POSTGRES_USER=shadowlab -e POSTGRES_PASSWORD=shadowlab-local \
  -e POSTGRES_DB=shadowlab -p 127.0.0.1:55433:5432 postgres:17-alpine
docker exec shadowlab-vercel-pg pg_isready -U shadowlab
SHADOWLAB_TEST_POSTGRES_URL=postgresql+psycopg://shadowlab:shadowlab-local@127.0.0.1:55433/shadowlab \
SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001 \
SHADOWLAB_TEST_DASHBOARD=http://127.0.0.1:3000 \
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/pytest -q
```

The final preserved application suite passed **72 tests, 0 failed, 0 skipped in 171.77 seconds**. This includes real UI identity tests and all three disposable patch verifications. The existing optional `test_postgres_persistence_if_configured` passed with the disposable PostgreSQL instance; its prerequisite/skip logic is unchanged. Nothing was removed or relabeled to obtain zero skips. The transient hosted PostgreSQL test belonged to the discarded multi-service proposal and is not counted as shipped coverage.

`docker compose config --quiet` passed with the existing local API token read only into the child process environment, without printing or changing it. The daemon and PostgreSQL readiness checks passed. No new Docker images or full Compose stack were built for this static website. Docker remains a trusted development runtime, not VM-grade isolation for arbitrary untrusted repositories. Repository execution restrictions, target scope, scan budgets and cancellation policies are unchanged.

### Results and sanitized evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Landing production build | Passed; only `/` and framework not-found/error support routes | `.shadowlab/vercel-validation/landing-build-final.log`; `apps/landing/.next/server/app-paths-manifest.json` |
| Static output contents | Passed; about 1.1 MiB, HTML/CSS/JS; no application API routes or runtime functions | `apps/landing/out/` (ignored generated artifact) |
| Landing TypeScript | Passed | `.shadowlab/vercel-validation/landing-typecheck-final.log` |
| Real Chromium website check | Passed **6 checks**: `/` 200; `/app`, `/demo`, `/api/v1/health`, `/api/v1/scans` 404; tabs/clipboard/install CTA/mobile/CSP assertions | `.shadowlab/vercel-validation/static-browser-csp.log`, `static-checks.json` |
| Responsive screenshots | Passed and visually inspected; no credentials, findings or backend data | `.shadowlab/vercel-validation/static-desktop.png`, `static-mobile.png` |
| Browser production policy | Passed with headers from the committed Vercel config applied locally; no eval, page errors, external page requests or runtime API calls | `scripts/validate-landing.py`; `static-checks.json` |
| Preserved application suite | **72 passed, 0 failed, 0 skipped** | `.shadowlab/vercel-validation/preserved-suite.log` |
| Preserved frontend TypeScript | Passed | `.shadowlab/vercel-validation/preserved-web-typecheck.log` |
| Python lint / diff whitespace | Passed | Commands above |
| Wheel packaging | Passed, **67 reviewed runtime assets**, no private/generated directories | `.shadowlab/vercel-validation/wheel-build.log`, `wheel-check.log` |
| Original native UI/API availability | `/`, `/demo`, `/app`, `/api/v1/health` on port 3000 all **200** | Loopback HTTP checks; full suite |
| Vercel account / cloud deployment | **Unavailable: CLI logged out; no deployment performed** | `.shadowlab/vercel-validation/vercel-account.log` |

The browser helper asserts only this fixed loopback origin, rejects other page requests and follows no redirects when fetching static assets. It checks both install tabs, copies the install command to the clipboard, follows the demo CTA to `#install`, checks the mobile body width, and asserts there are no `/api/` calls or page errors. It creates no login state, credentials, database or scan. The configured Vercel CSP/security headers are applied locally to test browser behavior; this does **not** establish that the provider delivered them. Provider-side delivery, project import/settings, cloud build, deployed URL and actual availability still need verification after deployment.

### Failures, corrections and blocked checks

- The initial static browser probe failed its mobile overflow assertion. Extracting the landing styles omitted the original shared `pre` wrapping rule. Restoring that existing rule fixed long installation commands; the rebuilt export and complete final browser probe passed. Initial log: `.shadowlab/vercel-validation/static-browser.log`; final: `static-browser-csp.log`.
- Before scope was narrowed, provisional `vercel dev --local` detected FastAPI/Next.js, passed bound health/protected request checks, and exposed development CSP/hydration timing problems. One initial focused database run failed because PostgreSQL had not become ready; its readiness-gated rerun passed. Those provisional dev/test results are historical diagnostics, not evidence of the final landing-only deployment. Their source and proposed fixes were archived and are absent from the shipped patch.
- Vercel CLI **63.1.0** account check used `XDG_DATA_HOME=/workspace/.cache/vercel-data`, `XDG_CONFIG_HOME=/workspace/.cache/vercel-config`, `XDG_CACHE_HOME=/workspace/.cache/vercel-cache`, `VERCEL_TELEMETRY_DISABLED=1`, then `/workspace/.cache/shadowlab-vercel-cli/node_modules/.bin/vercel whoami`. It returned **Logged out**. No credentials were requested in chat, changed, generated for hosting, or written to Vercel.
- The managed network denied reads of `https://vercel.com/docs/services` and `https://openapi.vercel.sh/vercel.json` with HTTP **403** during the provisional services investigation. CLI update checks also reported failure to fetch npm dist-tags. No network/security permissions were broadened. An authenticated provider deployment/build, hosted header delivery and remote CI were **not run**.

The native product remains available on loopback port 3000 and the static site preview on loopback port 3100. No API/data service, database provisioning, deployment credential change, merge, release, registry publication or arbitrary repository execution is included in this increment. The temporary PostgreSQL validation container is removed after the suite; existing native services and saved validation evidence remain.

## Vercel missing-manifest correction — 2026-10-10

The actual deployment compiled, passed TypeScript and generated its static pages, then failed with:

```text
The file "/vercel/path0/apps/landing/out/routes-manifest.json" couldn't be found.
```

The original `outputDirectory: "out"` setting and associated deployment instructions were incorrect for Vercel's **Next.js framework builder**. `out` is the standalone static export, while Next.js build metadata lives under `.next`. The original local export/browser checks did not exercise provider packaging, so they missed this defect. The fix removes the override, updates README/setup instructions, and keeps `output: 'export'`. An existing project's saved Output Directory override must also be disabled in **Vercel Project Settings → Build and Deployment** before redeploying. Root Directory remains `apps/landing`; no backend, bindings or application secrets are added.

### Provider reproduction and verification

The installed Vercel CLI **63.1.0** includes `@vercel/next` **22.0.0**. Its actual builder was called directly with the Vercel Next.js adapter enabled, in disposable copies containing only the reviewed landing sources and installed dependencies. Installation was skipped because locked packages were already installed. This requires no Vercel account, project linking, deployment or network-permission changes.

The original configuration was first compiled through this builder and reproduced **`NEXT_NO_ROUTES_MANIFEST`**, referencing `out/routes-manifest.json`, after successful compilation/static generation. The corrected configuration then passed the same builder and produced **Build Output v3 at `.next/output`**, with `static/index.html` and **zero runtime functions**. The check also applied the old `out` override to the successful build and required the exact same missing-manifest error. Generated scratch copies are removed after the regression helper finishes; only sanitized logs and metadata are retained.

```bash
npm_config_cache=/workspace/.cache/npm NODE_USE_ENV_PROXY=1 \
  node scripts/check-landing-vercel.cjs \
  /workspace/.cache/shadowlab-vercel-cli/node_modules/@vercel/next
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
# With the existing loopback static preview on port 3100:
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/validate-landing.py
.venv/bin/ruff check packages apps/api tests scripts
git diff --check
```

A new `landing-packaging` CI job installs the pinned CLI into the runner's temporary directory and runs this exact builder regression with Node.js 22. It does not deploy anything. Other CI jobs and the local investigation engine remain unchanged. Remote CI execution is not asserted by adding the job.

| Check | Result | Sanitized evidence |
| --- | --- | --- |
| Original override, real provider builder | Reproduced reported failure after successful compile | `.shadowlab/vercel-manifest-fix/broken.log`, `reproduced.json` |
| Corrected config, real provider builder | Passed; v3 static output, zero runtime functions | `.shadowlab/vercel-manifest-fix/fixed-builder.log`, `packaging-check.json` |
| Former override against successful build | Expected missing-manifest failure asserted by regression | `fixed-builder.log` |
| Plain static production build | Passed | `.shadowlab/vercel-manifest-fix/landing-build.log` |
| Landing TypeScript | Passed | `.shadowlab/vercel-manifest-fix/typecheck.log` |
| Real Chromium static site / configured production CSP | Passed six request/browser checks; tabs, clipboard, local-install CTA and mobile layout; application routes remain 404 | `.shadowlab/vercel-manifest-fix/browser.log`; `.shadowlab/vercel-validation/static-checks.json`, `static-desktop.png`, `static-mobile.png` |
| Python lint / diff whitespace | Passed | Commands above |
| Full investigation suite | Not repeated for this config/docs/CI-only fix; preceding increment passed 72 with zero skips | Prior `preserved-suite.log` above |
| Cloud project settings / redeployment | Not inspected or performed; account access is unavailable | User must clear any saved override and redeploy |

The provider builder check now covers the packaging stage that plain `next build` missed. It is still a local invocation of provider code, not proof of successful cloud redeployment, current project settings or delivered hosted headers. No credentials, permissions, scanner policy, database, local API or dashboard source changed.

## Public documentation and terminal walkthrough — 2026-10-10

The static landing site now has a separate `/docs/` page, linked from its navigation and installation box. It documents uv/Homebrew installation and updates, prerequisites, `shadow repl` / `shadow Repl`, the synthetic demo, explicit disposable patch approval, reports and cleanup, optional Chromium validation, and source-only analysis in a user's Next.js project. The existing API, dashboard, CLI, demo, execution policies and credentials are unchanged. `trailingSlash: true` exports `docs/index.html` for direct navigation/reload on ordinary static hosts. Vercel remains landing-only, with the Output Directory override disabled and no application bindings or secrets.

### Actual terminal captures

A fresh GitHub-main uv installation was made into isolated tool directories. The installed source was **`2392b1900ef2b48d33fc547f83a6b23ca77eee24`**. A private PTY driver launched that installed `shadow` from a disposable working directory, with a minimal child environment, `SHADOWLAB_NO_OPEN=1`, a separate `SHADOWLAB_HOME`, and compatible system Chromium. It sent these fixed console commands and waited for each real prompt/result:

```text
shadow repl
shadow> doctor
shadow> help
shadow> demo
shadow> findings
shadow> fix 1
shadow> report
shadow> demo browser
shadow> stop
shadow> quit
```

The initial HTTP demo completed with **four confirmed findings**. `fix 1` ran the supported authentication patch on its own disposable copy: **four verification checks passed**, including preserved owner access, and the finding remained **AWAITING_REVIEW**. The Markdown export exists in the private run directory. The subsequent browser scan completed with **11 assertions** across authentication (**3**), object authorization (**5**) and sensitive fields (**3**), and all three browser verdicts were **CONFIRMED**. Header reproduction uses HTTP evidence, not a separate browser identity case. After `stop`/`quit`, the console exited successfully and all **six observed owned listener ports** (including the temporary patch ports) were closed. No patch was merged.

A separate disposable synthetic Next.js source project contained only a simple GET route returning public fixture data. These standalone commands ran from that project, without a dynamic target or project execution:

```bash
shadow init
shadow analyze .
shadow scan --repository .
shadow findings
shadow report --format markdown > shadow-report.md
head -n 10 shadow-report.md
```

Route discovery and the scan completed. Semgrep completed with zero errors; the optional OSV binary was **unavailable**, which is shown in the published excerpt and private result receipt. Both resulting static hypotheses were **INCONCLUSIVE**, not confirmed vulnerabilities. The report was exported and read successfully. This fixture is inside the disposable validation directory under the checkout; route discovery therefore records the containing repository's source commit, rather than a separate synthetic Git commit.

**Nine published PNGs are screenshots of actual sanitized terminal recordings rendered in Chromium for readability.** They are not hand-authored example results. The installation and project-analysis images explicitly identify their excerpts; their downloadable transcripts retain fuller actual output. Private paths and disposable identifiers were normalized before rendering. The explicit publication set was checked against both newly generated local API-token values and synthetic credential/sensitive-value fixtures; no such values, bearer strings or workspace paths are published. Full operational logs, databases, patch worktrees and token files remain ignored/private.

### Commands, prerequisites and results

Commands ran from `/workspace/shadow-lab`, except the disposable console/project sessions described above. Prerequisites were Node.js **24.19.0**, npm **11.9.0**, Git, uv with Python **3.12**, the existing repository Python dependencies, Chromium `/usr/bin/chromium`, and the installed Vercel CLI **63.1.0** / `@vercel/next` **22.0.0**. Locked landing dependencies were already installed. Installation fetched the authorized GitHub repository and package registries; security/network permissions were not broadened.

```bash
UV_CACHE_DIR=/workspace/.cache/uv \
UV_TOOL_DIR=/workspace/shadow-lab/.shadowlab/docs-tools \
UV_TOOL_BIN_DIR=/workspace/shadow-lab/.shadowlab/docs-bin \
  uv tool install --reinstall --python 3.12 \
  'git+https://github.com/Devesh36/shadow-lab.git@main'

# Private capture drivers; output is not published wholesale:
PYTHONPATH=. .venv/bin/python .shadowlab/docs-capture/capture.py
PYTHONPATH=. .venv/bin/python .shadowlab/docs-capture/project-capture.py
PYTHONPATH=. .venv/bin/python .shadowlab/docs-capture/export.py

# Reproducible PNG rendering from the committed sanitized transcripts:
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium \
  .venv/bin/python scripts/render-terminal-docs.py
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
npm_config_cache=/workspace/.cache/npm NODE_USE_ENV_PROXY=1 \
  node scripts/check-landing-vercel.cjs \
  /workspace/.cache/shadowlab-vercel-cli/node_modules/@vercel/next

# Existing static preview; finish the build before checking it:
python3 -m http.server 3100 --bind 127.0.0.1 --directory apps/landing/out
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium \
  .venv/bin/python scripts/validate-landing.py
.venv/bin/ruff check packages apps/api tests scripts
git diff --check
```

| Check | Final result | Evidence |
| --- | --- | --- |
| Fresh GitHub uv installation and guided REPL | Passed, including real demo, patch approval/verification, export and exit | Private `install.log`, `capture.log`; sanitized `results.json` under `.shadowlab/docs-capture/` |
| Real multi-identity browser demo | Passed; three confirmed browser cases, 11 assertions | `.shadowlab/docs-capture/results.json`; private saved run DB; published `07-browser.png` / `.txt` |
| Source-only project workflow | Passed, two INCONCLUSIVE hypotheses; optional OSV unavailable honestly retained | `.shadowlab/docs-capture/project-checks.json`, `results.json`; published `09-project.png` / `.txt` |
| Nine PNGs / transcripts / credential check | Passed; published text checked before rendering | `apps/landing/public/docs/terminal/manifest.json` and explicit PNG/text assets |
| Landing production build / TypeScript | Passed; `/` and `/docs` are static, about 2.1 MiB exported site | `.shadowlab/docs-capture/landing-build.log`, `typecheck.log`; ignored `apps/landing/out/` |
| Real Vercel Next.js packaging | Passed; landing/docs HTML and all nine PNG/transcript pairs present, zero functions; old `out` override rejected as expected | `.shadowlab/docs-capture/vercel-packaging.log`; `.shadowlab/vercel-manifest-fix/packaging-check.json` |
| Real Chromium static-site checks | **8 checks passed**, zero final failures: homepage/docs 200; application/API routes 404; desktop/mobile navigation/reload, copied commands, all nine images loaded, transcript download, production CSP and no page errors/API calls | `.shadowlab/docs-capture/static-browser-final.log`; `.shadowlab/vercel-validation/static-checks.json` |
| Visual inspection | Passed; desktop guide, mobile gallery and actual terminal rendering inspected | `.shadowlab/vercel-validation/docs-desktop.png`, `docs-demo-section.png`, `docs-mobile.png`, `docs-mobile-gallery.png`; public terminal PNGs |
| Python lint / whitespace | Passed | Commands above |
| Original 72-test application suite / Docker / PostgreSQL | Not repeated for this static docs/assets increment; preceding full suite passed 72 with zero skips | Preserved application evidence above |
| Native macOS Homebrew / Windows WSL / hosted Vercel delivery | Not run in this Linux workspace; no deployment or hosted header claim | Limitations below |

The first static probe ran before the production build finished writing the new export and observed `/docs/` **404**; waiting for build completion and rerunning passed. The mobile screenshot helper was also adjusted to wait for lazy-loaded gallery images after reload, rather than capturing an unloaded placeholder. These were local validation sequencing corrections; final browser checks and provider packaging passed.

The optional `test_postgres_persistence_if_configured` is unchanged. It passed in the preceding database-enabled full suite; this docs-only increment adds no PostgreSQL requirement or new skips and does not claim a fresh database/full-suite run. Homebrew commands are documented from the shipped formula; the public recording is specifically the verified Linux/uv path. WSL is a POSIX option, not a tested native Windows launcher. Browser tests apply the committed production headers locally and restrict all requests to the fixed loopback preview; they do not verify actual Vercel project settings or hosted header delivery. No arbitrary untrusted repository code was executed, and Docker Compose is not asserted as VM-grade isolation.

## Landing redesign and motion — 2026-10-10

The public `apps/landing` homepage was redesigned with an off-white canvas, dark typography, lime highlights, a sticky navigation bar, illustrated workflow cards, a dedicated documentation section, and a three-state Source/Validate/Review product preview. **Docs** is a prominent navigation button on desktop and mobile; further links in the hero, guide section, installation panel and footer lead to `/docs/`. The documentation page and its nine real sanitized terminal recordings remain intact. The preserved local application in `apps/web` and the investigation engine were not redesigned.

Motion includes staggered hero entrances, a drawn underline, typing/caret effects, sequential result rows, floating badges/orbit markers, an evidence-flow marker, scroll reveals, preview-panel transitions, and button/card hover effects. CSS handles these effects; a single IntersectionObserver reveals sections once and disconnects on navigation. There are no additional animation packages, remote fonts, external assets or backend requests. A Pause/Resume control disables/restores animation and transitions; `prefers-reduced-motion: reduce` disables them automatically and shows all content. With JavaScript disabled, the exported page still displays its content and documentation links. The preview is explicitly marked **ILLUSTRATION**; it neither starts scans nor reports live validation.

### Commands and evidence

Prerequisites remain the installed landing dependencies, Node.js 22+ (tested 24.19.0), npm, the existing Python/Playwright dependencies, compatible Chromium `/usr/bin/chromium`, and the installed Vercel CLI 63.1.0 / `@vercel/next` 22.0.0. The static preview was already running at loopback port 3100; finish the production build before inspecting it.

```bash
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
npm_config_cache=/workspace/.cache/npm NODE_USE_ENV_PROXY=1 \
  node scripts/check-landing-vercel.cjs \
  /workspace/.cache/shadowlab-vercel-cli/node_modules/@vercel/next
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium \
  .venv/bin/python scripts/validate-landing.py
.venv/bin/ruff check packages apps/api tests scripts
git diff --check
```

| Check | Final result | Sanitized evidence |
| --- | --- | --- |
| Production build and TypeScript | Passed; `/` and `/docs` remain static | `.shadowlab/landing-redesign/build-final.log`, `typecheck-final.log` |
| Actual Vercel Next.js packaging | Passed; zero runtime functions; landing/docs HTML and nine PNG/transcript pairs retained; former `out` override rejected as expected | `.shadowlab/landing-redesign/packaging-final.log`, `packaging-check.json` |
| Chromium static-site regression | **10 checks passed**, zero final failures | `.shadowlab/landing-redesign/browser-final.log`, `static-checks.json` |
| Interactive preview / keyboard / replay | Passed; Source shows a hypothesis, Review preserves owner access and requires review; keyboard tabs select/focus correctly | Browser result above |
| Motion controls / reduced motion | Passed; running animations stop on Pause, resume afterward, and are absent under reduced motion; all reveal content stays visible | Browser result above |
| Responsive layout | Passed at **320, 390, 768, 1024, 1440 and 1920 px**; no horizontal overflow; Docs and installation controls fully within the viewport | Browser result; `redesign-hero-desktop.png`, `redesign-hero-mobile.png`, `static-desktop.png`, `static-mobile.png` |
| Docs / installation / clipboard | Passed; navigation and direct docs reload, command copying, nine loaded images and transcript download | Browser result; `docs-desktop.png`, `docs-mobile.png` |
| Progressive rendering without JavaScript | Passed; homepage content visible and Docs navigation works | Browser result above |
| Production CSP / request scope | Passed with configured headers applied locally; no page errors, external requests or runtime API calls; application/API paths still 404 | Browser result above |
| Lint / whitespace | Passed | Commands above |

Desktop and mobile screenshots were visually inspected. The first browser run exposed decorative step numbers in the accessible tab names; they are now hidden from assistive technology so the names match Source/Validate/Review. The next run caught the installation link extending about three pixels beyond a 320px viewport, despite the page's clipping preventing horizontal scrolling. Narrow-screen navigation spacing was corrected, and the final regression checks actual link bounds as well as overflow. Intermediate failures are retained in `browser-first.log` and `browser-second.log`; final rebuilt checks passed.

This is a static website change. The earlier 72-test investigation suite, Docker/PostgreSQL checks and terminal-demo captures were not repeated; their preceding results and optional PostgreSQL prerequisite/skip logic are unchanged. Chromium was tested, not all browser engines. Local provider packaging does not prove cloud deployment or delivered Vercel headers. Deploy the latest `main` with Root Directory **`apps/landing`**; the local product's separate `apps/web` landing is intentionally preserved. No Vercel deployment, credential change, execution-policy relaxation, network-permission change, new service binding or arbitrary repository execution was performed.

## Phase 2: project usability and reliability — 2026-10-10

The REPL now selects a project with `project PATH` and supports `scan`, `routes`, `findings`, `history`, `use NUMBER`, and `report [json]`. Quoted paths preserve case and spaces. Canonical project paths get independent private SQLite/history/report directories under `SHADOWLAB_HOME/projects/`; neither the operator database/settings nor the source project is used as session storage. Reopening a project selects its latest saved scan. History displays the ten latest scans, newest first.

Project scans use fixed installed analysis tools in an isolated Python import mode (`-I`) from the trusted package directory. They never build, install, execute or patch project code, start its app, make dynamic target requests, call an LLM, or run network advisory checks. Local Semgrep uses the shipped rules; OSV is explicitly disabled in this console mode. Static findings remain INCONCLUSIVE. Directory/symlink escapes are denied. Each project scan holds a nonblocking process lock, including in its worker; cancellation, timeout and failure terminate its process group before recording incomplete coverage. A new failed scan never displays the previous successful scan's findings or report. Reopened abandoned records are marked incomplete, without replaying actions.

Setup diagnostics now check Node's actual major version, show corrective actions, and keep raw command output/credentials out of diagnostics. Markdown reports show scanner status, incomplete coverage and parse-error counts. Public Docs and README describe the new workflow; the nine historical terminal screenshots remain actual recordings from their documented earlier commit. The reviewed runtime bundle now has 69 source assets and excludes generated hidden directories, including Vercel artifacts. CI adds installed-wheel project smoke checks and the existing real public-site browser regression. [Roadmap](roadmap.md) records delivered acceptance gates, next comparison/triage work and the recurring regression loop.

### Prerequisites and commands

Tested on Linux with Python 3.12.14, uv 0.12.19, Node 24.19.0, npm 11.9.0, the existing locked `.venv`/npm dependencies, installed Semgrep, Chromium `/usr/bin/chromium`, Vercel CLI 63.1.0 / `@vercel/next` 22.0.0, and cached PostgreSQL 17.11 (`postgres:17-alpine`). CI targets Node 22. The existing loopback native helper was restarted after rebuilding its assets, using separate `.shadowlab/phase2/native` data/token state. The static preview already served the rebuilt `apps/landing/out` on loopback port 3100.

The managed command sandbox blocked Docker socket/loopback access and stalled asyncio's cross-thread SQLite wakeups; the independent SQLite diagnostic passed outside that syscall sandbox. Native browser, worker, build and database checks used individually approved local-test escalations. Environment network policy, credentials, TLS verification, application allowlists and execution policy were not changed. No VM boundary is claimed.

```bash
.venv/bin/ruff check packages apps/api tests scripts
.venv/bin/python scripts/update-bundle.py
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/landing run build
npm --prefix apps/landing run typecheck
npm --prefix apps/web run typecheck
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack
NEXT_TELEMETRY_DISABLED=1 npm --prefix examples/vulnerable-nextjs run build -- --webpack
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/validate-landing.py
node scripts/check-landing-vercel.cjs /workspace/.cache/shadowlab-vercel-cli/node_modules/@vercel/next
UV_CACHE_DIR=/workspace/.cache/uv uv build --wheel
.venv/bin/python scripts/check-bundle.py dist/shadowlab-0.1.0-py3-none-any.whl
UV_CACHE_DIR=/workspace/.cache/uv \
UV_TOOL_DIR="$PWD/.shadowlab/phase2/tools" \
UV_TOOL_BIN_DIR="$PWD/.shadowlab/phase2/bin" \
  uv tool install --reinstall --python 3.12 dist/shadowlab-0.1.0-py3-none-any.whl
.venv/bin/python scripts/smoke-project-installed.py .shadowlab/phase2/bin/shadow
SHADOWLAB_HOME="$PWD/.shadowlab/phase2/demo-home" \
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium \
  .venv/bin/python scripts/smoke-installed.py .shadowlab/phase2/bin/shadow

# Local daemon selectors were cleared for Docker commands.
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
  -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock network create --internal shadowlab-phase2-pg
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
  -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock run --rm -d --name shadowlab-phase2-pg \
  --network shadowlab-phase2-pg -p 127.0.0.1:55432:5432 --user postgres --read-only \
  --tmpfs /tmp:rw,nosuid,size=192m --tmpfs /var/run/postgresql:rw,nosuid,uid=70,gid=70 \
  --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 128 --memory 256m --cpus 1 \
  -e PGDATA=/tmp/pgdata -e POSTGRES_USER=shadowlab -e POSTGRES_PASSWORD=shadowlab-local \
  -e POSTGRES_DB=shadowlab postgres:17-alpine
SHADOWLAB_API_TOKEN=synthetic-config-check docker compose config --quiet

# This internal network did not publish the requested loopback mapping.
# Inspect the container's private address for a fresh run; 172.18.0.2 was observed here.
SHADOWLAB_TEST_POSTGRES_URL='postgresql+psycopg://shadowlab:shadowlab-local@172.18.0.2:5432/shadowlab?connect_timeout=3' \
SHADOWLAB_TEST_TARGET=http://127.0.0.1:3001 \
SHADOWLAB_TEST_DASHBOARD=http://127.0.0.1:3000 \
SHADOWLAB_CHROMIUM_PATH=/usr/bin/chromium \
  .venv/bin/pytest -q
.venv/bin/pytest -q tests/unit/test_project.py tests/unit/test_doctor.py tests/unit/test_repl.py
git diff --check
```

PostgreSQL uses synthetic fixture credentials and temporary data only, on a Docker network with no outbound route. The private database address is not a scanning target or public service. Compose configuration initially refused interpolation without its API token; the configuration-only check supplied a synthetic placeholder, without changing any stored credential.

### Results and evidence

| Check | Final result | Sanitized evidence |
| --- | --- | --- |
| Complete Python/API/browser suite | **91 passed, 0 failed, 0 skipped**, 226.48 s | `.shadowlab/phase2/full-final.log` |
| Real three-identity browser baseline and patches | Three CONFIRMED baseline cases; identical browser assertions NOT_REPRODUCED on all three disposable patches; owner controls retained; review required, none merged | `.shadowlab/phase2/browser/results.json`, `report.md`, `report.json`; six safe UI PNGs in that directory |
| Project isolation, history, reopening, repeated scans and context switches | Passed; quotes/case, root/symlink denial, unchanged source, operator-state isolation, per-project lock, stale/failed history, interruption recovery | Full suite above; installed smoke below |
| Cancellation, timeout and failure cleanup | Passed; scanner descendant termination, malformed-manifest failure/retry, launch/exit failure, failed new scan never inherits old report; existing browser logout/relogin, repeated runs, cancellation and out-of-scope redirect tests preserved | Full suite above |
| Installed wheel project console | Passed outside checkout; scan/routes/findings/history/reopen/export; three static hypotheses INCONCLUSIVE; Semgrep completed, OSV disabled | `.shadowlab/phase2/installed-project.json` |
| Installed wheel synthetic demo | Passed; four expected cases confirmed, private report sanitized, all three service ports closed on quit | `.shadowlab/phase2/installed-demo.log` |
| Real setup diagnostics | Passed; Node major 24, npm/Git found; no project state created | `.shadowlab/phase2/doctor.json` |
| Wheel and reviewed bundle | Passed; 69 assets, no private/generated directories; all wheel assets match current reviewed files | `.shadowlab/phase2/bundle-check.log`, `wheel-build.log` |
| Landing build / TypeScript / actual Vercel packaging | Passed; `/` and `/docs` static, zero runtime functions; former `out` override still rejected as expected | `.shadowlab/phase2/landing-build.log`, `typecheck.log`, `vercel-packaging.log`; `.shadowlab/vercel-manifest-fix/packaging-check.json` |
| Public static-site Chromium checks | **10 passed**; updated project commands copy correctly; docs/navigation/images, responsive layout, animation controls/reduced motion, no-JS rendering and request restrictions retained | `.shadowlab/phase2/landing-browser.log`; `.shadowlab/vercel-validation/static-checks.json` and desktop/mobile PNGs |
| Preserved frontend / reviewed demo builds | Passed; local web TypeScript and both production builds | `.shadowlab/phase2/web-typecheck.log`, `web-build.log`, `demo-build.log` |
| Docker/PostgreSQL | Passed: Compose config; PostgreSQL 17.11 on isolated internal network; migrations and reconnect persistence test | Full suite above; disposable database/network removed afterward |
| Python lint / whitespace | Passed | Commands above |

Browser reports and screenshots were copied from the final e2e test's private SQLite/evidence directory after its successful three patch verifications. Exported text was checked for both synthetic identity tokens, the synthetic sensitive-value sentinel and the injected operator-secret sentinel; none were present. Reports retain redacted evidence and field names. The complete test database, settings documents, private API token files and service logs are not published. The usual local helper was restored with its original data/token after testing; the existing token's digest was unchanged. Only this task's disposable database/network was removed.


The first non-e2e run had **77 passed, one failed, nine deselected**: PostgreSQL's requested loopback publication was unavailable on the internal network. Its private address was then verified with a bounded connection and used for the complete suite. The first complete run had **89 passed, one failed**: the long-running local frontend served an earlier build with the removed feature-branch install URL, and its Homebrew tab did not respond. Rebuilding/restarting the identified repository helper corrected the stale asset state. No frontend redesign or application feature change was needed. The descendant-cleanup test's process mock was also narrowed so its final `ps` assertion checks the real descendant instead of launching the mock again. Final results above use that corrected test.

The optional `test_postgres_persistence_if_configured` still skips when `SHADOWLAB_TEST_POSTGRES_URL` is absent. Its prerequisite/skip logic is unchanged; it ran and passed in the final database-enabled suite. A missing database must not be represented as a passed persistence check.

Limitations: project mode is heuristic Next.js source analysis, with no runtime verdict or dependency advisories. Missing/failed scanners do not prove a clean project. Native macOS Homebrew and Windows/WSL were not exercised. CI configuration was updated, but a hosted CI run is not claimed by local checks. Vercel adapter packaging/browser checks are local, not a hosted deployment or delivered-header guarantee. This increment does not rebuild the complete Docker application stack; relevant Docker checks cover the reviewed Compose configuration and disposable PostgreSQL persistence. Arbitrary untrusted repository execution remains disabled pending verified VM-grade or equivalent hardened isolation; Docker Compose alone is not that boundary. No merge, release publication, credential change, wider scan or security/network-policy expansion was performed.
