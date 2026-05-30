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
    from .config import PRESERVE_LOGS
    from .process import rotate_log
    
    if PRESERVE_LOGS:
        rotate_log(service)
    else:
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
    from .ui.console import is_interactive, console
    from .ui.tables import build_ps_table

    services_data = []
    supervisor_pids = set()

    for svc, meta in services_meta.items():
        pid = read_pid(svc)
        if pid and is_running(pid):
            status = "running"
            supervisor_pids.add(str(pid))
        else:
            status = "stopped"
            remove_pid(svc)
            pid = None

        services_data.append({
            "name": svc,
            "status": status,
            "pid": pid,
            "dependencies": meta.get("dependencies", []),
            "logfile": f"{svc}.log"
        })

    extra = []
    try:
        out = subprocess.check_output(["pgrep", "-af", HIVEMIND_BIN], text=True)
        lines = out.strip().split("\n")

        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            c_pid = parts[0]

            try:
                ppid = subprocess.check_output(
                    ["ps", "-o", "ppid=", "-p", c_pid],
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                continue

            if ppid in supervisor_pids or c_pid in supervisor_pids:
                continue

            extra.append(line)

    except subprocess.CalledProcessError:
        pass

    if is_interactive():
        table = build_ps_table(services_data)
        console.print(table)
        if extra:
            console.print("\n[yellow][unmanaged hivemind processes][/yellow]")
            from rich.markup import escape
            for l in extra:
                console.print(f"  {escape(l)}")
    else:
        # Plain text fallback
        print(f"{'SERVICE':<15} {'STATUS':<10} {'PID':<8}")
        print("-" * 40)

        running_count = 0
        stopped_count = 0

        for s_data in services_data:
            pid_str = str(s_data["pid"]) if s_data["pid"] is not None else "-"
            print(f"{s_data['name']:<15} {s_data['status']:<10} {pid_str:<8}")
            if s_data["status"] == "running":
                running_count += 1
            else:
                stopped_count += 1

        print("-" * 40)
        print(f"Services: {len(services_data)}")
        print(f"Running : {running_count}")
        print(f"Stopped : {stopped_count}")

        if extra:
            print("\n[unmanaged hivemind processes]")
            for l in extra:
                print(" ", l)


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


def init():
    """
    Initializes a new hivemind-manager project environment.
    Creates or updates pyproject.toml with [tool.hm] configuration
    and creates the home directory for logs and PIDs.
    """
    import os
    from pathlib import Path

    project_root = Path(os.getcwd()).resolve()

    if not list(project_root.glob("*.hm")):
        import sys
        if sys.stdout.isatty() and sys.stdin.isatty():
            ans = input("No .hm service files found.\nInitialize anyway? [y/N] ")
            if ans.lower() not in ("y", "yes"):
                print("Aborted.")
                return
        else:
            print("Warning: No .hm service files found. Initializing anyway...")

    pyproject = project_root / "pyproject.toml"

    # 1. Update pyproject.toml
    if not pyproject.exists():
        content = """[tool.hm]
home_dir = "hm"
preserve_logs = true
max_log_history = 5
max_log_size_mb = 0.0
"""
        pyproject.write_text(content)
        config_status = "Created pyproject.toml with configuration"
    else:
        text = pyproject.read_text()
        if "[tool.hm]" not in text:
            # Append [tool.hm] section
            with open(pyproject, "a") as f:
                f.write("\n[tool.hm]\nhome_dir = \"hm\"\npreserve_logs = true\nmax_log_history = 5\nmax_log_size_mb = 0.0\n")
            config_status = "Added [tool.hm] configuration to pyproject.toml"
        else:
            missing = {
                "home_dir": 'home_dir = "hm"',
                "preserve_logs": 'preserve_logs = true',
                "max_log_history": 'max_log_history = 5',
                "max_log_size_mb": 'max_log_size_mb = 0.0'
            }
            try:
                from .config import tomllib
                data = tomllib.loads(text)
                hm_data = data.get("tool", {}).get("hm", {})
                for k in list(missing.keys()):
                    if k in hm_data:
                        del missing[k]
            except Exception:
                pass
            
            if missing:
                lines = text.split("\n")
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if line.strip().replace(" ", "") == "[tool.hm]":
                        for m_val in missing.values():
                            new_lines.append(m_val)
                pyproject.write_text("\n".join(new_lines))
                config_status = "Updated [tool.hm] with missing keys in pyproject.toml"
            else:
                config_status = "Configuration already exists in pyproject.toml"

    # 2. Create home directory
    from .config import BASE_DIR
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\u2713 Project root: {project_root}")
    print(f"\u2713 HM home: {BASE_DIR}")
    print(f"\u2713 {config_status}")


def doctor():
    """
    Prints diagnostic information about the current workspace configuration.
    """
    import shutil
    from .config import PROJECT_ROOT, BASE_DIR, HIVEMIND_BIN

    # 1. Config file check
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    has_config_warning = False
    if pyproject_path.is_file():
        has_config = False
        try:
            from .config import tomllib
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            has_config = "tool" in data and "hm" in data["tool"]
        except Exception:
            pass
        if has_config:
            config_str = str(pyproject_path)
        else:
            config_str = f"{pyproject_path} (exists, but [tool.hm] section is missing)"
            has_config_warning = True
    else:
        config_str = "None"
        has_config_warning = True

    # 2. Hivemind binary check
    hivemind_path = shutil.which(HIVEMIND_BIN)
    has_bin_warning = False
    if hivemind_path:
        bin_str = f"{hivemind_path}"
    else:
        bin_str = f"{HIVEMIND_BIN} [NOT FOUND in PATH]"
        has_bin_warning = True

    from .config import PRESERVE_LOGS, MAX_LOG_HISTORY, MAX_LOG_SIZE_MB
    size_str = f"{MAX_LOG_SIZE_MB} MB" if MAX_LOG_SIZE_MB > 0 else "disabled"

    from .ui.console import is_interactive, console
    if is_interactive():
        from .ui.panels import build_doctor_panels
        panels = build_doctor_panels(
            project_root=str(PROJECT_ROOT),
            hm_home=str(BASE_DIR),
            config_file=config_str,
            hivemind_bin=bin_str,
            preserve_logs=str(PRESERVE_LOGS).lower(),
            log_history=str(MAX_LOG_HISTORY),
            max_log_size=size_str,
            has_config_warning=has_config_warning,
            has_bin_warning=has_bin_warning
        )
        console.print(panels)
    else:
        print(f"{'Project Root':<13} : {PROJECT_ROOT}")
        print(f"{'HM Home':<13} : {BASE_DIR}")
        print(f"{'Config File':<13} : {config_str}")
        print(f"{'Hivemind Bin':<13} : {bin_str}")
        print(f"{'Preserve Logs':<13} : {str(PRESERVE_LOGS).lower()}")
        print(f"{'Log History':<13} : {MAX_LOG_HISTORY}")
        print(f"{'Max Log Size':<13} : {size_str}")


def list_services():
    """
    Lists all detected services in the project registry.
    """
    services_meta = discover_services()
    if not services_meta:
        print("No services detected.")
        return

    from .ui.console import is_interactive, console

    if is_interactive():
        from .ui.trees import build_service_tree
        tree = build_service_tree(services_meta)
        console.print(tree)
    else:
        print("Detected services:\n")
        for svc in sorted(services_meta.keys()):
            print(f"\u2713 {svc}")


def usage():
    cmd = Path(sys.argv[0]).name
    print(f"""
Usage:
  {cmd} init
  {cmd} doctor
  {cmd} list
  {cmd} graph
  {cmd} dashboard
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

    if cmd == "init":
        init()
        return

    if cmd == "doctor":
        doctor()
        return

    if cmd == "list":
        list_services()
        return

    if cmd == "graph":
        services_meta = discover_services()
        from .ui.console import is_interactive, console
        from .ui.trees import build_dependency_graph
        if is_interactive():
            tree = build_dependency_graph(services_meta)
            console.print(tree)
        else:
            print("Dependency graph requires an interactive terminal.")
        return

    if cmd == "dashboard":
        from .ui.console import is_interactive
        if not is_interactive():
            print("Error: hm dashboard requires an interactive terminal.")
            sys.exit(1)

        from .ui.dashboard import run_dashboard

        def provide_dashboard_data():
            meta = discover_services()
            services_data = []
            supervisor_pids = set()

            import psutil

            for svc, sm in meta.items():
                pid = read_pid(svc)
                if pid and is_running(pid):
                    status = "running"
                    supervisor_pids.add(str(pid))
                else:
                    status = "stopped"
                    pid = None

                services_data.append({
                    "name": svc,
                    "status": status,
                    "pid": pid,
                    "dependencies": sm.get("dependencies", []),
                    "logfile": f"{svc}.log"
                })

            unmanaged = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if cmdline and any(HIVEMIND_BIN in part for part in cmdline):
                        c_pid = str(proc.info['pid'])
                        ppid = str(proc.info['ppid'])

                        if c_pid in supervisor_pids or ppid in supervisor_pids:
                            continue

                        unmanaged.append(" ".join(cmdline))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "services": services_data,
                "unmanaged": unmanaged
            }

        run_dashboard(provide_dashboard_data)
        return

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

