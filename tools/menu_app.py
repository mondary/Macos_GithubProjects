#!/usr/bin/env python3
import rumps
import subprocess
import webbrowser
import os
import sys
from pathlib import Path

# Resolve paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DASHBOARD_PATH = REPO_ROOT / "dashboard-projets.html"
UPDATE_SCRIPT = SCRIPT_DIR / "update_projects_dashboard.py"

class ProjectHubApp(rumps.App):
    def __init__(self):
        super(ProjectHubApp, self).__init__("📁 Projects")
        self.menu = [
            rumps.MenuItem("Update Dashboard", callback=self.update_dashboard),
            None, # Separator
            rumps.MenuItem("Open Dashboard", callback=self.open_dashboard),
            rumps.MenuItem("Quit", callback=self.quit_app)
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

    def quit_app(self, _):
        rumps.app.quit()

if __name__ == "__main__":
    ProjectHubApp().run()
