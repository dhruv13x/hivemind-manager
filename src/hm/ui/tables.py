from rich.table import Table
from rich.text import Text
from typing import List, Dict, Any

from .styles import get_status_style

def build_ps_table(services_data: List[Dict[str, Any]]) -> Table:
    """
    Builds a Rich Table for the 'hm ps' command.

    services_data should be a list of dictionaries with keys:
    - name: str
    - status: str
    - pid: str or int
    - dependencies: list[str]
    """
    table = Table(
        title="Services Status",
        show_header=True,
        header_style="bold cyan",
        title_justify="left",
        title_style="bold",
        box=None  # or use rich.box.ROUNDED if needed, issue says "Unicode box drawing"
    )
    from rich import box
    table.box = box.ROUNDED

    table.add_column("SERVICE", style="cyan", no_wrap=True)
    table.add_column("STATUS", justify="left")
    table.add_column("PID", justify="right")
    table.add_column("DEPENDS ON", style="dim")
    table.add_column("LOG FILE", style="dim")

    running_count = 0
    stopped_count = 0
    total_count = len(services_data)

    for svc in services_data:
        name = svc["name"]
        status = svc["status"]
        pid = str(svc.get("pid", "-"))
        if pid == "None":
            pid = "-"
        deps = svc.get("dependencies", [])
        deps_str = ", ".join(deps) if deps else "-"
        logfile = svc.get("logfile", "-")

        if status == "running":
            running_count += 1
        else:
            stopped_count += 1

        status_style = get_status_style(status)
        status_text = Text(status, style=status_style)

        table.add_row(name, status_text, pid, deps_str, logfile)

    # Add footer summary text
    table.caption = f"Services: {total_count} | Running: {running_count} | Stopped: {stopped_count}"
    table.caption_justify = "left"

    return table
