from rich.style import Style

def status_color(status: str) -> str:
    """Returns a Rich color string for a given service status."""
    status = status.lower()
    if status == "running":
        return "green"
    elif status == "stopped":
        return "red"
    elif status == "starting":
        return "yellow"
    elif status == "restarting":
        return "magenta"
    else:
        return "white"
