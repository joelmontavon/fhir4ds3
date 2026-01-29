# Task SP-108-004: Function Calls - Edge Cases

**Created:** 2026-01-28
**Sprint:** SP-108
**Category:** Function Calls
**Impact:** 52 tests (54.0% → 100%, +5.6% overall compliance)
**Effort:** 10-14 hours
**Priority:** P1

---

## Task Description

Complete the function calls category to achieve 100% compliance. Currently at 54.0% (61/113 tests passing) with 52 failing tests covering function signature resolution, parameter handling, and missing implementations.

---

## Current State

**Passing Tests:** 61/113 (54.0%)
**Failing Tests:** 52
**Gap:** 46.0%

### Function Call Categories

1. **String Functions:**
   - `substring()`, `contains()`, `startsWith()`, `endsWith()`
   - `replace()`, `matches()`, `replaceMatches()`
   - `length()`, `upper()`, `lower()`, `trim()`

2. **Math Functions:**
   - `abs()`, `ceiling()`, `floor()`, `round()`, `truncate()`
   - `exp()`, `ln()`, `log()`, `power()`, `sqrt()`
   - Modulo operations

3. **DateTime Functions:**
   - `now()`, `today()`, `timeOfDay()`
   - `year()`, `month()`, `day()`, `hour()`, `minute()`, `second()`
   - Date arithmetic

4. **Type Conversion Functions:**
   - `toString()`, `toInteger()`, `toDecimal()`, `toBoolean()`
   - `toDateTime()`, `toDate()`, `toTime()`

5. **Collection Functions:**
   - `count()`, `empty()`, `exists()`, `distinct()`
   - `where()`, `select()`, `all()`, `aggregate()`

---

## Root Cause Analysis

### 1. Missing Function Implementations
**Issue:** Some functions not implemented

**Test Cases:** Various function calls
**Expected:** Function executes correctly
**Actual:** "Unknown function" or similar error

**Location:** Function registry and implementations

**Fix Strategy:**
- Identify missing functions from test failures
- Implement missing functions
- Register functions in function registry
- Test each new function

### 2. Function Signature Resolution
**Issue:** Function overloading not working correctly

**Test Cases:** Functions with multiple signatures
**Expected:** Correct signature selected based on parameters
**Actual:** Wrong signature or resolution error

**Location:** Function signature matching logic

**Fix Strategy:**
- Review signature resolution algorithm
- Fix type matching for parameters
- Handle type coercion correctly
- Test overloaded functions

### 3. Parameter Type Coercion
**Issue:** Parameters not coerced to correct types

**Test Cases:** Function calls with type mismatches
**Expected:** Automatic type coercion
**Actual:** Type errors or incorrect results

**Location:** Parameter type coercion logic

**Fix Strategy:**
- Implement parameter type coercion
- Follow FHIRPath coercion rules
- Test coercion between types

### 4. Function Error Handling
**Issue:** Functions not handling edge cases correctly

**Test Cases:** Functions with null, empty, or invalid inputs
**Expected:** Graceful handling per FHIRPath spec
**Actual:** Errors or incorrect results

**Location:** Individual function implementations

**Fix Strategy:**
- Review error handling for each function
- Handle null/empty inputs correctly
- Follow FHIRPath error semantics
- Test edge cases

---

## Implementation Plan

### Step 1: Identify Missing Functions (2 hours)
1. Run all function call tests
2. Group failures by function name
3. Identify which functions are missing
4. Prioritize by usage frequency

### Step 2: Implement Missing Functions (4-5 hours)
1. Implement each missing function:
   - String functions if missing
   - Math functions if missing
   - DateTime functions if missing
   - Other functions as needed
2. Follow FHIRPath specification
3. Handle edge cases correctly
4. Test each function

### Step 3: Fix Signature Resolution (2-3 hours)
1. Review signature resolution logic
2. Fix type matching for parameters
3. Handle type coercion correctly
4. Test overloaded functions

### Step 4: Fix Parameter Coercion (2-3 hours)
1. Implement parameter type coercion
2. Follow FHIRPath coercion rules
3. Test coercion between types
4. Handle edge cases

### Step 5: Comprehensive Testing (2-3 hours)
1. Run all function call tests
2. Group remaining failures by root cause
3. Fix remaining issues
4. Verify 100% compliance
5. Test both DuckDB and PostgreSQL

---

## Testing Strategy

### Unit Tests
```bash
# Run function call tests
pytest tests/unit/fhirpath/functions/test_functions.py -v
```

### Compliance Tests
```bash
# Run official function call tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py -k "function" -v
```

### Verification
- All 113 function call tests passing
- No regressions in other categories
- Both DuckDB and PostgreSQL passing

---

## Success Criteria

- [ ] All 113 function call tests passing (100%)
- [ ] All functions implemented
- [ ] Signature resolution working correctly
- [ ] Parameter coercion working
- [ ] Error handling correct
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both database dialects passing

---

## Files to Modify

**Likely Targets:**
- `fhir4ds/main/fhirpath/functions/` - Function implementations
- `fhir4ds/main/fhirpath/parser_core/function_registry.py` - Function registration
- `fhir4ds/main/fhirpath/sql/translator.py` - Function SQL generation

---

## Function Implementation Priority

**High Priority (Commonly Used):**
- String manipulation: `substring()`, `contains()`, `replace()`
- Math: `abs()`, `round()`, `ceiling()`, `floor()`
- DateTime: `now()`, `today()`, `year()`, `month()`, `day()`

**Medium Priority (Frequently Used):**
- String: `startsWith()`, `endsWith()`, `matches()`
- Math: `power()`, `sqrt()`, `exp()`, `ln()`
- DateTime: `hour()`, `minute()`, `second()`

**Low Priority (Less Common):**
- Advanced math: `log()`, `truncate()`
- Advanced string: `replaceMatches()`
- Edge case functions

---

## Notes

- Functions should follow FHIRPath specification exactly
- Error handling should return empty, not throw exceptions
- Type coercion should follow FHIRPath rules
- Function overloading requires proper signature matching
- Null/empty inputs should be handled gracefully

---

## References

- FHIRPath Specification: Functions
- Compliance Report: `compliance_report_sp107_official.json`
- Previous Work: SP-107 (String, Math, Boolean functions)
