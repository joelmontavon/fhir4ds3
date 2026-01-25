# Sprint Plan: FHIRPath 55% Compliance (SP-101)

**Sprint ID**: SP-101-FHIRPath-55pct
**Created**: 2026-01-25
**Sprint Goal**: Achieve 55% compliance (~514 tests) with highest-ROI fixes
**Current Baseline**: 50.1% compliance (468/934 tests)
**Target Duration**: 1 week (~80 hours capacity)

---

## Executive Summary

This sprint focuses on **highest-ROI compliance gaps** to achieve 55%+ compliance. The sprint prioritizes tasks with the highest test impact per effort hour while managing risk through careful scoping and regression testing.

**Sprint Strategy**:
- Focus on **well-defined, high-impact** fixes
- Avoid scope creep through **explicit task boundaries**
- Maintain **zero regression** on currently passing tests
- Establish **foundation for future sprints** through strategic fixes

---

## Current Status Analysis

### Compliance Baseline

| Metric | Value |
|--------|-------|
| Current Compliance | 50.1% (468/934 tests) |
| Target Compliance | 55.0% (514/934 tests) |
| Tests Needed | +46 tests |
| Sprint Duration | 1 week |

### Recently Completed (from SP-100)

- ✅ Aggregation functions (sum, avg, min, max) - +28 tests
- ✅ Conditional expression (iif) - +6 tests
- ✅ Empty collection handling (partial) - +15 tests
- ✅ extension() function fix - Already implemented
- ✅ count() tuple fix - +8 tests

### Remaining Gap Categories

| Priority | Gap | Tests | Effort | ROI (tests/hour) |
|----------|-----|-------|--------|-----------------|
| P1 | Arithmetic type coercion | ~36 | 15-20h | **1.8-2.4** |
| P1 | CTE column propagation | ~20 | 20-30h | **0.67-1.0** |
| P2 | Result logic mismatches | ~184 | 20-30h* | **6.1-9.2*** |
| P2 | Select nested arrays | ~11 | 15-20h | **0.55-0.73** |
| P2 | Type functions | ~44 | 30-40h | **1.1-1.5** |

*Requires categorization first (4h), then top 3 patterns

---

## Sprint Scope

### In Scope

1. **Arithmetic Type Coercion** (P1-A)
   - Implement FHIRPath type promotion rules
   - Fix mixed-type operations (int + decimal)
   - Handle division semantics
   - **Impact**: +36 tests, **Effort**: 15-20 hours

2. **CTE Column Propagation** (P1-C)
   - Fix collection slicing chains: `Patient.name.first().given`
   - Standardize column naming conventions
   - Add regression testing for chains
   - **Impact**: +20 tests, **Effort**: 20-30 hours

3. **Result Logic Mismatches - Top 3 Patterns** (P2-A)
   - Categorize ~184 failures by error type (4h)
   - Implement fixes for top 3 patterns only
   - **Impact**: ~60 tests (estimated), **Effort**: 24-34h total

### Out of Scope

- Complete type functions (deferred to future sprint)
- Select nested arrays (deferred unless capacity allows)
- XOR/Implies operators (lower priority)
- Date/Time literals (lower priority)
- Matches() regex semantics (deferred)

---

## Task Breakdown

### Task SP-101-001: Arithmetic Type Coercion

**Priority**: P1-A (High)
**Estimated Impact**: +36 tests
**Estimated Effort**: 15-20 hours

**Description**: Implement FHIRPath spec-compliant type coercion for arithmetic operators.

**Implementation Requirements**:
1. Add type inference helper for operands
2. Implement type promotion rules per FHIRPath spec:
   - integer + integer = integer
   - integer + decimal = decimal
   - decimal + decimal = decimal
   - division always returns decimal
3. Fix modulo operation edge cases
4. Handle implicit type coercion in function arguments

**Acceptance Criteria**:
- All arithmetic operator tests achieve 70%+ compliance
- Type coercion matches FHIRPath spec behavior
- Both DuckDB and PostgreSQL produce consistent results
- No regression on existing tests

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:2284-2921`

**Dependencies**: None

---

### Task SP-101-002: CTE Column Propagation

**Priority**: P1-B (High)
**Estimated Impact**: +20 tests
**Estimated Effort**: 20-30 hours

**Description**: Resolve CTE column reference propagation in collection function chains.

**Implementation Requirements**:
1. Add column alias registry to TranslationContext
2. Update `_traverse_expression_chain()` to register aliases
3. Fix nested field access on CTE results
4. Document column naming conventions
5. Add integration tests for chained operations

**Acceptance Criteria**:
- Collection slicing chains work correctly
- All chained operation tests pass
- Zero regression on single operations
- Both dialects supported

**Location**:
- `fhir4ds/main/fhirpath/sql/translator.py:1692-4009`
- `fhir4ds/main/fhirpath/sql/context.py`

**Dependencies**: None

---

### Task SP-101-003: Result Logic Mismatches (Top 3 Patterns)

**Priority**: P2-A (Medium, High Impact)
**Estimated Impact**: ~60 tests (after categorization)
**Estimated Effort**: 24-34 hours (includes categorization)

**Description**: Categorize and fix the top 3 patterns in the ~184 "result logic mismatch" failures.

**Implementation Requirements**:
1. **Categorization Phase** (4 hours):
   - Run test suite with detailed error logging
   - Group failures by error type/root cause
   - Identify top 3 patterns by test count
   - Document each pattern with examples

2. **Implementation Phase** (20-30 hours):
   - Implement fixes for top 3 patterns only
   - Batch similar fixes for efficiency
   - Document remaining patterns for future sprint

**Acceptance Criteria**:
- All 184 tests categorized into failure patterns
- Top 3 patterns identified and documented
- Fixes implemented for top 3 patterns
- Remaining patterns documented with estimates
- No regression on existing tests

**Location**: Multiple translator methods

**Dependencies**: None

---

## Success Criteria

### Sprint Success Metrics

1. **Compliance Target**: 55%+ (514/934 tests passing)
2. **Zero Regressions**: All 468 currently passing tests remain passing
3. **High-Impact Focus**: Priority tasks achieve expected test impact
4. **Documentation**: All tasks documented with acceptance criteria met
5. **Dual Dialect Parity**: Both DuckDB and PostgreSQL validated

### Quality Gates

1. **Build**: All tests pass with zero errors
2. **Compliance Report**: Automated report shows 55%+ compliance
3. **Code Review**: All changes reviewed for architectural compliance
4. **Multi-Database Testing**: Both DuckDB and PostgreSQL tested

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Result logic categorization reveals >10 patterns | Medium | Medium | Cap at top 3 patterns, defer remaining |
| CTE propagation fixes cause regressions | Medium | High | Comprehensive regression testing, incremental implementation |
| Arithmetic coercion requires parser changes | Low | Medium | 10-hour checkpoint to reassess approach |
| Team capacity assumptions incorrect | Medium | Medium | Adjust scope based on actual velocity |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Underestimated effort for complex tasks | Medium | Medium | Buffer time in sprint, defer low-priority items |
| Dependencies block parallel execution | Low | Medium | Order tasks sequentially, validate dependencies upfront |
| Unexpected architectural issues | Low | High | Create PEP if needed, pause implementation |

---

## Timeline

### Sprint Schedule

**Assumption**: 1-person team, 1-week sprint

**Day 1**: Sprint planning, task setup, categorization (SP-101-003 part 1)
**Days 2-3**: SP-101-001 Arithmetic Type Coercion
**Days 4-5**: SP-101-002 CTE Column Propagation
**Days 6-7**: SP-101-003 Result Logic Mismatches (implementation)
**Buffer**: Time for regression testing, code review, documentation

### Milestones

| Milestone | Day | Deliverable |
|-----------|-----|-------------|
| M1: Categorization Complete | Day 1 | Top 3 patterns identified |
| M2: Arithmetic Coercion Complete | Day 3 | +36 tests passing |
| M3: CTE Propagation Complete | Day 5 | +20 tests passing |
| M4: 55% Compliance Achieved | Day 7 | 514+ tests passing |

---

## Artifacts

### Deliverables

1. Sprint plan document (this file)
2. Task documents for each SP-101-* task
3. Implementation summary documenting all changes
4. Compliance report showing 55%+ achievement
5. Test results for both DuckDB and PostgreSQL

### Documentation Updates

1. Update compliance tracker with new results
2. Document implementation decisions in project-docs/
3. Update CLAUDE.md with any architectural notes
4. Archive task documents to project-docs/plans/archived-tasks/

---

## Glossary

- **CTE**: Common Table Expression
- **Type Coercion**: Implicit type conversion in mixed-type operations
- **Column Propagation**: Tracking CTE column aliases through operation chains
- **Result Logic Mismatch**: Test produces wrong value/type (not crash/error)

---

## Appendix A: Reference Files

### Key Implementation Files
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py` - SQL translator
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/context.py` - Translation context
- `/mnt/d/fhir4ds3/tests/compliance/fhirpath/official_tests.xml` - Official test suite
- `/mnt/d/fhir4ds3/tests/integration/fhirpath/official_test_runner.py` - Test runner

---

**Sprint Plan Status**: DRAFT - Pending Approval
**Next Step**: Review sprint plan and get user approval before task creation
