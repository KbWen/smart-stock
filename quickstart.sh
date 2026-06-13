#!/bin/bash
# Smart Stock — one-command quickstart (offline demo).
# Installs backend deps, seeds the bundled demo dataset + scores (no network),
# and prints how to launch. A newcomer sees a populated dashboard in minutes.
set -e
cd "$(dirname "$0")"

echo "==================================================="
echo "🚀 Smart Stock — Quickstart (offline demo)"
echo "==================================================="

echo "[1/3] Installing backend dependencies..."
python3 -m pip install -r requirements.txt

echo "[2/3] Seeding offline demo data + scores (no network needed)..."
python3 scripts/seed_demo.py

echo ""
echo "[3/3] ✅ Ready. Launch the app:"
echo "    Backend : python3 backend/main.py          → http://localhost:8000"
echo "    Frontend: cd frontend/v4 && npm install && npm run dev → http://localhost:5173"
echo "  (or run ./start.sh to start both at once)"
echo ""
echo "Note: no AI model is bundled, so AI probability shows N/A until you run"
echo "      'python3 backend/train_ai.py' to train one. Technical scores work offline now."
