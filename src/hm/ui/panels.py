from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.console import Group

def build_doctor_panels(
    project_root: str,
    hm_home: str,
    config_file: str,
    hivemind_bin: str,
    preserve_logs: str,
    log_history: str,
    max_log_size: str,
    has_config_warning: bool,
    has_bin_warning: bool
) -> Group:
    """
    Builds a Group of Panels for the 'hm doctor' command.
    """

    # Environment Panel
    env_table = Table.grid(padding=(0, 2))
    env_table.add_column(style="cyan bold", justify="right")
    env_table.add_column()

    env_table.add_row("Project Root :", project_root)
    env_table.add_row("HM Home :", hm_home)

    config_text = Text(config_file)
    if has_config_warning:
        config_text.stylize("yellow")
    env_table.add_row("Config File :", config_text)

    bin_text = Text(hivemind_bin)
    if has_bin_warning:
        bin_text.stylize("red bold")
    env_table.add_row("Hivemind Bin :", bin_text)

    env_panel = Panel(
        env_table,
        title="[bold blue]Environment[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
    )

    # Configuration Panel
    cfg_table = Table.grid(padding=(0, 2))
    cfg_table.add_column(style="cyan bold", justify="right")
    cfg_table.add_column()

    cfg_table.add_row("Preserve Logs :", preserve_logs)
    cfg_table.add_row("Log History :", str(log_history))
    cfg_table.add_row("Max Log Size :", max_log_size)

    cfg_panel = Panel(
        cfg_table,
        title="[bold blue]Configuration[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
    )

    return Group(env_panel, cfg_panel)
