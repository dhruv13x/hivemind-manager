import os
import sys
import time
import signal
import subprocess
from .config import BASE_DIR, PROJECT_ROOT, HIVEMIND_BIN, RESTART_DELAY, MAX_RESTART_DELAY

def pid_file(service):
    return BASE_DIR / f"{service}.pid"


def log_file(service):
    return BASE_DIR / f"{service}.log"


def is_running(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid(service):
    f = pid_file(service)
    if not f.exists():
        return None
    try:
        return int(f.read_text().strip())
    except:
        return None


def write_pid(service, pid):
    pid_file(service).write_text(str(pid))


def remove_pid(service):
    pid_file(service).unlink(missing_ok=True)


def stop_service(service):
    """
    Terminates the specified service.
    First tries to gracefully stop using the stored PID.
    Then scans the system for orphaned or unmanaged processes of that service and stops them as well.
    """
    pid = read_pid(service)
    stopped_any = False

    if pid:
        if is_running(pid):
            print(f"[{service}] stopping (PID {pid})")
            try:
                os.killpg(pid, signal.SIGTERM)
                stopped_any = True
            except ProcessLookupError:
                pass

            for _ in range(20):
                if not is_running(pid):
                    break
                time.sleep(0.2)

            if is_running(pid):
                print(f"[{service}] force killing")
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        remove_pid(service)

    # Terminate any leftover orphaned/unmanaged processes running the .hm file for this service
    try:
        out = subprocess.check_output(["pgrep", "-af", HIVEMIND_BIN], text=True)
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            p_pid = int(parts[0])
            cmdline = " ".join(parts[1:])

            if f"{service}.hm" in cmdline:
                print(f"[{service}] found orphaned/unmanaged process (PID {p_pid}): {cmdline}")
                print(f"[{service}] terminating process group for PID {p_pid}...")
                try:
                    pgid = os.getpgid(p_pid)
                    os.killpg(pgid, signal.SIGTERM)
                    # Wait up to 1 second for the process to exit
                    for _ in range(10):
                        try:
                            os.kill(p_pid, 0)
                        except OSError:
                            break
                        time.sleep(0.1)
                    # Force kill if still running
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except OSError:
                        pass
                    stopped_any = True
                except OSError:
                    try:
                        os.kill(p_pid, 0) # check existence
                        os.kill(p_pid, signal.SIGTERM)
                        for _ in range(10):
                            try:
                                os.kill(p_pid, 0)
                            except OSError:
                                break
                            time.sleep(0.1)
                        os.kill(p_pid, signal.SIGKILL)
                        stopped_any = True
                    except OSError:
                        pass
    except subprocess.CalledProcessError:
        pass

    if not pid and not stopped_any:
        print(f"[{service}] not running")


def run_supervised(service, extra_args):
    """
    Supervisor process loop. Monitors a single hivemind worker and restarts it if it crashes.
    """
    logfile = log_file(service)

    stop_flag = False
    child_proc = None

    def handle_exit(signum, frame):
        nonlocal stop_flag, child_proc
        stop_flag = True
        if child_proc and child_proc.poll() is None:
            try:
                os.killpg(child_proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    delay = RESTART_DELAY

    while not stop_flag:
        with open(logfile, "ab") as f:
            child_proc = subprocess.Popen(
                [HIVEMIND_BIN, f"{service}.hm"] + extra_args,
                stdout=f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                cwd=str(PROJECT_ROOT),
            )

        print(f"[{service}] worker started (PID {child_proc.pid})")

        exit_code = child_proc.wait()

        if stop_flag:
            break

        print(f"[{service}] worker exited (code {exit_code})")

        if exit_code == 0:
            break

        print(f"[{service}] restarting in {delay:.1f}s...")
        time.sleep(delay)

        delay = min(delay * 2, MAX_RESTART_DELAY)

    print(f"[{service}] supervisor exiting")
