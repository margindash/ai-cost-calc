# ai-cost-calc

[![npm version](https://img.shields.io/npm/v/ai-cost-calc.svg)](https://www.npmjs.com/package/ai-cost-calc)
[![PyPI version](https://img.shields.io/pypi/v/ai-cost-calc.svg)](https://pypi.org/project/ai-cost-calc/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

AI cost calculator and usage tracker for LLM apps.

- Live model pricing fetched at runtime (not a bundled static pricing file)
- Built for AI APIs where pricing changes often
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
const result = await calc.cost("gpt-4o", 1000, 500);
if (!result) return;
console.log(result.totalCost);
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc()
result = calc.cost("gpt-4o", input_tokens=1000, output_tokens=500)
if result is None:
    raise RuntimeError("Could not calculate cost")
print(result.total_cost)
```

## Quickstart: Estimate Cost From Text

JavaScript / TypeScript:

```ts
import { AiCostCalc } from "ai-cost-calc";

const calc = new AiCostCalc();
const result = await calc.cost("gpt-4o", "Write a release note for this PR.");
if (!result) return;
console.log(result.inputTokens, result.outputTokens, result.estimated);
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc()
result = calc.cost("gpt-4o", input_text="Write a release note for this PR.")
if result is None:
    raise RuntimeError("Could not estimate cost")
print(result.input_tokens, result.output_tokens, result.estimated)
```

## Optional Usage Tracking

Use this mode when you want customer-level usage and revenue event tracking.

JavaScript / TypeScript:

```ts
import { AiCostCalc } from "ai-cost-calc";

const calc = new AiCostCalc({ apiKey: process.env.AI_COST_CALC_API_KEY });

calc.addUsage({
  vendor: "openai",
  model: "gpt-4o",
  inputTokens: 1000,
  outputTokens: 500,
});

calc.track({ customerId: "cust_123", eventType: "chat" });
await calc.shutdown();
```

Python:

```py
from ai_cost_calc import AiCostCalc

calc = AiCostCalc(api_key="YOUR_API_KEY")

calc.add_usage(
    vendor="openai",
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500,
)

calc.track(customer_id="cust_123", event_type="chat")
calc.shutdown()
```

## Modes At A Glance

| Need | Mode |
| --- | --- |
| Quick cost checks with no account setup | `cost(...)` |
| Exact costs from provider token usage | token-count `cost` |
| Early estimation from prompt/response text | text-based `cost` |
| Customer and revenue tracking | `addUsage`/`track` (TS) or `add_usage`/`track` (Python) with `apiKey` |

## How Pricing Works

- Cost calculation fetches live pricing from the MarginDash API at runtime
- Each `AiCostCalc` instance caches pricing for 24 hours
- If a refresh fails after a successful fetch, the SDK reuses last-known pricing and retries after backoff

## Privacy Model

- Free cost calculator mode: no API key required, no prompt/response data sent to MarginDash
- Tracking mode: sends usage and event metadata (model, token counts, customer/event fields)
- Your app still calls AI providers directly; no proxy hop is added

## SDK Docs

- [TypeScript SDK README](./typescript/README.md)
- [Python SDK README](./python/README.md)
