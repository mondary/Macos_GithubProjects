#!/bin/bash

# Script pour lister tous les services de lancement (LaunchAgents et LaunchDaemons)
# Usage: ./list_launch_services.sh

echo "🚀 Liste des services de lancement"
echo "=================================="
echo ""

echo "📱 LaunchAgents (pour ton utilisateur uniquement) :"
echo "-----------------------------------------------"
echo "Installés :"
ls -la ~/Library/LaunchAgents/ | head -20
echo ""
echo "Actifs :"
launchctl list | grep user | head -10
echo ""

echo "🖥️  LaunchDaemons (système) :"
echo "------------------------------"
echo "Installés (/Library/LaunchDaemons/) :"
ls -la /Library/LaunchDaemons/ | head -20
echo ""

echo "Apple (/System/Library/LaunchDaemons/) :"
ls -la /System/Library/LaunchDaemons/ | grep -E "\.(plist)$" | head -10
echo ""

echo "🔍 Services actifs système :"
launchctl list | grep -v user | head -10
echo ""

echo "📊 Ton Project Hub spécifiquement :"
echo "---------------------------------"
echo "Statut :"
launchctl list | grep com.user.macosgithubprojects
echo ""
echo "Fichier de configuration :"
ls -la ~/Library/LaunchAgents/com.user.macosgithubprojects.plist