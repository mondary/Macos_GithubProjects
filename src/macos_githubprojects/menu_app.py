#!/usr/bin/env python3
# Ce fichier est gardé pour compatibilité, utilisez plutôt app/menu_app.py
PROJECTS_DIR = REPO_ROOT.parent
LAUNCHER_HOST = "127.0.0.1"
LAUNCHER_PORT = 37645


def project_count() -> int:
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
        return sum(
            1
            for child in PROJECTS_DIR.iterdir()
            if child.name
            and child.name not in {".git", "node_modules", ".DS_Store"}
            and not child.name.startswith((".", "-"))
        )

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
        self.menu = [
            rumps.MenuItem("Update Dashboard", callback=self.update_dashboard),
            None, # Separator
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard)
        ]

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
