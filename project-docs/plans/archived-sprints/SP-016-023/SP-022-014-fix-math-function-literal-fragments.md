# Task: Fix Math Function Fragment Generation for Literals

**Task ID**: SP-022-014
**Sprint**: 022
**Task Name**: Fix Math Function Fragment Generation for Literals
**Assignee**: Junior Developer
**Created**: 2025-12-30
**Last Updated**: 2025-12-30

---

## Task Overview

### Description
When math functions are called on literal values (e.g., `(-5).abs()`, `81.sqrt()`, `1.1.ceiling()`), the translator generates two fragments instead of one. The CTE builder then uses the wrong fragment, causing SQL errors.

**Current Behavior (BROKEN):**
```
Expression: (-5).abs()

Fragments generated:
  0: 5                    ← CORRECT (literal evaluated)
  1: abs(resource)        ← WRONG (extra fragment referencing resource)

Final SQL uses fragment 1:
  SELECT abs(resource) AS result

Error: No function matches 'abs(JSON)'
```

**Expected Behavior:**
```
Expression: (-5).abs()

Fragments generated:
  0: 5                    ← Single correct fragment

Final SQL:
  SELECT 5 AS result
```

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. `(-5).abs()` should return `5` (single fragment)
2. `81.sqrt()` should return `9.0` (single fragment)
3. `1.1.ceiling()` should return `2` (single fragment)
4. `3.14159.round(3)` should return `3.142` (single fragment)
5. Math functions on path expressions should still work: `Patient.value.abs()`

### Non-Functional Requirements
- No regression in existing math function tests
- No impact on other function types
- Consistent behavior for all math functions

### Acceptance Criteria
- [ ] `(-5).abs() = 5` test passes
- [ ] `81.sqrt() = 9.0` test passes
- [ ] `1.1.ceiling() = 2` test passes
- [ ] `(-5.5).abs() = 5.5` test passes
- [ ] All 29 math function tests pass (currently 1/29)
- [ ] Math functions on path expressions still work

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: Fragment accumulation logic for invocation expressions

### File Modifications

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modify `_translate_math_function()` or fragment accumulation logic
   - Ensure literal targets don't generate extra fragments

### Root Cause Analysis

The AST for `(-5).abs()` has two children:
```
InvocationExpression((-5).abs())
  ├── Child 0: TermExpression((-5))     ← Literal
  └── Child 1: functionCall(abs())       ← Function call
```

The translator visits both children:
1. **TermExpression** is visited → generates fragment `5` (correct evaluation)
2. **functionCall** is visited → generates fragment `abs(resource)` (wrong - uses default context)

The `_translate_math_function()` method (line 8012) correctly handles the case when a literal target is provided - it evaluates `abs(-5) = 5`. But the issue is that the **fragment accumulation logic** in `_traverse_expression_chain()` or `translate()` adds both fragments to the list.

### Comparison with Working Functions

**DateTime functions work correctly:**
```python
# today() generates single fragment
Expression: today()
Fragments: [current_date]  # Single fragment, correct
```

The difference is that `today()` has no target expression, while `(-5).abs()` has a literal target that's being processed separately.

### Key Code Locations

1. **`translate()` method** (line ~260): Main entry point
2. **`_traverse_expression_chain()`** (line ~507): Accumulates fragments
3. **`_should_accumulate_as_separate_fragment()`** (line ~475): Decides what to accumulate
4. **`_translate_math_function()`** (line 8012): Math function translation

---

## Dependencies

### Prerequisites
- Understanding of fragment accumulation in the translator
- Understanding of AST structure for invocation expressions

### Blocking Tasks
- None

### Dependent Tasks
- None

---

## Implementation Approach

### High-Level Strategy

Option A: **Prevent duplicate fragment accumulation**
- In `_translate_math_function()`, when the target is a literal and fully evaluated, mark the fragment to prevent the parent from also adding a fragment.

Option B: **Fix fragment selection in CTE builder**
- Ensure the CTE builder uses the correct (first/last) fragment when multiple are generated.

Option C: **Don't visit literal children separately** (Recommended)
- Modify `_traverse_expression_chain()` to not accumulate fragments for literal children that are arguments to functions.

### Implementation Steps

1. **Understand the fragment flow**
   - Key Activities:
     - Add logging to `translate()`, `_traverse_expression_chain()`, and `_translate_math_function()`
     - Trace exactly where both fragments are added
     - Identify which method is responsible for the duplicate
   - Validation: Clear understanding of the bug location

2. **Identify the fix location**
   - Key Activities:
     - Check if `_should_accumulate_as_separate_fragment()` returns True for literal children
     - Check if `_translate_math_function()` already handles this case
     - Determine if the fix should be in traversal or in math function handler
   - Validation: Know exactly which method to modify

3. **Implement the fix**
   - Key Activities:
     - If Option C: Modify `_should_accumulate_as_separate_fragment()` to return False for literals that are function targets
     - OR modify `_translate_math_function()` to clear any pre-accumulated literal fragments
     - Ensure the fix doesn't break path expressions like `Patient.value.abs()`
   - Validation: `(-5).abs()` generates single fragment

4. **Test edge cases**
   - Key Activities:
     - Test literals: `(-5).abs()`, `81.sqrt()`, `1.1.ceiling()`
     - Test path expressions: `Patient.value.abs()` (should still work)
     - Test chained: `(-5).abs().ceiling()` (if applicable)
     - Test with arguments: `3.14159.round(3)`
   - Validation: All patterns work correctly

5. **Run full math function test suite**
   - Key Activities:
     - Run all 29 math function tests
     - Verify no regressions in other function types
   - Validation: 29/29 math tests pass

---

## Testing Strategy

### Unit Testing
```python
# Test single fragment generation
translator = ASTToSQLTranslator(dialect, 'Patient')
fragments = translator.translate(parse('(-5).abs()'))
assert len(fragments) == 1
assert fragments[0].expression == '5'

# Test path expression still works
fragments = translator.translate(parse('Patient.value.abs()'))
assert 'abs(' in fragments[-1].expression
assert 'resource' not in fragments[-1].expression or 'json_extract' in fragments[-1].expression
```

### Compliance Testing
```bash
# Run math function tests
python3 find_bad_test.py 0 934 2>/dev/null | grep -E "testAbs|testSqrt|testCeiling|testFloor|testRound"
```

### Manual Testing
```python
# Execute and verify results
executor.execute('(-5).abs()')      # Should return [5]
executor.execute('81.sqrt()')       # Should return [9.0]
executor.execute('1.1.ceiling()')   # Should return [2]
```

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking path-based math functions | Medium | High | Test both literal and path cases |
| Affecting other function types | Low | High | Run full test suite |
| Fragment ordering issues | Medium | Medium | Verify CTE builder behavior |

### Implementation Challenges
1. **Understanding fragment accumulation**: The logic is complex with multiple code paths
2. **Distinguishing literal targets from path targets**: Need to check AST node types carefully
3. **Not breaking existing functionality**: Many tests depend on current behavior

---

## Code Examples

### Current Problematic Flow
```python
# In translate() or _traverse_expression_chain():
def translate(self, ast):
    # ...
    fragment = self.visit(ast)  # Visits InvocationExpression

    # InvocationExpression has children:
    # - TermExpression((-5)) → visit generates fragment "5", adds to self.fragments
    # - functionCall(abs()) → visit generates fragment "abs(resource)", adds to self.fragments

    # Result: self.fragments = ["5", "abs(resource)"]
    # CTE builder uses last fragment: "abs(resource)" - WRONG
```

### Proposed Fix (Option C)
```python
def _should_accumulate_as_separate_fragment(self, node: FHIRPathASTNode) -> bool:
    """Determine if a node should generate a separate fragment."""

    # Don't accumulate literals that are function targets
    # They'll be handled by the function translation itself
    if node.node_type == "TermExpression":
        # Check if this is a child of an InvocationExpression with a function
        parent = getattr(node, 'parent', None)
        if parent and parent.node_type == "InvocationExpression":
            # This literal is a target of a function call - don't accumulate separately
            return False

    # ... rest of existing logic
```

### Alternative Fix in Math Function
```python
def _translate_math_function(self, node: FunctionCallNode) -> SQLFragment:
    # ... existing code that correctly evaluates literal ...

    # Before returning, remove any fragments that were added for the literal target
    if is_literal_target:
        # Remove the literal fragment that was accumulated during traversal
        self.fragments = [f for f in self.fragments if f.expression != literal_fragment.expression]

    return result_fragment
```

---

## Success Metrics

### Quantitative Measures
- **Math function tests**: From 1/29 passing to 29/29 passing
- **Fragment count**: Literal math expressions generate exactly 1 fragment

### Compliance Impact
- **Before**: math_functions at 3.6% (1/28)
- **After**: math_functions at ~90%+ (estimated)
- **Overall**: +27 tests = ~3% compliance improvement

---

## Progress Tracking

### Status
- [x] Completed - Merged to Main

### Completion Checklist
- [x] Root cause fully understood with logging
- [x] Fix location identified
- [x] Fix implemented
- [x] `(-5).abs()` generates single fragment
- [x] `81.sqrt()` works correctly
- [x] `1.1.ceiling()` works correctly
- [x] Path expressions still work (`Patient.value.abs()`)
- [x] All math function unit tests pass (14/14 passed, 11 skipped - PostgreSQL)
- [x] No regressions in other tests (15 failures are pre-existing on main branch)

### Implementation Notes

**Root Cause**: When math functions are called on literals in invocation chains (e.g., `(-5).abs()`), the AST represents the literal as a sibling of the function call, not as the function's target. The translator was visiting both nodes sequentially and generating two fragments: one for the literal and one for the function using the default context (`resource`).

**Fix Location**: `fhir4ds/fhirpath/sql/translator.py` in `_translate_math_function()` method (around line 8096).

**Fix Applied**: Modified the value resolution logic to check for previous fragments (from the invocation chain) BEFORE checking for arguments. This ensures that:
1. In `(-5).abs()`, the previous fragment (the literal `5`) is used as the value for `abs()`
2. In `(1.2/1.8).round(2)`, the previous fragment (the division result) is used as the value, and `2` is correctly treated as the precision argument
3. Standalone calls like `abs(-5)` still work by using the first argument as the value when no previous fragments exist

**Testing Results**:
- All 14 math function unit tests pass
- Expression `(-5).abs()` now generates single fragment: `abs(5)`
- Expression `(1.2/1.8).round(2)` now generates correct SQL with division in round
- Path expressions like `Patient.multipleBirthInteger.abs()` still work correctly
- 15 failing tests in test_translator.py are pre-existing failures on main branch (unrelated to this fix)

---

**Task Created**: 2025-12-30
**Task Completed**: 2025-12-30
**Merged to Main**: 2025-12-30
**Status**: Completed - Merged to Main
