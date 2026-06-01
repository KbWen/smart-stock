@echo off
echo ===================================================
echo [Start] Starting Smart Stock Selector (Development Mode)
echo ===================================================
echo.

:: Ensure we run from the project root (where this script resides)
cd /d "%~dp0"

:: Start backend in a new window
echo Starting Backend API Server (Port 8000)...
start "Smart Stock Backend" cmd /c "python backend/main.py"

:: Wait 2 seconds for backend to initialize
timeout /t 2 /nobreak > nul

:: Start frontend dev server in a new window
echo Starting Frontend Dev Server (Port 5173)...
cd frontend/v4
start "Smart Stock Frontend" cmd /c "npm run dev"

:: Open browser
echo Opening browser to http://localhost:5173/...
start http://localhost:5173/

echo.
echo [SUCCESS] Both servers are starting. Close the separate console windows to stop them.
exit /b 0
