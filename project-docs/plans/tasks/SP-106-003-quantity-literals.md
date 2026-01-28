# SP-106-003: Implement Quantity Literals

**Priority:** HIGH
**Estimated Effort:** 12 hours
**Test Impact:** 80 tests

## Problem Statement

FHIRPath quantity literals (e.g., `10 'cm'`, `5.5 'kg'`) are not parsed or translated correctly, preventing numeric expressions with units from being evaluated.

## FHIRPath Specification

Quantity literals represent a numeric value with a unit:
- Syntax: `<number> '<unit>'` or `<decimal> '<unit>'`
- The unit is a string literal representing a UCUM unit or other unit code
- Quantity literals are equivalent to constructing a Quantity FHIR type
- Support arithmetic operations with unit compatibility checking

## Architecture Alignment

Quantity literals must be:
1. Parsed at the grammar/lexer level (ANTLR parser)
2. Represented as AST nodes with value and unit components
3. Translated to SQL with proper type handling
4. Stored/retrieved using appropriate JSON structure for FHIR Quantity

## Implementation Plan

1. **Grammar Enhancement**
   - Update ANTLR grammar to recognize quantity literal syntax
   - Add lexer rule for unit string (single-quoted)
   - Parse as a combined quantity expression node

2. **AST Representation**
   - Add `QuantityLiteral` node to AST
   - Store numeric value and unit string
   - Ensure proper typing for quantity operations

3. **SQL Translation**
   - Translate to JSON structure representing FHIR Quantity
   - Implement as object with `value` and `unit` fields
   - Use DuckDB/PostgreSQL JSON functions for construction

4. **Arithmetic Operations**
   - Implement quantity arithmetic (add, subtract, multiply, divide)
   - Add unit compatibility checks where required
   - Handle unit conversions if supported

5. **Comparison Operations**
   - Support comparison of quantities with compatible units
   - Implement comparison logic considering value and unit

## Testing Strategy

- Run official FHIRPath test suite for quantity literals (80 tests)
- Test parsing of various quantity formats
- Verify JSON structure generation for quantities
- Test arithmetic operations with quantities
- Validate comparison operations

## Success Criteria

- [ ] All 80 quantity literal tests pass
- [ ] Quantity literals parse correctly from FHIRPath syntax
- [ ] SQL generates proper FHIR Quantity JSON structure
- [ ] Arithmetic operations work with quantities
- [ ] Comparison operations handle units appropriately
- [ ] No regressions in existing numeric operations

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Related to: SP-106-004 (decimal comparisons)

## Technical Considerations

- FHIR Quantity type is a complex JSON structure
- Unit compatibility may require UCUM terminology service
- SQL JSON functions differ between dialects (isolate to dialect layer)
- Arithmetic with units may need special handling for incompatible units
