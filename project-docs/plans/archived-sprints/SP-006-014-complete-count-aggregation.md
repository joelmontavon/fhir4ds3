# Task: Complete count() Aggregation Function
**Task ID**: SP-006-014 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: High
**Status**: ✅ Completed

## Overview
Complete count() aggregation function implementation (currently partial from SP-005-011).

## Context
count() partially implemented in Sprint 005 but needs completion for all edge cases and collection scenarios.

## Acceptance Criteria
- [x] count() returns collection length
- [x] count() works on all collection types
- [x] Handles empty collections (returns 0)
- [x] Handles null (returns 0)
- [x] Multi-database: 100% consistency

## Dependencies
SP-006-013

**Phase**: 3 - Collection Functions

## Technical Approach
```python
# Extend existing count() implementation
def _translate_count_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)

    count_sql = self.dialect.generate_count_aggregation(
        collection_expr.expression
    )

    return SQLFragment(expression=count_sql, ...)

# Dialects
# DuckDB: json_array_length() or COUNT(*)
# PostgreSQL: jsonb_array_length() or COUNT(*)
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py` (extend existing)
- `fhir4ds/dialects/*.py` (verify/extend)
- `tests/unit/fhirpath/sql/test_translator_aggregation.py` (extend)

## Success Metrics
- [x] Collection functions: ~65% → ~70%+
- [x] All aggregation unit tests passing (29/29)
- [x] SQL translator unit tests passing (569/569)
- [x] Zero regressions

## Implementation Summary

### Changes Made

1. **Fixed Hardcoded Dialect Method** (translator.py:796-823)
   - Changed from hardcoded `json_array_length()` to `dialect.get_json_array_length()`
   - Ensures proper multi-database support (DuckDB vs PostgreSQL)
   - Follows thin dialect principle: business logic in translator, syntax in dialects

2. **Added Null/Empty Handling** (translator.py:808)
   - Added `COALESCE(array_length_expr, 0)` wrapper
   - Ensures FHIRPath spec compliance: "Returns 0 when the input collection is empty"
   - Handles null values gracefully

3. **Enhanced Test Coverage** (test_translator_aggregation.py:143-235)
   - Added `test_count_handles_null_with_coalesce_duckdb()`
   - Added `test_count_handles_null_with_coalesce_postgresql()`
   - Added `test_count_uses_dialect_method_duckdb()`
   - Added `test_count_uses_dialect_method_postgresql()`
   - Total count tests: 4 → 8 tests
   - All edge cases now covered

### Technical Details

**Before:**
```python
sql_expr = f"json_array_length({array_expr})"  # Hardcoded, no null handling
```

**After:**
```python
array_length_expr = self.dialect.get_json_array_length(
    column=self.context.current_table,
    path=json_path
)
sql_expr = f"COALESCE({array_length_expr}, 0)"  # Dialect method, null-safe
```

### Files Modified
- `fhir4ds/fhirpath/sql/translator.py` - Fixed count() implementation
- `tests/unit/fhirpath/sql/test_translator_aggregation.py` - Added 4 new tests

### Test Results
- **Aggregation tests**: 29/29 passed (100%)
- **SQL translator tests**: 569/569 passed (100%)
- **PostgreSQL compatibility**: ✅ Verified
- **DuckDB compatibility**: ✅ Verified

### Architectural Compliance
✅ **Thin Dialect Principle**: Uses dialect method, no hardcoded SQL
✅ **Population-First Design**: Maintains population-scale capability
✅ **FHIRPath Specification**: Returns 0 for empty/null per spec
✅ **Multi-Database Support**: 100% consistency across DuckDB and PostgreSQL

## Completion Date
2025-10-03

## Senior Review
**Review Date**: 2025-10-03
**Status**: ✅ APPROVED AND MERGED TO MAIN
**Review Document**: `project-docs/plans/reviews/SP-006-014-review.md`

### Review Summary
- **Architecture Compliance**: EXCELLENT - Perfect thin dialect implementation
- **Code Quality**: EXCELLENT - Clean, well-documented, spec-compliant
- **Test Coverage**: EXCELLENT - 100% for count(), 29/29 aggregation tests passing
- **Multi-Database**: EXCELLENT - 100% consistency DuckDB/PostgreSQL
- **FHIRPath Spec Compliance**: 100% - Returns 0 for empty/null per specification

**Merged to main**: 2025-10-03
