from __future__ import annotations

import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def projects_dir() -> Path:
    """Return the folder that contains all local projects."""
    override = os.environ.get("MACOS_GITHUBPROJECTS_PROJECTS_DIR")
    if override:
        return Path(override).expanduser().resolve()

    for candidate in (REPO_ROOT.parent, *REPO_ROOT.parents):
        if (candidate / "mondary").is_dir():
            return candidate

    return REPO_ROOT.parent


def source_dirs() -> list[Path]:
    """Return every folder scanned for projects.

    The management folder (mondary + meta tools) plus the classic
    PROJECTS folder when it lives next to it.
    """
    dirs = [PROJECTS_DIR]
    classic = PROJECTS_DIR.parent / "PROJECTS"
    if classic.is_dir() and classic.resolve() != PROJECTS_DIR.resolve():
        dirs.append(classic)
    return dirs


PROJECTS_DIR = projects_dir()
SOURCE_DIRS = source_dirs()
ROOT_HUB = PROJECTS_DIR.parent
