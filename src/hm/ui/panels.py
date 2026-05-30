from typing import Dict, Any
from rich.panel import Panel
from rich.console import Group
from rich.text import Text
from .console import console

def print_doctor_panels(diagnostics: Dict[str, Any]) -> None:
    """
    Displays diagnostic info in rich panels.
    diagnostics expects keys corresponding to the sections:
    - environment (Project Root, HM Home, Hivemind Bin)
    - configuration (Config File, Preserve Logs, Log History, Max Log Size)
    - service_discovery (Service Count, Active Supervisors, etc.)
    """

    env_text = Text()
    env_text.append(f"{'Project Root':<15}: {diagnostics.get('project_root', 'N/A')}\n")
    env_text.append(f"{'HM Home':<15}: {diagnostics.get('hm_home', 'N/A')}\n")
    bin_path = diagnostics.get('hivemind_bin', 'N/A')
    if "NOT FOUND" in bin_path:
        env_text.append(f"{'Hivemind Bin':<15}: ", style="")
        env_text.append(f"{bin_path}\n", style="bold red")
    else:
        env_text.append(f"{'Hivemind Bin':<15}: {bin_path}\n")

    env_panel = Panel(env_text, title="Environment", expand=False, border_style="blue")

    conf_text = Text()
    conf_file = diagnostics.get('config_file', 'N/A')
    if "missing" in conf_file:
        conf_text.append(f"{'Config File':<15}: ", style="")
        conf_text.append(f"{conf_file}\n", style="bold yellow")
    else:
        conf_text.append(f"{'Config File':<15}: {conf_file}\n")

    conf_text.append(f"{'Preserve Logs':<15}: {diagnostics.get('preserve_logs', 'N/A')}\n")
    conf_text.append(f"{'Log History':<15}: {diagnostics.get('max_log_history', 'N/A')}\n")
    conf_text.append(f"{'Max Log Size':<15}: {diagnostics.get('max_log_size', 'N/A')}\n")

    conf_panel = Panel(conf_text, title="Configuration", expand=False, border_style="magenta")

    svc_text = Text()
    svc_text.append(f"{'Discovered':<15}: {diagnostics.get('service_count', 0)}\n")
    svc_text.append(f"{'Active Supvs':<15}: {diagnostics.get('active_supervisors', 0)}\n")

    svc_panel = Panel(svc_text, title="Runtime Status", expand=False, border_style="green")

    console.print(env_panel)
    console.print(conf_panel)
    console.print(svc_panel)
