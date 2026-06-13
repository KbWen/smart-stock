# Smart Stock - one-command quickstart (offline demo).
# Installs backend deps, seeds the bundled demo dataset + scores (no network),
# and prints how to launch. A newcomer sees a populated dashboard in minutes.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==================================================="
Write-Host "Smart Stock - Quickstart (offline demo)"
Write-Host "==================================================="

Write-Host "[1/3] Installing backend dependencies..."
python -m pip install -r requirements.txt

Write-Host "[2/3] Seeding offline demo data + scores (no network needed)..."
python scripts/seed_demo.py

Write-Host ""
Write-Host "[3/3] Ready. Launch the app:"
Write-Host "    Backend : python backend/main.py            -> http://localhost:8000"
Write-Host "    Frontend: cd frontend/v4; npm install; npm run dev   -> http://localhost:5173"
Write-Host "  (or run .\start.bat to start both at once)"
Write-Host ""
Write-Host "Note: no AI model is bundled, so AI probability shows N/A until you run"
Write-Host "      'python backend/train_ai.py' to train one. Technical scores work offline now."
