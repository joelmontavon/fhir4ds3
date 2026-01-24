# Task: Implement all() Universal Quantifier
**Task ID**: SP-006-011 | **Sprint**: 006 | **Estimate**: 10h | **Priority**: High
**Status**: ✅ Complete

## Overview
Implement all() function for universal quantification - returns true if condition is true for all elements.

## Acceptance Criteria
- [x] all() tests condition on all collection elements
- [x] Returns true if all satisfy condition
- [x] Returns false if any don't satisfy
- [x] Multi-database: 100% consistency

## Dependencies
SP-006-010

**Phase**: 3 - Collection Functions

## Technical Approach
```python
# Translator: Business logic for quantification
def _translate_all_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)
    condition_expr = self.visit(node.arguments[0])

    # Generate SQL that checks if ALL elements satisfy condition
    all_check_sql = self.dialect.generate_universal_quantifier(
        collection_expr.expression,
        condition_expr.expression
    )

    return SQLFragment(expression=all_check_sql, ...)
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`

## Success Metrics
- [ ] Collection functions: ~30% → ~45%
