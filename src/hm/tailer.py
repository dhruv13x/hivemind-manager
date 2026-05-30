import os
import time
import threading
import sys
from .process import log_file, read_pid, is_running

def tail_worker(service: str, index: int):
    """
    Tails the log file for a specific service using a raw binary passthrough.
    This preserves all ANSI/OSC codes and line endings (including \r) exactly
     as written by the worker.
    """
    logfile = log_file(service)

    while not logfile.exists():
        time.sleep(0.1)

    with open(logfile, "rb") as f:
        f.seek(0, os.SEEK_END)

        while True:
            chunk = f.read(8192)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
            else:
                # auto-stop if service dead
                pid = read_pid(service)
                if not pid or not is_running(pid):
                    print(f"[{service}] stopped")
                    break
                time.sleep(0.1)


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
