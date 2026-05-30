import os
import time
import threading
from rich.console import Console
from .config import COLORS
from .process import log_file, read_pid, is_running

# Map legacy color codes to rich color names for compatibility and ease of use
RICH_COLORS = [
    "cyan",
    "yellow",
    "magenta",
    "green",
    "blue",
    "red",
]

console = Console()

def tail_worker(service, color_name):
    """
    Tails the log file for a specific service and color-prefixes output.
    Terminates when the service stops running.
    """
    logfile = log_file(service)

    while not logfile.exists():
        time.sleep(0.1)

    with open(logfile, "r") as f:
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if line:
                # Prefix the line with the colored service name
                prefix = f"[{color_name}][{service}][/{color_name}] "
                console.print(f"{prefix}{line.strip()}", markup=True, highlight=False)
            else:
                # auto-stop if service dead
                pid = read_pid(service)
                if not pid or not is_running(pid):
                    console.print(f"[{color_name}][{service}] stopped[/{color_name}]")
                    break
                time.sleep(0.2)


def multi_tail(services):
    """
    Spawns log tailing threads for multiple services.
    """
    console.print(f"[bold]Tailing logs:[/bold] {', '.join(services)}\n")

    threads = []

    for i, svc in enumerate(services):
        color = RICH_COLORS[i % len(RICH_COLORS)]
        t = threading.Thread(target=tail_worker, args=(svc, color), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Stopped log tail[/bold yellow]")
