#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd)
    return int(p.returncode)


def _py(script_name: str) -> list[str]:
    return [sys.executable, str(REPO_ROOT / "tools" / script_name)]


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="projects_hub",
        description="Hub: regenerate dashboard, auto-tag Finder, auto-icon Finder folders.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("dashboard", help="Regenerate projects.md + dashboard-projets.html")

    p_tags = sub.add_parser("tags", help="Apply Finder tags to PROJECTS/* based on git status")
    p_tags.add_argument("--dry-run", action="store_true")
    p_tags.add_argument("--no-purge", action="store_true")

    p_icons = sub.add_parser("icons", help="Apply Finder custom icons to PROJECTS/* based on git status")
    p_icons.add_argument("--dry-run", action="store_true")
    p_icons.add_argument("--remove", action="store_true")
    p_icons.add_argument("--size", type=int, default=256)
    p_icons.add_argument("--regen", action="store_true")

    p_all = sub.add_parser("all", help="dashboard + tags (+ icons optional)")
    p_all.add_argument("--icons", action="store_true", help="Also apply custom icons (needs fileicon)")
    p_all.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()

    if args.cmd == "dashboard":
        return _run(_py("update_projects_dashboard.py"))

    if args.cmd == "tags":
        cmd = _py("auto_tag_projects.py")
        if args.dry_run:
            cmd.append("--dry-run")
        if args.no_purge:
            cmd.append("--no-purge")
        return _run(cmd)

    if args.cmd == "icons":
        cmd = _py("auto_icon_projects.py")
        if args.remove:
            cmd.append("--remove")
        if args.regen:
            cmd.append("--regen")
        cmd += ["--size", str(args.size)]
        if args.dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--apply")
        return _run(cmd)

    if args.cmd == "all":
        rc = _run(_py("update_projects_dashboard.py"))
        if rc != 0:
            return rc
        cmd = _py("auto_tag_projects.py")
        if args.dry_run:
            cmd.append("--dry-run")
        rc = _run(cmd)
        if rc != 0:
            return rc
        if args.icons:
            cmd2 = _py("auto_icon_projects.py")
            if args.dry_run:
                cmd2.append("--dry-run")
            else:
                cmd2.append("--apply")
            return _run(cmd2)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
