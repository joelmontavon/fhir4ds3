# Task: Implement select() and first() Functions
**Task ID**: SP-005-009 | **Sprint**: 005 | **Estimate**: 12h | **Priority**: High
**Status**: Completed

## Overview
Implement _translate_select() and _translate_first() methods for array transformation and access.

## Acceptance Criteria
- [x] select() translates correctly (array transformation)
- [x] first() uses [0] indexing (population-friendly, NOT LIMIT 1)
- [x] Both functions tested with 15+ tests (29 tests total)
- [x] Multi-database consistency validated

## Dependencies
SP-005-008

**Phase**: 3 - Complex Operations

## Implementation Summary

### Implementation Details

**1. `_translate_select()` Method** (lines 745-849 in translator.py):
- Translates select() function to SQL with LATERAL UNNEST and projection
- Uses array operations and aggregation to transform array elements
- Generates population-friendly SQL using GROUP BY with patient ID
- Maintains population-scale performance with CTE-based approach
- Updates context table to new CTE name for chaining

**Key Features**:
- Single argument validation (projection expression)
- Array unnesting with LATERAL keyword
- Database-specific aggregation via `dialect.aggregate_to_json_array()`
- Context management (saves/restores path state)
- Proper fragment metadata (requires_unnest=True, is_aggregate=True)

**2. `_translate_first()` Method** (lines 851-934 in translator.py):
- Translates first() function to SQL using array indexing [0]
- Population-friendly design using JSON path indexing, NOT LIMIT 1
- Operates at JSON level, no unnesting required
- Updates context path with [0] for subsequent operations

**Key Features**:
- Zero argument validation (first() takes no parameters)
- Array indexing via path manipulation (appends "[0]")
- No unnesting needed (operates at JSON path level)
- Maintains current table reference
- Proper fragment metadata (requires_unnest=False, is_aggregate=False)

### Tests Created

**File**: `tests/unit/fhirpath/sql/test_translator_select_first.py` (29 tests total)

**Test Classes**:
1. `TestSelectBasicTranslation` (8 tests)
   - Simple field projection
   - Nested field projection
   - Context table updates
   - Error handling (no args, multiple args)
   - Dependency tracking
   - Unique CTE name generation
   - Path management during translation

2. `TestSelectDialectConsistency` (3 tests)
   - DuckDB syntax validation
   - Multi-database metadata consistency
   - Parametrized testing across dialects

3. `TestFirstBasicTranslation` (9 tests)
   - Simple array access with [0] indexing
   - Population-friendly design validation (NO LIMIT 1)
   - Context path updates
   - Error handling (arguments not allowed)
   - Flag validation (no unnest, not aggregate)
   - No dependencies
   - Table reference maintenance
   - Nested path handling

4. `TestFirstDialectConsistency` (5 tests)
   - DuckDB syntax validation
   - Multi-database metadata consistency
   - Critical validation: NO LIMIT clause in any dialect
   - Parametrized testing across dialects

5. `TestSelectFirstChaining` (2 tests)
   - first() after path navigation
   - select() on simple arrays

6. `TestPopulationScaleValidation` (2 tests)
   - first() population-friendly design
   - select() population-friendly design

### Architectural Decisions

**1. Population-First Design**:
- `select()`: Uses GROUP BY with patient ID for population-scale aggregation
- `first()`: Uses JSON path [0] indexing, NOT LIMIT 1 row limitation
- Both maintain ability to process entire patient populations in single queries

**2. Context Management**:
- `select()`: Updates context.current_table to new CTE for chaining
- `first()`: Appends "[0]" to context.parent_path for subsequent operations
- Both save/restore context state during translation

**3. Thin Dialect Architecture**:
- Business logic in translator methods
- Only syntax differences in dialect methods
- Calls `dialect.unnest_json_array()` and `dialect.aggregate_to_json_array()`

### Test Results

All tests pass successfully:
- 29 tests in test_translator_select_first.py: ✅ PASSED
- 238 total SQL translator tests: ✅ PASSED
- Multi-database consistency validated: ✅ DuckDB and PostgreSQL

### Files Modified

1. `/mnt/d/fhir4ds2/fhir4ds/fhirpath/sql/translator.py`:
   - Added `_translate_select()` method (105 lines)
   - Added `_translate_first()` method (84 lines)
   - Updated `visit_function_call()` dispatcher

2. `/mnt/d/fhir4ds2/tests/unit/fhirpath/sql/test_translator_select_first.py`:
   - Created comprehensive test file with 29 tests

3. `/mnt/d/fhir4ds2/tests/unit/fhirpath/sql/test_translator.py`:
   - Fixed test to use `exists()` instead of `first()` (implementation complete)

## Progress Updates

| Date | Status | Progress | Blockers | Next Steps |
|------|--------|----------|----------|------------|
| 30-09-2025 | In Progress | Created feature branch | None | Implement select() and first() |
| 30-09-2025 | In Development | Implemented both methods | None | Write comprehensive tests |
| 30-09-2025 | In Testing | 29 tests written, all passing | None | Validate multi-database |
| 30-09-2025 | Completed | All tests pass, ready for review | None | Move to SP-005-010 |
