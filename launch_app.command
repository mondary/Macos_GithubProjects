#!/bin/bash
# Launcher for Macos_GithubProjects menu bar app

cd /Users/clm/Documents/GitHub/PROJECTS/Macos_GithubProjects

# Kill any existing instance
pkill -f "menu_app.py" 2>/dev/null

# Wait a moment for processes to terminate
sleep 1

# Launch the menu app
echo "Launching menu bar app..."
./.venv/bin/python3 src/app/menu_app.py &

# Keep terminal open briefly to see any errors
sleep 2
echo "Menu bar app launched. You can close this window."
