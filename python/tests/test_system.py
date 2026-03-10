import json
import time
import urllib.request
import asyncio
from unittest.mock import MagicMock

from ai_cost_calc import AiCostCalc

import os
import sys

API_KEY = os.environ.get("MARGINDASH_API_KEY")
if not API_KEY:
    print("Set MARGINDASH_API_KEY env var to run system tests")
    sys.exit(1)

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


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = status_code < 400
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


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
# TEST 27: guarded_call without API key allows call
# ============================================================
print("--- TEST 27: guarded_call without API key ---")
calc27 = AiCostCalc()
result27 = calc27.guarded_call(customer_id="sdk_test_py_guard_no_key", call=lambda: "ok")
check(result27 == "ok", "guarded_call allows call without api_key")
print()

# ============================================================
# TEST 28: guarded_call validates callback and customer_id
# ============================================================
print("--- TEST 28: guarded_call validates inputs ---")
calc28 = AiCostCalc()
guard28a = False
try:
    calc28.guarded_call(customer_id="  ", call=lambda: "ok")
except ValueError as e:
    guard28a = "customer_id is required" in str(e)
check(guard28a, "guarded_call requires customer_id")

guard28b = False
try:
    calc28.guarded_call(customer_id="cust_123", call="not_callable")  # type: ignore[arg-type]
except ValueError as e:
    guard28b = "call must be a callable" in str(e)
check(guard28b, "guarded_call requires callable")
print()

# ============================================================
# TEST 29: guarded_call blocks organization and callback not run
# ============================================================
print("--- TEST 29: guarded_call blocks organization budget ---")
calc29 = AiCostCalc(api_key=API_KEY)
calc29._session.get = MagicMock(return_value=_mock_response({
    "version": 201,
    "ttl_seconds": 30,
    "changed": True,
    "recompute_in_progress": False,
    "blocked": {
        "organization": True,
        "event_types": [],
        "customer_ids": [],
    },
}))
called29 = False


def _blocked_provider_29():
    global called29
    called29 = True
    return "should_not_run"


blocked29 = False
try:
    calc29.guarded_call(customer_id="sdk_test_py_guard_org", call=_blocked_provider_29)
except RuntimeError as e:
    blocked29 = "organization-wide budget limit" in str(e)
check(blocked29, "guarded_call blocks on organization limit")
check(called29 is False, "blocked guarded_call does not execute callback")
calc29.shutdown()
print()

# ============================================================
# TEST 30: guarded_call blocks event type and customer
# ============================================================
print("--- TEST 30: guarded_call blocks event type/customer ---")
calc30 = AiCostCalc(api_key=API_KEY)
calc30._session.get = MagicMock(return_value=_mock_response({
    "version": 202,
    "ttl_seconds": 30,
    "changed": True,
    "recompute_in_progress": False,
    "blocked": {
        "organization": False,
        "event_types": ["chat"],
        "customer_ids": ["cust_blocked"],
    },
}))
blocked30a = False
blocked30b = False
try:
    calc30.guarded_call(customer_id="cust_ok", event_type=" chat ", call=lambda: "nope")
except RuntimeError as e:
    blocked30a = "event type budget limit (chat)" in str(e)
try:
    calc30.guarded_call(customer_id=" cust_blocked ", call=lambda: "nope")
except RuntimeError as e:
    blocked30b = "customer budget limit (cust_blocked)" in str(e)
check(blocked30a, "guarded_call blocks matching event_type")
check(blocked30b, "guarded_call blocks matching customer_id")
calc30.shutdown()
print()

# ============================================================
# TEST 31: guarded_call keeps state on unchanged blocklist
# ============================================================
print("--- TEST 31: guarded_call keeps prior state on unchanged response ---")
calc31 = AiCostCalc(api_key=API_KEY)
calc31._session.get = MagicMock(side_effect=[
    _mock_response({
        "version": 203,
        "ttl_seconds": 30,
        "changed": True,
        "recompute_in_progress": False,
        "blocked": {
            "organization": False,
            "event_types": [],
            "customer_ids": ["cust_cached"],
        },
    }),
    _mock_response({
        "version": 203,
        "ttl_seconds": 30,
        "changed": False,
        "recompute_in_progress": False,
    }),
])
blocked31a = False
blocked31b = False
try:
    calc31.guarded_call(customer_id="cust_cached", call=lambda: "nope")
except RuntimeError as e:
    blocked31a = "customer budget limit" in str(e)
calc31._budget_next_poll_at = 0.0
try:
    calc31.guarded_call(customer_id="cust_cached", call=lambda: "still_nope")
except RuntimeError as e:
    blocked31b = "customer budget limit" in str(e)
check(blocked31a, "first call blocked from changed blocklist payload")
check(blocked31b, "second call remains blocked when blocklist says unchanged")
check(calc31._session.get.call_count == 2, f"blocklist fetched twice (got {calc31._session.get.call_count})")
calc31.shutdown()
print()

# ============================================================
# TEST 32: guarded_call fail-open/fail-closed behavior
# ============================================================
print("--- TEST 32: guarded_call fail-open and fail-closed ---")
calc32a = AiCostCalc(api_key=API_KEY)
calc32a._session.get = MagicMock(side_effect=ConnectionError("network down"))
result32a = calc32a.guarded_call(customer_id="cust_fail_open", call=lambda: "allowed")
check(result32a == "allowed", "guarded_call defaults to fail-open")
calc32a.shutdown()

calc32b = AiCostCalc(api_key=API_KEY, budget_fail_closed=True)
calc32b._session.get = MagicMock(side_effect=ConnectionError("network down"))
blocked32b = False
try:
    calc32b.guarded_call(customer_id="cust_fail_closed", call=lambda: "blocked")
except RuntimeError as e:
    blocked32b = "fail-closed mode" in str(e)
check(blocked32b, "guarded_call blocks in fail-closed mode")
calc32b.shutdown()
print()

# ============================================================
# TEST 33: async_guarded_call supports sync and async callbacks
# ============================================================
print("--- TEST 33: async_guarded_call supports sync/async callbacks ---")
calc33 = AiCostCalc(api_key=API_KEY)
calc33._session.get = MagicMock(return_value=_mock_response({
    "version": 204,
    "ttl_seconds": 30,
    "changed": True,
    "recompute_in_progress": False,
    "blocked": {
        "organization": False,
        "event_types": [],
        "customer_ids": [],
    },
}))


async def _provider_async_33():
    return "async_ok"


result33a = asyncio.run(calc33.async_guarded_call(
    customer_id="sdk_test_py_guard_async",
    event_type="chat",
    call=_provider_async_33,
))
result33b = asyncio.run(calc33.async_guarded_call(
    customer_id="sdk_test_py_guard_sync",
    call=lambda: "sync_ok",
))
check(result33a == "async_ok", "async_guarded_call executes async callback")
check(result33b == "sync_ok", "async_guarded_call executes sync callback")
calc33.shutdown()
print()

# ============================================================
# TEST 34: async_guarded_call blocks/fail-closed on refresh failure
# ============================================================
print("--- TEST 34: async_guarded_call block and fail-closed ---")
calc34a = AiCostCalc(api_key=API_KEY)
calc34a._session.get = MagicMock(return_value=_mock_response({
    "version": 205,
    "ttl_seconds": 30,
    "changed": True,
    "recompute_in_progress": False,
    "blocked": {
        "organization": False,
        "event_types": [],
        "customer_ids": ["cust_async_blocked"],
    },
}))
blocked34a = False
try:
    asyncio.run(calc34a.async_guarded_call(customer_id="cust_async_blocked", call=lambda: "nope"))
except RuntimeError as e:
    blocked34a = "customer budget limit" in str(e)
check(blocked34a, "async_guarded_call blocks matching customer_id")
calc34a.shutdown()

calc34b = AiCostCalc(api_key=API_KEY, budget_fail_closed=True)
calc34b._session.get = MagicMock(side_effect=ConnectionError("network down"))
blocked34b = False
try:
    asyncio.run(calc34b.async_guarded_call(customer_id="cust_async_fail_closed", call=lambda: "nope"))
except RuntimeError as e:
    blocked34b = "fail-closed mode" in str(e)
check(blocked34b, "async_guarded_call blocks in fail-closed mode on refresh error")
calc34b.shutdown()
print()

# ============================================================
# Results
# ============================================================
print("=== PYTHON TESTS COMPLETE ===")
print(f"  {passed} passed, {failed} failed")
if failed > 0:
    exit(1)
