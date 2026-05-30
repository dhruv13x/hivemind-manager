import time
import psutil
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from typing import Callable, Dict, Any

from .console import console
from .tables import build_ps_table

def generate_dashboard_layout(services_data: list, unmanaged_procs: list, update_count: int) -> Layout:
    """
    Creates the dynamic layout for the dashboard.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )

    layout["main"].split_row(
        Layout(name="services", ratio=2),
        Layout(name="sidebar", ratio=1)
    )

    layout["sidebar"].split_column(
        Layout(name="stats"),
        Layout(name="system")
    )

    # Header
    header_content = f"[bold cyan]Hivemind Manager Dashboard[/bold cyan] | Auto-refreshing... (Updates: {update_count})"
    layout["header"].update(Panel(header_content, style="white on blue"))

    # Services table
    table = build_ps_table(services_data)
    table.title = None # remove title to fit better in panel
    table.caption = None
    layout["services"].update(Panel(table, title="[bold]Services Overview[/bold]", border_style="cyan"))

    # Stats
    running = sum(1 for s in services_data if s["status"] == "running")
    stopped = len(services_data) - running
    stats_text = f"Total Services: {len(services_data)}\n[green]Running: {running}[/green]\n[red]Stopped: {stopped}[/red]\n\nUnmanaged procs: {len(unmanaged_procs)}"
    layout["stats"].update(Panel(stats_text, title="[bold]Runtime Statistics[/bold]", border_style="yellow"))

    # System info (CPU / Mem pseudo-values or psutil if available)
    sys_text = f"CPU Usage: {psutil.cpu_percent()}%\nMem Usage: {psutil.virtual_memory().percent}%"
    layout["system"].update(Panel(sys_text, title="[bold]System Health[/bold]", border_style="magenta"))

    # Footer
    layout["footer"].update(Panel("[dim]Press Ctrl+C to exit[/dim]"))

    return layout

def run_dashboard(data_provider_fn: Callable[[], Dict[str, Any]]):
    """
    Runs the interactive dashboard using rich.live.Live.
    data_provider_fn should return a dict with:
      - 'services': list of service dicts (name, status, pid, dependencies)
      - 'unmanaged': list of unmanaged hivemind process info strings
    """
    update_count = 0

    try:
        with Live(console=console, screen=True, auto_refresh=False) as live:
            while True:
                data = data_provider_fn()
                layout = generate_dashboard_layout(data["services"], data["unmanaged"], update_count)
                live.update(layout, refresh=True)
                update_count += 1
                time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        console.print("[dim]Exited dashboard.[/dim]")
