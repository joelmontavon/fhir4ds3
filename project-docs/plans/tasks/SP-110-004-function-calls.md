# Task SP-110-004: Function Calls - Signature Resolution

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Feature Implementation
**Complexity:** MEDIUM
**Priority:** P0
**Estimated Effort:** 10-16 hours

---

## Task Description

Implement function signature registry and parameter type coercion to achieve 100% pass rate in function_calls category.

## Current State

**Category:** function_calls
**Current Pass Rate:** 55.8% (63/113 tests passing)
**Gap:** 50 failing tests
**Impact:** +5.4% overall compliance

## Key Issues

### 1. `iif()` Function with Collection Arguments
- `iif()` expects single-value criteria
- Collection arguments cause validation errors
- Implicit single-value conversion needed

### 2. Function Signature Resolution
- Multiple function signatures not supported
- Overload resolution missing
- Parameter type matching incomplete

### 3. Parameter Type Coercion
- Automatic type coercion missing
- String to number conversion
- Collection to single value conversion

### 4. Missing Function Implementations
- Some functions not implemented
- Incomplete function coverage
- Edge cases not handled

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

### Step 1: Implement Function Signature Registry
**Location:** `fhir4ds/main/fhirpath/sql/translator.py` or new module

Add function signature resolution logic:
- Track function signatures for overload resolution
- Implement parameter type matching
- Resolve best matching signature for function calls

### Step 2: Add Parameter Type Coercion
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Add parameter coercion in function call translation:
- Apply type coercion rules before generating SQL
- Handle string to number conversion
- Extract single value from collections

### Step 3: Fix `iif()` Validation
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `iif()` function translation:
- Convert collection condition to single value
- Generate appropriate CASE expression in SQL
- Handle collection-to-single-value coercion

### Step 4: Complete Missing Function Implementations
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Review and implement missing function translations:
- Identify missing functions from failing tests
- Add translation logic for missing functions
- Handle edge cases

## Testing Strategy

1. **Unit Tests:** Test signature resolution
2. **Integration Tests:** Test type coercion
3. **Compliance Tests:** Run full function_calls suite
4. **Edge Cases:** Test overload resolution

## Success Criteria

- [ ] All 50 function_calls tests passing
- [ ] Function signature registry working
- [ ] Parameter type coercion functional
- [ ] `iif()` handles collections
- [ ] All missing functions implemented
- [ ] No regressions
- [ ] Code reviewed and approved

## Dependencies

- SP-110-003 (Type Functions) - MUST COMPLETE FIRST
- Type system needed for signature resolution

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - Function call translation (FIX LOCATION)
**Supporting:**
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata types
- `fhir4ds/main/fhirpath/types/` - Type system definitions
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

## Notes

- This is a MEDIUM complexity task
- Depends on SP-110-003 completion
- Signature resolution is critical for function calls
- Consider creating function signature documentation
- Test with various argument type combinations

## Expected Compliance Impact

**Before:** 86.0% (803/934)
**After:** 91.4% (853/934)
**Improvement:** +5.4%
