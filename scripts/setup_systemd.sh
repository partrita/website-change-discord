#!/usr/bin/env bash
# Helper script to run setup_systemd using uv or python
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run setup_systemd "$@"
else
    exec python3 -m src.setup_systemd "$@"
fi
