# Task SP-012-004-B: Fix Math Function Error Handling

**Task ID**: SP-012-004-B
**Sprint**: Sprint 012 - PostgreSQL Execution and Compliance Advancement
**Parent Task**: SP-012-004 (Phase 1 completed)
**Task Name**: Fix Math Function Error Handling
**Assignee**: TBD
**Created**: 2025-10-23
**Priority**: Medium

---

## Task Overview

### Description

Fix 2 failing tests related to math function error handling. Tests expect errors to be raised when math functions receive too many arguments, but current implementation is not raising these errors.

**Parent Task Status**: SP-012-004 Phase 1 successfully merged (9/9 type registry fixes completed). This task addresses remaining Phase 3 work.

### Category
- [x] Bug Fix
- [ ] Feature Implementation
- [ ] Architecture Enhancement
- [ ] Testing

### Priority
- [ ] Critical (Blocker for sprint goals)
- [ ] High (Important for sprint success)
- [x] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Failing Tests (2)

```
tests/unit/fhirpath/sql/test_translator_advanced_math_functions.py::TestAdvancedMathFunctionErrorHandling::test_sqrt_with_too_many_arguments_raises_error
tests/unit/fhirpath/sql/test_translator_math_functions.py::TestMathFunctionErrorHandling::test_math_function_with_too_many_arguments_raises_error
```

### Expected Behavior

Math functions should validate argument counts and raise appropriate errors when:
- Too many arguments provided
- Too few arguments provided
- Invalid argument types

### Acceptance Criteria

- [x] Math functions validate argument counts
- [x] Appropriate errors raised for invalid argument counts
- [x] Both failing tests pass
- [x] Zero regressions in other math function tests
- [x] Error messages are clear and helpful

---

## Technical Investigation Required

### Step 1: Review Test Expectations

**Files**:
- `tests/unit/fhirpath/sql/test_translator_advanced_math_functions.py`
- `tests/unit/fhirpath/sql/test_translator_math_functions.py`

**Actions**:
1. Run tests to see exact failure messages
2. Understand what errors should be raised
3. Identify which exception types are expected

### Step 2: Review Current Implementation

**File**: `fhir4ds/fhirpath/sql/translator.py`

**Methods to Review**:
- Math function translation methods
- Argument validation logic
- Error handling paths

**Questions**:
- Where should argument count validation occur?
- What error should be raised? (FHIRPathTranslationError? FHIRPathValidationError?)
- Was this validation removed during type casting changes?

### Step 3: Identify Root Cause

**Possible Causes**:
1. Argument validation code was accidentally removed
2. Error handling path was modified
3. Validation logic was bypassed
4. Exception type changed

---

## Implementation Approach

### Recommended Steps

1. **Run Failing Tests** (0.5 hours):
   ```bash
   pytest tests/unit/fhirpath/sql/test_translator_advanced_math_functions.py::TestAdvancedMathFunctionErrorHandling::test_sqrt_with_too_many_arguments_raises_error -v
   pytest tests/unit/fhirpath/sql/test_translator_math_functions.py::TestMathFunctionErrorHandling::test_math_function_with_too_many_arguments_raises_error -v
   ```

2. **Review Function Translation Code** (0.5 hours):
   - Locate math function handlers in translator
   - Check for argument validation
   - Compare with working functions (if any)

3. **Implement Fix** (1 hour):
   - Add/restore argument count validation
   - Ensure proper error type raised
   - Add clear error messages

4. **Test and Verify** (0.5 hours):
   - Run failing tests
   - Run all math function tests
   - Run full test suite

**Total Estimate**: 2-3 hours

---

## Example Fix (Hypothetical)

**Before** (missing validation):
```python
def _translate_sqrt_function(self, node: FunctionCallNode) -> SQLFragment:
    # Missing argument count check
    arg_fragment = self.visit(node.children[0])
    return self.dialect.generate_sqrt(arg_fragment.expression)
```

**After** (with validation):
```python
def _translate_sqrt_function(self, node: FunctionCallNode) -> SQLFragment:
    # Validate argument count
    if len(node.children) != 1:
        raise FHIRPathTranslationError(
            f"sqrt() expects exactly 1 argument, got {len(node.children)}"
        )

    arg_fragment = self.visit(node.children[0])
    return self.dialect.generate_sqrt(arg_fragment.expression)
```

---

## Testing Strategy

### Unit Tests
- Run 2 failing error handling tests
- Run all math function tests
- Run all advanced math function tests

### Regression Tests
- Full test suite must pass
- Verify no impact on working math functions
- Verify error handling works for all functions

---

## Dependencies

### Prerequisites
- ✅ SP-012-004 Phase 1 merged
- ✅ Translator infrastructure stable

### Blocking
- None (can proceed independently)

---

## Success Metrics

- ✅ Both math function error tests passing
- ✅ Zero regressions
- ✅ Clear, helpful error messages
- ✅ Consistent error handling across all math functions

---

## Notes

- Likely a straightforward fix
- May have been accidentally removed during type casting implementation
- Should follow existing error handling patterns
- Keep changes minimal and focused

---

**Created**: 2025-10-23
**Status**: ✅ Completed and Merged to Main
**Estimated Effort**: 2-3 hours
**Actual Effort**: 1.5 hours
**Completed**: 2025-10-23
**Merged**: 2025-10-23

---

## Implementation Summary

### Changes Made

**File**: `fhir4ds/fhirpath/sql/translator.py` (lines 4970-4985)

Added function-specific argument validation that distinguishes between:
- Functions accepting optional additional arguments (`round`, `truncate`)
- Functions accepting no additional arguments (`abs`, `ceiling`, `floor`, `sqrt`, `exp`, `ln`, `log`)

### Root Cause

The original validation at line 4970 checked `len(remaining_args) > 1`, which only triggered for 2+ additional arguments. Since the first argument is consumed as the value before this check, functions like `abs(5, 10)` only had 1 remaining arg and didn't trigger the error.

### Solution

Implemented function-specific validation:
- Functions in `functions_with_optional_arg` set allow 0-1 additional arguments
- All other math functions must have 0 additional arguments
- Error message reports total argument count correctly

### Test Results

✅ Both failing tests now pass:
- `test_math_function_with_too_many_arguments_raises_error` - PASSED
- `test_sqrt_with_too_many_arguments_raises_error` - PASSED

✅ Zero regressions:
- All 25 basic math function tests - PASSED
- All 35 advanced math function tests - PASSED

### Architectural Alignment

✅ Business logic in translator (not dialect)
✅ Clear error messages with helpful context
✅ Consistent validation across all math functions
✅ Maintains support for optional precision argument in round/truncate
