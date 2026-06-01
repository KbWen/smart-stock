@echo off
echo ===================================================
echo [Daily Run] Smart Stock Selector - Daily Auto Update (Windows)
echo ===================================================
echo.

:: Ensure we run from the project root (where this script resides)
cd /d "%~dp0"

echo [1/3] Syncing Stock Data...
python backend/main.py --sync %*
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Error in Syncing!
    exit /b 1
)

echo.
echo [2/3] Retraining Sniper AI Ensemble...
python backend/train_ai.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Error in AI Training!
    exit /b 1
)

echo.
echo [3/3] Recalculating Scores ^& Ranks...
python backend/recalculate.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Error in Recalculation!
    exit /b 1
)

echo.
echo [SUCCESS] Daily Update Complete! Best picks are ready.
exit /b 0
