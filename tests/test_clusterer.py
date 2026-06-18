from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from difflux.clusterer import (
    ClusteringError,
    _AnthropicProvider,
    _OpenAIProvider,
    detect_provider,
    list_models,
)


def _fake_model(model_id):
    m = MagicMock()
    m.id = model_id
    return m


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


class TestListModels:
    def test_anthropic_list_models(self):
        with patch("difflux.clusterer.anthropic.Anthropic") as mock_client:
            client = mock_client.return_value
            client.models.list.return_value = [
                _fake_model("claude-opus-4-8"),
                _fake_model("claude-haiku-4-5"),
            ]
            provider = _AnthropicProvider("sk-ant-test")
            result = provider.list_models()

            assert result == ["claude-opus-4-8", "claude-haiku-4-5"]
            client.models.list.assert_called_once_with(limit=1000)

    def test_openai_list_models(self):
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai)}):
            client = mock_openai.return_value
            client.models.list.return_value = [
                _fake_model("gpt-4o"),
                _fake_model("o3-mini"),
            ]
            provider = _OpenAIProvider("sk-test")
            result = provider.list_models()

            assert result == ["gpt-4o", "o3-mini"]
            client.models.list.assert_called_once_with()

    def test_facade_routes_to_anthropic(self):
        with patch("difflux.clusterer.anthropic.Anthropic") as mock_client:
            client = mock_client.return_value
            client.models.list.return_value = [_fake_model("claude-opus-4-8")]
            result = list_models("anthropic", api_key="sk-ant-test")

            assert result == ["claude-opus-4-8"]

    def test_facade_routes_to_openai_with_base_url(self):
        mock_openai = MagicMock()
        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai)}):
            client = mock_openai.return_value
            client.models.list.return_value = [_fake_model("global-gemini-2.5-flash")]
            result = list_models(
                "openai", api_key="sk-test", base_url="https://gateway.example/v1"
            )

            assert result == ["global-gemini-2.5-flash"]
            mock_openai.assert_called_once_with(
                api_key="sk-test", base_url="https://gateway.example/v1"
            )

    def test_facade_unknown_provider_raises(self):
        with pytest.raises(ClusteringError, match="Unknown provider"):
            list_models("llama", api_key="key")

    def test_facade_propagates_sdk_exceptions(self):
        with patch("difflux.clusterer.anthropic.Anthropic") as mock_client:
            client = mock_client.return_value
            client.models.list.side_effect = RuntimeError("401 authentication failed")
            with pytest.raises(RuntimeError, match="401 authentication failed"):
                list_models("anthropic", api_key="bad-key")
