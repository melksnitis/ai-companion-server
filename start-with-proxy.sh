#!/bin/bash
# Start with OpenRouter Model Proxy to force all API calls to use free model

set -e

# Load environment
source .env 2>/dev/null || true

# Cleanup function
cleanup() {
    echo "[START] Shutting down..."
    kill $PROXY_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

VENV_PYTHON="/opt/ai-companion-server/.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    PYTHON_BIN_DEFAULT="$VENV_PYTHON"
else
    PYTHON_BIN_DEFAULT="$(command -v python3 || command -v python)"
fi
PYTHON_BIN="${PYTHON_BIN:-$PYTHON_BIN_DEFAULT}"

# Start the proxy in background
echo "[START] Starting OpenRouter Model Proxy on port 9999 using ${PYTHON_BIN}..."
"${PYTHON_BIN}" scripts/openrouter_proxy.py &
PROXY_PID=$!
sleep 2

# Check if proxy started
if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "[START] ERROR: Proxy failed to start"
    exit 1
fi

# Point AgentService to our proxy
export OPENROUTER_PROXY_URL="http://localhost:9999"
echo "[START] OPENROUTER_PROXY_URL=$OPENROUTER_PROXY_URL"

# Start main server
echo "[START] Starting main FastAPI server on port 8000..."
"${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Cleanup
cleanup
