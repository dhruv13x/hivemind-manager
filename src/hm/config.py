import os
import sys
from pathlib import Path

def find_project_root():
    """
    Traverses upwards from the current working directory to find a directory
    containing *.hm files. Falls back to the current directory if none are found.
    """
    current_dir = Path(os.getcwd()).resolve()
    for parent in [current_dir] + list(current_dir.parents):
        if list(parent.glob("*.hm")):
            return parent
    return current_dir

PROJECT_ROOT = find_project_root()
BASE_DIR = PROJECT_ROOT / "hm"
BASE_DIR.mkdir(exist_ok=True)

HIVEMIND_BIN = "hivemind"

RESTART_DELAY = 1.0
MAX_RESTART_DELAY = 10.0

COLORS = [
    "\033[36m",  # cyan
    "\033[33m",  # yellow
    "\033[35m",  # magenta
    "\033[32m",  # green
    "\033[34m",  # blue
    "\033[31m",  # red
]
RESET = "\033[0m"
