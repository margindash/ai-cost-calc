"""Python SDK — lightweight AI cost calculator and usage tracking."""

from __future__ import annotations

import atexit
import logging
import math
import random
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

import requests

from ai_cost_calc.types import AiCostCalcError, CostResult, ModelPricing

logger = logging.getLogger("ai_cost_calc")

_VERSION = "1.3.6"
_DEFAULT_BASE_URL = "https://margindash.com/api/v1"
_DEFAULT_FLUSH_INTERVAL = 5.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_EVENT_TYPE = "ai_request"
_MAX_QUEUE_SIZE = 1000
_BATCH_SIZE = 50
_MAX_PENDING_USAGES = 1000
_HTTP_TIMEOUT = 10
_MAX_BACKOFF = 30.0
_PRICING_CACHE_TTL = 86_400    # 24 hours
_PRICING_FAILURE_BACKOFF = 60  # 60 seconds


class AiCostCalc:
    """Track AI usage and revenue events.

    Usage::

        # Free — cost calculator only, no API key needed
        md = AiCostCalc()
        result = md.cost("gpt-4o", input_tokens=1000, output_tokens=500)

        # Paid — full tracking with API key
        md = AiCostCalc(api_key="md_live_...")
        md.add_usage(model="openai/gpt-4o", input_tokens=1200, output_tokens=340)
        md.track(customer_id="cust_123")
        md.shutdown()
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        flush_interval: float = _DEFAULT_FLUSH_INTERVAL,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        default_event_type: str = _DEFAULT_EVENT_TYPE,
        on_error: Callable[[AiCostCalcError], None] | None = None,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._base_url = base_url.rstrip("/")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        self._max_retries = max_retries
        self._default_event_type = default_event_type
        self._on_error = on_error
        self._api_key_warned = False

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"ai-cost-calc-python/{_VERSION}",
        })

        self._pending_usages: list[dict[str, Any]] = []
        self._queue: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()

        # Pricing cache
        self._pricing_cache: dict[str, ModelPricing] | None = None
        self._pricing_fetched_at: float = 0.0
        self._pricing_failed_at: float = 0.0
        self._pricing_lock = threading.Lock()

        # Encoder cache for text-based token counting
        self._encoder_cache: dict[str, Any] = {}
        self._encoder_lock = threading.Lock()

        # Only start background flush + atexit if api_key present
        self._thread: threading.Thread | None = None
        if self._api_key:
            if (
                isinstance(flush_interval, bool)
                or not isinstance(flush_interval, (int, float))
                or not math.isfinite(flush_interval)
                or flush_interval <= 0
            ):
                raise ValueError("flush_interval must be a finite number > 0 when api_key is set")
            self._session.headers["Authorization"] = f"Bearer {self._api_key}"
            self._thread = threading.Thread(
                target=self._flush_loop, args=(flush_interval,), daemon=True
            )
            self._thread.start()
            atexit.register(self.shutdown)

    def __enter__(self) -> AiCostCalc:
        return self

    def __exit__(self, *_: Any) -> None:
        self.shutdown()

    # -- Public API -----------------------------------------------------------

    def cost(
        self,
        model: str,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        input_text: str | None = None,
        output_text: str | None = None,
    ) -> CostResult | None:
        """Calculate the cost of an AI API call. Never throws — returns None on failure.

        Pass either (input_tokens + output_tokens) for exact costs, or
        (input_text [+ output_text]) for estimated costs using tiktoken.
        No API key required.
        """
        try:
            has_text = input_text is not None or output_text is not None
            has_tokens = input_tokens is not None or output_tokens is not None

            if has_text and has_tokens:
                self._report_error("Cannot mix text and token arguments")
                return None

            estimated = False

            if has_text:
                if input_text is None:
                    self._report_error("input_text is required for text-based estimation")
                    return None
                counted = self._count_tokens(input_text, model)
                if counted is None:
                    return None
                input_tokens = counted
                if output_text is not None:
                    counted = self._count_tokens(output_text, model)
                    if counted is None:
                        return None
                    output_tokens = counted
                else:
                    output_tokens = 0
                estimated = True
            elif input_tokens is not None and output_tokens is not None:
                if isinstance(input_tokens, bool) or isinstance(output_tokens, bool):
                    self._report_error("input_tokens and output_tokens must be integers, not bools")
                    return None
                if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
                    self._report_error("input_tokens and output_tokens must be integers")
                    return None
                if input_tokens < 0 or output_tokens < 0:
                    self._report_error("Token counts cannot be negative")
                    return None
            else:
                self._report_error(
                    "Provide either (input_tokens + output_tokens) or (input_text [+ output_text])"
                )
                return None

            self._ensure_pricing()
            if not self._pricing_cache or model not in self._pricing_cache:
                return None
            pricing = self._pricing_cache[model]
            input_cost = (input_tokens * pricing.input_price_per_1m) / 1_000_000
            output_cost = (output_tokens * pricing.output_price_per_1m) / 1_000_000
            return CostResult(
                model=model,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=input_cost + output_cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated=estimated,
            )
        except Exception as e:
            self._report_error(f"Unexpected error in cost(): {e}", cause=e)
            return None

    def _count_tokens(self, text: str, model: str) -> int | None:
        """Count tokens in text using tiktoken. Returns None on failure."""
        if len(text) > 1_000_000:
            self._report_error("Text exceeds 1MB limit for token estimation")
            return None
        try:
            import tiktoken
        except ImportError:
            self._report_error(
                "tiktoken is required for text-based cost estimation. "
                "Install it with: pip install ai-cost-calc[estimate]"
            )
            return None
        try:
            with self._encoder_lock:
                if model not in self._encoder_cache:
                    if len(self._encoder_cache) >= 128:
                        self._encoder_cache.pop(next(iter(self._encoder_cache)))
                    try:
                        self._encoder_cache[model] = tiktoken.encoding_for_model(model)
                    except KeyError:
                        self._encoder_cache[model] = tiktoken.get_encoding("cl100k_base")
                enc = self._encoder_cache[model]
            return len(enc.encode(text))
        except Exception as e:
            self._report_error(f"Token counting failed: {e}", cause=e)
            return None

    def add_usage(
        self, *, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Record usage from a single AI API call."""
        if not self._require_api_key("add_usage"):
            return
        slash_idx = model.find("/")
        vendor_name = model[:slash_idx] if slash_idx > 0 else model
        with self._lock:
            if len(self._pending_usages) >= _MAX_PENDING_USAGES:
                self._pending_usages.pop(0)
                logger.warning("pending usages limit reached, dropping oldest")
            self._pending_usages.append({
                "vendor_name": vendor_name,
                "ai_model_name": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })

    def track(
        self,
        *,
        customer_id: str,
        revenue_amount_in_cents: int | None = None,
        event_type: str | None = None,
        unique_request_token: str | None = None,
        occurred_at: str | None = None,
    ) -> None:
        """Enqueue an event with all buffered usage data. Never raises."""
        if not self._require_api_key("track"):
            return
        try:
            with self._lock:
                usages = self._pending_usages[:]
                self._pending_usages.clear()

                event: dict[str, Any] = {
                    "customer_id": customer_id,
                    "revenue_amount_in_cents": revenue_amount_in_cents,
                    "vendor_responses": usages,
                    "unique_request_token": unique_request_token or str(uuid4()),
                    "event_type": event_type or self._default_event_type,
                    "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
                }

                if len(self._queue) >= _MAX_QUEUE_SIZE:
                    self._queue.pop(0)
                    logger.warning("queue full, dropping oldest event")
                self._queue.append(event)
        except Exception:
            logger.exception("ai-cost-calc: failed to enqueue event")

    def flush(self) -> None:
        """Send all queued events immediately."""
        if not self._api_key:
            return
        with self._lock:
            events = self._queue[:]
            self._queue.clear()

        for i in range(0, len(events), _BATCH_SIZE):
            batch = events[i : i + _BATCH_SIZE]
            try:
                self._send(batch)
            except Exception as e:
                self._report_error(
                    "Request failed after retries", cause=e, events=batch
                )

    def shutdown(self) -> None:
        """Stop background flushing and send remaining events."""
        if self._stop.is_set():
            return
        self._stop.set()
        if self._api_key:
            atexit.unregister(self.shutdown)
            if self._thread:
                self._thread.join(timeout=5.0)
            self.flush()
        self._session.close()

    # -- Internals ------------------------------------------------------------

    def _require_api_key(self, method: str) -> bool:
        if self._api_key:
            return True
        if not self._api_key_warned:
            self._report_error(f"api_key required for {method} — calls will be skipped")
            self._api_key_warned = True
        return False

    def _ensure_pricing(self) -> None:
        now = time.monotonic()

        # Cache is fresh
        if self._pricing_cache is not None and (now - self._pricing_fetched_at) < _PRICING_CACHE_TTL:
            return

        # Recently failed — back off, use stale cache
        if self._pricing_failed_at and (now - self._pricing_failed_at) < _PRICING_FAILURE_BACKOFF:
            return

        with self._pricing_lock:
            # Double-check after acquiring lock
            now = time.monotonic()
            if self._pricing_cache is not None and (now - self._pricing_fetched_at) < _PRICING_CACHE_TTL:
                return
            if self._pricing_failed_at and (now - self._pricing_failed_at) < _PRICING_FAILURE_BACKOFF:
                return

            try:
                resp = requests.get(
                    f"{self._base_url}/models",
                    headers={"User-Agent": f"ai-cost-calc-python/{_VERSION}"},
                    timeout=_HTTP_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                cache = self._build_pricing_cache(data)

                self._pricing_cache = cache
                self._pricing_fetched_at = time.monotonic()
                self._pricing_failed_at = 0.0
                logger.debug("pricing loaded (%d models)", len(cache))
            except Exception as e:
                self._pricing_failed_at = time.monotonic()
                self._report_error("Failed to fetch pricing data", cause=e)

    def _build_pricing_cache(self, data: Any) -> dict[str, ModelPricing]:
        cache: dict[str, ModelPricing] = {}
        if not isinstance(data, dict):
            return cache

        models = data.get("models")
        if not isinstance(models, list):
            return cache

        for model in models:
            if not isinstance(model, dict):
                continue
            slug = model.get("slug")
            pricing = model.get("pricing")
            if not isinstance(slug, str) or not slug or not isinstance(pricing, dict):
                continue
            inp = pricing.get("input_per_1m_usd")
            out = pricing.get("output_per_1m_usd")
            if not isinstance(inp, (int, float)) or not isinstance(out, (int, float)):
                continue
            if not math.isfinite(inp) or not math.isfinite(out):
                continue
            cache[slug] = ModelPricing(
                slug=slug,
                input_price_per_1m=float(inp),
                output_price_per_1m=float(out),
            )

        return cache

    def _flush_loop(self, interval: float) -> None:
        while not self._stop.wait(interval):
            try:
                self.flush()
            except Exception as e:
                self._report_error(f"Flush error: {e}", cause=e)

    def _send(self, events: list[dict[str, Any]]) -> None:
        last_err: Exception | None = None

        for attempt in range(1 + self._max_retries):
            try:
                resp = self._session.post(
                    f"{self._base_url}/events",
                    json={"events": events},
                    timeout=_HTTP_TIMEOUT,
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    resp.raise_for_status()

                logger.debug("sent %d events (HTTP %d)", len(events), resp.status_code)

                if not resp.ok:
                    self._report_error(
                        f"Request failed with status {resp.status_code}: {resp.text}",
                        events=events,
                    )
                return
            except (requests.ConnectionError, requests.Timeout) as e:
                last_err = e
            except requests.HTTPError as e:
                last_err = e

            if attempt < self._max_retries:
                backoff = min(2.0 ** attempt, _MAX_BACKOFF)
                time.sleep(backoff + backoff * random.uniform(0, 0.5))

        if last_err:
            raise last_err

    def _report_error(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        events: list | None = None,
    ) -> None:
        logger.error("ai-cost-calc: %s", message)
        if self._on_error:
            try:
                self._on_error(AiCostCalcError(message=message, cause=cause, events=events))
            except Exception:
                pass
