import pytest
from pathlib import Path
import hm.discovery
import hm.config

@pytest.fixture(autouse=True)
def setup_fs(fs):
    """Use pyfakefs for all discovery tests."""
    fs.create_dir('/fake/project')
    hm.discovery.PROJECT_ROOT = Path('/fake/project')
    hm.config.PROJECT_ROOT = Path('/fake/project')
    yield fs

def test_discover_services_no_files():
    services = hm.discovery.discover_services()
    assert services == {}

def test_discover_services_valid_dependencies(fs):
    fs.create_file('/fake/project/app.hm', contents='# depends_on: db, cache \n# some other comment\n')
    fs.create_file('/fake/project/db.hm', contents='# depends_on: network\n')
    fs.create_file('/fake/project/cache.hm', contents='') # no dependencies

    services = hm.discovery.discover_services()

    assert 'app' in services
    assert services['app']['path'] == Path('/fake/project/app.hm')
    assert services['app']['dependencies'] == ['db', 'cache']

    assert 'db' in services
    assert services['db']['dependencies'] == ['network']

    assert 'cache' in services
    assert services['cache']['dependencies'] == []

def test_discover_services_invalid_file_read(fs, mocker):
    fs.create_file('/fake/project/app.hm', contents='')
    mocker.patch('builtins.open', side_effect=PermissionError())
    services = hm.discovery.discover_services()
    assert 'app' in services
    assert services['app']['dependencies'] == []

def test_discover_services_empty_depends_on(fs):
    fs.create_file('/fake/project/app.hm', contents='# depends_on:  \n')
    services = hm.discovery.discover_services()
    assert services['app']['dependencies'] == []
