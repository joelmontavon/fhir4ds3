# SP-106-007: Implement Unary Polarity Operators

**Priority:** MEDIUM
**Estimated Effort:** 6 hours
**Test Impact:** 30 tests

## Problem Statement

Unary polarity operators (unary minus `-`, unary plus `+`) are not implemented in FHIRPath, preventing numeric expressions like `-5` or `+3.14` from being evaluated.

## FHIRPath Specification

Unary polarity operators:
- Unary minus `-`: Negates the numeric value
- Unary plus `+`: Returns the numeric value unchanged (idempotent)
- Apply to integer and decimal types
- Follow standard arithmetic semantics
- Single value semantics: operate on single numeric values

## Architecture Alignment

Unary operators must be:
1. Parsed at the grammar level
2. Represented as unary expression nodes in AST
3. Translated to appropriate SQL unary operations
4. Handled consistently across numeric types

## Implementation Plan

1. **Grammar Enhancement**
   - Add unary minus and unary plus to ANTLR grammar
   - Ensure proper precedence (higher than multiplication)
   - Handle ambiguity with binary minus/plus

2. **AST Representation**
   - Add `UnaryMinusExpression` and `UnaryPlusExpression` nodes
   - Store operand expression
   - Ensure proper type annotations

3. **SQL Translation**
   - Translate unary minus to SQL `-` operator
   - Translate unary plus to SQL `+` operator or no-op
   - Ensure proper parentheses for operator precedence

4. **Type Handling**
   - Support integer and decimal types
   - Maintain type information through operations
   - Handle NULL values correctly

5. **Testing**
   - Test unary operators with various numeric types
   - Verify operator precedence
   - Test combination with other arithmetic operations

## Testing Strategy

- Run official FHIRPath test suite for unary operators (30 tests)
- Test with integers, decimals, and quantities
- Verify operator precedence in complex expressions
- Ensure consistent behavior across dialects

## Success Criteria

- [ ] All 30 unary operator tests pass
- [ ] Unary minus correctly negates numeric values
- [ ] Unary plus returns values unchanged
- [ ] Operator precedence is handled correctly
- [ ] Works with integers, decimals, and quantities
- [ ] No regressions in existing arithmetic operations

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Related to: SP-106-003 (quantity literals), SP-106-004 (decimal operations)

## Technical Considerations

- Operator precedence in grammar vs SQL
- Potential ambiguity with binary minus/plus in parsing
- SQL unary operators may have different precedence than FHIRPath
- Need proper parentheses in generated SQL
- Type promotion rules for unary operations
