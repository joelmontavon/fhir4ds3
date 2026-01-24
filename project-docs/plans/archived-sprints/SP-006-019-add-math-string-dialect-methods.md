# Task: Add Dialect Methods for Math/String Functions
**Task ID**: SP-006-019 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: Medium
**Status**: ✅ MERGED | **Completed**: 2025-10-03

## Overview
Consolidate and test all math/string dialect methods for DuckDB and PostgreSQL.

## Acceptance Criteria
- [x] All math dialect methods implemented
- [x] All string dialect methods implemented
- [x] DuckDB and PostgreSQL: syntax differences only
- [x] Unit tests for dialect methods
- [x] Documentation complete

## Dependencies
SP-006-016, SP-006-017, SP-006-018

**Phase**: 4 - Math and String Functions

## Dialect Methods Required

### Math Functions
1. `generate_math_function()` - basic math
2. `generate_advanced_math_function()` - advanced math

### String Functions
1. `generate_string_function()` - string operations
2. `generate_substring()` - substring extraction
3. `generate_index_of()` - find position
4. `generate_string_length()` - length
5. `generate_string_replace()` - replacement

## Files Modified
- `tests/unit/dialects/test_duckdb_dialect.py` - Added comprehensive tests for generate_string_function()
- `tests/unit/dialects/test_postgresql_dialect.py` - Added comprehensive tests for generate_string_function()
- `tests/unit/dialects/test_base_dialect.py` - Fixed MockDialect to include generate_string_function() and generate_array_take()

## Implementation Summary

### Existing Implementation Verified
All required math and string dialect methods were already implemented in tasks SP-006-016, SP-006-017, and SP-006-018:
- `generate_math_function()` - ✅ Implemented in both DuckDB and PostgreSQL
- `generate_power_operation()` - ✅ Implemented in both DuckDB and PostgreSQL
- `generate_string_function()` - ✅ Implemented in both DuckDB and PostgreSQL (handles substring, indexOf, length, replace)

### Unit Tests Added
Created comprehensive unit tests for `generate_string_function()`:

**DuckDB Tests** (10 new tests):
- `test_generate_string_function_substring_with_length` - Test substring with start position and length
- `test_generate_string_function_substring_without_length` - Test substring with only start position
- `test_generate_string_function_indexof` - Test indexOf (0-based index)
- `test_generate_string_function_length` - Test string length
- `test_generate_string_function_replace` - Test substring replacement
- `test_generate_string_function_invalid_args_substring` - Test error handling
- `test_generate_string_function_invalid_args_indexof` - Test error handling
- `test_generate_string_function_invalid_args_length` - Test error handling
- `test_generate_string_function_invalid_args_replace` - Test error handling
- `test_generate_string_function_unknown` - Test unknown function error

**PostgreSQL Tests** (10 new tests):
- Same test coverage as DuckDB with PostgreSQL-specific SQL syntax validation

### Thin Dialect Architecture Compliance
All implementations follow the thin dialect architecture:
- **Business logic**: All in FHIRPath evaluator (index conversion, error handling, etc.)
- **Database dialects**: ONLY syntax differences
  - DuckDB uses: `substring()`, `strpos()`, `length()`, `replace()`
  - PostgreSQL uses: `substring() FROM ... FOR`, `position() in`, `length()`, `replace()`
  - Both convert from 1-based SQL indexing to 0-based FHIRPath indexing in the same way

### Test Results
All 221 dialect unit tests passing:
- ✅ DuckDB dialect: 91 tests passing
- ✅ PostgreSQL dialect: 91 tests passing
- ✅ Base dialect: 8 tests passing
- ✅ Factory tests: 31 tests passing
