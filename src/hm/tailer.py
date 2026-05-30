import os
import time
import threading
import sys
from .config import COLORS
from .process import log_file, read_pid, is_running
from .ui.console import console, is_interactive

# Use rich console colors if interactive
RICH_COLORS = [
    "cyan", "yellow", "magenta", "green", "blue", "red"
]

def tail_worker(service, color_idx, is_tty):
    """
    Tails the log file for a specific service and color-prefixes output.
    Terminates when the service stops running.
    """
    logfile = log_file(service)

    while not logfile.exists():
        time.sleep(0.1)

    rich_color = RICH_COLORS[color_idx % len(RICH_COLORS)]
    COLORS[color_idx % len(COLORS)]

    with open(logfile, "r") as f:
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if line:
                # Strip newline for rich print, keep it for plain print
                if is_tty:
                    from rich.text import Text
                    t = Text()
                    t.append(f"[{service}] ", style=rich_color)
                    t.append(line.rstrip())
                    console.print(t)
                else:
                    sys.stdout.write(f"[{service}] {line}")
                    sys.stdout.flush()
            else:
                # auto-stop if service dead
                pid = read_pid(service)
                if not pid or not is_running(pid):
                    if is_tty:
                        console.print(f"[{rich_color}][{service}][/{rich_color}] [dim]stopped[/dim]")
                    else:
                        sys.stdout.write(f"[{service}] stopped\n")
                        sys.stdout.flush()
                    break
                time.sleep(0.2)


def multi_tail(services):
    """
    Spawns log tailing threads for multiple services.
    """
    is_tty = is_interactive()
    if is_tty:
        console.print(f"Tailing logs: [bold]{', '.join(services)}[/bold]\n")
    else:
        print(f"Tailing logs: {', '.join(services)}\n")

    threads = []

    for i, svc in enumerate(services):
        t = threading.Thread(target=tail_worker, args=(svc, i, is_tty), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if is_tty:
            console.print("\n[dim]Stopped log tail[/dim]")
        else:
            print("\nStopped log tail")
