# Path Navigation Examples (Official Sprint 011 Set)

**Last Updated**: 2025-11-02  
**Dataset**: `tests/fixtures/fhir/patients.json` (100 synthetic patients)

Each section below documents the official Path Navigation expressions exercised during Sprint 011 compliance and performance testing. Examples use DuckDB for live execution; PostgreSQL results were validated via generated SQL and stubbed execution.

---

## How to Run the Examples

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
```

For each expression below:
1. Execute `executor.execute_with_details(expression)`.
2. Inspect the generated SQL (`details["sql"]`).
3. Validate row counts and sample values.

---

## 1. `Patient.birthDate`

- **Expectation**: 100 rows (one birth date per patient)
- **Result Summary**: `len(results) == 100`
- **Sample SQL**:
  ```sql
  WITH
    cte_1 AS (
      SELECT resource.id,
             json_extract(resource, '$.birthDate') AS result
      FROM resource
    )
  SELECT * FROM cte_1;
  ```
- **Performance**: ~2.5 ms execution, 0.05 ms build

---

## 2. `Patient.gender`

- **Expectation**: 100 rows
- **SQL** similar to `Patient.birthDate` with `$.gender`.
- **Result Check**:
  ```python
  values = {row[1] for row in details["results"]}
  assert values <= {"male", "female"}
  ```

---

## 3. `Patient.active`

- **Expectation**: 100 boolean rows
- **Tip**: Use `bool(row[1])` to coerce textual booleans if needed.
- **Performance**: Execution <3 ms

---

## 4. `Patient.name`

- **Expectation**: 200 rows (two names per patient)
- **Key Metadata**: `array_column="json_extract(resource, '$.name')"`
- **SQL Excerpt**:
  ```sql
  FROM resource,
       LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
  ```
- **Validation**:
  ```python
  assert len(details["results"]) == 200
  ```

---

## 5. `Patient.name.given`

- **Expectation**: 300 rows (three given names across sample data)
- **CTE Chain**: Two CTEs; second depends on `cte_1`.
- **Row Order**: Deterministic because builder preserves insertion order.
- **Performance**: Execute ~4 ms, still <10 ms build.

---

## 6. `Patient.name.family`

- **Expectation**: 200 rows
- **SQL Excerpt**:
  ```sql
  json_extract(name_item, '$.family') AS result
  ```
- **Validation**: Unique family names count equals patient count (100).

---

## 7. `Patient.telecom`

- **Expectation**: 200 rows
- **UNNEST Alias**: `telecom_item`
- **Validation**:
  ```python
  assert all("system" in row[1] for row in details["results"])
  ```

---

## 8. `Patient.identifier`

- **Expectation**: 200 rows
- **Projection**: `projection_expression` often set to `identifier_item`
- **Performance**: Execution <5 ms

---

## 9. `Patient.address`

- **Expectation**: 100 rows
- **Metadata**: `array_column` uses `$.address`
- **Usage**:
  ```python
  addresses = [row[1] for row in details["results"]]
  assert all("line" in address for address in addresses)
  ```

---

## 10. `Patient.address.line`

- **Expectation**: 200 rows (two lines per address)
- **CTE Chain**: Similar to `name.given` with nested UNNEST.
- **Performance**: Execution ~5 ms; maintain <150 ms even for 1,000 patients per benchmarks.

---

## Observability Tips

- Use `details["timings_ms"]` to confirm average timings match the Sprint 011 benchmarks (parse ~1 ms, execute ~3 ms).
- `details["ctes"]` exposes metadata needed for debugging or visualisation. Inspect `cte.metadata["array_column"]` to ensure translator emitted correct JSON paths.
- Compare results against row-by-row baseline using `RowByRowProcessor` to validate correctness when onboarding new datasets.

---

**References**
- `project-docs/compliance/sprint-011-results.md`
- `tests/compliance/fhirpath/official/path_navigation.json`
- `tests/benchmarks/fhirpath/test_cte_performance.py`
