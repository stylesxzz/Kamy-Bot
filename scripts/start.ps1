$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (!(Test-Path .env)) { throw "Run scripts/install.ps1 first." }
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process") }
}
& .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port $(if ($env:KAMY_PORT) {$env:KAMY_PORT} else {"8765"})
