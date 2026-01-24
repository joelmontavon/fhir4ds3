# Task: Fix Type Casting in Comparisons

**Task ID**: SP-022-005
**Sprint**: 022
**Task Name**: Fix VARCHAR to Numeric/Date Type Casting in Comparisons
**Assignee**: Junior Developer
**Created**: 2025-12-11
**Last Updated**: 2025-12-29
**Status**: COMPLETED - MERGED TO MAIN

---

## Task Overview

### Description
When comparing JSON-extracted values (which are VARCHAR) with numeric or date literals, the SQL fails because it cannot compare different types. This causes ~50 compliance test failures.

**Current Behavior (WRONG):**
```sql
-- FHIRPath: Observation.value.value > 180.0
SELECT json_extract_string(resource, '$.value.value') > 180.0
-- ERROR: Cannot compare values of type VARCHAR and type DECIMAL
```

**Expected Behavior (CORRECT):**
```sql
-- FHIRPath: Observation.value.value > 180.0
SELECT CAST(json_extract_string(resource, '$.value.value') AS DECIMAL) > 180.0
-- Works correctly
```

### Category
- [x] Bug Fix

### Priority
- [x] Medium (Valuable but not essential)

---

## Requirements

### Functional Requirements
1. **Numeric comparisons**: `Observation.value.value > 180.0` should work
2. **Date comparisons**: `Patient.birthDate < today()` should work
3. **DateTime comparisons**: `now() > Patient.birthDate` should work
4. **Safe casting**: NULL values should remain NULL, not cause errors

### Acceptance Criteria
- [x] `Observation.value.value > 180.0` executes without error
- [x] `Patient.birthDate < today()` executes without error
- [x] Invalid values (non-numeric strings) don't crash but return NULL/false
- [x] All existing passing tests continue to pass

---

## Technical Specifications

### Root Cause Analysis
JSON extraction functions return VARCHAR (string) type:
```sql
SELECT typeof(json_extract_string(resource, '$.value'));  -- Returns 'VARCHAR'
```

When compared with numeric literals, SQL requires explicit casting.

### The Fix
Add type casting when generating comparison expressions:

```python
def _generate_comparison(self, left_expr, operator, right_expr, left_type, right_type):
    # If comparing VARCHAR with numeric, cast the VARCHAR
    if is_varchar(left_type) and is_numeric(right_type):
        left_expr = f"TRY_CAST({left_expr} AS DECIMAL)"

    if is_varchar(left_type) and is_date(right_type):
        left_expr = f"TRY_CAST({left_expr} AS DATE)"

    return f"({left_expr} {operator} {right_expr})"
```

### Files to Modify
- `fhir4ds/fhirpath/sql/translator.py` - Add casting in comparison translation

### How to Find the Code
```bash
# Find comparison operator translation
grep -n "def.*_translate.*comparison\|def.*_translate.*operator\|>=\|<=" \
    fhir4ds/fhirpath/sql/translator.py | head -20
```

---

## Implementation Steps

### Step 1: Understand the Problem
Run this to see the error:

```bash
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect
import json

dialect = DuckDBDialect(database=':memory:')
conn = dialect.get_connection()

obs = {
    'resourceType': 'Observation',
    'id': 'example',
    'valueQuantity': {'value': 185.0, 'unit': 'mg'}
}
conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
conn.execute('INSERT INTO resource VALUES (1, ?)', [json.dumps(obs)])

executor = FHIRPathExecutor(dialect, 'Observation')
try:
    result = executor.execute('Observation.value.value > 180.0')
    print('Result:', result)
except Exception as e:
    print('Error:', str(e)[:200])
"
```

### Step 2: Understand Type Detection
The translator needs to know when to cast. Look for:
1. How the translator determines expression types
2. How comparison operators are translated

### Step 3: Add Safe Casting Helper
Create a helper for safe type casting:

```python
def _safe_cast_for_comparison(self, expr: str, target_type: str) -> str:
    """Cast expression to target type safely using TRY_CAST.

    TRY_CAST returns NULL instead of error for invalid conversions.
    """
    if target_type == "decimal":
        return f"TRY_CAST({expr} AS DECIMAL)"
    elif target_type == "integer":
        return f"TRY_CAST({expr} AS BIGINT)"
    elif target_type == "date":
        return f"TRY_CAST({expr} AS DATE)"
    elif target_type == "timestamp":
        return f"TRY_CAST({expr} AS TIMESTAMP)"
    else:
        return expr
```

### Step 4: Modify Comparison Translation
Update the comparison operator handling to add casting:

```python
def _translate_comparison_operator(self, left, operator, right):
    """Translate comparison with automatic type casting."""
    left_expr = left.expression
    right_expr = right.expression

    # Determine types (you may need to track this in fragment metadata)
    left_is_json_string = self._is_json_extracted_string(left)
    right_is_literal = self._is_literal_expression(right_expr)

    # If left is JSON string and right is numeric literal, cast left
    if left_is_json_string and self._is_numeric_literal(right_expr):
        left_expr = self._safe_cast_for_comparison(left_expr, "decimal")

    # If left is JSON string and right is date, cast left
    if left_is_json_string and self._is_date_expression(right_expr):
        left_expr = self._safe_cast_for_comparison(left_expr, "date")

    # Handle the reverse case (literal on left, JSON on right)
    if self._is_numeric_literal(left_expr) and self._is_json_extracted_string(right):
        right_expr = self._safe_cast_for_comparison(right_expr, "decimal")

    return f"({left_expr} {operator} {right_expr})"
```

### Step 5: Handle Date/Time Comparisons
Date comparisons need special handling:

```python
# Patient.birthDate < today()
# json_extract_string returns '2000-01-15' as VARCHAR
# today() returns DATE

# Need: TRY_CAST(json_extract_string(...) AS DATE) < today()

def _translate_date_comparison(self, left_expr, operator, right_expr):
    # Cast VARCHAR date string to DATE
    if self._is_date_function(right_expr):  # today(), now(), etc.
        left_expr = f"TRY_CAST({left_expr} AS DATE)"
    return f"({left_expr} {operator} {right_expr})"
```

### Step 6: Test Your Changes

```bash
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect
import json

dialect = DuckDBDialect(database=':memory:')
conn = dialect.get_connection()

patient = {
    'resourceType': 'Patient',
    'id': 'example',
    'birthDate': '2000-01-15'
}
conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
conn.execute('INSERT INTO resource VALUES (1, ?)', [json.dumps(patient)])

executor = FHIRPathExecutor(dialect, 'Patient')

tests = [
    'Patient.birthDate < today()',
    'today() > Patient.birthDate',
]

for expr in tests:
    try:
        result = executor.execute(expr)
        print(f'PASS: {expr} = {result[0][-1]}')
    except Exception as e:
        print(f'FAIL: {expr} - {str(e)[:60]}')
"
```

---

## Database-Specific Considerations

### DuckDB
```sql
-- Safe casting with TRY_CAST
SELECT TRY_CAST('abc' AS INTEGER);  -- Returns NULL, not error
SELECT TRY_CAST('123' AS INTEGER);  -- Returns 123

-- Date handling
SELECT TRY_CAST('2000-01-15' AS DATE);  -- Returns DATE
SELECT current_date;  -- today() equivalent
```

### PostgreSQL
```sql
-- PostgreSQL doesn't have TRY_CAST, need to handle differently
-- Option 1: Use CASE with type checking
CASE
    WHEN value ~ '^[0-9]+\.?[0-9]*$' THEN value::decimal
    ELSE NULL
END

-- Option 2: Create a custom safe_cast function
CREATE FUNCTION safe_cast_decimal(text) RETURNS decimal AS $$
BEGIN
    RETURN $1::decimal;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

You'll need to add dialect-specific casting methods.

---

## Testing Strategy

### Unit Tests to Create
Create `tests/unit/fhirpath/sql/test_type_casting.py`:

```python
class TestTypeCasting:
    def test_numeric_comparison(self, executor):
        """Test comparing JSON value with numeric literal."""
        result = executor.execute("Observation.value.value > 180.0")
        # Should not raise error

    def test_date_comparison(self, executor):
        """Test comparing JSON date with today()."""
        result = executor.execute("Patient.birthDate < today()")
        assert result[0][-1] == True

    def test_invalid_value_returns_null(self, executor):
        """Test that invalid values don't crash."""
        # When value is "abc", comparing to 180.0 should return NULL/false
        result = executor.execute("Observation.value.value > 180.0")
        # Should not crash
```

---

## Common Pitfalls to Avoid

1. **Don't use CAST, use TRY_CAST** - CAST errors on invalid input, TRY_CAST returns NULL
2. **Handle NULL properly** - NULL comparisons should return NULL, not error
3. **Test both directions** - `value > 180` and `180 < value`
4. **Remember PostgreSQL differences** - It doesn't have TRY_CAST

---

## SQL Type Reference

| FHIRPath Type | JSON String Example | Target SQL Type |
|---------------|---------------------|-----------------|
| decimal | "185.5" | DECIMAL |
| integer | "42" | BIGINT |
| date | "2000-01-15" | DATE |
| dateTime | "2000-01-15T10:30:00Z" | TIMESTAMP |
| boolean | "true" | BOOLEAN |

---

## Progress Tracking

### Status
- [x] Completed - Pending Review

### Completion Checklist
- [x] Understood why type casting is needed
- [x] Located comparison translation code
- [x] Implemented safe casting helper
- [x] Added casting to comparison translation
- [x] Handled date/time comparisons
- [x] Tested with DuckDB
- [x] Tested with PostgreSQL
- [x] Created unit tests
- [x] Verified no regressions

---

## Implementation Summary

### Changes Made
1. **Base Dialect** (`fhir4ds/dialects/base.py`):
   - Added 5 new abstract methods for safe type casting:
     - `safe_cast_to_decimal()` - For decimal/numeric comparisons
     - `safe_cast_to_integer()` - For integer comparisons
     - `safe_cast_to_date()` - For date comparisons
     - `safe_cast_to_timestamp()` - For datetime comparisons
     - `safe_cast_to_boolean()` - For boolean comparisons

2. **DuckDB Dialect** (`fhir4ds/dialects/duckdb.py`):
   - Implemented safe casting using `TRY_CAST` (returns NULL on invalid input)

3. **PostgreSQL Dialect** (`fhir4ds/dialects/postgresql.py`):
   - Implemented safe casting using `CASE WHEN` with regex validation
   - PostgreSQL doesn't have TRY_CAST, so regex checks validate format before casting

4. **Translator** (`fhir4ds/fhirpath/sql/translator.py`):
   - Added `literal_type` and `is_literal` metadata to literal fragments
   - Added `is_json_string` metadata to JSON-extracted string fragments
   - Modified `_translate_binary_operator()` to detect type mismatches and apply safe casting
   - Added `_apply_safe_cast_for_type()` helper method

5. **Tests** (`tests/unit/fhirpath/sql/test_translator_type_casting.py`):
   - Created 11 new unit tests covering:
     - Numeric casting (decimal, integer)
     - Date/time casting
     - String comparison (no casting needed)
     - Boolean casting
     - Metadata verification for literals and JSON-extracted values

6. **Test Infrastructure** (`tests/unit/dialects/test_base_dialect.py`):
   - Updated MockDialect to include new safe casting methods

### Test Results
- All 11 new type casting tests pass
- No regressions introduced (pre-existing test failures remain unchanged)
- Tested with both DuckDB and PostgreSQL

### Examples
```sql
-- Before: ERROR - Cannot compare VARCHAR and DECIMAL
SELECT json_extract_string(resource, '$.valueQuantity.value') > 180.0

-- After: Works correctly with safe casting
SELECT TRY_CAST(json_extract_string(resource, '$.valueQuantity.value') AS DECIMAL) > 180.0

-- Date comparison now works
SELECT TRY_CAST(json_extract_string(resource, '$.birthDate') AS DATE) < DATE '2025-01-01'
```

---

**Task Created**: 2025-12-11
**Status**: Completed - Pending Review
**Completed**: 2025-12-29
