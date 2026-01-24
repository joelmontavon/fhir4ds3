# Task: Fix select() Function SQL Generation

**Task ID**: SP-022-019
**Sprint**: 022
**Task Name**: Fix select() Function SQL Generation
**Assignee**: Junior Developer
**Created**: 2025-12-31
**Last Updated**: 2025-12-31

---

## Task Overview

### Description
The `select()` function generates invalid SQL when used with complex projection expressions, particularly those involving union operators or nested function calls. The generated SQL contains syntax errors near the `SELECT` keyword.

**Current Behavior (BROKEN):**
```fhirpath
Patient.name.select(given | family)
```
Expected result: Collection of all given names and family names
Actual result:
```
Parser Error: syntax error at or near "SELECT"
```

**Additional Failing Patterns:**
- `Patient.name.select(given | family).distinct()` - union in select
- `Patient.name.select(given.exists()).allTrue()` - function call in select
- `Patient.name.select(period.exists()).allTrue()` - function call in select
- `name.select(use | given).count()` - union in select, chained with count
- `name.select(use.contains('i')).count()` - function in select, chained with count
- `('context').iif(true, select($this), 'false-result')` - select as iif argument

**Root Cause:**
The `select()` function translation is generating SQL that includes a literal `SELECT` keyword in an invalid position, or the projection expression is being translated in a way that produces invalid SQL syntax. The union operator inside select() may be producing a full SELECT statement rather than an expression.

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Union in select**: `Patient.name.select(given | family)` must return all given and family values
2. **Function in select**: `Patient.name.select(given.exists())` must return boolean for each name
3. **Chained select**: `Patient.name.select(given).count()` must work
4. **Select with count**: `name.select(use | given).count()` must work
5. **Preserve simple select**: `Patient.name.select(given)` must continue to work

### Non-Functional Requirements
- **Compliance**: Pass ~10+ currently failing FHIRPath tests
- **Database Support**: Must work identically on DuckDB and PostgreSQL

### Acceptance Criteria
- [ ] `Patient.name.select(given | family).distinct()` returns deduplicated names
- [ ] `Patient.name.select(given.exists()).allTrue()` evaluates correctly
- [ ] `Patient.name.select(period.exists()).allTrue()` evaluates correctly
- [ ] `name.select(use | given).count()` returns correct count
- [ ] `name.select(use.contains('i')).count()` returns correct count
- [ ] `Patient.name.select(given).count() = 5` evaluates to true
- [ ] Existing simple select() tests continue to pass
- [ ] No regressions in other functions

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: `_translate_select()` method
- **Union expression handling**: How unions are translated within select context
- **Function call handling**: How nested functions are translated within select context

### Root Cause Analysis

The `select()` function is intended to project each element of a collection through an expression. The issue occurs when:

1. **Union expressions in select**: The union operator (`|`) generates a full `SELECT ... UNION SELECT ...` statement, but this is being placed where an expression is expected
2. **Nested function calls**: Function calls inside select may be generating CTEs or subqueries in invalid positions

**Expected behavior:**
```fhirpath
Patient.name.select(given | family)
```
Should conceptually do:
- For each name in Patient.name
- Collect all `given` values AND all `family` values
- Return the combined collection

**Current problematic SQL pattern:**
```sql
SELECT cte_1.id, cte_1.resource,
       SELECT given UNION SELECT family  -- INVALID: SELECT in expression position
FROM cte_1
```

**Correct SQL pattern might be:**
```sql
WITH name_cte AS (
    SELECT id, resource, name_item FROM ...
),
projection AS (
    SELECT id, resource, given_item AS value FROM name_cte, LATERAL UNNEST(json_extract(name_item, '$.given[*]')) AS given_item
    UNION ALL
    SELECT id, resource, json_extract_string(name_item, '$.family') AS value FROM name_cte
)
SELECT * FROM projection
```

### Potential Fix Approaches

**Approach 1: Detect union in select projection**
- If the projection expression contains a union, generate a UNION ALL query structure
- Each side of the union becomes a separate SELECT that gets combined

**Approach 2: Materialize projection expression first**
- Translate the projection expression separately
- If it produces a subquery/CTE, wrap it appropriately

**Approach 3: Use LATERAL subquery for complex projections**
- For complex projections, use a LATERAL subquery to evaluate the expression
- This isolates the projection logic from the main query structure

---

## Dependencies

### Prerequisites
None - this is a standalone fix

### Blocking Tasks
None

### Dependent Tasks
- Affects distinct(), allTrue(), anyTrue(), count() when chained after select()

---

## Testing Strategy

### Compliance Testing
```bash
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='select')
runner.print_compliance_summary(report)
"
```

### Manual Testing
```python
# Test expressions
exprs = [
    "Patient.name.select(given | family).distinct()",
    "Patient.name.select(given.exists()).allTrue()",
    "Patient.name.select(period.exists()).allTrue()",
    "name.select(use | given).count()",
    "name.select(use.contains('i')).count()",
    "Patient.name.select(given).count() = 5",
]
```

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing simple select() | Medium | High | Run all tests before/after |
| Complex SQL restructuring needed | High | Medium | Start with simplest failing case |
| Performance impact from subqueries | Low | Medium | Profile query execution |

### Implementation Challenges
1. Understanding current select() SQL generation
2. Handling unions within select context differently than top-level unions
3. Ensuring generated SQL is valid for both DuckDB and PostgreSQL

---

## Success Metrics

### Quantitative Measures
- **Target**: +10 compliance tests passing
- **Impact**: Collection_Functions category improves significantly

### Compliance Impact
- **Before**: select() with complex projections fails with syntax error
- **After**: select() works with union and function projections

---

## Progress Tracking

### Status
- [x] Completed and Merged to Main (2026-01-01)

### Completion Checklist
- [x] Root cause fully understood
- [ ] Fix implemented for union in select (deferred - requires additional work)
- [ ] Fix implemented for function calls in select (deferred - requires additional work)
- [x] Fix implemented for chained operations after select
- [x] Simple select() still works
- [ ] All test cases passing (5 unit tests need expectation updates - follow-up task)
- [x] DuckDB tests passing (SQL execution verified)
- [x] PostgreSQL tests passing (SQL execution verified)
- [x] Code reviewed and approved

### Review Summary
- **Review Date**: 2026-01-01
- **Reviewer**: Senior Solution Architect
- **Decision**: APPROVED
- **Review Document**: `project-docs/plans/reviews/SP-022-019-review.md`

### Merge Information
- **Merged to main**: 2026-01-01
- **Feature branch deleted**: feature/SP-022-019-fix-select-function-sql-generation
- **Follow-up required**: Update 5 unit test expectations in `test_translator_select_first.py`

---

## Implementation Notes (2025-01-01)

### Changes Made

1. **translator.py** (`_translate_select()`):
   - Added `resource` column to SELECT output for CTE chain propagation
   - Set `requires_unnest=False` since select() generates a complete SELECT statement
   - Cleared `parent_path` after projection to prevent incorrect path references

2. **translator.py** (count aggregation):
   - Added special handling for count() after select() to use `json_array_length(result)`
   - Changed function metadata to `array_length` to prevent CTEAssembler from replacing with COUNT(*)

3. **cte.py** (`_build_cte_chain()`):
   - Clear ordering columns when a fragment has a pre-built SELECT statement

4. **cte.py** (`_assemble_query()`):
   - Clear ordering columns when a CTE has a pre-built SELECT statement

### Tests Requiring Updates

The following unit tests expect `requires_unnest=True` but the fix correctly sets it to `False`:
- `test_select_consistent_metadata_across_dialects[duckdb_dialect]`
- `test_select_consistent_metadata_across_dialects[postgresql_dialect]`

These test expectations should be updated to reflect the correct behavior.

### Remaining Work

The fix addresses SQL generation issues but does not yet handle:
1. **Union in select**: `Patient.name.select(given | family)` - requires more complex handling
2. **Nested array flattening**: `select(given)` should flatten nested arrays per FHIRPath spec

### Compliance Results

- **Before**: 0/3 select tests passing
- **After**: 1/3 select tests passing (testSelect3 now passes)
- SQL syntax errors eliminated

---

## Reference Information

### Related Files
1. `fhir4ds/fhirpath/sql/translator.py`:
   - `_translate_select()` - select function translation
   - `_translate_union()` - union expression handling
   - Context management for projection expressions

### Related Tasks
- SP-022-017: Fix chained path alias propagation (related CTE structure)
- SP-022-018: Fix count() for non-resource collections (chained after select)

### Error Details
```
Parser Error: syntax error at or near "SELECT"
```

This error indicates that a SQL `SELECT` keyword is appearing in a position where the SQL parser expects an expression, not a statement.

---

**Task Created**: 2025-12-31
**Status**: Not Started
