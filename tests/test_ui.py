import pytest
from rich.tree import Tree
from rich.table import Table
from rich.console import Group

from hm.ui.styles import get_status_style
from hm.ui.tables import build_ps_table
from hm.ui.panels import build_doctor_panels
from hm.ui.trees import build_service_tree, build_dependency_graph


def test_get_status_style():
    assert get_status_style("running") == "green"
    assert get_status_style("stopped") == "red"
    assert get_status_style("starting") == "yellow"
    assert get_status_style("restarting") == "magenta"
    assert get_status_style("unknown") == "default"


def test_build_ps_table():
    data = [
        {"name": "infra", "status": "running", "pid": 1234, "dependencies": []},
        {"name": "uab", "status": "stopped", "pid": None, "dependencies": ["infra"]},
    ]
    table = build_ps_table(data)
    assert isinstance(table, Table)
    assert len(table.columns) == 5
    assert table.row_count == 2
    assert "Services: 2 | Running: 1 | Stopped: 1" in str(table.caption)


def test_build_doctor_panels():
    panels = build_doctor_panels(
        project_root="/test/root",
        hm_home="/test/hm",
        config_file="/test/config.toml",
        hivemind_bin="/usr/bin/hivemind",
        preserve_logs="true",
        log_history="5",
        max_log_size="0 MB",
        has_config_warning=False,
        has_bin_warning=False
    )
    assert isinstance(panels, Group)
    # The group contains Environment and Configuration panels
    assert len(panels.renderables) == 2


def test_build_service_tree():
    services_meta = {
        "infra": {"path": "/app/infra.hm", "dependencies": []},
        "transfer": {"path": "/app/transfer.hm", "dependencies": ["infra"]},
    }
    tree = build_service_tree(services_meta)
    assert isinstance(tree, Tree)
    assert str(tree.label) == "[bold cyan]Detected services[/bold cyan]"
    assert len(tree.children) == 2


def test_build_dependency_graph():
    services_meta = {
        "infra": {"path": "/app/infra.hm", "dependencies": []},
        "transfer": {"path": "/app/transfer.hm", "dependencies": ["infra"]},
        "bypass": {"path": "/app/bypass.hm", "dependencies": ["infra"]},
        "uab": {"path": "/app/uab.hm", "dependencies": ["bypass"]},
    }
    tree = build_dependency_graph(services_meta)
    assert isinstance(tree, Tree)
    assert str(tree.label) == "[bold cyan]Dependency Graph[/bold cyan]"

    # Root should be 'infra' because it's the only one with no dependencies
    assert len(tree.children) == 1
    infra_node = tree.children[0]

    # infra has 'bypass' and 'transfer' depending on it
    assert len(infra_node.children) == 2
