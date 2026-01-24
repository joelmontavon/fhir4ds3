# CTE Infrastructure Integration Guide

**Last Updated**: 2025-11-02  
**Audience**: Developers integrating the Sprint 011 FHIRPath executor into services, notebooks, or downstream frameworks.

---

## 1. Quick Start – FHIRPathExecutor

```python
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor

dialect = DuckDBDialect(database=":memory:")
conn = dialect.get_connection()
conn.execute(
    """
    CREATE TABLE resource AS
    SELECT CAST(id AS INTEGER) AS id,
           to_json(patient) AS resource
    FROM read_json_auto(?) AS patient
    """,
    ['tests/fixtures/fhir/patients.json'],
)

executor = FHIRPathExecutor(dialect, resource_type="Patient")

result = executor.execute("Patient.name.given")
print(f"Flattened given names: {len(result)}")
```

- Dialect may be swapped for `PostgreSQLDialect` once a connection string is configured.
- Use `execute_with_details` when you need the generated SQL, CTE chain, or timing diagnostics.

## 2. Low-Level Control – Builder + Assembler

When you need to inspect or modify intermediate structures, work directly with the translator output:

```python
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.cte import CTEBuilder, CTEAssembler

parser = FHIRPathParser()
translator = ASTToSQLTranslator(dialect, resource_type="Patient")
builder = CTEBuilder(dialect)
assembler = CTEAssembler(dialect)

parsed = parser.parse("Patient.birthDate")
fragments = translator.translate(parsed.get_ast())
ctes = builder.build_cte_chain(fragments)
sql = assembler.assemble_query(ctes)

print(sql)
"""
WITH
  cte_1 AS (
    SELECT resource.id,
           json_extract(resource, '$.birthDate') AS result
    FROM resource
  )
SELECT * FROM cte_1;
"""
```

This is the recommended flow when building analytics tooling that needs access to intermediate artifacts (for example, to visualise dependency graphs or apply custom optimisations).

## 3. Multi-Dialect Execution

```python
from fhir4ds.dialects.postgresql import PostgreSQLDialect

duck = DuckDBDialect(database=":memory:")
pg = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")

for dialect in (duck, pg):
    executor = FHIRPathExecutor(dialect, "Patient")
    details = executor.execute_with_details("Patient.name")
    print(dialect.__class__.__name__, len(details["results"]))
```

- PostgreSQL currently executes via a stubbed interface in Sprint 011 test environments; use the generated SQL by calling `details["sql"]`.
- Dialects expose syntax-only helpers (e.g., `generate_lateral_unnest`) so behaviour remains identical.

## 4. Integration Checklist

- [ ] Load resource tables into the target database (`resource` table or similar schema).
- [ ] Instantiate appropriate dialect and executor.
- [ ] Prefer `execute_with_details` during development to inspect diagnostics.
- [ ] Run `tests/benchmarks/fhirpath/test_cte_performance.py` before release to ensure performance budgets hold.
- [ ] Capture compliance results from `tests/compliance/fhirpath/test_runner.py` (Path Navigation suite).

## 5. Common Pitfalls

| Issue | Resolution |
|-------|-----------|
| Empty result sets | Ensure the resource table uses the expected schema (`id`, `resource`). |
| Missing array values | Verify translator metadata includes `array_column`; run with `execute_with_details` to inspect CTE metadata. |
| Dialect errors | Confirm the dialect implements `generate_lateral_unnest`. Custom dialects should inherit from `DatabaseDialect`. |
| PostgreSQL stub results | Use `details["sql"]` for validation until live execution support lands in Sprint 012. |

## 6. Useful Diagnostics

- `details["timings_ms"]` – stage timings (`parse`, `translate`, `build`, `assemble`, `execute`).
- `details["ctes"]` – ordered list of `CTE` objects. Each entry includes `depends_on` and `metadata`.
- `details["sql"]` – final SQL string ready for execution or logging.

## 7. Next Steps

- Combine multiple expressions by running translators independently and concatenating CTE chains before assembly.
- Feed generated SQL into your query planner/optimizer for additional tuning.
- Integrate with the CQL engine (PEP-005) by routing define statements through the same executor pipeline.

---

**References**
- `fhir4ds/fhirpath/sql/executor.py`
- `project-docs/architecture/cte-infrastructure.md`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
