# Tools

`src/tools/*.py` are CLI entrypoints. Implementation code lives in
`src/macos_githubprojects/`; generated outputs live in `src/generated/`.

## update_projects_dashboard

Génère:

- `src/generated/projects.md` (liste des projets dans `PROJECTS/`)
- `src/generated/dashboard-projets.html` (dashboard HTML avec recherche + filtres + statut git)

Run:

```bash
python3 src/tools/update_projects_dashboard.py
```

## projects_hub

Hub (dashboard / tags Finder / icônes Finder):

```bash
python3 src/script_hub.py
python3 src/tools/projects_hub.py dashboard
python3 src/tools/projects_hub.py tags --dry-run
python3 src/tools/projects_hub.py tags
python3 src/tools/projects_hub.py icons --dry-run
python3 src/tools/projects_hub.py icons      # writes (passes --apply)
python3 src/tools/projects_hub.py all
python3 src/tools/projects_hub.py all --icons
```
