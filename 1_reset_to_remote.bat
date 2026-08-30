@echo off
rem === (1) Discard local changes and match origin/main ===
cd /d "%~dp0"
git fetch origin
git reset --hard origin/main
echo.
echo [done] reset to origin/main
pause
