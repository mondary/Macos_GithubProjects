#!/bin/bash

# Créer une application visible pour les Options de démarrage
# Usage: ./create_startup_app.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="ProjectHub Launcher"
APP_DIR="$HOME/Applications/$APP_NAME.app"

echo "🚀 Création de l'application visible pour le démarrage..."

# Créer la structure de l'application
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Créer l'icône (si une icône existe)
if [ -f "$SCRIPT_DIR/icon.png" ]; then
    cp "$SCRIPT_DIR/icon.png" "$APP_DIR/Contents/Resources/icon.icns"
fi

# Créer le binaire exécutable
cat > "$APP_DIR/Contents/MacOS/$APP_NAME" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && cd Resources && pwd)"
cd "/Users/clm/Documents/GitHub/PROJECTS/Macos_GithubProjects"
exec ./.venv/bin/python3 tools/menu_app.py
EOF

chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"

# Créer le fichier Info.plist
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>ProjectHub Launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.user.projecthublauncher</string>
    <key>CFBundleName</key>
    <string>ProjectHub Launcher</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo "✅ Application créée : $APP_DIR"
echo ""
echo "📍 Glisse maintenant '$APP_NAME.app' dans :"
echo "   Système → Préférences → Utilisateurs & Groupes → Options de connexion → Objets de connexion"
echo ""
echo "L'application apparaîtra dans les Options de démarrage mais restera invisible dans la barre des tâches !"