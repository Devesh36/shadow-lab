#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
root_dir="$PWD"
export NEXT_TELEMETRY_DISABLED=1
export SHADOWLAB_TOKEN_FILE="${SHADOWLAB_TOKEN_FILE:-$(realpath -m "${SHADOWLAB_DATA_DIR:-$root_dir/.shadowlab}/api-token")}"
.venv/bin/shadowlab init
pids=()
cleanup() { for pid in "${pids[@]}"; do kill -- "-$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
setsid .venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 & pids+=("$!")
(cd "$root_dir/apps/web" && exec setsid env HOSTNAME=127.0.0.1 PORT=3000 node .next/standalone/server.js) & pids+=("$!")
(cd "$root_dir/examples/vulnerable-nextjs" && exec setsid env HOSTNAME=127.0.0.1 PORT=3001 node .next/standalone/server.js) & pids+=("$!")
wait -n "${pids[@]}"
