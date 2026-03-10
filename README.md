# ai-cost-calc

[![npm version](https://img.shields.io/npm/v/ai-cost-calc.svg)](https://www.npmjs.com/package/ai-cost-calc)
[![PyPI version](https://img.shields.io/pypi/v/ai-cost-calc.svg)](https://pypi.org/project/ai-cost-calc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

AI cost calculator and usage tracker for LLM apps.

- Built for production-grade cost tracking, with pricing verification and continuous updates as model prices change.
- Privacy-first by default: your app keeps talking directly to AI providers
- Free cost calculator requires no API key
- Optional tracking mode sends usage and event metadata only

Powered by MarginDash live pricing.

The `model` passed to `cost(...)` must match a `slug` from:
https://margindash.com/api/v1/models

## Who This Is For

Teams building AI features that need accurate cost visibility without proxying prompts.

## Install

### JavaScript / TypeScript

```bash
npm install ai-cost-calc
```

Text estimation uses `js-tiktoken` (optional dependency). If your environment skips optional dependencies:

```bash
npm install js-tiktoken
```

### Python

```bash
pip install ai-cost-calc
```

Text estimation (optional):

```bash
pip install ai-cost-calc[estimate]
```

## Quickstart: Exact Cost From Token Counts

JavaScript / TypeScript:

```ts
import { AiCostCalc } from "ai-cost-calc";

const calc = new AiCostCalc();
const result = await calc.cost("provider/model-name", 1000, 500);
console.log(result.totalCost);
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc()
result = calc.cost("provider/model-name", input_tokens=1000, output_tokens=500)
print(result.total_cost)
```

## Quickstart: Estimate Cost From Text

JavaScript / TypeScript:

```ts
import { AiCostCalc } from "ai-cost-calc";

const calc = new AiCostCalc();

// Input text only
const result = await calc.cost("provider/model-name", "Write a release note for this PR.");

// Input + output text
const result2 = await calc.cost("provider/model-name", "Write a release note for this PR.", "Here is the release note for v1.3.7.");
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc()

# Input text only
result = calc.cost("provider/model-name", input_text="Write a release note for this PR.")

# Input + output text
result2 = calc.cost("provider/model-name", input_text="Write a release note for this PR.", output_text="Here is the release note for v1.3.7.")
```

## Optional Usage Tracking

Use this mode when you want customer-level usage and revenue event tracking.

JavaScript / TypeScript:

```ts
import { AiCostCalc } from "ai-cost-calc";

const calc = new AiCostCalc({ apiKey: process.env.AI_COST_CALC_API_KEY });

const response = await calc.guardedCall(
  { customerId: "cust_123", eventType: "chat" },
  () => providerCall()
);

calc.addUsage({
  model: response.model,
  inputTokens: response.usage?.prompt_tokens,
  outputTokens: response.usage?.completion_tokens,
});

calc.track({ customerId: "cust_123", eventType: "chat" });
await calc.shutdown();
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc(api_key="YOUR_API_KEY")

response = calc.guarded_call(customer_id="cust_123", event_type="chat", call=lambda: provider_call())

calc.add_usage(
    model=response.model,
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
)

calc.track(customer_id="cust_123", event_type="chat")
calc.shutdown()

```

Note: Python `guarded_call` is synchronous; in async frameworks (for example FastAPI), use `async_guarded_call` (or run `guarded_call` in a thread executor).

## Modes At A Glance

| Need | Mode |
| --- | --- |
| Quick cost checks with no account setup | `cost(...)` |
| Exact costs from provider token usage | token-count `cost` |
| Early estimation from prompt/response text | text-based `cost` |
| Customer and revenue tracking | `addUsage`/`track` (TS) or `add_usage`/`track` (Python) with `apiKey` |
| SDK-side budget blocking | `guardedCall` (TS) / `guarded_call` or `async_guarded_call` (Python) with `apiKey` |

## How Pricing Works

- Cost calculation fetches live pricing from the MarginDash API at runtime
- SDKs read pricing from `GET /api/v1/models` using:
  - `models[].pricing.input_per_1m_usd`
  - `models[].pricing.output_per_1m_usd`
- The endpoint also includes benchmark data at `models[].benchmarks.variants` (available for downstream use; not required for `cost(...)`)
- Each `AiCostCalc` instance caches pricing for 24 hours
- If a refresh fails after a successful fetch, the SDK reuses last-known pricing and retries after backoff

## Privacy Model

- Free cost calculator mode: no API key required, no prompt/response data sent to MarginDash
- Tracking mode: sends usage and event metadata (model, token counts, customer/event fields)
- Your app still calls AI providers directly; no proxy hop is added

## SDK Docs

- [TypeScript SDK README](./typescript/README.md)
- [Python SDK README](./python/README.md)
- [TypeScript Changelog](./typescript/CHANGELOG.md)
- [Python Changelog](./python/CHANGELOG.md)
