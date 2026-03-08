# ai-cost-calc

AI cost calculator and usage tracker for LLM apps.

- Powered by MarginDash live pricing fetched at runtime (not a bundled static pricing file)
- AI API pricing changes often, so costs stay accurate without manual table updates
- Privacy-first: your app talks directly to AI providers; prompts and responses stay in your stack
- Free cost calculator mode needs no API key; tracking mode is optional

## Packages

- npm (JavaScript/TypeScript): https://www.npmjs.com/package/ai-cost-calc
- PyPI (Python): https://pypi.org/project/ai-cost-calc/

## SDKs

- [TypeScript SDK](./typescript/README.md)
- [Python SDK](./python/README.md)

## Quick Start

TypeScript:

```bash
npm install ai-cost-calc
```

Python:

```bash
pip install ai-cost-calc
```

## Which Mode to Use

- Free cost calculator: call `cost(...)` with exact token counts or prompt/response text
- Usage tracking: use `addUsage`/`track` (TypeScript) or `add_usage`/`track` (Python) with an API key

## Pricing Data

Cost calculation uses live pricing fetched from the API, with caching and retry behavior in each SDK.

