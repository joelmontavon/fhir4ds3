# Task SP-110-008: Quick Wins - Remaining Edge Cases

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Bug Fix
**Complexity:** LOW
**Priority:** P3
**Estimated Effort:** 4-6 hours

---

## Task Description

Fix remaining edge cases in boolean_logic, path_navigation, datetime, and math to achieve 100% pass rate across all remaining categories.

## Current State

**Remaining Gap:** 5 tests across various categories
**Impact:** +0.5% overall compliance

## Key Issues

### 1. Boolean Logic Edge Cases
- `empty().not()` logic incorrect
- Boolean conversion edge cases
- Null handling in boolean operations

### 2. DateTime Comparisons
- `now() > today()` comparison
- DateTime precision issues
- Timezone handling in comparisons

### 3. Path Navigation Edge Cases
- Complex path navigation
- Deep nesting issues
- Traversal edge cases

### 4. Math Function Edge Cases
- Rounding precision
- Trigonometry functions
- Special value handling (infinity, NaN)

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

### Step 1: Fix `empty().not()` Logic
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `not()` operator translation for collections:
- Handle `empty().not()` correctly
- Generate proper boolean conversion SQL for collections
- Ensure correct negation logic

### Step 2: Fix DateTime Comparisons
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix datetime comparison translation:
- Handle `now() > today()` comparison correctly
- Normalize datetime precision in SQL
- Handle timezone in comparisons

### Step 3: Fix Path Navigation Edge Cases
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix path navigation translation:
- Handle deep nesting correctly
- Fix traversal edge cases
- Generate correct path expressions

### Step 4: Fix Math Function Edge Cases
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix math function translation:
- Handle special values (infinity, NaN)
- Use dialect-specific math functions
- Handle edge cases correctly

## Testing Strategy

1. **Unit Tests:** Test each fix
2. **Integration Tests:** Test combined scenarios
3. **Compliance Tests:** Run full compliance suite
4. **Edge Case Tests:** Test all edge cases

## Success Criteria

- [ ] All 5 remaining tests passing
- [ ] `empty().not()` working correctly
- [ ] DateTime comparisons fixed
- [ ] Path navigation edge cases resolved
- [ ] Math edge cases handled
- [ ] No regressions
- [ ] Code reviewed and approved
- [ ] **100% COMPLIANCE ACHIEVED**

## Dependencies

- None (can start immediately)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - All translation fixes (FIX LOCATION)
**Supporting:**
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata
- `fhir4ds/main/dialects/` - Dialect-specific math functions
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

## Notes

- This is a LOW complexity task
- Final task to achieve 100%
- Each fix is isolated
- Test thoroughly to confirm 100%
- Celebrate when complete!

## Expected Compliance Impact

**Before:** 99.5% (929/934)
**After:** 100.0% (934/934)
**Improvement:** +0.5%

**GOAL ACHIEVED: 100% FHIRPath COMPLIANCE**
