import os
import time
import threading
from .config import COLORS, RESET
from .process import log_file, read_pid, is_running

def tail_worker(service, color):
    """
    Tails the log file for a specific service and color-prefixes output.
    Terminates when the service stops running.
    """
    logfile = log_file(service)

    while not logfile.exists():
        time.sleep(0.1)

    with open(logfile, "r") as f:
        f.seek(0, os.SEEK_END)
        print(f"{color}[{service}] Log tail started...{RESET}")

        while True:
            line = f.readline()
            if line:
                print(f"{color}[{service}]{RESET} {line}", end="")
            else:
                # auto-stop if service dead
                pid = read_pid(service)
                if not pid or not is_running(pid):
                    print(f"{color}[{service}] stopped{RESET}")
                    break
                time.sleep(0.2)


def multi_tail(services):
    """
    Spawns log tailing threads for multiple services.
    """
    print(f"Tailing logs: {', '.join(services)}\n")

    threads = []

    for i, svc in enumerate(services):
        color = COLORS[i % len(COLORS)]
        t = threading.Thread(target=tail_worker, args=(svc, color), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped log tail")
