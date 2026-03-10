# ai-cost-calc (Python)

AI cost calculator and usage tracker for LLM apps.

- Built for production-grade cost tracking, with pricing verification and continuous updates as model prices change.
- Privacy-first: your app still talks directly to AI providers, so prompts/responses stay in your stack
- Tracking is optional and sends usage plus event metadata (customer ID, event type, revenue if provided)

Use it in two ways:
- Free cost calculator (`cost`) for 400+ models (no API key required):
  - exact mode with token counts (`input_tokens`, `output_tokens`)
  - estimate mode with prompt/response text (`input_text`, `output_text`)
  - live pricing with 24h cache per `AiCostCalc` instance
- Usage tracking (`add_usage` + `track`) with an API key

## Pricing Data

The `model` passed to `cost(...)` must match a `slug` from: https://margindash.com/api/v1/models

- The SDK reads pricing from:
  - `models[].pricing.input_per_1m_usd`
  - `models[].pricing.output_per_1m_usd`
- The API also returns benchmark variants at `models[].benchmarks.variants` (not required for `cost()`)
- Pricing data is cached per `AiCostCalc` instance for 24 hours
- Cache refresh happens automatically when the cache is stale
- If a refresh fails after a successful fetch, the SDK reuses last-known pricing and retries after backoff

## Caching Behavior

- Cache scope: per `AiCostCalc` instance
- Cache TTL: 24 hours
- Refresh failures: last-known pricing is reused, then retried after backoff
- Force refresh now: create a new `AiCostCalc` instance

## Requirements

- Python 3.10+

## Installation

```bash
pip install ai-cost-calc
```

For the tracking quickstart, install your provider SDK separately.

For text-based estimation with `tiktoken`:

```bash
pip install ai-cost-calc[estimate]
```

## Quickstart (Cost Calculator)

```python
from ai_cost_calc import AiCostCalc

md = AiCostCalc()

# Exact cost from token counts
result = md.cost("provider/model-name", input_tokens=1000, output_tokens=500)

# Estimate from input + output text
result2 = md.cost("provider/model-name", input_text="Write a release note for this PR.", output_text="Here is the release note for v1.3.7.")

# Estimate from input text only (output defaults to 0 tokens)
result3 = md.cost("provider/model-name", input_text="Write a release note for this PR.")
```

## Quickstart (Usage Tracking)

Use an API key from your MarginDash dashboard.

```python
from ai_cost_calc import AiCostCalc

md = AiCostCalc(api_key="YOUR_API_KEY")

response = md.guarded_call(
    customer_id="cust_123",
    event_type="chat",
    call=lambda: provider_call(),
)

md.add_usage(
    model=response.model,
    input_tokens=(response.usage.prompt_tokens if response.usage else 0),
    output_tokens=(response.usage.completion_tokens if response.usage else 0),
)

md.track(
    customer_id="cust_123",
    event_type="chat",
    revenue_amount_in_cents=250,
)
print(response.id)


md.shutdown()
```

`guarded_call` is synchronous and can do blocking HTTP I/O while refreshing budget state.
In async frameworks (for example FastAPI), run it in a thread executor.
Prefer `async_guarded_call` in async apps.

```python
import asyncio
from ai_cost_calc import AiCostCalc

md = AiCostCalc(api_key="YOUR_API_KEY")

async def main():
    result = await md.async_guarded_call(
        customer_id="cust_123",
        event_type="chat",
        call=lambda: {"ok": True},
    )
    print(result)

asyncio.run(main())
```

## When to Use Which Mode

| If you need... | Use... |
| --- | --- |
| Quick cost checks with no account setup | `cost()` only |
| Exact costs from provider token usage | `cost(model, input_tokens, output_tokens)` |
| Early estimation from prompt/response text | `cost(model, input_text, output_text)` |
| MarginDash customer/revenue tracking | `add_usage()` + `track()` with `api_key` |
| SDK-side budget blocking | `guarded_call()` with `api_key` |

## Return Values and Failure Modes

| Method | Failure behavior |
| --- | --- |
| `cost()` | Returns `None` |
| `add_usage()` / `track()` without `api_key` | No-op, reports via `on_error` once |
| `guarded_call()` | Raises when blocked by budget; defaults to fail-open on blocklist fetch failure |
| `async_guarded_call()` | Same blocking semantics as `guarded_call()`, without blocking the event loop for budget refresh |
| `flush()` / `shutdown()` | Do not raise for request failures; report via `on_error` |

## Common Integration Patterns

Provider response (`prompt_tokens` / `completion_tokens`):

```python
md.add_usage(
    model=response.model,
    input_tokens=(response.usage.prompt_tokens if response.usage else 0),
    output_tokens=(response.usage.completion_tokens if response.usage else 0),
)
```

Anthropic (`messages`):

```python
md.add_usage(
    model=response.model,
    input_tokens=(response.usage.input_tokens if response.usage else 0),
    output_tokens=(response.usage.output_tokens if response.usage else 0),
)
```

Google Gemini:

```python
usage = response.get("usageMetadata", {})
md.add_usage(
    model=response.get("modelVersion", "google/gemini-2.5-flash"),
    input_tokens=usage.get("promptTokenCount", 0),
    output_tokens=usage.get("candidatesTokenCount", 0),
)
```

## End-to-End Async Example (FastAPI + Provider SDK)

```python
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from ai_cost_calc import AiCostCalc

md = AiCostCalc(api_key=os.environ["AI_COST_CALC_API_KEY"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        md.shutdown()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    customer_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    response = await md.async_guarded_call(
        customer_id=req.customer_id,
        event_type="chat",
        call=lambda: provider_call(req.message),
    )

    usage = response.usage
    md.add_usage(
        model=response.model,
        input_tokens=(usage.prompt_tokens if usage else 0),
        output_tokens=(usage.completion_tokens if usage else 0),
    )
    md.track(customer_id=req.customer_id, event_type="chat")

    # Adapt response parsing to your provider response shape.
    return {"text": getattr(response, "text", None)}
```

## Environment Variables

Recommended pattern:

```python
import os
from ai_cost_calc import AiCostCalc

md = AiCostCalc(api_key=os.getenv("AI_COST_CALC_API_KEY"))
```

Common env vars:
- `AI_COST_CALC_API_KEY`: required only for tracking (from your MarginDash dashboard)
- `PROVIDER_API_KEY`: only needed if your provider SDK requires one

## API Reference

### `cost(model, *, input_tokens, output_tokens)`

Exact cost mode.

- `model`: model slug (example: `provider/model-name`, `anthropic/claude-sonnet-4`)
- `input_tokens`: non-negative integer
- `output_tokens`: non-negative integer

### `cost(model, *, input_text, output_text=None)`

Estimated cost mode using `tiktoken`.

- `input_text`: prompt text
- `output_text`: optional response text (defaults to 0 output tokens)

Returns `CostResult | None`.

`None` means one of:
- unknown model
- pricing fetch unavailable
- invalid arguments
- tokenizer unavailable/failure in estimate mode

`CostResult` fields:
- `model`
- `input_cost`
- `output_cost`
- `total_cost`
- `input_tokens`
- `output_tokens`
- `estimated`

### `add_usage(*, model, input_tokens, output_tokens)`

Buffers usage from one AI call. Requires `api_key` in constructor.

### `track(*, customer_id, revenue_amount_in_cents=None, event_type=None, unique_request_token=None, occurred_at=None)`

Creates an event from all currently buffered usage entries and enqueues it for delivery.
Requires `api_key`.

### `guarded_call(*, customer_id, call, event_type=None)`

Runs `call` only when current cached budget state allows it.

- `customer_id`: required
- `event_type`: optional
- `call`: provider call callback

Behavior:

- Polls `GET /api/v1/budgets/blocklist` using TTL/version caching
- Triggers immediate refresh when `/events` response returns a newer `budget_state_version`
- Raises when blocked by organization/event/customer budget
- Fail-open by default when blocklist fetch fails (set `budget_fail_closed=True` to invert)
- Synchronous method; can block up to the blocklist timeout during refresh

### `async_guarded_call(*, customer_id, call, event_type=None)`

Async variant of `guarded_call` for asyncio applications.

- Runs budget refresh/check in a thread to avoid blocking the event loop
- Accepts sync or async `call` callbacks
- Uses the same budget blocking semantics as `guarded_call`

### `flush()`

Immediately sends queued events.

### `shutdown()`

Stops background flushing thread and sends remaining events.
Call this before application exit.

## Configuration

```python
from ai_cost_calc import AiCostCalc

md = AiCostCalc(
    api_key="md_live_...",                     # optional for cost(); required for tracking
    base_url="https://margindash.com/api/v1",
    flush_interval=5.0,
    max_retries=3,
    default_event_type="ai_request",
    budget_fail_closed=False,
    on_error=lambda err: print(err.message),
)
```

Options:
- `api_key` (optional)
- `base_url` (default `https://margindash.com/api/v1`)
- `flush_interval` seconds (default `5.0`, must be a finite number `> 0` when `api_key` is set)
- `max_retries` (default `3`, must be a non-negative integer)
- `default_event_type` (default `ai_request`)
- `budget_fail_closed` (default `False`; when `True`, blocks `guarded_call` if budget state cannot be refreshed)
- `on_error` (optional callback)

## Error Handling

The SDK avoids raising for typical operational failures in cost/tracking flows.
Use `on_error` for observability.

```python
from ai_cost_calc import AiCostCalc

md = AiCostCalc(api_key="md_live_...", on_error=lambda err: print(err.message))
```

## Delivery Semantics

Tracking behavior:
- in-memory queue size limit: 1000 events (oldest dropped when full)
- pending usage limit before `track`: 1000 items (oldest dropped when full)
- batch size: 50 events/request
- retries on connection/timeouts, HTTP `429`, and `5xx` with exponential backoff

Idempotency:
- `unique_request_token` is the idempotency key for an event
- if omitted, SDK auto-generates a UUID
- for retry-safe exactly-once behavior across your own retries, provide your own stable token

## Privacy

Free cost mode only fetches pricing data.
If tracking is enabled, the SDK sends event metadata (for example: customer ID, event type, revenue), plus model and token counts.
Request/response content is not sent.

## Troubleshooting

- `cost()` returns `None`:
  - verify model slug
  - check network access to the pricing API
  - wire `on_error` callback for details
- numbers look outdated:
  - pricing cache TTL is 24 hours per `AiCostCalc` instance
  - create a new `AiCostCalc` instance for an immediate refresh if needed
- text estimation fails:
  - install extras: `pip install ai-cost-calc[estimate]`
- tracking methods appear to do nothing:
  - confirm `api_key` is set in constructor
- async app stalls on `guarded_call`:
  - use `async_guarded_call`, or run `guarded_call` in a thread executor
- events missing on shutdown:
  - call `md.shutdown()` before app exits

## Versioning and Releases

This SDK follows semantic versioning.

- PyPI package: `ai-cost-calc`
- changelog: [CHANGELOG.md](./CHANGELOG.md)
- check release history on PyPI/GitHub before major upgrades

## License

MIT
