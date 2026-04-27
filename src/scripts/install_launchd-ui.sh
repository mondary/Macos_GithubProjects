#!/bin/bash

# Alternative installation de launchd-ui si brew n'est pas disponible
# Téléchargement direct depuis GitHub

echo "🚲 Installation de launchd-ui..."

# Télécharger le script
curl -o launchd-ui https://raw.githubusercontent.com/johanandren/launchd-ui/master/launchd-ui

# Rendre exécutable
chmod +x launchd-ui

echo "✅ Installation terminée !"
echo ""
echo "📍 Pour lancer :"
echo "./launchd-ui"
echo ""
echo "🔗 L'interface web sera accessible à :"
echo "http://localhost:8080"
echo ""
echo "👥 Tu pourras voir ton Project Hub et gérer tous les services de lancement !"