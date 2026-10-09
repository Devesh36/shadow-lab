# Threat model

ShadowLab handles repository files, source paths, scanner output, HTTP responses, and provider output as untrusted data. Its trusted inputs are operator authorization, reviewed scanner rules, the shipped fixture manifest, installed package artifacts, and the execution policy. These are local single-user trust boundaries.

| Threat | Implemented boundary | Practical limit |
| --- | --- | --- |
| Model creates arbitrary commands | Only a typed index-selection tool; no model shell | Optional providers can leak supplied metadata; enable intentionally |
| SSRF, metadata access, DNS rebinding | Exact origins, non-global IP denial, explicit loopback exception, address pinning and rechecking | DNS/provider/control-plane traffic is distinct from target tests |
| Redirect escape | All redirects rejected; no follow | Applications requiring redirects need a reviewed adapter |
| Unbounded testing | GET-only plans plus fixed demo login/logout, category allowlist, 1–200 request cap, rate and time budgets, response cap, cancellation | GET must be non-destructive on the operator's target |
| Secret retention | Recursive sensitive-key redaction; unknown text omitted; no request auth headers persisted | Arbitrarily named secrets in allowed JSON fields need application-specific redactors |
| False confirmation | Seeded owned-resource baseline and a distinct second owner required for BOLA | Fixture identities and business rules are operator-supplied assumptions |
| Malicious repository code | Source reads only; no installs or execution for registered repositories | Parsers and scanners are not VM-isolated; use a separate VM for hostile samples |
| Patch overwrites user work | Trusted snapshot and separate Git worktree, exact manifest, no merges | General repository remediation is manual |
| Demo escapes its container | Non-root users, dropped capabilities, read-only app roots, no socket/mount credentials, private lab networking | Compose and trusted local subprocesses are not VM-grade isolation |
| Public dashboard access | Loopback startup defaults, local-host proxy checks, cross-origin rejection, authenticated backend | Public deployment and multi-user RBAC are not implemented |

The screenshot adapter renders sanitized evidence with JavaScript and network disabled. It does not visit untrusted target pages. The separate demo browser adapter visits only checksum-reviewed local demo UI, in three independent incognito contexts. It verifies server identity before each protected UI action, rejects session substitution, and persists no cookies, storage state, bearer values, raw DOM, HAR, or traces. Every routed request passes through the existing pinned DNS transport with a dead browser proxy; service workers and WebSockets are disabled. It permits only synthetic login/logout POSTs in addition to bounded reads. Browser request/byte/time caps and scan cancellation remain authoritative. Docker init reaps browser child processes. Native execution relies on the operator host for process/memory limits; neither Chromium nor Compose is a verified hostile-code boundary. ZAP is an operator-only passive adapter and has not been validated against a live daemon. The graph cannot select ZAP active scans or browser scripts.

Stored synthetic tokens are local settings used for fixture authentication; GET settings redacts them. Real target credentials should not be used in this version. API/LLM tokens belong in protected server environment settings, not reports, source, or browser state. Production secrets require a dedicated secrets and identity design.

The sandbox deliberately refuses arbitrary repository execution rather than presenting container development as a hostile-code boundary. A future VM worker must enforce egress outside the guest, block metadata, use disposable databases/accounts, apply hard resource limits, collect sanitized artifacts, and destroy the guest after testing.
