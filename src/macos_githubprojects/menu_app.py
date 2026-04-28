#!/usr/bin/env python3
# Ce fichier est gardé pour compatibilité, utilisez plutôt app/menu_app.py
import sys
import platform
import subprocess
import threading
import json
import re
import webbrowser
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import urllib.parse

try:
    import rumps
except ImportError:
    print("Installing rumps...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rumps"])
    import rumps

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT.parent
LAUNCHER_HOST = "127.0.0.1"
LAUNCHER_PORT = 37645
DASHBOARD_PATH = REPO_ROOT / "src" / "generated" / "dashboard-projets.html"
UPDATE_SCRIPT = REPO_ROOT / "src" / "macos_githubprojects" / "update_projects_dashboard.py"

# Default icons based on project type
DEFAULT_ICONS = {
    "Chrome_": "🌐",
    "CLI_": "💻",
    "Macos_": "🍎",
    "Web_": "🌍",
    "WP_": "📝",
    "VS_": "📦",
    "RC_": "⚙️",
}


def project_count() -> int:
    try:
        REPO_ROOT = Path(__file__).resolve().parents[2]
        PROJECTS_DIR = REPO_ROOT.parent
        DASHBOARD_PATH = REPO_ROOT / "src" / "generated" / "dashboard-projets.html"
        
        if DASHBOARD_PATH.exists():
            try:
                content = DASHBOARD_PATH.read_text(encoding="utf-8", errors="replace")
                match = re.search(
                    r'<script id="data" type="application/json">(.*?)</script>',
                    content,
                    re.S,
                )
                if match:
                    data = json.loads(match.group(1))
                    return len(data.get("projects", []))
            except (OSError, json.JSONDecodeError, TypeError):
                pass

        if PROJECTS_DIR.exists():
            count = sum(
                1
                for child in PROJECTS_DIR.iterdir()
                if child.name
                and child.name not in {".git", "node_modules", ".DS_Store"}
                and not child.name.startswith((".", "-"))
            )
            return count
    except Exception:
        pass
    
    return 0


def _open_vscode_new_window(path: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved.relative_to(PROJECTS_DIR.resolve())
    except (OSError, ValueError):
        return False

    cmd = ["code", "--new-window", str(resolved)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
    except OSError:
        pass

    fallback = [
        "open",
        "-na",
        "Visual Studio Code",
        "--args",
        "--new-window",
        str(resolved),
    ]
    return subprocess.run(fallback, capture_output=True, text=True, check=False).returncode == 0


class LauncherHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/open-vscode":
            self._send(404, b"not found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        raw_path = params.get("path", [""])[0]
        if not raw_path:
            self._send(400, b"missing path")
            return

        ok = _open_vscode_new_window(Path(raw_path))
        self._send(200 if ok else 400, b"ok" if ok else b"blocked")

    def log_message(self, *_):
        return

    def _send(self, status: int, body: bytes):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)


def start_launcher_server() -> None:
    def serve() -> None:
        try:
            server = ThreadingHTTPServer((LAUNCHER_HOST, LAUNCHER_PORT), LauncherHandler)
        except OSError:
            return
        server.serve_forever()

    threading.Thread(target=serve, daemon=True).start()


class ProjectHubApp(rumps.App):
    def __init__(self):
        super(ProjectHubApp, self).__init__(f"📁 {project_count()}")
        self.quick_actions_menu = rumps.MenuItem("Quick Actions")
        self.quick_actions_menu.menu = [
            rumps.MenuItem("🏠 Local", callback=self.open_local),
            rumps.MenuItem("🌐 GitHub", callback=self.open_github),
            rumps.MenuItem("🗂️ Finder", callback=self.open_finder),
        ]

        # Load projects from dashboard data
        projects = self._load_projects()

        # Build menu with projects
        menu_items = [
            rumps.MenuItem("Update Dashboard", callback=self.update_dashboard),
            None,  # Separator
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            None,  # Separator
            self.quick_actions_menu,
            None,  # Separator
        ]

        # Add projects to menu
        for project in projects:
            name = project.get("name", "Unknown")
            path = project.get("path", "")
            icon_path = project.get("iconPath", "")
            group = project.get("group", "")

            # Try to get custom icon from icon.png
            icon = None
            # First try to find icon.png in the project directory
            if path.startswith(".."):
                # Project in parent directory
                project_name = path.replace("../", "").strip("/")
                icon_full_path = (PROJECTS_DIR / project_name / "icon.png").resolve()
            elif path == ".":
                # Current repo
                icon_full_path = (REPO_ROOT / "icon.png").resolve()
            else:
                # Relative path in repo
                icon_full_path = (REPO_ROOT / path / "icon.png").resolve()

            if icon_full_path.exists():
                icon = str(icon_full_path)

            menu_items.append(rumps.MenuItem(name, callback=lambda _, p=path: self.open_project(p), icon=icon))

        # rumps adds "Quit" automatically, no need to add it manually
        self.menu = menu_items

    def _load_projects(self) -> list[dict]:
        """Load projects from dashboard JSON data."""
        try:
            if DASHBOARD_PATH.exists():
                content = DASHBOARD_PATH.read_text(encoding="utf-8", errors="replace")
                match = re.search(
                    r'<script id="data" type="application/json">(.*?)</script>',
                    content,
                    re.S,
                )
                if match:
                    data = json.loads(match.group(1))
                    return data.get("projects", [])
        except (OSError, json.JSONDecodeError, TypeError):
            pass
        return []

    def open_local(self, _):
        # Open in default file explorer
        projects_path = PROJECTS_DIR.resolve()
        if projects_path.exists():
            if platform.system() == "Darwin":
                subprocess.run(["open", str(projects_path)])
            else:
                subprocess.run(["xdg-open", str(projects_path)])

    def open_github(self, _):
        # Open GitHub (might need more specific implementation)
        webbrowser.open("https://github.com")

    def open_finder(self, _):
        # Open Finder in current projects directory
        projects_path = PROJECTS_DIR.resolve()
        if projects_path.exists():
            subprocess.run(["open", "-R", str(projects_path)])

    def open_project(self, path: str):
        """Open a project in VSCode."""
        # Path in dashboard JSON:
        # "../ProjectName" -> project in parent directory (PROJECTS_DIR)
        # "./" or "ProjectName" -> project in REPO_ROOT
        if path.startswith(".."):
            # Project is in parent directory (e.g., ../Chrome_SimpleGMAIL)
            project_name = path.replace("../", "")
            project_path = (PROJECTS_DIR / project_name).resolve()
        else:
            # Project is in REPO_ROOT (e.g., "." or relative path)
            if path == ".":
                project_path = REPO_ROOT
            else:
                project_path = (REPO_ROOT / path).resolve()

        if project_path.exists():
            _open_vscode_new_window(project_path)
        else:
            rumps.alert("Error", f"Project path not found:\n{project_path}")

    def update_dashboard(self, _):
        rumps.notification("Project Hub", "Updating...", "Running project scan and generating dashboard...")
        try:
            # Execute the update script
            # We use sys.executable to ensure we use the same python environment
            result = subprocess.run(
                [sys.executable, str(UPDATE_SCRIPT)],
                capture_output=True,
                text=True,
                check=True
            )
            rumps.notification("Project Hub", "Success", "Dashboard updated successfully!")
            self.title = f"📁 {project_count()}"
            self.open_dashboard(None)
        except subprocess.CalledProcessError as e:
            rumps.alert("Update Error", f"Failed to update dashboard:\n\n{e.stderr}")
        except Exception as e:
            rumps.alert("Unexpected Error", str(e))

    def open_dashboard(self, _):
        if DASHBOARD_PATH.exists():
            webbrowser.open(f"file://{DASHBOARD_PATH.absolute()}")
        else:
            rumps.alert("Error", "Dashboard file not found. Please run update first.")

if __name__ == "__main__":
    start_launcher_server()
    ProjectHubApp().run()
