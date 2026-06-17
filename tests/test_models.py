"""Tests for models.py — Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from scc.models import Cluster, ClusteringResult, ClusteringType

VALID_RESULT = {
    "clustering_type": "multi_cluster",
    "clusters": [
        {
            "id": "rename-session-token",
            "name": "Rename session token field",
            "summary": "Renames session_token to session_id across the auth module and all callers.",
            "position_rationale": "Establishes naming before the reader encounters it in feature code.",
            "hunk_ids": [1, 3, 5],
        },
        {
            "id": "add-validation-logic",
            "name": "Add token validation logic",
            "summary": "Validates session_id is non-null and non-expired before any read.",
            "position_rationale": "Depends on the rename; reviewed after.",
            "hunk_ids": [2, 4],
        },
    ],
    "note": None,
    "coverage": None,
}

SINGLE_IDEA_RESULT = {
    "clustering_type": "single_idea",
    "clusters": [
        {
            "id": "editorial-pass",
            "name": "Editorial pass on AGENTS.md",
            "summary": "Tightens prose throughout AGENTS.md with no semantic changes.",
            "position_rationale": "Single cluster, no ordering to decide.",
            "hunk_ids": list(range(1, 21)),
        }
    ],
    "note": "This diff is a uniform editorial operation. Read top to bottom.",
    "coverage": None,
}


def test_multi_cluster_result_parses():
    result = ClusteringResult.model_validate(VALID_RESULT)
    assert result.clustering_type == ClusteringType.MULTI_CLUSTER
    assert len(result.clusters) == 2


def test_cluster_fields():
    result = ClusteringResult.model_validate(VALID_RESULT)
    c = result.clusters[0]
    assert c.id == "rename-session-token"
    assert c.hunk_ids == [1, 3, 5]


def test_single_idea_result_parses():
    result = ClusteringResult.model_validate(SINGLE_IDEA_RESULT)
    assert result.clustering_type == ClusteringType.SINGLE_IDEA
    assert result.note is not None


def test_position_rationale_present_in_schema():
    # position_rationale must be in the schema (it's chain-of-thought scaffolding)
    schema = ClusteringResult.model_json_schema()
    cluster_props = schema["$defs"]["Cluster"]["properties"]
    assert "position_rationale" in cluster_props


def test_file_count_not_in_schema():
    schema = ClusteringResult.model_json_schema()
    cluster_props = schema["$defs"]["Cluster"]["properties"]
    assert "file_count" not in cluster_props
    assert "line_count" not in cluster_props
    assert "position" not in cluster_props


def test_too_large_not_in_clustering_type():
    valid_values = {e.value for e in ClusteringType}
    assert "too_large" not in valid_values


def test_invalid_clustering_type_raises():
    bad = dict(VALID_RESULT, clustering_type="too_large")
    with pytest.raises(ValidationError):
        ClusteringResult.model_validate(bad)


def test_note_defaults_to_none():
    result = ClusteringResult.model_validate(VALID_RESULT)
    assert result.note is None


def test_coverage_optional():
    with_coverage = dict(VALID_RESULT, coverage="H3 straddles clusters 1 and 2.")
    result = ClusteringResult.model_validate(with_coverage)
    assert result.coverage == "H3 straddles clusters 1 and 2."
