#!/usr/bin/env python3
"""
Main entry point for Macos_GithubProjects application.
This script provides a unified interface to all project management features.
"""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.cli import main as cli_main
from app.menu_app import main as menu_main


def main():
    """Main entry point - dispatch to appropriate interface."""
    if len(sys.argv) > 1:
        # Command line interface
        cli_main()
    else:
        # Menu bar interface
        menu_main()


if __name__ == "__main__":
    main()