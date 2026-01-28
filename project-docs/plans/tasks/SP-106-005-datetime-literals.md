# SP-106-005: Implement DateTime Literals

**Priority:** MEDIUM
**Estimated Effort:** 8 hours
**Test Impact:** 35 tests

## Problem Statement

DateTime literals in FHIRPath (e.g., `@2023-01-01`, `@2023-01-01T12:00:00Z`) are not properly parsed or translated to SQL date/time types.

## FHIRPath Specification

DateTime literals use the `@` prefix:
- Syntax: `@<datetime-string>` following ISO 8601 format
- Support various precisions: year, month, day, hour, minute, second, millisecond
- Timezone handling with offset or Z for UTC
- Partial precision (e.g., `@2023` for just year)

## Architecture Alignment

DateTime handling must:
1. Parse ISO 8601 format correctly at lexer level
2. Map to appropriate SQL date/time types
3. Handle timezone conversions properly
4. Support partial precision datetime values
5. Ensure consistent behavior across dialects

## Implementation Plan

1. **Grammar Enhancement**
   - Update ANTLR grammar for datetime literal syntax
   - Add lexer rule recognizing `@` prefix + ISO 8601 string
   - Parse into structured datetime components

2. **AST Representation**
   - Add `DateTimeLiteral` node to AST
   - Store parsed datetime value with precision level
   - Track timezone information

3. **SQL Translation**
   - Map to appropriate SQL datetime type (TIMESTAMP, DATE, etc.)
   - Handle timezone conversion to UTC if needed
   - Support partial precision (e.g., year-only dates)

4. **DateTime Operations**
   - Implement datetime arithmetic (add, subtract)
   - Support comparison operations
   - Handle datetime component extraction (year, month, day, etc.)

5. **Testing**
   - Test various datetime formats and precisions
   - Verify timezone handling
   - Validate arithmetic and comparison operations

## Testing Strategy

- Run official FHIRPath test suite for datetime literals (35 tests)
- Test various ISO 8601 formats and precisions
- Verify timezone conversions
- Test datetime arithmetic operations
- Ensure consistent behavior across dialects

## Success Criteria

- [ ] All 35 datetime literal tests pass
- [ ] DateTime literals parse correctly from FHIRPath syntax
- [ ] SQL generates proper datetime types
- [ ] Timezone handling is correct
- [ ] Partial precision datetime values work
- [ ] Datetime operations (arithmetic, comparison) function correctly
- [ ] No regressions in existing functionality

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Related to: SP-106-002 (type operations may be used with datetimes)

## Technical Considerations

- ISO 8601 format validation
- SQL dialect differences in datetime types and functions
- Timezone handling complexity (local vs UTC)
- Partial precision requires special handling (not all SQL types support)
- Existing workaround in codebase may need to be replaced
