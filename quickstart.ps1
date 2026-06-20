# Smart Stock - one-command quickstart (offline demo).
# Installs backend deps, seeds the bundled demo dataset + scores (no network),
# builds the web UI, and prints the single-URL launch command.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==================================================="
Write-Host "Smart Stock - Quickstart (offline demo)"
Write-Host "==================================================="

Write-Host "[1/4] Installing backend dependencies..."
python -m pip install -r requirements.txt

Write-Host "[2/4] Seeding offline demo data + scores (no network needed)..."
python scripts/seed_demo.py

Write-Host "[3/4] Building the web UI (one-time, needs Node.js >= 18)..."
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Push-Location frontend/v4
    try {
        npm ci
        npm run build
    } finally {
        Pop-Location
    }
} else {
    Write-Host "  [warn] Node.js/npm not found - the bundled web UI was NOT built."
    Write-Host "         Install Node.js >= 18, then run: cd frontend/v4; npm ci; npm run build"
}

Write-Host ""
Write-Host "[4/4] Ready. Launch the app (single URL):"
Write-Host "    python backend/main.py      ->  http://localhost:8000"
Write-Host "  (or just run .\start.ps1)"
Write-Host ""
Write-Host "Note: no AI model is bundled, so AI probability shows N/A until you run"
Write-Host "      'python backend/train_ai.py' to train one. Technical scores work offline now."
