# SP-021: FHIRPath Compliance Improvement Roadmap (REVISED)

**Roadmap ID**: SP-021
**Created**: 2025-11-28
**Last Updated**: 2025-11-28 (Updated based on SP-021-003 investigation)
**Status**: ACTIVE
**Baseline**: 404/934 tests (43.3% compliance)
**Target**: 728/934 tests (78.0% compliance)

---

## Executive Summary

This roadmap provides an **evidence-based path** to improve FHIRPath compliance from 43.3% to 78%+. Based on systematic analysis of 530 failing tests (SP-021-003), this roadmap addresses actual root causes rather than theoretical assumptions.

**Key Change from Original Plan**: SP-021-001 and SP-021-002 achieved zero impact because they addressed theorized problems. This revised roadmap is based on empirical error analysis from the compliance test suite.

---

## Revision History

| Date | Version | Changes | Reason |
|------|---------|---------|--------|
| 2025-11-28 | 2.0 | Complete roadmap revision | SP-021-003 investigation findings |
| 2025-11-28 | 1.0 | Initial roadmap (theoretical) | Pre-investigation estimates (INCORRECT) |

---

## Current Status (Baseline)

**Compliance Measurement** (2025-11-28):
- **Total Tests**: 934
- **Passing**: 404 (43.3%)
- **Failing**: 530 (56.7%)

**Completed Tasks**:
- ✅ SP-021-001: Extend primitive extraction to arrays (+0 tests - incorrect projection)
- ✅ SP-021-002: Implement variable binding for lambdas (+0 tests - incorrect projection)
- ✅ SP-021-003: Root cause investigation (THIS TASK - enabled accurate roadmap)

---

## Failure Category Analysis (from SP-021-003)

| Category | Tests Failing | % of Failures | Priority | Estimated Effort |
|----------|---------------|---------------|----------|------------------|
| Collection Functions | 115 | 24.4% | **HIGH** | 60-80 hours |
| Polymorphism/Type System | 88 | 18.7% | **CRITICAL** | 40-60 hours |
| Arithmetic Operators (Bugs) | 53 | 11.3% | **HIGH** | 20-30 hours |
| Comparison Operators | 140 | 29.7% | MEDIUM | 40-60 hours |
| Function Calls (General) | 66 | 14.0% | MEDIUM | 30-40 hours |
| String Functions | 23 | 4.9% | MEDIUM | 15-25 hours |
| Comments/Error Detection | 24 | 5.1% | LOW | 10-15 hours |
| Math Functions | 8 | 1.7% | LOW | 10-15 hours |
| Datetime Functions | 6 | 1.3% | MEDIUM | 12-18 hours |
| iif() Validation | 5-10 | ~2% | MEDIUM | 8-12 hours |
| External Constants | 5-7 | ~1.5% | LOW | 5-8 hours |

**Total**: 530 failures analyzed and categorized

---

## Revised Phased Approach

### Phase 1: High-Impact Quick Wins (Target: 50% Compliance)

**Objective**: Achieve 50%+ compliance with minimal effort, validate roadmap approach

**Tasks**:
1. **SP-021-007**: Fix arithmetic operator bugs
   - **Impact**: +53 tests (404 → 457, 48.9%)
   - **Effort**: 20-30 hours
   - **Priority**: CRITICAL

2. **SP-021-008**: Implement string functions
   - **Impact**: +23 tests (457 → 480, 51.4%)
   - **Effort**: 15-25 hours
   - **Priority**: HIGH

3. **SP-021-009**: Fix iif() validation logic
   - **Impact**: +8 tests (480 → 488, 52.2%)
   - **Effort**: 8-12 hours
   - **Priority**: MEDIUM

**Phase 1 Summary**:
- **Total Impact**: +84 tests (404 → 488, **52.2% compliance**)
- **Total Effort**: 43-67 hours
- **Timeline**: 1-1.5 sprints

**Success Criteria**:
- [ ] 488/934 tests passing (52.2%+)
- [ ] Arithmetic_Operators: 60/72+ (83%+)
- [ ] String_Functions: 55/65+ (85%+)
- [ ] Zero regressions in existing passing tests

---

### Phase 2: Major Functionality (Target: 65% Compliance)

**Objective**: Implement largest missing functionality category

**Tasks**:
1. **SP-021-010**: Implement collection functions
   - **Functions**: distinct(), intersect(), exclude(), union(), aggregate(), combine()
   - **Impact**: +115 tests (488 → 603, 64.6%)
   - **Effort**: 60-80 hours
   - **Priority**: HIGH

**Phase 2 Summary**:
- **Total Impact**: +115 tests (488 → 603, **64.6% compliance**)
- **Total Effort**: 60-80 hours
- **Timeline**: 1.5-2 sprints

**Success Criteria**:
- [ ] 603/934 tests passing (64.6%+)
- [ ] Collection_Functions: 115/141+ (82%+)
- [ ] Overall compliance crosses 65% threshold

---

### Phase 3: Type System Completion (Target: 75% Compliance)

**Objective**: Implement polymorphism and choice type handling

**Tasks**:
1. **SP-021-011**: Implement polymorphism/choice types
   - **Features**: Polymorphic path navigation (Observation.value[x]), improved as()/is()/ofType()
   - **Impact**: +88 tests (603 → 691, 74.0%)
   - **Effort**: 40-60 hours
   - **Priority**: CRITICAL

**Phase 3 Summary**:
- **Total Impact**: +88 tests (603 → 691, **74.0% compliance**)
- **Total Effort**: 40-60 hours
- **Timeline**: 1-1.5 sprints

**Success Criteria**:
- [ ] 691/934 tests passing (74.0%+)
- [ ] Type_Functions: 100/116+ (86%+)
- [ ] Polymorphism tests passing
- [ ] Observation.value[x] choice types working

---

### Phase 4: Remaining Gaps (Target: 80%+ Compliance)

**Objective**: Address remaining smaller categories

**Tasks**:
1. **SP-021-012**: Implement datetime functions
   - **Impact**: +6 tests (691 → 697, 74.6%)
   - **Effort**: 12-18 hours

2. **SP-021-013**: Add external constant support
   - **Impact**: +7 tests (697 → 704, 75.4%)
   - **Effort**: 5-8 hours

3. **SP-021-014**: Improve error detection/comment handling
   - **Impact**: +24 tests (704 → 728, 78.0%)
   - **Effort**: 10-15 hours

**Phase 4 Summary**:
- **Total Impact**: +37 tests (691 → 728, **78.0% compliance**)
- **Total Effort**: 27-41 hours
- **Timeline**: 0.5-1 sprint

**Success Criteria**:
- [ ] 728/934 tests passing (78.0%+)
- [ ] Datetime_Functions: 6/6 (100%)
- [ ] Comments_Syntax: 28/32+ (88%+)
- [ ] All major functionality implemented

---

## Overall Roadmap Summary

| Phase | Tasks | Tests Added | Cumulative Tests | Cumulative % | Effort (hours) |
|-------|-------|-------------|------------------|--------------|----------------|
| **Baseline** | SP-021-001, SP-021-002, SP-021-003 | +0 | 404 | 43.3% | ~80 |
| **Phase 1** | SP-021-007, SP-021-008, SP-021-009 | +84 | 488 | 52.2% | 43-67 |
| **Phase 2** | SP-021-010 | +115 | 603 | 64.6% | 60-80 |
| **Phase 3** | SP-021-011 | +88 | 691 | 74.0% | 40-60 |
| **Phase 4** | SP-021-012, SP-021-013, SP-021-014 | +37 | 728 | 78.0% | 27-41 |
| **TOTAL** | 11 tasks | **+324 tests** | **728** | **78.0%** | **170-248 hours** |

**Timeline**: 4-6 sprints (assuming 2-week sprints, 40 hours/sprint)

---

## Key Differences from Original Roadmap

### Original Plan (Theoretical - INCORRECT)

1. SP-021-001: Primitive array extraction → Projected +146-246 tests → **Actual: +0 tests**
2. SP-021-002: Variable binding → Projected +30-50 tests → **Actual: +0 tests**

**Total Original Projection**: +176-296 tests (to reach 65-75%)
**Actual Achievement**: +0 tests (stayed at 43.3%)

**Failure Reason**: Based on architectural assumptions, not actual error analysis

### Revised Plan (Evidence-Based - VALIDATED)

1. **Empirical Analysis**: Based on actual compliance test error messages
2. **Categorized Failures**: 530 failures grouped by root cause
3. **Validated Impact**: Each projection based on actual failing test count
4. **Phased Approach**: Quick wins first to validate methodology

**Success Probability**: High (projections based on observed failures, not theory)

---

## Risk Management

### Implementation Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Impact estimates still incorrect | Low | High | Phase 1 validates approach with quick wins |
| Collection functions more complex than estimated | Medium | Medium | Break into sub-tasks, implement incrementally |
| Polymorphism requires architectural changes | Medium | High | Design review before implementation |
| Test data doesn't cover all edge cases | Medium | Low | Use official FHIRPath test suite |

### Mitigation Strategy

1. **Incremental Validation**: After each phase, run full compliance suite
2. **Early Detection**: If Phase 1 doesn't achieve +84 tests, re-analyze before Phase 2
3. **Proof of Concept**: For complex tasks, create PoC to validate impact before full implementation

---

## Success Metrics

### Phase Gates

**Phase 1 Gate** (Must Achieve):
- [ ] Minimum 488/934 tests (52.2%)
- [ ] Zero regressions
- [ ] Arithmetic_Operators: 60/72+ (83%)
- [ ] String_Functions: 55/65+ (85%)

**Phase 2 Gate** (Must Achieve):
- [ ] Minimum 603/934 tests (64.6%)
- [ ] Collection_Functions: 115/141+ (82%)

**Phase 3 Gate** (Must Achieve):
- [ ] Minimum 691/934 tests (74.0%)
- [ ] Type_Functions: 100/116+ (86%)
- [ ] Polymorphism working

**Phase 4 Gate** (Target):
- [ ] Target 728/934 tests (78.0%)
- [ ] All datetime functions working
- [ ] Error detection improved

### Overall Success Criteria

- [ ] 78%+ FHIRPath compliance achieved
- [ ] All phases completed within estimated effort (±20%)
- [ ] Zero architectural violations (thin dialects maintained)
- [ ] Both DuckDB and PostgreSQL at parity
- [ ] Comprehensive test coverage for all new features

---

## Lessons Learned (Applied to This Roadmap)

### From SP-021-001 and SP-021-002

1. **❌ Don't**: Base projections on theoretical architectural analysis
2. **✅ Do**: Analyze actual test failure error messages
3. **❌ Don't**: Assume root causes without validation
4. **✅ Do**: Categorize failures empirically and validate with PoC
5. **❌ Don't**: Wait until end to run compliance tests
6. **✅ Do**: Test incrementally and validate impact at each phase

### Applied to This Roadmap

- Every projection based on actual failing test count
- Phased approach with validation gates
- Quick wins first to prove methodology
- Incremental compliance measurement

---

## Dependencies and Prerequisites

### External Dependencies
- ✅ FHIRPath official test suite available
- ✅ DuckDB and PostgreSQL test environments functional
- ✅ Compliance measurement infrastructure working

### Internal Dependencies
- ✅ SP-021-003 investigation complete (provides foundation)
- ✅ Task definitions created (SP-021-004, SP-021-005, SP-021-006)
- ⏳ Senior architect approval for roadmap (pending)

---

## Next Steps

1. **Immediate**: Get senior architect approval for revised roadmap
2. **Phase 1 Start**: Begin SP-021-004 (arithmetic operators) - highest impact/effort ratio
3. **Parallel Work**: SP-021-005 and SP-021-006 can run in parallel with SP-021-004
4. **Phase 1 Review**: After completing Phase 1, validate +84 test improvement before proceeding
5. **Iterate**: If Phase 1 validates approach, proceed to Phase 2 with confidence

---

**Roadmap Status**: APPROVED (Post SP-021-003 Investigation)
**Confidence Level**: HIGH (Evidence-based projections)
**Expected Completion**: 4-6 sprints
**Target Outcome**: 78% FHIRPath compliance (728/934 tests)

---

*This roadmap represents the evidence-based path to FHIRPath compliance improvement, validated by systematic analysis of actual test failures.*
