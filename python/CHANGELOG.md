# Changelog

All notable changes to the Python SDK are documented in this file.

## 1.3.12 - 2026-03-10

- Added SDK-side budget enforcement via `guarded_call(customer_id, call, event_type=None)`.
- Added `async_guarded_call(...)` for asyncio apps (non-blocking budget refresh path).
- Added `budget_fail_closed` option to block requests when budget state refresh fails.
- Added TTL/version-based blocklist caching (`/budgets/blocklist`).
- Added fast refresh when `/events` returns a newer `budget_state_version`.
- Added tests covering budget blocking, async usage, fail-open/fail-closed, cache TTL, and version-triggered refresh.
- Updated docs with sync/async guard semantics and FastAPI-friendly usage.
