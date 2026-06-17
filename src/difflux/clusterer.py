from __future__ import annotations

import sys

import anthropic

from difflux.config import DEFAULT_MODEL, HUNK_CEILING, TOKEN_CEILING
from difflux.hunks import Hunk
from difflux.models import ClusteringResult
from difflux.prompt import SYSTEM_PROMPT, build_user_message, render_hunks


class ClusteringError(Exception):
    pass


def _truncate_hunks(hunks: list[Hunk]) -> list[Hunk]:
    if len(hunks) > HUNK_CEILING:
        dropped = hunks[HUNK_CEILING:]
        hunks = hunks[:HUNK_CEILING]
        print(
            f"Warning: truncated at hunk {HUNK_CEILING}/{len(dropped) + HUNK_CEILING}. "
            f"IDs {dropped[0].id}–{dropped[-1].id} excluded.",
            file=sys.stderr,
        )
        return hunks

    rendered = render_hunks(hunks)
    est_tokens = len(rendered) // 4
    if est_tokens > TOKEN_CEILING:
        # Pop from the end until we fit
        while hunks and len(render_hunks(hunks)) // 4 > TOKEN_CEILING:
            dropped_hunk = hunks.pop()
        print(
            f"Warning: diff too large for context window; truncated at hunk {hunks[-1].id} "
            f"(estimated {len(render_hunks(hunks)) // 4:,} tokens). "
            f"Hunk {dropped_hunk.id} and later excluded.",
            file=sys.stderr,
        )

    return hunks


def cluster(
    hunks: list[Hunk],
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    correction_hint: str | None = None,
) -> ClusteringResult:
    hunks = _truncate_hunks(list(hunks))

    client = anthropic.Anthropic(api_key=api_key or None)

    tool_def = {
        "name": "return_clustering",
        "description": "Return the clustered diff analysis.",
        "input_schema": ClusteringResult.model_json_schema(),
    }

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(hunks, correction_hint)}],
        tools=[tool_def],
        tool_choice={"type": "any"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "return_clustering":
            result = ClusteringResult.model_validate(block.input)
            _validate_hunk_ids(result, hunks)
            return result

    raise ClusteringError("LLM did not call return_clustering — check model and API key")


def _validate_hunk_ids(result: ClusteringResult, hunks: list[Hunk]) -> None:
    valid_ids = {h.id for h in hunks}
    for c in result.clusters:
        bad = [i for i in c.hunk_ids if i not in valid_ids]
        if bad:
            raise ClusteringError(
                f"Cluster '{c.id}' references unknown hunk IDs: {bad}"
            )
