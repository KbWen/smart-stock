#!/bin/bash
# Smart Stock — one-command quickstart (offline demo).
# Installs backend deps, seeds the bundled demo dataset + scores (no network),
# builds the web UI, and prints the single-URL launch command.
set -e
cd "$(dirname "$0")"

echo "==================================================="
echo "🚀 Smart Stock — Quickstart (offline demo)"
echo "==================================================="

echo "[1/4] Installing backend dependencies..."
python3 -m pip install -r requirements.txt

echo "[2/4] Seeding offline demo data + scores (no network needed)..."
python3 scripts/seed_demo.py

echo "[3/4] Building the web UI (one-time, needs Node.js >= 18)..."
if command -v npm >/dev/null 2>&1; then
    ( cd frontend/v4 && npm ci && npm run build ) || echo "  [warn] UI build failed — install Node.js >= 18, then: cd frontend/v4 && npm ci && npm run build"
else
    echo "  [warn] Node.js/npm not found - the bundled web UI was NOT built."
    echo "         Install Node.js >= 18, then run: cd frontend/v4 && npm ci && npm run build"
fi

echo ""
echo "[4/4] ✅ Ready. Launch the app (single URL):"
echo "    python3 backend/main.py      →  http://localhost:8000"
echo "  (or just run ./start.sh)"
echo ""
echo "Note: no AI model is bundled, so AI probability shows N/A. For REAL AI"
echo "      (opt-in, slower): python3 scripts/setup_real_ai.py  (syncs full market, then trains)."
echo "      Technical scores already work offline."
