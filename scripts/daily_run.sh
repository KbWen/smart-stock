#!/bin/bash

echo "==================================================="
echo "🚀 Smart Stock Selector - Daily Auto Update (Mac/Linux)"
echo "==================================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")"

echo "[1/3] Syncing Stock Data..."
python3 backend/main.py --sync
if [ $? -ne 0 ]; then
    echo "❌ Error in Syncing!"
    exit 1
fi

echo ""
echo "[2/3] Retraining Sniper AI Ensemble..."
python3 backend/train_ai.py
if [ $? -ne 0 ]; then
    echo "❌ Error in AI Training!"
    exit 1
fi

echo ""
echo "[3/3] Recalculating Scores & Ranks..."
python3 backend/recalculate.py
if [ $? -ne 0 ]; then
    echo "❌ Error in Recalculation!"
    exit 1
fi

echo ""
echo "✅ Daily Update Complete! Best picks are ready."
exit 0
