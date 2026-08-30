@echo off
chcp 65001 >nul
rem === (2) Commit local changes, merge remote, push ===
cd /d "%~dp0"
git add .
git commit -m "★指摘"
git merge origin/main
git push
echo.
echo [done] commit / merge / push
pause
