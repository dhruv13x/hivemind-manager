import sys
from rich.console import Console

# Create a global console instance.
# Rich automatically detects if the output is not a tty (like when piped)
# and gracefully degrades by stripping colors and formatting appropriately.
console = Console()
