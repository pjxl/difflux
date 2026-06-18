from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from difflux.cli import _needs_setup
from difflux.tui.setup import SetupResult, SetupWizardApp, apply_setup


class TestApplySetup:
    def test_persists_defaults_then_key(self):
        result = SetupResult(
            provider="anthropic",
            base_url="https://gw.example.com",
            model="claude-opus-4-8",
            key="sk-ant-xyz",
            label="work",
        )
        fake_cf = MagicMock()
        with patch("difflux.config_file", fake_cf):
            apply_setup(result)

        fake_cf.save_defaults.assert_called_once_with(
            provider="anthropic",
            base_url="https://gw.example.com",
            model="claude-opus-4-8",
        )
        fake_cf.save_api_key.assert_called_once_with("anthropic", "sk-ant-xyz", "work")

    def test_direct_provider_passes_none_base_url(self):
        result = SetupResult(
            provider="openai",
            base_url=None,
            model="gpt-4o",
            key="sk-openai",
        )
        fake_cf = MagicMock()
        with patch("difflux.config_file", fake_cf):
            apply_setup(result)

        fake_cf.save_defaults.assert_called_once_with(
            provider="openai", base_url=None, model="gpt-4o"
        )
        fake_cf.save_api_key.assert_called_once_with("openai", "sk-openai", "")


class TestNeedsSetup:
    def _patch_env(self, monkeypatch, *, tty=True, env=None, config=None):
        monkeypatch.setattr("sys.stdout.isatty", lambda: tty)
        monkeypatch.setattr("os.environ", env if env is not None else {})
        monkeypatch.setattr(
            "difflux.config_file.load_config_file",
            lambda: (config if config is not None else {}),
        )

    def test_cold_start_returns_true(self, monkeypatch):
        self._patch_env(monkeypatch, tty=True, env={}, config={})
        assert _needs_setup(no_tui=False) is True

    def test_anthropic_key_set_returns_false(self, monkeypatch):
        self._patch_env(monkeypatch, env={"ANTHROPIC_API_KEY": "sk"})
        assert _needs_setup(no_tui=False) is False

    def test_openai_key_set_returns_false(self, monkeypatch):
        self._patch_env(monkeypatch, env={"OPENAI_API_KEY": "sk"})
        assert _needs_setup(no_tui=False) is False

    def test_non_empty_config_returns_false(self, monkeypatch):
        self._patch_env(monkeypatch, config={"keys": {"anthropic": {"key": "x"}}})
        assert _needs_setup(no_tui=False) is False

    def test_not_a_tty_returns_false(self, monkeypatch):
        self._patch_env(monkeypatch, tty=False)
        assert _needs_setup(no_tui=False) is False

    def test_no_tui_returns_false(self, monkeypatch):
        self._patch_env(monkeypatch, tty=True, env={}, config={})
        assert _needs_setup(no_tui=True) is False


class TestWizardFlow:
    """Drive the Textual wizard end-to-end to catch step-transition regressions
    (e.g. DuplicateIds when remounting #hint/#tip)."""

    def _run(self, coro):
        return asyncio.run(coro)

    def test_gateway_flow_completes(self):
        async def drive():
            app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
            async with app.run_test() as pilot:
                # choice step: move to "Custom gateway" (index 2) and select it
                await pilot.press("j", "j", "enter")
                # base-url step — this transition is where DuplicateIds used to fire
                app.query_one("#base-url-input").value = "https://gw.example/v1"
                await pilot.press("enter")
                # model step
                app.query_one("#model-input").value = "global-gemini-2.5-flash"
                await pilot.press("enter")
                # key step
                app.query_one("#key-input").value = "sk-litellm-xyz"
                await pilot.press("enter")
            return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.provider == "openai"  # gateway => OpenAI-compatible
        assert result.base_url == "https://gw.example/v1"
        assert result.model == "global-gemini-2.5-flash"
        assert result.key == "sk-litellm-xyz"

    def test_direct_anthropic_flow_completes(self):
        async def drive():
            app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
            async with app.run_test() as pilot:
                # choice step: select "Direct Anthropic" (index 0)
                await pilot.press("enter")
                # model step (prefilled with the default) — accept it
                await pilot.press("enter")
                # key step
                app.query_one("#key-input").value = "sk-ant-xyz"
                await pilot.press("enter")
            return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.provider == "anthropic"
        assert result.base_url is None
        assert result.model == "claude-opus-4-8"
        assert result.key == "sk-ant-xyz"

    def test_escape_cancels(self):
        async def drive():
            app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
            async with app.run_test() as pilot:
                await pilot.press("escape")
            return app.return_value

        assert self._run(drive()) is None
