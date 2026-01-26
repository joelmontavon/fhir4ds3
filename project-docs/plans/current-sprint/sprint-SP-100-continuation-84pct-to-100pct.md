# Sprint Plan: FHIRPath 100% Compliance Continuation (SP-100-C)

**Sprint ID**: SP-100-Continuation-84pct
**Created**: 2026-01-25
**Sprint Goal**: Continue toward 100% FHIRPath compliance from 84% baseline
**Current Baseline**: 84% compliance (42/50 sample tests)
**Estimated Overall Compliance**: ~55-60% (extrapolated)
**Target Duration**: 1 week sprint
**Approach**: Maximal scope (P0 + P1 tasks after validation)

---

## Executive Summary

This sprint continues the journey toward 100% FHIRPath specification compliance, building on the success of SP-101 (which achieved 55% compliance from 50%). The current baseline shows **84% compliance on a 50-test sample**, but extrapolation suggests **~55-60% overall compliance** across the full 934-test suite.

**Sprint Strategy**:
- **Validate before implementing**: Confirm iif() issues and test gaps
- **Maximal scope**: P0 (critical) + P1 (high-impact) tasks
- **Risk-managed approach**: Each task has clear acceptance criteria
- **Architecture compliance**: Maintain CTE-first, thin dialect principles

**Estimated Impact**:
- **P0 tasks**: ~25-30 tests
- **P1 tasks**: ~25 tests
- **Total potential**: ~50-55 tests

---

## Sprint Context

### Recent Achievements (SP-101)

**Completed**: ✅ Merged to main branch
- **SP-101-002**: CTE column propagation implementation (~20 tests)
- **SP-101-003**: convertsTo DateTime/Time pattern fixes (~8 tests)
- **Bug fixes**: Code review critical and high-priority issues

**Key Technical Wins**:
- CTE column reference propagation now works correctly
- DateTime/Time conversion patterns improved
- Known limitations documented

### Current Baseline: 84% (Sample)

| Metric | Value |
|--------|-------|
| Sample Compliance | 84% (42/50 tests) |
| Estimated Overall | ~55-60% (~514-560/934 tests) |
| Sample Failures | 8 tests |

### Validation Findings

**iif() Function Status**:
- ✅ **Simple cases work**: `iif(true, 1, 0)` passes
- ❌ **Empty collection handling fails**: `iif({}, true, false)` fails
- ❌ **Union expressions in criteria**: `iif({} | true, true, false)` fails

**This is NOT a routing fix** - the iif() implementation exists but needs edge case handling.

---

## Sprint Scope

### In Scope (Maximal Approach)

**P0 (Critical)** - Must complete:
1. **SP-100-002-Enhanced**: iif() empty collection handling (3-5 tests)
2. **SP-100-009**: XOR operator implementation (9 tests, 2-4 hrs)
3. **SP-100-010**: Implies operator completion (7 tests, 2-4 hrs)
4. **SP-100-011**: Matches() regex semantics (11 tests, 4-6 hrs)

**P1 (High Impact)** - Complete if capacity allows:
1. **SP-100-012**: DateTime literals (14 tests, 6-8 hrs)
2. **SP-100-007**: Select nested arrays (11 tests, 8-12 hrs)

### Out of Scope

- **SP-100-005**: Type functions (needs PEP for architecture validation)
- **SP-100-008**: Result logic batch fixes (needs spike/research)
- Performance optimization
- New feature development
- Technical debt not related to test compliance

---

## Task Breakdown

### P0: Critical Tasks

#### Task SP-100-002-Enhanced: iif() Empty Collection Handling

**Priority**: P0 (Critical)
**Estimated Impact**: +3-5 tests
**Estimated Effort**: 2-3 hours

**Description**: Fix iif() function to handle empty collections and union expressions in criteria.

**Current State**:
- ✅ Simple cases work: `iif(true, 1, 0)` returns `1`
- ❌ Empty collections fail: `iif({}, true, false)` causes errors
- ❌ Union expressions fail: `iif({} | true, true, false)` not handled

**Root Cause Analysis**:
- Empty collection `{}` in criterion expression causes evaluation errors
- Union expressions (`{}` | true) produce multi-item collections
- Current implementation expects single boolean criterion

**Implementation Requirements**:
1. Add empty collection detection in criterion evaluation
2. Handle union expressions as multi-item criteria
3. Apply FHIRPath empty collection semantics:
   - Empty collection in criterion → evaluate to false
   - Union with empty → evaluate non-empty side
4. Update `visit_conditional()` method in translator

**Acceptance Criteria**:
- `iif({}, true, false)` → returns `false` (empty → false)
- `iif({} | true, true, false)` → returns `true` (union evaluation)
- `iif(true & {}, 1, 0)` → returns `0` (and with empty → empty → false)
- `iif({}, {}, {})` → handles all empty cases
- No regression on existing passing iif() tests

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:visit_conditional()`

**Dependencies**: None (builds on existing iif() implementation)

**Testing Strategy**:
- Test empty collection in criterion
- Test union expressions in criterion
- Test nested empty collections
- Verify all existing iif() tests still pass

---

#### Task SP-100-009: XOR Operator Implementation

**Priority**: P0 (Critical)
**Estimated Impact**: +9 tests
**Estimated Effort**: 2-4 hours

**Description**: Implement XOR operator using `(a OR b) AND NOT (a AND b)` pattern.

**Current State**:
- XOR operator not implemented or partially implemented
- FHIRPath spec defines xor as exclusive OR

**Implementation Requirements**:
1. Implement `visit_xor_expression()` method
2. Generate SQL: `(a OR b) AND NOT (a AND b)`
3. Handle boolean logic with empty collections:
   - `true xor {}` → `true` (empty treated as false)
   - `{} xor {}` → `false` (both empty)
4. Ensure spec-compliant semantics for boolean operands
5. Support both DuckDB and PostgreSQL dialects

**Acceptance Criteria**:
- `true xor false` → `true`
- `true xor true` → `false`
- `false xor false` → `false`
- `true xor {}` → `true`
- `{} xor {}` → `false`
- All 9 XOR tests pass
- Both dialects produce consistent results

**Location**: `fhir4ds/main/fhirpath/sql/translator.py`

**Dependencies**: None

**Testing Strategy**:
- Unit tests for XOR truth table
- Empty collection edge cases
- Nested XOR expressions
- XOR with other boolean operators

---

#### Task SP-100-010: Implies Operator Completion

**Priority**: P0 (Critical)
**Estimated Impact**: +7 tests
**Estimated Effort**: 2-4 hours

**Description**: Complete implies() operator with proper empty collection semantics.

**Current State**:
- Implies operator partially implemented
- Edge cases with empty collections need work

**Implementation Requirements**:
1. Complete `visit_implies_expression()` method
2. Generate SQL: `(NOT a) OR b`
3. Handle empty collection semantics per FHIRPath spec:
   - `true implies {}` → `{} ` (propagate empty)
   - `{} implies true` → `true` (empty antecedent is true)
   - `false implies {}` → `true` (false implies anything)
4. Ensure truth table matches spec:
   - `true implies true` → `true`
   - `true implies false` → `false`
   - `false implies true` → `true`
   - `false implies false` → `true`

**Acceptance Criteria**:
- All implies() truth table cases pass
- Empty collection semantics correct per spec
- All 7 implies tests pass
- Both dialects supported

**Location**: `fhir4ds/main/fhirpath/sql/translator.py`

**Dependencies**: None

**Testing Strategy**:
- Complete truth table validation
- Empty collection edge cases
- Nested implies expressions
- Implies with other boolean operators

---

#### Task SP-100-011: Matches() Regex Semantics

**Priority**: P0 (Critical)
**Estimated Impact**: +11 tests
**Estimated Effort**: 4-6 hours

**Description**: Align matches() function with FHIRPath spec regex behavior.

**Current State**:
- matches() function exists but has semantic differences
- Some regex patterns don't match expected behavior

**Implementation Requirements**:
1. Review current matches() implementation
2. Identify semantic differences with FHIRPath spec
3. Fix regex pattern matching behavior:
   - Anchor handling (^, $)
   - Case sensitivity
   - Multi-line matching
   - Unicode handling
4. Ensure dialect parity (DuckDB vs PostgreSQL regex)

**Acceptance Criteria**:
- All 11 matches() tests pass
- Regex behavior matches FHIRPath spec
- Both dialects produce consistent results
- No regression on existing string function tests

**Location**: String function implementations in translator

**Dependencies**: None

**Testing Strategy**:
- Test all regex patterns from official suite
- Verify anchor behavior
- Test case sensitivity
- Test special character escaping

---

### P1: High Impact Tasks

#### Task SP-100-012: DateTime Literals

**Priority**: P1 (High Impact)
**Estimated Impact**: +14 tests
**Estimated Effort**: 6-8 hours

**Description**: Fix partial dates and timezone handling in DateTime literals.

**Current State**:
- Partial dates fail: `@2018-03` (month-only)
- Timezone suffix issues: `@2012-04-15T15:00:00Z`
- Date parsing edge cases

**Implementation Requirements**:
1. Enhance date literal parsing to handle partial dates:
   - Year-only: `@2018`
   - Year-month: `@2018-03`
   - Year-month-day: `@2018-03-01`
2. Handle timezone suffixes:
   - `Z` suffix (UTC)
   - `+HH:MM` offset
   - `-HH:MM` offset
3. Fix date parsing edge cases:
   - Leap years
   - Month boundaries
   - Invalid date detection
4. Ensure both dialects handle dates consistently

**Acceptance Criteria**:
- Partial dates parse correctly
- Timezone suffixes handled properly
- All 14 DateTime literal tests pass
- Both dialects supported
- No regression on existing date functions

**Location**: Temporal function implementations, parser

**Dependencies**: None

**Testing Strategy**:
- Test all partial date formats
- Test timezone variations
- Test invalid date handling
- Verify date arithmetic works with partial dates

---

#### Task SP-100-007: Select Nested Arrays

**Priority**: P1 (High Impact)
**Estimated Impact**: +11 tests
**Estimated Effort**: 8-12 hours

**Description**: Implement nested array handling in select() projections.

**Current State**:
- Nested array structures not flattened properly
- Union projections fail in select
- Example: `Patient.name.select(given.family)`

**Implementation Requirements**:
1. Detect nested array structures in select projections
2. Implement array flattening for nested results:
   - `select(given.family)` where given is array
   - Flatten to `[[given1.family1, given1.family2], [given2.family1]]`
3. Support union projections: `select(use | system)`
4. Fix SQL syntax issues for nested UNNEST
5. Ensure CTE structure handles nesting correctly

**Acceptance Criteria**:
- Nested arrays flatten correctly
- Union projections work
- All 11 select nested array tests pass
- No regression on existing select tests
- Both dialects supported

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:visit_select_clause()`

**Dependencies**: May overlap with CTE column propagation (SP-101-002, completed)

**Testing Strategy**:
- Test nested array flattening
- Test union projections
- Test deeply nested structures
- Verify CTE structure correctness

---

## P2: Deferred Tasks

### Task SP-100-005: Type Functions (Deferred)

**Reason**: Needs PEP for architecture validation
**Impact**: ~44 tests
**Complexity**: High (polymorphic type resolution)

**Issues**:
- Polymorphic type casting in `as()`
- `ofType()` with primitive types fails
- Type checking edge cases

**Next Steps**:
1. Create PEP for type system architecture
2. Get architect approval
3. Implement in future sprint

---

### Task SP-100-008: Result Logic Mismatches (Deferred)

**Reason**: Needs spike/research to categorize
**Impact**: ~184 tests
**Complexity**: Unknown (varies by pattern)

**Approach**:
1. Categorize failures by error type
2. Identify top 3 patterns
3. Implement high-impact fixes
4. Defer remaining issues

**Next Steps**:
1. Run analysis sprint
2. Document patterns
3. Plan implementation for future sprint

---

## Task Dependencies

```
P0 Tasks (Can run in parallel):
SP-100-002-Enhanced (iif empty collections) ─┐
SP-100-009 (XOR) ───────────────────────────┼─→ No dependencies
SP-100-010 (Implies) ───────────────────────┤
SP-100-011 (Matches regex) ──────────────────┘

P1 Tasks (Can run in parallel after P0):
SP-100-012 (DateTime literals) ─────────────┐
SP-100-007 (Select nested arrays) ───────────┘

P2 Tasks (Deferred):
SP-100-005 (Type functions) ──→ Needs PEP
SP-100-008 (Result logic) ────→ Needs spike
```

---

## Success Criteria

### Sprint Success Metrics

1. **P0 Complete**: All 4 P0 tasks completed and tested
2. **P1 Complete**: All 2 P1 tasks completed (if capacity allows)
3. **Compliance Progress**: +50-55 tests passing (estimated)
4. **Zero Regressions**: All currently passing tests (42) remain passing
5. **Architecture Compliance**: No violations of CTE-first, thin dialect principles
6. **Documentation**: All tasks documented with acceptance criteria

### Quality Gates

1. **Build**: All tests pass with zero errors
2. **Compliance Report**: Shows improvement in compliance percentage
3. **Code Review**: All changes reviewed for architectural compliance
4. **Multi-Database Testing**: Both DuckDB and PostgreSQL validated

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| iif() edge cases more complex than expected | Medium | Medium | Start with simple empty collection case, add union handling incrementally |
| XOR/Implies operator dialect differences | Low | Medium | Test both dialects early, use dialect abstraction layer |
| Regex semantics vary significantly between dialects | Medium | Medium | May need dialect-specific regex implementations |
| DateTime parsing requires parser changes | Low | Medium | Validate parser extensibility before implementing |
| Select nested arrays break existing functionality | Medium | High | Comprehensive regression testing, incremental implementation |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Underestimated effort for complex tasks | Medium | Medium | Prioritize P0 tasks, defer P1 if needed |
| P1 tasks take longer than expected | Medium | Low | Cap P1 scope, focus on P0 completion |
| Unexpected architectural issues | Low | High | Pause implementation, create PEP if needed |

---

## Timeline

### Sprint Schedule (1 Week)

**Assumption**: 1-person team, 1-week sprint

**Day 1**: Validation & Planning
- Validate iif() issues with targeted tests
- Review existing iif() implementation
- Set up task branches/documentation

**Days 2-3**: P0 Tasks (Part 1)
- **SP-100-002-Enhanced**: iif() empty collection handling (2-3 hrs)
- **SP-100-009**: XOR operator (2-4 hrs)
- **SP-100-010**: Implies operator (2-4 hrs)

**Days 4-5**: P0 Tasks (Part 2)
- **SP-100-011**: Matches regex semantics (4-6 hrs)
- Regression testing for P0 tasks
- Code review and documentation

**Days 6-7**: P1 Tasks (if capacity allows)
- **SP-100-012**: DateTime literals (6-8 hrs)
- **SP-100-007**: Select nested arrays (8-12 hrs)
- Final regression testing
- Sprint documentation

### Milestones

| Milestone | Day | Deliverable |
|-----------|-----|-------------|
| M1: Validation Complete | Day 1 | iif() issues confirmed, plan finalized |
| M2: P0 Part 1 Complete | Day 3 | iif(), XOR, Implies working |
| M3: P0 Part 2 Complete | Day 5 | Matches regex working, P0 done |
| M4: P1 Complete (optional) | Day 7 | DateTime, Select nested arrays done |
| M5: Sprint Complete | Day 7 | All tests passing, documentation done |

---

## Artifacts

### Deliverables

1. Sprint plan document (this file)
2. Task documents for each SP-100-* task (updated)
3. Implementation summary documenting all changes
4. Compliance report showing improvement
5. Test results for both DuckDB and PostgreSQL

### Documentation Updates

1. Update compliance tracker with new results
2. Document implementation decisions in project-docs/
3. Update CLAUDE.md with any architectural notes
4. Create PEP for SP-100-005 (Type functions) if needed
5. Archive task documents to project-docs/plans/archived-tasks/

---

## Glossary

- **CTE**: Common Table Expression
- **Empty Collection**: `{}` literal representing empty collection in FHIRPath
- **Union Expression**: `|` operator combining collections
- **XOR**: Exclusive OR boolean operator
- **Implies**: Logical implication operator (`a implies b` = `NOT a OR b`)
- **Regex Semantics**: Behavior of regular expression matching
- **DateTime Literal**: `@` prefix for date/time constants in FHIRPath

---

## Appendix A: Reference Files

### Key Implementation Files
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py` - SQL translator (11,000+ lines)
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/context.py` - Translation context
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser_core/ast_extensions.py` - Parser extensions
- `/mnt/d/fhir4ds3/tests/compliance/fhirpath/official_tests.xml` - Official test suite
- `/mnt/d/fhir4ds3/tests/integration/fhirpath/official_test_runner.py` - Test runner

### Compliance References
- `/mnt/d/fhir4ds3/compliance_report.json` - Latest compliance report (84% sample)
- `/mnt/d/fhir4ds3/project-docs/plans/current-sprint/sprint-FHIRPath-summary.md` - SP-100 summary
- `/mnt/d/fhir4ds3/project-docs/plans/current-sprint/sprint-SP-101-FHIRPath-55pct.md` - SP-101 plan

### Running Compliance Tests

```bash
# Quick compliance check (sample)
PYTHONPATH=/mnt/d/fhir4ds3:$PYTHONPATH python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner('duckdb')
report = runner.run_official_tests()
print(f'Compliance: {report.compliance_percentage:.1f}%')
"

# Full test suite (takes longer)
python3 -m pytest tests/compliance/fhirpath/ -v
```

---

## Appendix B: Test Categories

### Current Sample Compliance (42/50 passing)

| Category | Passing | Total | Compliance |
|----------|---------|-------|------------|
| Path Navigation | 9 | 9 | 100% |
| Function Calls | 9 | 9 | 100% |
| Basic Expressions | 2 | 2 | 100% |
| Type Functions | 7 | 8 | 87.5% |
| Comments Syntax | 7 | 8 | 87.5% |
| Collection Functions | 4 | 8 | 50% |
| Error Handling | 1 | 2 | 50% |
| Arithmetic Operators | 3 | 4 | 75% |

### Failing Tests (8)

1. **Comment syntax** (2): Unfinished expressions
2. **Type functions** (1): Polymorphism is() test
3. **Collection functions** (4): $this, skip(), CTE issues
4. **Error handling** (1): Negative literal convertsTo

---

**Sprint Plan Status**: DRAFT - Ready for Review
**Next Step**: Review sprint plan and get user approval before implementation

---

## Appendix C: iif() Validation Plan

Before implementing SP-100-002-Enhanced, validate the specific iif() issues:

### Test Cases to Validate

```python
# Simple case (should already work)
iif(true, 1, 0) → 1 ✅

# Empty collection in criterion (currently fails)
iif({}, true, false) → false ❌
iif({} | true, true, false) → true ❌

# Union with empty (currently fails)
iif(true & {}, 1, 0) → 0 ❌

# All empty (edge case)
iif({}, {}, {}) → {} ❓
```

### Validation Approach

1. Create targeted test file for iif() edge cases
2. Run tests to confirm specific failures
3. Review `visit_conditional()` implementation
4. Identify exact changes needed
5. Implement fixes incrementally

---

**End of Sprint Plan**
