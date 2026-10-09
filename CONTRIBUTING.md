# Contributing

Use Python 3.12 and Node.js 22 or newer. Run `bash scripts/setup.sh`, then the lint, unit/integration, build, and E2E commands in README. Add a meaningful test for policy changes and verify denial paths as well as success paths. Use frozen Python and npm locks for setup; update locks deliberately when changing dependencies.

Keep the graph independent of the frontend. Framework adapters must expose source references and explicitly document heuristic limits. Dynamic tools must be typed, bounded, audited, and enforced by the independent policy gateway. Do not expose shell commands or raw network clients to models.

Never call a static hypothesis confirmed without runtime evidence. New patch strategies must preserve user changes, generate regressions, rerun original validation, record failures, and require review. Changes to demo execution code require reviewing and updating its checksum manifest; this must never happen automatically during setup or patch generation.

Each cloud task is already isolated. Develop in its existing checkout; do not create task worktrees unless explicitly requested. The remediation engine's explicitly requested disposable patch worktrees are a separate product feature.

Changes to shipped demo/runtime assets must update the explicit package inventory:

```bash
uv run python scripts/update-bundle.py
uv build
```

The guided launcher copies only these reviewed files, never dependencies, generated builds, credentials or arbitrary files from the current directory. Verify the resulting wheel includes all inventory entries before changing the distribution. The Homebrew formula is HEAD-only until a separately approved stable release; do not invent release URLs or publish a package as part of ordinary local development.
