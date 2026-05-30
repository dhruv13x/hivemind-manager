import pytest
from unittest.mock import patch
from hm.ui.tables import print_ps_table
from hm.ui.panels import print_doctor_panels
from hm.ui.trees import print_list_tree, print_graph_tree

def test_print_ps_table():
    services = [
        {"name": "infra", "status": "running", "pid": 1234, "dependencies": []},
        {"name": "transfer", "status": "stopped", "pid": None, "dependencies": ["infra"]}
    ]
    with patch("hm.ui.tables.console.print") as mock_print:
        print_ps_table(services)
        assert mock_print.call_count == 4  # table, services, running, stopped

def test_print_doctor_panels():
    diagnostics = {
        "project_root": "/app",
        "hm_home": "/app/hm",
        "config_file": "/app/pyproject.toml",
        "hivemind_bin": "hivemind",
        "preserve_logs": "true",
        "max_log_history": "5",
        "max_log_size": "disabled",
        "service_count": 2,
        "active_supervisors": 1,
    }
    with patch("hm.ui.panels.console.print") as mock_print:
        print_doctor_panels(diagnostics)
        assert mock_print.call_count == 3  # three panels

def test_print_list_tree():
    services = {
        "infra": {"path": "/app/infra.hm", "dependencies": []},
        "transfer": {"path": "/app/transfer.hm", "dependencies": ["infra"]}
    }
    with patch("hm.ui.trees.console.print") as mock_print:
        print_list_tree(services)
        mock_print.assert_called_once()

def test_print_graph_tree():
    services = {
        "infra": {"path": "/app/infra.hm", "dependencies": []},
        "transfer": {"path": "/app/transfer.hm", "dependencies": ["infra"]}
    }
    with patch("hm.ui.trees.console.print") as mock_print:
        print_graph_tree(services)
        mock_print.assert_called_once()
