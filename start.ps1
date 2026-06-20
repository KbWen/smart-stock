# Smart Stock - single-port launcher.
# Starts the backend, which serves the built web UI on http://localhost:8000,
# then opens the browser. Run quickstart.ps1 first to build the UI.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==================================================="
Write-Host "Smart Stock Selector  (http://localhost:8000)"
Write-Host "==================================================="
Write-Host ""

if (-not (Test-Path "frontend/v4/dist/index.html")) {
    Write-Host "[warn] Built web UI not found in frontend/v4/dist."
    Write-Host "       Run .\quickstart.ps1 first, or: cd frontend/v4; npm ci; npm run build"
    Write-Host ""
}

Write-Host "Starting server on http://localhost:8000 ..."
Start-Process -FilePath "python" -ArgumentList "backend/main.py"

# Give the server a moment to boot, then open the browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:8000/"

Write-Host ""
Write-Host "[OK] Server starting in a separate process."
Write-Host "For hot-reload dev mode instead: cd frontend/v4; npm run dev"
