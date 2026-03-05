@echo off
setlocal

if exist "%~dp0deploy_brain.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_brain.ps1" %*
  exit /b %errorlevel%
)

where bash >nul 2>nul
if not errorlevel 1 (
  bash "%~dp0deploy_brain.sh" %*
  exit /b %errorlevel%
)

echo [ERROR] No launcher available. Install PowerShell or bash ^(Git Bash/WSL^).
exit /b 1