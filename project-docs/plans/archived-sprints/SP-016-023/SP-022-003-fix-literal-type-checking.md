# Task: Fix Type Checking on Literal Values

**Task ID**: SP-022-003
**Sprint**: 022
**Task Name**: Fix is() and as() Type Checking for Literal Values
**Assignee**: Junior Developer
**Created**: 2025-12-11
**Last Updated**: 2025-12-11

---

## Task Overview

### Description
The FHIRPath `is()` and `as()` type checking functions fail when applied to literal values (integers, decimals, strings). The translator tries to use JSON functions on non-JSON values, causing ~30 test failures.

**Current Behavior (WRONG):**
```sql
-- FHIRPath: 1.is(Integer)
SELECT json_type(1) IN ('BIGINT', 'INTEGER')  -- ERROR: json_type expects JSON, not integer
```

**Expected Behavior (CORRECT):**
```sql
-- FHIRPath: 1.is(Integer)
SELECT typeof(1) = 'INTEGER'  -- Use SQL typeof() for native types
```

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Integer type check**: `1.is(Integer)` should return `true`
2. **Decimal type check**: `1.0.is(Decimal)` should return `true`
3. **String type check**: `'hello'.is(String)` should return `true`
4. **Negative type check**: `1.is(Decimal).not()` should return `true` (1 is Integer, not Decimal)

### Acceptance Criteria
- [ ] `1.is(Integer)` returns `true`
- [ ] `1.is(System.Integer)` returns `true`
- [ ] `1.0.is(Decimal)` returns `true`
- [ ] `1.is(Decimal).not()` returns `true`
- [ ] `'hello'.is(String)` returns `true`
- [ ] All existing passing tests continue to pass

---

## Technical Specifications

### Root Cause Analysis
The translator uses `json_type()` for all type checking, but literal values aren't JSON:

```python
# Current (WRONG) - in translator.py
def _translate_is_function(self, node):
    # This assumes the input is always JSON, but literals aren't JSON!
    return f"json_type({expression}) IN ('BIGINT', 'INTEGER')"
```

### The Fix
Detect when the input is a literal value and use SQL's `typeof()` function instead:

```python
# Correct approach
def _translate_is_function(self, node):
    if is_literal_value(expression):
        # Use SQL typeof() for native SQL types
        return f"typeof({expression}) = 'INTEGER'"
    else:
        # Use json_type() for JSON values
        return f"json_type({expression}) IN ('BIGINT', 'INTEGER')"
```

### File to Modify
- `fhir4ds/fhirpath/sql/translator.py`

### How to Find the Code
```bash
# Find the is() function translation
grep -n "_translate_is\|is(Integer)\|json_type" fhir4ds/fhirpath/sql/translator.py | head -20
```

---

## Implementation Steps

### Step 1: Understand the Type Mapping

FHIRPath types map to SQL types:

| FHIRPath Type | DuckDB typeof() | PostgreSQL pg_typeof() |
|---------------|-----------------|------------------------|
| Integer | INTEGER, BIGINT | integer, bigint |
| Decimal | DOUBLE, DECIMAL, FLOAT | numeric, double precision |
| String | VARCHAR | text, character varying |
| Boolean | BOOLEAN | boolean |
| Date | DATE | date |
| DateTime | TIMESTAMP | timestamp |
| Time | TIME | time |

### Step 2: Locate the is() Translation Code
1. Open `fhir4ds/fhirpath/sql/translator.py`
2. Search for `_translate_is` or `is(` function handling
3. Understand how type checking is currently implemented

### Step 3: Add Literal Detection
Create a helper function to detect if an expression is a literal:

```python
def _is_literal_expression(self, expression: str) -> bool:
    """Check if the expression is a SQL literal (not JSON)."""
    expr = expression.strip()

    # Integer literal: just digits, possibly with leading minus
    if expr.lstrip('-').isdigit():
        return True

    # Decimal literal: digits with decimal point
    try:
        float(expr)
        return True
    except ValueError:
        pass

    # String literal: starts and ends with quotes
    if (expr.startswith("'") and expr.endswith("'")) or \
       (expr.startswith('"') and expr.endswith('"')):
        return True

    # Boolean literals
    if expr.upper() in ('TRUE', 'FALSE'):
        return True

    return False
```

### Step 4: Modify the Type Check Translation
Update the `is()` function translation to handle literals:

```python
def _translate_is_type_check(self, expression: str, target_type: str) -> str:
    """Translate is() type check to SQL."""

    # Handle literal values using typeof()
    if self._is_literal_expression(expression):
        return self._translate_literal_type_check(expression, target_type)

    # Handle JSON values using json_type()
    return self._translate_json_type_check(expression, target_type)

def _translate_literal_type_check(self, expression: str, target_type: str) -> str:
    """Type check for SQL literal values."""
    type_lower = target_type.lower().replace('system.', '')

    if type_lower == 'integer':
        return f"(typeof({expression}) IN ('INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT'))"
    elif type_lower == 'decimal':
        return f"(typeof({expression}) IN ('DOUBLE', 'DECIMAL', 'FLOAT', 'REAL'))"
    elif type_lower == 'string':
        return f"(typeof({expression}) = 'VARCHAR')"
    elif type_lower == 'boolean':
        return f"(typeof({expression}) = 'BOOLEAN')"
    else:
        return "false"  # Unknown type
```

### Step 5: Test Your Changes

```bash
# Quick test
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect
import json

dialect = DuckDBDialect(database=':memory:')
conn = dialect.get_connection()
conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
conn.execute(\"INSERT INTO resource VALUES (1, '{}')\")

executor = FHIRPathExecutor(dialect, 'Patient')

tests = [
    ('1.is(Integer)', True),
    ('1.is(System.Integer)', True),
    ('1.0.is(Decimal)', True),
    ('1.is(Decimal).not()', True),
]

for expr, expected in tests:
    try:
        result = executor.execute(expr)
        actual = result[0][-1] if result else None
        status = 'PASS' if actual == expected else 'FAIL'
        print(f'{status}: {expr} = {actual} (expected {expected})')
    except Exception as e:
        print(f'ERROR: {expr} - {e}')
"
```

---

## Testing Strategy

### Unit Tests to Create
Create `tests/unit/fhirpath/sql/test_literal_type_checking.py`:

```python
import pytest
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect

class TestLiteralTypeChecking:
    @pytest.fixture
    def executor(self):
        dialect = DuckDBDialect(database=":memory:")
        conn = dialect.get_connection()
        conn.execute("CREATE TABLE resource (id INTEGER, resource JSON)")
        conn.execute("INSERT INTO resource VALUES (1, '{}')")
        return FHIRPathExecutor(dialect, "Patient")

    def test_integer_is_integer(self, executor):
        result = executor.execute("1.is(Integer)")
        assert result[0][-1] == True

    def test_decimal_is_decimal(self, executor):
        result = executor.execute("1.0.is(Decimal)")
        assert result[0][-1] == True

    def test_integer_is_not_decimal(self, executor):
        result = executor.execute("1.is(Decimal).not()")
        assert result[0][-1] == True
```

---

## Common Pitfalls to Avoid

1. **Don't assume all values are JSON** - Literal values like `1`, `1.0`, `'hello'` are native SQL types
2. **Handle both System.Integer and Integer** - FHIRPath allows both notations
3. **Remember the `.not()` chain** - `1.is(Decimal).not()` should return true
4. **Test with different databases** - DuckDB uses `typeof()`, PostgreSQL uses `pg_typeof()`

---

## Database-Specific Considerations

### DuckDB
```sql
SELECT typeof(1);  -- Returns 'INTEGER'
SELECT typeof(1.0);  -- Returns 'DECIMAL(2,1)'
SELECT typeof('hello');  -- Returns 'VARCHAR'
```

### PostgreSQL
```sql
SELECT pg_typeof(1);  -- Returns 'integer'
SELECT pg_typeof(1.0);  -- Returns 'numeric'
SELECT pg_typeof('hello');  -- Returns 'text' or 'unknown'
```

You may need to add dialect-specific type mappings in the base dialect class.

---

## Resources

### FHIRPath Type System
- https://hl7.org/fhirpath/#types

### SQL Type Checking Functions
- DuckDB: `typeof(expr)` - https://duckdb.org/docs/sql/functions/utility
- PostgreSQL: `pg_typeof(expr)` - https://www.postgresql.org/docs/current/functions-info.html

---

## Progress Tracking

### Status
- [x] Completed - Merged to Main (2025-12-29)

### Completion Checklist
- [x] Understood the difference between JSON and literal type checking
- [x] Located is() translation code in translator.py
- [x] Implemented literal detection helper (`_is_sql_literal_expression`)
- [x] Implemented typeof()-based type checking (`_generate_literal_type_check`)
- [x] Fixed is(), as(), and ofType() to use previous fragment for invocation chains
- [x] Fixed not() to properly chain with previous is()/as() operations
- [x] Tested with both DuckDB and PostgreSQL
- [x] Verified no regressions introduced

---

## Implementation Summary

### Changes Made

1. **`_is_sql_literal_expression()` method** (lines 347-383)
   - Detects if an expression is a SQL literal (integer, decimal, string, boolean)
   - Used to route to simplified type checking for literals

2. **`_generate_literal_type_check()` method** (lines 385-451)
   - Generates simplified type checks for SQL literals using `typeof()` (DuckDB) or `pg_typeof()` (PostgreSQL)
   - Handles parametric type returns (e.g., `DECIMAL(2,1)`) using LIKE patterns

3. **Fixed `_translate_is_from_function_call()`** (lines 5589-5594)
   - Added handling for invocation patterns like `1.is(Integer)` where the literal is a sibling node
   - Uses previous fragment's expression when no path in node.text

4. **Fixed `_translate_as_from_function_call()`** (lines 5831-5842)
   - Same pattern fix for `as()` function

5. **Fixed `_translate_oftype_from_function_call()`** (lines 5959-5963)
   - Same pattern fix for `ofType()` function

6. **Fixed `_translate_not()`** (lines 6902-6925)
   - Added handling for chains like `1.is(Integer).not()` where not() operates on previous fragment

### Test Results

**DuckDB Tests (11/11 passing):**
- `1.is(Integer)` ✓
- `1.is(System.Integer)` ✓
- `1.0.is(Decimal)` ✓
- `1.0.is(System.Decimal)` ✓
- `'hello'.is(String)` ✓
- `'hello'.is(System.String)` ✓
- `1.is(Decimal).not()` ✓
- `1.is(String).not()` ✓
- `1.0.is(Integer).not()` ✓
- `'1'.is(Integer).not()` ✓
- `1.is(Integer).not().not()` ✓

**PostgreSQL Tests (8/8 passing):**
- All acceptance criteria tests pass

---

**Task Created**: 2025-12-11
**Task Completed**: 2025-12-29
**Merged to Main**: 2025-12-29
**Status**: Completed - Merged
