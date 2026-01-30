# Task SP-109-003: Function Calls - Signature Resolution

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 50 tests (55.8% → 100%, +5.4% overall)
**Effort:** 10-14 hours
**Priority:** P0
**Status:** Pending

---

## Objective

Implement proper function signature resolution, parameter type coercion, and fix `iif()` function validation to achieve 100% compliance in function calls category.

---

## Current State

**Function Calls: 55.8% (63/113 tests passing)**

### Key Issues Identified

1. **`iif()` Function with Collection Arguments**
   - `iif()` called on collections with multiple items fails
   - `iif()` criterion must be boolean, not collection
   - Error: "iif() cannot be called on a collection with multiple items"

2. **Function Signature Resolution**
   - Overloaded functions not resolved correctly
   - Ambiguous function calls fail
   - Missing function implementations

3. **Parameter Type Coercion**
   - Parameters not coerced to expected types
   - String literals not converted to numbers
   - Date/time strings not parsed correctly

4. **Missing Function Implementations**
   - Some functions simply not implemented
   - Functions return "not supported" error
   - Need to audit and implement all functions

---

## Implementation Plan

### Step 1: Implement Function Signature Registry (2-3 hours)

**Problem:** No systematic function signature tracking

**Solution:**
1. Create `FunctionSignature` dataclass
2. Create `FunctionRegistry` class
3. Register all FHIRPath functions with signatures
4. Implement signature matching logic

**Files to Create:**
- `fhir4ds/main/fhirpath/functions/signature.py`
- `fhir4ds/main/fhirpath/functions/registry.py`

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`

### Step 2: Implement Parameter Type Coercion (3-4 hours)

**Problem:** Parameters not coerced to expected types

**Solution:**
1. Implement type coercion for function parameters
2. Handle string to number conversion
3. Handle date/time string parsing
4. Add type validation before function calls

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/type_converter.py`
- `fhir4ds/main/fhirpath/functions/registry.py`

### Step 3: Fix `iif()` Validation (2-3 hours)

**Problem:** `iif()` doesn't validate single-value criterion

**Solution:**
1. Add validation for `iif()` criterion
2. Ensure criterion is boolean, not collection
3. Add proper error messages
4. Test all `iif()` edge cases

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/functions/test_iif.py`

### Step 4: Implement Missing Functions (3-4 hours)

**Problem:** Some functions not implemented

**Solution:**
1. Audit which functions are missing
2. Implement missing functions one by one
3. Test each implementation
4. Document all supported functions

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- Create new function-specific modules if needed

---

## Testing Strategy

### Unit Tests
1. Test function signature resolution
2. Test parameter type coercion
3. Test `iif()` validation
4. Test each implemented function

### Integration Tests
1. Test function calls in expressions
2. Test function calls with CTEs
3. Test overloaded function resolution
4. Test cross-database compatibility

### Compliance Tests
1. Run full function_calls test suite
2. Verify 100% pass rate
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All 113 function_calls tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 78.5%+

---

## Risk Assessment

**Risk Level:** Low to Medium

**Risks:**
- Function signature complexity may be high
- Type coercion may have edge cases
- `iif()` validation may be complex

**Mitigation:**
- Start with simple functions first
- Build signature registry incrementally
- Test each function as implemented
- Document all edge cases

---

## Dependencies

- None (can start immediately)

---

## Notes

- Function registry is a foundational improvement
- Will benefit all future function implementations
- Type coercion logic can be reused elsewhere
- Focus on core functions first, edge cases second
