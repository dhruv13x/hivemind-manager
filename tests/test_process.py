import pytest
import os
from pathlib import Path
import time
import subprocess
import signal

import hm.process
import hm.config

@pytest.fixture(autouse=True)
def setup_fs(fs):
    """Use pyfakefs for all process tests."""
    fs.create_dir('/fake/hm')
    hm.process.BASE_DIR = Path('/fake/hm')
    hm.config.BASE_DIR = Path('/fake/hm')
    yield fs

def test_pid_file():
    assert hm.process.pid_file('app') == Path('/fake/hm/app.pid')

def test_log_file():
    assert hm.process.log_file('app') == Path('/fake/hm/app.log')

def test_write_and_read_pid():
    hm.process.write_pid('app', 1234)
    assert hm.process.read_pid('app') == 1234

def test_read_pid_not_exist():
    assert hm.process.read_pid('app') is None

def test_read_pid_invalid_format(fs):
    fs.create_file('/fake/hm/app.pid', contents='not_an_int')
    assert hm.process.read_pid('app') is None

def test_remove_pid():
    hm.process.write_pid('app', 1234)
    hm.process.remove_pid('app')
    assert hm.process.read_pid('app') is None

def test_remove_pid_not_exist():
    hm.process.remove_pid('app')

def test_is_running(mocker):
    mock_kill = mocker.patch('os.kill')
    mock_kill.return_value = None
    assert hm.process.is_running(1234) is True

    mock_kill.side_effect = OSError()
    assert hm.process.is_running(1234) is False

def test_stop_service_graceful(mocker):
    hm.process.write_pid('app', 1234)
    mock_is_running = mocker.patch('hm.process.is_running', side_effect=[True, False, False, False])
    mock_killpg = mocker.patch('os.killpg')
    mocker.patch('subprocess.check_output', return_value='')
    hm.process.stop_service('app')
    mock_killpg.assert_called_once_with(1234, hm.process.signal.SIGTERM)
    assert hm.process.read_pid('app') is None

def test_stop_service_force_kill(mocker):
    hm.process.write_pid('app', 1234)
    mock_is_running = mocker.patch('hm.process.is_running', return_value=True)
    mock_killpg = mocker.patch('os.killpg')
    mock_sleep = mocker.patch('time.sleep')
    mocker.patch('subprocess.check_output', return_value='')

    hm.process.stop_service('app')

    assert mock_killpg.call_count == 2
    mock_killpg.assert_any_call(1234, hm.process.signal.SIGTERM)
    mock_killpg.assert_any_call(1234, hm.process.signal.SIGKILL)

def test_stop_service_unmanaged(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', return_value=5678)
    mock_killpg = mocker.patch('os.killpg')
    mocker.patch('os.kill', side_effect=OSError())
    hm.process.stop_service('app')
    mock_killpg.assert_any_call(5678, hm.process.signal.SIGTERM)

def test_rotate_log(fs, mocker):
    mocker.patch('hm.config.MAX_LOG_HISTORY', 3)
    fs.create_file('/fake/hm/app.log', contents='new_log')
    fs.create_file('/fake/hm/app.log.1', contents='old_log_1')
    fs.create_file('/fake/hm/app.log.2', contents='old_log_2')

    hm.process.rotate_log('app')

    assert Path('/fake/hm/app.log.1').read_text() == 'new_log'
    assert Path('/fake/hm/app.log.2').read_text() == 'old_log_1'
    assert Path('/fake/hm/app.log.3').read_text() == 'old_log_2'
    assert Path('/fake/hm/app.log').read_text() == ''

def test_run_supervised_success(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = 0
    mock_popen_class = mocker.patch('subprocess.Popen', return_value=mock_popen)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    hm.process.run_supervised('app', [])
    mock_popen_class.assert_called_once()

def test_stop_service_not_running(mocker, capsys):
    hm.process.write_pid('app', 1234)
    mocker.patch('hm.process.is_running', return_value=False)
    mocker.patch('subprocess.check_output', return_value='')
    hm.process.stop_service('app')
    assert hm.process.read_pid('app') is None

def test_stop_service_unmanaged_force_kill(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', side_effect=OSError())
    mock_kill = mocker.patch('os.kill')
    mock_kill.side_effect = [None, None] + [None]*10 + [None]
    mocker.patch('time.sleep')
    hm.process.stop_service('app')
    mock_kill.assert_any_call(5678, hm.process.signal.SIGKILL)

def test_run_supervised_loop_and_signals(mocker, fs):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 1, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 0.1, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 1)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.side_effect = [None, 1, 0, 0]
    mock_popen_class = mocker.patch('subprocess.Popen', return_value=mock_popen)
    mocker.patch('time.sleep')
    fs.create_file('/fake/hm/app.log', contents='A'*(1024*1024 + 1))
    hm.process.run_supervised('app', [])
    assert mock_popen_class.call_count == 2

def test_run_supervised_signal_handler(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = None
    mock_popen_class = mocker.patch('subprocess.Popen', return_value=mock_popen)
    mock_sleep = mocker.patch('time.sleep')
    mock_killpg = mocker.patch('os.killpg')
    def side_effect(*args):
        import signal
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        return None
    mock_sleep.side_effect = side_effect
    hm.process.run_supervised('app', [])
    mock_killpg.assert_called_once_with(9999, hm.process.signal.SIGTERM)

def test_stop_service_exceptions(mocker):
    hm.process.write_pid('app', 1234)
    mocker.patch('hm.process.is_running', return_value=True)
    mocker.patch('time.sleep')
    mocker.patch('subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'cmd'))
    mock_killpg = mocker.patch('os.killpg', side_effect=ProcessLookupError())
    hm.process.stop_service('app')
    assert mock_killpg.call_count == 2

def test_stop_service_unmanaged_exceptions(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', side_effect=OSError())
    mocker.patch('os.kill', side_effect=OSError())
    hm.process.stop_service('app')

def test_run_supervised_exceptions(mocker, fs):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 1, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 1)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = 0
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    fs.create_file('/fake/hm/app.log', contents='A'*10)
    import pathlib
    original_stat = pathlib.Path.stat
    def mock_stat(self, *args, **kwargs):
        if str(self) == '/fake/hm/app.log':
            raise OSError("stat failed")
        return original_stat(self, *args, **kwargs)
    mocker.patch('pathlib.Path.stat', mock_stat)
    mocker.patch('time.sleep')
    hm.process.run_supervised('app', [])

def test_stop_service_unmanaged_kill_exception(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', return_value=5678)
    mock_kill = mocker.patch('os.kill')
    mock_kill.return_value = None
    mocker.patch('time.sleep')
    mock_killpg = mocker.patch('os.killpg', side_effect=[None, OSError()])
    hm.process.stop_service('app')

def test_stop_service_unmanaged_getpgid_ok_but_check_fails(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', return_value=5678)
    mocker.patch('os.killpg')
    mocker.patch('os.kill', side_effect=OSError())
    hm.process.stop_service('app')

def test_stop_service_unmanaged_fallback_kill_check_fails(mocker):
    hm.process.remove_pid('app')
    mocker.patch('subprocess.check_output', return_value="5678 /path/to/hivemind app.hm\n")
    mocker.patch('os.getpgid', side_effect=OSError())
    mocker.patch('time.sleep')
    mocker.patch('os.kill', side_effect=[None, None, OSError(), None])
    hm.process.stop_service('app')

def test_run_supervised_handle_exit_lookup_error(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = None
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    mock_sleep = mocker.patch('time.sleep')
    mocker.patch('os.killpg', side_effect=ProcessLookupError())
    def side_effect(*args):
        import signal
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        return None
    mock_sleep.side_effect = side_effect
    hm.process.run_supervised('app', [])

def test_run_supervised_log_rotation_exception(mocker, fs):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 1, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 1)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = 0
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    fs.create_file('/fake/hm/app.log', contents='A'*(1024*1024 + 1))
    mocker.patch('hm.process.rotate_log', side_effect=OSError())
    mocker.patch('time.sleep')
    hm.process.run_supervised('app', [])

def test_run_supervised_stop_flag_break(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = None
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    mock_sleep = mocker.patch('time.sleep')
    mocker.patch('os.killpg')
    def side_effect(*args):
        import signal
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        return None
    mock_sleep.side_effect = side_effect
    hm.process.run_supervised('app', [])

def test_run_supervised_delay_cap(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 6.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.side_effect = [1, 1, 0, 0]
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    mocker.patch('time.sleep')
    hm.process.run_supervised('app', [])

def test_stop_service_unmanaged_skip_blank_lines(mocker):
    hm.process.remove_pid('app')
    mock_check_output = mocker.patch('subprocess.check_output')
    mock_check_output.return_value = " \n5678 /path/to/hivemind app.hm\n \n"
    mocker.patch('os.getpgid', return_value=5678)
    mocker.patch('os.killpg')
    mocker.patch('os.kill', side_effect=OSError())
    hm.process.stop_service('app')

def test_rotate_log_no_history(fs, mocker):
    mocker.patch('hm.config.MAX_LOG_HISTORY', 1)
    fs.create_file('/fake/hm/app.log', contents='new_log')
    fs.create_file('/fake/hm/app.log.1', contents='old_log_1')

    hm.process.rotate_log('app')

    assert Path('/fake/hm/app.log.1').read_text() == 'new_log'
    assert Path('/fake/hm/app.log').read_text() == ''

def test_stop_service_killpg_lookup_error(mocker):
    hm.process.write_pid('app', 1234)
    mocker.patch('hm.process.is_running', side_effect=[True] + [False]*25)
    mocker.patch('subprocess.check_output', return_value='')
    mock_killpg = mocker.patch('os.killpg', side_effect=[ProcessLookupError()])
    hm.process.stop_service('app')
    assert mock_killpg.call_count == 1

def test_run_supervised_stop_flag_break_before_print(mocker):
    mocker.patch('hm.process.MAX_LOG_SIZE_MB', 0, create=True)
    mocker.patch('hm.process.RESTART_DELAY', 1.0, create=True)
    mocker.patch('hm.process.MAX_RESTART_DELAY', 10.0, create=True)
    mocker.patch('hm.config.MAX_LOG_SIZE_MB', 0)
    mock_popen = mocker.MagicMock()
    mock_popen.pid = 9999
    mock_popen.poll.return_value = None
    mocker.patch('subprocess.Popen', return_value=mock_popen)
    mock_sleep = mocker.patch('time.sleep')
    mocker.patch('os.killpg')
    def sleep_side_effect(*args):
        import signal
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        return None
    mock_sleep.side_effect = sleep_side_effect
    hm.process.run_supervised('app', [])
