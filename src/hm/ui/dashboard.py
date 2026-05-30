import time
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from .console import console
from .styles import status_color

def make_dashboard_layout() -> Layout:
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=3)
    )
    layout["main"].split_row(
        Layout(name="services", ratio=2),
        Layout(name="details", ratio=1)
    )
    return layout

def generate_services_table(fetch_data_cb) -> Table:
    services, _ = fetch_data_cb()
    table = Table(expand=True, box=None)
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("PID")
    table.add_column("Depends On")

    for svc in services:
        status = svc["status"]
        color = status_color(status)
        table.add_row(
            svc["name"],
            f"[{color}]{status}[/{color}]",
            str(svc["pid"]) if svc["pid"] else "-",
            ", ".join(svc.get("dependencies", [])) if svc.get("dependencies") else "-"
        )
    return table

def run_dashboard(fetch_data_cb) -> None:
    """
    Runs the interactive dashboard.
    fetch_data_cb should return (services_list, runtime_stats_dict)
    """
    layout = make_dashboard_layout()

    try:
        with Live(layout, console=console, refresh_per_second=1, screen=True):
            while True:
                services, stats = fetch_data_cb()

                header = Panel(Text("Hivemind Manager - Dashboard", justify="center", style="bold white on blue"))
                layout["header"].update(header)

                table = generate_services_table(lambda: (services, stats))
                layout["services"].update(Panel(table, title="Services", border_style="cyan"))

                stats_text = Text()
                stats_text.append(f"Total Services: {stats.get('total', 0)}\n")
                stats_text.append(f"Running: {stats.get('running', 0)}\n", style="green")
                stats_text.append(f"Stopped: {stats.get('stopped', 0)}\n", style="red")
                layout["details"].update(Panel(stats_text, title="Runtime Statistics", border_style="magenta"))

                footer = Panel(Text("Press Ctrl+C to exit", justify="center", style="dim"))
                layout["footer"].update(footer)

                time.sleep(1)
    except KeyboardInterrupt:
        pass
