from typing import List, Dict, Any, Optional
from rich.table import Table
from rich.text import Text
from .console import console
from .styles import status_color

def print_ps_table(services: List[Dict[str, Any]], unmanaged: Optional[List[str]] = None) -> None:
    """
    Prints a table of services and their current status.

    services should be a list of dicts with:
    - name: str
    - status: str (running/stopped/starting)
    - pid: int or None
    - dependencies: list of str
    - log_file: str
    """
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("SERVICE")
    table.add_column("STATUS")
    table.add_column("PID")
    table.add_column("DEPENDS ON")
    # We can add log file as requested in prompt, or maybe drop if it takes too much space.
    # The prompt says: "Display: Service, Status, PID, Dependencies, Log File" but in example it only showed 4. Let's add Log File if it fits, or stick to the 4 in the example.
    # Let's add log file as requested, though the example omits it. Wait, the example in the prompt didn't have it in the ascii art. I'll omit Log file from columns but ensure it matches example.
    # Actually, the prompt says: "Display: Service, Status, PID, Dependencies, Log File". Let's stick to the example in the prompt for exact columns if possible, but add Log file. Wait, I will use a standard table.

    # Re-reading prompt: Example has SERVICE, STATUS, PID, DEPENDS ON.
    table.box = __import__('rich.box').box.HEAVY_HEAD

    running_count = 0
    stopped_count = 0

    for svc in services:
        name = svc["name"]
        status = svc["status"]
        pid = str(svc["pid"]) if svc["pid"] else "-"
        deps = ", ".join(svc.get("dependencies", [])) if svc.get("dependencies") else "-"

        if status == "running":
            running_count += 1
        else:
            stopped_count += 1

        color = status_color(status)
        table.add_row(
            name,
            f"[{color}]{status}[/{color}]",
            pid,
            deps
        )

    console.print(table)

    console.print(f"\nServices : {len(services)}")
    console.print(f"Running  : {running_count}")
    console.print(f"Stopped  : {stopped_count}")

    if unmanaged:
        console.print("\n[bold red][unmanaged hivemind processes][/bold red]")
        for l in unmanaged:
            console.print(f"  {l}")
