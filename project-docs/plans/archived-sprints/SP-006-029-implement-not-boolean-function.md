# Task: Implement not() Boolean Function

**Task ID**: SP-006-029 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: High
**Status**: ⏳ Pending

## Overview
Implement the `not()` boolean negation function to support boolean logic in FHIRPath expressions.

## Context from SP-006-021

**Current Status**:
- Boolean logic category: 0% coverage (0/6 tests passing)
- `not()` function appears in 10+ failed official tests
- Common pattern: `empty().not()`, `true.not()`, `condition.not()`

**Impact**:
- Blocks 10+ official tests (1.1% of total)
- Required for boolean logic expressions
- Commonly used in real-world queries

**Examples from Failed Tests**:
```fhirpath
Patient.name.empty().not()        # Check if name exists
true.not() = false                # Boolean negation
Patient.active.not()              # Negate boolean field
```

## FHIRPath Specification

### not() Function Semantics

**Signature**: `not() : Boolean`

**Description**: Returns the opposite boolean value of the input.

**Behavior**:
- Input `true` → Returns `false`
- Input `false` → Returns `true`
- Input `{}` (empty) → Returns `{}` (empty)
- Input collection with multiple values → Returns `{}`

**Type Rules**:
- Operates on Boolean type only
- Returns Boolean type
- For collections: applies to first element only (per FHIRPath spec)

## Technical Approach

### 1. SQL Generation Pattern

**Business Logic** (in translator):
```python
def _translate_not_function(self, node: FunctionCallNode) -> SQLFragment:
    """Translate not() boolean negation to SQL.

    FHIRPath: expression.not()
    SQL: NOT (expression)

    Handles:
    - Boolean values: NOT true → false
    - NULL values: NOT NULL → NULL (SQL behavior)
    - Collections: Extract first element, then negate
    """
    # Get the target expression
    target_expr = self.visit(node.target)

    # Generate NOT expression using dialect
    not_sql = self.dialect.generate_boolean_not(
        target_expr.expression
    )

    return SQLFragment(
        expression=not_sql,
        dependencies=target_expr.dependencies,
        context_mode=ContextMode.SCALAR  # not() returns scalar boolean
    )
```

**Dialect Methods** (syntax only):

DuckDB:
```python
def generate_boolean_not(self, expr: str) -> str:
    """Generate boolean NOT for DuckDB."""
    return f"NOT ({expr})"
```

PostgreSQL:
```python
def generate_boolean_not(self, expr: str) -> str:
    """Generate boolean NOT for PostgreSQL."""
    return f"NOT ({expr})"
```

**Note**: Both dialects use standard SQL `NOT`, so dialect methods are identical. However, we still use the method pattern for consistency and future extensibility.

### 2. Edge Case Handling

**NULL Handling**:
```sql
-- SQL NOT behavior with NULL
NOT NULL → NULL  -- This matches FHIRPath empty collection behavior
```

**Non-Boolean Input**:
```python
# Should raise error or coerce to boolean?
# FHIRPath spec: not() only accepts boolean input
# Decision: Raise clear error for non-boolean input
if not is_boolean_type(target_expr):
    raise FHIRPathError(f"not() requires boolean input, got {target_expr.type}")
```

**Collection Handling**:
```python
# FHIRPath spec: not() on collection applies to first element
# Implementation approach:
# 1. If scalar: Apply NOT directly
# 2. If collection: Extract first element, then apply NOT
# 3. If empty collection: Return empty (NULL in SQL)

if target_expr.context_mode == ContextMode.COLLECTION:
    # Extract first element
    first_elem = self.dialect.generate_first_element(target_expr.expression)
    not_sql = self.dialect.generate_boolean_not(first_elem)
else:
    # Direct NOT on scalar
    not_sql = self.dialect.generate_boolean_not(target_expr.expression)
```

## Implementation Steps

### 1. Add not() Function to Translator (3h)

**File**: `fhir4ds/fhirpath/sql/translator.py`

**Changes**:
1. Add `"not"` to function dispatch in `visit_function_call()`
2. Implement `_translate_not_function()` method
3. Handle boolean type checking
4. Handle collection vs scalar context
5. Generate SQL using dialect method

**Error Handling**:
- Check for zero arguments (not() takes no arguments)
- Verify target expression is boolean type
- Handle empty collections appropriately

### 2. Add Dialect Methods (2h)

**Files**:
- `fhir4ds/dialects/base.py` - Abstract method
- `fhir4ds/dialects/duckdb.py` - DuckDB implementation
- `fhir4ds/dialects/postgresql.py` - PostgreSQL implementation

**Methods to Add**:
```python
@abstractmethod
def generate_boolean_not(self, expr: str) -> str:
    """Generate boolean NOT expression.

    Args:
        expr: SQL expression evaluating to boolean

    Returns:
        SQL expression performing boolean negation
    """
    pass
```

### 3. Add Unit Tests (2h)

**File**: `tests/unit/fhirpath/sql/test_translator_boolean_functions.py` (new)

**Test Coverage**:
```python
class TestNotFunctionBasic:
    """Test basic not() functionality."""

    def test_not_true_literal(self):
        """Test: true.not() = false"""

    def test_not_false_literal(self):
        """Test: false.not() = true"""

    def test_not_boolean_field(self):
        """Test: Patient.active.not()"""

class TestNotFunctionEdgeCases:
    """Test not() edge cases."""

    def test_not_empty_collection(self):
        """Test: {}.not() = {}"""

    def test_not_multiple_values(self):
        """Test: {true, false}.not() (should use first)"""

    def test_not_null_value(self):
        """Test: (null as Boolean).not()"""

class TestNotFunctionComposition:
    """Test not() in complex expressions."""

    def test_not_with_empty(self):
        """Test: Patient.name.empty().not()"""

    def test_double_negation(self):
        """Test: true.not().not() = true"""

    def test_not_in_where_clause(self):
        """Test: Patient.where(active.not())"""

class TestNotFunctionMultiDatabase:
    """Test not() across database dialects."""

    @pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
    def test_not_consistency(self, dialect):
        """Test not() produces same results in both databases."""

class TestNotFunctionErrorHandling:
    """Test not() error cases."""

    def test_not_non_boolean_type(self):
        """Test: 'string'.not() should raise error"""

    def test_not_with_arguments(self):
        """Test: true.not(arg) should raise error"""
```

**Target**: 90%+ coverage, 15+ comprehensive tests

### 4. Integration Testing (1h)

**Validate Against Official Tests**:
```bash
# Re-run official test suite
pytest tests/integration/fhirpath/test_real_expressions_integration.py \
  ::TestOfficialFHIRPathExpressionTranslation::test_all_official_expressions_duckdb -v

# Expected improvement:
# Boolean logic: 0/6 (0%) → 6/6 (100%)
# Overall: 494/934 (52.9%) → 504/934 (54.0%)
```

**Manual Validation**:
```python
# Test actual execution with sample data
def test_not_function_execution_duckdb():
    """Execute not() function against real DuckDB database."""
    expr = "Patient.active.not()"
    result = execute_fhirpath_query(expr, patient_data, dialect="duckdb")
    # Verify results
```

## Acceptance Criteria

- [x] not() function translates to SQL correctly
- [x] Boolean negation works on literals, fields, and expressions
- [x] Edge cases handled (null, empty, collections)
- [x] Dialect methods implemented for both DuckDB and PostgreSQL
- [x] Unit tests: 90%+ coverage (15+ tests passing)
- [x] Multi-database consistency: 100%
- [x] Official tests: 0/6 → 6/6 boolean logic tests passing
- [x] Integration tests passing with real data

## Dependencies
None (standalone function)

## Success Metrics
- [x] Boolean logic category: 0% → 100% (6/6 tests)
- [x] Overall coverage: 52.9% → 54%+ (approximately +10 tests)
- [x] Unit test coverage: 90%+ for not() function
- [x] Multi-database consistency: 100%
- [x] Performance: <5ms per not() operation

## Files Modified
- `fhir4ds/fhirpath/sql/translator.py` - Add not() function translation
- `fhir4ds/dialects/base.py` - Add `generate_boolean_not()` abstract method
- `fhir4ds/dialects/duckdb.py` - Implement `generate_boolean_not()`
- `fhir4ds/dialects/postgresql.py` - Implement `generate_boolean_not()`
- `tests/unit/fhirpath/sql/test_translator_boolean_functions.py` (new) - Unit tests

## Testing Strategy

### Unit Tests
- Basic boolean negation (true/false literals)
- Field-based negation (Patient.active.not())
- Expression composition (empty().not())
- Edge cases (null, empty, collections)
- Error handling (non-boolean input)
- Multi-database consistency

### Integration Tests
- Execute against official FHIRPath test suite
- Validate with real FHIR data in both databases
- Verify performance benchmarks

### Manual Validation
```python
# Test cases to manually verify:
assert eval("true.not()") == False
assert eval("false.not()") == True
assert eval("Patient.active.not()") == (not patient.active)
assert eval("Patient.name.empty().not()") == (not is_empty(patient.name))
```

## Architecture Alignment
- ✅ **Thin Dialect**: Boolean NOT is standard SQL, minimal dialect differences
- ✅ **Business Logic in Translator**: Type checking, collection handling in translator
- ✅ **Population-First**: not() works on full datasets
- ✅ **CTE-First Ready**: Generates SQLFragment for CTE wrapping

## References
- **FHIRPath R4 Specification**: Boolean operations
- **SP-006-021**: Identified not() as blocking 10+ tests
- **SQL Standard**: NOT operator behavior

---

**Estimated Total Effort**: 8 hours
- Translator implementation: 3h
- Dialect methods: 2h
- Unit tests: 2h
- Integration testing: 1h
