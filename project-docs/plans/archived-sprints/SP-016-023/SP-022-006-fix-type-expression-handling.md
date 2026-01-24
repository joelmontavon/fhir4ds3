# Task: Fix TypeExpression Handling for is/as Operations

**Task ID**: SP-022-006
**Sprint**: 022
**Task Name**: Fix TypeExpression Handling for is/as Operations
**Assignee**: Junior Developer
**Created**: 2025-12-29
**Last Updated**: 2025-12-29

---

## Task Overview

### Description
The `is` and `as` type operations fail with `[FP040] Unknown FHIR type 'Unknown'` error. The root cause is that the AST traversal visits the `TypeSpecifier` child node as a standalone expression before the parent `TypeExpression` is properly handled. The TypeSpecifier node (which contains the type name like "Quantity") gets visited independently, and when it tries to resolve the type, it can't find it in the context.

**Current Behavior (WRONG):**
```
Expression: Observation.value is Quantity

AST Traversal Order:
1. Visit TypeSpecifier(Quantity) → ERROR: Unknown FHIR type 'Unknown'
2. Visit TypeExpression(is) → Never reached due to earlier error

Error: [FP040] Unknown FHIR type 'Unknown'
```

**Expected Behavior (CORRECT):**
```
Expression: Observation.value is Quantity

AST Traversal Order:
1. TypeExpression(is) handled as a unit
2. TypeSpecifier(Quantity) read as metadata, not visited as expression
3. Result: SQL type check expression
```

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **is() operation**: `Observation.value is Quantity` should return boolean
2. **as() operation**: `Observation.value.as(Quantity).unit` should return the unit field
3. **Parenthesized form**: `(Observation.value as Quantity).unit` should work
4. **Type checking**: `Observation.issued is instant` should return true/false

### Acceptance Criteria
- [x] `Observation.value is Quantity` executes without error
- [x] `Observation.issued is instant` executes without error
- [x] `Observation.value.as(Quantity).unit` executes without error (returns None due to separate polymorphic value issue)
- [x] `(Observation.value as Quantity).unit` executes without error (returns None due to separate polymorphic value issue)
- [x] All existing passing tests continue to pass
- [x] 8 new unit tests added and passing for TypeExpression handling

---

## Technical Specifications

### Root Cause Analysis

The issue is in the AST traversal in `_traverse_expression_chain()` at `translator.py:549-561`:

```python
for i, child in enumerate(node.children):
    if self._should_accumulate_as_separate_fragment(child):
        child_fragment = self._traverse_expression_chain(child, accumulate=True)
    else:
        child_fragment = self.visit(child)  # ← TypeSpecifier visited here!
```

For a `TypeExpression` node with children `[InvocationExpression, TypeSpecifier]`:
- Child 0 (InvocationExpression) should be visited to get the value expression
- Child 1 (TypeSpecifier) should NOT be visited - it's just metadata for the type name

### The Fix

**Option A (Recommended)**: Modify `_should_accumulate_as_separate_fragment()` to skip TypeSpecifier nodes entirely:

```python
def _should_accumulate_as_separate_fragment(self, node) -> bool:
    node_type = getattr(node, 'node_type', None)

    # TypeSpecifier is metadata for TypeExpression, not a separate expression
    if node_type == 'TypeSpecifier':
        return False  # Skip processing entirely

    # ... rest of existing logic
```

**Option B**: Add early return in the TypeSpecifier handling in `visit_generic()`:

```python
def visit_generic(self, node: Any) -> SQLFragment:
    node_type = getattr(node, 'node_type', '')

    # TypeSpecifier nodes are metadata, not standalone expressions
    if node_type == 'TypeSpecifier':
        return SQLFragment(
            expression='NULL',  # Placeholder - never used
            source_table=self.context.current_table,
            requires_unnest=False,
            is_aggregate=False
        )
```

### Files to Modify

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modify `_should_accumulate_as_separate_fragment()` OR
   - Add TypeSpecifier handling in `visit_generic()`

### How to Find the Code

```bash
# Find the traversal logic
grep -n "_should_accumulate_as_separate_fragment\|_traverse_expression_chain" \
    fhir4ds/fhirpath/sql/translator.py

# Find visit_generic
grep -n "def visit_generic" fhir4ds/fhirpath/sql/translator.py
```

---

## Implementation Steps

### Step 1: Understand the Current AST Structure
Run this to see how TypeExpression AST is structured:

```bash
PYTHONPATH=. python3 << 'EOF'
from fhir4ds.fhirpath.parser import FHIRPathParser

parser = FHIRPathParser()
expr = 'Observation.value is Quantity'
ast = parser.parse(expr).get_ast()

def show_tree(node, indent=0):
    prefix = '  ' * indent
    text = getattr(node, 'text', '?')
    ntype = getattr(node, 'node_type', '?')
    print(f'{prefix}[{ntype}] text="{text}"')
    if hasattr(node, 'children') and node.children:
        for c in node.children:
            show_tree(c, indent + 1)

show_tree(ast)
EOF
```

Expected output:
```
[TypeExpression] text="is"
  [InvocationExpression] text="Observation.value"
    ...
  [TypeSpecifier] text="Quantity"
    ...
```

### Step 2: Add TypeSpecifier Skip Logic

In `translator.py`, find `_should_accumulate_as_separate_fragment()` (around line 600-650) and add:

```python
def _should_accumulate_as_separate_fragment(self, node) -> bool:
    """Determine if a node should generate its own fragment."""
    node_type = getattr(node, 'node_type', None)

    # SP-022-006: TypeSpecifier is metadata for TypeExpression, not a standalone expression
    # It should not be visited/accumulated separately
    if node_type == 'TypeSpecifier':
        return False

    # ... rest of existing implementation
```

### Step 3: Test the Fix

```bash
# Test is() operation
PYTHONPATH=. python3 << 'EOF'
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect
import json

dialect = DuckDBDialect(database=':memory:')
conn = dialect.get_connection()
conn.execute("DROP TABLE IF EXISTS resource")
conn.execute("CREATE TABLE resource (id INTEGER, resource JSON)")
conn.execute("""INSERT INTO resource VALUES (1, '{"resourceType": "Observation", "valueQuantity": {"value": 100, "unit": "mg"}}')""")

executor = FHIRPathExecutor(dialect, 'Observation')

# Test is()
details = executor.execute_with_details('Observation.value is Quantity')
print(f"is Quantity result: {list(details['results'])}")

# Test as()
details = executor.execute_with_details('Observation.value.as(Quantity).unit')
print(f"as(Quantity).unit result: {list(details['results'])}")
EOF
```

### Step 4: Run Official Compliance Tests

```bash
PYTHONPATH=. python3 tests/integration/fhirpath/official_test_runner.py --summary 2>&1 | grep -E "Type_Functions|testPolymorphism"
```

Expected improvement: Type_Functions should go from 50% (4/8) to higher.

---

## Testing Strategy

### Unit Tests to Create

Create `tests/unit/fhirpath/sql/test_translator_type_expression.py`:

```python
"""Tests for TypeExpression handling (SP-022-006)."""

import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect


@pytest.fixture
def translator():
    dialect = DuckDBDialect(database=':memory:')
    return ASTToSQLTranslator(dialect, 'Observation')


class TestIsOperationBasic:
    def test_is_quantity_does_not_raise_unknown_type(self, translator):
        """is Quantity should not raise Unknown type error."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.value is Quantity').get_ast()

        # Should not raise FHIRPathTranslationError
        fragments = translator.translate(ast)
        assert fragments, "Should produce fragments"

    def test_is_instant_does_not_raise_unknown_type(self, translator):
        """is instant should not raise Unknown type error."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.issued is instant').get_ast()

        fragments = translator.translate(ast)
        assert fragments, "Should produce fragments"


class TestAsOperationBasic:
    def test_as_quantity_with_field_access(self, translator):
        """as(Quantity).unit should work without error."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.value.as(Quantity).unit').get_ast()

        fragments = translator.translate(ast)
        assert fragments, "Should produce fragments"
        assert 'unit' in fragments[-1].expression.lower()
```

### Compliance Testing

Run the official test runner and verify these tests pass:
- testPolymorphismIsA2: `Observation.value is Quantity`
- testPolymorphismIsA3: `Observation.issued is instant`
- testPolymorphismAsA: `Observation.value.as(Quantity).unit`
- testPolymorphismAsAFunction: `(Observation.value as Quantity).unit`

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Fix breaks other TypeExpression handling | Low | High | Run full test suite before/after |
| TypeSpecifier needed elsewhere | Low | Medium | Check all usages of node_type == 'TypeSpecifier' |

### Implementation Challenges
1. **AST Traversal Order**: Need to understand exactly when TypeSpecifier gets visited
2. **Multiple Code Paths**: Both `_traverse_expression_chain` and `visit()` may need updates

---

## Success Metrics

### Quantitative Measures
- **Before**: 4/8 Type_Functions tests passing (50%)
- **Target**: 7/8 Type_Functions tests passing (87.5%)
- **Compliance Improvement**: +4 tests passing

### Compliance Impact
- **testPolymorphismIsA2**: Should PASS
- **testPolymorphismIsA3**: Should PASS
- **testPolymorphismAsA**: Should PASS
- **testPolymorphismAsAFunction**: Should PASS

---

## Progress Tracking

### Status
- [x] Completed - Pending Review

### Completion Checklist
- [x] Root cause confirmed with debugging
- [x] Fix implemented in ast_extensions.py (routing TypeExpression to TypeExpressionAdapter)
- [x] Unit tests created and passing (8 new tests in TestTypeExpressionParsing)
- [x] Type functions integration tests pass (11/11)
- [x] No regressions in existing tests (pre-existing failures confirmed on main)
- [ ] Code reviewed and approved

### Implementation Notes

**Root Cause**: TypeExpression nodes with `category=FUNCTION_CALL` were being treated as wrapper nodes and routed to `visit_generic()`, which then visited all children including TypeSpecifier. The TypeSpecifier (with `category=TYPE_OPERATION`) was processed independently before its parent TypeExpression, causing the "Unknown FHIR type" error.

**Fix Applied**: Added explicit check for `node_type == 'TypeExpression'` in the FUNCTION_CALL category handling to route these nodes directly to a TypeExpressionAdapter, bypassing the wrapper node logic. Also added TypeSpecifierPlaceholder for TypeSpecifier nodes that are visited outside their parent context.

**Files Changed**:
- `fhir4ds/fhirpath/parser_core/ast_extensions.py` - Added TypeExpressionAdapter in FUNCTION_CALL branch and TypeSpecifierPlaceholder in TYPE_OPERATION branch
- `tests/unit/fhirpath/sql/test_translator_type_operations.py` - Added TestTypeExpressionParsing class with 8 tests

---

**Task Created**: 2025-12-29
**Task Completed**: 2025-12-29
**Status**: Completed - Pending Review
