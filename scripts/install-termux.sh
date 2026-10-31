#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
pkg update -y
pkg install -y python git clang rust
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p data
if [ ! -f .env ]; then
 cp .env.example .env
 KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
 sed -i "s|^KAMY_MASTER_KEY=.*|KAMY_MASTER_KEY=$KEY|" .env
fi
echo "Ready. Start with: ./scripts/start.sh"
