# Getting Started with FHIRPath Execution

**Last Updated**: 2025-11-02  
This guide introduces the Sprint 011 FHIRPath execution pipeline and shows how to run your first population-scale query.

---

## 1. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fhir4ds duckdb
```

Optional: install PostgreSQL client libraries if you intend to validate generated SQL against Postgres.

## 2. Prepare Sample Data

Use the bundled 100-patient fixture or load your own Patient resources:

```python
from fhir4ds.dialects.duckdb import DuckDBDialect

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
```

The executor expects a table named `resource` with columns `id` (integer) and `resource` (JSON payload).

## 3. Execute Your First Expression

```python
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor

executor = FHIRPathExecutor(dialect, resource_type="Patient")
details = executor.execute_with_details("Patient.name.given")

print(details["sql"])
print(details["results"][:5])
print(details["timings_ms"])
```

- Results contain flattened given names across the entire dataset.
- `timings_ms` confirms stage-level performance targets (<10 ms build, <150 ms execute for 1k patients).

## 4. Validate Correctness and Performance

- Run the official Path Navigation suite:
  ```bash
  python -m tests.compliance.fhirpath.test_runner
  ```
- Execute the regression benchmarks:
  ```bash
  pytest tests/benchmarks/fhirpath/test_cte_performance.py
  ```

## 5. Next Steps

- Read the architectural overview: `project-docs/architecture/fhirpath-execution-pipeline.md`
- Browse tutorials for detailed examples: `project-docs/tutorials/fhirpath-execution.md`
- Configure PostgreSQL dialect to inspect generated SQL for enterprise deployments.

---

**Need help?** See `project-docs/guides/troubleshooting-guide.md` and open an issue with the generated SQL plus diagnostics from `execute_with_details`.
