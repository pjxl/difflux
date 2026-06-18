from __future__ import annotations

import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "difflux"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_ENV_VAR: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def load_config_file() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def bootstrap_config() -> None:
    """Populate os.environ from config.toml for any key not already set."""
    data = load_config_file()
    for provider, env_var in _ENV_VAR.items():
        entry = data.get("keys", {}).get(provider, {})
        key = entry.get("key", "")
        if key and env_var not in os.environ:
            os.environ[env_var] = key


def save_api_key(provider: str, key: str, label: str = "") -> None:
    """Write key+label for provider to config.toml and inject into os.environ."""
    env_var = _ENV_VAR.get(provider)
    if env_var is None:
        raise ValueError(f"Unknown provider: {provider!r}")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)

    data = load_config_file()
    data.setdefault("keys", {})[provider] = {"key": key, "label": label}
    _write_config(data)

    os.environ[env_var] = key


def delete_api_key(provider: str) -> None:
    """Remove a provider's key from config.toml and os.environ."""
    env_var = _ENV_VAR.get(provider)
    data = load_config_file()
    data.get("keys", {}).pop(provider, None)
    _write_config(data)
    if env_var:
        os.environ.pop(env_var, None)


def get_wallet() -> dict[str, dict[str, str]]:
    """Return {provider: {key, label}} for all stored entries."""
    return load_config_file().get("keys", {})


def _toml_escape(value: str) -> str:
    """Escape a string for safe inclusion in a TOML basic string."""
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _write_config(data: dict) -> None:
    lines: list[str] = []
    for provider, entry in data.get("keys", {}).items():
        lines.append(f"[keys.{provider}]\n")
        lines.append(f'key = "{_toml_escape(entry.get("key", ""))}"\n')
        lines.append(f'label = "{_toml_escape(entry.get("label", ""))}"\n')
        lines.append("\n")
    CONFIG_FILE.write_text("".join(lines))
    CONFIG_FILE.chmod(0o600)
