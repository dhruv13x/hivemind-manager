import os
import time
import threading
import sys
from .process import log_file, read_pid, is_running

def tail_worker(service: str, index: int):
    """
    Tails the log file for a specific service using a raw binary passthrough.
    """
    logfile = log_file(service)

    while True:
        if not logfile.exists():
            time.sleep(0.5)
            continue

        try:
            with open(logfile, "rb") as f:
                # Baseline the inode
                try:
                    last_inode = os.fstat(f.fileno()).st_ino
                except OSError:
                    last_inode = None

                # History check (last 2KB)
                try:
                    size = os.path.getsize(logfile)
                    if size > 2048:
                        f.seek(-2048, os.SEEK_END)
                        f.readline()
                    else:
                        f.seek(0)
                except OSError:
                    f.seek(0)

                last_pos = f.tell()

                while True:
                    # 1. Check if file is still there and hasn't changed Inode
                    try:
                        curr_stat = os.stat(logfile)
                        if last_inode is not None and curr_stat.st_ino != last_inode:
                            sys.stdout.buffer.write(f"\n--- [{service}] logs rotated (new file) ---\n".encode())
                            sys.stdout.buffer.flush()
                            break 
                    except OSError:
                        # File moved/deleted, wait for it to reappear in outer loop
                        break

                    # 2. Check for truncation
                    if curr_stat.st_size < last_pos:
                        sys.stdout.buffer.write(f"\n--- [{service}] logs truncated ---\n".encode())
                        sys.stdout.buffer.flush()
                        f.seek(0)
                        last_pos = 0
                    
                    # 3. Read data
                    chunk = f.read(16384)
                    if chunk:
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.buffer.flush()
                        last_pos = f.tell()
                        continue
                    
                    time.sleep(0.1)
        except (OSError, IOError):
            time.sleep(0.5)
            continue


def multi_tail(services):
    """
    Spawns log tailing threads for multiple services.
    """
    # Version marker [v4.1] ensures we are running the Inode-aware code
    print(f"Tailing logs [v4.1]: {', '.join(services)}\n")
    sys.stdout.flush()

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
