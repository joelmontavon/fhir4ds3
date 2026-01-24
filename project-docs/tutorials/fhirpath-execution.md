# Tutorial Series: FHIRPath Execution with CTE Infrastructure

**Last Updated**: 2025-11-02  
**Prerequisites**: Python 3.10+, DuckDB installed (`pip install duckdb`), sample Patient dataset (`tests/fixtures/fhir/patients.json`).

---

## Tutorial 1 — Basic Path Navigation

Goal: Evaluate scalar expressions such as `Patient.birthDate`.

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

executor = FHIRPathExecutor(dialect, "Patient")

details = executor.execute_with_details("Patient.birthDate")
print(details["sql"])
print(details["results"][:3])
```

**What to Observe**
- Generated SQL contains a single CTE projecting `birthDate`.
- `timings_ms["execute"]` should be <5 ms on a laptop.
- Result set length equals patient count (100).

## Tutorial 2 — Array Navigation with LATERAL UNNEST

Goal: Understand how the builder uses dialect helpers to flatten arrays.

```python
details = executor.execute_with_details("Patient.name.given")

for cte in details["ctes"]:
    print(cte.name, cte.depends_on, cte.metadata.get("array_column"))

print(details["sql"])
"""
WITH
  cte_1 AS (
    SELECT resource.id,
           json_extract(resource, '$.name') AS name_item
    FROM resource,
         LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
  ),
  cte_2 AS (
    SELECT cte_1.id,
           given_item AS given_item
    FROM cte_1,
         LATERAL UNNEST(json_extract(name_item, '$.given')) AS given_item
  )
SELECT * FROM cte_2;
"""
print("Given names:", len(details["results"]))
```

**Key Points**
- Two CTEs are generated: one for `Patient.name`, one for `name.given`.
- Dependencies `[cte_1]` ensure assembler ordering.
- Array column metadata is visible through `cte.metadata`.

## Tutorial 3 — Advanced Expressions and Performance

Goal: Combine navigation with filters and inspect performance characteristics.

```python
expression = "Patient.name.given.where($this.startsWith('A'))"
report = executor.execute_with_details(expression)

print("CTE order:", [cte.name for cte in report["ctes"]])
print("Timings (ms):", report["timings_ms"])
print("Rows returned:", len(report["results"]))
```

**Performance Validation**
- `report["timings_ms"]["build"]` and `["assemble"]` remain <10 ms.
- Compare execution time against row-by-row baseline using:
  ```python
  from tests.benchmarks.fhirpath.row_by_row_processor import RowByRowProcessor
  processor = RowByRowProcessor(dialect, "Patient")
  baseline = processor.execute(expression, [int(r["id"]) for r in dialect.execute_query("SELECT id FROM resource")])
  assert sorted(baseline) == sorted(report["results"])
  ```
- Improvement factor should be ≥10x.

**Troubleshooting**
- If SQL contains unexpected duplicate joins, inspect translator metadata using `report["fragments"]`.
- Ensure the dataset includes the necessary elements (`given` names starting with 'A') to avoid empty results.

---

## Next Steps

1. Run the official Path Navigation compliance suite (`python -m tests.compliance.fhirpath.test_runner`).
2. Execute benchmark tests to confirm performance budgets.
3. Try executing the same expressions with `PostgreSQLDialect` to validate dialect parity.
4. Explore CQL integration by feeding FHIRPath expressions generated from CQL defines into the same executor flow.

---

**References**
- `project-docs/architecture/fhirpath-execution-pipeline.md`
- `project-docs/guides/cte-integration-guide.md`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
