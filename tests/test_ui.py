from hm.ui.styles import get_status_color, get_log_color
from hm.ui.tables import render_services_table
from hm.ui.panels import render_doctor_panel
from hm.ui.trees import render_services_list, render_dependency_graph
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

def test_styles_get_status_color():
    assert get_status_color("running") == "green"
    assert get_status_color("stopped") == "red"
    assert get_status_color("unknown") == "white"

def test_styles_get_log_color():
    color_0 = get_log_color(0)
    assert isinstance(color_0, str)
    assert get_log_color(0) == color_0

def test_render_services_table():
    services = [
        {"name": "test_service", "status": "running", "pid": "123", "depends_on": "infra"},
        {"name": "stopped_service", "status": "stopped", "pid": "-", "depends_on": "-"}
    ]
    table = render_services_table(services)
    assert isinstance(table, Table)
    # 5 columns: SERVICE, STATUS, PID, UPTIME, DEPENDS ON
    assert len(table.columns) == 5

def test_render_doctor_panel():
    panel = render_doctor_panel(
        project_root="/path/to/project",
        hm_home="/path/to/hm",
        config_file="/path/to/pyproject.toml",
        hivemind_bin="/usr/bin/hivemind",
        preserve_logs="true",
        log_history="5",
        max_log_size="0.0",
        services_count=3
    )
    assert isinstance(panel, Panel)
    assert panel.title == "HM Diagnostics"

def test_render_services_list():
    services_meta = {
        "service_a": {"path": "/path/a", "dependencies": ["service_b"]},
        "service_b": {"path": "/path/b", "dependencies": []}
    }
    tree = render_services_list(services_meta)
    assert isinstance(tree, Tree)

def test_render_dependency_graph():
    services_meta = {
        "service_a": {"path": "/path/a", "dependencies": ["service_b"]},
        "service_b": {"path": "/path/b", "dependencies": []}
    }
    tree = render_dependency_graph(services_meta)
    assert isinstance(tree, Tree)
