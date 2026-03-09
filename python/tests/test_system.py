import json
import sys
import urllib.request

from ai_cost_calc import AiCostCalc

API_KEY = "REPLACE_WITH_ENV_VAR"

print("=== PYTHON SDK COMPREHENSIVE TEST ===\n")

# ============================================================
# TEST 1: cost() with exact token counts (root README example)
# ============================================================
print("--- TEST 1: cost(model, input_tokens, output_tokens) ---")
calc1 = AiCostCalc()
result1 = calc1.cost("openai/gpt-4o", input_tokens=1000, output_tokens=500)
print(f"  model: {result1.model}")
print(f"  input_cost: {result1.input_cost}")
print(f"  output_cost: {result1.output_cost}")
print(f"  total_cost: {result1.total_cost}")
print(f"  input_tokens: {result1.input_tokens}")
print(f"  output_tokens: {result1.output_tokens}")
print(f"  estimated: {result1.estimated}")
print()

# ============================================================
# TEST 2: cost() with input text only (root README example)
# ============================================================
print("--- TEST 2: cost(model, input_text) ---")
result2 = calc1.cost("openai/gpt-4o", input_text="Write a release note for this PR.")
print(f"  model: {result2.model}")
print(f"  input_cost: {result2.input_cost}")
print(f"  output_cost: {result2.output_cost}")
print(f"  total_cost: {result2.total_cost}")
print(f"  input_tokens: {result2.input_tokens}")
print(f"  output_tokens: {result2.output_tokens}")
print(f"  estimated: {result2.estimated}")
print()

# ============================================================
# TEST 3: cost() with input + output text (root README example)
# ============================================================
print("--- TEST 3: cost(model, input_text, output_text) ---")
result3 = calc1.cost("openai/gpt-4o", input_text="Write a release note for this PR.", output_text="Here is the release note for v1.3.7.")
print(f"  model: {result3.model}")
print(f"  input_cost: {result3.input_cost}")
print(f"  output_cost: {result3.output_cost}")
print(f"  total_cost: {result3.total_cost}")
print(f"  input_tokens: {result3.input_tokens}")
print(f"  output_tokens: {result3.output_tokens}")
print(f"  estimated: {result3.estimated}")
print()

# ============================================================
# TEST 4: cost() with different models
# ============================================================
print("--- TEST 4: cost() with anthropic/claude-sonnet-4 ---")
result4 = calc1.cost("anthropic/claude-sonnet-4", input_tokens=1000, output_tokens=500)
print(f"  model: {result4.model}")
print(f"  input_cost: {result4.input_cost}")
print(f"  output_cost: {result4.output_cost}")
print(f"  total_cost: {result4.total_cost}")
print()

print("--- TEST 4b: cost() with google/gemini-2.5-flash ---")
result4b = calc1.cost("google/gemini-2.5-flash", input_tokens=1000, output_tokens=500)
if result4b:
    print(f"  model: {result4b.model}")
    print(f"  input_cost: {result4b.input_cost}")
    print(f"  output_cost: {result4b.output_cost}")
    print(f"  total_cost: {result4b.total_cost}")
else:
    print(f"  Result: {result4b}")
print()

# ============================================================
# TEST 5: cost() with unknown model
# ============================================================
print("--- TEST 5: cost() with unknown model ---")
result5 = calc1.cost("fake/not-a-model", input_tokens=1000, output_tokens=500)
print(f"  Result: {result5}")
print()

# ============================================================
# TEST 6: Usage tracking - basic (root README example)
# ============================================================
print("--- TEST 6: add_usage + track (basic, no revenue) ---")
calc6 = AiCostCalc(api_key=API_KEY)

calc6.add_usage(
    model="openai/gpt-4o",
    input_tokens=1000,
    output_tokens=500,
)

calc6.track(customer_id="sdk_test_py_1", event_type="chat")
calc6.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 7: Usage tracking - with revenue (root README example)
# ============================================================
print("--- TEST 7: add_usage + track (with revenue) ---")
calc7 = AiCostCalc(api_key=API_KEY)

calc7.add_usage(
    model="openai/gpt-4o",
    input_tokens=1200,
    output_tokens=340,
)

calc7.track(
    customer_id="sdk_test_py_2",
    event_type="summarize",
    revenue_amount_in_cents=500,
)
calc7.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 8: Multiple usages then track (batch/agent scenario)
# ============================================================
print("--- TEST 8: Multiple add_usage + single track ---")
calc8 = AiCostCalc(api_key=API_KEY)

calc8.add_usage(
    model="openai/gpt-4o",
    input_tokens=800,
    output_tokens=200,
)

calc8.add_usage(
    model="anthropic/claude-sonnet-4",
    input_tokens=1500,
    output_tokens=600,
)

calc8.add_usage(
    model="google/gemini-2.5-flash",
    input_tokens=2000,
    output_tokens=1000,
)

calc8.track(
    customer_id="sdk_test_py_3",
    event_type="agent_workflow",
    revenue_amount_in_cents=1500,
)
calc8.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 9: Track without revenue (optional field)
# ============================================================
print("--- TEST 9: track without revenue ---")
calc9 = AiCostCalc(api_key=API_KEY)

calc9.add_usage(
    model="openai/gpt-4o",
    input_tokens=500,
    output_tokens=100,
)

calc9.track(customer_id="sdk_test_py_4")
calc9.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 10: Track with default event type
# ============================================================
print("--- TEST 10: track with no event_type (should default to ai_request) ---")
calc10 = AiCostCalc(api_key=API_KEY, default_event_type="ai_request")

calc10.add_usage(
    model="openai/gpt-4o",
    input_tokens=300,
    output_tokens=50,
)

calc10.track(customer_id="sdk_test_py_5")
calc10.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 11: shutdown() flushes remaining events
# ============================================================
print("--- TEST 11: shutdown() flushes remaining ---")
calc11 = AiCostCalc(api_key=API_KEY)

calc11.add_usage(
    model="openai/gpt-4o",
    input_tokens=100,
    output_tokens=50,
)

calc11.track(customer_id="sdk_test_py_6", event_type="shutdown_test")
calc11.shutdown()
print("  Shutdown complete")
print()

# ============================================================
# TEST 12: No API key - cost() still works
# ============================================================
print("--- TEST 12: cost() works without API key ---")
calc12 = AiCostCalc()
result12 = calc12.cost("openai/gpt-4o", input_tokens=1000, output_tokens=500)
print(f"  total_cost: {result12.total_cost}")
print()

# ============================================================
# TEST 13: No API key - add_usage/track are no-ops
# ============================================================
print("--- TEST 13: add_usage/track without API key (should be no-op) ---")
errors = []
calc13 = AiCostCalc(on_error=lambda err: errors.append(err.message))

calc13.add_usage(model="openai/gpt-4o", input_tokens=100, output_tokens=50)
calc13.track(customer_id="should_not_send")
print(f"  Errors reported: {errors}")
print()

# ============================================================
# TEST 14: Documentation page example (Python)
# ============================================================
print("--- TEST 14: Documentation page example ---")
md14 = AiCostCalc(api_key=API_KEY)

md14.add_usage(
    model="openai/gpt-4o",
    input_tokens=1200,
    output_tokens=340,
)

md14.track(
    customer_id="8291",
    event_type="summarize",
    revenue_amount_in_cents=500,
)

md14.shutdown()
print("  Documentation example complete")
print()

# ============================================================
# TEST 15: REST API equivalent via urllib (docs page cURL example)
# ============================================================
print("--- TEST 15: REST API direct call ---")
payload = json.dumps({
    "events": [{
        "customer_id": "12345",
        "event_type": "summarize",
        "vendor_responses": [{
            "model": "openai/gpt-4o",
            "input_tokens": 1200,
            "output_tokens": 340,
        }],
    }],
}).encode()

req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=payload,
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
)
resp = urllib.request.urlopen(req)
print(f"  Status: {resp.status}")
print(f"  Response: {resp.read().decode()}")
print()

print("=== ALL PYTHON TESTS COMPLETE ===")
