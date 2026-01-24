# Task: Fix iif() Criterion Validation

**Task ID**: SP-022-011
**Sprint**: 022
**Task Name**: Fix iif() Criterion Validation
**Assignee**: Junior Developer
**Created**: 2025-12-30
**Last Updated**: 2025-12-30

---

## Task Overview

### Description
The `iif()` function incorrectly rejects valid boolean literal criteria like `true` and `false`. The current validation logic checks the AST node type but doesn't properly handle wrapper nodes like `TermExpression` that wrap boolean literals.

**Current Behavior (WRONG):**
```
Expression: iif(true, 'yes', 'no')
Error: [FP030] iif() criterion must be a boolean expression, got: TermExpression
```

**Expected Behavior:**
```
Expression: iif(true, 'yes', 'no')
Result: 'yes'
```

The error logs show:
```
Error visiting node TermExpression(iif(true,true,false)): [FP030] iif() criterion must be a boolean expression, got: TermExpression
Error visiting node TermExpression(iif({},true,false)): [FP030] iif() criterion must be a boolean expression, got: TermExpression
```

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Boolean literals**: `iif(true, a, b)` and `iif(false, a, b)` must be accepted
2. **Comparison results**: `iif(1 > 0, a, b)` must work (already works)
3. **Function results**: `iif(exists(), a, b)` must work (already works)
4. **Union expressions**: `iif(1|2, a, b)` should correctly be rejected (not boolean)
5. **Empty collections**: `iif({}, a, b)` - check FHIRPath spec for expected behavior

### Non-Functional Requirements
- **Compliance**: Match FHIRPath specification for iif() semantics
- **Error Messages**: Clear error messages for genuinely invalid criteria
- **Performance**: No performance impact from additional validation

### Acceptance Criteria
- [ ] `iif(true, 'yes', 'no')` returns `'yes'`
- [ ] `iif(false, 'yes', 'no')` returns `'no'`
- [ ] `iif(true, true, false)` returns `true`
- [ ] `iif(Patient.name.exists(), 'named', 'unnamed')` works
- [ ] Invalid criteria still produce appropriate errors
- [ ] All existing passing iif() tests continue to pass

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: `_is_boolean_expression()` method

### File Modifications

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modify `_is_boolean_expression()` (around line 4014)
   - Add logic to unwrap `TermExpression` and other wrapper nodes

### Root Cause Analysis

The current `_is_boolean_expression()` method (lines 4014-4055) checks:
```python
def _is_boolean_expression(self, node) -> bool:
    # Literal boolean values
    if hasattr(node, 'node_type') and node.node_type == "literal":
        if isinstance(node.value, bool):
            return True
```

**The Problem**: When `true` is parsed, it becomes:
```
TermExpression
  └── BooleanLiteral (value=True)
```

The method checks for `node_type == "literal"` but receives `node_type == "TermExpression"`. It needs to **unwrap wrapper nodes** to find the actual boolean literal inside.

### AST Wrapper Nodes

The FHIRPath parser wraps expressions in various container nodes:
- `TermExpression` - wraps terms
- `InvocationExpression` - wraps invocations
- `PolarityExpression` - wraps polarity (positive/negative)

The fix must recursively unwrap these to find the actual expression type.

---

## Dependencies

### Prerequisites
- Understanding of FHIRPath AST structure
- Familiarity with how wrapper nodes work

### Blocking Tasks
- None

### Dependent Tasks
- None

---

## Implementation Approach

### High-Level Strategy
Modify `_is_boolean_expression()` to:
1. First unwrap any wrapper nodes (TermExpression, InvocationExpression, etc.)
2. Then check if the unwrapped node is a boolean expression
3. Recursively handle nested wrappers

### Implementation Steps

1. **Add wrapper node detection and unwrapping**
   - Key Activities:
     - Create helper method `_unwrap_expression_node(node)` or add unwrapping logic
     - Handle: TermExpression, InvocationExpression, PolarityExpression
     - Recursively unwrap until reaching a non-wrapper node
   - Validation: `_unwrap_expression_node(TermExpression(BooleanLiteral))` returns `BooleanLiteral`

2. **Modify `_is_boolean_expression()` to unwrap first**
   - Key Activities:
     - At the start of `_is_boolean_expression()`, unwrap the node
     - Then apply existing boolean detection logic to unwrapped node
   - Location: Line 4014 in translator.py
   - Validation: `_is_boolean_expression(TermExpression(BooleanLiteral(True)))` returns `True`

3. **Handle BooleanLiteral node type specifically**
   - Key Activities:
     - Check for `node_type == "BooleanLiteral"` in addition to `"literal"`
     - The parsed AST may use different type names
   - Validation: Both "literal" and "BooleanLiteral" node types are handled

4. **Test edge cases**
   - Key Activities:
     - Test `iif(true, 'a', 'b')` - should work
     - Test `iif(1|2, 'a', 'b')` - should fail (not boolean)
     - Test `iif({}, 'a', 'b')` - check spec for expected behavior
   - Validation: All iif tests pass

---

## Testing Strategy

### Unit Testing
```python
# Test boolean literal detection
from fhir4ds.fhirpath.parser import FHIRPathParser
parser = FHIRPathParser()

# Parse and check AST structure
ast = parser.parse("iif(true, 'yes', 'no')").get_ast()
# Debug: print(ast) to see structure

# Execute and verify
executor.execute("iif(true, 'yes', 'no')")  # Should return ['yes']
executor.execute("iif(false, 'yes', 'no')")  # Should return ['no']
```

### Compliance Testing
```bash
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='iif')
runner.print_compliance_summary(report)
"
```

### Manual Testing
Test these expressions:
1. `iif(true, 1, 2)` -> `1`
2. `iif(false, 1, 2)` -> `2`
3. `iif(true, true, false)` -> `true`
4. `iif(1 = 1, 'equal', 'not')` -> `'equal'`
5. `iif(Patient.name.exists(), 'has name', 'no name')` -> depends on data

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Over-accepting non-boolean expressions | Medium | Medium | Keep union/collection rejection logic |
| Breaking existing iif functionality | Low | High | Run all iif tests before/after |
| Infinite recursion in unwrapping | Low | High | Add max depth limit |

### Implementation Challenges
1. **AST node type variations**: Different node types may represent the same concept
2. **Spec compliance for edge cases**: `iif({}, a, b)` behavior needs spec verification

---

## Code Examples

### Example: Unwrapping Wrapper Nodes
```python
def _unwrap_expression_node(self, node) -> Any:
    """Unwrap wrapper nodes to get the actual expression node."""
    wrapper_types = {'TermExpression', 'InvocationExpression', 'PolarityExpression', 'InvocationTerm'}

    max_depth = 10  # Prevent infinite loops
    current = node

    for _ in range(max_depth):
        if not hasattr(current, 'node_type'):
            break
        if current.node_type not in wrapper_types:
            break
        # Get the single child (wrapper nodes typically have one child)
        if hasattr(current, 'children') and len(current.children) == 1:
            current = current.children[0]
        else:
            break

    return current
```

### Example: Modified _is_boolean_expression
```python
def _is_boolean_expression(self, node) -> bool:
    """Check if an AST node represents a boolean expression."""
    # Unwrap wrapper nodes first
    unwrapped = self._unwrap_expression_node(node)

    # Literal boolean values
    if hasattr(unwrapped, 'node_type'):
        # Check for BooleanLiteral node type
        if unwrapped.node_type in ('literal', 'BooleanLiteral'):
            if isinstance(getattr(unwrapped, 'value', None), bool):
                return True
            # Also check for string 'true'/'false' in some AST representations
            if getattr(unwrapped, 'value', None) in (True, False, 'true', 'false'):
                return True

    # ... rest of existing logic for operators, functions, etc.
```

---

## Success Metrics

### Quantitative Measures
- **Target**: All 6 `iif()` related tests passing
- **Impact**: ~6 additional tests in `function_calls` category

### Compliance Impact
- **Before**: iif() tests failing with validation errors
- **After**: iif() tests passing

---

## Progress Tracking

### Status
- [x] Completed - Merged to Main

### Completion Checklist
- [x] `_unwrap_expression_node()` helper implemented
- [x] `_is_boolean_expression()` calls unwrap first
- [x] `iif(true, 'a', 'b')` works
- [x] `iif(false, 'a', 'b')` works
- [x] `iif(true, true, false)` works
- [x] Invalid criteria still rejected appropriately
- [x] DuckDB tests passing
- [x] PostgreSQL tests passing
- [x] No regressions in existing tests

---

## Implementation Summary

### Changes Made

1. **Added `_unwrap_expression_node()` method** (translator.py:4301-4336)
   - Recursively unwraps wrapper nodes (TermExpression, InvocationTerm, PolarityExpression)
   - Uses max depth of 10 to prevent infinite loops
   - Returns the innermost non-wrapper node

2. **Modified `_is_boolean_expression()` method** (translator.py:4338-4436)
   - Now calls `_unwrap_expression_node()` first to get the actual expression
   - Added detection of boolean text ('true', 'false') in literal nodes
   - Added support for empty collection '{}' as valid boolean criterion
   - Added handling for InvocationExpression ending with boolean functions
   - Extended boolean function list with additional functions (matches, contains, startswith, etc.)
   - Added detection of boolean expression types (EqualityExpression, etc.)

3. **Fixed bug in unit test file** (test_translator_conditionals.py:36)
   - Changed `parser.parse(expression.get_ast())` to `parser.parse(expression).get_ast()`

### Test Results

**Unit Tests (test_translator_conditionals.py):**
- `test_iif_generates_case_expression` - PASSED
- `test_iif_optional_false_branch_returns_empty_collection` - PASSED
- `test_iif_rejects_non_boolean_condition` - PASSED
- 3 pre-existing failures (unrelated to this fix)

**Manual Validation:**
| Expression | Expected | Result |
|------------|----------|--------|
| `iif(true, 'yes', 'no')` | Accept | PASS |
| `iif(false, 'yes', 'no')` | Accept | PASS |
| `iif(true, true, false)` | Accept | PASS |
| `iif(1 = 1, 'yes', 'no')` | Accept | PASS |
| `iif(Patient.name.exists(), 'named', 'unnamed')` | Accept | PASS |
| `iif({}, true, false)` | Accept | PASS |
| `iif('string', 'yes', 'no')` | Reject | PASS |
| `iif(1\|2, 'a', 'b')` | Reject | PASS |

### Files Modified
- `fhir4ds/fhirpath/sql/translator.py` - Core fix
- `tests/unit/fhirpath/sql/test_translator_conditionals.py` - Bug fix in test helper

---

**Task Created**: 2025-12-30
**Task Completed**: 2025-12-31
**Merged to Main**: 2025-12-31
**Status**: Completed - Merged to Main
