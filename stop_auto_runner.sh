#!/bin/bash
# Stops the auto_runner.py background process
# Usage: bash stop_auto_runner.sh

PID_FILE="data/auto_runner.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill "$PID" 2>/dev/null; then
        echo "✅ Auto runner stopped (PID: $PID)"
    else
        echo "⚠️  Process $PID was not running."
    fi
    rm "$PID_FILE"
else
    echo "⚠️  No PID file found. Trying pkill..."
    pkill -f auto_runner.py && echo "✅ Stopped." || echo "❌ No process found."
fi
