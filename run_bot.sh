#!/bin/bash
# chmod +x run_bot.sh allow permission first
# Navigate to the script's directory
cd "$(dirname "$0")"

# Check if uv is available in the environment, use it to run bot.py
if command -v uv &> /dev/null; then
    echo "Starting Telegram Bot using uv..."
    uv run bot.py
else
    echo "Starting Telegram Bot using python..."
    python bot.py
fi
