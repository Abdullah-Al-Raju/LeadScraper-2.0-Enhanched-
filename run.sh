#!/usr/bin/env bash
set -e

echo "==================================================="
echo "            LeadScraper Falcon Launcher"
echo "==================================================="
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.10+ using your package manager."
    exit 1
fi

# 2. Setup Virtual Environment if missing
if [ ! -d "venv" ]; then
    echo "[INFO] Setting up your virtual environment for the first time..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[INFO] Installing required dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 3. Run the Scraper (opens interactive menu)
python3 main.py
