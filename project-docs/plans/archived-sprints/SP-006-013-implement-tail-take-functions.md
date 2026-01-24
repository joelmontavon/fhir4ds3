# Task: Implement tail() and take() Functions
**Task ID**: SP-006-013 | **Sprint**: 006 | **Estimate**: 10h | **Priority**: Medium
**Status**: ✅ Completed

## Overview
Implement tail() (all but first) and take() (first N elements) collection functions.

## Acceptance Criteria
- [x] tail() returns all elements except first
- [x] take(n) returns first n elements
- [x] Handle edge cases
- [x] Multi-database: 100% consistency

## Dependencies
SP-006-012

**Phase**: 3 - Collection Functions

## Technical Approach
```python
# tail() is equivalent to skip(1)
# take() is opposite of skip()

def _translate_tail_function(self, node: FunctionCallNode) -> SQLFragment:
    # Reuse skip(1) logic
    return self._translate_skip_function_with_count(node, 1)

def _translate_take_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)
    take_count = self.visit(node.arguments[0])

    take_sql = self.dialect.generate_collection_take(
        collection_expr.expression,
        take_count.expression
    )

    return SQLFragment(expression=take_sql, ...)
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`

## Success Metrics
- [x] Collection functions: ~55% → ~65%

## Implementation Summary

### Changes Made
1. **Translator Functions** (`fhir4ds/fhirpath/sql/translator.py`):
   - Added `_translate_tail()` function that delegates to `skip(1)` for code reuse
   - Added `_translate_take()` function with array slicing logic
   - Registered both functions in `visit_function_call()` dispatch

2. **Dialect Methods**:
   - Added `generate_array_take()` abstract method to `DatabaseDialect` (`fhir4ds/dialects/base.py`)
   - Implemented DuckDB version using `list_slice(array, 1, take_count)` (`fhir4ds/dialects/duckdb.py`)
   - Implemented PostgreSQL version using `jsonb_array_elements` + `row_number()` filtering (`fhir4ds/dialects/postgresql.py`)

3. **Test Coverage**:
   - Created comprehensive test suite for `tail()`: 15 tests covering basic translation, error handling, context preservation, dialect consistency, equivalence to skip(1), population-scale patterns, and fragment properties
   - Created comprehensive test suite for `take()`: 19 tests covering basic translation, edge cases, error handling, context preservation, dialect consistency, population-scale patterns, fragment properties, and complementary relationship with skip()
   - All 51 collection slicing tests (skip, tail, take) pass in both DuckDB and PostgreSQL

### Design Decisions
1. **tail() as skip(1)**: Implemented tail() by creating a synthetic skip(1) call, maximizing code reuse and ensuring consistent behavior
2. **Population-First**: Both functions use array slicing operations (not LIMIT/OFFSET) to maintain population-scale capability
3. **Thin Dialects**: All business logic in translator, only SQL syntax differences in dialect methods
4. **Edge Case Handling**: Both functions handle edge cases (negative counts, zero counts, counts exceeding array length) via CASE statements in dialect implementations

### Files Modified
- `fhir4ds/fhirpath/sql/translator.py` (+173 lines)
- `fhir4ds/dialects/base.py` (+33 lines)
- `fhir4ds/dialects/duckdb.py` (+25 lines)
- `fhir4ds/dialects/postgresql.py` (+35 lines)

### Files Created
- `tests/unit/fhirpath/sql/test_translator_tail.py` (378 lines, 15 tests)
- `tests/unit/fhirpath/sql/test_translator_take.py` (567 lines, 19 tests)

### Test Results
- All 51 collection slicing tests pass (skip: 17, tail: 15, take: 19)
- 100% multi-database consistency between DuckDB and PostgreSQL
- No regressions in existing test suite (2696 tests still passing)

**Completed**: 2025-10-03
