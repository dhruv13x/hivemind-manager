import sys
from rich.console import Console

# Create a shared console instance
console = Console()

def is_interactive() -> bool:
    """
    Returns True if the output is connected to an interactive TTY.
    Allows features like rich tables/panels.
    """
    return sys.stdout.isatty()

def print_error(msg: str):
    """
    Helper to print errors consistently.
    """
    if is_interactive():
        console.print(f"[red]Error:[/red] {msg}", style="bold")
    else:
        print(f"Error: {msg}", file=sys.stderr)
