#!/usr/bin/env python3
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from macos_githubprojects.projects_hub import main


if __name__ == "__main__":
    raise SystemExit(main())
