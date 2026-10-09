# Disposable authorization fixture

This app contains only synthetic identities, records, and credentials. Start with `npm ci && npm run dev -- --webpack` or use the root startup/Compose helpers. Do not deploy it to a public environment.

| Endpoint | Intended behavior | Deliberate defect |
| --- | --- | --- |
| POST `/api/login` | Select Alice or Bob and return their demo token | Synthetic login, not production authentication |
| GET `/api/records/[id]` | An owner can read their own record | Handler authenticates but omits ownership validation |
| GET `/api/unprotected` | Protect Alice's seeded record | No session check; anonymous access succeeds |
| GET `/api/profile` | Return a public profile projection for the session | Includes `passwordHash` and `apiKey` fields |
| GET `/` | Show lab instructions | No CSP, Referrer-Policy, or Content-Type protection headers |

Bearer `demo-alice` accesses Alice's fixture; `demo-bob` accesses Bob's. Record IDs are `alice-record` and `bob-record`. This is intentional lab data, not real credentials. The two positive baselines distinguish an ownership bypass from a generic success response.

Template remediation supports the three API defects. Each proposed fix includes a generated regression plan and is verified in a disposable Git worktree. Original files are never changed. `infrastructure/sandbox/demo-manifest.json` records reviewed source checksums; source changes cause verification to refuse execution until maintainers review and explicitly update the manifest.

The local UI supports synthetic Alice/Bob login using an HttpOnly SameSite cookie, logout, and a server identity probe. The browser adapter uses separate anonymous/Alice/Bob contexts and the same two immutable seeded records, which are disposable with the demo process. The UI displays only status, resource/owner IDs, and sensitive field names; credential values never enter its DOM. The reviewed manifest includes these session routes and UI changes.
