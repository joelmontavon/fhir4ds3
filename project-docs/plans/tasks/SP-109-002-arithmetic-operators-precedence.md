# Task SP-109-002: Arithmetic Operators - Precedence and Precision

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 39 tests (45.8% → 100%, +4.2% overall)
**Effort:** 8-12 hours
**Priority:** P1
**Status:** Pending

---

## Objective

Fix arithmetic operator precedence, precision, and edge cases to achieve 100% compliance in this category, improving overall compliance by 4.2 percentage points.

---

## Current State

**Arithmetic Operators: 45.8% (33/72 tests passing)**

### Key Issues Identified

1. **Unary Polarity Operator Precedence**
   - `-Patient.name.given.count()` fails
   - Parser precedence incorrect for unary operators
   - Related to SP-109-001 precedence fix

2. **Decimal Overflow/Precision Issues**
   - Large decimals cause overflow
   - Precision loss in calculations
   - Rounding behavior incorrect

3. **Negative Number Comparisons**
   - Negative number comparison logic
   - Type coercion with negatives
   - Edge cases with zero

4. **Mixed Type Arithmetic Operations**
   - Integer + Decimal operations
   - Quantity arithmetic
   - String to number coercion

---

## Implementation Plan

### Step 1: Fix Unary Polarity Operator Precedence (2-3 hours)

**Problem:** Unary minus has incorrect precedence

**Solution:**
1. Review parser grammar for unary operators
2. Adjust precedence: unary should bind tighter than binary
3. Add test cases for unary with function calls
4. Verify SQL translation handles precedence correctly

**Files to Modify:**
- `fhir4ds/main/fhirpath/parser.py`
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPathParser.g4`

**Dependencies:** SP-109-001 (shared precedence fix)

### Step 2: Implement Proper Decimal Precision Handling (2-3 hours)

**Problem:** Decimals lose precision or overflow

**Solution:**
1. Review DuckDB decimal handling
2. Implement proper precision tracking
3. Add overflow detection and handling
4. Test with various decimal ranges

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/dialects/duckdb.py`

### Step 3: Fix Negative Number Comparison Logic (2-3 hours)

**Problem:** Negative numbers compared incorrectly

**Solution:**
1. Review comparison operator implementation
2. Fix negative number handling
3. Add test cases for negative comparisons
4. Verify SQL generates correct comparisons

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/test_operator_edge_cases.py`

### Step 4: Implement Mixed Type Arithmetic (2-3 hours)

**Problem:** Mixed type operations fail

**Solution:**
1. Implement type coercion for arithmetic
2. Handle Integer + Decimal correctly
3. Add Quantity arithmetic support (if needed)
4. Test all type combinations

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/main/fhirpath/types/type_converter.py`

---

## Testing Strategy

### Unit Tests
1. Test unary operator precedence
2. Test decimal precision and overflow
3. Test negative number comparisons
4. Test mixed type arithmetic

### Integration Tests
1. Test arithmetic in expressions
2. Test arithmetic with CTEs
3. Test arithmetic across databases
4. Test edge cases (zero, infinity, NaN)

### Compliance Tests
1. Run full arithmetic_operators test suite
2. Verify 100% pass rate
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All 72 arithmetic_operators tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 73.1%+

---

## Risk Assessment

**Risk Level:** Low

**Risks:**
- Precedence changes may affect other operators
- Decimal precision may be database-specific
- Mixed type coercion may be complex

**Mitigation:**
- Coordinate precedence fix with SP-109-001
- Test all operators after precedence change
- Use database-agnostic precision handling where possible
- Test edge cases thoroughly

---

## Dependencies

- SP-109-001 (shared unary precedence fix)

---

## Notes

- This is a lower-risk task that can build momentum
- Precedence fix is shared with type functions
- Arithmetic operators are foundational for many expressions
- Focus on correctness over performance initially
