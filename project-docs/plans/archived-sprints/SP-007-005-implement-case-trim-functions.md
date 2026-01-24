# Task: Implement upper(), lower(), and trim() Functions

**Task ID**: SP-007-005 | **Sprint**: 007 | **Estimate**: 6h | **Priority**: Medium
**Status**: ✅ Merged to Main
**Phase**: 1 - High-Value String Functions (Week 1)
**Completed**: 2025-10-07
**Merged**: 2025-10-07
**Senior Review**: ✅ Approved (see project-docs/plans/reviews/SP-007-005-review.md)

---

## Overview

Implement three fundamental string transformation functions: `upper()` for uppercase conversion, `lower()` for lowercase conversion, and `trim()` for whitespace removal.

## FHIRPath Specification

### upper() Function

**Signature**: `upper() : String`
**Description**: Converts string to uppercase
**Example**: `'hello'.upper()` → `'HELLO'`

### lower() Function

**Signature**: `lower() : String`
**Description**: Converts string to lowercase
**Example**: `'HELLO'.lower()` → `'hello'`

### trim() Function

**Signature**: `trim() : String`
**Description**: Removes leading and trailing whitespace
**Example**: `'  hello  '.trim()` → `'hello'`

## Technical Approach

### Translator Implementation

```python
def _translate_upper(self, node: FunctionCallNode) -> SQLFragment:
    """Translate upper() to SQL UPPER() function."""
    # No arguments validation
    if len(node.arguments) != 0:
        raise ValueError("upper() takes no arguments")

    target_expr = ...
    upper_sql = self.dialect.generate_case_conversion(target_expr, 'upper')
    return SQLFragment(...)

def _translate_lower(self, node: FunctionCallNode) -> SQLFragment:
    """Translate lower() to SQL LOWER() function."""
    ...

def _translate_trim(self, node: FunctionCallNode) -> SQLFragment:
    """Translate trim() to SQL TRIM() function."""
    ...
```

### Dialect Methods

```python
# Base Dialect
@abstractmethod
def generate_case_conversion(self, string_expr: str, case_type: str) -> str:
    """Generate SQL for case conversion (upper/lower)."""
    pass

@abstractmethod
def generate_trim(self, string_expr: str) -> str:
    """Generate SQL for whitespace trimming."""
    pass

# DuckDB/PostgreSQL (standard SQL)
def generate_case_conversion(self, string_expr: str, case_type: str) -> str:
    if case_type == 'upper':
        return f"UPPER({string_expr})"
    elif case_type == 'lower':
        return f"LOWER({string_expr})"

def generate_trim(self, string_expr: str) -> str:
    return f"TRIM({string_expr})"
```

## Implementation Steps

1. **Add three functions to translator** (2h)
2. **Dialect methods** (1.5h): Both methods for both dialects
3. **Unit tests** (2h): 15+ tests for all three functions
4. **Integration** (0.5h): +5-6 tests expected

## Acceptance Criteria

- [x] upper() translates to UPPER()
- [x] lower() translates to LOWER()
- [x] trim() translates to TRIM()
- [x] NULL handling correct for all
- [x] Multi-database: 100% consistency
- [x] Unit tests: 90%+ coverage

## Files to Modify

1. `fhir4ds/fhirpath/sql/translator.py` - All three functions
2. `fhir4ds/dialects/base.py` - Both abstract methods
3. `fhir4ds/dialects/duckdb.py` - Both implementations
4. `fhir4ds/dialects/postgresql.py` - Both implementations
5. `tests/unit/fhirpath/sql/test_translator_case_trim.py`

---

## Completion Summary

**Implementation completed**: 2025-10-07

### Changes Made:
1. Added abstract methods to base dialect:
   - `generate_case_conversion(string_expr, case_type)` - Handles upper/lower conversions
   - `generate_trim(string_expr)` - Handles whitespace trimming

2. Implemented dialect methods for both DuckDB and PostgreSQL:
   - Both use standard SQL UPPER(), LOWER(), and TRIM() functions
   - 100% consistency across databases (no syntax differences)

3. Added translator methods:
   - `_translate_upper(node)` - Converts strings to uppercase
   - `_translate_lower(node)` - Converts strings to lowercase
   - `_translate_trim(node)` - Removes leading/trailing whitespace
   - All methods validate that no arguments are passed

4. Created comprehensive unit tests:
   - 21 tests covering all three functions
   - Multi-database consistency validation
   - Error handling for invalid arguments
   - Context handling verification
   - All tests passing (100% success rate)

### Files Modified:
- `fhir4ds/dialects/base.py` - Added 2 abstract methods
- `fhir4ds/dialects/duckdb.py` - Implemented 2 methods
- `fhir4ds/dialects/postgresql.py` - Implemented 2 methods
- `fhir4ds/fhirpath/sql/translator.py` - Added 3 translator methods
- `tests/unit/fhirpath/sql/test_translator_case_trim.py` - Created 21 tests

### Test Results:
- Unit tests: 21/21 passed ✅
- Integration tests: All string-related tests passing ✅
- Both DuckDB and PostgreSQL validated ✅

### Architectural Compliance:
- ✅ Thin dialect architecture maintained (only syntax differences in dialects)
- ✅ Business logic in translator, not dialects
- ✅ Population-first design preserved
- ✅ No hardcoded values introduced
- ✅ Multi-database consistency verified

---

**Created**: 2025-10-05
**Owner**: Mid-Level Developer
**Estimated Effort**: 6 hours
**Actual Effort**: ~4 hours
