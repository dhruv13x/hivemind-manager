import pytest
import os
import threading
import time
import sys
import io
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

def test_tail_worker_binary(fs, mocker):
    content = b"line1\n\rline2\n"
    fs.create_file('/fake/hm/app.log', contents=content)

    mocker.patch('hm.process.read_pid', side_effect=[1234, 1234, None])
    mocker.patch('hm.process.is_running', return_value=True)

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)
    
    # Mock sys.stdout.buffer.write
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    
    # Mock print to capture stopped message
    mock_print = mocker.patch('builtins.print')
    mocker.patch('time.sleep')

    hm.tailer.tail_worker('app', 0)

    # Verify binary content
    # We check that at least one call contained our content
    # In this mock setup, it's usually one big read
    mock_write.assert_any_call(content)
    
    # Verify stopped message
    mock_print.assert_any_call("[app] stopped")

def test_multi_tail(mocker):
    mock_thread = mocker.patch('threading.Thread')
    mock_sleep = mocker.patch('time.sleep', side_effect=KeyboardInterrupt())

    hm.tailer.multi_tail(['app1', 'app2'])

    assert mock_thread.call_count == 2

def test_tail_worker_wait_for_file(fs, mocker):
    sleep_counter = 0
    def mock_sleep(s):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter == 2:
            fs.create_file('/fake/hm/app.log', contents=b"line1\n")

    mocker.patch('time.sleep', side_effect=mock_sleep)
    mocker.patch('hm.process.read_pid', return_value=None)

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)
    
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    mock_print = mocker.patch('builtins.print')

    hm.tailer.tail_worker('app', 0)

    mock_write.assert_any_call(b"line1\n")
    mock_print.assert_any_call("[app] stopped")

def test_tail_worker_not_running_no_pid(fs, mocker):
    fs.create_file('/fake/hm/app.log', contents=b'line\n')

    original_open = open
    def mock_open(*args, **kwargs):
        f = original_open(*args, **kwargs)
        original_seek = f.seek
        f.seek = lambda offset, whence=0: original_seek(0, 0) if whence == os.SEEK_END else original_seek(offset, whence)
        return f

    mocker.patch('builtins.open', side_effect=mock_open)
    mocker.patch('hm.process.read_pid', return_value=1234)

    mocker.patch('hm.process.is_running', side_effect=[True, False])
    
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    mock_print = mocker.patch('builtins.print')
    mocker.patch('time.sleep')

    hm.tailer.tail_worker('app', 0)

    mock_write.assert_any_call(b"line\n")
    mock_print.assert_any_call("[app] stopped")
