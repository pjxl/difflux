from __future__ import annotations

from difflux.enrich import ClusterView, ReviewSession


def render_overview(session: ReviewSession, model: str) -> str:
    lines = [f"difflux · {model} · {len(session.clusters)} clusters · {session.total_files} files\n"]
    for i, v in enumerate(session.clusters, 1):
        mark = "✓" if v.reviewed else " "
        lines.append(
            f"  {mark} {i:2}  {v.cluster.name:<35}"
            f"  {len(v.hunks)}h  {v.file_count}f  ~{v.line_count} lines"
        )
        lines.append(f"       {v.cluster.summary}")
    if session.coverage:
        lines.append(f"\nCoverage note: {session.coverage}")
    return "\n".join(lines)


def render_cluster(view: ClusterView) -> str:
    lines = [f"\n{view.cluster.name}", view.cluster.summary, ""]
    for h in view.hunks:
        end_line = h.new_start + h.new_count - 1
        lines.append(f"  {h.file_path}  lines {h.new_start}–{end_line}")
        lines.append(h.header)
        lines.append(h.body)
    return "\n".join(lines)
