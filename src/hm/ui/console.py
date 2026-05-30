import sys
from rich.console import Console
from rich.theme import Theme

from .styles import UI_THEME

# Global console instance with custom theme
console = Console(theme=Theme(UI_THEME))

def is_interactive() -> bool:
    """
    Returns True if stdout is a TTY and we can safely render Rich components.
    Useful for ensuring pipe/redirection compatibility.
    """
    return sys.stdout.isatty()
