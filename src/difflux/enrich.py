from __future__ import annotations

from dataclasses import dataclass, field

from difflux.hunks import Hunk, HunkIndex
from difflux.models import Cluster, ClusteringResult, ClusteringType


@dataclass
class ClusterView:
    cluster: Cluster
    hunks: list[Hunk]
    file_count: int
    added: int
    removed: int
    reviewed: bool = False

    @property
    def churn(self) -> int:
        return self.added + self.removed


@dataclass
class ReviewSession:
    clustering_type: ClusteringType
    note: str | None
    coverage: str | None
    clusters: list[ClusterView]
    total_files: int
    total_hunks: int


def build_session(result: ClusteringResult, index: HunkIndex) -> ReviewSession:
    views = []
    for c in result.clusters:
        resolved = index.by_ids(c.hunk_ids)
        file_count = len({h.file_path for h in resolved})
        lines = [line for h in resolved for line in h.body.splitlines()]
        added = sum(1 for line in lines if line.startswith("+"))
        removed = sum(1 for line in lines if line.startswith("-"))
        views.append(ClusterView(
            cluster=c,
            hunks=resolved,
            file_count=file_count,
            added=added,
            removed=removed,
        ))

    all_hunk_ids = {hid for c in result.clusters for hid in c.hunk_ids}
    return ReviewSession(
        clustering_type=result.clustering_type,
        note=result.note,
        coverage=result.coverage,
        clusters=views,
        total_files=len({h.file_path for v in views for h in v.hunks}),
        total_hunks=len(all_hunk_ids),
    )
