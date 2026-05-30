import sys
import time
import subprocess
from pathlib import Path
from .config import PROJECT_ROOT, HIVEMIND_BIN
from .discovery import discover_services
from .process import (
    read_pid,
    is_running,
    log_file,
    stop_service,
    run_supervised,
    remove_pid
)
from .tailer import multi_tail

def start(service, follow=True, extra_args=None, started_set=None):
    """
    Starts a service supervisor. Checks and starts dependencies first if they are not running.
    """
    if extra_args is None:
        extra_args = []
    if started_set is None:
        started_set = set()

    services_meta = discover_services()
    if service not in services_meta:
        print(f"Unknown service: {service}")
        sys.exit(1)

    if service in started_set:
        return
    started_set.add(service)

    # 1. Resolve and start dependencies
    deps = services_meta[service]["dependencies"]
    for dep in deps:
        if dep not in services_meta:
            print(f"Warning: [{service}] depends on unknown service '{dep}'")
            continue

        dep_pid = read_pid(dep)
        if dep_pid and is_running(dep_pid):
            # Dependency already running, no action needed
            continue

        print(f"[{service}] Dependency '{dep}' is not running. Starting '{dep}' first...")
        start(dep, follow=False, started_set=started_set)
        # Brief pause to allow the dependency supervisor & worker to start
        time.sleep(1.5)

    # 2. Stop existing service instance to prevent collision
    stop_service(service)

    logfile = log_file(service)
    # Truncate logs
    open(logfile, "w").close()

    print(f"[{service}] supervisor starting...")

    # Spawn supervisor pointing back to the entrypoint CLI wrapper
    entrypoint_script = str(Path(sys.argv[0]).resolve())
    proc = subprocess.Popen(
        [sys.executable, entrypoint_script, "_run", service] + extra_args,
        preexec_fn=os_setsid_safely(),
        cwd=str(PROJECT_ROOT),
    )

    from .process import write_pid
    write_pid(service, proc.pid)

    print(f"[{service}] supervisor started (PID {proc.pid})")

    if follow:
        multi_tail([service])


def os_setsid_safely():
    """
    Safely returns os.setsid reference if available (Unix systems).
    """
    import os
    return getattr(os, "setsid", None)


def ps():
    """
    Lists running services and unmanaged hivemind processes.
    """
    services_meta = discover_services()
    print(f"{'SERVICE':<15} {'STATUS':<10} {'PID':<8}")
    print("-" * 40)

    supervisor_pids = set()

    for svc in services_meta:
        pid = read_pid(svc)
        if pid and is_running(pid):
            print(f"{svc:<15} {'running':<10} {pid:<8}")
            supervisor_pids.add(str(pid))
        else:
            print(f"{svc:<15} {'stopped':<10} -")
            remove_pid(svc)

    try:
        out = subprocess.check_output(["pgrep", "-af", HIVEMIND_BIN], text=True)
        lines = out.strip().split("\n")

        extra = []

        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            pid = parts[0]

            try:
                ppid = subprocess.check_output(
                    ["ps", "-o", "ppid=", "-p", pid],
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                continue

            if ppid in supervisor_pids or pid in supervisor_pids:
                continue

            extra.append(line)

        if extra:
            print("\n[unmanaged hivemind processes]")
            for l in extra:
                print(" ", l)

    except subprocess.CalledProcessError:
        pass


def status(service=None):
    """
    Shows status of all or a specific service.
    """
    if service is None:
        ps()
        return

    pid = read_pid(service)
    if pid and is_running(pid):
        print(f"[{service}] running (PID {pid})")
    else:
        print(f"[{service}] stopped")
        remove_pid(service)


def up():
    """
    Starts all discovered services in dynamic order.
    """
    services_meta = discover_services()
    started_set = set()
    for svc in services_meta:
        start(svc, follow=False, started_set=started_set)
    print("\nAll services started.\n")


def down():
    """
    Stops all discovered services.
    """
    services_meta = discover_services()
    for svc in services_meta:
        stop_service(svc)
    print("\nAll services stopped.\n")


def usage():
    cmd = Path(sys.argv[0]).name
    print(f"""
Usage:
  {cmd} start <service> [--no-follow]
  {cmd} stop <service>
  {cmd} restart <service>
  {cmd} status [service]
  {cmd} logs <service> [service2...]
  {cmd} ps
  {cmd} up
  {cmd} down
""")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "_run":
        if len(sys.argv) < 3:
            print("Error: service name required for _run")
            sys.exit(1)
        service = sys.argv[2]
        extra_args = sys.argv[3:]
        run_supervised(service, extra_args)
        return

    if cmd in ("up", "down"):
        if cmd == "up":
            up()
        else:
            down()
        return

    if cmd == "ps":
        ps()
        return

    if cmd == "status":
        if len(sys.argv) == 2:
            status(None)
        else:
            status(sys.argv[2])
        return

    if cmd == "logs":
        if len(sys.argv) < 3:
            usage()
            return
        multi_tail(sys.argv[2:])
        return

    if len(sys.argv) < 3:
        usage()
        sys.exit(1)

    service = sys.argv[2]
    extra_args = sys.argv[3:]

    follow = True
    if "--no-follow" in extra_args:
        follow = False
        extra_args.remove("--no-follow")

    if cmd == "start":
        start(service, follow, extra_args)
    elif cmd == "stop":
        stop_service(service)
    elif cmd == "restart":
        stop_service(service)
        start(service, follow, extra_args)
    else:
        usage()
