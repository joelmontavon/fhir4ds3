# Task: Add TypeExpression Support to AST Adapter
**Task ID**: SP-006-001 | **Sprint**: 006 | **Estimate**: 12h | **Priority**: Critical
**Status**: ✅ Complete (Merged to main 2025-10-02)

## Overview
Add TypeExpression node conversion support to the AST adapter to enable type functions (is, as, ofType).

## Context from SP-005-022
Integration testing revealed 125 type function tests failing due to missing TypeExpression handling in AST adapter. Type functions have 15.2% success rate (19/125) - major gap.

Additionally, 2 of 41 healthcare use cases fail due to missing `as()` function, which requires TypeExpression support.

## Acceptance Criteria
- [x] AST adapter converts TypeExpression nodes to FHIRPath AST
- [x] 100% of official tests with TypeExpression parse successfully
- [x] Unit tests cover TypeExpression conversion paths
- [x] Zero regression in existing AST conversions
- [x] Documentation updated with TypeExpression handling

## Dependencies
SP-005-022 (Complete)

**Phase**: 1 - AST Adapter Enhancements

## Technical Approach

### TypeExpression Structure
```python
# Enhanced AST (from parser)
TypeExpression(
    expression=<base_expression>,
    type_specifier=<type_name>,  # e.g., "String", "Integer", "DateTime"
    operation="is" | "as" | "ofType"
)
```

### Conversion Pattern
```python
# In ast_adapter.py
def convert_type_expression(enhanced_node) -> FHIRPathASTNode:
    """Convert TypeExpression to FunctionCallNode."""
    base_expr = convert_enhanced_ast_to_fhirpath_ast(enhanced_node.expression)

    return FunctionCallNode(
        function_name=enhanced_node.operation,  # "is", "as", or "ofType"
        arguments=[
            base_expr,
            LiteralNode(value=enhanced_node.type_specifier, value_type="type")
        ]
    )
```

### Type Specifiers Supported
- String
- Integer
- Decimal
- Boolean
- DateTime
- Date
- Time
- Quantity
- Code
- Coding
- CodeableConcept

## Implementation Steps

1. **Add TypeExpression Conversion** (4h)
   - Add `convert_type_expression()` method to ast_adapter.py
   - Handle is(), as(), ofType() operations
   - Map type specifiers to FHIRPath types

2. **Update Main Conversion Logic** (2h)
   - Add TypeExpression case to main converter
   - Ensure recursive conversion for nested expressions

3. **Add Unit Tests** (4h)
   - Test is() type checking conversion
   - Test as() type casting conversion
   - Test ofType() type filtering conversion
   - Test all supported type specifiers
   - Test nested type expressions

4. **Validate with Official Tests** (2h)
   - Run official test suite
   - Verify 100% TypeExpression parsing
   - Document any edge cases

## Testing Strategy

### Unit Tests
```python
def test_type_expression_is_conversion():
    """Test is() type checking conversion."""
    enhanced_ast = TypeExpression(
        expression=IdentifierExpression("value"),
        type_specifier="String",
        operation="is"
    )

    fhirpath_ast = convert_enhanced_ast_to_fhirpath_ast(enhanced_ast)

    assert isinstance(fhirpath_ast, FunctionCallNode)
    assert fhirpath_ast.function_name == "is"
    assert fhirpath_ast.arguments[1].value == "String"
```

### Integration Tests
- Run SP-005-022 integration tests
- Verify type function category improvement
- Confirm no regressions

## Files Modified
- `fhir4ds/fhirpath/sql/ast_adapter.py` - Add TypeExpression conversion
- `tests/unit/fhirpath/sql/test_ast_adapter.py` - Add TypeExpression tests

## Success Metrics
- [x] TypeExpression conversion implemented
- [x] 100% of TypeExpression tests parse successfully
- [x] Unit test coverage: 90%+ (13 tests added)
- [x] Zero regressions in existing tests (1138 unit tests pass)
- [x] Official test coverage improves (enables type functions)

## Implementation Summary

Successfully implemented TypeExpression support in AST adapter:

### Changes Made

1. **Parser Enhancement** (`fhir4ds/fhirpath/parser_core/ast_extensions.py`):
   - Modified `ASTNodeFactory.create_from_fhirpath_node()` to preserve `terminalNodeText` from raw parser output
   - Added special handling for TypeExpression nodes to extract operation (`is` or `as`) and store in `metadata.custom_attributes['operation']`

2. **AST Adapter** (`fhir4ds/fhirpath/sql/ast_adapter.py`):
   - Added `_is_type_expression()` method to detect TypeExpression nodes
   - Added `_convert_type_expression()` method to convert TypeExpression to FunctionCallNode
   - Added `_extract_type_name()` to extract type specifier from TypeSpecifier node
   - Added `_extract_type_operation()` to retrieve operation from metadata
   - Updated main `convert()` method to handle TypeExpression before other node types

3. **Unit Tests** (`tests/unit/fhirpath/sql/test_ast_adapter.py`):
   - Created comprehensive test suite with 13 tests
   - Tests cover `is` and `as` operations with simple and complex expressions
   - Tests verify all common FHIR type specifiers
   - Tests confirm operation preservation from parser to adapter
   - Tests verify existing functionality (zero regressions)

### Technical Details

- TypeExpression nodes from parser have structure: `[TermExpression (base), TypeSpecifier (type)]`
- Operation (`is`/`as`) stored in `metadata.custom_attributes['operation']`
- Converted to `FunctionCallNode` with 2 arguments: base expression + type literal
- `ofType()` handled as regular function call (not TypeExpression)

## Architecture Alignment
- ✅ Parser layer enhancement (AST adapter)
- ✅ No business logic in AST conversion (just structural transformation)
- ✅ Enables translator to implement type function logic
- ✅ Foundation for thin dialect type operations

## References
- FHIRPath R4 Specification: Type operations
- SP-005-022 Review: Type function gaps identified
- Sprint 006 Plan: AST adapter enhancement phase
