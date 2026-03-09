import { AiCostCalc } from "ai-cost-calc";

const API_KEY = process.env.MARGINDASH_API_KEY;
if (!API_KEY) {
  console.error("Set MARGINDASH_API_KEY env var to run system tests");
  process.exit(1);
}
let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (condition) { passed++; console.log(`  ✓ ${msg}`); }
  else { failed++; console.error(`  ✗ ${msg}`); }
}

console.log("=== TYPESCRIPT SDK COMPREHENSIVE TEST ===\n");

// ============================================================
// TEST 1: cost() with exact token counts (root README example)
// ============================================================
console.log("--- TEST 1: cost(model, inputTokens, outputTokens) ---");
const calc1 = new AiCostCalc({ debug: true });
const result1 = await calc1.cost("openai/gpt-4o", 1000, 500);
assert(result1 !== null, "result is not null");
assert(result1.model === "openai/gpt-4o", `model = ${result1.model}`);
assert(result1.totalCost > 0, `totalCost = ${result1.totalCost}`);
assert(result1.inputCost > 0, `inputCost = ${result1.inputCost}`);
assert(result1.outputCost > 0, `outputCost = ${result1.outputCost}`);
assert(result1.inputTokens === 1000, `inputTokens = ${result1.inputTokens}`);
assert(result1.outputTokens === 500, `outputTokens = ${result1.outputTokens}`);
assert(result1.estimated === false, `estimated = ${result1.estimated}`);
console.log();

// ============================================================
// TEST 2: cost() with input text only (root README example)
// ============================================================
console.log("--- TEST 2: cost(model, inputText) ---");
const result2 = await calc1.cost("openai/gpt-4o", "Write a release note for this PR.");
assert(result2 !== null, "result is not null");
assert(result2.inputTokens > 0, `inputTokens = ${result2.inputTokens}`);
assert(result2.outputTokens === 0, `outputTokens = ${result2.outputTokens}`);
assert(result2.estimated === true, `estimated = ${result2.estimated}`);
console.log();

// ============================================================
// TEST 3: cost() with input + output text (root README example)
// ============================================================
console.log("--- TEST 3: cost(model, inputText, outputText) ---");
const result3 = await calc1.cost("openai/gpt-4o", "Write a release note for this PR.", "Here is the release note for v1.3.7.");
assert(result3 !== null, "result is not null");
assert(result3.inputTokens > 0, `inputTokens = ${result3.inputTokens}`);
assert(result3.outputTokens > 0, `outputTokens = ${result3.outputTokens}`);
assert(result3.estimated === true, `estimated = ${result3.estimated}`);
console.log();

// ============================================================
// TEST 4: cost() with different models
// ============================================================
console.log("--- TEST 4: cost() with anthropic/claude-sonnet-4 ---");
const result4 = await calc1.cost("anthropic/claude-sonnet-4", 1000, 500);
assert(result4 !== null, "result is not null");
assert(result4.model === "anthropic/claude-sonnet-4", `model = ${result4.model}`);
assert(result4.totalCost > 0, `totalCost = ${result4.totalCost}`);
console.log();

console.log("--- TEST 4b: cost() with google/gemini-2.5-flash ---");
const result4b = await calc1.cost("google/gemini-2.5-flash", 1000, 500);
assert(result4b !== null, "result is not null");
assert(result4b.model === "google/gemini-2.5-flash", `model = ${result4b.model}`);
assert(result4b.totalCost > 0, `totalCost = ${result4b.totalCost}`);
console.log();

// ============================================================
// TEST 4c: cost() with more vendors (Bedrock, Groq, Meta)
// ============================================================
console.log("--- TEST 4c: cost() with additional vendors ---");
const bedrockResult = await calc1.cost("amazon/nova-pro-v1", 1000, 500);
assert(bedrockResult !== null, "amazon/nova-pro-v1 returned pricing");
if (bedrockResult) assert(bedrockResult.totalCost > 0, `amazon/nova-pro-v1 totalCost = ${bedrockResult.totalCost}`);

const groqResult = await calc1.cost("meta-llama/llama-3.3-70b-instruct", 1000, 500);
assert(groqResult !== null, "meta-llama/llama-3.3-70b-instruct returned pricing");
if (groqResult) assert(groqResult.totalCost > 0, `meta-llama/llama-3.3-70b-instruct totalCost = ${groqResult.totalCost}`);

const mistralResult = await calc1.cost("mistralai/mistral-large-2411", 1000, 500);
assert(mistralResult !== null, "mistralai/mistral-large-2411 returned pricing");
if (mistralResult) assert(mistralResult.totalCost > 0, `mistralai/mistral-large-2411 totalCost = ${mistralResult.totalCost}`);
console.log();

// ============================================================
// TEST 5: cost() with unknown model
// ============================================================
console.log("--- TEST 5: cost() with unknown model ---");
const result5 = await calc1.cost("fake/not-a-model", 1000, 500);
assert(result5 === null, `unknown model returns null (got ${result5})`);
console.log();

// ============================================================
// TEST 5a: cost() with negative tokens — returns null
// ============================================================
console.log("--- TEST 5a: cost() with negative tokens ---");
const errNeg = [];
const calcNeg = new AiCostCalc({ onError: (e) => errNeg.push(e.message) });
const resultNeg = await calcNeg.cost("openai/gpt-4o", -100, 500);
assert(resultNeg === null, `negative inputTokens returns null`);
const resultNeg2 = await calcNeg.cost("openai/gpt-4o", 100, -500);
assert(resultNeg2 === null, `negative outputTokens returns null`);
assert(errNeg.length >= 2, `onError called ${errNeg.length} times`);
console.log();

// ============================================================
// TEST 5b: cost() with zero tokens
// ============================================================
console.log("--- TEST 5b: cost() with zero tokens ---");
const resultZero = await calc1.cost("openai/gpt-4o", 0, 0);
assert(resultZero !== null, "result is not null");
assert(resultZero.totalCost === 0, `totalCost = ${resultZero.totalCost}`);
assert(resultZero.inputCost === 0, `inputCost = ${resultZero.inputCost}`);
assert(resultZero.outputCost === 0, `outputCost = ${resultZero.outputCost}`);
console.log();

// ============================================================
// TEST 5c: cost() with very large token counts
// ============================================================
console.log("--- TEST 5c: cost() with very large token counts ---");
const resultLarge = await calc1.cost("openai/gpt-4o", 10_000_000, 5_000_000);
assert(resultLarge !== null, "result is not null");
assert(resultLarge.totalCost > 0, `totalCost = ${resultLarge.totalCost}`);
assert(resultLarge.inputTokens === 10_000_000, `inputTokens = ${resultLarge.inputTokens}`);
assert(resultLarge.outputTokens === 5_000_000, `outputTokens = ${resultLarge.outputTokens}`);
console.log();

// ============================================================
// TEST 5e: cost() with non-integer tokens — returns null
// ============================================================
console.log("--- TEST 5e: cost() with non-integer tokens ---");
const errFloat = [];
const calcFloat = new AiCostCalc({ onError: (e) => errFloat.push(e.message) });
const resultFloat = await calcFloat.cost("openai/gpt-4o", 1.5, 500);
assert(resultFloat === null, `non-integer inputTokens returns null`);
const resultFloat2 = await calcFloat.cost("openai/gpt-4o", 1000, 2.7);
assert(resultFloat2 === null, `non-integer outputTokens returns null`);
console.log();

// ============================================================
// TEST 5f: cost() missing outputTokens — returns null
// ============================================================
console.log("--- TEST 5f: cost() missing outputTokens ---");
const errMissing = [];
const calcMissing = new AiCostCalc({ onError: (e) => errMissing.push(e.message) });
const resultMissing = await calcMissing.cost("openai/gpt-4o", 1000);
assert(resultMissing === null, `missing outputTokens returns null`);
assert(errMissing.length > 0, `onError called: ${errMissing[0]}`);
console.log();

// ============================================================
// TEST 5g: cost() mixed types — string input + number output — returns null
// ============================================================
console.log("--- TEST 5g: cost() mixed types (string input, number output) ---");
const errMixed = [];
const calcMixed = new AiCostCalc({ onError: (e) => errMixed.push(e.message) });
const resultMixed = await calcMixed.cost("openai/gpt-4o", "some input text", 500);
assert(resultMixed === null, `string input + number output returns null`);
assert(errMixed.length > 0, `onError called: ${errMixed[0]}`);
console.log();

// ============================================================
// TEST 5h: cost() with empty string input
// ============================================================
console.log("--- TEST 5h: cost() with empty string input ---");
const resultEmpty = await calc1.cost("openai/gpt-4o", "", "some output");
assert(resultEmpty !== null, "result is not null");
assert(resultEmpty.inputTokens === 0, `inputTokens = ${resultEmpty.inputTokens}`);
assert(resultEmpty.outputTokens > 0, `outputTokens = ${resultEmpty.outputTokens}`);
assert(resultEmpty.estimated === true, `estimated = true`);
console.log();

// ============================================================
// TEST 5i: cost() scales linearly with token count
// ============================================================
console.log("--- TEST 5i: cost() scales linearly ---");
const r1x = await calc1.cost("openai/gpt-4o", 1000, 500);
const r2x = await calc1.cost("openai/gpt-4o", 2000, 1000);
assert(r1x !== null && r2x !== null, "both results returned");
assert(Math.abs(r2x.totalCost - r1x.totalCost * 2) < 0.000001, `2x tokens = 2x cost (${r1x.totalCost} * 2 = ${r2x.totalCost})`);
assert(Math.abs(r2x.inputCost - r1x.inputCost * 2) < 0.000001, `inputCost scales linearly`);
assert(Math.abs(r2x.outputCost - r1x.outputCost * 2) < 0.000001, `outputCost scales linearly`);
console.log();

// ============================================================
// TEST 5d: Cached pricing — second cost() call uses cache
// ============================================================
console.log("--- TEST 5d: cached pricing (no re-fetch) ---");
const calc5d = new AiCostCalc({ debug: true });
const r5d_1 = await calc5d.cost("openai/gpt-4o", 1000, 500);
const r5d_2 = await calc5d.cost("anthropic/claude-sonnet-4", 1000, 500);
assert(r5d_1 !== null, "first cost() returned result");
assert(r5d_2 !== null, "second cost() returned result (from cache)");
assert(r5d_1.totalCost > 0, `first totalCost = ${r5d_1.totalCost}`);
assert(r5d_2.totalCost > 0, `second totalCost = ${r5d_2.totalCost}`);
console.log();

// ============================================================
// TEST 6: Usage tracking - basic (root README example)
// ============================================================
console.log("--- TEST 6: addUsage + track (basic, no revenue) ---");
const calc6 = new AiCostCalc({ apiKey: API_KEY, debug: true });

calc6.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 1000,
  outputTokens: 500,
});

calc6.track({ customerId: "sdk_test_ts_1", eventType: "chat" });
await calc6.flush();
console.log("  Flushed successfully");
console.log();

// ============================================================
// TEST 7: Usage tracking - with revenue (root README example)
// ============================================================
console.log("--- TEST 7: addUsage + track (with revenue) ---");
const calc7 = new AiCostCalc({ apiKey: API_KEY, debug: true });

calc7.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 1200,
  outputTokens: 340,
});

calc7.track({
  customerId: "sdk_test_ts_2",
  eventType: "summarize",
  revenueAmountInCents: 500,
});
await calc7.flush();
console.log("  Flushed successfully");
console.log();

// ============================================================
// TEST 8: Multiple usages then track (batch/agent scenario)
// ============================================================
console.log("--- TEST 8: Multiple addUsage + single track ---");
const calc8 = new AiCostCalc({ apiKey: API_KEY, debug: true });

calc8.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 800,
  outputTokens: 200,
});

calc8.addUsage({
  model: "anthropic/claude-sonnet-4",
  inputTokens: 1500,
  outputTokens: 600,
});

calc8.addUsage({
  model: "google/gemini-2.5-flash",
  inputTokens: 2000,
  outputTokens: 1000,
});

calc8.track({
  customerId: "sdk_test_ts_3",
  eventType: "agent_workflow",
  revenueAmountInCents: 1500,
});
await calc8.flush();
console.log("  Flushed successfully");
console.log();

// ============================================================
// TEST 9: Track without revenue (optional field)
// ============================================================
console.log("--- TEST 9: track without revenue ---");
const calc9 = new AiCostCalc({ apiKey: API_KEY, debug: true });

calc9.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 500,
  outputTokens: 100,
});

calc9.track({ customerId: "sdk_test_ts_4" });
await calc9.flush();
console.log("  Flushed successfully");
console.log();

// ============================================================
// TEST 10: Track with default event type
// ============================================================
console.log("--- TEST 10: track with no eventType (should default to ai_request) ---");
const calc10 = new AiCostCalc({ apiKey: API_KEY, debug: true, defaultEventType: "ai_request" });

calc10.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 300,
  outputTokens: 50,
});

calc10.track({ customerId: "sdk_test_ts_5" });
await calc10.flush();
console.log("  Flushed successfully");
console.log();

// ============================================================
// TEST 11: shutdown() flushes remaining events
// ============================================================
console.log("--- TEST 11: shutdown() flushes remaining ---");
const calc11 = new AiCostCalc({ apiKey: API_KEY, debug: true });

calc11.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 100,
  outputTokens: 50,
});

calc11.track({ customerId: "sdk_test_ts_6", eventType: "shutdown_test" });
await calc11.shutdown();
console.log("  Shutdown complete");
console.log();

// ============================================================
// TEST 12: No API key - cost() still works
// ============================================================
console.log("--- TEST 12: cost() works without API key ---");
const calc12 = new AiCostCalc();
const result12 = await calc12.cost("openai/gpt-4o", 1000, 500);
assert(result12 !== null, "cost() works without API key");
assert(result12.totalCost > 0, `totalCost = ${result12.totalCost}`);
console.log();

// ============================================================
// TEST 13: No API key - addUsage/track are no-ops
// ============================================================
console.log("--- TEST 13: addUsage/track without API key (should be no-op) ---");
const errors13 = [];
const calc13 = new AiCostCalc({
  debug: true,
  onError: (err) => errors13.push(err.message),
});

calc13.addUsage({ model: "openai/gpt-4o", inputTokens: 100, outputTokens: 50 });
calc13.track({ customerId: "should_not_send" });
assert(errors13.length > 0, `onError called with: ${errors13[0]}`);
console.log();

// ============================================================
// TEST 14: Documentation page example (TS)
// ============================================================
console.log("--- TEST 14: Documentation page example ---");
const md14 = new AiCostCalc({ apiKey: API_KEY, debug: true });

md14.addUsage({
  model: "openai/gpt-4o",
  inputTokens: 1200,
  outputTokens: 340,
});

md14.track({
  customerId: "8291",
  eventType: "summarize",
  revenueAmountInCents: 500,
});

await md14.shutdown();
console.log("  Documentation example complete");
console.log();

// ============================================================
// TEST 15: REST API equivalent via fetch (docs page cURL example)
// ============================================================
console.log("--- TEST 15: REST API fetch equivalent ---");
const restRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    events: [{
      customer_id: "12345",
      event_type: "summarize",
      vendor_responses: [{
        model: "openai/gpt-4o",
        input_tokens: 1200,
        output_tokens: 340,
      }],
    }],
  }),
});
const restBody = await restRes.json();
assert(restRes.status === 200, `REST status = ${restRes.status}`);
assert(restBody.results?.[0]?.status === "created" || restBody.results?.[0]?.status === "duplicate", `REST result = ${restBody.results?.[0]?.status}`);
console.log();

// ============================================================
// TEST 16: Idempotency — same uniqueRequestToken twice
// ============================================================
console.log("--- TEST 16: Idempotency (duplicate uniqueRequestToken) ---");
const idempotencyToken = `idem_ts_${Date.now()}`;

const calc16a = new AiCostCalc({ apiKey: API_KEY, debug: true });
calc16a.addUsage({ model: "openai/gpt-4o", inputTokens: 100, outputTokens: 50 });
calc16a.track({ customerId: "sdk_test_ts_idem", eventType: "idem_test", uniqueRequestToken: idempotencyToken });
await calc16a.flush();

// Send same token again
const idemRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": `Bearer ${API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "sdk_test_ts_idem",
      event_type: "idem_test",
      unique_request_token: idempotencyToken,
      vendor_responses: [{ model: "openai/gpt-4o", input_tokens: 100, output_tokens: 50 }],
    }],
  }),
});
const idemBody = await idemRes.json();
assert(idemRes.status === 200, `duplicate request accepted (status ${idemRes.status})`);
assert(idemBody.results?.[0]?.status === "duplicate", `second send returns duplicate (got ${idemBody.results?.[0]?.status})`);
console.log();

// ============================================================
// TEST 17: Batch flush — multiple track() calls before flush
// ============================================================
console.log("--- TEST 17: Batch flush (multiple tracks, one flush) ---");
const calc17 = new AiCostCalc({ apiKey: API_KEY, debug: true });

for (let i = 0; i < 5; i++) {
  calc17.addUsage({ model: "openai/gpt-4o", inputTokens: 100 + i * 10, outputTokens: 50 });
  calc17.track({ customerId: `sdk_test_ts_batch_${i}`, eventType: "batch_test" });
}

await calc17.flush();
console.log("  5 events flushed in single batch");
console.log();

// ============================================================
// TEST 18: Large batch — 60 events to trigger batch splitting (BATCH_SIZE=50)
// ============================================================
console.log("--- TEST 18: Large batch (60 events, splits into 2 batches) ---");
const calc18 = new AiCostCalc({ apiKey: API_KEY, debug: true });

for (let i = 0; i < 60; i++) {
  calc18.addUsage({ model: "openai/gpt-4o", inputTokens: 50, outputTokens: 20 });
  calc18.track({ customerId: `sdk_test_ts_large_${i}`, eventType: "large_batch" });
}

await calc18.flush();
console.log("  60 events flushed (should show 2 batches in debug output)");
console.log();

// ============================================================
// TEST 19: Custom uniqueRequestToken
// ============================================================
console.log("--- TEST 19: Custom uniqueRequestToken ---");
const customToken = `custom_ts_${Date.now()}`;
const calc19 = new AiCostCalc({ apiKey: API_KEY, debug: true });
calc19.addUsage({ model: "openai/gpt-4o", inputTokens: 200, outputTokens: 100 });
calc19.track({ customerId: "sdk_test_ts_custom_token", eventType: "token_test", uniqueRequestToken: customToken });
await calc19.flush();
console.log("  Custom token accepted");
console.log();

// ============================================================
// TEST 20: Custom occurredAt timestamp (recent — accepted)
// ============================================================
console.log("--- TEST 20a: Custom occurredAt (recent, accepted) ---");
const calc20a = new AiCostCalc({ apiKey: API_KEY, debug: true });
calc20a.addUsage({ model: "openai/gpt-4o", inputTokens: 150, outputTokens: 75 });
calc20a.track({
  customerId: "sdk_test_ts_timestamp",
  eventType: "timestamp_test",
  occurredAt: new Date(Date.now() - 3600_000).toISOString(),
});
await calc20a.flush();
console.log("  Recent timestamp accepted");
console.log();

// ============================================================
// TEST 20b: Custom occurredAt timestamp (>90 days ago — rejected)
// ============================================================
console.log("--- TEST 20b: Custom occurredAt (>90 days ago, rejected) ---");
const oldRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": `Bearer ${API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "sdk_test_ts_old_ts",
      event_type: "timestamp_test",
      occurred_at: "2025-01-15T10:30:00Z",
      vendor_responses: [{ model: "openai/gpt-4o", input_tokens: 150, output_tokens: 75 }],
    }],
  }),
});
assert(oldRes.status === 422, `>90 day timestamp returns 422 (got ${oldRes.status})`);
console.log();

// ============================================================
// TEST 21: Invalid API key — expect 401
// ============================================================
console.log("--- TEST 21: Invalid API key (expect 401) ---");
const badRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": "Bearer invalid_key_12345", "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "should_fail",
      event_type: "test",
      vendor_responses: [{ model: "openai/gpt-4o", input_tokens: 100, output_tokens: 50 }],
    }],
  }),
});
assert(badRes.status === 401, `invalid key returns 401 (got ${badRes.status})`);
console.log();

// ============================================================
// TEST 22: Invalid model slug in event — server rejects gracefully
// ============================================================
console.log("--- TEST 22: Invalid model slug in event ---");
const badModelRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": `Bearer ${API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "sdk_test_ts_badmodel",
      event_type: "test",
      vendor_responses: [{ model: "fake/nonexistent-model-xyz", input_tokens: 100, output_tokens: 50 }],
    }],
  }),
});
const badModelBody = await badModelRes.json();
assert(badModelRes.status === 422, `invalid model returns 422 (got ${badModelRes.status})`);
assert(badModelBody.results?.[0]?.status === "error", `result status is error (got ${badModelBody.results?.[0]?.status})`);
console.log();

// ============================================================
// TEST 23: Zero tokens in event — server rejects
// ============================================================
console.log("--- TEST 23: Zero tokens in event ---");
const zeroRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": `Bearer ${API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "sdk_test_ts_zero",
      event_type: "zero_token_test",
      vendor_responses: [{ model: "openai/gpt-4o", input_tokens: 0, output_tokens: 0 }],
    }],
  }),
});
assert(zeroRes.status === 422, `zero tokens returns 422 (got ${zeroRes.status})`);
console.log();

// ============================================================
// TEST 24: Very large token counts in event
// ============================================================
console.log("--- TEST 24: Very large token counts in event ---");
const calc24 = new AiCostCalc({ apiKey: API_KEY, debug: true });
calc24.addUsage({ model: "openai/gpt-4o", inputTokens: 50_000_000, outputTokens: 10_000_000 });
calc24.track({ customerId: "sdk_test_ts_huge", eventType: "large_token_test", revenueAmountInCents: 100000 });
await calc24.flush();
console.log("  Large token event accepted");
console.log();

// ============================================================
// TEST 25: Empty customer ID — server rejects
// ============================================================
console.log("--- TEST 25: Empty customer ID ---");
const emptyCustomerRes = await fetch("https://margindash.com/api/v1/events", {
  method: "POST",
  headers: { "Authorization": `Bearer ${API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    events: [{
      customer_id: "",
      event_type: "test",
      vendor_responses: [{ model: "openai/gpt-4o", input_tokens: 100, output_tokens: 50 }],
    }],
  }),
});
assert(emptyCustomerRes.status === 422, `empty customer_id returns 422 (got ${emptyCustomerRes.status})`);
console.log();

// ============================================================
// TEST 26: SDK handles server error without crashing
// ============================================================
console.log("--- TEST 26: SDK onError callback for invalid model ---");
const errors26 = [];
const calc26 = new AiCostCalc({
  apiKey: API_KEY,
  debug: true,
  onError: (err) => errors26.push(err.message),
});
calc26.addUsage({ model: "fake/will-fail", inputTokens: 100, outputTokens: 50 });
calc26.track({ customerId: "sdk_test_ts_error", eventType: "error_test" });
await calc26.flush();
assert(errors26.length > 0, `onError called (${errors26.length} error(s))`);
console.log();

// ============================================================
// Results
// ============================================================
console.log("=== TYPESCRIPT TESTS COMPLETE ===");
console.log(`  ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
