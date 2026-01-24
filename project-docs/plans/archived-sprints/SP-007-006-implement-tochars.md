# Task: Implement toChars() Function

**Task ID**: SP-007-006 | **Sprint**: 007 | **Estimate**: 4h | **Priority**: Low
**Status**: ✅ Completed - Pending Review
**Phase**: 1 - High-Value String Functions (Week 1)
**Completed**: 2025-10-07

---

## Overview

Implement the FHIRPath `toChars()` function that converts a string into an array of single-character strings. This enables character-level string processing in FHIRPath expressions.

## FHIRPath Specification

### toChars() Function

**Signature**: `toChars() : collection`

**Description**: Returns a collection where each element is a single character from the input string.

**Behavior**:
- Input: String
- Returns: Collection of single-character strings
- Empty string: Returns empty collection
- NULL input: Returns empty collection

**Examples**:
```fhirpath
'hello'.toChars()  → {'h', 'e', 'l', 'l', 'o'}
'ab'.toChars()     → {'a', 'b'}
''.toChars()       → {}
```

## Technical Approach

### Translator Implementation

```python
def _translate_tochars(self, node: FunctionCallNode) -> SQLFragment:
    """Translate toChars() to SQL string splitting.

    FHIRPath: string.toChars()
    SQL: Generate array of characters using string split/unnest
    """
    # No arguments
    if len(node.arguments) != 0:
        raise ValueError("toChars() takes no arguments")

    target_expr = ...

    # Use dialect method to split into character array
    chars_sql = self.dialect.generate_char_array(target_expr)

    return SQLFragment(
        expression=chars_sql,
        requires_unnest=False,  # Already returns array
        ...
    )
```

### Dialect Methods

**DuckDB**:
```python
def generate_char_array(self, string_expr: str) -> str:
    """Split string into character array using DuckDB functions."""
    # Option 1: Use string_split with empty delimiter (if supported)
    # Option 2: Use list comprehension with substring
    return f"list_transform(generate_series(1, length({string_expr})), i -> substring({string_expr}, i, 1))"
```

**PostgreSQL**:
```python
def generate_char_array(self, string_expr: str) -> str:
    """Split string into character array using PostgreSQL."""
    return f"string_to_array({string_expr}, NULL)"  # NULL delimiter = split each char
```

## Implementation Steps

1. **Research character splitting** (1h): Test approaches in both DBs
2. **Add to translator** (1h): Function implementation
3. **Dialect methods** (1h): Both database implementations
4. **Unit tests** (1h): 8+ tests including edge cases

## Acceptance Criteria

- [x] toChars() returns character array
- [x] Empty string returns empty array
- [x] Multi-database: 100% consistency
- [x] Unit tests: 90%+ coverage
- [x] Performance: <10ms

## Files to Modify

1. `fhir4ds/fhirpath/sql/translator.py`
2. `fhir4ds/dialects/base.py`
3. `fhir4ds/dialects/duckdb.py`
4. `fhir4ds/dialects/postgresql.py`
5. `tests/unit/fhirpath/sql/test_translator_tochars.py`

---

**Created**: 2025-10-05
**Owner**: Mid-Level Developer
**Estimated Effort**: 4 hours

---

## Implementation Summary

### Implementation Approach

Successfully implemented `toChars()` function using `regexp_split_to_array()` with empty delimiter in both DuckDB and PostgreSQL. Used `CASE WHEN` to handle empty string edge case (should return empty array, not array containing empty string).

### Key Technical Decisions

1. **Empty String Handling**: Used `CASE WHEN length(expr) = 0 THEN [] ELSE regexp_split_to_array(expr, '') END` pattern to ensure empty strings return empty arrays
2. **Database Consistency**: Both databases use `regexp_split_to_array()` with different empty array syntax:
   - DuckDB: `[]`
   - PostgreSQL: `ARRAY[]::text[]`
3. **Thin Dialect Pattern**: All business logic in translator, only syntax differences in dialect methods

### Files Modified

1. **fhir4ds/dialects/base.py**: Added abstract `generate_char_array()` method
2. **fhir4ds/dialects/duckdb.py**: Implemented DuckDB-specific character array generation
3. **fhir4ds/dialects/postgresql.py**: Implemented PostgreSQL-specific character array generation
4. **fhir4ds/fhirpath/sql/translator.py**: Added `_translate_tochars()` method
5. **tests/unit/fhirpath/sql/test_translator_tochars.py**: Created comprehensive test suite (9 tests)

### Test Results

- ✅ All 9 unit tests passing
- ✅ All 775 SQL translator tests passing
- ✅ Integration tests passing in both DuckDB and PostgreSQL
- ✅ Edge cases tested: empty strings, single characters, multi-character strings
- ✅ Multi-database consistency validated

### Performance

- Translation time: <1ms
- Execution time: <10ms (within performance target)

### Compliance

- ✅ FHIRPath specification compliant
- ✅ Thin dialect architecture maintained
- ✅ Population-first design preserved
- ✅ No hardcoded values introduced
