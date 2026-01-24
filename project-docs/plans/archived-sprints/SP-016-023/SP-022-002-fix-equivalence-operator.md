# Task: Fix Equivalence Operator (~) Translation

**Task ID**: SP-022-002
**Sprint**: 022
**Task Name**: Fix FHIRPath Equivalence Operator (~) SQL Translation
**Assignee**: Junior Developer
**Created**: 2025-12-11
**Last Updated**: 2025-12-11

---

## Task Overview

### Description
The FHIRPath equivalence operator `~` is incorrectly translated to SQL `LIKE` operator. This causes ~29 compliance test failures.

**Current Behavior (WRONG):**
```sql
-- FHIRPath: 1 ~ 1
SELECT (1 LIKE 1) AS result  -- ERROR: LIKE requires strings
```

**Expected Behavior (CORRECT):**
```sql
-- FHIRPath: 1 ~ 1
SELECT (1 = 1) AS result  -- For simple values, equivalence is equality
```

### What is Equivalence (~) in FHIRPath?
The `~` operator tests "equivalence" which is different from equality (`=`):
- For simple types (integers, decimals, booleans): equivalence is the same as equality
- For strings: equivalence is case-insensitive comparison
- For collections: order doesn't matter (set comparison)
- For quantities: units are compared semantically (1 'm' ~ 100 'cm' is true)

For this task, focus on **simple types** first (integers, decimals, strings, booleans).

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Integer equivalence**: `1 ~ 1` should return `true`
2. **Decimal equivalence**: `1.0 ~ 1.0` should return `true`
3. **String equivalence**: `'ABC' ~ 'abc'` should return `true` (case-insensitive)
4. **Boolean equivalence**: `true ~ true` should return `true`

### Acceptance Criteria
- [ ] `1 ~ 1` returns `true`
- [ ] `1.toDecimal() ~ 1.0` returns `true`
- [ ] `'abc' ~ 'ABC'` returns `true`
- [ ] All existing passing tests continue to pass
- [ ] At least 20 of the 29 equivalence-related tests pass

---

## Technical Specifications

### Root Cause Analysis
In the translator, the `~` operator is being mapped to SQL `LIKE`:

```python
# Current (WRONG) - somewhere in translator.py
if operator == '~':
    sql = f"{left} LIKE {right}"  # LIKE is for pattern matching, not equivalence!
```

### The Fix
Replace the LIKE translation with proper equivalence logic:

```python
# Correct approach
if operator == '~':
    # For simple types, use equality
    # For strings, use case-insensitive comparison
    if is_string_type(left) or is_string_type(right):
        sql = f"LOWER({left}) = LOWER({right})"
    else:
        sql = f"{left} = {right}"
```

### File to Modify
- `fhir4ds/fhirpath/sql/translator.py`

### How to Find the Code
1. Search for `LIKE` in translator.py
2. Look for the operator translation section (around line 2000-3000)
3. Find where `~` or "equivalence" is handled

```bash
# Find the equivalence operator translation
grep -n "LIKE\|equivalen\|~" fhir4ds/fhirpath/sql/translator.py
```

---

## Implementation Steps

### Step 1: Locate the Code
1. Open `fhir4ds/fhirpath/sql/translator.py`
2. Search for where operators are translated to SQL
3. Find the section handling the `~` operator

**Validation:** You should find code that generates `LIKE` for the `~` operator.

### Step 2: Understand the Current Logic
1. Read the surrounding code to understand how operators are handled
2. Note what information is available (left operand, right operand, types)
3. Look at how `=` (equality) is implemented for reference

**Validation:** You can explain how the current operator translation works.

### Step 3: Implement the Fix
1. Replace the `LIKE` translation with proper equivalence logic
2. For strings: use `LOWER(left) = LOWER(right)` for case-insensitive comparison
3. For numbers/booleans: use simple `=` comparison

Example code structure:
```python
def _translate_equivalence_operator(self, left_expr, right_expr, left_type, right_type):
    """Translate FHIRPath ~ operator to SQL."""
    # String equivalence is case-insensitive
    if self._is_string_type(left_type) or self._is_string_type(right_type):
        return f"(LOWER(CAST({left_expr} AS VARCHAR)) = LOWER(CAST({right_expr} AS VARCHAR)))"

    # For other types, equivalence is equality
    return f"({left_expr} = {right_expr})"
```

**Validation:** Run the test `1 ~ 1` and verify it returns `true`.

### Step 4: Handle NULL Cases
FHIRPath equivalence has specific NULL handling:
- `null ~ null` returns `true` (both are empty)
- `1 ~ null` returns `false` (different)

```python
# Add NULL handling
if left_can_be_null or right_can_be_null:
    return f"""(
        CASE
            WHEN {left_expr} IS NULL AND {right_expr} IS NULL THEN true
            WHEN {left_expr} IS NULL OR {right_expr} IS NULL THEN false
            ELSE {equivalence_expression}
        END
    )"""
```

### Step 5: Test Your Changes
Run these tests to verify:
```bash
# Run equivalence-related compliance tests
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner('duckdb')
report = runner.run_official_tests()

# Filter for equivalence tests
for r in runner.test_results:
    if '~' in r.expression and not r.passed:
        print(f'FAIL: {r.expression[:50]}')
        print(f'      {r.actual_result}')
"
```

---

## Testing Strategy

### Unit Tests to Create
Create a new test file `tests/unit/fhirpath/sql/test_equivalence_operator.py`:

```python
import pytest
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect

@pytest.fixture
def executor():
    dialect = DuckDBDialect(database=":memory:")
    # Set up test data...
    return FHIRPathExecutor(dialect, "Patient")

def test_integer_equivalence(executor):
    result = executor.execute("1 ~ 1")
    assert result == [True]

def test_string_equivalence_case_insensitive(executor):
    result = executor.execute("'ABC' ~ 'abc'")
    assert result == [True]

def test_decimal_equivalence(executor):
    result = executor.execute("1.0 ~ 1.0")
    assert result == [True]
```

### Compliance Tests
Run the full compliance suite to measure improvement:
```bash
PYTHONPATH=. python3 -m pytest tests/compliance/fhirpath/ -v -k "equivalen" 2>/dev/null
```

---

## Common Pitfalls to Avoid

1. **Don't use LIKE for non-string comparisons** - LIKE is only for string pattern matching
2. **Remember case-insensitivity for strings** - `'A' ~ 'a'` must be true
3. **Handle NULL properly** - Check both operands for NULL
4. **Don't break equality (=)** - The `=` operator should still work as before
5. **Test with both DuckDB and PostgreSQL** - The LOWER() function works in both

---

## Resources

### FHIRPath Specification
- Equivalence: https://hl7.org/fhirpath/#equivalence

### Key Differences: Equivalence (~) vs Equality (=)
| Expression | Equality (=) | Equivalence (~) |
|------------|--------------|-----------------|
| `'A' = 'a'` | false | true |
| `1 = 1.0` | true | true |
| `{} = {}` | true | true |
| `(1\|2) = (2\|1)` | false | true |

---

## Progress Tracking

### Status
- [x] Completed - Ready for Final Merge

### Senior Review Finding (2025-12-27)
**BUG FOUND AND FIXED**: The `_is_string_operand()` method was updated to correctly detect string literals from `EnhancedASTNode` objects by checking the `text` attribute for quote-enclosed values.

**Fix Applied**:
- Added text-based string detection: checks if `ast_node.text` starts/ends with quotes
- Added recursive child checking for wrapper nodes like `TermExpression`
- Maintained backwards compatibility with `LiteralNode` and `FunctionCallNode`

**Verification Results** (8/8 tests pass):
- `'abc' ~ 'ABC'` returns `true` (case-insensitive)
- `'abc' !~ 'ABC'` returns `false` (case-insensitive)

### Completion Checklist
- [x] Located equivalence operator code in translator.py (line 2152, operator_map)
- [x] Understood current LIKE-based implementation
- [x] Implemented proper equivalence logic (`_generate_equivalence_sql` method)
- [x] Added NULL handling (CASE WHEN for null ~ null = true, value ~ null = false)
- [x] Code reviewed
- [x] **FIXED**: Updated `_is_string_operand()` for EnhancedASTNode string detection
- [x] Re-verified all 8 string equivalence tests pass

### Implementation Summary
**Changes Made:**
1. Updated `operator_map` to map `~` and `!~` to themselves (instead of LIKE/NOT LIKE)
2. Added `_is_string_operand()` helper to detect string type operands
3. Added `_generate_equivalence_sql()` method to handle equivalence logic:
   - For strings: case-insensitive comparison using `LOWER(CAST(...))`
   - For non-strings: simple equality comparison
   - Proper NULL handling: `null ~ null = true`, `value ~ null = false`
4. Modified comparison handling in `_translate_binary_operator()` to call `_generate_equivalence_sql()` for `~` and `!~` operators

**Files Modified:**
- `fhir4ds/fhirpath/sql/translator.py`

**Test Results:**
- SQL generation verified: integers use `=`, strings use `LOWER()` comparison
- NULL handling verified: `null ~ null = true`, `1 ~ null = false`
- 41/41 operator unit tests pass
- No regressions in existing tests

---

**Task Created**: 2025-12-11
**Status**: Completed and Merged to Main (2025-12-27)
**Branch**: feature/SP-022-002-fix-equivalence-operator (deleted after merge)
