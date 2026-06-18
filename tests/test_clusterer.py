from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from difflux.clusterer import (
    ClusteringError,
    _AnthropicProvider,
    _OpenAIProvider,
    detect_provider,
)


class TestDetectProvider:
    def test_claude_model(self):
        assert detect_provider("claude-opus-4-8") == "anthropic"

    def test_claude_prefix_variants(self):
        assert detect_provider("claude-3-5-sonnet-20241022") == "anthropic"
        assert detect_provider("claude-haiku-4-5") == "anthropic"

    def test_gpt_model(self):
        assert detect_provider("gpt-4o") == "openai"
        assert detect_provider("gpt-4o-mini") == "openai"
        assert detect_provider("gpt-3.5-turbo") == "openai"

    def test_o_series_model(self):
        assert detect_provider("o3-mini") == "openai"
        assert detect_provider("o1-preview") == "openai"
        assert detect_provider("o4-mini") == "openai"

    def test_unknown_model_raises(self):
        with pytest.raises(ClusteringError, match="Cannot detect provider"):
            detect_provider("llama3")

    def test_unknown_model_suggests_flag(self):
        with pytest.raises(ClusteringError, match="--provider"):
            detect_provider("mistral-large")


class TestBaseURLForwarding:
    def test_anthropic_forwards_base_url(self):
        with patch("difflux.clusterer.anthropic.Anthropic") as mock_client:
            _AnthropicProvider("sk-ant-test", base_url="https://gateway.example/v1")
            mock_client.assert_called_once_with(
                api_key="sk-ant-test", base_url="https://gateway.example/v1"
            )

    def test_anthropic_base_url_defaults_to_none(self):
        with patch("difflux.clusterer.anthropic.Anthropic") as mock_client:
            _AnthropicProvider("sk-ant-test")
            mock_client.assert_called_once_with(api_key="sk-ant-test", base_url=None)

    def test_openai_forwards_base_url(self):
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai)}):
            _OpenAIProvider("sk-test", base_url="https://gateway.example/v1")
            mock_openai.assert_called_once_with(
                api_key="sk-test", base_url="https://gateway.example/v1"
            )

    def test_openai_base_url_defaults_to_none(self):
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai)}):
            _OpenAIProvider("sk-test")
            mock_openai.assert_called_once_with(api_key="sk-test", base_url=None)
