# Macos_GithubProjects

Outil de gestion de projets pour macOS avec menu bar app et dashboard HTML.

## Fonctionnalités

- **Menu Bar App** : Accès rapide à tous vos projets depuis la barre de menu macOS
- **Dashboard HTML** : Interface web avec recherche, filtres et statut Git
- **Icônes personnalisées** : Affichage des icônes de projets (icon.png)
- **Statut Git** : Indicateur visuel pour les dépôts GitHub
- **Ouverture rapide** : Ouvrez les projets directement dans VS Code

## Menu Bar App

L'application menu bar permet d'accéder rapidement à tous vos projets.

### Lancement

Double-cliquez sur `launch_app.command` ou utilisez :

```bash
./.venv/bin/python3 src/app/menu_app.py &
```

### Fonctionnalités du menu

- **Update Dashboard** : Met à jour la liste des projets et le dashboard HTML
- **Open Dashboard** : Ouvre le dashboard HTML dans le navigateur
- **Open Finder** : Ouvre le dossier des projets dans Finder
- **Quick Actions** :
  - 🏠 Local : Ouvre le dossier des projets
  - 🌐 GitHub : Ouvre GitHub.com
  - 🗂️ Finder : Ouvre le dossier dans Finder
- **Liste des projets** : Cliquez pour ouvrir dans VS Code
  - Icône du projet à gauche
  - Logo GitHub si le projet a un dépôt Git
- **Quit** : Ferme l'application

## Dashboard HTML

Le dashboard HTML est généré automatiquement et inclut :

- Recherche instantanée
- Filtres par groupe (Chrome_, CLI_, Macos_, Web_, etc.)
- Filtres par statut Git (Clean, Dirty, No Remote, No Git)
- Informations détaillées sur chaque projet
- Liens rapides (Local, GitHub, Finder, VS Code)

### Lancement

Le dashboard est généré dans `generated/dashboard-projets.html`.

## Structure

```
Macos_GithubProjects/
├── src/
│   ├── app/
│   │   └── menu_app.py          # Wrapper menu bar app
│   ├── macos_githubprojects/
│   │   ├── menu_app.py          # Menu bar app principale
│   │   ├── update_projects_dashboard.py  # Script de mise à jour
│   │   └── github-logo.png      # Logo GitHub officiel
│   └── generated/
│       ├── dashboard-projets.html  # Dashboard HTML généré
│       └── projects.md          # Liste des projets en markdown
├── generated/
│   └── dashboard-projets.html   # Dashboard actuel (utilisé par l'app)
└── launch_app.command           # Launcher pour double-clic
```

## Développement

### Environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Scripts

```bash
# Mettre à jour le dashboard
python3 src/macos_githubprojects/update_projects_dashboard.py

# Lancer l'app menu bar
./.venv/bin/python3 src/app/menu_app.py &
```

## Statut Git

Les projets affichent un indicateur GitHub s'ils ont :
- Un dépôt Git initialisé
- Un remote configuré (origin)

Les indicateurs dans le dashboard montrent :
- 🟢 Clean : Dépôt Git propre avec remote
- 🟡 Dirty : Modifications non commitées
- 🟡 No Remote : Pas de remote configuré
- 🔴 No Git : Pas un dépôt Git
