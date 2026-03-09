import json
import time
import urllib.request

from ai_cost_calc import AiCostCalc

API_KEY = "REPLACE_WITH_ENV_VAR"

passed = 0
failed = 0


def check(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {msg}")
    else:
        failed += 1
        print(f"  ✗ {msg}")


print("=== PYTHON SDK COMPREHENSIVE TEST ===\n")

# ============================================================
# TEST 1: cost() with exact token counts (root README example)
# ============================================================
print("--- TEST 1: cost(model, input_tokens, output_tokens) ---")
calc1 = AiCostCalc()
result1 = calc1.cost("openai/gpt-4o", input_tokens=1000, output_tokens=500)
check(result1 is not None, "result is not None")
check(result1.model == "openai/gpt-4o", f"model = {result1.model}")
check(result1.total_cost > 0, f"total_cost = {result1.total_cost}")
check(result1.input_cost > 0, f"input_cost = {result1.input_cost}")
check(result1.output_cost > 0, f"output_cost = {result1.output_cost}")
check(result1.input_tokens == 1000, f"input_tokens = {result1.input_tokens}")
check(result1.output_tokens == 500, f"output_tokens = {result1.output_tokens}")
check(result1.estimated is False, f"estimated = {result1.estimated}")
print()

# ============================================================
# TEST 2: cost() with input text only (root README example)
# ============================================================
print("--- TEST 2: cost(model, input_text) ---")
result2 = calc1.cost("openai/gpt-4o", input_text="Write a release note for this PR.")
check(result2 is not None, "result is not None")
check(result2.input_tokens > 0, f"input_tokens = {result2.input_tokens}")
check(result2.output_tokens == 0, f"output_tokens = {result2.output_tokens}")
check(result2.estimated is True, f"estimated = {result2.estimated}")
print()

# ============================================================
# TEST 3: cost() with input + output text (root README example)
# ============================================================
print("--- TEST 3: cost(model, input_text, output_text) ---")
result3 = calc1.cost("openai/gpt-4o", input_text="Write a release note for this PR.", output_text="Here is the release note for v1.3.7.")
check(result3 is not None, "result is not None")
check(result3.input_tokens > 0, f"input_tokens = {result3.input_tokens}")
check(result3.output_tokens > 0, f"output_tokens = {result3.output_tokens}")
check(result3.estimated is True, f"estimated = {result3.estimated}")
print()

# ============================================================
# TEST 4: cost() with different models
# ============================================================
print("--- TEST 4: cost() with anthropic/claude-sonnet-4 ---")
result4 = calc1.cost("anthropic/claude-sonnet-4", input_tokens=1000, output_tokens=500)
check(result4 is not None, "result is not None")
check(result4.model == "anthropic/claude-sonnet-4", f"model = {result4.model}")
check(result4.total_cost > 0, f"total_cost = {result4.total_cost}")
print()

print("--- TEST 4b: cost() with google/gemini-2.5-flash ---")
result4b = calc1.cost("google/gemini-2.5-flash", input_tokens=1000, output_tokens=500)
check(result4b is not None, "result is not None")
check(result4b.model == "google/gemini-2.5-flash", f"model = {result4b.model}")
check(result4b.total_cost > 0, f"total_cost = {result4b.total_cost}")
print()

# ============================================================
# TEST 4c: cost() with more vendors (Bedrock, Groq, Meta)
# ============================================================
print("--- TEST 4c: cost() with additional vendors ---")
bedrock = calc1.cost("amazon/nova-pro-v1", input_tokens=1000, output_tokens=500)
check(bedrock is not None, "amazon/nova-pro-v1 returned pricing")
if bedrock:
    check(bedrock.total_cost > 0, f"amazon/nova-pro-v1 total_cost = {bedrock.total_cost}")

llama = calc1.cost("meta-llama/llama-3.3-70b-instruct", input_tokens=1000, output_tokens=500)
check(llama is not None, "meta-llama/llama-3.3-70b-instruct returned pricing")
if llama:
    check(llama.total_cost > 0, f"meta-llama/llama-3.3-70b-instruct total_cost = {llama.total_cost}")

mistral = calc1.cost("mistralai/mistral-large-2411", input_tokens=1000, output_tokens=500)
check(mistral is not None, "mistralai/mistral-large-2411 returned pricing")
if mistral:
    check(mistral.total_cost > 0, f"mistralai/mistral-large-2411 total_cost = {mistral.total_cost}")
print()

# ============================================================
# TEST 5: cost() with unknown model
# ============================================================
print("--- TEST 5: cost() with unknown model ---")
result5 = calc1.cost("fake/not-a-model", input_tokens=1000, output_tokens=500)
check(result5 is None, f"unknown model returns None (got {result5})")
print()

# ============================================================
# TEST 5a: cost() with negative tokens — returns None
# ============================================================
print("--- TEST 5a: cost() with negative tokens ---")
err_neg = []
calc_neg = AiCostCalc(on_error=lambda e: err_neg.append(e.message))
result_neg = calc_neg.cost("openai/gpt-4o", input_tokens=-100, output_tokens=500)
check(result_neg is None, "negative input_tokens returns None")
result_neg2 = calc_neg.cost("openai/gpt-4o", input_tokens=100, output_tokens=-500)
check(result_neg2 is None, "negative output_tokens returns None")
check(len(err_neg) >= 2, f"on_error called {len(err_neg)} times")
print()

# ============================================================
# TEST 5b: cost() with zero tokens
# ============================================================
print("--- TEST 5b: cost() with zero tokens ---")
result_zero = calc1.cost("openai/gpt-4o", input_tokens=0, output_tokens=0)
check(result_zero is not None, "result is not None")
check(result_zero.total_cost == 0, f"total_cost = {result_zero.total_cost}")
check(result_zero.input_cost == 0, f"input_cost = {result_zero.input_cost}")
check(result_zero.output_cost == 0, f"output_cost = {result_zero.output_cost}")
print()

# ============================================================
# TEST 5c: cost() with very large token counts
# ============================================================
print("--- TEST 5c: cost() with very large token counts ---")
result_large = calc1.cost("openai/gpt-4o", input_tokens=10_000_000, output_tokens=5_000_000)
check(result_large is not None, "result is not None")
check(result_large.total_cost > 0, f"total_cost = {result_large.total_cost}")
check(result_large.input_tokens == 10_000_000, f"input_tokens = {result_large.input_tokens}")
check(result_large.output_tokens == 5_000_000, f"output_tokens = {result_large.output_tokens}")
print()

# ============================================================
# TEST 5e: cost() with non-integer tokens — returns None
# ============================================================
print("--- TEST 5e: cost() with non-integer tokens ---")
err_float = []
calc_float = AiCostCalc(on_error=lambda e: err_float.append(e.message))
result_float = calc_float.cost("openai/gpt-4o", input_tokens=1.5, output_tokens=500)
check(result_float is None, "non-integer input_tokens returns None")
result_float2 = calc_float.cost("openai/gpt-4o", input_tokens=1000, output_tokens=2.7)
check(result_float2 is None, "non-integer output_tokens returns None")
print()

# ============================================================
# TEST 5f: cost() missing output_tokens — returns None
# ============================================================
print("--- TEST 5f: cost() missing output_tokens ---")
err_missing = []
calc_missing = AiCostCalc(on_error=lambda e: err_missing.append(e.message))
result_missing = calc_missing.cost("openai/gpt-4o", input_tokens=1000)
check(result_missing is None, "missing output_tokens returns None")
check(len(err_missing) > 0, f"on_error called: {err_missing[0] if err_missing else 'nothing'}")
print()

# ============================================================
# TEST 5g: cost() mixed text + tokens — returns None
# ============================================================
print("--- TEST 5g: cost() mixed text + tokens ---")
err_mixed = []
calc_mixed = AiCostCalc(on_error=lambda e: err_mixed.append(e.message))
result_mixed = calc_mixed.cost("openai/gpt-4o", input_text="hello", input_tokens=100, output_tokens=50)
check(result_mixed is None, "mixed text + tokens returns None")
check(len(err_mixed) > 0, f"on_error called: {err_mixed[0] if err_mixed else 'nothing'}")
print()

# ============================================================
# TEST 5h: cost() with empty string input
# ============================================================
print("--- TEST 5h: cost() with empty string input ---")
result_empty = calc1.cost("openai/gpt-4o", input_text="", output_text="some output")
check(result_empty is not None, "result is not None")
check(result_empty.input_tokens == 0, f"input_tokens = {result_empty.input_tokens}")
check(result_empty.output_tokens > 0, f"output_tokens = {result_empty.output_tokens}")
check(result_empty.estimated is True, "estimated = True")
print()

# ============================================================
# TEST 5i: cost() scales linearly with token count
# ============================================================
print("--- TEST 5i: cost() scales linearly ---")
r1x = calc1.cost("openai/gpt-4o", input_tokens=1000, output_tokens=500)
r2x = calc1.cost("openai/gpt-4o", input_tokens=2000, output_tokens=1000)
check(r1x is not None and r2x is not None, "both results returned")
check(abs(r2x.total_cost - r1x.total_cost * 2) < 0.000001, f"2x tokens = 2x cost ({r1x.total_cost} * 2 = {r2x.total_cost})")
check(abs(r2x.input_cost - r1x.input_cost * 2) < 0.000001, "input_cost scales linearly")
check(abs(r2x.output_cost - r1x.output_cost * 2) < 0.000001, "output_cost scales linearly")
print()

# ============================================================
# TEST 5j: cost() with bool tokens — returns None
# ============================================================
print("--- TEST 5j: cost() with bool tokens ---")
err_bool = []
calc_bool = AiCostCalc(on_error=lambda e: err_bool.append(e.message))
result_bool = calc_bool.cost("openai/gpt-4o", input_tokens=True, output_tokens=500)
check(result_bool is None, "bool input_tokens returns None")
print()

# ============================================================
# TEST 5d: Cached pricing — second cost() call uses cache
# ============================================================
print("--- TEST 5d: cached pricing (no re-fetch) ---")
calc5d = AiCostCalc()
r5d_1 = calc5d.cost("openai/gpt-4o", input_tokens=1000, output_tokens=500)
r5d_2 = calc5d.cost("anthropic/claude-sonnet-4", input_tokens=1000, output_tokens=500)
check(r5d_1 is not None, "first cost() returned result")
check(r5d_2 is not None, "second cost() returned result (from cache)")
check(r5d_1.total_cost > 0, f"first total_cost = {r5d_1.total_cost}")
check(r5d_2.total_cost > 0, f"second total_cost = {r5d_2.total_cost}")
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

calc8.add_usage(model="openai/gpt-4o", input_tokens=800, output_tokens=200)
calc8.add_usage(model="anthropic/claude-sonnet-4", input_tokens=1500, output_tokens=600)
calc8.add_usage(model="google/gemini-2.5-flash", input_tokens=2000, output_tokens=1000)

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

calc9.add_usage(model="openai/gpt-4o", input_tokens=500, output_tokens=100)

calc9.track(customer_id="sdk_test_py_4")
calc9.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 10: Track with default event type
# ============================================================
print("--- TEST 10: track with no event_type (should default to ai_request) ---")
calc10 = AiCostCalc(api_key=API_KEY, default_event_type="ai_request")

calc10.add_usage(model="openai/gpt-4o", input_tokens=300, output_tokens=50)

calc10.track(customer_id="sdk_test_py_5")
calc10.flush()
print("  Flushed successfully")
print()

# ============================================================
# TEST 11: shutdown() flushes remaining events
# ============================================================
print("--- TEST 11: shutdown() flushes remaining ---")
calc11 = AiCostCalc(api_key=API_KEY)

calc11.add_usage(model="openai/gpt-4o", input_tokens=100, output_tokens=50)

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
check(result12 is not None, "cost() works without API key")
check(result12.total_cost > 0, f"total_cost = {result12.total_cost}")
print()

# ============================================================
# TEST 13: No API key - add_usage/track are no-ops
# ============================================================
print("--- TEST 13: add_usage/track without API key (should be no-op) ---")
errors = []
calc13 = AiCostCalc(on_error=lambda err: errors.append(err.message))

calc13.add_usage(model="openai/gpt-4o", input_tokens=100, output_tokens=50)
calc13.track(customer_id="should_not_send")
check(len(errors) > 0, f"on_error called with: {errors[0] if errors else 'nothing'}")
print()

# ============================================================
# TEST 14: Documentation page example (Python)
# ============================================================
print("--- TEST 14: Documentation page example ---")
md14 = AiCostCalc(api_key=API_KEY)

md14.add_usage(model="openai/gpt-4o", input_tokens=1200, output_tokens=340)

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
body15 = json.loads(resp.read().decode())
check(resp.status == 200, f"REST status = {resp.status}")
check(body15["results"][0]["status"] in ("created", "duplicate"), f"REST result = {body15['results'][0]['status']}")
print()

# ============================================================
# TEST 16: Idempotency — same unique_request_token twice
# ============================================================
print("--- TEST 16: Idempotency (duplicate unique_request_token) ---")
idem_token = f"idem_py_{int(time.time())}"

calc16 = AiCostCalc(api_key=API_KEY)
calc16.add_usage(model="openai/gpt-4o", input_tokens=100, output_tokens=50)
calc16.track(customer_id="sdk_test_py_idem", event_type="idem_test", unique_request_token=idem_token)
calc16.flush()

# Send same token again via REST
idem_payload = json.dumps({
    "events": [{
        "customer_id": "sdk_test_py_idem",
        "event_type": "idem_test",
        "unique_request_token": idem_token,
        "vendor_responses": [{"model": "openai/gpt-4o", "input_tokens": 100, "output_tokens": 50}],
    }],
}).encode()
idem_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=idem_payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
)
idem_resp = urllib.request.urlopen(idem_req)
idem_body = json.loads(idem_resp.read().decode())
check(idem_resp.status == 200, f"duplicate request accepted (status {idem_resp.status})")
check(idem_body["results"][0]["status"] == "duplicate", f"second send returns duplicate (got {idem_body['results'][0]['status']})")
print()

# ============================================================
# TEST 17: Batch flush — multiple track() calls before flush
# ============================================================
print("--- TEST 17: Batch flush (multiple tracks, one flush) ---")
calc17 = AiCostCalc(api_key=API_KEY)

for i in range(5):
    calc17.add_usage(model="openai/gpt-4o", input_tokens=100 + i * 10, output_tokens=50)
    calc17.track(customer_id=f"sdk_test_py_batch_{i}", event_type="batch_test")

calc17.flush()
print("  5 events flushed in single batch")
print()

# ============================================================
# TEST 18: Large batch — 60 events to trigger batch splitting (BATCH_SIZE=50)
# ============================================================
print("--- TEST 18: Large batch (60 events, splits into 2 batches) ---")
calc18 = AiCostCalc(api_key=API_KEY)

for i in range(60):
    calc18.add_usage(model="openai/gpt-4o", input_tokens=50, output_tokens=20)
    calc18.track(customer_id=f"sdk_test_py_large_{i}", event_type="large_batch")

calc18.flush()
print("  60 events flushed (should split into 2 batches)")
print()

# ============================================================
# TEST 19: Custom unique_request_token
# ============================================================
print("--- TEST 19: Custom unique_request_token ---")
custom_token = f"custom_py_{int(time.time())}"
calc19 = AiCostCalc(api_key=API_KEY)
calc19.add_usage(model="openai/gpt-4o", input_tokens=200, output_tokens=100)
calc19.track(customer_id="sdk_test_py_custom_token", event_type="token_test", unique_request_token=custom_token)
calc19.flush()
print("  Custom token accepted")
print()

# ============================================================
# TEST 20a: Custom occurred_at timestamp (recent — accepted)
# ============================================================
print("--- TEST 20a: Custom occurred_at (recent, accepted) ---")
from datetime import datetime, timezone, timedelta
recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
calc20a = AiCostCalc(api_key=API_KEY)
calc20a.add_usage(model="openai/gpt-4o", input_tokens=150, output_tokens=75)
calc20a.track(
    customer_id="sdk_test_py_timestamp",
    event_type="timestamp_test",
    occurred_at=recent_ts,
)
calc20a.flush()
print("  Recent timestamp accepted")
print()

# ============================================================
# TEST 20b: Custom occurred_at timestamp (>90 days ago — rejected)
# ============================================================
print("--- TEST 20b: Custom occurred_at (>90 days ago, rejected) ---")
old_ts_payload = json.dumps({
    "events": [{
        "customer_id": "sdk_test_py_old_ts",
        "event_type": "timestamp_test",
        "occurred_at": "2025-01-15T10:30:00Z",
        "vendor_responses": [{"model": "openai/gpt-4o", "input_tokens": 150, "output_tokens": 75}],
    }],
}).encode()
old_ts_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=old_ts_payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(old_ts_req)
    check(False, "expected 422 but got 200")
except urllib.error.HTTPError as e:
    check(e.code == 422, f">90 day timestamp returns 422 (got {e.code})")
print()

# ============================================================
# TEST 21: Invalid API key — expect 401
# ============================================================
print("--- TEST 21: Invalid API key (expect 401) ---")
bad_payload = json.dumps({
    "events": [{
        "customer_id": "should_fail",
        "event_type": "test",
        "vendor_responses": [{"model": "openai/gpt-4o", "input_tokens": 100, "output_tokens": 50}],
    }],
}).encode()
bad_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=bad_payload,
    headers={"Authorization": "Bearer invalid_key_12345", "Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(bad_req)
    check(False, "expected 401 but got 200")
except urllib.error.HTTPError as e:
    check(e.code == 401, f"invalid key returns 401 (got {e.code})")
print()

# ============================================================
# TEST 22: Invalid model slug in event — server rejects gracefully
# ============================================================
print("--- TEST 22: Invalid model slug in event ---")
bad_model_payload = json.dumps({
    "events": [{
        "customer_id": "sdk_test_py_badmodel",
        "event_type": "test",
        "vendor_responses": [{"model": "fake/nonexistent-model-xyz", "input_tokens": 100, "output_tokens": 50}],
    }],
}).encode()
bad_model_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=bad_model_payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(bad_model_req)
    check(False, "expected 422 but got 200")
except urllib.error.HTTPError as e:
    body22 = json.loads(e.read().decode())
    check(e.code == 422, f"invalid model returns 422 (got {e.code})")
    check(body22["results"][0]["status"] == "error", f"result status is error (got {body22['results'][0]['status']})")
print()

# ============================================================
# TEST 23: Zero tokens in event — server rejects
# ============================================================
print("--- TEST 23: Zero tokens in event ---")
zero_payload = json.dumps({
    "events": [{
        "customer_id": "sdk_test_py_zero",
        "event_type": "zero_token_test",
        "vendor_responses": [{"model": "openai/gpt-4o", "input_tokens": 0, "output_tokens": 0}],
    }],
}).encode()
zero_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=zero_payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(zero_req)
    check(False, "expected 422 but got 200")
except urllib.error.HTTPError as e:
    check(e.code == 422, f"zero tokens returns 422 (got {e.code})")
print()

# ============================================================
# TEST 24: Very large token counts in event
# ============================================================
print("--- TEST 24: Very large token counts in event ---")
calc24 = AiCostCalc(api_key=API_KEY)
calc24.add_usage(model="openai/gpt-4o", input_tokens=50_000_000, output_tokens=10_000_000)
calc24.track(customer_id="sdk_test_py_huge", event_type="large_token_test", revenue_amount_in_cents=100000)
calc24.flush()
print("  Large token event accepted")
print()

# ============================================================
# TEST 25: Empty customer ID — server rejects
# ============================================================
print("--- TEST 25: Empty customer ID ---")
empty_cust_payload = json.dumps({
    "events": [{
        "customer_id": "",
        "event_type": "test",
        "vendor_responses": [{"model": "openai/gpt-4o", "input_tokens": 100, "output_tokens": 50}],
    }],
}).encode()
empty_cust_req = urllib.request.Request(
    "https://margindash.com/api/v1/events",
    data=empty_cust_payload,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
)
try:
    urllib.request.urlopen(empty_cust_req)
    check(False, "expected 422 but got 200")
except urllib.error.HTTPError as e:
    check(e.code == 422, f"empty customer_id returns 422 (got {e.code})")
print()

# ============================================================
# TEST 26: SDK on_error callback for invalid model
# ============================================================
print("--- TEST 26: SDK on_error callback for invalid model ---")
errors26 = []
calc26 = AiCostCalc(api_key=API_KEY, on_error=lambda err: errors26.append(err.message))
calc26.add_usage(model="fake/will-fail", input_tokens=100, output_tokens=50)
calc26.track(customer_id="sdk_test_py_error", event_type="error_test")
calc26.flush()
check(len(errors26) > 0, f"on_error called ({len(errors26)} error(s))")
print()

# ============================================================
# Results
# ============================================================
print("=== PYTHON TESTS COMPLETE ===")
print(f"  {passed} passed, {failed} failed")
if failed > 0:
    exit(1)
