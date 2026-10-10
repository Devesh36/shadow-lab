# ShadowLab working instructions

Preserve the implemented application, checkout and existing user changes. Work in the existing checkout; do not create a worktree unless requested. Arbitrary untrusted repository execution stays disabled until verified VM-grade or equivalent hardened isolation is available. Do not treat Docker Compose as that boundary or broaden security/network permissions as part of routine development.

## Keep the public phase history current

The user wants each work chat and commit reflected in the landing page's **Phases** section. For each completed change, update `apps/landing/content/phases.json` with a concise, public description of what changed and what it enables for users. Record dates in **Asia/Kolkata (India Standard Time)**. Describe actual results; do not invent earlier dates or mark planned work as implemented. Summarize the work, not the conversation: never copy private chat transcripts, credentials, internal logs or sensitive evidence into the public catalog.

For an existing commit, use its full 40-character SHA. For the change being committed, use `commit: null`, an exact `matchSubject` matching the intended commit subject, and today's IST date. The build resolves that annotation to its own commit without a self-referential commit hash. Keep subjects unique enough to identify the change. At the start of each new increment, resolve older pending annotations to their verified full SHA and IST date using Git before adding a new note. New unannotated Git commits still appear using their subjects; add useful product-impact notes for them when working on the next increment.

`apps/landing/scripts/generate-phases.mjs` collects up to 1,000 available commits at build time and merges reviewed notes/snapshot history. Generated `.generated/phases.json` is ignored: never commit it. A Git-free source archive uses the reviewed snapshot; valid injected Vercel commit metadata can link its matching current note using the reviewed work date. Preserve historical entries. Complete Git history remains linked through the public archive. CI checks out full history; there are no browser-time GitHub requests or automatic write-back commits.

For landing/history changes run the history tests, landing production build, TypeScript check, real static browser regression and local Vercel packaging check documented in `docs/validation.md`. Update that report with actual outcomes and limitations. Follow `CONTRIBUTING.md` for application/distribution changes and preserve explicit patch review.
