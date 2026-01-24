# Task: Implement ofType() Type Filtering Function
**Task ID**: SP-006-007 | **Sprint**: 006 | **Estimate**: 10h | **Priority**: High
**Status**: ⏳ Pending

## Overview
Implement ofType() to filter collections by type.

## Acceptance Criteria
- [ ] ofType() filters collections by type
- [ ] All FHIRPath types supported
- [ ] Multi-database consistency: 100%
- [ ] Unit tests: 90%+

## Dependencies
SP-006-005

**Phase**: 2 - Type Functions

## Technical Approach
```python
# Translator: Business logic for filtering
def _translate_oftype_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)
    target_type = node.arguments[0].value

    filter_sql = self.dialect.generate_collection_type_filter(
        collection_expr.expression,
        target_type
    )
    return SQLFragment(expression=filter_sql, ...)

# Dialect: Syntax only
def generate_collection_type_filter(self, collection: str, type: str) -> str:
    # DuckDB/PostgreSQL specific JSON array filtering syntax
    pass
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`
- `tests/unit/fhirpath/sql/test_translator_type_functions.py`

## Success Metrics
- [ ] Type functions: ~35% → ~50%
