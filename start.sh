#!/bin/bash
echo "==================================================="
echo "🚀 Starting Smart Stock Selector (Development Mode)"
echo "==================================================="
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")"

# Start backend in background
echo "Starting Backend API Server (Port 8000)..."
python3 backend/main.py &
BACKEND_PID=$!

# Wait 2 seconds
sleep 2

# Start frontend dev server in background
echo "Starting Frontend Dev Server (Port 5173)..."
cd frontend/v4
npm run dev &
FRONTEND_PID=$!

# Open browser depending on OS
echo "Opening browser to http://localhost:5173/..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5173/
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:5173/ 2>/dev/null || echo "Please open http://localhost:5173/ in your browser."
fi

# Function to stop both background processes on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "Press Ctrl+C to stop both servers."
wait
