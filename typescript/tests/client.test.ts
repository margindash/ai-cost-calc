import { describe, it, beforeEach, afterEach, mock } from "node:test";
import assert from "node:assert/strict";
import { AiCostCalc } from "../src/client.js";

const MOCK_MODELS_RESPONSE = {
  generated_at: "2026-03-09T00:00:00Z",
  models: [
    {
      slug: "gpt-4o",
      name: "GPT-4o",
      provider: "openai",
      pricing: { input_per_1m_usd: 2.5, output_per_1m_usd: 10.0, cache_read_per_1m_usd: 1.25 },
      benchmarks: { variants: [] },
    },
    {
      slug: "gpt-4o-mini",
      name: "GPT-4o Mini",
      provider: "openai",
      pricing: { input_per_1m_usd: 0.15, output_per_1m_usd: 0.6, cache_read_per_1m_usd: 0.075 },
      benchmarks: { variants: [] },
    },
    {
      slug: "claude-sonnet-4",
      name: "Claude Sonnet 4",
      provider: "anthropic",
      pricing: { input_per_1m_usd: 3.0, output_per_1m_usd: 15.0, cache_read_per_1m_usd: null },
      benchmarks: { variants: [] },
    },
  ],
};

function mockFetchSuccess(data: unknown) {
  return mock.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(data),
      text: () => Promise.resolve(JSON.stringify(data)),
    } as unknown as Response)
  );
}

function mockFetchFailure() {
  return mock.fn(() => Promise.reject(new Error("network down")));
}

describe("No API key", () => {
  it("constructor without key does not throw", () => {
    const md = new AiCostCalc();
    assert.ok(md);
  });

  it("addUsage without key is a no-op", () => {
    const md = new AiCostCalc();
    md.addUsage({ vendor: "openai", model: "gpt-4o", inputTokens: 100, outputTokens: 50 });
    // No error thrown — that's the test
  });

  it("track without key is a no-op", () => {
    const md = new AiCostCalc();
    md.track({ customerId: "cust_123" });
  });

  it("flush without key resolves", async () => {
    const md = new AiCostCalc();
    await md.flush();
  });

  it("shutdown without key resolves", async () => {
    const md = new AiCostCalc();
    await md.shutdown();
  });

  it("warns once for tracking methods", () => {
    const errors: { message: string }[] = [];
    const md = new AiCostCalc({ onError: (e) => errors.push(e) });
    md.addUsage({ vendor: "openai", model: "gpt-4o", inputTokens: 100, outputTokens: 50 });
    md.addUsage({ vendor: "openai", model: "gpt-4o", inputTokens: 100, outputTokens: 50 });
    md.track({ customerId: "cust_123" });
    assert.equal(errors.length, 1);
    assert.ok(errors[0].message.includes("apiKey required"));
  });

  it("throws for invalid maxRetries", () => {
    assert.throws(() => new AiCostCalc({ maxRetries: -1 }), /maxRetries must be a non-negative integer/);
    assert.throws(
      () => new AiCostCalc({ maxRetries: 1.5 as unknown as number }),
      /maxRetries must be a non-negative integer/
    );
  });

  it("throws for invalid flushIntervalMs when apiKey is set", () => {
    assert.throws(
      () => new AiCostCalc({ apiKey: "key", flushIntervalMs: 0 }),
      /flushIntervalMs must be a finite number > 0/
    );
    assert.throws(
      () => new AiCostCalc({ apiKey: "key", flushIntervalMs: -1 }),
      /flushIntervalMs must be a finite number > 0/
    );
  });
});

describe("cost()", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns cost result for known model", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);

    assert.ok(result);
    assert.equal(result.model, "gpt-4o");
    assert.equal(result.inputCost, 0.0025);
    assert.equal(result.outputCost, 0.005);
    assert.equal(result.totalCost, 0.0075);
  });

  it("returns null for unknown model", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("nonexistent-model", 1000, 500);
    assert.equal(result, null);
  });

  it("returns null on network failure", async () => {
    globalThis.fetch = mockFetchFailure() as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);
    assert.equal(result, null);
  });

  it("uses stale cache on refetch failure", async () => {
    const successFetch = mockFetchSuccess(MOCK_MODELS_RESPONSE);
    globalThis.fetch = successFetch as unknown as typeof fetch;
    const md = new AiCostCalc();

    // First call populates cache
    const result1 = await md.cost("gpt-4o", 1000, 500);
    assert.ok(result1);

    // Force cache expiry by accessing private field
    (md as any).pricingFetchedAt = 0;

    // Make refetch fail
    globalThis.fetch = mockFetchFailure() as unknown as typeof fetch;
    const result2 = await md.cost("gpt-4o", 1000, 500);

    // Should still return from stale cache (within backoff window)
    assert.ok(result2);
    assert.equal(result2.totalCost, 0.0075);
  });

  it("failure backoff prevents repeated fetches", async () => {
    const failFetch = mockFetchFailure();
    globalThis.fetch = failFetch as unknown as typeof fetch;
    const md = new AiCostCalc();

    await md.cost("gpt-4o", 1000, 500);
    await md.cost("gpt-4o", 1000, 500);
    await md.cost("gpt-4o", 1000, 500);

    // Should only attempt fetch once due to 60s backoff
    assert.equal(failFetch.mock.callCount(), 1);
  });

  it("caches across calls", async () => {
    const successFetch = mockFetchSuccess(MOCK_MODELS_RESPONSE);
    globalThis.fetch = successFetch as unknown as typeof fetch;
    const md = new AiCostCalc();

    await md.cost("gpt-4o", 1000, 500);
    await md.cost("gpt-4o-mini", 1000, 500);
    await md.cost("claude-sonnet-4", 1000, 500);

    // Only one HTTP call — rest served from cache
    assert.equal(successFetch.mock.callCount(), 1);
  });
});

describe("cost() with text", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns estimated result with input and output text", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", "Hello world", "Hi there");

    assert.ok(result);
    assert.equal(result.model, "gpt-4o");
    assert.equal(result.estimated, true);
    assert.ok(typeof result.inputTokens === "number" && result.inputTokens > 0);
    assert.ok(typeof result.outputTokens === "number" && result.outputTokens > 0);
  });

  it("returns estimated result with input text only (pre-call)", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", "Hello world");

    assert.ok(result);
    assert.equal(result.estimated, true);
    assert.ok(typeof result.inputTokens === "number" && result.inputTokens > 0);
    assert.equal(result.outputTokens, 0);
    assert.equal(result.outputCost, 0);
  });

  it("falls back to cl100k_base for non-OpenAI models", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("claude-sonnet-4", "Hello world");

    assert.ok(result);
    assert.equal(result.estimated, true);
    assert.ok(typeof result.inputTokens === "number" && result.inputTokens > 0);
  });

  it("returns null with error for mixed token/text args", async () => {
    const errors: { message: string }[] = [];
    const md = new AiCostCalc({ onError: (e) => errors.push(e) });
    // @ts-expect-error — intentionally passing wrong arg types
    const result = await md.cost("gpt-4o", 1000, "foo");

    assert.equal(result, null);
    assert.equal(errors.length, 1);
    assert.ok(errors[0].message.includes("outputTokens is required"));
  });

  it("populates new fields on token-based cost", async () => {
    globalThis.fetch = mockFetchSuccess(MOCK_MODELS_RESPONSE) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);

    assert.ok(result);
    assert.equal(result.inputTokens, 1000);
    assert.equal(result.outputTokens, 500);
    assert.equal(result.estimated, false);
  });

  it("returns null for oversized text", async () => {
    const errors: { message: string }[] = [];
    const md = new AiCostCalc({ onError: (e) => errors.push(e) });
    const bigText = "x".repeat(1_000_001);
    const result = await md.cost("gpt-4o", bigText);

    assert.equal(result, null);
    assert.ok(errors.some(e => e.message.includes("1MB")));
  });

  it("returns null when outputTokens missing in number mode", async () => {
    const errors: { message: string }[] = [];
    const md = new AiCostCalc({ onError: (e) => errors.push(e) });
    // @ts-expect-error — intentionally omitting outputTokens
    const result = await md.cost("gpt-4o", 1000);

    assert.equal(result, null);
    assert.ok(errors.some(e => e.message.includes("outputTokens")));
  });
});

describe("Defensive parsing", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("skips malformed top-level model entries", async () => {
    globalThis.fetch = mockFetchSuccess({
      models: [
        "not-a-dict",
        {
          slug: "gpt-4o",
          pricing: { input_per_1m_usd: 2.5, output_per_1m_usd: 10.0 },
        },
      ],
    }) as unknown as typeof fetch;

    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);
    assert.ok(result);
  });

  it("skips malformed model entries", async () => {
    globalThis.fetch = mockFetchSuccess({
      models: [
        "not-a-dict",
        { slug: "gpt-4o", pricing: { input_per_1m_usd: 2.5, output_per_1m_usd: 10.0 } },
        { slug: "bad", pricing: { input_per_1m_usd: "not-a-number", output_per_1m_usd: 10.0 } },
        { slug: "nan", pricing: { input_per_1m_usd: NaN, output_per_1m_usd: 10.0 } },
        { slug: "", pricing: { input_per_1m_usd: 1.0, output_per_1m_usd: 1.0 } },
      ],
    }) as unknown as typeof fetch;

    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);
    assert.ok(result);

    // Only gpt-4o should be cached
    assert.equal((md as any).pricingCache.size, 1);
  });

  it("handles missing models key", async () => {
    globalThis.fetch = mockFetchSuccess({}) as unknown as typeof fetch;
    const md = new AiCostCalc();
    const result = await md.cost("gpt-4o", 1000, 500);
    assert.equal(result, null);
  });

});
