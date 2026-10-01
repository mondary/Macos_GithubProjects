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


PROJECTS_DIR = projects_dir()
ROOT_HUB = PROJECTS_DIR.parent
