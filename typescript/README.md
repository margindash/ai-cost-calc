# ai-cost-calc (JavaScript/TypeScript)

AI cost calculator and usage tracker for LLM apps.

- Built for production-grade cost tracking, with pricing verification and continuous updates as model prices change.
- Privacy-first: your app still talks directly to AI providers, so prompts/responses stay in your stack
- Tracking is optional and sends usage plus event metadata (customer ID, event type, revenue if provided)

Use it in two ways:
- Free cost calculator (`cost`) for 400+ models (no API key required):
  - exact mode with token counts (`inputTokens`, `outputTokens`)
  - estimate mode with prompt/response text (`inputText`, `outputText`)
  - live pricing with 24h cache per `AiCostCalc` instance
- Usage tracking (`addUsage` + `track`) with an API key

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

- Node.js 18+

## Installation

```bash
npm install ai-cost-calc
```

For the tracking quickstart, install your provider SDK separately.

For text-based estimation, `js-tiktoken` is used. It is an optional dependency,
so some environments may skip it. If needed:

```bash
npm install js-tiktoken
```

## Quickstart (Cost Calculator)

```typescript
import { AiCostCalc } from "ai-cost-calc";

async function run() {
  const md = new AiCostCalc();

  // Exact cost from token counts
  const result = await md.cost("provider/model-name", 1000, 500);

  // Estimate from input + output text
  const result2 = await md.cost("provider/model-name", "Write a release note for this PR.", "Here is the release note for v1.3.7.");

  // Estimate from input text only (output defaults to 0 tokens)
  const result3 = await md.cost("provider/model-name", "Write a release note for this PR.");
}

run();
```

## Quickstart (Usage Tracking)

Use an API key from your MarginDash dashboard.

```typescript
import { AiCostCalc } from "ai-cost-calc";

async function run() {
  const md = new AiCostCalc({ apiKey: process.env.AI_COST_CALC_API_KEY });

  const response = await md.guardedCall(
    { customerId: "cust_123", eventType: "chat" },
    () => providerCall()
  );

  md.addUsage({
    model: response.model,
    inputTokens: response.usage?.prompt_tokens,
    outputTokens: response.usage?.completion_tokens,
  });

  md.track({
    customerId: "cust_123",
    eventType: "chat",
    revenueAmountInCents: 250,
  });
  console.log(response.id);

  await md.shutdown();
}

run();
```

## When to Use Which Mode

| If you need... | Use... |
| --- | --- |
| Quick cost checks with no account setup | `cost()` only |
| Exact costs from provider token usage | `cost(model, inputTokens, outputTokens)` |
| Early estimation from prompt/response text | `cost(model, inputText, outputText?)` |
| MarginDash customer/revenue tracking | `addUsage()` + `track()` with `apiKey` |
| SDK-side budget blocking | `guardedCall()` with `apiKey` |

## Return Values and Failure Modes

| Method | Failure behavior |
| --- | --- |
| `cost()` | Returns `null` |
| `addUsage()` / `track()` without `apiKey` | No-op, reports via `onError` once |
| `guardedCall()` | Throws when blocked by budget; defaults to fail-open on blocklist fetch failure |
| `flush()` / `shutdown()` | Do not throw for request failures; report via `onError` |

## Common Integration Patterns

Provider response (`prompt_tokens` / `completion_tokens`):

```typescript
md.addUsage({
  model: response.model,
  inputTokens: response.usage?.prompt_tokens ?? 0,
  outputTokens: response.usage?.completion_tokens ?? 0,
});
```

Anthropic (`messages`):

```typescript
md.addUsage({
  model: response.model,
  inputTokens: response.usage?.input_tokens ?? 0,
  outputTokens: response.usage?.output_tokens ?? 0,
});
```

Google Gemini:

```typescript
md.addUsage({
  model: response.modelVersion ?? "google/gemini-2.5-flash",
  inputTokens: response.usageMetadata?.promptTokenCount ?? 0,
  outputTokens: response.usageMetadata?.candidatesTokenCount ?? 0,
});
```

## Environment Variables

- `AI_COST_CALC_API_KEY`: required only for tracking (from your MarginDash dashboard)
- `PROVIDER_API_KEY`: only needed if your provider SDK requires one

## API Reference

### `cost(model, inputTokens, outputTokens)`

Exact cost mode.

- `model`: model slug (example: `provider/model-name`, `anthropic/claude-sonnet-4`)
- `inputTokens`: non-negative integer
- `outputTokens`: non-negative integer

### `cost(model, inputText, outputText?)`

Estimated cost mode using `js-tiktoken`.

- `inputText`: prompt text
- `outputText`: optional response text (defaults to 0 output tokens)

Returns `Promise<CostResult | null>`.

`null` means one of:
- unknown model
- pricing fetch unavailable
- invalid arguments
- tokenizer unavailable/failure in estimate mode

`CostResult` fields:
- `model`
- `inputCost`
- `outputCost`
- `totalCost`
- `inputTokens`
- `outputTokens`
- `estimated`

### `addUsage({ model, inputTokens, outputTokens })`

Buffers usage from one AI call. Requires `apiKey` in constructor.

### `track({ customerId, revenueAmountInCents?, eventType?, uniqueRequestToken?, occurredAt? })`

Creates an event from all currently buffered usage entries and enqueues it for delivery.
Requires `apiKey`.

### `guardedCall({ customerId, eventType? }, callFn)`

Runs `callFn` only when current cached budget state allows it.

- `customerId`: required
- `eventType`: optional
- `callFn`: your provider call callback

Behavior:

- Polls `GET /api/v1/budgets/blocklist` using TTL/version caching
- Triggers immediate refresh when `/events` response returns a newer `budget_state_version`
- Throws when blocked by organization/event/customer budget
- Fail-open by default when blocklist fetch fails (set `budgetFailClosed: true` to invert)

### `flush()`

Immediately sends queued events. Returns `Promise<void>`.

### `shutdown()`

Stops the background flush timer and flushes remaining events. Returns `Promise<void>`.
Call this before process exit.

## Configuration

```typescript
import { AiCostCalc } from "ai-cost-calc";

const md = new AiCostCalc({
  apiKey: process.env.AI_COST_CALC_API_KEY, // optional for cost(); required for tracking
  baseUrl: "https://margindash.com/api/v1",
  flushIntervalMs: 5000,
  maxRetries: 3,
  defaultEventType: "ai_request",
  budgetFailClosed: false,
  debug: false,
  onError: (err) => console.error(err.message),
});
```

Options:
- `apiKey` (optional)
- `baseUrl` (default `https://margindash.com/api/v1`)
- `flushIntervalMs` (default `5000`, must be a finite number `> 0` when `apiKey` is set)
- `maxRetries` (default `3`, must be a non-negative integer)
- `defaultEventType` (default `ai_request`)
- `budgetFailClosed` (default `false`; when `true`, blocks `guardedCall` if budget state cannot be refreshed)
- `debug` (default `false`)
- `onError` (optional callback)

## Error Handling

The SDK is non-throwing for normal tracking/cost failures and reports errors via:
- `onError` callback
- console logs when `debug: true`

Example:

```typescript
const md = new AiCostCalc({
  apiKey: process.env.AI_COST_CALC_API_KEY,
  onError: (err) => console.error(err.message),
});
```

## Delivery Semantics

Tracking behavior:
- in-memory queue size limit: 1000 events (oldest dropped when full)
- pending usage limit before `track`: 1000 items (oldest dropped when full)
- batch size: 50 events/request
- retries on network errors, HTTP `429`, and `5xx` with exponential backoff

Idempotency:
- `uniqueRequestToken` is the idempotency key for an event
- if omitted, SDK auto-generates a UUID
- for retry-safe exactly-once behavior across your own retries, provide your own stable token

## Privacy

Free cost mode only fetches pricing data.
If tracking is enabled, the SDK sends event metadata (for example: customer ID, event type, revenue), plus model and token counts.
Request/response content is not sent.

## Troubleshooting

- `cost()` returns `null`:
  - verify model slug
  - check network access to the pricing API
  - add `onError` and/or `debug: true`
- numbers look outdated:
  - pricing cache TTL is 24 hours per `AiCostCalc` instance
  - create a new `AiCostCalc` instance for an immediate refresh if needed
- text estimation fails:
  - install `js-tiktoken` (`npm install js-tiktoken`)
- tracking methods appear to do nothing:
  - confirm `apiKey` is set in constructor
- events missing on shutdown:
  - `await md.shutdown()` before process exits

## Versioning and Releases

This SDK follows semantic versioning.

- npm package: `ai-cost-calc`
- changelog: [CHANGELOG.md](./CHANGELOG.md)
- check release history on npm/GitHub before major upgrades

## License

MIT
