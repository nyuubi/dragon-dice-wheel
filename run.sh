#!/bin/bash
echo "==================================================="
echo "  Setting up environment & Starting Dragon Dice Wheel..."
echo "==================================================="

# Check if Python virtual environment exists, if not create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate environment and install dependencies
source .venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Open browser based on OS
echo ""
echo "Launching game server at http://127.0.0.1:8000 ..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://127.0.0.1:8000
else
    xdg-open http://127.0.0.1:8000 2>/dev/null || true
fi

# Launch server
python -m uvicorn app:app --reload --port 8000