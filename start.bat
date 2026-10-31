@echo off
setlocal
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul
docker compose up --build -d
if errorlevel 1 (
  echo Kamy Bot failed to start. Check Docker Desktop and run: docker compose logs
  pause
  exit /b 1
)
set "KAMY_PORT=8000"
for /f "tokens=2 delims==" %%A in ('findstr /b "KAMY_PORT=" .env') do set "KAMY_PORT=%%A"
echo Kamy Bot is starting: http://localhost:%KAMY_PORT%/
docker compose ps
pause
endlocal
