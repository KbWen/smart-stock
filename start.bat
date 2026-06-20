@echo off
echo ===================================================
echo [Start] Smart Stock Selector  (http://localhost:8000)
echo ===================================================
echo.

:: Ensure we run from the project root (where this script resides)
cd /d "%~dp0"

if not exist "frontend\v4\dist\index.html" (
  echo [warn] Built web UI not found in frontend\v4\dist.
  echo        Run quickstart first, or: cd frontend/v4 ^&^& npm ci ^&^& npm run build
  echo.
)

:: Start the backend, which serves the built web UI on a single port
echo Starting server on http://localhost:8000 ...
start "Smart Stock" cmd /c "python backend/main.py"

:: Wait 2 seconds for the server to initialize, then open the browser
timeout /t 2 /nobreak > nul
start http://localhost:8000/

echo.
echo [SUCCESS] Server starting in a separate window. Close it to stop.
echo For hot-reload dev mode instead: cd frontend/v4 ^&^& npm run dev
exit /b 0
