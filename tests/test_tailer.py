import pytest
import os
import threading
import time
from pathlib import Path

import hm.tailer
import hm.process
import hm.config

@pytest.fixture(autouse=True)
def setup_fs(fs):
    """Use pyfakefs for all tailer tests."""
    fs.create_dir('/fake/hm')
    hm.process.BASE_DIR = Path('/fake/hm')
    hm.config.BASE_DIR = Path('/fake/hm')
    yield fs

def test_tail_worker_interactive(fs, mocker, capsys):
    fs.create_file('/fake/hm/app.log', contents='line1\nline2\n')

    mocker.patch('hm.process.read_pid', side_effect=[1234, 1234, None])
    mocker.patch('hm.process.is_running', return_value=True)

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)

    mocker.patch('hm.tailer.is_interactive', return_value=True)
    mocker.patch('hm.tailer.get_log_color', return_value='red')
    mock_console_print = mocker.patch('hm.tailer.console.print')

    hm.tailer.tail_worker('app', 0)

    assert mock_console_print.call_count == 3
    mock_console_print.assert_any_call("[red][app][/red] line1\n", end="")
    mock_console_print.assert_any_call("[red][app][/red] line2\n", end="")
    mock_console_print.assert_any_call("[red][app] stopped[/red]")

def test_tail_worker_non_interactive(fs, mocker, capsys):
    fs.create_file('/fake/hm/app.log', contents='line1\nline2\n')

    mocker.patch('hm.process.read_pid', side_effect=[1234, 1234, None])
    mocker.patch('hm.process.is_running', return_value=True)

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)
    mocker.patch('hm.tailer.is_interactive', return_value=False)

    hm.tailer.tail_worker('app', 0)

    out, err = capsys.readouterr()
    assert "[app] line1\n" in out
    assert "[app] line2\n" in out
    assert "[app] stopped\n" in out

def test_multi_tail(mocker):
    mock_thread = mocker.patch('threading.Thread')
    mock_sleep = mocker.patch('time.sleep', side_effect=KeyboardInterrupt())

    hm.tailer.multi_tail(['app1', 'app2'])

    assert mock_thread.call_count == 2

def test_tail_worker_wait_for_file(fs, mocker, capsys):
    mocker.patch('hm.tailer.is_interactive', return_value=False)

    sleep_counter = 0
    def mock_sleep(s):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter == 2:
            fs.create_file('/fake/hm/app.log', contents='line1\n')

    mocker.patch('time.sleep', side_effect=mock_sleep)
    mocker.patch('hm.process.read_pid', return_value=None)

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)

    hm.tailer.tail_worker('app', 0)

    out, err = capsys.readouterr()
    assert "[app] line1\n" in out

def test_tail_worker_not_running_no_pid(fs, mocker, capsys):
    fs.create_file('/fake/hm/app.log', contents='line\n')

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)
    mocker.patch('hm.process.read_pid', return_value=1234)
    mocker.patch('hm.tailer.is_interactive', return_value=False)

    mocker.patch('hm.process.is_running', side_effect=[True, False])
    mock_sleep = mocker.patch('time.sleep')

    hm.tailer.tail_worker('app', 0)

    out, err = capsys.readouterr()
    assert "[app] stopped\n" in out
