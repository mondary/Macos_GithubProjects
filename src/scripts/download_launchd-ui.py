#!/usr/bin/env python3

import urllib.request
import urllib.error
import os

# URL du script launchd-ui
url = "https://raw.githubusercontent.com/johanandren/launchd-ui/master/launchd-ui"
output_file = "launchd-ui"

print("🚲 Téléchargement de launchd-ui...")

try:
    # Télécharger le fichier
    urllib.request.urlretrieve(url, output_file)
    
    # Rendre exécutable
    os.chmod(output_file, 0o755)
    
    print("✅ Installation terminée !")
    print("")
    print("📍 Pour lancer :")
    print(f"./{output_file}")
    print("")
    print("🔗 L'interface web sera accessible à :")
    print("http://localhost:8080")
    print("")
    print("👥 Tu pourras voir ton Project Hub et gérer tous les services de lancement !")
    
except Exception as e:
    print(f"❌ Erreur de téléchargement : {e}")
    print("Tu peux peut-être télécharger manuellement depuis :")
    print(url)