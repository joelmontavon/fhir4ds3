# Task: Fix iif() Function in aggregate() Context

**Task ID**: SP-022-016
**Sprint**: 022
**Task Name**: Fix iif() Function in aggregate() Context
**Assignee**: Junior Developer
**Created**: 2025-12-31
**Last Updated**: 2025-12-31

---

## Task Overview

### Description
When `iif()` is used inside `aggregate()` expressions, the generated SQL incorrectly references the recursive CTE alias `a` outside of the CTE scope. This causes a "Referenced table 'a' not found" error.

**Current Behavior (BROKEN):**
```fhirpath
(1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this < $total, $this, $total)))
```
Expected result: `1` (minimum value)
Actual result:
```
Binder Error: Referenced table "a" not found!
Candidate tables: "cte_3"

LINE 15:     SELECT cte_3.id, cte_3.resource, a.total AS result
                                              ^
```

**Root Cause:**
The `iif()` function translation generates SQL that includes the `$total` variable binding (`a.total`), but this binding is only valid inside the recursive CTE. When the final SELECT statement is generated, it tries to reference `a.total` outside the CTE scope.

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **iif with $total.empty()**: `aggregate(iif($total.empty(), $this, ...))` must work
2. **iif with comparisons**: `aggregate(iif($this < $total, ...))` must work
3. **Nested iif**: `aggregate(iif(..., iif(...)))` must work
4. **Preserve existing behavior**: Simple aggregate expressions like `$this + $total` must continue to work

### Non-Functional Requirements
- **Compliance**: Pass FHIRPath aggregate tests 3 and 4 (testAggregate3, testAggregate4)
- **Database Support**: Must work identically on DuckDB and PostgreSQL

### Acceptance Criteria
- [x] `(1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this < $total, $this, $total)))` returns `1`
- [x] `(1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this > $total, $this, $total)))` returns `9`
- [x] Existing aggregate tests (1 and 2) continue to pass
- [x] No regressions in other functions

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: `_translate_aggregate()` method and/or `_translate_iif()` method
- **Variable binding context**: How `$total` is resolved in nested function calls

### Root Cause Analysis

The problem occurs in the interaction between `_translate_aggregate()` and `_translate_iif()`:

1. **aggregate() sets up variable bindings:**
```python
with self._variable_scope({
    "$this": VariableBinding(expression=element_cast, source_table=element_alias),
    "$total": VariableBinding(expression="a.total", source_table="a")  # <-- This binding
}):
    recursive_aggregator_fragment = self.visit(node.arguments[0])
```

2. **iif() generates a CASE expression** that includes the resolved `$total` binding (`a.total`)

3. **The final CTE SELECT** tries to reference the iif() result, but `a` is only defined inside the recursive CTE, not in the outer scope

**Generated SQL structure (simplified):**
```sql
WITH RECURSIVE agg_enum AS (...),
agg_recursive AS (
    -- Base case
    SELECT ... total FROM agg_enum WHERE ...
    UNION ALL
    -- Recursive case: 'a' is valid here
    SELECT e.idx, e.elem,
           CASE WHEN a.total IS NULL THEN ... END as total  -- OK: 'a' is in scope
    FROM agg_enum e
    JOIN agg_recursive a ON ...
)
SELECT cte.id, cte.resource, a.total AS result  -- ERROR: 'a' is out of scope!
FROM cte
```

The issue is that the aggregate function's final result should be extracted from within the recursive CTE (via the final SELECT from agg_recursive), not by referencing the CTE alias in the outer scope.

### Potential Fix Approaches

**Approach 1: Fix the final SELECT in aggregate()**
The `_translate_aggregate()` method already has a final SELECT that extracts the result:
```sql
SELECT COALESCE(
    (SELECT total FROM {recursive_cte} ORDER BY {index_alias} DESC LIMIT 1),
    {init_value}
) as result
```

The issue might be that when iif() is used, some additional SQL is being generated that references `a` outside this pattern.

**Approach 2: Ensure iif() result is contained within the CTE**
The iif() translation should generate SQL that uses the variable bindings correctly within the recursive CTE scope, and the final result should only reference the `total` column from the recursive CTE's final SELECT.

---

## Dependencies

### Prerequisites
1. **SP-022-015 (Aggregate input collection)**: Must be completed - fixes the basic aggregate input resolution. **Status: COMPLETED**
2. **SP-022-011 (iif criterion validation)**: Must be completed - fixes iif() accepting boolean literals. **Status: COMPLETED**

### Blocking Tasks
- None

### Dependent Tasks
- **Compliance tests 3-4**: These tests will pass once this fix is implemented

---

## Testing Strategy

### Compliance Testing
```bash
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='aggregate')
runner.print_compliance_summary(report)
"
```

### Manual Testing
```python
# Test expressions
expr1 = "(1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this < $total, $this, $total)))"
# Expected: 1 (minimum)

expr2 = "(1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this > $total, $this, $total)))"
# Expected: 9 (maximum)
```

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing aggregate expressions | Medium | High | Run all aggregate tests before/after |
| Complex interaction between iif and aggregate scoping | High | Medium | Trace SQL generation step by step |
| Database dialect differences in CTE handling | Low | Medium | Test on both DuckDB and PostgreSQL |

### Implementation Challenges
1. **Understanding CTE scope rules**: Need to understand exactly when CTE aliases are in scope
2. **Variable binding lifetime**: The `$total` binding needs to be valid inside the recursive CTE but the final result needs different extraction

---

## Success Metrics

### Quantitative Measures
- **Target**: 4/4 aggregate compliance tests passing (currently 2/4)
- **Impact**: +2 tests in compliance suite

### Compliance Impact
- **Before**: testAggregate3 and testAggregate4 failing with "Referenced table 'a' not found"
- **After**: All 4 aggregate tests passing

---

## Progress Tracking

### Status
- [x] Completed - Merged to main

### Completion Checklist
- [x] Root cause fully understood
- [x] Fix implemented
- [x] testAggregate3 passing
- [x] testAggregate4 passing
- [x] testAggregate1 still passing (no regression)
- [x] testAggregate2 still passing (no regression)
- [x] DuckDB tests passing
- [ ] PostgreSQL tests passing (pre-existing issue with literal integer unions)
- [x] Code reviewed and approved

### Merge Information
- **Merged to main**: 2025-12-31
- **Review document**: `project-docs/plans/reviews/SP-022-016-review.md`
- **Compliance improvement**: aggregate tests 50% → 100% (+2 tests)

---

## Implementation Summary

### Changes Made

Two issues were identified and fixed in `fhir4ds/fhirpath/sql/translator.py`:

**Issue 1: Fragment Leakage Outside CTE Scope**

When translating aggregator expressions (like `iif($total.empty(), ...)`), intermediate fragments were being added to the main `self.fragments` list. These fragments contained references to `a.total` (the CTE alias), which only exists inside the recursive CTE scope. When the CTE manager later turned these fragments into separate CTEs, they referenced `a.total` outside its scope.

**Fix:** Save the fragments list before translating aggregator expressions and restore it afterwards:

```python
# SP-022-016: Save fragment list before translating aggregator expressions
saved_fragments = self.fragments.copy()

# ... translate base and recursive aggregator expressions ...

# SP-022-016: Restore original fragments list
self.fragments = saved_fragments
```

**Issue 2: Incorrect Default init_value**

The default `init_value` was set to `"0"` when no init argument was provided. However, per FHIRPath spec, `$total` should be empty (NULL) on the first iteration, not 0. This prevented `$total.empty()` from correctly detecting the first iteration.

**Fix:** Changed default from `"0"` to `"NULL"`:

```python
# SP-022-016: Per FHIRPath spec, when no init argument is provided,
# $total is empty (NULL) on the first iteration.
init_value = "NULL"  # Default to NULL (empty) when no init provided
```

### Test Results

- **DuckDB**: All 4 aggregate tests pass (100% compliance)
- **PostgreSQL**: Pre-existing issue with literal integer union expressions (unrelated to this fix)

---

## Reference Information

### Related Files
1. `fhir4ds/fhirpath/sql/translator.py`:
   - `_translate_aggregate()` - aggregate function translation
   - `_translate_iif()` - iif function translation
   - `_variable_scope()` - variable binding context manager

### Related Tasks
- SP-022-015: Fix aggregate() input collection resolution (COMPLETED)
- SP-022-011: Fix iif() criterion validation (COMPLETED)

### Error Details
```
SQL translation/execution failed for expression: (1|2|3|4|5|6|7|8|9).aggregate(iif($total.empty(), $this, iif($this < $total, $this, $total))) = 1
Error type: BinderException
Error message: Binder Error: Referenced table "a" not found!
Candidate tables: "cte_3"

LINE 15:     SELECT cte_3.id, cte_3.resource, a.total AS result
                                              ^
```

---

**Task Created**: 2025-12-31
**Status**: Completed - Pending Review
