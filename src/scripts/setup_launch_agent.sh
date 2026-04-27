#!/bin/bash

# Script pour installer le Project Hub comme LaunchAgent
# Usage: ./setup_launch_agent.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_PLIST="$SCRIPT_DIR/com.user.macosgithubprojects.plist"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
LAUNCH_AGENT_PLIST="$LAUNCH_AGENT_DIR/com.user.macosgithubprojects.plist"

echo "🚀 Installation du Project Hub au démarrage..."

# Créer le dossier LaunchAgents s'il n'existe pas
mkdir -p "$LAUNCH_AGENT_DIR"

# Copier le fichier plist
cp "$SERVICE_PLIST" "$LAUNCH_AGENT_PLIST"

# Charger le service
launchctl load "$LAUNCH_AGENT_PLIST"

echo "✅ Installation terminée !"
echo ""
echo "L' application se lancera automatiquement au démarrage."
echo ""
echo "Pour la tester maintenant :"
echo "launchctl start com.user.macosgithubprojects"
echo ""
echo "Pour désinstaller :"
echo "launchctl unload \"$LAUNCH_AGENT_PLIST\""
echo "rm \"$LAUNCH_AGENT_PLIST\""