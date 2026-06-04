import sys
import time
import subprocess
from pathlib import Path
from .config import (
    PROJECT_ROOT,
    HIVEMIND_BIN,
    BASE_DIR,
    PRESERVE_LOGS,
    MAX_LOG_HISTORY,
    MAX_LOG_SIZE_MB,
    tomllib,
)
from .discovery import discover_services
from .process import (
    read_pid,
    is_running,
    log_file,
    stop_service,
    run_supervised,
    remove_pid,
    rotate_log,
    write_pid,
    get_service_uptime,
)
from .tailer import multi_tail

from importlib.metadata import version, PackageNotFoundError

try:
    VERSION = version("hivemind-manager")
except PackageNotFoundError:
    VERSION = "unknown"

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

    supervisor_pids = set()
    running_count = 0
    stopped_count = 0

    services_data = []

    for svc, meta in services_meta.items():
        pid = read_pid(svc)
        deps = ", ".join(meta.get("dependencies", []))
        if pid and is_running(pid):
            services_data.append({
                "name": svc,
                "status": "running",
                "pid": str(pid),
                "depends_on": deps,
                "uptime": get_service_uptime(svc)
            })
            supervisor_pids.add(str(pid))
            running_count += 1
        else:
            services_data.append({
                "name": svc,
                "status": "stopped",
                "pid": "-",
                "depends_on": deps,
                "uptime": "-"
            })
            remove_pid(svc)
            stopped_count += 1

    from .ui.console import is_interactive, console
    from .ui.tables import render_services_table

    if is_interactive():
        table = render_services_table(services_data)
        console.print(table)

        # Add summary footer
        from rich.text import Text
        summary = Text.assemble(
            ("Services : ", "bold"), str(len(services_meta)), "\n",
            ("Running  : ", "bold green"), str(running_count), "\n",
            ("Stopped  : ", "bold red"), str(stopped_count)
        )
        console.print(summary)
    else:
        # Fallback to plain text for pipe support
        print(f"{'SERVICE':<15} {'STATUS':<10} {'PID':<8} {'UPTIME':<10}")
        print("-" * 50)
        for s in services_data:
            print(f"{s['name']:<15} {s['status']:<10} {s['pid']:<8} {s['uptime']:<10}")

        print("-" * 50)
        print(f"Services: {len(services_meta)}")
        print(f"Running : {running_count}")
        print(f"Stopped : {stopped_count}")

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


def up(follow=False):
    """
    Starts all discovered services in dynamic order.
    """
    services_meta = discover_services()
    started_set = set()
    for svc in services_meta:
        start(svc, follow=False, started_set=started_set)
    print("\nAll services started.\n")

    if follow:
        multi_tail(list(services_meta.keys()))


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
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\u2713 Project root: {project_root}")
    print(f"\u2713 HM home: {BASE_DIR}")
    print(f"\u2713 {config_status}")


def doctor():
    """
    Prints diagnostic information about the current workspace configuration.
    """
    import shutil

    # 1. Config file check
    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if pyproject_path.is_file():
        has_config = False
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            has_config = "tool" in data and "hm" in data["tool"]
        except Exception:
            pass
        if has_config:
            config_str = str(pyproject_path)
        else:
            config_str = f"{pyproject_path} (exists, but [tool.hm] section is missing)"
    else:
        config_str = "None"

    # 2. Hivemind binary check
    hivemind_path = shutil.which(HIVEMIND_BIN)
    if hivemind_path:
        bin_str = f"{hivemind_path}"
    else:
        bin_str = f"{HIVEMIND_BIN} [NOT FOUND in PATH]"

    size_str = f"{MAX_LOG_SIZE_MB} MB" if MAX_LOG_SIZE_MB > 0 else "disabled"

    from .ui.console import is_interactive, console
    from .ui.panels import render_doctor_panel

    services_count = len(discover_services())

    if is_interactive():
        panel = render_doctor_panel(
            project_root=str(PROJECT_ROOT),
            hm_home=str(BASE_DIR),
            config_file=config_str,
            hivemind_bin=bin_str,
            preserve_logs=str(PRESERVE_LOGS).lower(),
            log_history=str(MAX_LOG_HISTORY),
            max_log_size=size_str,
            services_count=services_count
        )
        console.print(panel)
    else:
        print(f"{'Project Root':<13} : {PROJECT_ROOT}")
        print(f"{'HM Home':<13} : {BASE_DIR}")
        print(f"{'Config File':<13} : {config_str}")
        print(f"{'Hivemind Bin':<13} : {bin_str}")
        print(f"{'Preserve Logs':<13} : {str(PRESERVE_LOGS).lower()}")
        print(f"{'Log History':<13} : {MAX_LOG_HISTORY}")
        print(f"{'Max Log Size':<13} : {size_str}")
        print(f"{'Service Count':<13} : {services_count}")


def list_services():
    """
    Lists all detected services in the project registry.
    """
    services_meta = discover_services()
    if not services_meta:
        print("No services detected.")
        return

    from .ui.console import is_interactive, console
    from .ui.trees import render_services_list

    if is_interactive():
        tree = render_services_list(services_meta)
        console.print(tree)
    else:
        print("Detected services:\n")
        for svc in sorted(services_meta.keys()):
            print(f"\u2713 {svc}")


def graph():
    """
    Renders dependency relationships of services.
    """
    services_meta = discover_services()
    if not services_meta:
        print("No services detected.")
        return

    from .ui.console import is_interactive, console
    from .ui.trees import render_dependency_graph

    if is_interactive():
        tree = render_dependency_graph(services_meta)
        console.print(tree)
    else:
        # Fallback to a simple text printout
        print("Service Dependencies:\n")
        for svc, meta in sorted(services_meta.items()):
            deps = meta.get("dependencies", [])
            if deps:
                print(f"{svc} -> {', '.join(deps)}")
            else:
                print(f"{svc} (no dependencies)")


def dashboard():
    """
    Starts the interactive TUI dashboard.
    """
    from .ui.console import is_interactive
    if not is_interactive():
        print("Error: hm dashboard requires an interactive terminal.")
        sys.exit(1)

    from .ui.dashboard import run_dashboard
    
    services_meta_cached = discover_services()

    def get_services_data():
        services_data = []
        for svc, meta in services_meta_cached.items():
            pid = read_pid(svc)
            deps = ", ".join(meta.get("dependencies", []))
            if pid and is_running(pid):
                services_data.append({
                    "name": svc,
                    "status": "running",
                    "pid": str(pid),
                    "depends_on": deps,
                    "uptime": get_service_uptime(svc)
                })
            else:
                services_data.append({
                    "name": svc,
                    "status": "stopped",
                    "pid": "-",
                    "depends_on": deps,
                    "uptime": "-"
                })
        return services_data

    def get_services_meta():
        return services_meta_cached

    run_dashboard(get_services_data, get_services_meta)


def usage():
    cmd = Path(sys.argv[0]).name
    print(f"""
Usage:
  {cmd} --help | -h
  {cmd} --version | -v
  {cmd} init
  {cmd} doctor
  {cmd} list
  {cmd} graph
  {cmd} dashboard
  {cmd} start <service> [--no-follow]
  {cmd} stop <service>
  {cmd} restart <service> [--no-follow]
  {cmd} status [service]
  {cmd} logs <service> [service2...]
  {cmd} ps
  {cmd} up [--follow]
  {cmd} down
""")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd in ("-h", "--help"):
        usage()
        sys.exit(0)

    if cmd in ("-v", "--version"):
        print(f"hivemind-manager v{VERSION}")
        return

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
        graph()
        return

    if cmd == "dashboard":
        dashboard()
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
            follow = "--follow" in sys.argv
            up(follow=follow)
        else:
            down()
        return

    if cmd == "ps":
        ps()
        return

    # Commands that target services
    if cmd in ("start", "stop", "restart", "logs", "status"):
        if cmd == "status" and len(sys.argv) == 2:
            status(None)
            return

        if len(sys.argv) < 3:
            usage()
            sys.exit(1)

        services_meta = discover_services()
        
        if cmd == "logs":
            targets = sys.argv[2:]
            for t in targets:
                if t not in services_meta:
                    print(f"Unknown service: {t}")
                    sys.exit(1)
            multi_tail(targets)
            return

        service = sys.argv[2]
        if service not in services_meta:
            print(f"Unknown service: {service}")
            sys.exit(1)

        if cmd == "status":
            status(service)
            return

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
            start(service, follow, extra_args)
        return

    usage()
    sys.exit(1)
