# SP-106-006: Fix Collection Function String Literals

**Priority:** MEDIUM
**Estimated Effort:** 4 hours
**Test Impact:** 18 tests

## Problem Statement

Collection functions (e.g., `contains`, `startsWith`, `endsWith`) are not correctly handling string literal arguments, causing test failures in string manipulation operations.

## FHIRPath Specification

Collection functions for strings:
- `contains(string)`: Tests if string contains substring
- `startsWith(string)`: Tests if string starts with prefix
- `endsWith(string)`: Tests if string ends with suffix
- String literals must be properly escaped and quoted
- Case sensitivity depends on function semantics

## Architecture Alignment

String function handling must:
1. Parse string literals correctly (including escaping)
2. Translate to appropriate SQL string functions
3. Handle NULL values properly
4. Ensure consistent behavior across dialects
5. Support both simple and complex string expressions

## Implementation Plan

1. **Diagnosis**
   - Identify which collection function tests are failing
   - Determine if issue is parsing, translation, or execution
   - Check string literal handling in function arguments

2. **String Literal Fix**
   - Ensure string literals are properly escaped
   - Verify SQL quoting is correct for dialect
   - Handle special characters in strings

3. **Function Translation**
   - Map FHIRPath string functions to SQL equivalents
   - Handle case sensitivity correctly
   - Ensure NULL propagation follows FHIRPath semantics

4. **Testing**
   - Test all string collection functions
   - Verify with various string literals (empty, special chars, unicode)
   - Ensure consistent behavior across dialects

## Testing Strategy

- Run official FHIRPath test suite for collection string functions (18 tests)
- Test various string literal formats
- Verify edge cases (empty strings, null values, special characters)
- Ensure consistent results across DuckDB and PostgreSQL

## Success Criteria

- [ ] All 18 collection string function tests pass
- [ ] String literals parse correctly in function arguments
- [ ] SQL generates proper string function calls
- [ ] Special characters are handled correctly
- [ ] NULL values propagate according to FHIRPath semantics
- [ ] No regressions in existing string operations

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Related to: SP-106-007 (unary operators may interact with string operations)

## Technical Considerations

- SQL string functions differ between dialects (isolate to dialect layer)
- String escaping for SQL injection safety
- Unicode and special character handling
- Case sensitivity may be dialect-dependent
- NULL handling in string functions
