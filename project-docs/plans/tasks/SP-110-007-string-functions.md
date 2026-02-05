# Task SP-110-007: String Functions - Edge Cases

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Bug Fix
**Complexity:** LOW
**Priority:** P2
**Estimated Effort:** 6-10 hours

---

## Task Description

Fix remaining string function edge cases to achieve 100% pass rate in string_functions category.

## Current State

**Category:** string_functions
**Current Pass Rate:** 75.4% (49/65 tests passing)
**Gap:** 16 failing tests
**Impact:** +1.7% overall compliance

## Key Issues

### 1. `matches()` with Regex Patterns
- Regex pattern matching incorrect
- Special character escaping
- Case sensitivity handling
- Multi-line matching

### 2. `replaceAll()` Edge Cases
- Empty string replacement
- Overlapping matches
- Special regex characters
- Null handling

### 3. `substring()` Boundary Conditions
- Start index out of bounds
- Length longer than string
- Negative indices
- Empty string handling

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

### Step 1: Fix Regex Pattern Matching
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `matches()` function translation:
- Generate appropriate regex matching SQL
- Handle special character escaping
- Handle case sensitivity
- Use dialect-specific regex functions

### Step 2: Fix `replaceAll()` Edge Cases
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `replaceAll()` function translation:
- Generate SQL for regex replacement
- Handle empty string replacement
- Handle overlapping matches
- Escape special regex characters

### Step 3: Fix `substring()` Boundary Conditions
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `substring()` function translation:
- Generate SQL with proper bounds checking
- Handle start index out of bounds
- Handle length longer than string
- Handle negative indices

### Step 4: Test All String Functions
Run compliance tests to verify:
- Test all string functions
- Test edge cases
- Test null handling
- Test empty strings

## Testing Strategy

1. **Unit Tests:** Test each string function
2. **Edge Case Tests:** Test boundary conditions
3. **Compliance Tests:** Run full string_functions suite
4. **Regex Tests:** Test regex patterns thoroughly

## Success Criteria

- [ ] All 16 string_functions tests passing
- [ ] `matches()` working correctly
- [ ] `replaceAll()` handling edge cases
- [ ] `substring()` boundary conditions fixed
- [ ] All string functions working
- [ ] No regressions
- [ ] Code reviewed and approved

## Dependencies

- None (can start immediately)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - String function translation (FIX LOCATION)
**Supporting:**
- `fhir4ds/main/dialects/` - Dialect-specific regex/substring functions
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

## Notes

- This is a LOW complexity task
- Most functions already working
- Focus on edge cases
- Test regex patterns thoroughly
- Consider using Python's re module

## Expected Compliance Impact

**Before:** 97.8% (913/934)
**After:** 99.5% (929/934)
**Improvement:** +1.7%
