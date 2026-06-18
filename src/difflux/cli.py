from __future__ import annotations

import argparse
import sys

from difflux.config import (
    ANTHROPIC_API_KEY,
    DEFAULT_MODEL,
    DIFFLUX_PROVIDER,
    GITHUB_TOKEN,
    OPENAI_API_KEY,
)
from difflux.clusterer import ClusteringError, detect_provider
from difflux.hunks import HunkIndex, parse_diff
from difflux.enrich import build_session
from difflux.render_text import render_overview


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
    p.add_argument("--no-tui", action="store_true", help="Print plain text instead of launching the TUI.")
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
        return fetch_pr_diff(source, token=GITHUB_TOKEN)

    print(f"difflux: unrecognised source '{source}'. Expected a GitHub PR URL or no argument (stdin).", file=sys.stderr)
    sys.exit(1)


def _check_api_key(provider: str | None, model: str) -> None:
    if provider is None:
        try:
            provider = detect_provider(model)
        except ClusteringError as e:
            print(f"difflux: {e}", file=sys.stderr)
            sys.exit(1)

    if provider == "anthropic" and not ANTHROPIC_API_KEY:
        print(
            f"difflux: model '{model}' requires ANTHROPIC_API_KEY, which is not set.",
            file=sys.stderr,
        )
        print(
            "  export ANTHROPIC_API_KEY=sk-ant-...  (get a key at https://console.anthropic.com/)",
            file=sys.stderr,
        )
        print("  Or use an OpenAI model: difflux --model gpt-4o", file=sys.stderr)
        sys.exit(1)

    if provider == "openai" and not OPENAI_API_KEY:
        print(
            f"difflux: model '{model}' requires OPENAI_API_KEY, which is not set.",
            file=sys.stderr,
        )
        print(
            "  export OPENAI_API_KEY=sk-...  (get a key at https://platform.openai.com/)",
            file=sys.stderr,
        )
        print("  Or use an Anthropic model: difflux --model claude-opus-4-8", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = _make_arg_parser().parse_args()
    model = args.model or DEFAULT_MODEL
    provider = args.provider or DIFFLUX_PROVIDER or None

    _check_api_key(provider, model)

    try:
        diff_text = _resolve_diff(args.source)
    except RuntimeError as e:
        print(f"difflux: {e}", file=sys.stderr)
        sys.exit(1)
    hunks = parse_diff(diff_text)

    if not hunks:
        print("difflux: diff is empty — nothing to cluster.", file=sys.stderr)
        sys.exit(0)

    from difflux.clusterer import cluster

    def run_clustering():
        result = cluster(hunks, model=model, provider=provider)
        index = HunkIndex(hunks)
        return build_session(result, index)

    try:
        session = run_clustering()
    except ClusteringError as e:
        print(f"difflux: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        msg = str(e).lower()
        if "401" in msg or "authentication" in msg or "api_key" in msg:
            print("difflux: your API key was rejected — check it at the provider console.", file=sys.stderr)
        elif "403" in msg or "permission" in msg or "not found" in msg:
            print(
                f"difflux: your account may not have access to model '{model}' — try a different model.",
                file=sys.stderr,
            )
        else:
            print(f"difflux: {e}", file=sys.stderr)
        sys.exit(1)

    use_tui = not args.no_tui and sys.stdout.isatty()

    if use_tui:
        from difflux.tui.app import DiffluxApp
        app = DiffluxApp(session=session, regenerate=run_clustering, model=model)
        app.run()
        n_reviewed = sum(1 for v in session.clusters if v.reviewed)
        print(f"Reviewed {n_reviewed} clusters, {session.total_files} files with {model}")
    else:
        print(render_overview(session, model))
