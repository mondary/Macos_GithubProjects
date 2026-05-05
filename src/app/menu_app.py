#!/usr/bin/env python3
import sys
import logging
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from macos_githubprojects.menu_app import ProjectHubApp, start_launcher_server

# Enable logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting menu app...")
    start_launcher_server()
    logger.info("Starting ProjectHubApp...")
    ProjectHubApp().run()
