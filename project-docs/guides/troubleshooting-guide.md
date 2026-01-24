# CTE Infrastructure Troubleshooting Guide

**Last Updated**: 2025-11-02  
**Audience**: Engineers diagnosing issues with the Sprint 011 FHIRPath execution pipeline.

---

## 1. Quick Diagnostics Flow

1. **Re-run with details**  
   ```python
   report = executor.execute_with_details(expression)
   ```
   Inspect `report["ctes"]`, `report["sql"]`, and `report["timings_ms"]`.
2. **Validate SQL fragments**  
   Ensure translator metadata (e.g., `array_column`, `result_alias`) is populated.
3. **Check dialect capabilities**  
   Dialect must implement `generate_lateral_unnest` and `execute_query`.
4. **Reproduce with fixtures**  
   Use `tests/benchmarks/fhirpath/dataset_utils.py` to create deterministic patient data.

## 2. Common Symptoms

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| `ValueError: CTE dependency cycle detected` | Translator emitted circular dependencies | Review fragment dependencies; verify translator defers cross references until dependencies exist. |
| SQL contains duplicate `FROM` entries | Fragment metadata missing `source_table`; builder fell back to previous CTE incorrectly | Confirm translator fills `source_table` for root fragments. |
| PostgreSQL tests return empty rows | Dialect stub executed but resource table not populated | Ensure fixtures are loaded into PostgreSQL test instance; until Sprint 012 the stub returns canned data—use DuckDB for result validation. |
| `generate_lateral_unnest` AttributeError | Custom dialect missing helper | Implement `generate_lateral_unnest(self, source, array_expr, alias)` per base contract. |
| `Failed to return connection to pool` warnings in PostgreSQL unit tests | Tests replace `psycopg2.connect` with lightweight fakes that lack connection metadata | PostgreSQL dialect falls back to an internal manual pool—ensure the fake exposes `cursor/commit/rollback` and rerun pytest; no production action required. |
| Memory usage spikes >100 MB | Large dataset without indexes or repeated materialisation | Drop temporary tables after each run as benchmark suite does; consider chunking loads. |

## 3. Debugging Tips

- **Print CTE chain**  
  ```python
  for cte in report["ctes"]:
      print(cte.name, cte.depends_on, cte.metadata.get("array_column"))
  ```
- **Enable logging**  
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```
  The executor logs pipeline stage transitions and failures.
- **Verify UNNEST output**  
  Run the generated SQL manually in the dialect to confirm JSON extraction paths.
- **Check topological order**  
  Order is deterministic; compare against expected `[cte_1, cte_2, ...]` to spot missing dependencies.

## 4. Regression Tests to Run

- `pytest tests/compliance/fhirpath/test_runner.py::test_path_navigation_suite`
- `pytest tests/benchmarks/fhirpath/test_cte_performance.py -k cte_outperforms_row_by_row`
- `pytest tests/benchmarks/fhirpath/test_cte_performance.py -k scalability`

All three suites run quickly (<2 minutes on a laptop) and cover correctness, performance, and scaling concerns.

## 5. When to Escalate

- Dialect output deviates from DuckDB results after confirming identical SQL.
- Topological sorting raises cycles for expressions that previously worked.
- Performance benchmarks regress by >20% compared to stored baselines.
- Compliance suite drops below 10/10 Path Navigation tests.

Document findings and notify the Senior Solution Architect with:
- Expression(s) causing failure
- Generated SQL snippet
- Stage timings
- Database logs (if applicable)

---

**References**
- `project-docs/architecture/cte-infrastructure.md`
- `project-docs/architecture/performance-characteristics.md`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
