# Kamy installers

- Linux/macOS: `bash scripts/install.sh`, then `bash scripts/start.sh`.
- Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/install.ps1`, then `scripts/start.ps1`.
- Termux: `bash scripts/install-termux.sh`, then `bash scripts/start.sh`.

The app binds to 127.0.0.1 only. Back up `.env` and the data directory securely. Never commit secrets.
