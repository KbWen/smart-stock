#!/bin/bash
echo "==================================================="
echo "🚀 Smart Stock Selector  (http://localhost:8000)"
echo "==================================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")"

if [ ! -f "frontend/v4/dist/index.html" ]; then
    echo "[warn] Built web UI not found in frontend/v4/dist."
    echo "       Run ./quickstart.sh first, or: cd frontend/v4 && npm ci && npm run build"
    echo ""
fi

# Start the backend, which serves the built web UI on a single port
echo "Starting server on http://localhost:8000 ..."
python3 backend/main.py &
BACKEND_PID=$!

# Wait, then open the browser
sleep 2
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000/
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:8000/ 2>/dev/null || echo "Please open http://localhost:8000/ in your browser."
fi

# Stop the server cleanly on exit
cleanup() {
    echo ""
    echo "Stopping server..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo "Press Ctrl+C to stop. For hot-reload dev mode instead: cd frontend/v4 && npm run dev"
wait
