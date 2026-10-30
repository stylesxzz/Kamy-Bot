@echo off
cd /d "%~dp0"
if not exist .env copy .env.example .env
docker compose up --build -d
if errorlevel 1 pause
echo Kamy Bot: http://localhost:8000/
docker compose ps
pause
