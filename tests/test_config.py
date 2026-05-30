import pytest
import os
import sys
from pathlib import Path

@pytest.fixture
def clean_config(fs):
    if 'hm.config' in sys.modules:
        del sys.modules['hm.config']
    yield fs
    if 'hm.config' in sys.modules:
        del sys.modules['hm.config']

def test_config_env_root(clean_config, monkeypatch):
    clean_config.create_dir('/fake/env/root')
    monkeypatch.setenv("HM_PROJECT_ROOT", "/fake/env/root")
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/env/root"

def test_config_project_anchor_git(clean_config, monkeypatch):
    clean_config.create_dir('/fake/repo/.git')
    monkeypatch.chdir('/fake/repo')
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/repo"

def test_config_project_anchor_pyproject(clean_config, monkeypatch):
    clean_config.create_dir('/fake/repo/subdir')
    clean_config.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]\nhome_dir = "hm_dir"\nrestart_delay = 5.0')
    monkeypatch.chdir('/fake/repo/subdir')
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/repo"
    assert hm.config.RESTART_DELAY == 5.0
    assert str(hm.config.BASE_DIR) == "/fake/repo/hm_dir"

def test_config_project_anchor_pyproject_invalid(clean_config, monkeypatch):
    clean_config.create_dir('/fake/repo')
    clean_config.create_file('/fake/repo/pyproject.toml', contents='[tool.other]\nval = 1')
    monkeypatch.chdir('/fake/repo')
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/repo"

def test_config_project_anchor_pyproject_parse_error(clean_config, monkeypatch):
    clean_config.create_dir('/fake/repo')
    clean_config.create_file('/fake/repo/pyproject.toml', contents='[[[invalid toml')
    monkeypatch.chdir('/fake/repo')
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/repo"

def test_config_defaults(clean_config, monkeypatch):
    clean_config.create_dir('/fake/empty')
    monkeypatch.chdir('/fake/empty')
    import hm.config
    assert str(hm.config.BASE_DIR) == "/fake/empty/hm"
    assert hm.config.HIVEMIND_BIN == "hivemind"
    assert hm.config.RESTART_DELAY == 1.0
    assert hm.config.MAX_RESTART_DELAY == 10.0
    assert hm.config.PRESERVE_LOGS is False
    assert hm.config.MAX_LOG_HISTORY == 5
    assert hm.config.MAX_LOG_SIZE_MB == 0.0

def test_config_env_overrides(clean_config, monkeypatch):
    clean_config.create_dir('/fake/empty')
    monkeypatch.chdir('/fake/empty')
    monkeypatch.setenv("HM_HOME_DIR", "/absolute/hm/dir")
    monkeypatch.setenv("HM_HIVEMIND_BIN", "custom_hm")
    monkeypatch.setenv("HM_RESTART_DELAY", "2.5")
    monkeypatch.setenv("HM_MAX_RESTART_DELAY", "20.5")
    monkeypatch.setenv("HM_PRESERVE_LOGS", "true")
    monkeypatch.setenv("HM_MAX_LOG_HISTORY", "10")
    monkeypatch.setenv("HM_MAX_LOG_SIZE_MB", "100.0")
    import hm.config
    assert str(hm.config.BASE_DIR) == "/absolute/hm/dir"
    assert hm.config.HIVEMIND_BIN == "custom_hm"
    assert hm.config.RESTART_DELAY == 2.5
    assert hm.config.MAX_RESTART_DELAY == 20.5
    assert hm.config.PRESERVE_LOGS is True
    assert hm.config.MAX_LOG_HISTORY == 10
    assert hm.config.MAX_LOG_SIZE_MB == 100.0

def test_config_env_overrides_invalid_types(clean_config, monkeypatch):
    clean_config.create_dir('/fake/empty')
    monkeypatch.chdir('/fake/empty')
    monkeypatch.setenv("HM_RESTART_DELAY", "not_a_float")
    monkeypatch.setenv("HM_MAX_RESTART_DELAY", "not_a_float")
    monkeypatch.setenv("HM_MAX_LOG_HISTORY", "not_an_int")
    monkeypatch.setenv("HM_MAX_LOG_SIZE_MB", "not_a_float")
    import hm.config
    assert hm.config.RESTART_DELAY == 1.0
    assert hm.config.MAX_RESTART_DELAY == 10.0
    assert hm.config.MAX_LOG_HISTORY == 5
    assert hm.config.MAX_LOG_SIZE_MB == 50.0

def test_get_env_bool(clean_config):
    import hm.config
    assert hm.config.get_env_bool("NON_EXISTENT", True) is True
    assert hm.config.get_env_bool("NON_EXISTENT", False) is False
    os.environ["MOCK_BOOL_TEST_TRUE"] = "yes"
    assert hm.config.get_env_bool("MOCK_BOOL_TEST_TRUE", False) is True

def test_config_tomllib_import_error(clean_config, monkeypatch, mocker):
    clean_config.create_dir('/fake/repo')
    clean_config.create_file('/fake/repo/pyproject.toml', contents='[tool.hm]\nhome_dir = "hm_dir"')
    monkeypatch.chdir('/fake/repo')
    import builtins
    original_import = builtins.__import__
    def mock_import(name, *args, **kwargs):
        if name in ('tomllib', 'tomli'):
            if name == 'tomllib':
                raise ImportError()
        return original_import(name, *args, **kwargs)
    mocker.patch('builtins.__import__', side_effect=mock_import)
    import sys
    sys.modules['tomli'] = mocker.MagicMock()
    import hm.config
    assert str(hm.config.PROJECT_ROOT) == "/fake/repo"

def test_get_env_bool_boolean(clean_config, monkeypatch):
    import hm.config
    monkeypatch.setenv("MOCK_BOOL_LITERAL", "True")
    import os
    original_get = os.environ.get
    def mock_get(key, default=None):
        if key == "MOCK_BOOL_LITERAL":
            return True
        return original_get(key, default)
    hm.config.os.environ.get = mock_get
    assert hm.config.get_env_bool("MOCK_BOOL_LITERAL", False) is True
