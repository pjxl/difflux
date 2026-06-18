from __future__ import annotations

import os
import tomllib

import pytest

from difflux import config_file

_DEFAULT_ENV_VARS = ["DIFFLUX_PROVIDER", "DIFFLUX_BASE_URL", "DIFFLUX_MODEL"]
_KEY_ENV_VARS = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point CONFIG_DIR/CONFIG_FILE at a temp location and clean env around the test."""
    config_dir = tmp_path / "difflux"
    config_file_path = config_dir / "config.toml"
    monkeypatch.setattr(config_file, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_file, "CONFIG_FILE", config_file_path)

    for var in _DEFAULT_ENV_VARS + _KEY_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    yield config_file_path


def test_save_defaults_round_trips(isolated_config):
    config_file.save_defaults(
        provider="litellm", base_url="https://gw.example.com", model="gpt-4o"
    )
    assert config_file.load_defaults() == {
        "provider": "litellm",
        "base_url": "https://gw.example.com",
        "model": "gpt-4o",
    }


def test_save_defaults_partial_merge(isolated_config):
    config_file.save_defaults(base_url="https://gw.example.com")
    config_file.save_defaults(model="gpt-4o")

    defaults = config_file.load_defaults()
    assert defaults["base_url"] == "https://gw.example.com"
    assert defaults["model"] == "gpt-4o"
    assert "provider" not in defaults


def test_save_defaults_sets_environ_immediately(isolated_config):
    config_file.save_defaults(
        provider="litellm", base_url="https://gw.example.com", model="gpt-4o"
    )
    assert os.environ["DIFFLUX_PROVIDER"] == "litellm"
    assert os.environ["DIFFLUX_BASE_URL"] == "https://gw.example.com"
    assert os.environ["DIFFLUX_MODEL"] == "gpt-4o"


def test_save_defaults_partial_does_not_set_unspecified_env(isolated_config):
    config_file.save_defaults(model="gpt-4o")
    assert os.environ["DIFFLUX_MODEL"] == "gpt-4o"
    assert "DIFFLUX_PROVIDER" not in os.environ
    assert "DIFFLUX_BASE_URL" not in os.environ


def test_bootstrap_populates_default_env_vars(isolated_config):
    config_file.save_defaults(
        provider="litellm", base_url="https://gw.example.com", model="gpt-4o"
    )
    # Clear what save_defaults set so bootstrap is exercised from disk.
    for var in _DEFAULT_ENV_VARS:
        os.environ.pop(var, None)

    config_file.bootstrap_config()
    assert os.environ["DIFFLUX_PROVIDER"] == "litellm"
    assert os.environ["DIFFLUX_BASE_URL"] == "https://gw.example.com"
    assert os.environ["DIFFLUX_MODEL"] == "gpt-4o"


def test_bootstrap_does_not_overwrite_preset_env(isolated_config, monkeypatch):
    config_file.save_defaults(provider="litellm", model="gpt-4o")
    for var in _DEFAULT_ENV_VARS:
        os.environ.pop(var, None)

    monkeypatch.setenv("DIFFLUX_PROVIDER", "preset-provider")
    config_file.bootstrap_config()

    # Env wins over persisted default.
    assert os.environ["DIFFLUX_PROVIDER"] == "preset-provider"
    # But unset ones still come from defaults.
    assert os.environ["DIFFLUX_MODEL"] == "gpt-4o"


def test_keys_and_defaults_coexist(isolated_config):
    config_file.save_api_key("anthropic", "sk-test-123", label="work")
    config_file.save_defaults(
        provider="anthropic", base_url="https://gw.example.com", model="claude"
    )

    # Both reload correctly.
    assert config_file.get_wallet()["anthropic"] == {
        "key": "sk-test-123",
        "label": "work",
    }
    assert config_file.load_defaults() == {
        "provider": "anthropic",
        "base_url": "https://gw.example.com",
        "model": "claude",
    }

    # File is valid TOML parseable by tomllib.
    with open(isolated_config, "rb") as f:
        data = tomllib.load(f)
    assert data["defaults"]["provider"] == "anthropic"
    assert data["keys"]["anthropic"]["key"] == "sk-test-123"


def test_load_defaults_empty_when_no_file(isolated_config):
    assert config_file.load_defaults() == {}
