@echo off
cd /d "%~dp0"
if not exist venv (
  echo No virtual environment found - run setup.bat first.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
echo Starting EditOS backend at http://localhost:8000
echo Leave this window open. Press Ctrl+C here to stop it.
uvicorn app.main:app --host 0.0.0.0 --port 8000
pause

