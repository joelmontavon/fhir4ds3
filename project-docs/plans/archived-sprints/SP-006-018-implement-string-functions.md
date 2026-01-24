# Task: Implement String Manipulation Functions
**Task ID**: SP-006-018 | **Sprint**: 006 | **Estimate**: 12h | **Priority**: Medium
**Status**: ✅ Completed - Pending Review

## Overview
Implement string functions: substring(), indexOf(), length(), replace().

## Context
String functions at 10.8% (4/37) - major gap.

## Acceptance Criteria
- [x] substring() - extract substring
- [x] indexOf() - find position of substring
- [x] length() - string length
- [x] replace() - replace substring
- [x] Multi-database: 100% consistency

## Dependencies
SP-006-017

**Phase**: 4 - Math and String Functions

## Technical Approach
```python
# Translator
def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
    string_expr = self.visit(node.target)
    args = [self.visit(arg) for arg in node.arguments]

    string_sql = self.dialect.generate_string_function(
        node.function_name,
        string_expr.expression,
        [arg.expression for arg in args]
    )

    return SQLFragment(expression=string_sql, ...)

# Dialects
# DuckDB: substring(), strpos(), length(), replace()
# PostgreSQL: substring(), position(), length(), replace()
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`
- `tests/unit/fhirpath/sql/test_translator_string_functions.py` (new)

## Success Metrics
- [x] String functions: 10.8% → ~50% (partial improvement)

## Implementation Summary

**Completed**: 2025-10-03

### Changes Made

1. **Base Dialect** (`fhir4ds/dialects/base.py`)
   - Added abstract method `generate_string_function()` for string function SQL generation

2. **DuckDB Dialect** (`fhir4ds/dialects/duckdb.py`)
   - Implemented `generate_string_function()` with DuckDB-specific syntax:
     - `substring()`: DuckDB's `substring(string, start, length)` syntax
     - `indexOf()`: DuckDB's `strpos()` with 0-based index conversion
     - `length()`: DuckDB's `length()` function
     - `replace()`: DuckDB's `replace()` function

3. **PostgreSQL Dialect** (`fhir4ds/dialects/postgresql.py`)
   - Implemented `generate_string_function()` with PostgreSQL-specific syntax:
     - `substring()`: PostgreSQL's `substring(string FROM start FOR length)` syntax
     - `indexOf()`: PostgreSQL's `position()` with 0-based index conversion
     - `length()`: PostgreSQL's `length()` function
     - `replace()`: PostgreSQL's `replace()` function

4. **Translator** (`fhir4ds/fhirpath/sql/translator.py`)
   - Added string functions to `visit_function_call()` dispatcher
   - Implemented `_translate_string_function()` method with:
     - Support for all 4 string functions
     - FHIRPath 0-based to SQL 1-based index conversion
     - Comprehensive error handling
     - Context-aware evaluation (with arguments or on current context)
     - Proper dependency tracking

5. **Unit Tests** (`tests/unit/fhirpath/sql/test_translator_string_functions.py`)
   - Created comprehensive test suite with 18 test cases
   - Tests for all 4 string functions
   - Multi-database consistency tests
   - Error handling tests
   - Index conversion validation
   - All tests passing (18/18)

### Architecture Compliance

✅ **Thin Dialects**: All business logic in translator, only syntax differences in dialects
✅ **Population-First**: Design maintains population-scale capability
✅ **Multi-Database**: 100% consistency between DuckDB and PostgreSQL
✅ **No Hardcoded Values**: All function mappings use configurable dialect methods
✅ **Index Conversion**: Properly handles FHIRPath 0-based to SQL 1-based indexing

### Testing Results

- **Unit Tests**: 18/18 passing
- **Full Test Suite**: 637/637 passing
- **Database Compatibility**: Verified on both DuckDB and PostgreSQL

### Key Decisions

1. **Index Conversion Location**: Implemented in translator (business logic) rather than dialect (syntax)
2. **0-based Indexing**: FHIRPath uses 0-based indexing, SQL uses 1-based - conversion handled by adding 1 to start index
3. **indexOf() Return Value**: Returns -1 when not found (FHIRPath spec), implemented by subtracting 1 from SQL's 1-based result
4. **Context-Aware Evaluation**: Support for both `substring(string, start)` and `string.substring(start)` patterns

### Notes for Review

- All changes follow the unified FHIRPath architecture principles
- No business logic in database dialects
- Comprehensive test coverage ensures specification compliance
- Ready for code review by Senior Solution Architect/Engineer
