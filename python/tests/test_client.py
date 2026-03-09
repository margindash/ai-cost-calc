"""Tests for ai-cost-calc Python SDK."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_cost_calc import CostResult, AiCostCalc, ModelPricing


MOCK_MODELS_RESPONSE = {
    "generated_at": "2026-03-09T00:00:00Z",
    "models": [
        {
            "slug": "gpt-4o",
            "name": "GPT-4o",
            "provider": "openai",
            "pricing": {"input_per_1m_usd": 2.5, "output_per_1m_usd": 10.0, "cache_read_per_1m_usd": 1.25},
            "benchmarks": {"variants": []},
        },
        {
            "slug": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "provider": "openai",
            "pricing": {"input_per_1m_usd": 0.15, "output_per_1m_usd": 0.6, "cache_read_per_1m_usd": 0.075},
            "benchmarks": {"variants": []},
        },
        {
            "slug": "claude-sonnet-4",
            "name": "Claude Sonnet 4",
            "provider": "anthropic",
            "pricing": {"input_per_1m_usd": 3.0, "output_per_1m_usd": 15.0, "cache_read_per_1m_usd": None},
            "benchmarks": {"variants": []},
        },
    ]
}


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = status_code < 400
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


class TestNoApiKey:
    def test_constructor_without_key_does_not_raise(self):
        md = AiCostCalc()
        assert md._api_key == ""
        assert md._thread is None

    def test_add_usage_without_key_is_noop(self):
        md = AiCostCalc()
        md.add_usage(vendor="openai", model="gpt-4o", input_tokens=100, output_tokens=50)
        assert len(md._pending_usages) == 0

    def test_track_without_key_is_noop(self):
        md = AiCostCalc()
        md.track(customer_id="cust_123")
        assert len(md._queue) == 0

    def test_flush_without_key_is_noop(self):
        md = AiCostCalc()
        md.flush()  # should not raise

    def test_shutdown_without_key_is_noop(self):
        md = AiCostCalc()
        md.shutdown()  # should not raise

    def test_warns_once_for_tracking_methods(self):
        errors: list = []
        md = AiCostCalc(on_error=lambda e: errors.append(e))
        md.add_usage(vendor="openai", model="gpt-4o", input_tokens=100, output_tokens=50)
        md.add_usage(vendor="openai", model="gpt-4o", input_tokens=100, output_tokens=50)
        md.track(customer_id="cust_123")
        assert len(errors) == 1
        assert "api_key required" in errors[0].message

    def test_constructor_rejects_invalid_max_retries(self):
        with pytest.raises(ValueError, match="max_retries"):
            AiCostCalc(max_retries=-1)

        with pytest.raises(ValueError, match="max_retries"):
            AiCostCalc(max_retries=1.5)  # type: ignore[arg-type]

    def test_constructor_rejects_invalid_flush_interval_when_key_set(self):
        with pytest.raises(ValueError, match="flush_interval"):
            AiCostCalc(api_key="key", flush_interval=0)

        with pytest.raises(ValueError, match="flush_interval"):
            AiCostCalc(api_key="key", flush_interval=-1)


class TestCost:
    @patch("ai_cost_calc.client.requests.get")
    def test_cost_returns_result(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)

        assert result is not None
        assert result.model == "gpt-4o"
        assert result.input_cost == pytest.approx(0.0025)
        assert result.output_cost == pytest.approx(0.005)
        assert result.total_cost == pytest.approx(0.0075)

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_unknown_model_returns_none(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()
        result = md.cost("nonexistent-model", input_tokens=1000, output_tokens=500)
        assert result is None

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_network_failure_returns_none(self, mock_get):
        mock_get.side_effect = ConnectionError("network down")
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert result is None

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_uses_stale_cache_on_refetch_failure(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()

        # First call — populates cache
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert result is not None

        # Force cache expiry
        md._pricing_fetched_at = 0.0

        # Make refetch fail
        mock_get.side_effect = ConnectionError("network down")
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)

        # Should still return from stale cache (within backoff window)
        assert result is not None
        assert result.total_cost == pytest.approx(0.0075)

    @patch("ai_cost_calc.client.requests.get")
    def test_failure_backoff_prevents_repeated_fetches(self, mock_get):
        mock_get.side_effect = ConnectionError("network down")
        md = AiCostCalc()

        md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        md.cost("gpt-4o", input_tokens=1000, output_tokens=500)

        # Should only attempt fetch once due to 60s backoff
        assert mock_get.call_count == 1

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_caches_across_calls(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()

        md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        md.cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        md.cost("claude-sonnet-4", input_tokens=1000, output_tokens=500)

        # Only one HTTP call — rest served from cache
        assert mock_get.call_count == 1


class TestCostWithText:
    @patch("ai_cost_calc.client.requests.get")
    def test_cost_with_text_returns_estimated_result(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()

        with patch.object(md, "_count_tokens", side_effect=[10, 20]):
            result = md.cost("gpt-4o", input_text="Hello world", output_text="Hi there friend")

        assert result is not None
        assert result.model == "gpt-4o"
        assert result.input_tokens == 10
        assert result.output_tokens == 20
        assert result.estimated is True
        assert result.input_cost == pytest.approx(10 * 2.5 / 1_000_000)
        assert result.output_cost == pytest.approx(20 * 10.0 / 1_000_000)

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_with_input_text_only(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()

        with patch.object(md, "_count_tokens", return_value=5):
            result = md.cost("gpt-4o", input_text="Hello")

        assert result is not None
        assert result.input_tokens == 5
        assert result.output_tokens == 0
        assert result.estimated is True
        assert result.output_cost == 0.0

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_with_text_non_openai_model(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()

        with patch.object(md, "_count_tokens", return_value=8):
            result = md.cost("claude-sonnet-4", input_text="Hello world")

        assert result is not None
        assert result.input_tokens == 8
        assert result.estimated is True

    def test_cost_with_text_missing_tiktoken(self):
        errors: list = []
        md = AiCostCalc(on_error=lambda e: errors.append(e))

        with patch.dict("sys.modules", {"tiktoken": None}):
            # Force reimport failure by clearing encoder cache and patching import
            md._encoder_cache.clear()
            with patch("builtins.__import__", side_effect=ImportError("no tiktoken")):
                result = md.cost("gpt-4o", input_text="Hello")

        assert result is None
        assert any("tiktoken" in e.message for e in errors)

    def test_cost_with_mixed_invalid_args(self):
        errors: list = []
        md = AiCostCalc(on_error=lambda e: errors.append(e))
        result = md.cost("gpt-4o", input_text="Hello", output_tokens=100)
        assert result is None
        assert any("Cannot mix" in e.message for e in errors)

    @patch("ai_cost_calc.client.requests.get")
    def test_cost_with_tokens_populates_new_fields(self, mock_get):
        mock_get.return_value = _mock_response(MOCK_MODELS_RESPONSE)
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)

        assert result is not None
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.estimated is False

    def test_cost_with_oversized_text(self):
        errors: list = []
        md = AiCostCalc(on_error=lambda e: errors.append(e))
        big_text = "x" * 1_000_001
        result = md.cost("gpt-4o", input_text=big_text)
        assert result is None
        assert any("1MB" in e.message for e in errors)


class TestDefensiveParsing:
    @patch("ai_cost_calc.client.requests.get")
    def test_skips_malformed_top_level_model_entries(self, mock_get):
        mock_get.return_value = _mock_response({
            "models": [
                "not-a-dict",
                {"slug": "gpt-4o", "pricing": {"input_per_1m_usd": 2.5, "output_per_1m_usd": 10.0}},
            ]
        })
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert result is not None

    @patch("ai_cost_calc.client.requests.get")
    def test_skips_malformed_model_entries(self, mock_get):
        mock_get.return_value = _mock_response({
            "models": [
                "not-a-dict",
                {"slug": "gpt-4o", "pricing": {"input_per_1m_usd": 2.5, "output_per_1m_usd": 10.0}},
                {"slug": "bad", "pricing": {"input_per_1m_usd": "not-a-number", "output_per_1m_usd": 10.0}},
                {"slug": "nan", "pricing": {"input_per_1m_usd": float("nan"), "output_per_1m_usd": 10.0}},
                {"slug": "", "pricing": {"input_per_1m_usd": 1.0, "output_per_1m_usd": 1.0}},
            ],
        })
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert result is not None
        # Only gpt-4o should be cached — all others are malformed
        assert len(md._pricing_cache) == 1

    @patch("ai_cost_calc.client.requests.get")
    def test_handles_missing_models_key(self, mock_get):
        mock_get.return_value = _mock_response({})
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)
        assert result is None
