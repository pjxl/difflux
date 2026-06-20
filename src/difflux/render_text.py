from __future__ import annotations

import textwrap

from difflux.enrich import ClusterView, ReviewSession
from difflux.format import churn_bar, meta_label

_SUMMARY_INDENT = " " * 7
_WRAP_WIDTH = 80


def render_overview(session: ReviewSession, model: str) -> str:
    reviewed = sum(1 for v in session.clusters if v.reviewed)
    lines = [
        f"difflux · {model} · {len(session.clusters)} clusters · "
        f"{session.total_files} files · {reviewed}/{len(session.clusters)} reviewed"
    ]
    if session.note:
        lines.append(f"Note: {session.note}")
    if session.coverage:
        lines.append(f"Coverage: {session.coverage}")
    lines.append("")

    max_churn = max((v.churn for v in session.clusters), default=0)
    for i, v in enumerate(session.clusters, 1):
        mark = "✓" if v.reviewed else " "
        bar = churn_bar(v.churn, max_churn)
        meta = meta_label(len(v.hunks), v.file_count, v.added, v.removed)
        lines.append(f"  {mark} {i:2}  {v.cluster.name:<32}  {bar}  {meta}")
        lines.append(textwrap.fill(
            v.cluster.summary,
            width=_WRAP_WIDTH,
            initial_indent=_SUMMARY_INDENT,
            subsequent_indent=_SUMMARY_INDENT,
        ))
    return "\n".join(lines)


def render_cluster(view: ClusterView) -> str:
    lines = [f"\n{view.cluster.name}", view.cluster.summary, ""]
    for h in view.hunks:
        end_line = h.new_start + h.new_count - 1
        lines.append(f"  {h.file_path}  lines {h.new_start}–{end_line}")
        lines.append(h.header)
        lines.append(h.body)
    return "\n".join(lines)
