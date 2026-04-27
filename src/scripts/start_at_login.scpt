#!/usr/bin/osascript

# Script AppleScript pour démarrer le Project Hub au démarrage
# À placer dans les éléments de démarrage de macOS

on run
    tell application "Terminal"
        activate
        do script "cd '/Users/clm/Documents/GitHub/PROJECTS/Macos_GithubProjects' && ./.venv/bin/python3 tools/menu_app.py"
    end tell
end run