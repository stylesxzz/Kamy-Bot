#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo "Python 3.11+ is required."; exit 1; }
python3 - <<'PY'
import sys
if sys.version_info < (3,11): raise SystemExit("Python 3.11 or newer is required.")
PY
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data
if [ ! -f .env ]; then
  cp .env.example .env
  KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
  if grep -q '^KAMY_MASTER_KEY=' .env; then sed -i.bak "s|^KAMY_MASTER_KEY=.*|KAMY_MASTER_KEY=$KEY|" .env; else printf '\nKAMY_MASTER_KEY=%s\n' "$KEY" >> .env; fi
  echo "Created .env and generated a local encryption key. Back it up securely."
fi
echo "Install complete. Start with: ./scripts/start.sh"
