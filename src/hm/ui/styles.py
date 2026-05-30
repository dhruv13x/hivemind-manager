# Define standard status colors and styles

STATUS_COLORS = {
    "running": "green",
    "stopped": "red",
    "starting": "yellow",
    "restarting": "magenta",
}

# Rich theme definition
UI_THEME = {
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
    "service.name": "cyan bold",
    "status.running": "green",
    "status.stopped": "red",
    "status.starting": "yellow",
    "status.restarting": "magenta",
}

def get_status_style(status: str) -> str:
    """
    Returns the rich style tag for a given status.
    """
    return STATUS_COLORS.get(status.lower(), "default")
