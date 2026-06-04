from typing import List, Dict, Any
from rich.table import Table
from rich import box
from .styles import get_status_color

def render_services_table(services: List[Dict[str, Any]]) -> Table:
    """
    Renders a rich table for the `hm ps` command.

    `services` is expected to be a list of dictionaries with keys:
    - name (str)
    - status (str)
    - pid (str or int, optionally '-')
    - depends_on (str, comma separated list or '-')
    """
    table = Table(box=box.HEAVY_EDGE, show_header=True, header_style="bold white")

    table.add_column("SERVICE", style="cyan", no_wrap=True)
    table.add_column("STATUS", justify="left")
    table.add_column("PID", justify="left")
    table.add_column("UPTIME", justify="left")
    table.add_column("DEPENDS ON", justify="left")

    for svc in services:
        status = svc.get("status", "unknown")
        color = get_status_color(status)
        status_text = f"[{color}]{status}[/{color}]"

        depends = svc.get("depends_on", "-")
        if not depends:
             depends = "-"

        pid = str(svc.get("pid", "-"))
        if not pid:
             pid = "-"
             
        uptime = str(svc.get("uptime", "-"))

        table.add_row(
            svc["name"],
            status_text,
            pid,
            uptime,
            depends
        )

    return table
