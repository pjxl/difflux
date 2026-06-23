from __future__ import annotations

import os
import tempfile
import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "difflux"
CONFIG_FILE = CONFIG_DIR / "config.toml"

_ENV_VAR: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "github": "GITHUB_TOKEN",
}

_DEFAULTS_ENV_VAR: dict[str, str] = {
    "provider": "DIFFLUX_PROVIDER",
    "base_url": "DIFFLUX_BASE_URL",
    "model": "DIFFLUX_MODEL",
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

    defaults = data.get("defaults", {})
    for field, env_var in _DEFAULTS_ENV_VAR.items():
        value = defaults.get(field, "")
        if value and env_var not in os.environ:
            os.environ[env_var] = value


def save_api_key(provider: str, key: str, label: str = "") -> None:
    """Write key+label for provider to config.toml and inject into os.environ."""
    env_var = _ENV_VAR.get(provider)
    if env_var is None:
        raise ValueError(f"Unknown provider: {provider!r}")

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


# TODO(#5 org distribution): an internal install wrapper could pre-seed
# [defaults] for a whole org (e.g. Etsy LiteLLM: provider/base_url/model) by
# calling save_defaults(...) at install time, so users skip the first-run
# wizard entirely. Keep Etsy/org specifics OUT of this repo — the wrapper lives
# in an internal channel and only calls this public API. See the menu/plan in
# ~/.claude/plans/onboarding-friction-3-4-5.md (#5).
def save_defaults(
    *,
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> None:
    """Merge non-None defaults into [defaults] in config.toml and inject into os.environ."""
    data = load_config_file()
    defaults = data.setdefault("defaults", {})

    updates = {"provider": provider, "base_url": base_url, "model": model}
    for field, value in updates.items():
        if value is None:
            continue
        defaults[field] = value
        os.environ[_DEFAULTS_ENV_VAR[field]] = value

    _write_config(data)


def load_defaults() -> dict:
    """Return the [defaults] table as a dict (subset of provider/base_url/model)."""
    return load_config_file().get("defaults", {})


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
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)

    lines: list[str] = []

    # A top-level [defaults] table must be emitted before any [keys.*] tables:
    # TOML top-level keys belong to the most recently declared table header.
    defaults = data.get("defaults", {})
    if defaults:
        lines.append("[defaults]\n")
        for field in ("provider", "base_url", "model"):
            if field in defaults:
                lines.append(f'{field} = "{_toml_escape(defaults[field])}"\n')
        lines.append("\n")

    for provider, entry in data.get("keys", {}).items():
        lines.append(f"[keys.{provider}]\n")
        lines.append(f'key = "{_toml_escape(entry.get("key", ""))}"\n')
        lines.append(f'label = "{_toml_escape(entry.get("label", ""))}"\n')
        lines.append("\n")

    content = "".join(lines).encode()
    fd, tmp = tempfile.mkstemp(dir=CONFIG_DIR, prefix=".config_", suffix=".toml.tmp")
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, content)
    finally:
        os.close(fd)
    Path(tmp).replace(CONFIG_FILE)
