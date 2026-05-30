import time
from typing import Callable, Any
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.align import Align
from rich.text import Text

from .console import console
from .tables import render_services_table
from .trees import render_dependency_graph

def run_dashboard(get_services_data_fn: Callable[[], Any], get_services_meta_fn: Callable[[], Any]):
    """
    Runs the interactive `hm dashboard`.
    `get_services_data_fn` should return a list of dicts describing the current state of services.
    `get_services_meta_fn` should return the service meta dictionary for the dependency graph.
    """

    def generate_layout() -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right", ratio=2)
        )

        # Header
        header_text = Text("Hivemind Manager - Dashboard", style="bold white on blue", justify="center")
        layout["header"].update(Panel(header_text, style="blue"))

        # Footer
        footer_text = Text("Press Ctrl+C to exit", style="bold red", justify="center")
        layout["footer"].update(Panel(footer_text, style="red"))

        return layout

    def update_layout(layout: Layout):
        # Fetch fresh data
        services_data = get_services_data_fn()
        services_meta = get_services_meta_fn()

        # Left Panel - Dependencies
        dep_tree = render_dependency_graph(services_meta)
        layout["left"].update(Panel(dep_tree, title="Dependency Graph", border_style="magenta"))

        # Right Panel - Services Table
        services_table = render_services_table(services_data)

        # Adding a summary directly into the right layout panel
        running_count = sum(1 for s in services_data if s.get("status") == "running")
        stopped_count = sum(1 for s in services_data if s.get("status") == "stopped")
        summary_text = Text.assemble(
            ("Services: ", "bold"), str(len(services_data)), " | ",
            ("Running: ", "bold green"), str(running_count), " | ",
            ("Stopped: ", "bold red"), str(stopped_count)
        )

        right_content = Layout()
        right_content.split_column(
            Layout(services_table, ratio=1),
            Layout(Panel(Align.center(summary_text)), size=3)
        )

        layout["right"].update(Panel(right_content, title="Process Health", border_style="cyan"))


    layout = generate_layout()

    with Live(layout, console=console, refresh_per_second=1, screen=True) as live:
        try:
            while True:
                update_layout(layout)
                time.sleep(1)
        except KeyboardInterrupt:
            pass
