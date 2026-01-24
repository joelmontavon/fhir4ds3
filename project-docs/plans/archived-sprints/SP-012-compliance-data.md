# SP-012 Compliance Data

**Task**: SP-012-008 - Official Test Suite Validation  
**Date**: 2025-10-25  
**Author**: Junior Developer

---

## Execution Summary

| Database | Total Tests | Passed | Failed | Compliance | Total Time (ms) | Avg/Test (ms) |
|----------|-------------|--------|--------|------------|-----------------|---------------|
| DuckDB | 934 | 363 | 571 | 38.9% | 332,522.6 | 356.0 |
| PostgreSQL | 934 | 0 | 934 | 0.0% | 22.4 | <0.1 |

**Baseline (Sprint 011)**: 72% overall compliance on DuckDB. Current DuckDB run shows significant regression (-33.1 pp). PostgreSQL execution failed to produce any compliant results (expected parity with DuckDB).

---

## Category-Level Results

| Category | DuckDB Passed | DuckDB Total | DuckDB % | PostgreSQL Passed | PostgreSQL Total | PostgreSQL % | Delta Passed |
|----------|--------------:|-------------:|---------:|------------------:|-----------------:|-------------:|-------------:|
| arithmetic_operators | 12 | 72 | 16.7% | 0 | 72 | 0.0% | +12 |
| basic_expressions | 1 | 2 | 50.0% | 0 | 2 | 0.0% | +1 |
| boolean_logic | 0 | 6 | 0.0% | 0 | 6 | 0.0% | 0 |
| collection_functions | 22 | 141 | 15.6% | 0 | 141 | 0.0% | +22 |
| comments_syntax | 8 | 32 | 25.0% | 0 | 32 | 0.0% | +8 |
| comparison_operators | 206 | 338 | 60.9% | 0 | 338 | 0.0% | +206 |
| datetime_functions | 0 | 6 | 0.0% | 0 | 6 | 0.0% | 0 |
| error_handling | 0 | 5 | 0.0% | 0 | 5 | 0.0% | 0 |
| function_calls | 37 | 113 | 32.7% | 0 | 113 | 0.0% | +37 |
| math_functions | 25 | 28 | 89.3% | 0 | 28 | 0.0% | +25 |
| path_navigation | 0 | 10 | 0.0% | 0 | 10 | 0.0% | 0 |
| string_functions | 28 | 65 | 43.1% | 0 | 65 | 0.0% | +28 |
| type_functions | 24 | 116 | 20.7% | 0 | 116 | 0.0% | +24 |

---

## Observed Failures

- **DuckDB top failures**: comment parsing (tests `testComment7`, `testComment8`), patient path navigation (`name.given`, `telecom.use`), basic presence checks (`birthDate`).
- **PostgreSQL failure pattern**: all expressions return `Unexpected evaluation outcome` immediately, indicating evaluation pipeline did not execute SQL (likely regression in PostgreSQL execution integration).
- Multi-database parity requirement **failed** (363 vs 0 passes).

---

## Raw Data

- DuckDB report JSON: `project-docs/plans/current-sprint/data/SP-012-008-duckdb-report.json`
- PostgreSQL report JSON: `project-docs/plans/current-sprint/data/SP-012-008-postgresql-report.json`

All subsequent documentation references these artifacts.
