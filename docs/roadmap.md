# ShadowLab improvement roadmap

ShadowLab V1 proves a bounded investigation on a reviewed local demo. The next milestones improve everyday use and reliability before expanding execution scope. These are delivery gates, not claims that future capabilities exist.

## Phase 2: usable project console

Implemented in this increment:

- Select a Next.js project with `project PATH`, then use `scan`, `routes`, `findings`, `history`, `use NUMBER`, and `report [json]` without leaving the REPL.
- Retain the ten latest scans in history, reopen private state by canonical project path, and keep operator settings/database, demo runs and source projects separate.
- Preserve path case and quoted spaces. Deny directory and symlink escapes outside the configured repository root.
- Keep source analysis separate from execution: no application build, install, launch, runtime target, LLM call, dependency-advisory request or project patch.
- Terminate analysis workers and scanner process groups on cancellation, timeout and failure. Keep failed/cancelled records visible; never reuse a previous successful verdict for a new failed run.
- Check the installed Node major version in setup diagnostics, show corrective actions, and report scanner coverage in Markdown as well as JSON.
- Exercise the installed wheel's project workflow and the public site's real browser regression in CI, alongside existing application/browser/patch tests.

Acceptance: installed console works outside this checkout; repeated runs and reopening preserve history; source remains unchanged; static findings remain INCONCLUSIVE; cancellation/failure releases process groups and project locks; existing synthetic demo, owner controls, three identity contexts and patch review behavior remain intact. See [validation evidence](validation.md) for measured results and prerequisites.

## Phase 3: understand changes between scans

Next priority: compare two completed source scans for added/removed routes and hypothesis changes. Carry commit/source attribution and scanner failures into the comparison; never interpret a missing or failed scanner as a resolved vulnerability. Add local triage notes with explicit human attribution. Keep findings as hypotheses until supported by runtime evidence.

Acceptance: deterministic comparison fixtures; correct handling of failed scans, renamed routes and missing tools; no overwrite of original evidence; usable console and report output. Define a stable exported report schema before offering external integrations.

## Phase 4: clearer analysis coverage

Add focused framework cases for imported authentication helpers and ownership patterns, with fixtures that demonstrate both false positives and missed coverage. Improve error and incomplete-coverage guidance based on real user reports. Consider optional, explicit dependency-advisory checks without silently adding network requests to project mode.

Acceptance: each new supported pattern has a positive and negative fixture; reports state what was analyzed and what remains unsupported; existing runtime safety tests remain mandatory.

## Continuous improvement loop

For each small increment:

1. Record a concrete user problem and a measurable acceptance check.
2. Implement a reviewable change while preserving the prior application and execution policy.
3. Run Python regressions, API/frontend checks, installed-package smoke tests, public-site browser/provider packaging checks, and relevant PostgreSQL/trusted-demo checks.
4. Add regression coverage for a reproduced defect. Record failed, skipped, blocked and incomplete checks honestly in `docs/validation.md`; retain sanitized evidence privately.
5. Review the diff and exported evidence before delivery. Release publication, deployment and changes to credentials or security/network permissions require separate authorization.

CI runs on every push and pull request. It prevents regressions; it does not autonomously redesign the product or grant execution permissions. This workspace task delivers one bounded increment, not an unattended background agent.

## Deferred execution scope

Arbitrary untrusted repository execution stays disabled until VM-grade or equivalent hardened isolation is implemented **and verified**. Docker Compose alone does not satisfy that gate. Generalized patches, arbitrary browser identity adapters, multi-user server authentication and wider target scanning need separate designs and authorization; they are outside this phase.
