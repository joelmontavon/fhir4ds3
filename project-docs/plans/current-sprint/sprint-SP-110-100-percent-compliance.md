# Sprint SP-110: 100% FHIRPath Compliance

**Created:** 2026-01-30
**Last Updated:** 2026-02-04 (SP-110 Autopilot Sprint Execution)
**Sprint Goal:** Achieve 100% FHIRPath official test compliance
**Starting Compliance:** 69.2% (646/934 tests passing)
**Target Compliance:** 100% (934/934 tests passing)
**Gap to Close:** 288 tests (30.8%)
**Status:** ACTIVE - Parallel Execution (ULTRAPILOT)

---

## Sprint Vision

Building on SP-109's progress toward 100%, SP-110 completes the remaining 36.5% gap to achieve **full FHIRPath specification compliance**. This sprint addresses all remaining failing tests with a systematic approach prioritized by impact and complexity.

### Strategic Alignment

This sprint completes the journey to 100% FHIRPath compliance:
- **Focus:** All remaining failing tests across 7 categories
- **Strategy:** High-impact tasks first, parallel execution via ultrapilot
- **Impact:** 100% specification compliance
- **Learning:** Complete FHIRPath implementation expertise

### Architectural Approach (CRITICAL)

**DO NOT MODIFY THE ANTLR GRAMMAR.** All fixes must be implemented in the translation layer.

**5-Layer Architecture:**
1. **Layer 1: Grammar** (`parser_core/fhirpath_py/FHIRPath.g4`) - DO NOT TOUCH
2. **Layer 2: AST Construction** (`parser_core/fhirpath_py/ASTPathListener.py`) - Minimal changes only
3. **Layer 3: AST Metadata** (`parser_core/metadata_types.py`) - Safe to extend
4. **Layer 4: Translation** (`sql/translator.py`) - PRIMARY FIX LOCATION
5. **Layer 5: SQL Generation** (`dialects/`) - Dialect-specific syntax only

**Key Rule:** If a fix seems to require grammar changes, stop and reassess. The fix likely belongs in the translator layer instead.

---

## Gap Analysis Summary

### Current State (SP-110 Autopilot Execution - February 4, 2026)

**Overall: 69.2% (646/934 tests passing)**
**Gap: 288 tests (30.8%)**

#### Priority Categories (High to Low Impact)

| Rank | Category | Failures | Pass Rate | Impact | Complexity | Priority |
|------|----------|----------|-----------|--------|------------|----------|
| 1 | comparison_operators | 75 | 77.8% | 8.0% | HIGH | P0 |
| 2 | collection_functions | 67 | 52.5% | 7.2% | VERY_HIGH | P0 |
| 3 | function_calls | 46 | 59.3% | 4.9% | MEDIUM | P1 |
| 4 | type_functions | 41 | 64.7% | 4.4% | MEDIUM | P1 |
| 5 | arithmetic_operators | 37 | 47.9% | 4.0% | MEDIUM | P1 |
| 6 | string_functions | 19 | 78.7% | 2.0% | LOW | P1 |
| 7 | path_navigation | 1 | 90.0% | 0.1% | LOW | P2 |
| 8 | datetime_functions | 1 | 83.3% | 0.1% | LOW | P2 |
| 9 | boolean_logic | 1 | 83.3% | 0.1% | LOW | P2 |

**ALREADY COMPLETED:**
- comments_syntax: 100% (9/9) - COMPLETED IN PREVIOUS WORK

---

## Task Breakdown (UPDATED - February 4, 2026)

### Task SP-110-001: Comparison Operators - DateTime and Quantity

**Impact:** 75 tests (77.8% → 100%, +8.0% overall)
**Effort:** 16-24 hours
**Complexity:** HIGH
**Priority:** P0
**Status:** READY FOR EXECUTION

**Description:**
Fix datetime timezone handling, DATE/TIME type compatibility, and Quantity unit conversion in comparison operators.

**Key Issues:**
- DateTime timezone handling in comparisons
- DATE vs TIME literal comparisons (currently blocked by validation)
- Mixed-type comparisons (Quantity vs string)
- Calendar duration comparisons

**Implementation:**
1. Implement datetime timezone normalization
2. Fix DATE/TIME type compatibility or accept validation blocking
3. Add Quantity unit conversion for comparisons
4. Implement calendar duration conversion
5. Test all comparison operators

**Expected Compliance:** 63.5% → 72.6% (+9.1%)

### Task SP-110-002: Collection Functions - CTE Architecture

**Impact:** 67 tests (52.5% → 100%, +7.2% overall)
**Effort:** 20-30 hours
**Complexity:** VERY_HIGH
**Priority:** P0
**Status:** READY FOR EXECUTION

**Description:**
Implement comprehensive CTE column preservation and complete set comparison functions.

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

**Expected Compliance:** 72.6% → 80.3% (+7.7%)

### Task SP-110-003: Type Functions - Complete Implementation

**Impact:** 41 tests (64.7% → 100%, +4.4% overall)
**Effort:** 12-18 hours
**Complexity:** MEDIUM
**Priority:** P1
**Status:** READY FOR EXECUTION

**Description:**
Fix type conversion edge cases and complete type operations.

**Key Issues:**
- `convertsToInteger()`, `convertsToDecimal()` with negative numbers
- `as()` type conversion edge cases
- `is()` operator with complex types
- `ofType()` collection filtering

**Implementation:**
1. Fix negative number type conversion
2. Complete `as()` operator for all types
3. Fix `is()` operator edge cases
4. Implement `ofType()` collection filtering
5. Test all type functions

**Expected Compliance:** 80.3% → 86.0% (+5.7%)

### Task SP-110-004: Function Calls - Signature Resolution

**Impact:** 46 tests (59.3% → 100%, +4.9% overall)
**Effort:** 10-16 hours
**Complexity:** MEDIUM
**Priority:** P1
**Dependencies:** SP-110-003 (Type Functions) - DEPENDENCY REMOVED (can run parallel)
**Status:** READY FOR EXECUTION

**Description:**
Implement function signature registry and parameter type coercion.

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

**Expected Compliance:** 86.0% → 91.4% (+5.4%)

### Task SP-110-005: Arithmetic Operators - Precedence and Precision

**Impact:** 37 tests (47.9% → 100%, +4.0% overall)
**Effort:** 8-14 hours
**Complexity:** MEDIUM
**Priority:** P1
**Status:** READY FOR EXECUTION

**Description:**
Fix unary polarity operator precedence and decimal precision handling.

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

**Expected Compliance:** 91.4% → 95.6% (+4.2%)

### Task SP-110-006: Comments Syntax - Parser Support

**Impact:** 0 tests (100% → 100%, +0.0% overall)
**Effort:** 0 hours
**Complexity:** LOW
**Priority:** P1
**Status:** COMPLETED (100% pass rate achieved)

**Description:**
Implement full comment syntax support in parser.

**Key Issues:**
- Multi-line comments `/* */`
- Single-line comments `//`
- Comment preservation in AST

**Implementation:**
1. Add comment parsing to lexer
2. Implement comment AST nodes
3. Test comment syntax

**Expected Compliance:** 95.6% → 97.8% (+2.2%)

### Task SP-110-007: String Functions - Edge Cases

**Impact:** 19 tests (78.7% → 100%, +2.0% overall)
**Effort:** 6-10 hours
**Complexity:** LOW
**Priority:** P1
**Status:** READY FOR EXECUTION

**Description:**
Fix remaining string function edge cases.

**Key Issues:**
- `matches()` with regex patterns
- `replaceAll()` edge cases
- `substring()` boundary conditions

**Implementation:**
1. Fix regex pattern matching
2. Fix replaceAll edge cases
3. Fix substring boundary conditions
4. Test all string functions

**Expected Compliance:** 97.8% → 99.5% (+1.7%)

### Task SP-110-008: Quick Wins - Remaining Edge Cases

**Impact:** 3 tests (various → 100%, +0.3% overall)
**Effort:** 2-4 hours
**Complexity:** LOW
**Priority:** P2
**Status:** READY FOR EXECUTION

**Description:**
Fix remaining edge cases in boolean_logic, path_navigation, datetime, math.

**Key Issues:**
- `empty().not()` logic
- `now() > today()` comparison
- Path navigation edge cases

**Implementation:**
1. Fix empty().not() logic
2. Fix now() > today() comparison
3. Fix path navigation edge cases
4. Test all edge cases

**Expected Compliance:** 99.5% → 100.0% (+0.5%)

---

## Success Metrics

### Target: 100% Compliance

| Metric | Baseline | Target |
|--------|----------|--------|
| **Overall Compliance** | 63.5% | 100% |
| **Tests Passing** | 593/934 | 934/934 |
| **Tests Fixed** | 0 | 341 |
| **Improvement** | - | +36.5% |

### Completed Tasks
- [ ] SP-110-001: Comparison Operators
- [ ] SP-110-002: Collection Functions
- [ ] SP-110-003: Type Functions
- [ ] SP-110-004: Function Calls
- [ ] SP-110-005: Arithmetic Operators
- [ ] SP-110-006: Comments Syntax
- [ ] SP-110-007: String Functions
- [ ] SP-110-008: Quick Wins

---

## Testing Strategy

### After Each Task
1. Run compliance test suite
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

## Execution Plan (ACTIVE - February 4, 2026)

### ULTRAPILOT Round 1 (Parallel - 5 Workers)
**Status:** READY TO LAUNCH
**Estimated Duration:** 12-18 hours (parallel execution)

- **Worker 1:** SP-110-001 (Comparison Operators) - 75 failures [P0, HIGH, +8.0%]
- **Worker 2:** SP-110-003 (Type Functions) - 41 failures [P1, MEDIUM, +4.4%]
- **Worker 3:** SP-110-004 (Function Calls) - 46 failures [P1, MEDIUM, +4.9%]
- **Worker 4:** SP-110-005 (Arithmetic Operators) - 37 failures [P1, MEDIUM, +4.0%]
- **Worker 5:** SP-110-007 (String Functions) - 19 failures [P1, LOW, +2.0%]

**Expected Compliance After Round 1:** 69.2% → 93.1% (+23.9%)

### ULTRAPILOT Round 2 (Parallel - 2 Workers)
**Status:** PENDING ROUND 1 COMPLETION
**Estimated Duration:** 20-30 hours (parallel execution)

- **Worker 1:** SP-110-002 (Collection Functions) - 67 failures [P0, VERY_HIGH, +7.2%]
- **Worker 2:** SP-110-008 (Quick Wins) - 3 failures [P2, LOW, +0.3%]

**Expected Compliance After Round 2:** 93.1% → 100.0% (+6.9%)

### Integration & Testing
- Full compliance suite run
- Regression testing
- Code review cycle (RALPH)
- Final validation

**Expected Duration:** 4-6 hours

### Total Effort Estimate
- **Sequential:** 80-126 hours
- **Parallelized (ultrapilot):** 22-33 hours

---

## Dependencies

### Internal
- SP-109 must be merged to main (DONE)
- Compliance test suite functional (DONE)
- Package installed in dev mode (DONE)

### Task Dependencies
- SP-110-004 (Function Calls) depends on SP-110-003 (Type Functions)

### External
- None (self-contained sprint)

---

## Risk Assessment

### Low Risk
- Comments syntax: Well-defined parser changes
- String functions: Clear edge cases
- Quick wins: Isolated issues

### Medium Risk
- Type functions: Type system complexity
- Function calls: Signature resolution complexity
- Arithmetic operators: Precedence rules

### High Risk
- Comparison operators: Timezone and unit conversion complexity
- Collection functions: Complex CTE architecture changes

### Mitigation
- Start with lower-risk tasks in Ultraround 1
- Tackle complex tasks in Ultraround 2 with dependencies resolved
- Test after each fix, not just at end
- Keep changes minimal and targeted
- Use ultrapilot for parallel execution
- RALPH loop for code review until approved

---

## Definition of Done

For each task:
- [ ] All tests in category passing
- [ ] Code reviewed and approved by architect
- [ ] No regressions in other categories
- [ ] Documentation updated (if needed)
- [ ] Compliance report shows improvement
- [ ] Both DuckDB and PostgreSQL tests passing

For sprint:
- [ ] All planned tasks complete
- [ ] Full compliance suite at 100%
- [ ] Code reviewed and approved
- [ ] Ready to merge to main
- [ ] Sprint documentation complete

---

## Timeline Estimate

**Phase 1 (Planning):** Complete
**Phase 2 (Prioritization):** In Progress
**Phase 3 (User Approval):** Pending
**Phase 4 (Create Tasks):** Pending
**Phase 5 (Execution):** 22-33 hours (parallelized)
**Phase 6 (Review):** 4-8 hours (RALPH loop)
**Phase 7 (Validation):** 2-4 hours
**Phase 8 (Merge):** 1-2 hours
**Phase 9 (Cleanup):** 1 hour
**Phase 10 (Documentation):** 2-3 hours

**Total Sprint Duration:** 32-51 hours (1.3-2.1 days of parallel work)

---

