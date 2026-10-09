#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -m)" != "x86_64" || "$(uname -s)" != "Linux" ]]; then
  echo "This helper pins Linux amd64. Install the matching signed/checksummed official OSV release for your platform."
  exit 1
fi
mkdir -p .shadowlab/tools
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT
curl -fsSL https://github.com/google/osv-scanner/releases/download/v2.6.0/osv-scanner_linux_amd64 -o "$temp_dir/osv-scanner"
printf '%s  %s\n' 'ca69b3d3cd08f889a49dc0a383122f71cc528b83803671df5fd874d97485b108' "$temp_dir/osv-scanner" | sha256sum --check
install -m 755 "$temp_dir/osv-scanner" .shadowlab/tools/osv-scanner
.shadowlab/tools/osv-scanner --version
