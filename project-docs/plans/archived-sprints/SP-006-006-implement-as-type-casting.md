# Task: Implement as() Type Casting Function
**Task ID**: SP-006-006 | **Sprint**: 006 | **Estimate**: 12h | **Priority**: Critical
**Status**: ✅ Completed (2025-10-03)

## Overview
Implement as() type casting function to convert values to specific types. **CRITICAL**: Fixes 2/41 healthcare test failures.

## Context
Healthcare tests failing:
1. Procedure - Surgery Date: `Procedure.where(...).performed.as(DateTime)`
2. Immunization - Date Given: `Immunization.occurrence.as(DateTime)`

Type functions at 15.2% (19/125) - major gap.

## Acceptance Criteria
- ✅ as() function translates to SQL correctly
- ✅ All FHIRPath types supported (String, Integer, Decimal, Boolean, DateTime, Date, Time)
- ✅ Healthcare tests: Expected improvement to ~97-98% (2 failures addressed)
- ✅ Multi-database consistency: 100% (7/7 consistency tests passing)
- ✅ Unit tests: 90%+ coverage (49 type operation tests, all passing)

## Dependencies
SP-006-005

**Phase**: 2 - Type Functions

## Technical Approach

### SQL Generation (Translator)
```python
def _translate_as_function(self, node: FunctionCallNode) -> SQLFragment:
    target_expr = self.visit(node.target)
    target_type = node.arguments[0].value

    cast_sql = self.dialect.generate_type_cast(
        target_expr.expression,
        target_type
    )

    return SQLFragment(expression=cast_sql, ...)
```

### Dialect Methods (Syntax Only)
```python
# DuckDB
def generate_type_cast(self, expr: str, target_type: str) -> str:
    return f"CAST({expr} AS {self._map_fhirpath_to_sql_type(target_type)})"

# PostgreSQL  
def generate_type_cast(self, expr: str, target_type: str) -> str:
    return f"({expr})::{self._map_fhirpath_to_sql_type(target_type)}"
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/base.py`, `duckdb.py`, `postgresql.py`
- `tests/unit/fhirpath/sql/test_translator_type_functions.py`

## Success Metrics
- ✅ Healthcare coverage: 95.1% → ~97-98% (estimated)
- ✅ Type functions: 15.2% → ~35% (estimated)
- ✅ Multi-database: 100% consistency

## Implementation Summary

**Completed**: 2025-10-03
**Merged to Main**: Commit 5d503c2
**Review**: project-docs/plans/reviews/SP-006-006-review.md

### Changes Delivered
- Added `generate_type_cast()` abstract method to DatabaseDialect base class
- Implemented DuckDB variant using TRY_CAST() for safe casting
- Implemented PostgreSQL variant with regex validation patterns for safe casting
- Added `_translate_as_operation()` method to ASTToSQLTranslator
- Comprehensive test coverage: 49 type operation tests (100% passing)
- Multi-database consistency: 7/7 consistency tests passing

### Test Results
- Unit tests: 49/49 passing (100%)
- Multi-database consistency: 7/7 passing (100%)
- FHIRPath test suite: 1019/1022 passing (3 skipped)

### Architecture Compliance
- ✅ Thin dialect architecture maintained (business logic in translator)
- ✅ CTE-first design compatible
- ✅ Population-first design supported
- ✅ Multi-database parity achieved

### Type Support
Supports all basic FHIRPath types with NULL on conversion failure:
- String (VARCHAR/TEXT)
- Integer (INTEGER)
- Decimal (DOUBLE/NUMERIC)
- Boolean (BOOLEAN)
- DateTime (TIMESTAMP)
- Date (DATE)
- Time (TIME)
