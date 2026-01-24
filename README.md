# FHIR for Data Science (FHIR4DS)

Population-scale analytics platform for FHIR R4 with unified FHIRPath execution.

**Sprint 011 Highlights**
- ✅ 10/10 official Path Navigation tests passing (DuckDB + PostgreSQL parity)
- ✅ ≥72% overall FHIRPath specification compliance (up from ~60% pre-sprint)
- 🚀 ≥10× speed-up versus row-by-row execution across all navigation expressions
- 📈 Stage timings well below targets (DuckDB execute average: 2.83 ms)

## Key Capabilities

- **Unified FHIRPath pipeline** – Parser → Translator → CTE Builder/Assembler → Dialect execution
- **Dual database support** – DuckDB (live execution) and PostgreSQL (SQL parity, execution landing in Sprint 012)
- **Population-first SQL generation** – Common Table Expressions for array navigation, nested traversal, and scalar projections
- **Benchmark-backed performance** – Regression harness enforces <10 ms CTE build, <150 ms execution for 1k patients, ≥10× improvement vs row-by-row
- **Documentation-first workflow** – Architecture diagrams, integration guides, and tutorials covering every stage of the pipeline

## FHIRPath Execution Quick Start

```bash
pip install fhir4ds duckdb
```

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

report = executor.execute_with_details("Patient.name.given")
print(report["sql"])
print(f"Flattened given names: {len(report['results'])}")
print(f"Execution time: {report['timings_ms']['execute']:.2f} ms")
```

- Swap `DuckDBDialect` for `PostgreSQLDialect` to validate SQL generation against Postgres.
- Use `report["ctes"]` to inspect generated WITH clauses and dependencies.

For high-level integration guidance, see `project-docs/guides/cte-integration-guide.md`.

## Documentation

- Architecture overview: `project-docs/architecture/fhirpath-execution-pipeline.md`
- CTE infrastructure deep dive: `project-docs/architecture/cte-infrastructure.md`
- Performance findings: `project-docs/architecture/performance-characteristics.md`
- Tutorials: `project-docs/tutorials/fhirpath-execution.md` and `project-docs/tutorials/path-navigation-examples.md`
- Troubleshooting & extensions: `project-docs/guides/troubleshooting-guide.md`, `project-docs/guides/extension-guide.md`

## Experimental: Clinical Quality Language (CQL) Support

FHIR4DS now includes **experimental support** for Clinical Quality Language (CQL), specifically optimized for population health analytics and quality measure evaluation.

### Implemented CQL Functionality

- CQL expression parser extending FHIRPath parser
- CQL-to-FHIRPath translation for seamless SQL generation
- Library management with define statements, includes, and parameters
- Context management (Patient, Population, Practitioner, Encounter contexts)
- Population-first processing - 10-100x performance improvement

### Known Limitations & Gaps

- Complex CQL expressions with advanced syntax patterns may not parse correctly
- Some CQL-specific constructs still under development
- Advanced query expressions (complex `from`/`where`/`return` clauses) have limited support
- Terminology functions (CodeSystem, ValueSet operations) are basic implementations
- Error handling for edge cases needs improvement

### 🔬 CQL Quick Start

```python
from fhir4ds.cql.core.engine import CQLEngine
from fhir4ds.cql.measures.quality import QualityMeasureEngine
from fhir4ds.dialects import DuckDBDialect

# Initialize CQL engine (defaults to population-first processing)
cql_engine = CQLEngine(dialect="duckdb")

# Simple CQL expression evaluation
sql = cql_engine.evaluate_expression("Patient.name.family")

# Population health analytics (optimized for large datasets)
cql_engine.set_population_context({
    'ageRange': (18, 65),
    'gender': 'female'
})

# Quality measure evaluation
quality_engine = QualityMeasureEngine(cql_engine)
quality_engine.load_predefined_measures()
results = quality_engine.evaluate_measure("CMS122v12")  # Diabetes HbA1c measure
```

## Testing

Run the comprehensive test suite:

```bash
# Test both DuckDB and PostgreSQL dialects
python tests/run_tests.py --dialect all

# Test specific dialect
python tests/run_tests.py --dialect duckdb
python tests/run_tests.py --dialect postgresql
```

Sprint 011 compliance results: `tests/compliance/fhirpath/test_runner.py` reports 10/10 official Path Navigation tests passing on DuckDB and PostgreSQL. See `project-docs/compliance/sprint-011-results.md` for detailed metrics.

## License

GNU General Public License v3 (GPLv3)

## Related Projects

- [SQL-on-FHIR Specification](https://github.com/FHIR/sql-on-fhir-v2) - Official specification
- [FHIR R4 Specification](https://hl7.org/fhir/R4/) - FHIR standard
- [DuckDB](https://duckdb.org/) - High-performance analytics database
- [PostgreSQL](https://www.postgresql.org/) - Enterprise-grade relational database
