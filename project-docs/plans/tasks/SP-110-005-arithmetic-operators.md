# Task SP-110-005: Arithmetic Operators - Precedence and Precision

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Bug Fix
**Complexity:** MEDIUM
**Priority:** P1
**Estimated Effort:** 8-14 hours

---

## Task Description

Fix unary polarity operator precedence and decimal precision handling to achieve 100% pass rate in arithmetic_operators category.

## Current State

**Category:** arithmetic_operators
**Current Pass Rate:** 45.8% (33/72 tests passing)
**Gap:** 39 failing tests
**Impact:** +4.2% overall compliance

## Key Issues

### 1. Unary Polarity Operator Precedence
- Unary `+` and `-` precedence too low
- `-5 + 3` parses as `-(5 + 3)` instead of `(-5) + 3`
- AST generation incorrect for unary operators

### 2. Decimal Overflow/Precision Issues
- Decimal arithmetic causes overflow
- Precision loss in calculations
- Scale handling incorrect

### 3. Negative Number Comparisons
- Negative numbers in comparisons
- Unary minus in comparison expressions
- Sign preservation

### 4. Mixed Type Arithmetic Operations
- Integer and decimal mixing
- String to number conversion
- Type promotion rules

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

**IMPORTANT:** Unary polarity operator precedence issues are in the GRAMMAR layer. Since we CANNOT modify the grammar, we must work around this in the translator layer by handling the AST as it comes from the parser.

### Step 1: Fix Unary Polarity Operator Handling in Translator
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Since the grammar generates AST with incorrect precedence, we must:
- Detect unary polarity patterns in the AST
- Adjust translation to handle the actual structure
- Generate correct SQL despite AST structure limitations

**Note:** If the grammar issue causes fundamentally incorrect AST structure that cannot be worked around, we may need to accept this limitation or make minimal changes in `parser_core/ast_extensions.py` to restructure the AST.

### Step 2: Implement Proper Decimal Precision Handling
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix arithmetic operator translation:
- Use database decimal/numeric types for precision
- Handle scale correctly in SQL generation
- Use dialect-specific decimal handling methods

### Step 3: Fix Negative Number Comparison Logic
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Ensure comparison operators handle negative numbers:
- Preserve sign information in generated SQL
- Handle unary minus correctly in comparisons
- Generate correct comparison expressions

### Step 4: Test All Arithmetic Operations
Run compliance tests to verify:
- Test unary operator handling
- Test decimal precision
- Test negative number comparisons
- Test mixed-type operations
- Test edge cases (overflow, underflow)

## Testing Strategy

1. **Unit Tests:** Test each operator
2. **Precedence Tests:** Verify operator precedence
3. **Precision Tests:** Test decimal arithmetic
4. **Compliance Tests:** Run full arithmetic_operators suite

## Success Criteria

- [ ] All 39 arithmetic_operators tests passing
- [ ] Unary operator precedence correct
- [ ] Decimal precision handled properly
- [ ] Negative number comparisons working
- [ ] Mixed-type operations correct
- [ ] No regressions
- [ ] Code reviewed and approved

## Dependencies

- None (can start immediately)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - Arithmetic operator translation (FIX LOCATION)
**Supporting (Minimal Changes):**
- `fhir4ds/main/fhirpath/parser_core/ast_extensions.py` - AST restructuring (if absolutely needed)
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

**Note:** Unary operator precedence is a grammar-level issue. Work around in translator or make minimal AST restructuring in `ast_extensions.py`.

## Notes

- This is a MEDIUM complexity task
- **CRITICAL:** Unary operator precedence is in the grammar, which we cannot modify
- Must work around grammar limitations in the translator layer
- If workaround is impossible, minimal AST restructuring in `ast_extensions.py` may be needed
- Test thoroughly after changes
- Use database decimal types for precision
- Document any workarounds clearly

## Expected Compliance Impact

**Before:** 91.4% (853/934)
**After:** 95.6% (892/934)
**Improvement:** +4.2%
