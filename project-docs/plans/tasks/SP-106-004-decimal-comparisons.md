# SP-106-004: Fix Decimal Comparisons

**Priority:** HIGH
**Estimated Effort:** 6 hours
**Test Impact:** 33 tests

## Problem Statement

Decimal comparison operations in FHIRPath are not producing correct results, likely due to floating-point precision issues or incorrect SQL type handling.

## FHIRPath Specification

Decimal comparisons follow IEEE 754 semantics:
- Support standard comparison operators: =, !=, <, <=, >, >=
- Decimals must be compared with proper precision handling
- Decimal values should maintain FHIRPath decimal semantics (not float/double)

## Architecture Alignment

Decimal handling must:
1. Use appropriate SQL numeric types (DECIMAL/NUMERIC, not FLOAT)
2. Maintain precision through calculations
3. Handle edge cases (NaN, infinity, precision loss)
4. Ensure consistent behavior across database dialects

## Implementation Plan

1. **Diagnosis**
   - Identify which decimal comparison tests are failing
   - Determine root cause (type precision, rounding, edge cases)
   - Check SQL type being used for decimal literals

2. **Type System Fix**
   - Ensure decimal literals map to SQL DECIMAL/NUMERIC type
   - Update SQL translation to use precise numeric types
   - Avoid floating-point types that lose precision

3. **Comparison Logic**
   - Implement proper decimal comparison semantics
   - Handle precision matching correctly
   - Add tolerance for floating-point representation issues if needed

4. **Edge Case Handling**
   - Handle NaN values correctly
   - Handle infinity values correctly
   - Ensure consistent behavior across dialects

## Testing Strategy

- Run official FHIRPath test suite for decimal comparisons (33 tests)
- Test various decimal precision levels
- Verify edge case handling (very large/small values)
- Ensure consistent results across DuckDB and PostgreSQL

## Success Criteria

- [ ] All 33 decimal comparison tests pass
- [ ] Decimal precision is maintained through operations
- [ ] Comparison results match FHIRPath specification
- [ ] Consistent behavior across database dialects
- [ ] No regressions in existing numeric operations

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Related to: SP-106-003 (quantity literals may use decimals)

## Technical Considerations

- SQL DECIMAL/NUMERIC types have configurable precision
- DuckDB and PostgreSQL handle DECIMAL differently
- FHIRPath decimals may have different precision than SQL defaults
- Need to balance precision with performance
- ANSI SQL standard for DECIMAL operations
