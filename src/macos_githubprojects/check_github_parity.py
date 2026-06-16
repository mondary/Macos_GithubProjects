#!/usr/bin/env python3
"""Vérifie la parité entre les projets locaux (PROJECTS/*) et les dépôts GitHub.

Compare via les remotes git (source de vérité) plutôt que par nom de dossier.
Usage: ./check_github_parity.py [--user mondary]
"""
import argparse
import json
import os
import subprocess
import urllib.request

PROJECTS_DIR = "/Users/clm/Documents/GitHub/PROJECTS"


def github_repos(user: str) -> list[str]:
    url = f"https://api.github.com/users/{user}/repos?per_page=100&type=all"
    with urllib.request.urlopen(url) as r:
        data = json.load(r)
    return sorted(repo["name"] for repo in data)


def local_remotes() -> tuple[dict[str, str], list[str]]:
    remotes: dict[str, str] = {}
    no_remote: list[str] = []
    for d in sorted(os.listdir(PROJECTS_DIR)):
        p = os.path.join(PROJECTS_DIR, d)
        if d.startswith(".") or not os.path.isdir(p):
            continue
        r = subprocess.run(
            ["git", "-C", p, "remote", "get-url", "origin"],
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
