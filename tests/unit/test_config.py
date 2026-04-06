from wxtools.runtime.config import Config, load_config


def test_default_config_values():
    cfg = Config()
    assert cfg.get("default_limit") == 100
    assert cfg.get("log_level") == "WARNING"
    assert cfg.get("query_timeout") == 30
    assert cfg.get("keystore_protection") == "auto"


def test_config_from_dict():
    cfg = Config(overrides={"default_limit": 50, "log_level": "DEBUG"})
    assert cfg.get("default_limit") == 50
    assert cfg.get("log_level") == "DEBUG"


def test_config_get_unknown_key_returns_default():
    cfg = Config()
    assert cfg.get("nonexistent", "fallback") == "fallback"


def test_config_home_dir(tmp_path):
    cfg = Config(overrides={"_home": str(tmp_path / ".wxtools")})
    assert cfg.home_dir == tmp_path / ".wxtools"


def test_config_validates_limit():
    cfg = Config(overrides={"default_limit": 99999})
    assert cfg.get("default_limit") == 10000  # clamped to max


def test_load_config_from_yaml(tmp_path):
    config_dir = tmp_path / ".wxtools"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("default_limit: 200\nlog_level: INFO\n")
    cfg = load_config(home=config_dir)
    assert cfg.get("default_limit") == 200
    assert cfg.get("log_level") == "INFO"


def test_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("WXTOOLS_LOG_LEVEL", "DEBUG")
    cfg = load_config(home=tmp_path / ".wxtools")
    assert cfg.get("log_level") == "DEBUG"


def test_config_session_dir(tmp_path):
    cfg = Config(overrides={"_home": str(tmp_path / ".wxtools")})
    assert cfg.session_dir == tmp_path / ".wxtools" / "session"
