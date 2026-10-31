#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[ -d .venv ] || { echo "Run ./scripts/install.sh first."; exit 1; }
set -a
[ ! -f .env ] || . ./.env
set +a
exec .venv/bin/uvicorn app:app --host 127.0.0.1 --port "${KAMY_PORT:-8765}"
