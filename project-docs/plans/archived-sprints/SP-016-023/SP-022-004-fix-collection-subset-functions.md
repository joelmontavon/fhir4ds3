# Task: Fix Collection Subset Functions (first, last, skip, take, tail)

**Task ID**: SP-022-004
**Sprint**: 022
**Task Name**: Fix FHIRPath Collection Subset Functions
**Assignee**: Junior Developer
**Created**: 2025-12-11
**Last Updated**: 2025-12-11

---

## Task Overview

### Description
The FHIRPath collection subset functions (`first()`, `last()`, `skip()`, `take()`, `tail()`) are not working correctly. They either produce JSON path errors or return wrong results. This causes ~25 compliance test failures.

**Current Behavior (WRONG):**
```sql
-- FHIRPath: Patient.name.given.first()
SELECT json_extract_string(resource, '$[0]')  -- Extracts from resource, not from given names!
-- Result: NULL (wrong path)
```

**Expected Behavior (CORRECT):**
```sql
-- FHIRPath: Patient.name.given.first()
-- After unnesting given names into rows, select the first row
SELECT given_item FROM cte_unnest ORDER BY row_order LIMIT 1
-- Result: 'Peter' (first given name)
```

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **first()**: `Patient.name.given.first()` returns the first given name ("Peter")
2. **last()**: `Patient.name.given.last()` returns the last given name
3. **skip(n)**: `Patient.name.skip(1)` skips the first name entry
4. **take(n)**: `Patient.name.take(2)` returns only the first 2 name entries
5. **tail()**: `Patient.name.tail()` returns all but the first entry (same as skip(1))

### Acceptance Criteria
- [ ] `Patient.name.given.first()` returns `'Peter'`
- [ ] `Patient.name.given.first() = 'Peter'` returns `true`
- [ ] `Patient.name.first().count() = 1` returns `true`
- [ ] `Patient.name.skip(1).given` returns the correct names
- [ ] All existing passing tests continue to pass

---

## Technical Specifications

### Root Cause Analysis
The translator is generating JSON path expressions for subset functions instead of SQL LIMIT/OFFSET:

```python
# Current (WRONG) - tries to use JSON path indexing
def _translate_first_function(self, node):
    return f"json_extract_string({expr}, '$[0]')"  # Wrong: extracts from wrong path
```

The issue is that `first()` should operate on the **result of the previous expression**, not go back to the original JSON.

### The Fix
When the input is an UNNESTED collection (multiple rows), use SQL row operations:

```python
# Correct approach - use SQL LIMIT/OFFSET
def _translate_first_function(self, node, input_fragment):
    if input_fragment.requires_unnest:
        # The collection is already unnested into rows
        # Select the first row using ordering
        return "SELECT ... FROM input_cte ORDER BY row_order LIMIT 1"
    else:
        # The collection is still JSON, use JSON indexing
        return f"json_extract({expr}, '$[0]')"
```

### Files to Modify
- `fhir4ds/fhirpath/sql/translator.py` - Fix function translation
- `fhir4ds/fhirpath/sql/cte.py` - May need to add row limiting CTEs

### How to Find the Code
```bash
# Find the first/last/skip/take translations
grep -n "_translate_first\|_translate_last\|_translate_skip\|_translate_take" \
    fhir4ds/fhirpath/sql/translator.py
```

---

## Implementation Steps

### Step 1: Understand the Problem
Run this test to see the current behavior:

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
    'name': [
        {'family': 'Chalmers', 'given': ['Peter', 'James']},
        {'family': 'Windsor', 'given': ['Jim']}
    ]
}

conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
conn.execute('INSERT INTO resource VALUES (1, ?)', [json.dumps(patient)])

executor = FHIRPathExecutor(dialect, 'Patient')
details = executor.execute_with_details('Patient.name.given.first()')

print('Generated SQL:')
print(details['sql'])
print()
print('Result:', details['results'])
"
```

### Step 2: Understand How UNNEST Works
After `Patient.name.given`, the CTE chain produces rows like:
```
id | resource | cte_1_order | cte_2_order | given_item
1  | {...}    | 1           | 1           | "Peter"
1  | {...}    | 1           | 2           | "James"
1  | {...}    | 2           | 1           | "Jim"
```

`first()` should return only the row where `cte_1_order = 1 AND cte_2_order = 1`.

### Step 3: Locate the Function Translation
1. Search for `first` in translator.py
2. Find the `_translate_first_function` or similar method
3. Understand how it currently generates SQL

### Step 4: Implement the Fix for first()
The key insight is that `first()` on an UNNESTED collection needs to:
1. Use the ordering columns (`cte_1_order`, `cte_2_order`)
2. Select only row(s) where all ordering columns = 1

```python
def _translate_first_function(self, node):
    # Get information about the input collection
    input_fragment, dependencies, _, snapshot, _, _ = self._resolve_function_target(node)

    # Check if we have ordering columns (indicates UNNEST occurred)
    ordering_columns = self._get_ordering_columns_from_context(snapshot)

    if ordering_columns:
        # Collection is unnested - use row filtering
        # Select rows where all ordering columns = 1
        where_clauses = [f"{col} = 1" for col in ordering_columns]
        filter_expr = " AND ".join(where_clauses)

        return SQLFragment(
            expression=input_fragment.expression,
            source_table=snapshot["current_table"],
            requires_unnest=False,
            metadata={
                "filter": filter_expr,
                "function": "first"
            }
        )
    else:
        # Collection is still JSON - use JSON indexing
        return SQLFragment(
            expression=f"json_extract({input_fragment.expression}, '$[0]')",
            source_table=snapshot["current_table"],
            requires_unnest=False
        )
```

### Step 5: Implement skip() and take()
Similar logic but with different row filtering:

```python
# skip(n): Select rows where ordering column > n
def _translate_skip_function(self, node, skip_count):
    filter_expr = f"{last_ordering_column} > {skip_count}"
    # ...

# take(n): Select rows where ordering column <= n
def _translate_take_function(self, node, take_count):
    filter_expr = f"{last_ordering_column} <= {take_count}"
    # ...
```

### Step 6: Handle first().count() Chaining
When `first()` is followed by `count()`, we need to ensure:
1. `first()` filters to one row
2. `count()` counts that one row

The aggregation fix from SP-022-001 should handle this if `first()` is implemented correctly.

---

## Testing Strategy

### Manual Tests
```bash
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect
import json

dialect = DuckDBDialect(database=':memory:')
conn = dialect.get_connection()

patient = {
    'resourceType': 'Patient', 'id': 'example',
    'name': [
        {'family': 'Chalmers', 'given': ['Peter', 'James']},
        {'family': 'Windsor', 'given': ['Jim']}
    ]
}
conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
conn.execute('INSERT INTO resource VALUES (1, ?)', [json.dumps(patient)])

executor = FHIRPathExecutor(dialect, 'Patient')

tests = [
    ('Patient.name.given.first()', 'Peter'),
    ('Patient.name.first().family', 'Chalmers'),
    ('Patient.name.skip(1).family', 'Windsor'),
]

for expr, expected in tests:
    try:
        result = executor.execute(expr)
        actual = result[0][-1] if result else None
        status = 'PASS' if str(actual) == expected else 'FAIL'
        print(f'{status}: {expr} = {actual} (expected {expected})')
    except Exception as e:
        print(f'ERROR: {expr} - {str(e)[:50]}')
"
```

### Unit Tests to Create
Create `tests/unit/fhirpath/sql/test_collection_subset.py`:

```python
class TestCollectionSubset:
    def test_first_returns_first_element(self, executor):
        result = executor.execute("Patient.name.given.first()")
        assert result[0][-1] == "Peter"

    def test_skip_skips_elements(self, executor):
        result = executor.execute("Patient.name.skip(1).family")
        assert result[0][-1] == "Windsor"

    def test_first_then_count(self, executor):
        result = executor.execute("Patient.name.first().count() = 1")
        assert result[0][-1] == True
```

---

## SQL Patterns Reference

### first() on Unnested Collection
```sql
-- Input CTE has: id, resource, cte_1_order, cte_2_order, item
-- first() should filter to first row
WITH cte_first AS (
    SELECT * FROM cte_input
    WHERE cte_1_order = 1 AND cte_2_order = 1
)
SELECT * FROM cte_first;
```

### skip(n) on Unnested Collection
```sql
-- skip(1) should exclude first row at each level
WITH cte_skip AS (
    SELECT * FROM cte_input
    WHERE cte_1_order > 1  -- Skip first at outer level
)
SELECT * FROM cte_skip;
```

### take(n) on Unnested Collection
```sql
-- take(2) should keep only first 2 rows
WITH cte_take AS (
    SELECT * FROM cte_input
    WHERE cte_1_order <= 2
)
SELECT * FROM cte_take;
```

---

## Common Pitfalls to Avoid

1. **Don't use JSON indexing on unnested data** - After UNNEST, data is in rows, not JSON
2. **Remember the ordering columns** - They're essential for correct first/last/skip
3. **Handle nested arrays** - `name.given` has two levels of unnesting
4. **Test function chaining** - `first().count()`, `skip(1).given`, etc.

---

## Progress Tracking

### Status
- [x] Completed and Merged to Main

### Completion Checklist
- [x] Understood how UNNEST and ordering columns work
- [x] Located first/last/skip/take translation code
- [x] Implemented first() using row filtering with subset_filter metadata
- [x] Implemented last() using correlated subquery for per-patient max
- [x] Implemented skip(n) and take(n) using ordering column filters
- [x] Implemented tail() as skip(1)
- [x] Fixed subsequent field access after subset functions (current_element_column)
- [x] Fixed population-first semantics (PARTITION BY patient id)
- [x] Tested function chaining scenarios
- [x] Verified no regressions (pre-existing test failures unrelated to changes)

---

## Implementation Summary

### Changes Made

**1. TranslationContext (`fhir4ds/fhirpath/sql/context.py`)**
- Added `current_element_column` field to track when field access should use the filtered result column
- Added `current_element_type` field for proper type resolution on extracted elements
- Updated `reset()` to clear these new fields

**2. Translator (`fhir4ds/fhirpath/sql/translator.py`)**
- Updated `_snapshot_context()` and `_restore_context()` to include new context fields
- Refactored `_translate_first()` to:
  - Check for UNNEST fragments and use row filtering with `subset_filter: "first"` metadata
  - Set `current_element_column = "result"` for subsequent field access
  - Clear parent_path since we're now at element level
- Refactored `_translate_last()` similarly with `subset_filter: "last"`
- Refactored `_translate_skip()` to use row filtering with `subset_filter: "skip"` and `subset_count`
- Refactored `_translate_take()` similarly with `subset_filter: "take"`
- Refactored `_translate_tail()` to use skip(1) logic
- Added handling in `visit_identifier()` to extract from `current_element_column` when set

**3. CTE Builder (`fhir4ds/fhirpath/sql/cte.py`)**
- Updated `_wrap_simple_query()` to pass source_table to `_build_subset_filter()`
- Updated `_build_subset_filter()` to:
  - Handle `first`, `last`, `skip`, `take` filter types
  - Use correlated subqueries for per-patient semantics in `last()`
  - Use `WHERE ordering_col = 1` for `first()`
  - Use `WHERE ordering_col > n` for `skip(n)`
  - Use `WHERE ordering_col <= n` for `take(n)`
- Fixed `_wrap_unnest_query()` to always partition ROW_NUMBER by patient id for population-first semantics

### Test Results
All key functionality tests pass:
- `Patient.name.first().family` → Chalmers (per patient)
- `Patient.name.last().family` → Windsor (per patient)
- `Patient.name.skip(1).family` → Windsor (skipped first)
- `Patient.name.take(1).family` → Chalmers (first only)
- `Patient.name.tail().family` → Windsor (skip 1)
- `Patient.name.given.first()` → Peter (first given per patient)
- `Patient.name.given.last()` → Jim/David (last given per patient)

---

**Task Created**: 2025-12-11
**Status**: Completed and Merged to Main
**Completed**: 2025-12-29
**Merged**: 2025-12-29
**Review**: See `project-docs/plans/reviews/SP-022-004-review.md`
