#!/bin/bash

# Installation script for Macos_GithubProjects Hub
set -e

echo "🚀 Installing Project Hub Menu App..."

# 1. Ensure Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it from python.org or via brew install python"
    exit 1
fi

# 2. Install dependencies in a virtual environment
echo "📦 Setting up virtual environment..."
python3 -m venv .venv
./.venv/bin/pip install rumps

# 3. Make scripts executable
echo "🛠️ Setting permissions..."
chmod +x tools/update_projects_dashboard.py
chmod +x tools/menu_app.py

echo "✅ Installation complete!"
echo ""
echo "To launch the menu bar app, run:"
echo "./.venv/bin/python3 tools/menu_app.py"
echo ""
echo "Tip: To make it start at login, you can create a macOS LaunchAgent or use an app like 'AppCleaner' or 'LaunchControl'."
