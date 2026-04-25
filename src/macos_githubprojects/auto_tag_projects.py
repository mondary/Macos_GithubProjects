#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT.parent

EXCLUDE_NAMES = {".git", "node_modules", ".DS_Store"}

# Finder tag colors: 0..7 (Apple internal). Works on modern macOS.
COLOR_GRAY = 0
COLOR_GREEN = 1
COLOR_PURPLE = 2
COLOR_BLUE = 3
COLOR_YELLOW = 4
COLOR_RED = 5
COLOR_ORANGE = 6


XATTR_TAGS_KEY = "com.apple.metadata:_kMDItemUserTags"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _is_excluded(name: str) -> bool:
    if not name:
        return True
    if name in EXCLUDE_NAMES:
        return True
    if name.startswith(".") or name.startswith("-"):
        return True
    return False


@dataclass(frozen=True)
class GitInfo:
    is_git: bool
    dirty: bool
    has_remote: bool
    remote_url: str | None


def _git_info(project_path: Path) -> GitInfo:
    cwd = project_path if project_path.is_dir() else project_path.parent
    inside = _run(["git", "-C", str(cwd), "rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        return GitInfo(False, False, False, None)

    porcelain = _run(["git", "-C", str(cwd), "status", "--porcelain"])
    dirty = bool(porcelain.stdout.strip())

    remote_url = None
    has_remote = False
    origin = _run(["git", "-C", str(cwd), "remote", "get-url", "origin"])
    if origin.returncode == 0 and origin.stdout.strip():
        remote_url = origin.stdout.strip()
        has_remote = True
    else:
        remotes = _run(["git", "-C", str(cwd), "remote", "-v"])
        if remotes.returncode == 0 and remotes.stdout.strip():
            first = remotes.stdout.splitlines()[0].strip()
            parts = first.split()
            if len(parts) >= 2:
                remote_url = parts[1]
                has_remote = True

    return GitInfo(True, dirty, has_remote, remote_url)


def _finder_read_tags(path: Path) -> list[str]:
    proc = _run(["xattr", "-px", XATTR_TAGS_KEY, str(path)])
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        raw = bytes.fromhex(proc.stdout.strip())
        value = plistlib.loads(raw)
        if isinstance(value, list):
            return [str(x) for x in value]
    except Exception:
        return []
    return []


def _finder_write_tags(path: Path, tags: list[str], *, dry_run: bool) -> None:
    data = plistlib.dumps(tags, fmt=plistlib.FMT_BINARY)
    if dry_run:
        return
    _run(["xattr", "-wx", XATTR_TAGS_KEY, data.hex(), str(path)])


def _tag(name: str, color: int | None) -> str:
    # Finder stores "Name\n<color>" (color omitted means no color). Use explicit color.
    if color is None:
        return name
    return f"{name}\n{color}"


def _strip_git_tags(existing: list[str]) -> list[str]:
    out: list[str] = []
    for t in existing:
        base = t.split("\n", 1)[0].strip().lower()
        if base.startswith("git:") or base.startswith("github:"):
            continue
        out.append(t)
    return out


def _desired_git_tags(info: GitInfo) -> list[str]:
    tags: list[str] = []
    if not info.is_git:
        tags.append(_tag("git:no-git ⛔︎", COLOR_GRAY))
        return tags

    if not info.has_remote:
        tags.append(_tag("git:no-remote ☁︎⨯", COLOR_ORANGE))
    if info.dirty:
        tags.append(_tag("git:dirty ⚠︎", COLOR_YELLOW))
    else:
        tags.append(_tag("git:clean ✓", COLOR_GREEN))

    if info.remote_url and "github.com" in info.remote_url.lower():
        tags.append(_tag("github:remote ⌁", COLOR_GRAY))

    return tags


def main() -> None:
    ap = argparse.ArgumentParser(description="Auto-tag Finder folders in PROJECTS/ based on git status.")
    ap.add_argument("--dry-run", action="store_true", help="No writes; just prints planned changes.")
    ap.add_argument("--no-purge", action="store_true", help="Do not remove existing git:* / github:* tags.")
    args = ap.parse_args()

    if not PROJECTS_DIR.exists():
        raise SystemExit(f"Missing: {PROJECTS_DIR}")

    changed = 0
    scanned = 0
    for child in sorted(PROJECTS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if _is_excluded(child.name):
            continue
        scanned += 1

        existing = _finder_read_tags(child)
        base = existing if args.no_purge else _strip_git_tags(existing)

        info = _git_info(child)
        desired = base + _desired_git_tags(info)

        if existing == desired:
            continue

        changed += 1
        print(f"{child.name}:")
        print(f"  was: {existing}")
        print(f"  now: {desired}")
        _finder_write_tags(child, desired, dry_run=args.dry_run)

    print(f"done. scanned={scanned} changed={changed} dry_run={bool(args.dry_run)}")


if __name__ == "__main__":
    main()
