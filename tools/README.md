# Tools

## update_projects_dashboard

Génère:

- `projects.md` (liste des projets dans `PROJECTS/`)
- `dashboard-projets.html` (dashboard HTML avec recherche + filtres + statut git)

Run:

```bash
python3 tools/update_projects_dashboard.py
```

## projects_hub

Hub (dashboard / tags Finder / icônes Finder):

```bash
python3 tools/projects_hub.py dashboard
python3 tools/projects_hub.py tags --dry-run
python3 tools/projects_hub.py tags
python3 tools/projects_hub.py icons --dry-run
python3 tools/projects_hub.py icons      # writes (passes --apply)
python3 tools/projects_hub.py all
python3 tools/projects_hub.py all --icons
```
