#!/bin/bash

# Start Corvelli Backend Services

echo "Starting Corvelli Backend..."

# Check if Python connection server is running
if ! lsof -ti:5000 > /dev/null 2>&1; then
    echo "Starting Python Connection Server on port 5000..."
    cd "$(dirname "$0")"
    python3 connection_server.py &
    PYTHON_PID=$!
    echo "   Python server PID: $PYTHON_PID"
    sleep 2
else
    echo "[OK] Python Connection Server already running on port 5000"
fi

# Check if Node.js server is running
if ! lsof -ti:3000 > /dev/null 2>&1; then
    echo "Starting Node.js Server on port 3000..."
    cd "$(dirname "$0")"
    node server.js &
    NODE_PID=$!
    echo "   Node.js server PID: $NODE_PID"
else
    echo "[OK] Node.js Server already running on port 3000"
fi

echo ""
echo "Backend services ready!"
echo "   Python Connection Server: http://localhost:5000"
echo "   Node.js API Server: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
wait
