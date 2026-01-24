# Task: Implement contains() Function

**Task ID**: SP-007-003 | **Sprint**: 007 | **Estimate**: 4h | **Priority**: High
**Status**: ✅ Completed - Pending Review
**Phase**: 1 - High-Value String Functions (Week 1)
**Completed**: 2025-10-06

---

## Overview

Implement the FHIRPath `contains()` function for substring detection. This is a fundamental string operation used extensively in filtering and validation queries.

## FHIRPath Specification

### contains() Function Semantics

**Signature**: `contains(substring: String) : Boolean`

**Description**: Returns true if the input string contains the specified substring.

**Behavior**:
- Input: String to search
- Argument: Substring to find
- Returns: Boolean (true if found, false if not)
- Case-sensitive matching
- Empty substring: Returns true
- Empty input: Returns empty (null)

**Examples**:
```fhirpath
'hello world'.contains('world')  → true
'hello'.contains('xyz')          → false
name.family.contains('Smith')    → true/false
''.contains('')                  → true (empty contains empty)
```

## Technical Approach

### Translator Implementation

```python
def _translate_contains(self, node: FunctionCallNode) -> SQLFragment:
    """Translate contains() to SQL substring detection.

    FHIRPath: string.contains(substring)
    SQL: (string LIKE '%' || substring || '%')  [Standard SQL]
          POSITION(substring IN string) > 0     [Alternative]
    """
    # Validate arguments
    if len(node.arguments) != 1:
        raise ValueError(
            f"contains() requires 1 argument (substring), got {len(node.arguments)}"
        )

    # Get string and substring expressions
    target_expr = ...
    substring_expr = ...

    # Use dialect method
    contains_sql = self.dialect.generate_substring_check(
        target_expr,
        substring_expr
    )

    return SQLFragment(...)
```

### Dialect Methods

**DuckDB**:
```python
def generate_substring_check(self, string_expr: str, substring: str) -> str:
    # Option 1: LIKE pattern
    return f"({string_expr} LIKE '%' || {substring} || '%')"
    # Option 2: POSITION function
    # return f"(POSITION({substring} IN {string_expr}) > 0)"
```

**PostgreSQL**:
```python
def generate_substring_check(self, string_expr: str, substring: str) -> str:
    return f"({string_expr} LIKE '%' || {substring} || '%')"
```

## Implementation Steps

1. **Add to translator** (1.5h): Function dispatch, argument validation
2. **Dialect methods** (1h): Base abstract + implementations
3. **Unit tests** (1h): 8+ tests for edge cases
4. **Integration** (0.5h): Validate +3-4 tests

## Acceptance Criteria

- [x] contains(substring) translates correctly ✅
- [x] Case-sensitive matching works ✅
- [x] Empty string edge cases handled ✅
- [x] NULL handling correct ✅
- [x] Multi-database: 100% consistency ✅
- [x] Unit tests: 90%+ coverage ✅ (20 comprehensive tests)

## Files to Modify

1. `fhir4ds/fhirpath/sql/translator.py`
2. `fhir4ds/dialects/base.py`
3. `fhir4ds/dialects/duckdb.py`
4. `fhir4ds/dialects/postgresql.py`
5. `tests/unit/fhirpath/sql/test_translator_contains.py`

---

## Completion Summary

**Implementation completed successfully on 2025-10-06.**

### Changes Made

1. **Base Dialect (`fhir4ds/dialects/base.py`)**:
   - Added abstract method `generate_substring_check(string_expr, substring)` with comprehensive documentation

2. **DuckDB Dialect (`fhir4ds/dialects/duckdb.py`)**:
   - Implemented `generate_substring_check()` using standard SQL LIKE operator with concatenation
   - Syntax: `(string_expr LIKE '%' || substring || '%')`

3. **PostgreSQL Dialect (`fhir4ds/dialects/postgresql.py`)**:
   - Implemented `generate_substring_check()` using standard SQL LIKE operator with concatenation
   - Syntax: `(string_expr LIKE '%' || substring || '%')` (identical to DuckDB)

4. **Translator (`fhir4ds/fhirpath/sql/translator.py`)**:
   - Added `contains` to function dispatch in `visit_function_call()` method
   - Implemented `_translate_contains()` method with comprehensive documentation
   - Follows same pattern as `matches()` and `replaceMatches()` implementations
   - Proper error handling for invalid argument counts
   - Dependency tracking for complex expressions

5. **Unit Tests (`tests/unit/fhirpath/sql/test_translator_contains.py`)**:
   - Created comprehensive test suite with 20 tests
   - All tests passing on both DuckDB and PostgreSQL
   - Test categories:
     - Basic translation (4 tests)
     - Identifier/context handling (2 tests)
     - Error handling (2 tests)
     - Multi-database consistency (4 tests)
     - Edge cases (4 tests)
     - Special strings (2 tests)
     - Fragment properties (2 tests)

6. **Test Infrastructure (`tests/unit/dialects/test_base_dialect.py`)**:
   - Updated MockDialect to implement `generate_substring_check()` method

### Test Results

- **Unit Tests**: 20/20 passed (100%)
- **All SQL Unit Tests**: 1595 passed, 3 skipped
- **Multi-database**: Verified 100% consistency between DuckDB and PostgreSQL
- **Coverage**: Comprehensive coverage of all edge cases and error conditions

### Key Design Decisions

1. **Thin Dialect Pattern**: Both DuckDB and PostgreSQL use identical SQL syntax (LIKE with concatenation), demonstrating proper thin dialect implementation with zero business logic in dialect classes.

2. **Standard SQL Approach**: Used standard SQL LIKE operator instead of database-specific functions (e.g., POSITION, STRPOS) for maximum compatibility and simplicity.

3. **Consistent Pattern**: Implementation follows exact same pattern as `matches()` and `replaceMatches()` functions for maintainability.

4. **Comprehensive Testing**: Created extensive test suite covering all edge cases including empty strings, special characters, whitespace, punctuation, and NULL handling.

### Notes

- Implementation maintains population-scale performance (no row-by-row operations)
- No hardcoded values introduced
- All tests passing in both database environments
- Clean, well-documented code following project standards
- Ready for senior architect review

---

**Created**: 2025-10-05
**Owner**: Mid-Level Developer
**Estimated Effort**: 4 hours
**Actual Effort**: ~3 hours
