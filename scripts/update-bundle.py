"""Maintain the explicit assets shipped to the guided demo; excludes all generated/private state."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = {"alembic.ini", "pyproject.toml", "uv.lock", "infrastructure/sandbox/demo-manifest.json"}
for directory in ("packages", "apps/api", "apps/web/app", "apps/web/components", "apps/web/lib",
                  "examples/vulnerable-nextjs/app", "examples/vulnerable-nextjs/lib"):
    for path in (root / directory).rglob("*"):
        if path.is_symlink() or any(part.startswith('.') or part in {'node_modules', '__pycache__', 'dist', 'build', 'out'}
                                    for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix in {".py", ".tsx", ".ts", ".css", ".yml", ".toml"}:
            files.add(path.relative_to(root).as_posix())
for directory in ("apps/web", "examples/vulnerable-nextjs"):
    for name in ("package.json", "package-lock.json", "next.config.ts", "tsconfig.json"):
        files.add(f"{directory}/{name}")
files.add("apps/web/postcss.config.mjs")
(root / "packages/core/bundle-files.json").write_text(json.dumps(sorted(files), indent=2) + "\n")
print(f"Bundled {len(files)} reviewed source assets")
