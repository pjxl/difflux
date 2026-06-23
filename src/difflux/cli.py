from __future__ import annotations

import argparse
import os
import sys

from difflux.config import DEFAULT_MODEL
from difflux.clusterer import ClusteringError, detect_provider
from difflux.hunks import HunkIndex, parse_diff
from difflux.enrich import build_session
from difflux.render_text import render_overview


def _reopen_stdin_for_tui() -> None:
    """Redirect FD 0 to /dev/tty so Textual sees a live keyboard after stdin was a pipe."""
    if sys.__stdin__.isatty():
        return
    try:
        _tty = open("/dev/tty")
        try:
            os.dup2(_tty.fileno(), sys.__stdin__.fileno())
        finally:
            _tty.close()
    except OSError:
        pass


def _make_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="difflux",
        description="Decompose a git diff into conceptual clusters for review.",
    )
    p.add_argument(
        "source",
        nargs="?",
        help="GitHub PR URL (e.g. https://github.com/owner/repo/pull/123). "
             "Omit to read a diff from stdin.",
    )
    p.add_argument("--model", default=None, help="Override the model to use. Also set via DIFFLUX_MODEL env var.")
    p.add_argument(
        "--provider",
        default=None,
        choices=["anthropic", "openai"],
        help="LLM provider. Auto-detected from model name if omitted. "
             "Also set via DIFFLUX_PROVIDER env var.",
    )
    p.add_argument(
        "--base-url",
        default=None,
        help="Custom API base URL for an OpenAI/Anthropic-compatible gateway (e.g. LiteLLM). "
             "Also set via DIFFLUX_BASE_URL env var.",
    )
    p.add_argument("--no-tui", action="store_true", help="Print plain text instead of launching the TUI.")
    p.add_argument(
        "--reconfigure",
        "--setup",
        dest="reconfigure",
        action="store_true",
        help="Force the first-run setup wizard to run again, even if a config already exists.",
    )
    return p


def _resolve_diff(source: str | None) -> str:
    if source is None:
        if sys.stdin.isatty():
            print("difflux: pipe a git diff or provide a GitHub PR URL.", file=sys.stderr)
            print("  example: git diff HEAD~1 | difflux", file=sys.stderr)
            sys.exit(1)
        from difflux.sources.stdin import read_stdin
        return read_stdin()

    from difflux.sources.github import is_github_pr_url, fetch_pr_diff
    if is_github_pr_url(source):
        return fetch_pr_diff(source, token=os.environ.get("GITHUB_TOKEN"))

    print(f"difflux: unrecognised source '{source}'. Expected a GitHub PR URL or no argument (stdin).", file=sys.stderr)
    sys.exit(1)


def _resolve_provider(provider_arg: str | None, model: str) -> str:
    """Return the concrete provider string, detecting from model name if needed."""
    if provider_arg:
        return provider_arg
    try:
        return detect_provider(model)
    except ClusteringError as e:
        print(f"difflux: {e}", file=sys.stderr)
        sys.exit(1)


def _ensure_github_token(*, no_tui: bool) -> None:
    """Guarantee GITHUB_TOKEN is in os.environ. Prompts if missing and persists the result."""
    if os.environ.get("GITHUB_TOKEN"):
        return
    import subprocess
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        os.environ["GITHUB_TOKEN"] = result.stdout.strip()
        return
    use_tui = not no_tui and sys.stdout.isatty()
    if use_tui:
        from difflux.tui.key_entry import KeyEntryApp
        token = KeyEntryApp("github").run()
    else:
        import getpass
        print(
            "difflux: GitHub token required for private repos"
            " (https://github.com/settings/tokens)",
            file=sys.stderr,
        )
        try:
            token = getpass.getpass("GITHUB_TOKEN: ")
        except (KeyboardInterrupt, EOFError):
            token = None
    token = (token or "").strip()
    if not token:
        print("difflux: no token provided, exiting.", file=sys.stderr)
        sys.exit(1)
    os.environ["GITHUB_TOKEN"] = token
    from difflux.config_file import save_api_key
    save_api_key("github", token)


def _ensure_api_key(provider: str, model: str, *, no_tui: bool, base_url: str | None = None) -> None:
    """Guarantee the API key for provider is in os.environ. Prompts if missing."""
    env_var = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    if os.environ.get(env_var):
        return

    use_tui = not no_tui and sys.stdout.isatty()
    custom_base_url = bool(base_url)

    if use_tui:
        from difflux.tui.key_entry import KeyEntryApp
        key = KeyEntryApp(provider, custom_base_url=custom_base_url).run()
    else:
        import getpass
        if custom_base_url:
            print(f"difflux: API key required for {base_url}", file=sys.stderr)
        else:
            provider_label = "Anthropic" if provider == "anthropic" else "OpenAI"
            url = "https://console.anthropic.com/" if provider == "anthropic" else "https://platform.openai.com/"
            print(f"difflux: {provider_label} API key required (get one at {url})", file=sys.stderr)
        try:
            key = getpass.getpass(f"{env_var}: ")
        except (KeyboardInterrupt, EOFError):
            key = None

    key = (key or "").strip()
    if not key:
        print("difflux: no API key provided, exiting.", file=sys.stderr)
        sys.exit(1)

    from difflux.config_file import save_api_key
    save_api_key(provider, key)


def _needs_setup(*, no_tui: bool) -> bool:
    """True only on a cold start: interactive, TUI allowed, no LLM key or defaults configured."""
    if no_tui or not sys.stdout.isatty():
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        return False
    from difflux.config_file import load_config_file
    data = load_config_file()
    keys = data.get("keys", {})
    return not (keys.get("anthropic") or keys.get("openai") or data.get("defaults"))


def _run_reconfigure(*, no_tui: bool) -> None:
    """Run the setup wizard on demand and exit — no diff required.

    `difflux --reconfigure` is a pure setup action: it does not read a diff and
    does not cluster, it just (re)collects provider/base-url/model/key and saves.
    """
    if no_tui or not sys.stdout.isatty():
        print("difflux: --reconfigure requires an interactive terminal.", file=sys.stderr)
        sys.exit(1)
    # If a diff was piped, FD 0 is the pipe; give the TUI a live keyboard.
    _reopen_stdin_for_tui()
    from difflux.tui.setup import SetupWizardApp, apply_setup
    result = SetupWizardApp(default_anthropic_model=DEFAULT_MODEL).run()
    if result is None:
        print("difflux: setup cancelled.", file=sys.stderr)
        sys.exit(1)
    apply_setup(result)
    print("difflux: configuration saved.")


def main() -> None:
    args = _make_arg_parser().parse_args()

    # --reconfigure is a standalone setup action: run the wizard and exit,
    # without requiring a piped diff or source.
    if args.reconfigure:
        _run_reconfigure(no_tui=args.no_tui)
        return

    # Consume stdin before any TUI launch (the diff may be piped in).
    # GitHub PR URLs get a token re-prompt loop; stdin and bad sources exit immediately.
    from difflux.sources.github import is_github_pr_url, GithubAuthError
    if args.source and is_github_pr_url(args.source):
        while True:
            try:
                diff_text = _resolve_diff(args.source)
                break
            except GithubAuthError as e:
                failed_token = os.environ.pop("GITHUB_TOKEN", None)
                from difflux.config_file import get_wallet, delete_api_key
                if failed_token and failed_token == get_wallet().get("github", {}).get("key", ""):
                    delete_api_key("github")
                print(f"difflux: {e}", file=sys.stderr)
                _ensure_github_token(no_tui=args.no_tui)
            except RuntimeError as e:
                print(f"difflux: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        try:
            diff_text = _resolve_diff(args.source)
        except RuntimeError as e:
            print(f"difflux: {e}", file=sys.stderr)
            sys.exit(1)

    # After reading a piped diff, stdin (FD 0) is at EOF. Textual's Linux
    # driver reads from sys.__stdin__.fileno() (always FD 0) — reassigning
    # sys.stdin has no effect. Use dup2 to redirect FD 0 to /dev/tty so
    # Textual sees a live keyboard device.
    _reopen_stdin_for_tui()

    # First-run setup wizard — only after stdin is drained and FD 0 is a live
    # keyboard (above), so the TUI never reads the piped diff as keystrokes.
    # (--reconfigure is handled earlier and exits before this point.)
    if _needs_setup(no_tui=args.no_tui):
        from difflux.tui.setup import SetupWizardApp, apply_setup
        result = SetupWizardApp(default_anthropic_model=DEFAULT_MODEL).run()
        if result is not None:
            apply_setup(result)

    # Resolve from LIVE os.environ — the wizard above may have just set these,
    # whereas the config module constants were computed at import time.
    model = args.model or os.environ.get("DIFFLUX_MODEL") or DEFAULT_MODEL
    provider = _resolve_provider(args.provider or os.environ.get("DIFFLUX_PROVIDER") or None, model)
    base_url = args.base_url or os.environ.get("DIFFLUX_BASE_URL") or None

    hunks = parse_diff(diff_text)
    if not hunks:
        print("difflux: diff is empty — nothing to cluster.", file=sys.stderr)
        sys.exit(0)

    from difflux.clusterer import cluster

    def run_clustering():
        result = cluster(hunks, model=model, provider=provider, base_url=base_url)
        index = HunkIndex(hunks)
        return build_session(result, index)

    env_var = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"

    while True:
        _ensure_api_key(provider, model, no_tui=args.no_tui, base_url=base_url)
        try:
            session = run_clustering()
            break
        except ClusteringError as e:
            print(f"difflux: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            msg = str(e).lower()
            if "401" in msg or "authentication" in msg or "api_key" in msg:
                from difflux.config_file import delete_api_key
                delete_api_key(provider)
                os.environ.pop(env_var, None)
                print("difflux: API key rejected — please enter a valid key.", file=sys.stderr)
                # Loop back to re-prompt; _ensure_api_key will show the modal again.
            elif "403" in msg or "permission" in msg or "not found" in msg:
                print(
                    f"difflux: model '{model}' is unavailable (not found or no access).",
                    file=sys.stderr,
                )
                print(
                    "  pick another with --model <name>, run `difflux --reconfigure` to "
                    "re-run setup, or edit ~/.config/difflux/config.toml",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                print(f"difflux: {e}", file=sys.stderr)
                sys.exit(1)

    use_tui = not args.no_tui and sys.stdout.isatty()

    if use_tui:
        from difflux.tui.app import DiffluxApp
        app = DiffluxApp(session=session, regenerate=run_clustering, model=model, provider=provider)
        app.run()
        n_reviewed = sum(1 for v in app.session.clusters if v.reviewed)
        print(f"Reviewed {n_reviewed} clusters, {app.session.total_files} files with {model}")
    else:
        print(render_overview(session, model))
