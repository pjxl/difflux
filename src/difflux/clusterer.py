from __future__ import annotations

import json
import re
import sys
from typing import Protocol

import anthropic

from difflux.config import DEFAULT_MODEL, HUNK_CEILING, TOKEN_CEILING
from difflux.hunks import Hunk
from difflux.models import ClusteringResult
from difflux.prompt import SYSTEM_PROMPT, build_user_message, render_hunks


class ClusteringError(Exception):
    pass


class _Provider(Protocol):
    def call(
        self,
        *,
        model: str,
        system_prompt: str,
        user_message: str,
        tool_schema: dict,
    ) -> dict: ...

    def list_models(self) -> list[str]: ...


class _AnthropicProvider:
    def __init__(self, api_key: str | None, base_url: str | None = None) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or None, base_url=base_url or None)

    def call(self, *, model: str, system_prompt: str, user_message: str, tool_schema: dict) -> dict:
        tool_def = {
            "name": "return_clustering",
            "description": "Return the clustered diff analysis.",
            "input_schema": tool_schema,
        }
        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[tool_def],
            tool_choice={"type": "any"},
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "return_clustering":
                return block.input  # already a dict
        raise ClusteringError("LLM did not call return_clustering — check model and API key")

    def list_models(self) -> list[str]:
        return [m.id for m in self._client.models.list(limit=1000)]


def _is_o_series(model: str) -> bool:
    return bool(re.match(r"^o\d", model))


class _OpenAIProvider:
    def __init__(self, api_key: str | None, base_url: str | None = None) -> None:
        try:
            from openai import OpenAI  # noqa: PLC0415
            self._client = OpenAI(api_key=api_key or None, base_url=base_url or None)
        except ImportError:
            raise ClusteringError("openai package is not installed.") from None

    def call(self, *, model: str, system_prompt: str, user_message: str, tool_schema: dict) -> dict:
        tool_def = {
            "type": "function",
            "function": {
                "name": "return_clustering",
                "description": "Return the clustered diff analysis.",
                "parameters": tool_schema,
            },
        }
        # o-series reasoning models require max_completion_tokens; other models use max_tokens
        token_limit_kwarg = "max_completion_tokens" if _is_o_series(model) else "max_tokens"
        response = self._client.chat.completions.create(
            model=model,
            **{token_limit_kwarg: 4096},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=[tool_def],
            # "required" is a plain string: avoids the Chat Completions vs Responses API
            # tool_choice object format mismatch on newer models (e.g. gpt-5-codex via
            # LiteLLM). Since we define exactly one tool, "required" always calls it.
            tool_choice="required",
        )
        for choice in response.choices:
            if choice.message.tool_calls:
                for tc in choice.message.tool_calls:
                    if tc.function.name == "return_clustering":
                        return json.loads(tc.function.arguments)
        raise ClusteringError("LLM did not call return_clustering — check model and API key")

    def list_models(self) -> list[str]:
        return [m.id for m in self._client.models.list()]


def detect_provider(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt-") or re.match(r"^o\d", model):
        return "openai"
    raise ClusteringError(
        f"Cannot detect provider from model '{model}'. Use --provider or DIFFLUX_PROVIDER."
    )


def _make_provider(name: str, api_key: str | None, base_url: str | None = None) -> _Provider:
    if name == "anthropic":
        return _AnthropicProvider(api_key, base_url)
    if name == "openai":
        return _OpenAIProvider(api_key, base_url)
    raise ClusteringError(f"Unknown provider '{name}'. Choose 'anthropic' or 'openai'.")


def list_models(provider: str, *, api_key: str | None, base_url: str | None = None) -> list[str]:
    p = _make_provider(provider, api_key, base_url)
    return p.list_models()


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
    provider: str | None = None,
    base_url: str | None = None,
) -> ClusteringResult:
    hunks = _truncate_hunks(list(hunks))

    provider_name = provider or detect_provider(model)
    p = _make_provider(provider_name, api_key, base_url)

    raw = p.call(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        user_message=build_user_message(hunks, correction_hint),
        tool_schema=ClusteringResult.model_json_schema(),
    )
    result = ClusteringResult.model_validate(raw)
    _validate_hunk_ids(result, hunks)
    return result


def _validate_hunk_ids(result: ClusteringResult, hunks: list[Hunk]) -> None:
    valid_ids = {h.id for h in hunks}
    for c in result.clusters:
        bad = [i for i in c.hunk_ids if i not in valid_ids]
        if bad:
            raise ClusteringError(
                f"Cluster '{c.id}' references unknown hunk IDs: {bad}"
            )
