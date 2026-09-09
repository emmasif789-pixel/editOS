@echo off
cd /d "%~dp0"
echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Python was not found on this computer.
  echo Install it from https://www.python.org/downloads/ first.
  echo IMPORTANT: on the first install screen, check the box "Add python.exe to PATH".
  echo Then run this file again.
  pause
  exit /b 1
)

echo Creating a virtual environment in .\venv ...
python -m venv venv
call venv\Scripts\activate.bat

echo Installing dependencies - this can take a few minutes the first time...
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist .env (
  copy .env.example .env >nul
  echo.
  echo Created a .env file. Open it in Notepad and paste your real Gemini API key
  echo in place of "paste-your-real-key-here", then save it.
  notepad .env
)

echo.
echo Setup complete. Double-click start.bat to launch the backend.
pause
