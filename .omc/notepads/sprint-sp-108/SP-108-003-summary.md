# SP-108-003 Summary: Collection Functions Core

**Date:** 2026-01-28
**Status:** Completed (Partial - 75% compliance for tested collection functions)
**Improvement:** 33.3% → 75.0% (+41.7%)

---

## Changes Made

### 1. Fixed `empty()` and `exists()` Aggregation on Unnested Collections

**Files Modified:**
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`
  - `_translate_empty()`: Added detection for unnested collections, set `is_aggregate=True` with `exclude_order_from_group_by=True`
  - `_translate_exists()`: Same fix as empty()
  - `_translate_not()`: Added propagation of `aggregate_function` metadata from previous fragment
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/cte.py`
  - `_needs_collection_aggregation()`: Added check for unary operators (not()) on aggregate functions
  - `_add_aggregation_cte()`: Check `aggregate_function` metadata first, apply NOT operator when needed

**Problem:** `Patient.name.given.empty().not()` returned array of booleans instead of single boolean
**Solution:** Make empty/exists aggregate back to patient level when operating on unnested collections

---

### 2. Fixed `contains` Operator for Collections

**Files Modified:**
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser_core/ast_extensions.py`
  - Added early check for `MembershipExpression` before general PATH_EXPRESSION handling
  - Created `MembershipExpressionAdapter` to convert membership expression to function call
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`
  - `visit_function_call()`: Detect membership contains (2 args) vs string contains (1 arg)
  - Implemented `_translate_contains_membership()` method
- `/mnt/d/fhir4ds3/fhir4ds/dialects/base.py`
  - Added abstract method `generate_membership_test()`
- `/mnt/d/fhir4ds3/fhir4ds/dialects/duckdb.py`
  - Implemented `generate_membership_test()` using `json_each()` with string literal handling
- `/mnt/d/fhir4ds3/fhir4ds/dialects/postgresql.py`
  - Implemented `generate_membership_test()` using `jsonb_array_elements()` with string literal handling

**Problem:** `(1 | 2 | 3) contains 1` was treated as path navigation instead of membership test
**Solution:** Convert MembershipExpression to function call, implement membership test SQL generation

---

## Test Results

### Collection Function Compliance Tests (12 tests)

| Test | Before | After | Status |
|------|--------|-------|--------|
| `Patient.name.given.empty().not()` | FAIL | PASS | Fixed |
| `(1 | 2 | 3) contains 1` | FAIL | PASS | Fixed |
| `(2 | 3) contains 1` | FAIL | PASS | Fixed |
| `('a' | 'c' | 'd') contains 'a'` | FAIL | PASS | Fixed |
| `('a' | 'c' | 'd') contains 'b'` | FAIL | PASS | Fixed |

**Before:** 4/12 passing (33.3%)
**After:** 9/12 passing (75.0%)

---

### Remaining Failures (3 tests)

All related to `iif()` collection boolean context:

1. `testCollectionBoolean1: iif(1 | 2 | 3, true, false)` - Expected semantic failure
2. `testCollectionBoolean5: iif(true, true, 1/0)` - Type coercion issue
3. `testCollectionBoolean6: iif(false, 1/0, true)` - Type coercion issue

These require:
- Detection of collection-based boolean context (non-empty collection → true)
- Proper type handling for collection expressions in conditional statements
- Short-circuit evaluation based on collection emptiness

---

## Impact

- **Compliance:** 33.3% → 75.0% (+41.7 percentage points)
- **Tests Fixed:** 5 of 8 collection function tests
- **Architecture:** Improved aggregation metadata propagation, added membership operator support

---

## Files Modified

1. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py` - empty/exists aggregation, not() propagation, contains membership
2. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/cte.py` - aggregation CTE generation for unary operators
3. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser_core/ast_extensions.py` - MembershipExpression handling
4. `/mnt/d/fhir4ds3/fhir4ds/dialects/base.py` - Abstract membership test method
5. `/mnt/d/fhir4ds3/fhir4ds/dialects/duckdb.py` - Membership test implementation
6. `/mnt/d/fhir4ds3/fhir4ds/dialects/postgresql.py` - Membership test implementation

---

## Notes

The remaining `iif()` issues are tracked in task SP-108-004 (Function Calls Edge Cases) and require:
1. Detecting when condition is a collection (should evaluate to true if non-empty)
2. Proper type coercion for mixed types in CASE expressions
3. Short-circuit evaluation to avoid division-by-zero in unexecuted branches
