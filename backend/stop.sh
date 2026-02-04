#!/bin/bash

# Kill all Corvelli backend processes

echo "Stopping Corvelli services..."

# Kill Python server
if lsof -ti:5000 > /dev/null 2>&1; then
    echo "Stopping Python Connection Server..."
    kill $(lsof -ti:5000) 2>/dev/null
fi

# Kill Node.js server
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "Stopping Node.js Server..."
    kill $(lsof -ti:3000) 2>/dev/null
fi

echo "All services stopped."
