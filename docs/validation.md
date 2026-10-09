# Validation evidence

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
