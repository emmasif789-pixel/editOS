@echo off
echo Starting EditOS backend...
cd /d "%~dp0"
docker compose up -d
echo.
echo Done. Backend running in the background at http://localhost:8000
echo You can close this window - the containers keep running.
echo First time only: pull the AI model with:
echo   docker exec -it editos-backend-ollama-1 ollama pull llama3.2:1b
pause
