@echo off
echo Stopping EditOS backend...
cd /d "%~dp0"
docker compose down
echo Done.
pause
