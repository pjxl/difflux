from __future__ import annotations

import sys
import unittest.mock
from unittest.mock import MagicMock, patch

import pytest

from difflux.clusterer import ClusteringError, _detect_provider, _OpenAIProvider


class TestDetectProvider:
    def test_claude_model(self):
        assert _detect_provider("claude-opus-4-8") == "anthropic"

    def test_claude_prefix_variants(self):
        assert _detect_provider("claude-3-5-sonnet-20241022") == "anthropic"
        assert _detect_provider("claude-haiku-4-5") == "anthropic"

    def test_gpt_model(self):
        assert _detect_provider("gpt-4o") == "openai"
        assert _detect_provider("gpt-4o-mini") == "openai"
        assert _detect_provider("gpt-3.5-turbo") == "openai"

    def test_o_series_model(self):
        assert _detect_provider("o3-mini") == "openai"
        assert _detect_provider("o1-preview") == "openai"
        assert _detect_provider("o4-mini") == "openai"

    def test_unknown_model_raises(self):
        with pytest.raises(ClusteringError, match="Cannot detect provider"):
            _detect_provider("llama3")

    def test_unknown_model_suggests_flag(self):
        with pytest.raises(ClusteringError, match="--provider"):
            _detect_provider("mistral-large")


class TestOpenAIProviderMissingPackage:
    def test_raises_with_install_hint_when_openai_not_installed(self):
        with patch.dict(sys.modules, {"openai": None}):
            with pytest.raises(ClusteringError, match="pip install 'difflux\\[openai\\]'"):
                _OpenAIProvider()
