import os
import time
import threading
from .process import log_file, read_pid, is_running
from .ui.console import is_interactive, console
from .ui.styles import get_log_color

def tail_worker(service: str, index: int):
    """
    Tails the log file for a specific service and color-prefixes output.
    Terminates when the service stops running.
    """
    logfile = log_file(service)

    while not logfile.exists():
        time.sleep(0.1)

    interactive = is_interactive()
    color = get_log_color(index)

    with open(logfile, "r", encoding="utf-8", errors="replace") as f:
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()
            if line:
                if interactive:
                    from rich.markup import escape
                    console.print(f"[{color}][{service}][/{color}] {escape(line)}", end="")
                else:
                    print(f"[{service}] {line}", end="")
            else:
                # auto-stop if service dead
                pid = read_pid(service)
                if not pid or not is_running(pid):
                    if interactive:
                        console.print(f"[{color}][{service}] stopped[/{color}]")
                    else:
                        print(f"[{service}] stopped")
                    break
                time.sleep(0.2)


def multi_tail(services):
    """
    Spawns log tailing threads for multiple services.
    """
    print(f"Tailing logs: {', '.join(services)}\n")

    threads = []

    for i, svc in enumerate(services):
        t = threading.Thread(target=tail_worker, args=(svc, i), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped log tail")
