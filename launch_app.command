#!/bin/bash
# Launcher for Macos_GithubProjects menu bar app

cd "$(dirname "$0")"

# Kill any existing instance
pkill -f "menu_app.py" 2>/dev/null

# Launch the menu app
python3 src/macos_githubprojects/menu_app.py &
