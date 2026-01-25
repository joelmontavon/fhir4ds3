# Task: SP-100-003 - Fix Empty Collection Handling

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P0 (Critical)
**Estimated Effort**: 10-15 hours

---

## Task Description

Implement proper empty collection `{}` semantics per FHIRPath specification throughout the translator. Currently, empty collections cause errors like "Could not convert string '{}' to BOOL/INT32".

## Current State

**Issue**: Empty collection literal `{}` is not handled consistently across functions.

**Error Examples**:
- `true = {}` should evaluate to false but causes conversion error
- `'1.1'.toInteger() = {}` should handle empty collection result
- Empty collections in comparisons cause SQL conversion errors

**FHIRPath Spec Requirements**:
- Empty collections should evaluate to `false` in boolean context
- Empty collections have special semantics in comparisons
- Empty() function should return `true` for empty collections

## Requirements

### Functional Requirements

1. **Empty collection literal**: `{}` should be recognized and handled specially
2. **Boolean context**: `{}` in boolean expressions evaluates to false
3. **Comparisons**: `{}` compared with any value should return false
4. **Type operations**: `{}.is(X)` should work correctly
5. **Consistent semantics**: All functions handle empty collections uniformly

### SQL Generation Requirements

- Detect empty collection literals during translation
- Generate appropriate SQL for empty collection handling
- Use `CASE` statements for boolean context evaluation
- Handle empty collections in comparisons with proper NULL semantics

### Examples

| FHIRPath Expression | Expected Behavior |
|---------------------|-------------------|
| `{}.exists()` | false |
| `{}.empty()` | true |
| `{} | false (in boolean context) |
| `{} = 5` | false |
| `{1, 2} = {}` | false |
| `{}` | Empty collection |

## Implementation Plan

### Step 1: Detect Empty Collection Literals

Add helper method in `ASTToSQLTranslator`:

```python
def _is_empty_collection_literal(self, node: ASTNode) -> bool:
    """Check if node represents empty collection literal {}."""
    if isinstance(node, LiteralNode):
        # Check for empty collection marker
        return hasattr(node, 'is_empty_collection') and node.is_empty_collection
    return False
```

### Step 2: Create Empty Collection SQL Handler

```python
def _translate_empty_collection(self, context: str) -> str:
    """Generate SQL for empty collection handling.

    For boolean context: Returns 'FALSE' or equivalent
    For comparisons: Returns appropriate NULL/falsy value
    """
    # Boolean context - empty collections are falsy
    if context == 'boolean':
        return 'FALSE'

    # Comparison context - empty collections don't match anything
    if context == 'comparison':
        return 'NULL'  # Won't equal anything

    # Default empty collection representation
    return 'ARRAY[]'  # Empty JSON array
```

### Step 3: Update Boolean Expressions

Modify comparison and boolean logic translators to check for empty collections:

```python
def _translate_equality_operator(self, left_expr, right_expr, operator):
    # Check if either side is empty collection
    left_empty = self._is_empty_collection_literal(left_node)
    right_empty = self._is_empty_collection_literal(right_node)

    if left_empty or right_empty:
        # Generate special handling
        # Empty collections don't equal anything (including each other)
        pass
```

### Step 4: Update Collection Functions

Ensure functions like `exists()`, `empty()`, `count()` handle empty collections:

```python
def _translate_exists(self, node: FunctionCallNode) -> SQLFragment:
    # Check if input is empty collection literal
    # Special case: empty.exists() returns FALSE, empty.empty() returns TRUE
```

## Acceptance Criteria

1. ✅ All empty collection tests pass (~17 tests)
2. ✅ `true = {}` evaluates to false
3. ✅ `'1.1'.toInteger() = {}` handles correctly
4. ✅ `{}`.exists() returns false
5. ✅ `{}`.empty() returns true
6. ✅ Consistent behavior across all functions
7. ✅ No regression on existing tests
8. ✅ Both dialects supported

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_translator_empty_collections.py`:

- Boolean context with empty collections
- Comparisons with empty collections
- Type operations with empty collections
- exists(), empty() with empty collections
- Nested operations with empty collections

### Integration Tests

Run official test suite with empty collection filter:

```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter empty
```

## Dependencies

- None - can be implemented independently
- May help with other collection function fixes

## References

- FHIRPath Specification: https://build.fhir.org/ig/HL7/FHIRPath/
- Test suite: `tests/compliance/fhirpath/official_tests.xml`
- Error location: Multiple translator methods

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: None
