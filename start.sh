#!/usr/bin/env bash
# ==============================================================================
# CiteVerify Unified Startup Script (macOS / Linux)
# Launches both FastAPI Python Backend and Vite React Frontend with supervisor
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$DIR/citeverify-backend"
FRONTEND_DIR="$DIR/citeverify-frontend/citeverify_frontend"

echo ""
echo "============================================================"
echo "   CiteVerify — Verify the Science. Trust the Evidence.     "
echo "============================================================"
echo ""

# Find Python executable
PYTHON_BIN=""
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
elif [ -f "$BACKEND_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
elif command -v python3.11 &>/dev/null; then
    PYTHON_BIN="$(command -v python3.11)"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
else
    echo "[ERROR] Python 3.10+ is required but was not found."
    exit 1
fi

echo "[INFO] Using Python: $PYTHON_BIN"

# Check node & npm
if ! command -v npm &>/dev/null; then
    echo "[ERROR] Node.js & npm are required but were not found."
    exit 1
fi

echo "[INFO] Using Node: $(node -v) / npm: $(npm -v)"

# Ensure frontend dependencies are installed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# Ensure uploads and reports directories exist
mkdir -p "$BACKEND_DIR/uploads" "$BACKEND_DIR/reports"

# Cleanup function on Ctrl+C
cleanup() {
    echo ""
    echo "[INFO] Shutting down CiteVerify servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "[INFO] Shutdown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "[INFO] Starting FastAPI Backend on http://127.0.0.1:8000..."
(
    cd "$BACKEND_DIR"
    export PYTHONPATH="."
    "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) &
BACKEND_PID=$!

# Start frontend
echo "[INFO] Starting Vite Frontend on http://127.0.0.1:5173..."
(
    cd "$FRONTEND_DIR"
    npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "============================================================"
echo " CiteVerify is running!"
echo " Backend API:     http://127.0.0.1:8000 (Docs: /docs)"
echo " Frontend App:    http://127.0.0.1:5173"
echo " Press Ctrl+C to stop both servers."
echo "============================================================"
echo ""

wait
