#!/bin/bash

# Wrapper simple pour le lancement du Project Hub
# Ce script est conçu pour être appelé par launchd

cd "/Users/clm/Documents/GitHub/PROJECTS/Macos_GithubProjects"
exec ./.venv/bin/python3 tools/menu_app_improved.py "$@"