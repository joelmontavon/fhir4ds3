# FHIRPath Compliance Testing

## Important: Use the Correct Test Runner

**DO NOT use `test_fhirpath_compliance.py` (if it exists) - it is a stub that always passes.**

## Correct Test Runner

Use: `tests/integration/fhirpath/official_test_runner.py`

This runner:
- Uses SQL translation exclusively (production path)
- Actually validates results against expected outputs
- Provides accurate compliance measurements
- Supports both DuckDB and PostgreSQL

## Running Compliance Tests

### Quick Validation (50 tests)
```python
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement

# Run limited tests for quick validation (~18 seconds)
report = run_compliance_measurement(database_type='duckdb', max_tests=50)
```

### Full Suite
```python
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement

# Run full suite (~6 minutes)
report = run_compliance_measurement(database_type='duckdb', max_tests=None)
```

### Command Line
```bash
# With timeout (recommended)
PYTHONPATH=. timeout 512 python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=None)
"

# Quick validation
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=100)
"
```

---

## Test Suite Information

| Metric | Value |
|--------|-------|
| Total tests in official suite | 934 |
| Source | HL7 FHIRPath R4 test cases (`official_tests.xml`) |
| Average time per test | ~0.37 seconds |
| Full suite execution time | ~6 minutes |
| Recommended timeout | 512 seconds (8.5 minutes) |

---

## Timing and Performance

### Measured Performance (2025-12-30)

| Batch Size | Elapsed Time | Per Test |
|------------|--------------|----------|
| 50 tests | 18.2s | 0.364s |
| 100 tests | 36.8s | 0.368s |
| 200 tests | ~73s | 0.367s |

### Recommended Timeout Configuration

For CI/CD pipelines, use a timeout of **512 seconds** (8.5 minutes) to allow for variance:

```bash
# Environment variable
export FHIRPATH_COMPLIANCE_TIMEOUT_SECONDS=512

# pytest with timeout
timeout 512 python3 -m pytest tests/integration/fhirpath/ -v
```

### Memory Considerations

Each test creates a temporary DuckDB database. For environments with limited memory:

1. **Run in batches** of 200-300 tests using `max_tests` parameter
2. **Increase available memory** to at least 2GB for full suite
3. **Use process isolation** if memory pressure occurs

---

## Current Compliance Status

### As of 2026-01-01 (Sprint 022)

**Full suite: 50.2% compliance** (469/934 tests passing)

| Category | Compliance | Passed | Failed | Notes |
|----------|------------|--------|--------|-------|
| Basic_Expressions | 100.0% | 2 | 0 | Simple expressions |
| Path_Navigation | 90.0% | 9 | 1 | Core path access |
| Datetime_Functions | 83.3% | 5 | 1 | today(), now() comparisons |
| Comparison_Operators | 71.0% | 240 | 98 | Equality, ordering |
| Math_Functions | 67.9% | 19 | 9 | abs(), ceiling(), etc. |
| Boolean_Logic | 66.7% | 4 | 2 | and, or, not, implies, xor |
| String_Functions | 61.5% | 40 | 25 | String manipulation |
| Function_Calls | 39.8% | 45 | 68 | convertsTo*, to*, iif |
| Type_Functions | 37.9% | 44 | 72 | is(), as(), ofType() |
| Arithmetic_Operators | 25.0% | 18 | 54 | Math operations |
| Collection_Functions | 24.8% | 35 | 106 | where(), select(), first(), etc. |
| Comments_Syntax | 21.9% | 7 | 25 | Comment parsing |
| Error_Handling | 20.0% | 1 | 4 | Invalid expressions |

### Key Focus Areas for Improvement

Based on error analysis, these are the highest-impact issues to address:

#### High Priority (Major Impact)

1. **Result logic mismatches** (~184 tests in "Other" category)
   - Various expressions execute but return incorrect results
   - Requires case-by-case analysis of specific test failures
   - Many involve complex type handling and collection semantics

2. **Union operator result handling** (~30 tests)
   - Expressions with `|` operator produce incorrect results
   - Affects: collection comparisons, equality with unions
   - Root cause: Union collection semantics not fully aligned with spec

3. **Type conversion functions** (~25 tests)
   - `convertsToInteger()`, `toDecimal()`, etc. produce wrong results
   - Affects type checking and conversion operations

4. **is() type checking** (~23 tests)
   - Type assertions returning incorrect boolean values
   - Example: `Observation.value is Quantity`

5. **Collection slicing chains** (~20 tests)
   - Error: "Referenced column 'name_item'/'result' not found"
   - Affects: `Patient.name.first().given`, `name.take(2).given`
   - Root cause: CTE column references not propagating through function chains

#### Medium Priority

6. **Empty collection {} handling** (~17 tests)
   - Error: "Could not convert string '{}' to BOOL/INT32"
   - Affects: `true = {}`, `'1.1'.toInteger() = {}`
   - Root cause: Empty collection literal needs special comparison handling

7. **Date/time literal handling** (~14 tests)
   - Partial dates: `@2018-03`, timezone: `@2012-04-15T15:00:00Z`
   - Root cause: Year-month dates and Z timezone suffix parsing

8. **count() function** (~12 tests)
   - Issues with count after select() and on non-resource collections
   - Partially improved in SP-022-019

9. **select() function** (~11 tests)
   - Nested array flattening not implemented
   - Union in select projection not handled
   - SQL syntax issues mostly resolved in SP-022-019

10. **iif() type mismatch** (~10 tests)
    - Error: "Cannot mix values of type DOUBLE and BOOLEAN in CASE"
    - CASE expression requires same type in all branches

#### Lower Priority

11. **XOR operator** (~9 tests) - Not implemented in DuckDB
12. **matches() regex** (~11 tests) - Regex semantics differences
13. **implies operator** (~7 tests) - Boolean logic with empty collections
14. **Quantity arithmetic** (~5 tests) - `2.0 'cm' * 2.0 'm'`
15. **repeat() function** (~3 tests) - Recursive path expansion
16. **Error rejection** (~26 tests) - Should reject invalid syntax but accepts it

### Recently Fixed Issues (Sprint 022)

- ~~**Union operator exponential growth**~~ - **FIXED in SP-022-013**
- ~~**iif() boolean literal validation**~~ - **FIXED in SP-022-011**
- ~~**where() $this variable binding**~~ - **FIXED in SP-022-012**
- ~~**aggregate() input collection**~~ - **FIXED in SP-022-015**
- ~~**iif() in aggregate() context**~~ - **FIXED in SP-022-016**
- ~~**Chained path alias propagation**~~ - **FIXED in SP-022-017**
- ~~**count() for non-resource collections**~~ - **FIXED in SP-022-018**
- ~~**select() SQL generation and CTE chain**~~ - **FIXED in SP-022-019**

See `project-docs/plans/tasks/` for task documentation.

---

## Test Categories

The test runner categorizes tests into these FHIRPath specification areas:

- **path_navigation**: Simple path expressions (e.g., `Patient.name.given`)
- **boolean_logic**: Logical operators (`and`, `or`, `not`, `implies`, `xor`)
- **comparison_operators**: Equality and ordering (`=`, `!=`, `<`, `>`, `~`)
- **arithmetic_operators**: Math operations (`+`, `-`, `*`, `/`, `div`, `mod`)
- **string_functions**: String manipulation (`substring`, `contains`, `matches`)
- **collection_functions**: Collection operations (`where`, `select`, `first`, `exists`)
- **type_functions**: Type operations (`is`, `as`, `ofType`)
- **datetime_functions**: Date/time functions (`today`, `now`, `timeOfDay`)
- **function_calls**: General function invocations
- **literals_constants**: Literal values and constants
- **error_handling**: Invalid expression handling
- **comments_syntax**: Comment parsing

---

## Interpreting Results

### Compliance Report Fields

```python
report.total_tests        # Total tests executed
report.passed_tests       # Tests that passed
report.failed_tests       # Tests that failed
report.compliance_percentage  # Pass rate as percentage
report.test_categories    # Breakdown by category
report.failed_test_analysis  # Details on first 10 failures
```

### Debugging Failures

To investigate specific failures:

```python
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='iif')  # Filter by name

# Check detailed failure info
for result in runner.test_results:
    if not result.passed:
        print(f"Test: {result.name}")
        print(f"Expression: {result.expression}")
        print(f"Expected: {result.expected_outputs}")
        print(f"Actual: {result.actual_result}")
        print(f"Error: {result.error_message}")
        print()
```

---

## Historical Compliance

| Date | Compliance | Tests Passing | Notes |
|------|------------|---------------|-------|
| 2025-10-17 | 64.99% | 607/934 | Sprint 009 baseline |
| 2025-12-30 | 35.91% | 334/930 | Sprint 022 (SQL-only mode, 4 tests skipped) |
| 2025-12-31 | 49.3% | 460/934 | Sprint 022 (all tests running, multiple fixes merged) |
| 2026-01-01 | 50.2% | 469/934 | Sprint 022 (SP-022-019 select() fix merged) |

**Note**: The decrease from Sprint 009 to 35.91% reflects the switch to SQL-only execution mode (no Python evaluator fallback), which tests actual production capabilities. The improvement to 50.2% reflects fixes for union operator, aggregate(), iif(), where(), select(), and count() functions.
