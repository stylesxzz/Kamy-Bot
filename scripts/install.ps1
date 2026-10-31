$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) { py -3.11 -m venv .venv } else { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt
New-Item -ItemType Directory -Force data | Out-Null
if (!(Test-Path .env)) {
  Copy-Item .env.example .env
  $key = & .\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  (Get-Content .env) -replace '^KAMY_MASTER_KEY=.*', "KAMY_MASTER_KEY=$key" | Set-Content .env
}
Write-Host "Install complete. Run .\scripts\start.ps1"
