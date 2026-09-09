@echo off
echo Starting EditOS backend...
cd /d "%~dp0"
docker compose up -d
echo.
echo Done. Backend running in the background at http://localhost:8000
echo You can close this window - the container keeps running.
echo Make sure GEMINI_API_KEY is set in your .env file (see .env.example).
pause
