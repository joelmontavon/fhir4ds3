# Sprint SP-109: Push to 100% FHIRPath Compliance

**Created:** 2026-01-29
**Sprint Goal:** Achieve 90%+ compliance toward 100% target
**Starting Compliance:** 63.2% (590/934 tests passing)
**Target Compliance:** 90%+ (840+/934 tests passing)
**Stretch Goal:** 95%+ (887+/934 tests passing)
**Status:** In Planning

---

## Sprint Vision

Building on SP-108's intermediate gains (84.4% translation, 63.2% execution), SP-109 targets **high-impact remaining failures** to push toward 100% FHIRPath compliance. The strategy focuses on **architectural improvements** that will unblock multiple test categories simultaneously.

### Strategic Alignment

This sprint continues the systematic approach to 100% FHIRPath compliance:
- **Focus:** High-impact categories with most failures (P0: comparison, collection, type, functions)
- **Strategy:** Fix architectural root causes to unblock many tests at once
- **Impact:** Target 90%+ compliance, setting up for final 100% push in SP-110
- **Learning:** Build expertise for final edge cases

---

## Gap Analysis Summary

### Current State (Post SP-108)

**Overall: 63.2% (590/934 tests passing)**

#### Priority Categories (High Impact)

| Category | Pass Rate | Failed | Impact | Effort | Priority |
|----------|-----------|--------|--------|--------|----------|
| comparison_operators | 74.0% | 88 | +9.4% | 16-20h | P0 |
| collection_functions | 48.9% | 72 | +7.7% | 20-24h | P0 |
| type_functions | 54.3% | 53 | +5.7% | 12-16h | P0 |
| function_calls | 55.8% | 50 | +5.4% | 10-14h | P0 |
| arithmetic_operators | 45.8% | 39 | +4.2% | 8-12h | P1 |
| string_functions | 75.4% | 16 | +1.7% | 6-8h | P2 |

#### Quick Wins (Low-Hanging Fruit)

| Category | Pass Rate | Failed | Impact |
|----------|-----------|--------|--------|
| math_functions | 96.4% | 1 | +0.1% |
| path_navigation | 90.0% | 1 | +0.1% |
| datetime_functions | 83.3% | 1 | +0.1% |

---

## Implementation Strategy

### Phase 1: Type Functions (P0) - Foundation

#### Task SP-109-001: Type Functions - Complete Implementation
**Impact:** 53 tests (54.3% → 100%, +5.7% overall)
**Effort:** 12-16 hours
**Priority:** P0

**Key Issues:**
- `convertsToInteger()`, `convertsToDecimal()` with negative numbers
- `as()` type conversion edge cases
- `is()` operator with complex types
- `ofType()` collection filtering

**Implementation:**
1. Fix unary polarity operator precedence in parser
2. Implement negative number type conversion
3. Complete `as()` operator for all types
4. Fix `is()` operator edge cases
5. Implement `ofType()` collection filtering

**Expected Compliance:** 63.2% → 68.9% (+5.7%)

### Phase 2: Arithmetic Operators (P1) - Precedence

#### Task SP-109-002: Arithmetic Operators - Precedence and Precision
**Impact:** 39 tests (45.8% → 100%, +4.2% overall)
**Effort:** 8-12 hours
**Priority:** P1

**Key Issues:**
- Unary polarity operator precedence
- Decimal overflow/precision issues
- Negative number comparisons
- Mixed type arithmetic operations

**Implementation:**
1. Fix unary polarity operator precedence in AST
2. Implement proper decimal precision handling
3. Fix negative number comparison logic
4. Test all arithmetic operations

**Expected Compliance:** 68.9% → 73.1% (+4.2%)

### Phase 3: Function Calls (P0) - Registry

#### Task SP-109-003: Function Calls - Signature Resolution
**Impact:** 50 tests (55.8% → 100%, +5.4% overall)
**Effort:** 10-14 hours
**Priority:** P0

**Key Issues:**
- `iif()` function with collection arguments
- Function signature resolution
- Parameter type coercion
- Missing function implementations

**Implementation:**
1. Implement function signature registry
2. Add parameter type coercion
3. Fix `iif()` validation for single-value criteria
4. Complete missing function implementations
5. Test function call edge cases

**Expected Compliance:** 73.1% → 78.5% (+5.4%)

### Phase 4: Collection Functions (P0) - CTE Architecture

#### Task SP-109-004: Collection Functions - CTE Column Preservation
**Impact:** 72 tests (48.9% → 100%, +7.7% overall)
**Effort:** 20-24 hours
**Priority:** P0 (Most Complex)

**Key Issues:**
- Column reference errors in CTEs with `take()`, `first()`, `last()`
- `supersetOf()`, `subsetOf()` not implemented
- `select()` with lambda variables
- `repeat()` with non-JSON values
- `single()` collection validation
- `allTrue()`, `anyTrue()` quantifiers

**Implementation:**
1. Implement comprehensive CTE column preservation
2. Add set comparison functions (`supersetOf`, `subsetOf`)
3. Fix lambda variable scope in `select()`
4. Implement `repeat()` with type conversion
5. Add `single()` collection validation
6. Implement `allTrue()`, `anyTrue()` quantifiers

**Expected Compliance:** 78.5% → 86.2% (+7.7%)

### Phase 5: Comparison Operators (P0) - Final Push

#### Task SP-109-005: Comparison Operators - Temporal and Quantity
**Impact:** 88 tests (74.0% → 100%, +9.4% overall)
**Effort:** 16-20 hours
**Priority:** P0

**Key Issues:**
- DateTime timezone handling in comparisons
- DATE vs TIME literal comparisons
- Mixed-type comparisons (Quantity vs string)
- Calendar duration comparisons

**Implementation:**
1. Implement datetime timezone normalization
2. Fix DATE/TIME type compatibility
3. Add Quantity unit conversion
4. Implement calendar duration conversion
5. Test all comparison operators

**Expected Compliance:** 86.2% → 95.6% (+9.4%)

### Phase 6: Quick Wins (P2) - Polish

#### Task SP-109-006: Quick Wins - Edge Cases
**Impact:** 20 tests (various → 100%, +2.1% overall)
**Effort:** 6-8 hours
**Priority:** P2

**Implementation:**
1. Fix remaining math function issue
2. Fix path navigation edge case
3. Fix datetime function edge case
4. Fix remaining string function issues

**Expected Compliance:** 95.6% → 97.7% (+2.1%)

---

## Success Metrics

### Target vs Stretch

| Metric | Target | Stretch | Expected |
|--------|--------|---------|----------|
| **Overall Compliance** | 90%+ | 95%+ | 97.7% |
| **P0 Categories Complete** | 4 | 4 | 4 |
| **Improvement** | +26.8% | +31.8% | +34.5% |
| **Tests Passing** | 840+ | 887+ | 912+ |

### Completed Tasks (Expected)
- [ ] SP-109-001: Type Functions
- [ ] SP-109-002: Arithmetic Operators
- [ ] SP-109-003: Function Calls
- [ ] SP-109-004: Collection Functions
- [ ] SP-109-005: Comparison Operators
- [ ] SP-109-006: Quick Wins

---

## Testing Strategy

### After Each Task
1. Run compliance test suite: `python3 run_compliance_tests.py`
2. Generate compliance report
3. Verify expected improvement
4. Check for regressions
5. Document results

### Continuous Testing
- Run DuckDB tests after each fix
- Run PostgreSQL tests before merge
- Verify no regressions in passing categories
- Test edge cases thoroughly

### Final Validation
1. Run full compliance suite (DuckDB + PostgreSQL)
2. Generate detailed compliance report
3. Verify all tasks complete
4. Check for side effects
5. Review compliance improvement

---

## Dependencies

### Internal
- SP-108 must be merged to main (DONE)
- Compliance test suite functional (DONE)
- Package installed in dev mode (DONE)

### External
- None (self-contained sprint)

---

## Risk Assessment

### Low Risk
- Quick wins: Well-defined edge cases
- Arithmetic operators: Clear precedence rules

### Medium Risk
- Type functions: Type system complexity
- Function calls: Signature resolution complexity

### High Risk
- Collection functions: Complex CTE architecture changes
- Comparison operators: Timezone and unit conversion complexity

### Mitigation
- Start with lower-risk tasks (type functions, arithmetic)
- Build momentum before tackling complex collection functions
- Test after each fix, not just at end
- Keep changes minimal and targeted
- Use ultrapilot for parallel execution

---

## Timeline Estimate

**Phase 1 (P0):** 12-16 hours
**Phase 2 (P1):** 8-12 hours
**Phase 3 (P0):** 10-14 hours
**Phase 4 (P0):** 20-24 hours
**Phase 5 (P0):** 16-20 hours
**Phase 6 (P2):** 6-8 hours

**Total Effort:** 72-94 hours
**Parallelized (5 workers via ultrapilot):** 14-19 hours

---

## Definition of Done

For each task:
- [ ] All tests in category passing (or target percentage reached)
- [ ] Code reviewed and approved by code-reviewer
- [ ] No regressions in other categories
- [ ] Documentation updated (if needed)
- [ ] Compliance report shows improvement
- [ ] Both DuckDB and PostgreSQL tests passing

For sprint:
- [ ] All planned tasks complete
- [ ] Full compliance suite passing at expected level
- [ ] Code reviewed and approved
- [ ] Ready to merge to main
- [ ] Sprint documentation complete

---

## Execution Plan

### Ultraround 1 (Parallel - 3 workers)
- Worker 1: SP-109-001 (Type Functions)
- Worker 2: SP-109-002 (Arithmetic Operators)
- Worker 3: SP-109-003 (Function Calls)

### Ultraround 2 (Parallel - 2 workers)
- Worker 1: SP-109-004 (Collection Functions) - Most complex
- Worker 2: SP-109-005 (Comparison Operators)

### Integration & Testing
- SP-109-006 (Quick Wins)
- Full compliance suite run
- Regression testing
- Code review cycle
- Final validation
