# Task: SP-100-002 - Implement Conditional Expression (iif)

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P0 (Critical)
**Estimated Effort**: 8-12 hours

---

## Task Description

Implement the `visit_conditional()` method to support FHIRPath `iif()` conditional expressions. This is currently marked as `NotImplementedError`.

## Current State

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:4030-4032`

```python
def visit_conditional(self, node: ConditionalNode) -> SQLFragment:
    """Translate conditional expressions to SQL.

    Args:
        node: ConditionalNode representing iif(condition, true_expr, false_expr)

    Returns:
        SQLFragment containing the conditional SQL

    Raises:
        NotImplementedError: Implementation pending in future sprint

    Example (future implementation):
        Input: ConditionalNode with condition and branches
        Output: SQLFragment with SQL CASE statement
    """
    raise NotImplementedError(
        "visit_conditional implementation pending in future sprint"
    )
```

## Requirements

### Functional Requirements

1. **iif(condition, true_expr, false_expr)** - Ternary conditional expression
2. **Condition evaluation** - Must evaluate to boolean
3. **Type consistency** - Both branches must return same type (SQL requirement)
4. **Nested conditionals** - Support iif() within iif()
5. **Empty collection handling** - Proper boolean semantics for empty collections

### SQL Generation Requirements

- Generate SQL CASE statements
- Handle type coercion for type consistency
- Support lazy evaluation (only evaluate selected branch)
- Support both DuckDB and PostgreSQL dialects

### Examples

| FHIRPath Expression | Expected SQL |
|---------------------|-------------|
| `iif(true, 1, 0)` | `CASE WHEN TRUE THEN 1 ELSE 0 END` |
| `iif(Patient.active, 'active', 'inactive')` | `CASE WHEN (json_extract(resource, '$.active') = 'true') THEN 'active' ELSE 'inactive' END` |
| `iif(empty(name), 'none', name.first())` | `CASE WHEN (empty_collection_condition) THEN 'none' ELSE (first_name_query) END` |

## Implementation Plan

### Step 1: Implement visit_conditional Method

Add method in `ASTToSQLTranslator` class:

```python
def visit_conditional(self, node: ConditionalNode) -> SQLFragment:
    """Translate iif() conditional expression to SQL CASE statement.

    Args:
        node: ConditionalNode with condition, true_expr, false_expr

    Returns:
        SQLFragment with CASE expression

    Raises:
        FHIRPathTranslationError: If type coercion fails
    """
    # Translate condition
    condition_fragment = self.visit(node.condition)
    condition_sql = condition_fragment.expression

    # Translate true branch
    true_fragment = self.visit(node.true_expr)
    true_sql = true_fragment.expression

    # Translate false branch
    false_fragment = self.visit(node.false_expr)
    false_sql = false_fragment.expression

    # Ensure type consistency - add CAST if needed
    # SQL CASE requires same type in all branches
    true_sql = self._ensure_type_compatibility(true_sql, false_sql, node)
    false_sql = self._ensure_type_compatibility(false_sql, true_sql, node)

    # Build CASE expression
    sql = f"CASE WHEN {condition_sql} THEN {true_sql} ELSE {false_sql} END"

    return SQLFragment(
        expression=sql,
        source_table=self.context.current_table,
        dependencies=condition_fragment.dependencies + true_fragment.dependencies + false_fragment.dependencies
    )
```

### Step 2: Type Compatibility Helper

Add helper method for type coercion:

```python
def _ensure_type_compatibility(self, sql: str, reference_sql: str, node: ASTNode) -> str:
    """Ensure SQL expression matches reference type, adding CAST if needed.

    This handles the SQL requirement that CASE branches have compatible types.
    """
    # Detect type from reference_sql and ensure sql matches
    # Add CAST expression if type mismatch detected
    # Return original sql if types compatible
    return sql  # Implementation to be detailed
```

### Step 3: Handle Edge Cases

**Empty collections**: Evaluate condition correctly with empty input
**Boolean literals**: Handle true/false constants
**Nested conditionals**: Support iif() within branches
**Type mismatches**: Add SQL CAST for type coercion

## Acceptance Criteria

1. ✅ All iif() tests pass (~10-15 tests)
2. ✅ Nested conditionals work correctly
3. ✅ Type consistency maintained across branches
4. ✅ Both DuckDB and PostgreSQL dialects supported
5. ✅ No regression on existing tests
6. ✅ Proper boolean semantics for empty collections

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_translator_conditional.py`:

- Basic iif() with boolean literals
- iif() with resource data
- Nested iif() expressions
- Type coercion cases
- Empty collection edge cases

### Integration Tests

Run official test suite with conditional filter:

```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter iif
```

### Multi-Database Testing

```bash
# DuckDB
python -m tests.integration.fhirpath.official_test_runner --database_type duckdb

# PostgreSQL
python -m tests.integration.fhirpath.official_test_runner --database_type postgresql
```

## Dependencies

- None - can be implemented independently
- May overlap with type coercion work (SP-100-006)

## References

- FHIRPath Specification: https://build.fhir.org/ig/HL7/FHIRPath/
- Translator location: `fhir4ds/main/fhirpath/sql/translator.py:4030-4032`
- Official tests: `tests/compliance/fhirpath/official_tests.xml` (testCollectionBoolean group)

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: None
