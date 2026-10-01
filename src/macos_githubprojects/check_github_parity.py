#!/usr/bin/env python3
"""Vérifie la parité entre les projets locaux (PROJECTS/*) et les dépôts GitHub.

Compare via les remotes git (source de vérité) plutôt que par nom de dossier.
Usage: ./check_github_parity.py [--user mondary]
"""
import argparse
import json
import re
import subprocess
import urllib.request
from pathlib import Path

try:
    from macos_githubprojects.paths import PROJECTS_DIR
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from macos_githubprojects.paths import PROJECTS_DIR


def github_repos(user: str) -> list[str]:
    token = github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = "https://api.github.com/user/repos?per_page=100&type=all"
    else:
        url = f"https://api.github.com/users/{user}/repos?per_page=100&type=all"

    repos: list[dict] = []
    while url:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
            if isinstance(data, list):
                repos.extend(data)
            link = r.headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else ""
        if not token:
            break

    return sorted(repo["name"] for repo in repos if not repo.get("archived"))


def github_token() -> str | None:
    proc = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def local_remotes() -> tuple[dict[str, str], list[str]]:
    remotes: dict[str, str] = {}
    no_remote: list[str] = []
    for p in iter_local_projects():
        d = p.name
        if d.startswith(".") or not p.is_dir():
            continue
        r = subprocess.run(
            ["git", "-C", str(p), "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        url = r.stdout.strip()
        if r.returncode == 0 and url:
            name = url.split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            remotes[d] = name
        else:
            no_remote.append(d)
    return remotes, no_remote


def is_git_repo(path: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return r.returncode == 0 and r.stdout.strip().lower() == "true"


def iter_local_projects() -> list[Path]:
    paths: list[Path] = []
    for child in sorted(PROJECTS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if child.name.startswith(".") or not child.is_dir():
            continue
        nested_git_projects: list[Path] = []
        if "+++" in child.name and not is_git_repo(child):
            nested_git_projects = [
                nested
                for nested in sorted(child.iterdir(), key=lambda p: p.name.lower())
                if not nested.name.startswith(".") and nested.is_dir() and is_git_repo(nested)
            ]
        if nested_git_projects:
            paths.extend(nested_git_projects)
        else:
            paths.append(child)
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", default="mondary")
    args = ap.parse_args()

    gh = github_repos(args.user)
    gh_set = {g.lower() for g in gh}
    remotes, no_remote = local_remotes()
    linked = {n.lower() for n in remotes.values()}

    print(f"Local total            : {len(no_remote) + len(remotes)}")
    print(f"  avec remote GitHub   : {len(remotes)}")
    print(f"  SANS remote          : {len(no_remote)}")
    print(f"GitHub total ({args.user}): {len(gh)}")
    print(f"GitHub liés au local   : {len(linked & gh_set)}")
    print(f"\n=== LOCAUX sans remote ({len(no_remote)}) ===")
    for d in no_remote:
        print(f"  {d}")
    print(f"\n=== GitHub sans dossier local ({len(gh_set - linked)}) ===")
    for g in sorted(gh_set - linked):
        print(f"  {[x for x in gh if x.lower() == g][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
