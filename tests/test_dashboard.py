import pytest
from hm.ui.dashboard import generate_services_table

def test_generate_services_table():
    services = [
        {"name": "infra", "status": "running", "pid": 1234, "dependencies": []},
        {"name": "transfer", "status": "stopped", "pid": None, "dependencies": ["infra"]}
    ]
    stats = {"total": 2, "running": 1, "stopped": 1}

    def fetch_data():
        return services, stats

    table = generate_services_table(fetch_data)
    assert table is not None
    assert len(table.columns) == 4
    assert table.row_count == 2
