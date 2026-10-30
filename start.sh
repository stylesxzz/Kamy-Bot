#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo 'Docker is required.'; exit 1; }
[ -f .env ] || cp .env.example .env
docker compose up --build -d
PORT=$(grep '^KAMY_PORT=' .env | cut -d= -f2 || echo 8000)
echo "Kamy Bot is starting: http://localhost:${PORT:-8000}"
docker compose ps
