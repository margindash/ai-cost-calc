import { AiCostCalc } from "ai-cost-calc";

const API_KEY = "REPLACE_WITH_ENV_VAR";

console.log("=== TYPESCRIPT SDK COMPREHENSIVE TEST ===\n");

// ============================================================
// TEST 1: cost() with exact token counts (root README example)
// ============================================================
console.log("--- TEST 1: cost(model, inputTokens, outputTokens) ---");
const calc1 = new AiCostCalc({ debug: true });
const result1 = await calc1.cost("openai/gpt-4o", 1000, 500);
console.log("Result:", JSON.stringify(result1, null, 2));
console.log();

// ============================================================
// TEST 2: cost() with input text only (root README example)
// ============================================================
console.log("--- TEST 2: cost(model, inputText) ---");
const result2 = await calc1.cost("openai/gpt-4o", "Write a release note for this PR.");
console.log("Result:", JSON.stringify(result2, null, 2));
console.log();

// ============================================================
// TEST 3: cost() with input + output text (root README example)
// ============================================================
console.log("--- TEST 3: cost(model, inputText, outputText) ---");
const result3 = await calc1.cost("openai/gpt-4o", "Write a release note for this PR.", "Here is the release note for v1.3.7.");
console.log("Result:", JSON.stringify(result3, null, 2));
console.log();

// ============================================================
// TEST 4: cost() with different models
// ============================================================
console.log("--- TEST 4: cost() with anthropic/claude-sonnet-4 ---");
const result4 = await calc1.cost("anthropic/claude-sonnet-4", 1000, 500);
console.log("Result:", JSON.stringify(result4, null, 2));
console.log();

console.log("--- TEST 4b: cost() with google/gemini-2.5-flash ---");
const result4b = await calc1.cost("google/gemini-2.5-flash", 1000, 500);
console.log("Result:", JSON.stringify(result4b, null, 2));
console.log();

// ============================================================
// TEST 5: cost() with unknown model
// ============================================================
console.log("--- TEST 5: cost() with unknown model ---");
const result5 = await calc1.cost("fake/not-a-model", 1000, 500);
console.log("Result:", result5);
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
console.log("Flushed successfully");
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
console.log("Flushed successfully");
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
console.log("Flushed successfully");
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
console.log("Flushed successfully");
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
console.log("Flushed successfully");
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
console.log("Shutdown complete");
console.log();

// ============================================================
// TEST 12: No API key - cost() still works
// ============================================================
console.log("--- TEST 12: cost() works without API key ---");
const calc12 = new AiCostCalc();
const result12 = await calc12.cost("openai/gpt-4o", 1000, 500);
console.log("Result:", JSON.stringify(result12, null, 2));
console.log();

// ============================================================
// TEST 13: No API key - addUsage/track are no-ops
// ============================================================
console.log("--- TEST 13: addUsage/track without API key (should be no-op) ---");
const calc13 = new AiCostCalc({
  debug: true,
  onError: (err) => console.log("  onError:", err.message),
});

calc13.addUsage({ model: "openai/gpt-4o", inputTokens: 100, outputTokens: 50 });
calc13.track({ customerId: "should_not_send" });
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
console.log("Documentation example complete");
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
console.log("REST API status:", restRes.status);
const restBody = await restRes.json();
console.log("REST API response:", JSON.stringify(restBody, null, 2));
console.log();

console.log("=== ALL TYPESCRIPT TESTS COMPLETE ===");
