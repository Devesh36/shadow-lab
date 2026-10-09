#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.shadowlab/cache/uv}"
export npm_config_cache="${npm_config_cache:-$PWD/.shadowlab/cache/npm}"
uv sync --locked
npm --prefix apps/web ci --no-audit --no-fund
npm --prefix examples/vulnerable-nextjs ci --no-audit --no-fund
mkdir -p .shadowlab
uv run alembic upgrade head
uv run shadowlab init
NEXT_TELEMETRY_DISABLED=1 npm --prefix apps/web run build -- --webpack
NEXT_TELEMETRY_DISABLED=1 npm --prefix examples/vulnerable-nextjs run build -- --webpack
