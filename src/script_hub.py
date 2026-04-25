#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "src" / "tools"
DASHBOARD = REPO_ROOT / "src" / "generated" / "dashboard-projets.html"
PYTHON = REPO_ROOT / ".venv" / "bin" / "python3"


@dataclass(frozen=True)
class Action:
    key: str
    label: str
    command: list[str] | None = None
    open_path: Path | None = None
    background: bool = False


def _python() -> str:
    return str(PYTHON if PYTHON.exists() else Path(sys.executable))


def _actions() -> list[Action]:
    py = _python()
    return [
        Action("1", "🚀 Launch menu bar app", [py, str(TOOLS_DIR / "menu_app.py")], background=True),
        Action("2", "📊 Regenerate dashboard + projects.md", [py, str(TOOLS_DIR / "projects_hub.py"), "dashboard"]),
        Action("3", "🌐 Open dashboard in browser", open_path=DASHBOARD),
        Action("4", "🏷️ Finder tags dry-run", [py, str(TOOLS_DIR / "projects_hub.py"), "tags", "--dry-run"]),
        Action("5", "✅ Apply Finder tags", [py, str(TOOLS_DIR / "projects_hub.py"), "tags"]),
        Action("6", "🖼️ Finder icons dry-run", [py, str(TOOLS_DIR / "projects_hub.py"), "icons", "--dry-run"]),
        Action("7", "🎨 Apply Finder icons", [py, str(TOOLS_DIR / "projects_hub.py"), "icons"]),
        Action("8", "🧪 Run dashboard + tags dry-run", [py, str(TOOLS_DIR / "projects_hub.py"), "all", "--dry-run"]),
    ]


def _run(action: Action) -> int:
    if action.open_path:
        if not action.open_path.exists():
            print(f"Missing: {action.open_path}")
            return 1
        webbrowser.open(f"file://{action.open_path.resolve()}")
        return 0

    if not action.command:
        return 0

    if action.background:
        subprocess.Popen(
            action.command,
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("Launched in background.")
        return 0

    return subprocess.run(action.command, cwd=REPO_ROOT, check=False).returncode


def main() -> int:
    actions = _actions()
    by_key = {action.key: action for action in actions}

    while True:
        print()
        print("🧭 Macos_GithubProjects script hub")
        print("----------------------------------")
        for action in actions:
            print(f"{action.key}. {action.label}")
        print("q. 👋 Quit")
        choice = input("> ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return 0

        action = by_key.get(choice)
        if not action:
            print("Unknown choice.")
            continue

        rc = _run(action)
        if rc != 0:
            print(f"Failed with exit code {rc}.")


if __name__ == "__main__":
    raise SystemExit(main())
