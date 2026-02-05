# Task SP-110-001: Comparison Operators - DateTime and Quantity

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Feature Implementation
**Complexity:** HIGH
**Priority:** P0
**Estimated Effort:** 16-24 hours

---

## Task Description

Fix datetime timezone handling, DATE/TIME type compatibility, and Quantity unit conversion in comparison operators to achieve 100% pass rate in comparison_operators category.

## Current State

**Category:** comparison_operators
**Current Pass Rate:** 74.9% (254/339 tests passing)
**Gap:** 85 failing tests
**Impact:** +9.1% overall compliance

## Key Issues

### 1. DateTime Timezone Handling
- DateTime comparisons without proper timezone normalization
- UTC vs local timezone comparisons
- Timezone-aware vs naive datetime comparisons

### 2. DATE/TIME Type Compatibility
- DATE literal vs TIME literal comparisons (currently blocked by validation)
- Mixed temporal type comparisons
- DateTime precision differences

### 3. Quantity Unit Conversion
- Quantity comparisons without unit conversion
- Different unit representations (e.g., 'cm' vs 'm')
- UCUM unit code handling

### 4. Calendar Duration Comparisons
- Duration comparisons with calendar units
- Month/year duration handling
- Precise vs calendar duration

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

### Step 1: Implement DateTime Timezone Normalization
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Add datetime normalization in the comparison operator translation methods:
- In `visit_comparison_operator()` or related methods
- Normalize datetime values to UTC before comparison
- Handle timezone-aware vs naive datetimes

### Step 2: Fix DATE/TIME Type Compatibility
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

- Review validation errors for DATE/TIME comparisons
- Decide: accept validation blocking OR implement compatibility
- If implementing: add type coercion for temporal types in comparison translation

### Step 3: Add Quantity Unit Conversion
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Add quantity normalization in comparison operators:
- Implement `normalize_quantity_for_comparison()` helper
- Convert quantities to common unit before comparison
- Handle UCUM unit codes

### Step 4: Implement Calendar Duration Conversion
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Add duration comparison logic:
- Implement `compare_durations()` helper
- Handle calendar vs precise durations
- Convert to common representation for comparison

### Step 5: Test All Comparison Operators
Run compliance tests to verify:
- Test timezone handling
- Test DATE/TIME comparisons
- Test Quantity unit conversions
- Test Duration comparisons
- Test mixed-type comparisons

## Testing Strategy

1. **Unit Tests:** Test each normalization function
2. **Integration Tests:** Test comparison operators with normalized values
3. **Compliance Tests:** Run full comparison_operators test suite
4. **Edge Cases:** Test null handling, type mismatches

## Success Criteria

- [ ] All 85 comparison_operators tests passing
- [ ] DateTime timezone handling correct
- [ ] DATE/TIME compatibility implemented or accepted
- [ ] Quantity unit conversion functional
- [ ] Calendar duration comparison working
- [ ] No regressions in passing tests
- [ ] Code reviewed and approved

## Dependencies

- None (can start immediately)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - Comparison operator translation (FIX LOCATION)
**Supporting:**
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata types
- `fhir4ds/main/fhirpath/types/` - Type system definitions
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

## Notes

- This is a HIGH complexity task due to timezone and unit conversion complexity
- Consider using python-dateutil for datetime handling
- UCUM unit library may be needed for Quantity normalization
- Focus on common cases first, edge cases second

## Expected Compliance Impact

**Before:** 63.5% (593/934)
**After:** 72.6% (678/934)
**Improvement:** +9.1%
