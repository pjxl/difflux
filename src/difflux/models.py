from enum import StrEnum

from pydantic import BaseModel, Field


class ClusteringType(StrEnum):
    MULTI_CLUSTER = "multi_cluster"
    SINGLE_IDEA = "single_idea"
    # "too_large" is intentionally NOT in the v1 enum


class Cluster(BaseModel):
    id: str = Field(description="kebab-case slug, unique within this result")
    name: str = Field(description="3–5 words, specific to this diff")
    summary: str = Field(description="One sentence, specific enough to drive sequencing decisions")
    position_rationale: str = Field(
        description="INTERNAL chain-of-thought scaffolding. Never rendered in the TUI."
    )
    hunk_ids: list[int] = Field(description="IDs of hunks assigned to this cluster")


class ClusteringResult(BaseModel):
    clustering_type: ClusteringType
    clusters: list[Cluster]
    note: str | None = Field(
        default=None,
        description="Human-readable string surfaced to the reviewer in non-standard cases",
    )
    coverage: str | None = Field(
        default=None,
        description="Notes on ambiguous assignments or hunks that straddle clusters",
    )
