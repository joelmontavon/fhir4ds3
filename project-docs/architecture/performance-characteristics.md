# Performance Characteristics – CTE Infrastructure

**Last Updated**: 2025-11-02  
**Derived From**: SP-011-014 compliance run, SP-011-015 benchmark suite

---

## 1. Summary Metrics (Sprint 011)

| Metric | DuckDB | PostgreSQL | Notes |
|--------|--------|------------|-------|
| Path Navigation compliance | 10 / 10 tests (100%) | 10 / 10 tests (100%) | See `project-docs/compliance/sprint-011-results.md` |
| Avg parse time | 1.26 ms | 0.81 ms | Per-expression average from compliance diagnostics |
| Avg translation time | 0.07 ms | 0.07 ms | Translator overhead remains negligible |
| Avg CTE build time | 0.05 ms | 0.02 ms | Matches <0.1 ms target |
| Avg execution time | 2.83 ms | 0.01 ms* | DuckDB measured end-to-end; PostgreSQL currently stubs execution |
| Row-by-row comparison | ≥10x slower | ≥10x slower | Enforced by `tests/benchmarks/fhirpath/test_cte_performance.py` |
| Memory growth (1k patients) | < 100 MB | < 100 MB | Verified by benchmark suite |
| Scalability | Linear to 10k patients | Linear (stub) | High-water mark enforced in benchmarks |

\*PostgreSQL dialect presently validates SQL generation using a stub executor. Live execution timings will be recorded once CI infrastructure provisions a PostgreSQL instance.

## 2. Benchmark Coverage

The regression harness at `tests/benchmarks/fhirpath/test_cte_performance.py` enforces four critical guarantees:

1. **CTE Build Time** – `test_cte_generation_under_10ms` repeats each expression three times and asserts the average `build` stage stays below 10 ms.
2. **Execution Latency** – `test_sql_execution_population_scale` runs each expression against a 1,000-patient dataset with a 150 ms budget.
3. **Row-by-Row Baseline** – `test_cte_outperforms_row_by_row` compares execution against the naive processor implemented in `tests/benchmarks/fhirpath/row_by_row_processor.py`, asserting ≥10x improvement while also verifying identical results.
4. **Scalability** – `test_execution_scalability_linear` ensures growth remains linear (±20%) when scaling from 100 to 10,000 patients.

These tests are designed to run in CI; they materialise deterministic patient datasets via `tests/benchmarks/fhirpath/dataset_utils.py`.

## 3. Observed Timing Distribution (DuckDB)

The compliance harness captured per-stage averages for the 10 official Path Navigation expressions (100-patient dataset):

```text
parse     : 1.26 ms
translate : 0.07 ms
build     : 0.05 ms
assemble  : 0.05 ms
execute   : 2.83 ms
```

- `execute` includes database query time and result materialisation.
- `build` and `assemble` operate entirely in Python and remain well under the 10 ms goal.

## 4. Population-Scale Efficiency

- **Query Count Reduction**: CTE assembly collapses multi-step navigation into a single SQL statement, eliminating per-patient queries entirely.
- **Array Flattening**: LATERAL UNNEST templates ensure nested arrays (e.g., `Patient.name.given`) are flattened in one pass.
- **Memory Footprint**: The in-process RSS increase remains below the 100 MB ceiling for 1,000-patient workloads with nested arrays, leaving headroom for additional expressions.

## 5. Dialect Parity

- Generated SQL for DuckDB and PostgreSQL is structurally identical aside from syntax helpers (UNNEST, JSON extraction).
- Compliance runs confirm equal row counts, sample values, and identifier coverage.
- Benchmark suite currently executes live queries on DuckDB and validates SQL plus row-by-row comparisons on both dialects. PostgreSQL live execution will be added once infrastructure is available.

## 6. Next Steps

1. **Extended Categories**: Incorporate official function/operator suites into the benchmark harness as new translator features arrive.
2. **Telemetry Integration**: Feed `timings_ms` from `FHIRPathExecutor.execute_with_details` into logging/metrics systems for production observability.
3. **PostgreSQL Execution**: Replace the stubbed execution lambda with real database connections during Sprint 012 infrastructure work.
4. **Performance Budget Tracking**: Persist latest timings to a machine-readable JSON file so CI can detect regressions without executing the full benchmark battery on every run.

---

**References**
- `project-docs/compliance/sprint-011-results.md`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
- `tests/benchmarks/fhirpath/row_by_row_processor.py`
- `tests/benchmarks/fhirpath/dataset_utils.py`
