from __future__ import annotations

import argparse
import sys

from scc.config import ANTHROPIC_API_KEY, DEFAULT_MODEL, GITHUB_TOKEN
from scc.hunks import HunkIndex, parse_diff
from scc.enrich import build_session
from scc.render_text import render_overview


def _make_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scc",
        description="Decompose a git diff into conceptual clusters for review.",
    )
    p.add_argument(
        "source",
        nargs="?",
        help="GitHub PR URL (e.g. https://github.com/owner/repo/pull/123). "
             "Omit to read a diff from stdin.",
    )
    p.add_argument("--model", default=None, help="Override the Claude model to use.")
    p.add_argument("--no-tui", action="store_true", help="Print plain text instead of launching the TUI.")
    return p


def _resolve_diff(source: str | None) -> str:
    if source is None:
        if sys.stdin.isatty():
            print("scc: pipe a git diff or provide a GitHub PR URL.", file=sys.stderr)
            print("  example: git diff HEAD~1 | scc", file=sys.stderr)
            sys.exit(1)
        from scc.sources.stdin import read_stdin
        return read_stdin()

    from scc.sources.github import is_github_pr_url, fetch_pr_diff
    if is_github_pr_url(source):
        return fetch_pr_diff(source, token=GITHUB_TOKEN)

    print(f"scc: unrecognised source '{source}'. Expected a GitHub PR URL or no argument (stdin).", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    args = _make_arg_parser().parse_args()
    model = args.model or DEFAULT_MODEL

    diff_text = _resolve_diff(args.source)
    hunks = parse_diff(diff_text)

    if not hunks:
        print("scc: diff is empty — nothing to cluster.", file=sys.stderr)
        sys.exit(0)

    from scc.clusterer import cluster
    from scc.config import ANTHROPIC_API_KEY

    api_key = ANTHROPIC_API_KEY or None

    def run_clustering():
        result = cluster(hunks, model=model, api_key=api_key)
        index = HunkIndex(hunks)
        return build_session(result, index)

    session = run_clustering()

    use_tui = not args.no_tui and sys.stdout.isatty()

    if use_tui:
        from scc.tui.app import SCCApp
        app = SCCApp(session=session, regenerate=run_clustering)
        app.run()
        n_reviewed = sum(1 for v in session.clusters if v.reviewed)
        print(f"Reviewed {n_reviewed} clusters, {session.total_files} files")
    else:
        print(render_overview(session))
