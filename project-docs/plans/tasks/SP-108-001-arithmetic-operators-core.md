# Task SP-108-001: Arithmetic Operators - Core Issues

**Created:** 2026-01-28
**Sprint:** SP-108
**Category:** Arithmetic Operators
**Impact:** 42 tests (41.7% → 100%, +4.5% overall compliance)
**Effort:** 8-12 hours
**Priority:** P0

---

## Task Description

Complete the arithmetic operators category to achieve 100% compliance. Currently at 41.7% (30/72 tests passing) with 42 failing tests covering basic arithmetic operations, unary operators, and edge cases.

---

## Current State

**Passing Tests:** 30/72 (41.7%)
**Failing Tests:** 42
**Gap:** 58.3%

### Key Failing Test Patterns

Based on analysis from compliance_report_sp107_official.json:

1. **Unary Polarity Precedence:**
   - `testPolarityPrecedence`: `-Patient.name.given.count() = -5`
   - Issue: Unary minus not binding correctly to function call results

2. **Negative Number Comparisons:**
   - `testLiteralIntegerGreaterThan`: `Patient.name.given.count() > -3`
   - Issue: Comparison with negative literals producing unexpected results

3. **Decimal Precision/Overflow:**
   - `testLiteralDecimalMax`: `1234567890987654321.0.convertsToDecimal()`
   - Issue: Large decimal precision/overflow handling

---

## Root Cause Analysis

### 1. Unary Operator Precedence
**Issue:** Unary polarity operators (`-`, `+`) have incorrect precedence in AST

**Location:** `fhir4ds/main/fhirpath/parser_core/semantic_validator.py` or parser grammar

**Impact:** Any expression combining unary operators with function calls fails

**Fix Strategy:**
- Review unary operator precedence rules in FHIRPath spec
- Update AST construction to enforce correct precedence
- Ensure unary operators bind tightly to operands

### 2. Negative Literal Parsing
**Issue:** Negative number literals not parsed correctly

**Location:** Parser lexer/parser

**Impact:** Comparisons with negative numbers produce wrong results

**Fix Strategy:**
- Ensure negative numbers are parsed as single numeric literals
- NOT as unary minus applied to positive literal
- Verify literal value in AST

### 3. Decimal Type Handling
**Issue:** Large decimal values lose precision or overflow

**Location:** SQL translator or dialect

**Impact:** `convertsToDecimal()` fails for large values

**Fix Strategy:**
- Ensure DECIMAL type used in SQL (not FLOAT)
- Verify precision/scale settings
- Test boundary values

---

## Implementation Plan

### Step 1: Unary Operator Precedence (2-3 hours)
1. Review FHIRPath unary operator precedence specification
2. Identify AST construction point for unary operators
3. Fix precedence binding in parser or semantic validator
4. Add unit tests for precedence
5. Verify fix with `testPolarityPrecedence`

### Step 2: Negative Literals (1-2 hours)
1. Review parser lexer for numeric literals
2. Ensure negative numbers parsed as single token
3. Fix literal value construction
4. Add unit tests for negative literals
5. Verify fix with `testLiteralIntegerGreaterThan`

### Step 3: Decimal Precision (2-3 hours)
1. Review SQL generation for decimal types
2. Ensure DECIMAL type used (not FLOAT/DOUBLE)
3. Verify precision/scale in both DuckDB and PostgreSQL
4. Test boundary values (min/max decimals)
5. Verify fix with `testLiteralDecimalMax`

### Step 4: Comprehensive Testing (2-3 hours)
1. Run all arithmetic operator tests
2. Group any remaining failures by root cause
3. Fix remaining issues
4. Verify 100% compliance
5. Test both DuckDB and PostgreSQL

---

## Testing Strategy

### Unit Tests
```bash
# Run arithmetic operator tests
pytest tests/unit/fhirpath/parser_core/test_arithmetic_operators.py -v
```

### Compliance Tests
```bash
# Run official arithmetic operator tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py -k arithmetic -v
```

### Verification
- All 72 arithmetic operator tests passing
- No regressions in other categories
- Both DuckDB and PostgreSQL passing

---

## Success Criteria

- [ ] All 72 arithmetic operator tests passing (100%)
- [ ] Unary operator precedence fixed
- [ ] Negative literals working correctly
- [ ] Decimal precision handling correct
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both database dialects passing

---

## Files to Modify

**Likely Targets:**
- `fhir4ds/main/fhirpath/parser_core/semantic_validator.py` - Operator precedence
- `fhir4ds/main/fhirpath/parser_core/parser_core.py` - Parser grammar
- `fhir4ds/main/fhirpath/sql/translator.py` - SQL generation for arithmetic
- `fhir4ds/dialects/duckdb.py` - DuckDB-specific decimal handling
- `fhir4ds/dialects/postgresql.py` - PostgreSQL-specific decimal handling

---

## Notes

- FHIRPath arithmetic operators: `+`, `-`, `*`, `/`, `mod`, `div`
- Unary operators: `+`, `-`
- Precedence: Unary > Multiplicative (*, /, mod, div) > Additive (+, -)
- Numeric types: Integer, Decimal, Quantity
- Division by zero should return empty result

---

## References

- FHIRPath Specification: Arithmetic Operators
- Compliance Report: `compliance_report_sp107_official.json`
- Previous Work: SP-106-007 (Unary Polarity)
