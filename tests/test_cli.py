from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

import difflux.cli as cli


class _StopMain(Exception):
    """Raised by the fake wizard to halt main() once ordering is observable."""


def _fake_args(**overrides):
    defaults = dict(source=None, model=None, provider=None, base_url=None, no_tui=False)
    defaults.update(overrides)
    return MagicMock(**defaults)


def test_setup_wizard_runs_after_stdin_drained_and_reattached(monkeypatch):
    """Regression guard: on the `git diff | difflux` cold start, the setup wizard
    must launch only after the piped diff is consumed and FD 0 is reattached to
    /dev/tty — otherwise Textual reads the diff as keystrokes."""
    calls: list[str] = []

    monkeypatch.setattr(
        cli, "_make_arg_parser", lambda: MagicMock(parse_args=lambda: _fake_args())
    )

    # stdin is a pipe (not a tty), so the reattach branch is exercised.
    fake_stdin = MagicMock()
    fake_stdin.isatty.return_value = False
    fake_stdin.fileno.return_value = 0
    monkeypatch.setattr(sys, "__stdin__", fake_stdin)

    def fake_resolve_diff(source):
        calls.append("diff")
        return "diff --git a/x b/x\n@@ -1 +1 @@\n-a\n+b\n"

    monkeypatch.setattr(cli, "_resolve_diff", fake_resolve_diff)

    # Fake the /dev/tty reopen + dup2 so the reattach is observable and never
    # depends on a real controlling terminal being present.
    real_open = open

    def fake_open(path, *a, **k):
        if path == "/dev/tty":
            calls.append("reattach")
            tty = MagicMock()
            tty.fileno.return_value = 99
            return tty
        return real_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", fake_open)
    monkeypatch.setattr("os.dup2", lambda *a, **k: None)

    monkeypatch.setattr(cli, "_needs_setup", lambda *, no_tui: True)

    class FakeWizard:
        def __init__(self, **kwargs):
            pass

        def run(self):
            calls.append("wizard")
            raise _StopMain()

    monkeypatch.setattr("difflux.tui.setup.SetupWizardApp", FakeWizard)

    with pytest.raises(_StopMain):
        cli.main()

    assert calls == ["diff", "reattach", "wizard"]


def test_setup_skipped_when_not_needed(monkeypatch):
    """When setup isn't needed, the wizard is never constructed/run, and the
    diff is still consumed first."""
    calls: list[str] = []

    monkeypatch.setattr(
        cli,
        "_make_arg_parser",
        lambda: MagicMock(
            parse_args=lambda: _fake_args(model="claude-opus-4-8", provider="anthropic")
        ),
    )

    fake_stdin = MagicMock()
    fake_stdin.isatty.return_value = True  # interactive stdin; no reattach needed
    monkeypatch.setattr(sys, "__stdin__", fake_stdin)

    def fake_resolve_diff(source):
        calls.append("diff")
        return "diff --git a/x b/x\n@@ -1 +1 @@\n-a\n+b\n"

    monkeypatch.setattr(cli, "_resolve_diff", fake_resolve_diff)
    monkeypatch.setattr(cli, "_needs_setup", lambda *, no_tui: False)

    def boom(**kwargs):
        raise AssertionError("wizard must not be constructed when setup isn't needed")

    monkeypatch.setattr("difflux.tui.setup.SetupWizardApp", boom)

    # Stop main() right after the wizard decision point so we don't run clustering.
    def fake_parse_diff(text):
        calls.append("parse")
        raise _StopMain()

    monkeypatch.setattr(cli, "parse_diff", fake_parse_diff)

    with pytest.raises(_StopMain):
        cli.main()

    assert calls == ["diff", "parse"]
