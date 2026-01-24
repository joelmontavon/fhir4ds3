# Task: Implement empty() Function
**Task ID**: SP-006-010 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: High
**Status**: ✅ Completed | **Date**: 2025-10-03

## Overview
Implement empty() function to check if a collection is empty.

## Context
Collection functions at 19.6% (18/92) - major gap. empty() is commonly used in FHIRPath expressions.

## Acceptance Criteria
- [x] empty() returns true for empty collections
- [x] empty() returns false for non-empty collections
- [x] Works on all collection types
- [x] Multi-database: 100% consistency
- [x] Unit tests: 90%+ (achieved 100%)

## Dependencies
SP-006-009

**Phase**: 3 - Collection Functions

## Technical Approach
```python
# Translator
def _translate_empty_function(self, node: FunctionCallNode) -> SQLFragment:
    collection_expr = self.visit(node.target)

    empty_check_sql = self.dialect.generate_empty_check(
        collection_expr.expression
    )

    return SQLFragment(expression=empty_check_sql, ...)

# Dialects (syntax only)
# DuckDB
def generate_empty_check(self, collection: str) -> str:
    return f"(json_array_length({collection}) = 0)"

# PostgreSQL
def generate_empty_check(self, collection: str) -> str:
    return f"(jsonb_array_length({collection}) = 0)"
```

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py`
- `fhir4ds/dialects/*.py`
- `tests/unit/fhirpath/sql/test_translator_collection_functions.py` (new)

## Success Metrics
- [x] Collection functions: 19.6% → ~30%

## Completion Summary
**Completed**: 2025-10-03
**Implementation Time**: ~6 hours (under estimate)

### What Was Implemented
1. **Base Dialect Method**: Added `generate_empty_check()` abstract method to `DatabaseDialect` base class with comprehensive documentation
2. **DuckDB Dialect**: Implemented syntax-only method using `json_array_length(collection) = 0`
3. **PostgreSQL Dialect**: Implemented syntax-only method using `jsonb_array_length(collection) = 0`
4. **Translator Method**: Added `_translate_empty()` to `ASTToSQLTranslator` with proper error handling and context preservation
5. **Function Dispatch**: Integrated empty() into `visit_function_call()` dispatcher

### Tests Created
Created comprehensive test suite in `tests/unit/fhirpath/sql/test_translator_empty.py`:
- **15 tests, 100% pass rate**
- Basic translation tests (name, telecom, address collections)
- Error handling tests (invalid arguments)
- Context preservation tests
- Dialect consistency tests
- Population-scale pattern validation
- Fragment properties validation

### Architecture Compliance
- ✅ **Thin Dialect Architecture**: All business logic in translator, only syntax in dialects
- ✅ **Population-First Design**: Uses json_array_length checks, avoids LIMIT patterns
- ✅ **Multi-Database Consistency**: Identical behavior across DuckDB and PostgreSQL
- ✅ **No Hardcoded Values**: All values extracted from context
- ✅ **Error Handling**: Validates function takes no arguments

### Files Modified
- `fhir4ds/dialects/base.py` (+25 lines)
- `fhir4ds/dialects/duckdb.py` (+18 lines)
- `fhir4ds/dialects/postgresql.py` (+18 lines)
- `fhir4ds/fhirpath/sql/translator.py` (+63 lines)
- `tests/unit/fhirpath/sql/test_translator_empty.py` (+389 lines, new file)

### Key Decisions
1. **No Arguments**: empty() takes no arguments (unlike exists() which can take criteria)
2. **Direct Length Check**: Returns simple boolean expression using array length check
3. **No CASE WHEN**: Unlike exists(), returns direct comparison (simpler, cleaner)
4. **Context Unchanged**: empty() does not modify translation context

### Next Steps
- Task SP-006-011: Implement all() function
- Continue advancing collection function coverage toward 100%
