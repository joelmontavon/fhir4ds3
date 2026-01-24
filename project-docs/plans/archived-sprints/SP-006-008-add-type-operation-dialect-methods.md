# Task: Add Dialect Methods for Type Operations
**Task ID**: SP-006-008 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: High
**Status**: ✅ Completed - Pending Review

## Overview
Consolidate and test all type operation dialect methods for both DuckDB and PostgreSQL.

## Acceptance Criteria
- [x] All type dialect methods implemented
- [x] DuckDB and PostgreSQL: identical logic, different syntax
- [x] Helper methods for type mapping
- [x] Unit tests for dialect methods
- [x] Documentation complete

## Dependencies
SP-006-005, SP-006-006, SP-006-007

**Phase**: 2 - Type Functions

## Dialect Methods Required
1. `generate_type_check()` - for is()
2. `generate_type_cast()` - for as()
3. `generate_collection_type_filter()` - for ofType()
4. `_map_fhirpath_to_sql_type()` - helper for type mapping

## Files Modified
- `fhir4ds/dialects/base.py` - Already contains abstract method definitions
- `fhir4ds/dialects/duckdb.py` - Already contains implementations
- `fhir4ds/dialects/postgresql.py` - Already contains implementations
- `tests/unit/dialects/test_duckdb_dialect.py` - Added comprehensive type operation tests
- `tests/unit/dialects/test_postgresql_dialect.py` - Added comprehensive type operation tests

## Implementation Summary

### Type Operations Implemented
All three type operation methods are implemented in both DuckDB and PostgreSQL dialects:

1. **generate_type_check()** - Type checking for is() operation
   - DuckDB: Uses `typeof()` function
   - PostgreSQL: Uses `pg_typeof()::text IN (...)` pattern

2. **generate_type_cast()** - Type casting for as() operation
   - DuckDB: Uses `TRY_CAST()`
   - PostgreSQL: Uses `CASE` with regex validation for safe casting

3. **generate_collection_type_filter()** - Collection filtering for ofType() operation
   - DuckDB: Uses `list_filter()` with lambda
   - PostgreSQL: Uses `UNNEST` and `array_agg()` pattern

### Type Mapping
Both dialects include consistent type mapping from FHIRPath types to SQL types:
- String → VARCHAR (DuckDB) / TEXT (PostgreSQL)
- Integer → INTEGER
- Decimal → DOUBLE (DuckDB) / NUMERIC (PostgreSQL)
- Boolean → BOOLEAN
- DateTime → TIMESTAMP
- Date → DATE
- Time → TIME

### Test Coverage
Added 32 new tests per dialect (64 total):
- Type check tests for all supported types (7 types + unknown)
- Type cast tests for all supported types (7 types + unknown)
- Collection filter tests for all supported types (7 types + unknown)
- Type mapping consistency tests (parametrized, 7 types)

All 162 dialect tests pass successfully.

## Architectural Compliance
✅ Thin dialect architecture maintained - only syntax differences in implementations
✅ No business logic in dialect methods
✅ Type mapping is part of syntax adaptation
✅ Both databases tested and validated
