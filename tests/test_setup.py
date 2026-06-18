from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from difflux.cli import _needs_setup
from difflux.tui.setup import (
    SetupResult,
    SetupWizardApp,
    _rank_models,
    apply_setup,
)


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


class TestRankModels:
    def test_openai_blocklist_and_ordering(self):
        ids = [
            "gpt-4o",
            "text-embedding-3-large",
            "whisper-1",
            "dall-e-3",
            "o3-mini",
            "tts-1",
            "babbage-002",
        ]
        ranked = _rank_models("openai", ids)
        # Non-chat families are dropped by the soft blocklist.
        assert "text-embedding-3-large" not in ranked
        assert "whisper-1" not in ranked
        assert "dall-e-3" not in ranked
        assert "tts-1" not in ranked
        # gpt-/o-series come first, before the leftover (babbage-002).
        assert set(ranked) == {"gpt-4o", "o3-mini", "babbage-002"}
        assert ranked.index("gpt-4o") < ranked.index("babbage-002")
        assert ranked.index("o3-mini") < ranked.index("babbage-002")

    def test_gateway_no_name_filtering(self):
        ids = ["global-gemini-2.5-flash", "claude-3-5-sonnet", "text-embedding-3"]
        ranked = _rank_models("openai", ids, base_url="https://gw.example/v1")
        # Gateway path keeps everything (even "embedding"); sorted alphabetically.
        assert set(ranked) == set(ids)
        assert ranked == sorted(ids)

    def test_anthropic_keeps_all(self):
        ids = ["claude-3-5-haiku", "claude-opus-4-8", "claude-3-5-sonnet"]
        ranked = _rank_models("anthropic", ids)
        assert set(ranked) == set(ids)
        # Newest-first proxy: reverse-lexical.
        assert ranked == sorted(ids, reverse=True)


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
    (e.g. DuplicateIds when remounting #hint/#tip). list_models is patched so no
    network occurs; the threaded fetch worker is awaited via pilot/workers."""

    def _run(self, coro):
        return asyncio.run(coro)

    async def _settle_picker(self, app, pilot):
        """Let the fetch worker finish and the model picker mount."""
        await app.workers.wait_for_complete()
        await pilot.pause()

    def test_direct_anthropic_flow_completes(self):
        async def drive():
            fake = ["claude-3-5-haiku", "claude-opus-4-8", "claude-3-5-sonnet"]
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    # choice: Direct Anthropic (index 0)
                    await pilot.press("enter")
                    # key step (now precedes model)
                    app.query_one("#key-input").value = "sk-ant-xyz"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    # model picker: select claude-opus-4-8 from the OptionList
                    option_list = app.query_one("#model-list")
                    idx = list(option_list.options).index(
                        next(o for o in option_list.options if o.id == "claude-opus-4-8")
                    )
                    option_list.highlighted = idx
                    await pilot.pause()
                    option_list.focus()
                    await pilot.pause()
                    option_list.action_select()
                    await pilot.pause()
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.provider == "anthropic"
        assert result.base_url is None
        assert result.model == "claude-opus-4-8"
        assert result.key == "sk-ant-xyz"

    def test_direct_openai_flow_completes(self):
        async def drive():
            fake = ["gpt-4o", "text-embedding-3-large", "o3-mini"]
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    # choice: Direct OpenAI (index 1)
                    await pilot.press("j", "enter")
                    app.query_one("#key-input").value = "sk-openai"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    option_list = app.query_one("#model-list")
                    # embedding model is filtered out of the default view.
                    shown_ids = [o.id for o in option_list.options]
                    assert "text-embedding-3-large" not in shown_ids
                    idx = shown_ids.index("gpt-4o")
                    option_list.highlighted = idx
                    option_list.focus()
                    await pilot.pause()
                    option_list.action_select()
                    await pilot.pause()
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.provider == "openai"
        assert result.base_url is None
        assert result.model == "gpt-4o"
        assert result.key == "sk-openai"

    def test_gateway_flow_completes(self):
        async def drive():
            fake = ["global-gemini-2.5-flash", "claude-3-5-sonnet"]
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    # choice: Custom gateway (index 2)
                    await pilot.press("j", "j", "enter")
                    # base-url step (this transition is where DuplicateIds used to fire)
                    app.query_one("#base-url-input").value = "https://gw.example/v1"
                    await pilot.press("enter")
                    # key step
                    app.query_one("#key-input").value = "sk-litellm-xyz"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    option_list = app.query_one("#model-list")
                    shown_ids = [o.id for o in option_list.options]
                    idx = shown_ids.index("global-gemini-2.5-flash")
                    option_list.highlighted = idx
                    option_list.focus()
                    await pilot.pause()
                    option_list.action_select()
                    await pilot.pause()
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.provider == "openai"  # gateway => OpenAI-compatible
        assert result.base_url == "https://gw.example/v1"
        assert result.model == "global-gemini-2.5-flash"
        assert result.key == "sk-litellm-xyz"

    def test_duplicate_model_ids_do_not_crash(self):
        """A gateway (e.g. LiteLLM) can list the same id twice; the picker must
        dedupe rather than crash with DuplicateID (regression)."""
        async def drive():
            fake = ["openai/sora-2", "gpt-4o", "openai/sora-2"]  # duplicate id
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    await pilot.press("j", "j", "enter")  # Custom gateway
                    app.query_one("#base-url-input").value = "https://gw.example"
                    await pilot.press("enter")
                    app.query_one("#key-input").value = "sk-litellm"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    option_list = app.query_one("#model-list")
                    shown_ids = [o.id for o in option_list.options]
                    assert shown_ids.count("openai/sora-2") == 1  # deduped
                    idx = shown_ids.index("gpt-4o")
                    option_list.highlighted = idx
                    option_list.focus()
                    await pilot.pause()
                    option_list.action_select()
                    await pilot.pause()
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.model == "gpt-4o"

    def test_arrow_keys_navigate_and_enter_selects(self):
        """↑/↓ drive the OptionList from the (focused) filter box, and Enter on
        the filter selects the highlighted option (regression: j/k typed into the
        filter and the list wasn't navigable)."""
        async def drive():
            fake = ["claude-3-5-haiku", "claude-opus-4-8", "claude-3-5-sonnet"]
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    await pilot.press("enter")  # Direct Anthropic
                    app.query_one("#key-input").value = "sk-ant-xyz"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    option_list = app.query_one("#model-list")
                    assert option_list.highlighted == 0  # starting anchor
                    ranked = [o.id for o in option_list.options]
                    await pilot.press("down")  # move highlight down by one
                    await pilot.pause()
                    assert option_list.highlighted == 1
                    await pilot.press("enter")  # Enter on the filter selects it
                    await pilot.pause()
                return app.return_value, ranked

        result, ranked = self._run(drive())
        assert result is not None
        assert result.model == ranked[1]

    def test_free_text_fallback_when_list_models_raises(self):
        async def drive():
            with patch(
                "difflux.clusterer.list_models",
                side_effect=RuntimeError("connection refused"),
                create=True,
            ):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    await pilot.press("enter")  # Direct Anthropic
                    app.query_one("#key-input").value = "sk-ant-xyz"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    # Manual fallback free-text input, prefilled with the default.
                    model_input = app.query_one("#model-input")
                    assert model_input.value == "claude-opus-4-8"
                    model_input.value = "claude-custom-model"
                    await pilot.press("enter")
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.model == "claude-custom-model"
        assert result.key == "sk-ant-xyz"

    def test_empty_list_falls_back_to_manual_with_default(self):
        async def drive():
            with patch("difflux.clusterer.list_models", return_value=[], create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    await pilot.press("enter")  # Direct Anthropic
                    app.query_one("#key-input").value = "sk-ant-xyz"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    model_input = app.query_one("#model-input")
                    assert model_input.value == "claude-opus-4-8"
                    await pilot.press("enter")  # accept the prefilled default
                return app.return_value

        result = self._run(drive())
        assert result is not None
        assert result.model == "claude-opus-4-8"

    def test_filter_narrows_and_show_all_restores(self):
        async def drive():
            fake = ["gpt-4o", "gpt-4o-mini", "o3-mini", "babbage-002"]
            with patch("difflux.clusterer.list_models", return_value=fake, create=True):
                app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
                async with app.run_test() as pilot:
                    await pilot.press("j", "enter")  # Direct OpenAI
                    app.query_one("#key-input").value = "sk-openai"
                    await pilot.press("enter")
                    await self._settle_picker(app, pilot)
                    option_list = app.query_one("#model-list")

                    full_default = [o.id for o in option_list.options]
                    assert "gpt-4o" in full_default

                    # Filter narrows to "mini" matches.
                    app.query_one("#model-filter").value = "mini"
                    await pilot.pause()
                    narrowed = [o.id for o in option_list.options]
                    assert set(narrowed) == {"gpt-4o-mini", "o3-mini"}

                    # Clear filter, then Tab to "show all" (unfiltered set,
                    # which for openai still equals the ranked set here, but the
                    # toggle must repopulate the list deterministically).
                    app.query_one("#model-filter").value = ""
                    await pilot.pause()
                    await pilot.press("tab")
                    await pilot.pause()
                    restored = [o.id for o in option_list.options]
                    assert set(restored) == set(fake)
                # Cancel so the test app exits cleanly.
                return None

        self._run(drive())

    def test_escape_cancels(self):
        async def drive():
            app = SetupWizardApp(default_anthropic_model="claude-opus-4-8")
            async with app.run_test() as pilot:
                await pilot.press("escape")
            return app.return_value

        assert self._run(drive()) is None
