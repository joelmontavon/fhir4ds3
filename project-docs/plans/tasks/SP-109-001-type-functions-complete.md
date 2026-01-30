# Task SP-109-001: Type Functions - Complete Implementation

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 53 tests (54.3% → 100%, +5.7% overall)
**Effort:** 12-16 hours
**Priority:** P0
**Status:** Pending

---

## Objective

Complete implementation of FHIRPath type functions to achieve 100% compliance in this category, improving overall compliance by 5.7 percentage points.

---

## Current State

**Type Functions: 54.3% (63/116 tests passing)**

### Key Issues Identified

1. **Negative Number Type Conversion**
   - `-1.convertsToInteger()` fails
   - `-0.1.convertsToDecimal()` fails
   - Root cause: Unary polarity operator precedence

2. **`as()` Type Conversion Edge Cases**
   - Complex type conversions not implemented
   - Type system doesn't handle all FHIR types
   - Missing conversions for primitive types

3. **`is()` Operator with Complex Types**
   - Polymorphic type checking incomplete
   - Type discriminator logic gaps
   - Collection type handling

4. **`ofType()` Collection Filtering**
   - Not implemented
   - Requires collection type analysis
   - Needs type preservation through CTEs

---

## Implementation Plan

### Step 1: Fix Unary Polarity Operator Precedence (2-3 hours)

**Problem:** Parser treats `-1.convertsToInteger()` as `-(1.convertsToInteger())`

**Solution:**
1. Review parser grammar for unary operators
2. Adjust precedence rules for unary polarity
3. Add test cases for negative number type conversions
4. Verify SQL translation handles negative numbers correctly

**Files to Modify:**
- `fhir4ds/main/fhirpath/parser.py`
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPathParser.g4`

### Step 2: Implement Negative Number Type Conversion (2-3 hours)

**Problem:** Type converter doesn't handle negative numbers

**Solution:**
1. Update `TypeConverter` to handle negative numbers
2. Add test cases for negative integers and decimals
3. Verify conversion accuracy
4. Update documentation

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/type_converter.py`
- `tests/unit/fhirpath/types/test_type_converter.py`

### Step 3: Complete `as()` Operator Implementation (3-4 hours)

**Problem:** Many type conversions not supported

**Solution:**
1. Audit all missing `as()` conversions
2. Implement conversion logic for each type
3. Add CTE support for type casting
4. Test all conversion paths

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/main/fhirpath/types/type_converter.py`

### Step 4: Fix `is()` Operator Edge Cases (2-3 hours)

**Problem:** Complex type checking incomplete

**Solution:**
1. Enhance type discriminator logic
2. Handle polymorphic types correctly
3. Fix collection type checking
4. Add comprehensive test coverage

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/type_discriminators.py`
- `fhir4ds/main/fhirpath/sql/translator.py`

### Step 5: Implement `ofType()` Collection Filtering (3-4 hours)

**Problem:** Function not implemented

**Solution:**
1. Implement `ofType()` in translator
2. Add type filtering logic in CTEs
3. Preserve type information through CTE chain
4. Test with various collection types

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/main/fhirpath/sql/cte.py`

---

## Testing Strategy

### Unit Tests
1. Test negative number type conversions
2. Test all `as()` conversions
3. Test `is()` with complex types
4. Test `ofType()` filtering

### Integration Tests
1. Test type functions in expressions
2. Test type functions with collections
3. Test type functions with CTEs
4. Test cross-database compatibility

### Compliance Tests
1. Run full type_functions test suite
2. Verify 100% pass rate
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All 116 type_functions tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 68.9%+

---

## Risk Assessment

**Risk Level:** Medium

**Risks:**
- Type system complexity may require architectural changes
- Negative number precedence may affect other operators
- Type conversion edge cases may be extensive

**Mitigation:**
- Start with simplest fixes (precedence, negatives)
- Test thoroughly after each change
- Keep changes localized to type system
- Document all edge cases encountered

---

## Dependencies

- None (can start immediately)

---

## Notes

- This is a foundational task that may help with other categories
- Type system improvements will benefit comparison operators
- Focus on core type operations first, edge cases second
