# Task: Implement skip() Collection Slicing
**Task ID**: SP-006-012 | **Sprint**: 006 | **Estimate**: 10h | **Priority**: High
**Status**: ✅ Complete | **Merged**: 2025-10-03

## Overview
Implement skip() function to skip first N elements of a collection.

## Acceptance Criteria
- [x] skip(n) returns collection without first n elements
- [x] Handles edge cases (n > length, n = 0, n negative)
- [x] Multi-database: 100% consistency

## Completion Summary
- **Completed**: 2025-10-03
- **Review**: Approved by Senior Solution Architect/Engineer
- **Merged to**: main branch
- **Test Results**: 17/17 unit tests passing, 0 regressions

## Dependencies
SP-006-011

**Phase**: 3 - Collection Functions

## Technical Approach
```python
# Translator
def _translate_skip_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)
    skip_count = self.visit(node.arguments[0])

    skip_sql = self.dialect.generate_collection_skip(
        collection_expr.expression,
        skip_count.expression
    )

    return SQLFragment(expression=skip_sql, ...)

# Dialects: Array slicing syntax
# DuckDB: list_slice(array, start, end)
# PostgreSQL: array[start:end] syntax
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`

## Success Metrics
- [ ] Collection functions: ~45% → ~55%
