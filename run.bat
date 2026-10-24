@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 (
  echo.
  echo OSLLM could not start. Read the error above and see README.md troubleshooting.
  pause
  exit /b 1
)
endlocal
