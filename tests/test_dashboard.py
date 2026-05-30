import pytest
import hm.ui.dashboard
from rich.layout import Layout

def test_run_dashboard(mocker):
    mock_live = mocker.patch('hm.ui.dashboard.Live')
    mock_live_instance = mocker.MagicMock()
    mock_live.return_value.__enter__.return_value = mock_live_instance
    mocker.patch('time.sleep', side_effect=KeyboardInterrupt)
    services_data = [
        {"name": "app1", "status": "running", "pid": "1234", "depends_on": ""},
        {"name": "app2", "status": "stopped", "pid": "-", "depends_on": ""}
    ]
    def get_services_data(): return services_data
    services_meta = {
        "app1": {"dependencies": []},
        "app2": {"dependencies": []}
    }
    def get_services_meta(): return services_meta
    mock_render_table = mocker.patch('hm.ui.dashboard.render_services_table', return_value="table")
    mock_render_graph = mocker.patch('hm.ui.dashboard.render_dependency_graph', return_value="graph")
    hm.ui.dashboard.run_dashboard(get_services_data, get_services_meta)
    mock_render_table.assert_called_once_with(services_data)
    mock_render_graph.assert_called_once_with(services_meta)
