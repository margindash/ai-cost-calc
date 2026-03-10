# Changelog

All notable changes to the TypeScript SDK are documented in this file.

## 1.3.12 - 2026-03-10

- Added SDK-side budget enforcement via `guardedCall(context, call)`.
- Added `budgetFailClosed` option to block requests when budget state refresh fails.
- Added TTL/version-based blocklist caching (`/budgets/blocklist`) with deduplicated refreshes.
- Added fast refresh when `/events` returns a newer `budget_state_version`.
- Added tests covering budget blocking, fail-open/fail-closed, cache TTL, and version-triggered refresh.
- Updated docs with budget guard usage and behavior.
