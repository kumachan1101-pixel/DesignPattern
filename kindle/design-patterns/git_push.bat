@echo off
rem usage: git_push.bat "commit message"   (or double-click and type it)
setlocal
cd /d "%~dp0"

set "GIT=git"
where git >nul 2>&1 || set "GIT=C:\Program Files\Git\cmd\git.exe"

set "MSG=%~1"
if "%MSG%"=="" set /p "MSG=commit message: "
if "%MSG%"=="" set "MSG=update"

> commit_push_log.txt 2>&1 (
  echo ==== %DATE% %TIME% ====
  echo [message] %MSG%
  echo [where git]
  where git
  echo [rev-parse --show-toplevel]
  "%GIT%" rev-parse --show-toplevel
  echo [add]
  "%GIT%" add .
  echo [commit]
  "%GIT%" commit -m "%MSG%"
  echo [fetch]
  "%GIT%" fetch origin
  echo [merge origin/main]
  "%GIT%" merge origin/main --no-edit
  echo [push]
  "%GIT%" push
  echo [status]
  "%GIT%" status -sb
)

type commit_push_log.txt
echo.
echo ---- saved to commit_push_log.txt ----
endlocal
pause
