import pytest
import os
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

class ExitLoop(Exception):
    pass

def test_tail_worker_robust_inode_rotation(fs, mocker):
    """
    Proven test for Inode-following. 
    Simulates: Read file 1 -> File 1 moved, new File 2 created -> Read File 2.
    """
    logfile = Path('/fake/hm/app.log')
    fs.create_file(logfile, contents=b"content 1\n")
    
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    
    call_count = 0
    def mock_sleep(s):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # SIMULATE ROTATION: Move old, create new
            # In pyfakefs, unlinking and recreating changes the inode
            logfile.unlink()
            fs.create_file(logfile, contents=b"content 2\n")
        elif call_count == 2:
            raise ExitLoop()

    mocker.patch('time.sleep', side_effect=mock_sleep)

    with pytest.raises(ExitLoop):
        hm.tailer.tail_worker('app', 0)

    # Check that we got BOTH pieces of content across the rotation
    all_writes = b"".join([c.args[0] for c in mock_write.call_args_list])
    assert b"content 1\n" in all_writes
    assert b"logs rotated (new file)" in all_writes
    assert b"content 2\n" in all_writes

def test_tail_worker_truncation_no_rotation(fs, mocker):
    """
    Simulates a restart that truncates the file WITHOUT changing the inode.
    """
    logfile = Path('/fake/hm/app.log')
    fs.create_file(logfile, contents=b"old content\n")
    
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    
    call_count = 0
    def mock_sleep(s):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # SIMULATE TRUNCATION: Same file, smaller size
            with open(logfile, "wb") as f:
                f.write(b"new\n")
        elif call_count == 2:
            raise ExitLoop()

    mocker.patch('time.sleep', side_effect=mock_sleep)

    with pytest.raises(ExitLoop):
        hm.tailer.tail_worker('app', 0)

    all_writes = b"".join([c.args[0] for c in mock_write.call_args_list])
    assert b"old content\n" in all_writes
    assert b"logs truncated" in all_writes
    assert b"new\n" in all_writes

def test_tail_worker_large_history_seek(fs, mocker):
    logfile = Path('/fake/hm/app.log')
    # Create file larger than 2KB
    content = b"header\n" + (b"filler\n" * 400) + b"footer\n"
    fs.create_file(logfile, contents=content)
    
    mock_write = mocker.patch('sys.stdout.buffer.write')
    mocker.patch('sys.stdout.buffer.flush')
    mocker.patch('time.sleep', side_effect=ExitLoop())

    with pytest.raises(ExitLoop):
        hm.tailer.tail_worker('app', 0)
    
    all_writes = b"".join([call.args[0] for call in mock_write.call_args_list])
    assert b"footer\n" in all_writes
    assert b"header\n" not in all_writes
