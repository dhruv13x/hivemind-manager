from rich.panel import Panel
from rich.table import Table
from rich.console import Group
from rich import box

def render_doctor_panel(project_root: str, hm_home: str, config_file: str, hivemind_bin: str,
                        preserve_logs: str, log_history: str, max_log_size: str, services_count: int) -> Panel:
    """
    Renders diagnostics information for `hm doctor`.
    """

    # Environment Table
    env_table = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
    env_table.add_column("Key", style="bold cyan")
    env_table.add_column("Value")

    env_table.add_row("Project Root", str(project_root))
    env_table.add_row("HM Home", str(hm_home))

    config_style = "default" if "[NOT FOUND" not in config_file and "missing" not in config_file else "yellow"
    env_table.add_row("Config File", f"[{config_style}]{config_file}[/{config_style}]")

    bin_style = "default" if "[NOT FOUND" not in hivemind_bin else "red"
    env_table.add_row("Hivemind Bin", f"[{bin_style}]{hivemind_bin}[/{bin_style}]")

    # Config Table
    config_table = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
    config_table.add_column("Key", style="bold green")
    config_table.add_column("Value")
    config_table.add_row("Preserve Logs", str(preserve_logs))
    config_table.add_row("Log History", str(log_history))
    config_table.add_row("Max Log Size", str(max_log_size))
    config_table.add_row("Service Count", str(services_count))

    # Group them together
    content = Group(
        Panel(env_table, title="Environment", border_style="blue", box=box.ROUNDED),
        Panel(config_table, title="Configuration", border_style="green", box=box.ROUNDED)
    )

    return Panel(content, title="HM Diagnostics", border_style="cyan", box=box.HEAVY)
