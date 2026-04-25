# Macos_GithubProjects

![Project icon](icon.png)

[🇫🇷 FR](README.md) · [🇬🇧 EN](README_en.md)

✨ Hub centralisant des outils d'automatisation et des compétences spécialisées pour agents IA.

## ✅ Fonctionnalités

- **Compétences pour Agents IA** : Bibliothèque de skills spécialisés dans `.agent/-skills` (Design, Git, Publication, Rédaction).
- **Outils d'Automatisation** : Tout le projet opérationnel vit dans `src/` : code, wrappers CLI, installation et fichiers générés.
- **Workflows de Publication** : Procédures automatisées pour VS Code Marketplace, Chrome Web Store, MacOS (Sparkle) et WordPress.
- **Infrastructure** : Automatisation de la redirection de domaines (OVH).

## 🧠 Utilisation

### Outils
Le code applicatif vit dans `src/macos_githubprojects/`. Les scripts `src/tools/*.py` sont les points d'entrée CLI :
- `src/script_hub.py` : Menu interactif pour lancer les scripts.
- `projects_hub.py` : Gestion du hub de projets.
- `update_projects_dashboard.py` : Mise à jour du tableau de bord.

```bash
# Menu interactif principal
./.venv/bin/python3 src/script_hub.py

# Générer le dashboard HTML et le Markdown
./.venv/bin/python3 src/tools/projects_hub.py dashboard

# Lancer l'app menu bar macOS
./.venv/bin/python3 src/tools/menu_app.py
```

Fichiers générés :
- `src/generated/dashboard-projets.html`
- `src/generated/projects.md`

### Skills (`.agent/-skills/`)
Ces fichiers Markdown sont conçus pour être injectés dans le contexte d'un agent IA pour lui fournir des instructions précises sur des tâches complexes.

## 🧾 Changelog

- 1.0.0 : Initial release.

## 🔗 Liens

- EN README : [README_en.md](README_en.md)
