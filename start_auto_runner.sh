#!/bin/bash
# Launches auto_runner.py in the background
# Usage: bash start_auto_runner.sh

cd "$(dirname "$0")"

nohup python3 auto_runner.py >> data/auto_runner.log 2>&1 &
echo $! > data/auto_runner.pid

echo "✅ Auto runner started (PID: $(cat data/auto_runner.pid))"
echo "   Checking the inbox based on the interval set in config.json"
echo ""
echo "   To see activity:  tail -f data/auto_runner.log"
echo "   To stop it:       bash stop_auto_runner.sh"
