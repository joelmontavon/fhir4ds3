# SP-106-002: Implement Type Operations is/as/$this

**Priority:** HIGH
**Estimated Effort:** 16 hours
**Test Impact:** 81 tests

## Problem Statement

FHIRPath type operations (is, as, $this) are not fully implemented in the SQL translator, preventing type checking and type casting expressions from working correctly.

## FHIRPath Specification

### Type Operator: `is`
Tests whether the left operand is of the type specified as the right operand.
- Returns true if the runtime type of the left operand is the same as or a descendant of the type specified
- Single value semantics: evaluates to a single boolean

### Type Operator: `as`
Converts or casts the value of the left operand to the type specified as the right operand.
- Returns null if the operand cannot be converted to the target type
- Single value semantics: evaluates to a single value or null

### Special Variable: `$this`
Refers to the context item during expression evaluation.
- Used in membership and filter expressions
- Provides access to the current item being evaluated

## Architecture Alignment

These operations are core to FHIRPath's type system and must be implemented at the AST translation layer, not in database dialects. The SQL translator must:
1. Preserve type information through the execution pipeline
2. Generate appropriate SQL type checks and casts
3. Maintain proper context for $this references

## Implementation Plan

1. **AST Extensions**
   - Add `IsExpression`, `AsExpression`, and `ThisRef` nodes to AST
   - Define proper type annotations for type operations
   - Ensure compatibility with existing expression nodes

2. **SQL Translation**
   - Implement `is` as SQL type checking (e.g., `IS NOT NULL` + type column check)
   - Implement `as` as SQL `CAST` or `TRY_CAST` operations
   - Implement `$this` as column reference to current context item

3. **Type System Integration**
   - Ensure type operations respect FHIR type hierarchy
   - Handle polymorphic resource types correctly
   - Support type checking for FHIR primitive types

4. **Context Handling**
   - Track context items through nested expressions
   - Preserve context in filter and membership operations
   - Ensure $this resolves to correct item in nested scopes

## Testing Strategy

- Run official FHIRPath test suite for type operations (81 tests)
- Verify type checking with FHIR resource types
- Test type casting with primitive and complex types
- Validate $this behavior in nested expressions

## Success Criteria

- [ ] All 81 type operation tests pass
- [ ] `is` operator correctly identifies type matches
- [ ] `as` operator performs type conversion with null for invalid casts
- [ ] `$this` correctly references context items
- [ ] No regressions in existing functionality

## Dependencies

- Depends on: SP-106-001 (column selection fix)
- Blocks: SP-106-005, SP-106-006 (some tests may require type operations)

## Technical Considerations

- Type information may be stored in resource metadata columns
- FHIR polymorphism requires careful type checking logic
- SQL dialect differences in CAST syntax must be isolated to dialect layer
