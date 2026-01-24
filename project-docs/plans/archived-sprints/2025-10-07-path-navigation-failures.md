# Path Navigation Failure Investigation Report

**Date**: 2025-10-07  
**Investigator**: Junior Developer (complete task SP-007-011)  
**Sprint**: 007 (Path Navigation)

## Executive Summary
- Reviewed 131 official FHIRPath path navigation expressions; 26 succeed and 105 fail (19.8% pass rate).
- Every failure traces to missing translator support for path-adjacent utility functions (no parser errors observed).
- Three dominant gaps drive 76% of failures: quantity boundary helpers (31 tests), numeric/quantity `convertsTo*` functions (26 tests), and primitive `convertsTo*` functions (23 tests).
- Identified 28 high-confidence quick wins ready for SP-007-012 (<2h each) focused on primitive `convertsTo*`, join/exclude/repeat helpers, and the pending `count()` hook.
- Remaining 77 tests require deeper translator features (quantity boundary math, decimal/time conversions, encoding pipelines) and should be scheduled across Sprint 008.

## Failure Category Overview

| Category | Tests | Failure % | Recommended Track |
| --- | --- | --- | --- |
| Primitive convertsTo (bool/int/string) | 23 | 21.9% | Quick wins (SP-007-012) |
| Numeric/Quantity convertsTo | 26 | 24.8% | Sprint 008 deep work |
| Primitive toX (toString/toBoolean) | 11 | 10.5% | Pair with quick wins |
| toQuantity/toDecimal | 3 | 2.9% | Sprint 008 deep work |
| Quantity boundary (low/high) | 31 | 29.5% | Sprint 008 anchor epics |
| Quantity comparable | 3 | 2.9% | Sprint 008 follow-up |
| String join | 2 | 1.9% | Quick wins (SP-007-012) |
| String encode/decode/unescape | 3 | 2.9% | Sprint 008 deep work |
| Collection repeat | 1 | 1.0% | Quick wins (SP-007-012) |
| Collection exclude | 1 | 1.0% | Quick wins (SP-007-012) |
| count() placeholder | 1 | 1.0% | Quick wins (SP-007-012) |

## Category Details

### Primitive `convertsTo*` (23 tests, Quick Win)
- **Root Cause**: Translator raises `Unknown or unsupported function` for `convertsToBoolean`, `convertsToInteger`, and `convertsToString` despite parser support.
- **Impact**: Blocks simple truthy/path conversions needed for quick-win follow-up task SP-007-012.
- **Representative Tests**: `testLiteralInteger1`, `testLiteralInteger0`, `testStringLiteralConvertsToString`.
- **Recommendation**: Implement translator dispatch for these functions by reusing existing type inference (`is`, `as`) logic. Requires dialect-agnostic predicates only. Estimate: 8–10h total.

### Numeric & Quantity `convertsTo*` (26 tests, Deep Work)
- **Root Cause**: Missing translator logic for decimal, quantity, and temporal conversions (e.g., `convertsToDecimal`, `convertsToQuantity`, `convertsToTime`).
- **Complexity**: Requires normalization rules and dialect-aware casting; overlaps with upcoming SP-007-013 convertsTo* analysis.
- **Recommendation**: Schedule as Sprint 008 epic with dedicated design session. Estimate: 20–24h plus dialect parity validation.

### Primitive `toX` Functions (11 tests, Quick Win Adjacent)
- **Root Cause**: `toString`/`toBoolean` share the same unsupported-function pattern.
- **Recommendation**: Implement alongside primitive `convertsTo*` work (shared predicate handling). Estimate: +6h.

### `toQuantity` / `toDecimal` (3 tests, Deep Work)
- **Root Cause**: Requires quantity construction (units + value) and decimal casting beyond literal scope.
- **Recommendation**: Combine with numeric/quantity `convertsTo*` epic to avoid duplicated adapters.

### Quantity Boundary Helpers (31 tests, Deep Work)
- **Root Cause**: Translator lacks support for `lowBoundary()` / `highBoundary()` (used for interval semantics on decimals and quantities). Needs interval modeling plus dialect math helpers.
- **Recommendation**: Treat as Sprint 008 anchor story; implement boundary extraction in translator with dialect hooks for JSON scalar extraction. Estimate: 24–28h including tests.

### Quantity `comparable()` (3 tests, Deep Work)
- **Root Cause**: Requires chainable unit normalization and comparison logic.
- **Recommendation**: Tackle after numeric conversions, reusing quantity normalization infrastructure. Estimate: 8h.

### String Join / Combine (2 tests, Quick Win)
- **Root Cause**: Missing translator branch for `join()` after `split()` or `name.given`.
- **Recommendation**: Add SQL `string_agg`/`array_join` wrapper via dialect interface. Estimate: 3h (includes dialect parity verification).

### String Encode/Decode/Unescape (3 tests, Deep Work)
- **Root Cause**: Requires implementing codec helpers or deferring to SQL functions not yet exposed in dialect interface.
- **Recommendation**: Schedule Sprint 008 after evaluating dialect capability gaps (may require custom UDF strategy). Estimate: 12h plus RFC.

### Collection Repeat / Exclude / Count (3 tests + 1 placeholder, Quick Win)
- **Root Cause**: Translator lacks support for `repeat()` (string duplication) and `exclude()` (set subtraction). `count()` currently returns placeholder error despite aggregation scaffolding.
- **Recommendation**: Address in SP-007-012 quick-win batch. `count()` should build on aggregation branch landed in SP-007-009. Estimate: 6h combined.

## Quick Wins for SP-007-012

28 tests identified as <2h fixes; grouped around primitive conversion helpers and small collection/string utilities. Raw data: `path_navigation_results.json`.

| Test ID | Expression | Root Cause |
| --- | --- | --- |
| testCount1 | `Patient.name.count()` | Reuse aggregation implementation added in SP-007-009 |
| testDecimalLiteralConvertsToBoolean | `1.0.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testFalseLiteralConvertsToBoolean | `false.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testIntegerLiteralConvertsToBoolean | `1.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testIntegerLiteralConvertsToBooleanFalse | `2.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testIntegerLiteralFalseConvertsToBoolean | `0.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testLiteralBooleanFalse | `false.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testLiteralBooleanTrue | `true.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testStringFalseLiteralAlsoConvertsToBoolean | `'False'.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testStringFalseLiteralConvertsToBoolean | `'false'.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testStringTrueLiteralConvertsToBoolean | `'true'.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testTrueLiteralConvertsToBoolean | `true.convertsToBoolean()` | Implement convertsToBoolean translator hook |
| testBooleanLiteralConvertsToInteger | `true.convertsToInteger()` | Implement convertsToInteger translator hook |
| testIntegerLiteralConvertsToInteger | `1.convertsToInteger()` | Implement convertsToInteger translator hook |
| testLiteralInteger0 | `0.convertsToInteger()` | Implement convertsToInteger translator hook |
| testLiteralInteger1 | `1.convertsToInteger()` | Implement convertsToInteger translator hook |
| testLiteralIntegerMax | `2147483647.convertsToInteger()` | Implement convertsToInteger translator hook |
| testStringLiteralConvertsToInteger | `'1'.convertsToInteger()` | Implement convertsToInteger translator hook |
| testBooleanLiteralConvertsToString | `true.convertsToString()` | Implement convertsToString translator hook |
| testDecimalLiteralConvertsToString | `1.0.convertsToString()` | Implement convertsToString translator hook |
| testIntegerLiteralConvertsToString | `1.convertsToString()` | Implement convertsToString translator hook |
| testLiteralString2 | `'test'.convertsToString()` | Implement convertsToString translator hook |
| testQuantityLiteralConvertsToString | `1 'wk'.convertsToString()` | Implement convertsToString translator hook |
| testStringLiteralConvertsToString | `'true'.convertsToString()` | Implement convertsToString translator hook |
| testCombine2 | `name.given.combine(name.family).exclude('Jim')` | Implement collection exclude using array difference |
| testJoin | `name.given.join(',')` | Add join() string aggregation support |
| testSplit4 | `'[stop]ONE[stop][stop]TWO[stop][stop][stop]THREE[stop][stop]'.split('[stop]').join('[stop]')` | Add join() string aggregation support |
| testRepeat5 | `Patient.name.repeat('test')` | Add repeat() support as string multiplication |

## Sprint 008 Implementation Plan (Draft)

1. **Week 1 – Primitive Conversion Completion (16h)**
   - Ship quick-win bundle (SP-007-012) plus remaining `toString`/`toBoolean`.
   - Validate on DuckDB and PostgreSQL markers.
2. **Week 2 – Numeric & Quantity Conversions (24h)**
   - Implement `convertsToDecimal`, `convertsToQuantity`, `toDecimal`, `toQuantity`.
   - Introduce quantity normalization helpers; coordinate with SP-007-013 findings.
3. **Week 3 – Interval Boundary & Comparable (28h)**
   - Add `lowBoundary`/`highBoundary` plus `comparable()` support, ensuring thin-dialect compliance.
4. **Week 4 – Advanced String Utilities (12h)**
   - Explore dialect capabilities for encode/decode/unescape; add UDF fallback if required.
5. **Week 4 Exit Criteria**
   - Re-run official suite; target ≥70% pass rate for path navigation category.
   - Update translation coverage report and documentation.

## Recommendations
- Prioritize a shared conversion utility module to avoid duplication between `convertsTo*` and `to*` implementations.
- Align SP-007-013 convertsTo* analysis with Sprint 008 backlog grooming to validate estimates.
- Introduce regression tests for join/exclude/repeat once quick-win fixes land to prevent future regressions.

## Risks
- **Dialect Capability Gaps**: Encode/decode/unescape may lack native support, requiring custom SQL functions or fallbacks.
- **Quantity Normalization Complexity**: Unit conversion rules could expand surface area; coordinate with architecture team to avoid dialect drift.
- **Performance Impact**: Boundary/comparable implementations must remain population-first; plan for targeted performance benchmarks post-implementation.

## Appendix
- **Raw Failure Data**: `path_navigation_results.json` (generated 2025-10-07).
- **Reproduction Commands**:
  1. `pytest tests/integration/fhirpath/test_real_expressions_integration.py::TestOfficialFHIRPathExpressionTranslation::test_all_official_expressions_duckdb -q`
  2. `python3 - <<'PY' ... PY` *(inline script in command history that filters official tests, reruns translation, and writes `path_navigation_results.json`)*.
- **Supporting Files**: Aggregated coverage snapshots remain in `translation_report_all_expressions.json`.
