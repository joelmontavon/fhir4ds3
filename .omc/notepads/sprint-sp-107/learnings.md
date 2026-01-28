# Sprint SP-107 Learnings

## Sprint Context
- **Starting Point:** SP-106 just merged to main
- **Baseline Compliance:** 57.39% (536/934 passing)
- **Gap:** 398 failing tests (42.61%)
- **Previous Work:** SP-106 addressed quantity literals, datetime literals, type operations (is/as/this), and column preservation

## Technical Discoveries

### Test Runner Behavior
- Compliance tests require fresh package installation: `python3 -m pip install -e .`
- Test runner at `tests/compliance/fhirpath/test_runner.py`
- Results stored in JSON format with detailed failure analysis

### Key Insights from SP-106 Results
1. **Quick Win Categories** (60%+ pass rate):
   - path_navigation: 90% (1 fail remaining)
   - datetime_functions: 83.3% (1 fail remaining)
   - string_functions: 69.2% (20 fails)
   - comparison_operators: 69.2% (104 fails)
   - math_functions: 67.9% (9 fails)

2. **High-Effort Categories** (<50% pass rate):
   - comments_syntax: 34.4% (21 fails)
   - type_functions: 41.4% (68 fails)
   - arithmetic_operators: 41.7% (42 fails)
   - collection_functions: 45.4% (77 fails)

3. **Remaining SP-106 Issues** (from failed_test_analysis):
   - Polymorphism: `.as(Quantity)` still returning empty
   - DateTime literals: `@2015T` type checking issues
   - Time literals: `@T14:34:28Z` semantic validation
   - Quantity literals: `10 'mg'.convertsToQuantity()` failing
   - Unary polarity: `Patient.name.given.count() > -3` type coercion

## Patterns and Approaches

### Successful Patterns from Previous Sprints
1. **Column Preservation:** Use `preserved_columns` field in CTEs
2. **Type Navigation:** Track polymorphic types through navigation chains
3. **Literal Parsing:** Special handling for datetime/quantity/time literals
4. **Semantic Validation:** Reject invalid expressions at parse time

### Architecture Principles
- **CTE-First Design:** Every operation maps to CTE templates
- **Thin Dialects:** Business logic in FHIRPath engine, NOT in dialects
- **Population Analytics:** Default to population queries
- **Multi-Dialect Parity:** Must work identically in DuckDB and PostgreSQL

## Known Issues

### SP-107-001: testPolymorphismAsA - ROOT CAUSE IDENTIFIED AND FIXED

**Problem:** `Observation.value.as(Quantity).unit` was returning empty instead of `"lbs"`.

**Root Cause:** The `TypeOperationNodeAdapter` in `fhir4ds/main/fhirpath/parser_core/ast_extensions.py` was incorrectly parsing `.as()` operations as `.is()` operations.

**Details:**
- The adapter's `_extract_operation_and_type()` method checked for `' as '` (with spaces) in the text
- But the `.as()` function call node has text `"as()"` (without spaces or leading dot)
- When the pattern didn't match, it defaulted to `'is'` operation
- This caused the `.as()` operation to be processed as a type check instead of a type cast

**Fix:** Added explicit check for `'as()'` pattern before checking for `' as '` pattern:

```python
# SP-107-001: Check for as() operation (function call syntax)
# The text for as() is 'as()' so we check for that pattern first
if text == 'as()' or 'as(' in text:
    target_type = self._extract_type_from_children(node)
    return 'as', target_type or 'Unknown'
```

**Files Modified:**
- `fhir4ds/main/fhirpath/parser_core/ast_extensions.py` (line 950-953)

**Test Results:**
- ✅ `Observation.value.as(Quantity).unit` → `"lbs"` (PASS)
- ✅ `Observation.value.as(Quantity).value` → `10` (PASS)
- ✅ `Observation.value.as(String)` → `"normal"` (PASS)
- ✅ Official test `testPolymorphismAsA` PASSED

**Impact:**
- Fixes 1 failing test in path_navigation category
- Improves path_navigation compliance from 90% to 100% (pending full test suite run)

### DateTime Literal Handling
- DateTime literals like `@2015T` need proper type inference
- Missing `is(DateTime)` checks returning wrong results
- Time literals `@T14:34:28Z` need semantic validation

### Quantity Literal Support
- Quantity literals syntax: `10 'mg'` or `10.1 'mg'`
- `.convertsToQuantity()` needs type checking
- Unit extraction and validation

### Unary Operator Precedence
- `-Patient.name.given.count()` type coercion issues
- Unary operators need proper type propagation
- Comparison with negative literals: `count() > -3`

### Comments Syntax
- 34.4% compliance suggests systematic issue
- Need to review comment parsing and tokenization

## Code Quality Notes

### Parser Adapter Pattern
- The `TypeOperationNodeAdapter` wraps raw AST nodes to provide a consistent interface
- Critical for distinguishing between infix syntax (`value is Type`) and function call syntax (`value.as(Type)`)
- Pattern matching on text is fragile - consider using AST structure instead

### Translation Context Management
- `parent_path` tracks the current navigation path through the FHIR resource
- Polymorphic field mappings allow subsequent field access to use resolved types
- Context snapshot/restore prevents state leakage between operations

### Testing Strategy
- Use direct SQL generation testing to debug translator issues
- Test with minimal data fixtures before running full compliance suite
- Verify edge cases (missing fields, wrong types, empty collections)
