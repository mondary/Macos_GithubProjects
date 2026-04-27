#!/bin/bash

# Script pour nettoyer et organiser proprement le projet
# Usage: ./cleanup_organization.sh

echo "🧹 Nettoyage et organisation du projet..."

# Créer la structure de dossier propre
mkdir -p src/scripts/
mkdir -p src/docs/

# Déplacer les scripts d'installation et utilitaires
echo "📁 Déplacement des scripts..."
for file in setup_launch_agent.sh create_startup_app.sh install_launchd-ui.sh \
           list_launch_services.sh simple_launch_monitor.py download_launchd-ui.py \
           simple_launcher.sh start_at_login.scpt setup_app.py; do
    if [ -f "$file" ]; then
        mv "$file" src/scripts/
        echo "   ✅ $file → src/scripts/"
    fi
done

# Déplacer les fichiers de config
echo "⚙️  Déplacement des fichiers de configuration..."
for file in com.user.macosgithubprojects.plist run_menu_app.sh; do
    if [ -f "$file" ]; then
        mv "$file" src/scripts/
        echo "   ✅ $file → src/scripts/"
    fi
done

# Déplacer les docs README
echo "📚 Déplacement des documentation..."
if [ -f "README_en.md" ]; then
    mv "README_en.md" src/docs/
    echo "   ✅ README_en.md → src/docs/"
fi

# Déplacer le script lui-même dans src/scripts
echo "🔄 Déplacement du script d'organisation..."
mv "$0" src/scripts/cleanup_organization.sh
echo "   ✅ cleanup_organization.sh → src/scripts/"

# Vérifier que tout est bien placé
echo ""
echo "📋 Structure finale :"
echo "📂 /"
echo "├── src/"
echo "│   ├── macos_githubprojects/"
echo "│   ├── tools/"  
echo "│   ├── scripts/"
echo "│   │   ├── setup_launch_agent.sh"
echo "│   │   ├── simple_launch_monitor.py"
echo "│   │   └── cleanup_organization.sh"
echo "│   ├── docs/"
echo "│   │   └── README_en.md"
echo "│   └── generated/"
echo "├── README.md"
echo "├── .gitignore"
echo "└── icon.png"

echo ""
echo "✅ Nettoyage terminé !"
echo ""
echo "📍 Les chemins dans le plist doivent maintenant être mis à jour :"