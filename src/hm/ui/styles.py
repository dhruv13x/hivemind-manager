from typing import Optional
from rich.style import Style

# Status colors mapping
STATUS_COLORS = {
    "running": "green",
    "stopped": "red",
    "starting": "yellow",
    "restarting": "magenta",
}

def get_status_color(status: str) -> str:
    """
    Returns the rich color string for a given service status.
    """
    return STATUS_COLORS.get(status.lower(), "white")

# Define a stable list of colors for log tailing prefixes
LOG_COLORS = [
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "red",
    "bright_cyan",
    "bright_magenta",
    "bright_green",
    "bright_yellow",
    "bright_blue",
]

def get_log_color(index: int) -> str:
    """
    Returns a stable rich color string based on an index.
    """
    return LOG_COLORS[index % len(LOG_COLORS)]
