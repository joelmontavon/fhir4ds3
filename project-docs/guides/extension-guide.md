# CTE Infrastructure Extension Guide

**Last Updated**: 2025-11-02  
**Audience**: Contributors adding new database dialects or extending translator capabilities on top of the Sprint 011 foundation.

---

## 1. Adding a New Database Dialect

1. **Subclass `DatabaseDialect`**
   ```python
   from fhir4ds.dialects.base import DatabaseDialect

   class BigQueryDialect(DatabaseDialect):
       def generate_lateral_unnest(self, source: str, array_expr: str, alias: str) -> str:
           return f"LATERAL FLATTEN({array_expr}) AS {alias}"
   ```
2. **Implement Execution Hooks**
   - `execute_query(sql: str) -> list[Any]`
   - Optional: `execute_script`, connection lifecycle helpers.
3. **Wire into Translator**
   - Provide dialect-specific JSON helpers if needed (e.g., `json_extract`).
   - Ensure translator metadata aligns with dialect capabilities.
4. **Validate with Benchmarks**
   - Run `tests/benchmarks/fhirpath/test_cte_performance.py --dialect bigquery`.
   - Confirm ≥10x improvement vs row-by-row baseline (update helper if needed).

## 2. Extending Translator Output

When supporting new FHIRPath constructs:

- Emit `SQLFragment` instances with appropriate metadata.
- For array interactions, set `requires_unnest=True` and include:
  ```python
  metadata={
      "array_column": "...",
      "result_alias": "...",
      "projection_expression": "...",
      "id_column": "...",
  }
  ```
- Use `fragment.dependencies` to express cross-CTE requirements (e.g., filters applied after navigation).

## 3. Customising CTE Assembly

- Prefer adding metadata to `CTE.metadata` instead of altering builder/assembler signatures.
- If you need additional SELECT clauses at the end (e.g., grouping), wrap the assembled SQL instead of modifying `_generate_final_select`.
- Proposed enhancements should maintain dialect agnosticism. If you find yourself adding database-specific logic, re-express it as a dialect helper.

## 4. Compliance & Regression Checklist

- [ ] Path Navigation compliance suite still passes (10/10).
- [ ] Performance benchmarks stay within budgets (<10 ms build, ≥10x improvement).
- [ ] Dialect parity tests succeed (identical row counts DuckDB vs new dialect).
- [ ] Documentation updated:
  - Dialect reference in `project-docs/architecture/cte-infrastructure.md`
  - Performance impact recorded in `project-docs/architecture/performance-characteristics.md`
  - User-facing README quick start mentions new dialect if public.

## 5. Packaging & Release Considerations

- Add optional dependencies for new dialect drivers under `extras_require` in `pyproject.toml`.
- Update CI matrix to include new dialect benchmarks.
- Provide sample connection configuration in `docs/guides/integration.md`.

## 6. Example: Adding Snowflake Support (Outline)

1. Implement `SnowflakeDialect` with UNNEST mapping to `LATERAL FLATTEN`.
2. Ensure translator JSON helpers emit `PARSE_JSON`.
3. Run compliance suite using Snowflake test containers or mocks.
4. Capture benchmark results and append to performance documentation.

---

**References**
- `fhir4ds/dialects/base.py`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
- `project-docs/architecture/cte-infrastructure.md`
