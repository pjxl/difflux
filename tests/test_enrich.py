"""Tests for enrich.py — local count derivation and view model construction."""

from difflux.hunks import Hunk, HunkIndex
from difflux.models import Cluster, ClusteringResult, ClusteringType
from difflux.enrich import build_session, ClusterView, ReviewSession


def _hunk(id: int, file_path: str = "src/foo.py", body: str = "+add\n-remove\n ctx") -> Hunk:
    return Hunk(
        id=id, file_path=file_path,
        old_start=1, old_count=3, new_start=1, new_count=3,
        header="@@ -1,3 +1,3 @@",
        body=body,
    )


def _cluster(id: str, name: str, hunk_ids: list[int]) -> Cluster:
    return Cluster(
        id=id, name=name,
        summary="A summary sentence.",
        position_rationale="internal only",
        hunk_ids=hunk_ids,
    )


def _result(clusters: list[Cluster], clustering_type=ClusteringType.MULTI_CLUSTER) -> ClusteringResult:
    return ClusteringResult(clustering_type=clustering_type, clusters=clusters)


def test_build_session_returns_review_session():
    hunks = [_hunk(1), _hunk(2)]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Cluster One", [1, 2])])
    session = build_session(result, index)
    assert isinstance(session, ReviewSession)


def test_cluster_view_has_resolved_hunks():
    hunks = [_hunk(1), _hunk(2, "src/bar.py")]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Cluster One", [1, 2])])
    session = build_session(result, index)
    assert len(session.clusters[0].hunks) == 2


def test_file_count_computed_locally():
    hunks = [_hunk(1, "a.py"), _hunk(2, "a.py"), _hunk(3, "b.py")]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Name", [1, 2, 3])])
    session = build_session(result, index)
    assert session.clusters[0].file_count == 2  # a.py and b.py


def test_added_and_removed_count_plus_and_minus_lines():
    body = "+added\n-removed\n context\n+also added"
    hunks = [_hunk(1, body=body)]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Name", [1])])
    session = build_session(result, index)
    view = session.clusters[0]
    assert view.added == 2  # 2 "+" lines
    assert view.removed == 1  # 1 "-" line
    assert view.churn == 3


def test_added_and_removed_exclude_context_lines():
    body = " context only\n context also"
    hunks = [_hunk(1, body=body)]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Name", [1])])
    session = build_session(result, index)
    view = session.clusters[0]
    assert view.added == 0
    assert view.removed == 0
    assert view.churn == 0


def test_total_files_across_clusters():
    hunks = [_hunk(1, "a.py"), _hunk(2, "b.py"), _hunk(3, "c.py")]
    index = HunkIndex(hunks)
    result = _result([
        _cluster("c1", "One", [1]),
        _cluster("c2", "Two", [2, 3]),
    ])
    session = build_session(result, index)
    assert session.total_files == 3


def test_total_hunks():
    hunks = [_hunk(1), _hunk(2), _hunk(3)]
    index = HunkIndex(hunks)
    result = _result([
        _cluster("c1", "One", [1, 2]),
        _cluster("c2", "Two", [3]),
    ])
    session = build_session(result, index)
    assert session.total_hunks == 3


def test_reviewed_defaults_to_false():
    hunks = [_hunk(1)]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Name", [1])])
    session = build_session(result, index)
    assert session.clusters[0].reviewed is False


def test_cluster_view_does_not_expose_position_rationale_as_top_level():
    # position_rationale lives on ClusterView.cluster.position_rationale
    # but must not be a direct attribute of ClusterView
    hunks = [_hunk(1)]
    index = HunkIndex(hunks)
    result = _result([_cluster("c1", "Name", [1])])
    session = build_session(result, index)
    cv = session.clusters[0]
    assert not hasattr(cv, "position_rationale")
    # It IS accessible via the nested cluster object (for internal use only)
    assert cv.cluster.position_rationale == "internal only"


def test_single_idea_session():
    hunks = [_hunk(i) for i in range(1, 6)]
    index = HunkIndex(hunks)
    result = _result(
        [_cluster("all", "All changes", list(range(1, 6)))],
        clustering_type=ClusteringType.SINGLE_IDEA,
    )
    session = build_session(result, index)
    assert session.clustering_type == ClusteringType.SINGLE_IDEA
