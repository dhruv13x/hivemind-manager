import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

def is_project_anchor(directory: Path) -> bool:
    """
    Checks if a directory is a valid project anchor (contains a pyproject.toml
    with [tool.hm] or a .git directory).
    """
    pyproject = directory / "pyproject.toml"
    if pyproject.is_file():
        try:
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            if "tool" in data and "hm" in data["tool"]:
                return True
        except Exception:
            pass
    if (directory / ".git").is_dir():
        return True
    return False

def find_project_root():
    """
    Traverses upwards from the current working directory to find a directory
    containing a pyproject.toml with [tool.hm] or a .git directory.
    Falls back to the environment variable HM_PROJECT_ROOT, or the current directory.
    """
    env_root = os.environ.get("HM_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()

    current_dir = Path(os.getcwd()).resolve()
    for parent in [current_dir] + list(current_dir.parents):
        if is_project_anchor(parent):
            return parent
    return current_dir

PROJECT_ROOT = find_project_root()

# Load configuration from pyproject.toml at PROJECT_ROOT if present
config_data = {}
pyproject_path = PROJECT_ROOT / "pyproject.toml"
if pyproject_path.is_file():
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        config_data = pyproject_data.get("tool", {}).get("hm", {})
    except Exception:
        pass

# Default values
default_home_dir = config_data.get("home_dir", "hm")
default_hivemind_bin = config_data.get("hivemind_bin", "hivemind")
default_restart_delay = float(config_data.get("restart_delay", 1.0))
default_max_restart_delay = float(config_data.get("max_restart_delay", 10.0))

# Log rotation defaults
default_preserve_logs = config_data.get("preserve_logs", False)
default_max_log_history = int(config_data.get("max_log_history", 5))
default_max_log_size_mb = float(config_data.get("max_log_size_mb", 0.0))

# Environment overrides
home_dir_str = os.environ.get("HM_HOME_DIR", default_home_dir)
home_dir_path = Path(home_dir_str)
if home_dir_path.is_absolute():
    BASE_DIR = home_dir_path
else:
    BASE_DIR = (PROJECT_ROOT / home_dir_path).resolve()

# Create base directory safely
BASE_DIR.mkdir(parents=True, exist_ok=True)

HIVEMIND_BIN = os.environ.get("HM_HIVEMIND_BIN", default_hivemind_bin)

try:
    RESTART_DELAY = float(os.environ.get("HM_RESTART_DELAY", default_restart_delay))
except ValueError:
    RESTART_DELAY = 1.0

try:
    MAX_RESTART_DELAY = float(os.environ.get("HM_MAX_RESTART_DELAY", default_max_restart_delay))
except ValueError:
    MAX_RESTART_DELAY = 10.0

def get_env_bool(name, default):
    val = os.environ.get(name)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "t", "y")

PRESERVE_LOGS = get_env_bool("HM_PRESERVE_LOGS", default_preserve_logs)

try:
    MAX_LOG_HISTORY = int(os.environ.get("HM_MAX_LOG_HISTORY", default_max_log_history))
except ValueError:
    MAX_LOG_HISTORY = 5

try:
    MAX_LOG_SIZE_MB = float(os.environ.get("HM_MAX_LOG_SIZE_MB", default_max_log_size_mb))
except ValueError:
    MAX_LOG_SIZE_MB = 50.0

COLORS = [
    "\033[36m",  # cyan
    "\033[33m",  # yellow
    "\033[35m",  # magenta
    "\033[32m",  # green
    "\033[34m",  # blue
    "\033[31m",  # red
]
RESET = "\033[0m"
