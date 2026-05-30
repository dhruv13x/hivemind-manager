import os
from collections import deque
from typing import Dict, List, Any, Set, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.layout import Layout
from rich.text import Text
from rich.style import Style

# Global console instance
console = Console()

def render_ps_table(services_meta: Dict[str, Any], running_pids: Dict[str, int], unmanaged: List[str]) -> None:
    table = Table(title="Services Status", show_header=True, header_style="bold magenta", expand=False)
    table.add_column("SERVICE", style="cyan")
    table.add_column("STATUS", justify="center")
    table.add_column("PID", justify="right")
    table.add_column("DEPENDENCIES", style="dim")

    running_count = 0
    stopped_count = 0

    for svc in sorted(services_meta.keys()):
        deps = ", ".join(services_meta[svc].get("dependencies", []))
        if not deps:
            deps = "-"

        if svc in running_pids:
            status = "[bold green]running[/bold green]"
            pid = str(running_pids[svc])
            running_count += 1
        else:
            status = "[bold red]stopped[/bold red]"
            pid = "-"
            stopped_count += 1

        table.add_row(svc, status, pid, deps)

    console.print(table)

    summary = Table.grid(padding=(0, 1))
    summary.add_row("Total Services:", str(len(services_meta)))
    summary.add_row("Running:", f"[green]{running_count}[/green]")
    summary.add_row("Stopped:", f"[red]{stopped_count}[/red]")
    console.print(Panel(summary, title="Summary", expand=False, border_style="blue"))

    if unmanaged:
        console.print("\n[bold yellow]Unmanaged Hivemind Processes:[/bold yellow]")
        for l in unmanaged:
            console.print(f"  {l}")


def render_doctor_panels(diagnostics: Dict[str, Any]) -> None:
    layout = Layout()
    layout.split_column(
        Layout(name="env", size=10),
        Layout(name="config", size=10)
    )

    env_table = Table.grid(padding=(0, 2))
    env_table.add_row("[bold cyan]Project Root[/bold cyan]", str(diagnostics.get("project_root", "")))
    env_table.add_row("[bold cyan]HM Home[/bold cyan]", str(diagnostics.get("hm_home", "")))
    env_table.add_row("[bold cyan]Config File[/bold cyan]", str(diagnostics.get("config_file", "")))
    env_table.add_row("[bold cyan]Hivemind Bin[/bold cyan]", str(diagnostics.get("hivemind_bin", "")))
    env_table.add_row("[bold cyan]Service Count[/bold cyan]", str(diagnostics.get("service_count", "")))
    env_table.add_row("[bold cyan]Active Supervisors[/bold cyan]", str(diagnostics.get("active_supervisors", "")))
    env_panel = Panel(env_table, title="Environment", border_style="green", expand=False)

    config_table = Table.grid(padding=(0, 2))
    config_table.add_row("[bold cyan]Preserve Logs[/bold cyan]", str(diagnostics.get("preserve_logs", "")))
    config_table.add_row("[bold cyan]Log History[/bold cyan]", str(diagnostics.get("log_history", "")))
    config_table.add_row("[bold cyan]Max Log Size[/bold cyan]", str(diagnostics.get("max_log_size", "")))
    config_panel = Panel(config_table, title="Configuration Values", border_style="blue", expand=False)

    console.print(env_panel)
    console.print(config_panel)

def build_tree_node(tree: Tree, svc: str, services_meta: Dict[str, Any], visited: Set[str]) -> None:
    # Get services that this one depends on
    children = services_meta.get(svc, {}).get("dependencies", [])

    for child in sorted(children):
        if child in visited:
            tree.add(f"[dim]{child} (already listed)[/dim]")
            continue
        child_node = tree.add(f"[cyan]{child}[/cyan]")
        build_tree_node(child_node, child, services_meta, visited | {child})

def render_service_tree(services_meta: Dict[str, Any], title: str = "Service Hierarchy") -> None:
    # Find root services (ones that no other service depends on)

    tree = Tree(f"[bold]{title}[/bold]")

    # Find roots (services that no one depends on)
    all_deps = set()
    for svc, meta in services_meta.items():
        all_deps.update(meta.get("dependencies", []))

    roots = []
    for svc in services_meta:
        if svc not in all_deps:
            roots.append(svc)

    for root in sorted(roots):
        root_node = tree.add(f"[bold cyan]{root}[/bold cyan]")
        build_tree_node(root_node, root, services_meta, {root})

    console.print(tree)

def render_service_list(services_meta: Dict[str, Any]) -> None:
    if not services_meta:
        console.print("[yellow]No services detected.[/yellow]")
        return

    console.print("[bold]Detected services:[/bold]\n")
    for svc in sorted(services_meta.keys()):
        console.print(f"[green]✓[/green] [cyan]{svc}[/cyan]")

def create_dashboard_layout(
    services_meta: Dict[str, Any],
    running_pids: Dict[str, int],
    recent_logs: List[str]
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
    )
    layout["main"].split_row(
        Layout(name="services", ratio=1),
        Layout(name="logs", ratio=2),
    )

    # Header
    running_count = len(running_pids)
    total_count = len(services_meta)
    header_text = f"Hivemind Manager Dashboard | Services: {running_count}/{total_count} Running"
    layout["header"].update(Panel(Text(header_text, justify="center", style="bold white on blue")))

    # Services
    services_table = Table(expand=True, show_header=False, box=None)
    for svc in sorted(services_meta.keys()):
        status = "[green]●[/green]" if svc in running_pids else "[red]○[/red]"
        services_table.add_row(status, f"[cyan]{svc}[/cyan]")
    layout["services"].update(Panel(services_table, title="Services", border_style="cyan"))

    # Logs
    log_text = Text.from_markup("\n".join(recent_logs[-20:]))
    layout["logs"].update(Panel(log_text, title="Recent Logs (All Services)", border_style="yellow"))

    return layout
