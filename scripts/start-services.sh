#!/bin/bash
set -e

echo "🚀 Starting AI Companion Server with Claude Code Router..."

# Start Claude Code Router in the background
echo "📡 Starting Claude Code Router on port 3000..."
ccr code &
ROUTER_PID=$!

# Wait a moment for router to initialize
sleep 2

# Start FastAPI server
echo "🐍 Starting FastAPI server on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Function to handle shutdown
shutdown() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $ROUTER_PID 2>/dev/null || true
    kill $FASTAPI_PID 2>/dev/null || true
    exit 0
}

# Trap signals
trap shutdown SIGTERM SIGINT

echo "✅ Services started:"
echo "   - FastAPI:           http://0.0.0.0:8000"
echo "   - Claude Code Router: http://0.0.0.0:3000"
echo ""
echo "Press Ctrl+C to stop"

# Wait for both processes
wait
