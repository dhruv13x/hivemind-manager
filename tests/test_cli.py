import pytest
import sys
import os
from pathlib import Path

import hm.cli

def test_cli_start_unknown_service(mocker, capsys):
    mocker.patch('hm.cli.discover_services', return_value={})

    with pytest.raises(SystemExit) as e:
        hm.cli.start('unknown_app')

    assert e.value.code == 1
    out, _ = capsys.readouterr()
    assert "Unknown service: unknown_app" in out

def test_cli_start_with_dependencies(mocker, capsys):
    services_meta = {
        'app': {'dependencies': ['db', 'missing_dep']},
        'db': {'dependencies': []}
    }
    mocker.patch('hm.cli.discover_services', return_value=services_meta)

    mocker.patch('hm.cli.read_pid', side_effect=lambda svc: 1234 if svc == 'db' else None)
    mocker.patch('hm.cli.is_running', return_value=True)

    mock_stop = mocker.patch('hm.cli.stop_service')
    mocker.patch('hm.process.rotate_log')
    mocker.patch('hm.config.PRESERVE_LOGS', True)

    mocker.patch('hm.cli.log_file', return_value=Path('/fake/log'))
    mocker.patch('builtins.open', mocker.mock_open())

    mock_popen = mocker.patch('subprocess.Popen')
    mock_popen.return_value.pid = 9999

    mocker.patch('sys.executable', '/mock/python')
    mocker.patch('hm.cli.multi_tail')
    mocker.patch('hm.process.write_pid')

    hm.cli.start('app', follow=True)

    out, _ = capsys.readouterr()
    assert "Warning: [app] depends on unknown service 'missing_dep'" in out
    mock_stop.assert_called_with('app')
    mock_popen.assert_called()

def test_cli_start_with_dependencies_not_running(mocker, capsys):
    services_meta = {
        'app': {'dependencies': ['db']},
        'db': {'dependencies': []}
    }
    mocker.patch('hm.cli.discover_services', return_value=services_meta)

    mocker.patch('hm.cli.read_pid', return_value=None)
    mocker.patch("hm.cli.is_running", side_effect=[False, True])

    mock_stop = mocker.patch('hm.cli.stop_service')
    mocker.patch('hm.config.PRESERVE_LOGS', False)

    mocker.patch('hm.cli.log_file', return_value=Path('/fake/log'))
    mocker.patch('builtins.open', mocker.mock_open())

    mock_popen = mocker.patch('subprocess.Popen')
    mock_popen.return_value.pid = 9999

    mocker.patch('time.sleep')
    mocker.patch('hm.process.write_pid')

    hm.cli.start('app', follow=False)

    out, _ = capsys.readouterr()
    assert "Dependency 'db' is not running. Starting 'db' first..." in out
    assert mock_popen.call_count == 2

def test_cli_start_already_started(mocker, capsys):
    services_meta = {'app': {'dependencies': []}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)

    hm.cli.start('app', started_set={'app'})

    out, _ = capsys.readouterr()
    assert out == ""

def test_cli_up(mocker, capsys):
    services_meta = {'app1': {}, 'app2': {}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mock_start = mocker.patch('hm.cli.start')

    hm.cli.up()

    assert mock_start.call_count == 2
    out, _ = capsys.readouterr()
    assert "All services started." in out

def test_cli_down(mocker, capsys):
    services_meta = {'app1': {}, 'app2': {}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mock_stop = mocker.patch('hm.cli.stop_service')

    hm.cli.down()

    assert mock_stop.call_count == 2
    out, _ = capsys.readouterr()
    assert "All services stopped." in out

def test_cli_init_no_files_abort(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('sys.stdout.isatty', return_value=True)
    mocker.patch('sys.stdin.isatty', return_value=True)
    mocker.patch('builtins.input', return_value='n')

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Aborted." in out

def test_cli_init_no_files_non_interactive(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('sys.stdout.isatty', return_value=False)
    mocker.patch('sys.stdin.isatty', return_value=False)

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Warning: No .hm service files found. Initializing anyway..." in out
    assert Path('/fake/repo/pyproject.toml').exists()

def test_cli_init_with_files_new_pyproject(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/app.hm', contents='')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Created pyproject.toml with configuration" in out
    assert Path('/fake/repo/pyproject.toml').exists()
    assert '[tool.hm]' in Path('/fake/repo/pyproject.toml').read_text()

def test_cli_init_append_pyproject(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/app.hm', contents='')
    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.pytest]\n')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Added [tool.hm] configuration to pyproject.toml" in out
    assert '[tool.hm]' in Path('/fake/repo/pyproject.toml').read_text()

def test_cli_init_update_missing_keys(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/app.hm', contents='')
    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]\nhome_dir = "hm"\n')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Updated [tool.hm] with missing keys in pyproject.toml" in out
    content = Path('/fake/repo/pyproject.toml').read_text()
    assert 'preserve_logs = true' in content
    assert 'max_log_history = 5' in content
    assert 'max_log_size_mb = 0.0' in content

def test_cli_init_already_configured(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/app.hm', contents='')
    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]\nhome_dir = "hm"\npreserve_logs = true\nmax_log_history = 5\nmax_log_size_mb = 0.0\n')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Configuration already exists in pyproject.toml" in out

def test_cli_init_invalid_toml(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/app.hm', contents='')
    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]\n[invalid\n')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Updated [tool.hm] with missing keys in pyproject.toml" in out

def test_cli_init_interactive_yes(fs, mocker, capsys, monkeypatch):
    fs.create_dir('/fake/repo')
    monkeypatch.chdir('/fake/repo')

    mocker.patch('sys.stdout.isatty', return_value=True)
    mocker.patch('sys.stdin.isatty', return_value=True)
    mocker.patch('builtins.input', return_value='y')
    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))

    hm.cli.init()

    out, _ = capsys.readouterr()
    assert "Created pyproject.toml with configuration" in out



def test_cli_doctor_interactive_fixed(fs, mocker, capsys, monkeypatch):
    mocker.patch('hm.ui.console.is_interactive', return_value=True)
    mock_console_print = mocker.patch('hm.ui.console.console.print')
    mock_doctor_panel = mocker.patch('hm.ui.panels.render_doctor_panel', return_value="panel")

    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]')
    mocker.patch('hm.config.PROJECT_ROOT', Path('/fake/repo'))
    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))
    mocker.patch('hm.config.HIVEMIND_BIN', 'hivemind')
    mocker.patch('shutil.which', return_value='/usr/bin/hivemind')

    mocker.patch('hm.config.PRESERVE_LOGS', True)
    mocker.patch('hm.config.MAX_LOG_HISTORY', 5)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 50.0)

    mocker.patch('hm.cli.discover_services', return_value={'app': {}})

    hm.cli.doctor()

    mock_doctor_panel.assert_called_once()
    mock_console_print.assert_called_once()

def test_cli_doctor_non_interactive_fixed(fs, mocker, capsys, monkeypatch):
    mocker.patch('hm.ui.console.is_interactive', return_value=False)
    mocker.patch('hm.config.PROJECT_ROOT', Path('/fake/repo'))
    mocker.patch('hm.config.BASE_DIR', Path('/fake/repo/hm'))
    mocker.patch('hm.config.HIVEMIND_BIN', 'hivemind')
    mocker.patch('shutil.which', return_value=None)
    mocker.patch('hm.config.PRESERVE_LOGS', False)
    mocker.patch('hm.config.MAX_LOG_HISTORY', 5)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0.0)

    mocker.patch('hm.cli.discover_services', return_value={'app': {}})

    hm.cli.doctor()

    out, _ = capsys.readouterr()
    assert "None" in out
    assert "NOT FOUND in PATH" in out
    assert "disabled" in out

def test_cli_doctor_pyproject_without_tool_hm_fixed(fs, mocker, capsys):
    mocker.patch('hm.ui.console.is_interactive', return_value=False)
    # the doctor() uses PROJECT_ROOT directly from hm.cli which was imported from hm.config
    mocker.patch('hm.cli.PROJECT_ROOT', Path('/fake/repo'))
    mocker.patch('hm.config.PROJECT_ROOT', Path('/fake/repo'))
    fs.create_dir('/fake/repo')
    fs.create_file('/fake/repo/pyproject.toml', contents='[tool.other]\n')
    mocker.patch('shutil.which', return_value='/bin/hm')
    mocker.patch('hm.cli.discover_services', return_value={})

    hm.cli.doctor()
    out, _ = capsys.readouterr()
    assert "exists, but [tool.hm] section is missing" in out

def test_cli_list_services_no_services(mocker, capsys):
    mocker.patch('hm.cli.discover_services', return_value={})
    hm.cli.list_services()
    out, _ = capsys.readouterr()
    assert "No services detected." in out

def test_cli_list_services_interactive(mocker, capsys):
    services_meta = {'app': {}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.ui.console.is_interactive', return_value=True)
    mock_render = mocker.patch('hm.ui.trees.render_services_list', return_value="tree")
    mock_print = mocker.patch('hm.ui.console.console.print')

    hm.cli.list_services()
    mock_render.assert_called_once_with(services_meta)
    mock_print.assert_called_once_with("tree")

def test_cli_list_services_non_interactive(mocker, capsys):
    services_meta = {'app': {}, 'db': {}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.ui.console.is_interactive', return_value=False)

    hm.cli.list_services()
    out, _ = capsys.readouterr()
    assert "Detected services:" in out
    assert "app" in out
    assert "db" in out

def test_cli_graph_no_services(mocker, capsys):
    mocker.patch('hm.cli.discover_services', return_value={})
    hm.cli.graph()
    out, _ = capsys.readouterr()
    assert "No services detected." in out

def test_cli_graph_interactive(mocker, capsys):
    services_meta = {'app': {}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.ui.console.is_interactive', return_value=True)
    mock_render = mocker.patch('hm.ui.trees.render_dependency_graph', return_value="graph")
    mock_print = mocker.patch('hm.ui.console.console.print')

    hm.cli.graph()
    mock_render.assert_called_once_with(services_meta)
    mock_print.assert_called_once_with("graph")

def test_cli_graph_non_interactive(mocker, capsys):
    services_meta = {'app': {'dependencies': ['db']}, 'db': {'dependencies': []}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.ui.console.is_interactive', return_value=False)

    hm.cli.graph()
    out, _ = capsys.readouterr()
    assert "app -> db" in out
    assert "db (no dependencies)" in out

def test_cli_dashboard_non_interactive(mocker, capsys):
    mocker.patch('hm.ui.console.is_interactive', return_value=False)
    with pytest.raises(SystemExit) as e:
        hm.cli.dashboard()
    assert e.value.code == 1
    out, _ = capsys.readouterr()
    assert "hm dashboard requires an interactive terminal" in out

def test_cli_dashboard_interactive(mocker):
    services_meta = {'app': {'dependencies': ['db']}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.ui.console.is_interactive', return_value=True)
    mocker.patch('hm.cli.read_pid', return_value=1234)
    mocker.patch('hm.cli.is_running', return_value=True)

    mock_run_dashboard = mocker.patch('hm.ui.dashboard.run_dashboard')

    hm.cli.dashboard()

    mock_run_dashboard.assert_called_once()
    args, kwargs = mock_run_dashboard.call_args
    get_services_data = args[0]
    get_services_meta = args[1]

    data = get_services_data()
    assert data[0]['name'] == 'app'
    assert data[0]['status'] == 'running'

    mocker.patch("hm.cli.is_running", side_effect=[False, True])
    data = get_services_data()
    assert data[0]['status'] == 'stopped'

    assert get_services_meta() == services_meta

def test_cli_usage(capsys):
    import sys
    sys.argv = ['hm']
    hm.cli.usage()
    out, _ = capsys.readouterr()
    assert "Usage:" in out

def test_cli_main_no_args(mocker, capsys):
    mocker.patch('sys.argv', ['hm'])
    with pytest.raises(SystemExit) as e:
        hm.cli.main()
    assert e.value.code == 1

def test_cli_main_commands(mocker):
    commands = [
        ('init', 'hm.cli.init'),
        ('doctor', 'hm.cli.doctor'),
        ('list', 'hm.cli.list_services'),
        ('graph', 'hm.cli.graph'),
        ('dashboard', 'hm.cli.dashboard'),
        ('up', 'hm.cli.up'),
        ('down', 'hm.cli.down')
    ]

    for cmd, patch_target in commands:
        mock_cmd = mocker.patch(patch_target)
        mocker.patch('sys.argv', ['hm', cmd])
        hm.cli.main()
        mock_cmd.assert_called_once()

def test_cli_main_run_no_args(mocker, capsys):
    mocker.patch('sys.argv', ['hm', '_run'])
    with pytest.raises(SystemExit) as e:
        hm.cli.main()
    assert e.value.code == 1
    out, _ = capsys.readouterr()
    assert "service name required for _run" in out

def test_cli_main_run(mocker):
    mocker.patch('sys.argv', ['hm', '_run', 'app'])
    mock_run = mocker.patch('hm.cli.run_supervised')
    hm.cli.main()
    mock_run.assert_called_once_with('app', [])

def test_cli_main_logs(mocker, capsys):
    mocker.patch('sys.argv', ['hm', 'logs'])
    hm.cli.main()
    # It just calls usage
    out, _ = capsys.readouterr()
    assert "Usage:" in out

    mocker.patch('sys.argv', ['hm', 'logs', 'app'])
    mock_tail = mocker.patch('hm.cli.multi_tail')
    hm.cli.main()
    mock_tail.assert_called_once_with(['app'])

def test_cli_main_start_stop_restart(mocker, capsys):
    mocker.patch('sys.argv', ['hm', 'invalid_cmd'])
    with pytest.raises(SystemExit):
        hm.cli.main()
    out, _ = capsys.readouterr()
    assert "Usage:" in out

    mock_start = mocker.patch('hm.cli.start')
    mock_stop = mocker.patch('hm.cli.stop_service')

    mocker.patch('sys.argv', ['hm', 'start', 'app'])
    hm.cli.main()
    mock_start.assert_called_with('app', True, [])

    mocker.patch('sys.argv', ['hm', 'start', 'app', '--no-follow'])
    hm.cli.main()
    mock_start.assert_called_with('app', False, [])

    mocker.patch('sys.argv', ['hm', 'stop', 'app'])
    hm.cli.main()
    mock_stop.assert_called_with('app')

    mocker.patch('sys.argv', ['hm', 'restart', 'app'])
    hm.cli.main()
    mock_stop.assert_called_with('app')
    mock_start.assert_called_with('app', True, [])

def test_cli_main_status(mocker, capsys):
    mocker.patch('sys.argv', ['hm', 'status'])
    mock_status = mocker.patch('hm.cli.status')
    hm.cli.main()
    mock_status.assert_called_once_with(None)

    mocker.patch('sys.argv', ['hm', 'status', 'app'])
    mock_status.reset_mock()
    hm.cli.main()
    mock_status.assert_called_once_with('app')

def test_cli_main_ps(mocker, capsys):
    mocker.patch('sys.argv', ['hm', 'ps'])
    mock_ps = mocker.patch('hm.cli.ps')
    hm.cli.main()
    mock_ps.assert_called_once()

def test_cli_main_start_no_args(mocker, capsys):
    mocker.patch('sys.argv', ['hm', 'start'])
    with pytest.raises(SystemExit):
        hm.cli.main()

def test_cli_status_running_and_stopped(mocker, capsys):
    mocker.patch('hm.cli.read_pid', side_effect=lambda svc: 1234 if svc == 'app' else None)
    mocker.patch('hm.cli.is_running', side_effect=lambda pid: True)
    mock_remove = mocker.patch('hm.cli.remove_pid')

    hm.cli.status('app')
    out, _ = capsys.readouterr()
    assert "[app] running (PID 1234)" in out

    hm.cli.status('app2')
    out, _ = capsys.readouterr()
    assert "[app2] stopped" in out
    mock_remove.assert_called_with('app2')

def test_cli_ps_interactive(mocker, capsys):
    services_meta = {'app': {'dependencies': []}, 'app2': {'dependencies': ['app']}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)

    mocker.patch('hm.cli.read_pid', side_effect=[1234, None])
    mocker.patch('hm.cli.is_running', return_value=True)
    mock_remove = mocker.patch('hm.cli.remove_pid')

    # We must patch get_unmanaged_processes
    mocker.patch('subprocess.check_output', return_value="9999 /path/hivemind other.hm\n")

    mocker.patch('hm.ui.console.is_interactive', return_value=True)
    mock_render = mocker.patch('hm.ui.tables.render_services_table', return_value="table")
    mock_print = mocker.patch('hm.ui.console.console.print')

    hm.cli.ps()

    mock_render.assert_called_once()
    mock_print.assert_called() # one for table, maybe one for unmanaged
    mock_remove.assert_called_once_with('app2')

def test_cli_ps_non_interactive(mocker, capsys):
    services_meta = {'app': {'dependencies': []}}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('hm.cli.read_pid', return_value=1234)
    mocker.patch('hm.cli.is_running', return_value=True)

    mocker.patch('subprocess.check_output', return_value="9999 /path/hivemind other.hm\n")
    mocker.patch('hm.ui.console.is_interactive', return_value=False)

    hm.cli.ps()
    out, _ = capsys.readouterr()
    assert "app" in out
    assert "1234" in out
    assert "unmanaged hivemind processes" in out
    assert "9999" in out

def test_cli_ps_subprocess_error(mocker, capsys):
    services_meta = {}
    mocker.patch('hm.cli.discover_services', return_value=services_meta)
    mocker.patch('subprocess.check_output', side_effect=mocker.patch('subprocess.CalledProcessError')(1, 'cmd'))
    mocker.patch('hm.ui.console.is_interactive', return_value=False)

    hm.cli.ps()
    out, _ = capsys.readouterr()
    assert "Unmanaged hivemind processes" not in out
