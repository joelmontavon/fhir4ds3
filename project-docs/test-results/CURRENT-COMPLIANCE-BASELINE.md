# Current FHIRPath Compliance Baseline

**Test Date**: 2025-11-06  
**Database**: DuckDB (`fhir4ds.fhirpath` enhanced runner)  
**Total Tests**: 934  
**Status**: ⚠️ **42.3% compliance (395/934 tests passing)**

Source data: `project-docs/test-results/compliance-main-2025-11-06-duckdb.json`

---

## Executive Summary

- Fresh official-suite measurement on `main` shows **395/934 tests passing (42.3%)**.  
- This supersedes the 2025-11-04 baseline (44.1%) and confirms we are still **well below** the Sprint 016 acceptance gate (≥46.5%).  
- Compliance on `feature/SP-016-002` matches the main-branch number (no regression detected).  
- Major remaining gaps: arithmetic operators, collection functions (including `$this/$index/$total`), type conversions, and semantic validation for comments/escaped identifiers.

---

## Overall Results

| Metric | Value |
|--------|-------|
| **Passed** | 395 |
| **Failed** | 539 |
| **Compliance** | 42.3% |
| **Execution Time** | 296s (median 398ms/test) |
| **Runner Command** | `python3 - <<'PY' ... run_official_tests()` (see Appendix) |

---

## Category Breakdown

| Category | Passed/Total | % | Status |
|----------|--------------|---|--------|
| Comments / Syntax | 13 / 32 | 40.6% | 🔴 Critical |
| Arithmetic Operators | 10 / 72 | 13.9% | 🔴 Critical |
| Basic Expressions | 2 / 2 | 100.0% | 🟢 Healthy |
| Path Navigation | 8 / 10 | 80.0% | 🟡 Stable (still gaps) |
| Error Handling | 1 / 5 | 20.0% | 🔴 Critical |
| Type Functions | 30 / 116 | 25.9% | 🔴 Critical |
| Collection Functions | 32 / 141 | 22.7% | 🔴 Critical |
| Function Calls | 36 / 113 | 31.9% | 🟠 Needs Work |
| Comparison Operators | 195 / 338 | 57.7% | 🟡 Fair |
| Date/Time Functions | 5 / 6 | 83.3% | 🟢 Healthy (basic literals only) |
| Boolean Logic | 2 / 6 | 33.3% | 🟠 Needs Work |
| String Functions | 41 / 65 | 63.1% | 🟡 Fair |
| Math Functions | 20 / 28 | 71.4% | 🟢 Healthy |

---

## Key Findings

1. **Evaluator still the blocker** – SQL translator unit tests continue to pass, but the in-memory evaluator used by the official suite lacks full arithmetic, type, and collection semantics.
2. **Path navigation improvements landed** – Fixes from SP-016-001 raised navigation tests from 2/10 to 8/10, but polymorphism and `$this` edge cases still fail (`testPolymorphism*`, `testDollarThis2`).
3. **Conversion functions missing** – `convertsToDecimal()`, `convertsToQuantity()`, and related helpers are absent, causing 40+ failures across arithmetic and collection categories.
4. **Lambda variables unresolved** – `$this`, `$index`, `$total` are still unreliable, driving the majority of collection-function failures.
5. **Comments / syntax validation** – Semantic validator accepts malformed expressions (e.g., `2 + 2 /`), which should produce parse errors, inflating failure counts in the comments/syntax bucket.

---

## Next Steps

1. **Documented Baseline** – Treat **42.3%** as the authoritative baseline for Sprint 016 planning. All task documents referencing 64% or 75% must be updated (see `project-docs/plans/COMPLIANCE-REALITY-CHECK.md`).
2. **Compliance Gate** – Sprint-016 tasks must lift compliance above **46.5%**; current delta is **+41 tests**.
3. **Priority fixes**:
   - Arithmetic/operator handling (unary `+/-`, division edge cases)
   - Type + quantity conversions (`convertsTo*`, `to*`)
   - Collection lambdas (`$this/$index/$total`) and `repeat()/where()/select()`
   - Comment/escaped identifier validation in the parser/semantic validator
4. **Regression Tracking** – Store each official-suite run inside `project-docs/test-results/` with branch/date metadata for auditability.

---

## Appendix: Reproduction Details

```bash
# Main branch baseline (DuckDB)
python3 - <<'PY'
from pathlib import Path
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type="duckdb")
report = runner.run_official_tests()
runner.print_compliance_summary(report)
runner.save_compliance_report(Path("project-docs/test-results/compliance-main-2025-11-06-duckdb.json"))
PY
```

- Feature branch `feature/SP-016-002` was measured with the same command → identical 42.3% result (JSON saved as `project-docs/test-results/compliance-feature-SP-016-002-2025-11-06-duckdb.json`).
- Use these JSON artifacts when updating sprint/task documentation or responding to reviews.
