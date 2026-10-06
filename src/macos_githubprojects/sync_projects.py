#!/usr/bin/env python3
"""pkprojects-sync — regenerate all views and auto-push the profile README.

Runs the full generation (dashboard, library, hub, comparison, profile,
mondary README) then commits + pushes mondary/README.md when it changed.
Designed for launchd (com.user.pkprojects-sync) or manual runs.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_REPO = REPO_ROOT.parent / "mondary"
LOG = Path.home() / "Library" / "Logs" / "pkprojects-sync.log"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {msg}\n")


def run(cmd: list[str], cwd: Path | None = None) -> bool:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        log(result.stdout.strip())
    if result.returncode != 0 and result.stderr.strip():
        log("ERROR: " + result.stderr.strip())
    return result.returncode == 0


def main() -> int:
    log("sync start")

    generator = REPO_ROOT / "src" / "macos_githubprojects" / "update_projects_dashboard.py"
    if not run([sys.executable, str(generator)]):
        log("generation FAILED")
        return 1
    log("generation ok")

    if (PROFILE_REPO / ".git").is_dir():
        # git diff --quiet exits 1 when there IS a diff.
        if not run(["git", "diff", "--quiet", "--", "README.md"], cwd=PROFILE_REPO):
            run(["git", "add", "README.md"], cwd=PROFILE_REPO)
            run(["git", "commit", "-m", "Auto-sync: regenerate profile README"], cwd=PROFILE_REPO)
            if run(["git", "push", "origin", "main"], cwd=PROFILE_REPO):
                log("profile README pushed")
            else:
                log("push FAILED")
                return 1
        else:
            log("profile README unchanged")
    else:
        log("profile repo missing, skip push")

    log("sync done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
