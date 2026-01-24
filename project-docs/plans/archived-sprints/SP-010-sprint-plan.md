# Sprint 010 Plan - Option B: Broader Coverage

**Plan Type**: Sprint Refocus - Critical Correction Response
**Date Created**: 2025-10-17
**Sprint**: 010
**Duration Remaining**: ~2-3 weeks
**Strategy**: Option B - Fix multiple medium-impact areas for broader improvement

---

## Executive Summary

**Current State**: 64.99% compliance (607/934 tests passing)
**Target State**: 72.4% compliance (676/934 tests passing)
**Expected Gain**: +69 tests (+7.4% improvement)

**Strategy**: Address multiple medium-impact categories to build broader foundation for Sprint 010, rather than deep-dive on single critical area.

---

## Background

See `CRITICAL-CORRECTION-SP-009-compliance-reality.md` for context on why Sprint 009 is being refocused from false 100% claims to actual 65% baseline.

**Key Decision**: Selected Option B (Broader Coverage) over Option A (Critical Blockers) to:
- Build foundation across multiple categories
- Achieve measurable improvement in 5 different areas
- Create momentum through multiple wins
- Defer deep Type Functions work to Sprint 011

---

## Refocus Task Breakdown

### Task 1: Fix Path Navigation Basics
**Task ID**: SP-010-001
**Priority**: Critical
**Estimated Effort**: 16h (2 days)
**Current State**: 2/10 tests (20%)
**Target State**: 8/10 tests (80%)
**Expected Gain**: +8 tests

**Scope**:
- Fix escaped identifier handling (`` `given` ``)
- Fix basic path traversal (`name.given`, `birthDate`)
- Implement context validation
- Add semantic validation for invalid paths

**Success Criteria**:
- [ ] Escaped identifiers work
- [ ] Basic paths work
- [ ] Context validation works
- [ ] 8/10 Path Navigation tests pass
- [ ] Zero regressions

---

### Task 2: Fix Comments/Syntax Validation
**Task ID**: SP-010-002
**Priority**: High
**Estimated Effort**: 16-20h (2-3 days)
**Current State**: 15/32 tests (46.9%)
**Target State**: 28/32 tests (87.5%)
**Expected Gain**: +17 tests

**Scope**:
- Fix multi-line comment edge cases
- Implement semantic validation for incomplete comments
- Handle comment syntax edge cases
- Validate according to FHIRPath specification

**Success Criteria**:
- [ ] Multi-line comments validated
- [ ] Incomplete comments detected
- [ ] 28/32 Comments/Syntax tests pass
- [ ] Zero regressions

---

### Task 3: Fix Arithmetic Operators
**Task ID**: SP-010-003
**Priority**: High
**Estimated Effort**: 16-20h (2-3 days)
**Current State**: 36/72 tests (50%)
**Target State**: 65/72 tests (90%)
**Expected Gain**: +36 tests

**Scope**:
- Fix unary operators (`+x`, `-x`)
- Fix division edge cases
- Implement proper type coercion
- Handle arithmetic operator precedence

**Success Criteria**:
- [ ] Unary operators work
- [ ] Division edge cases handled
- [ ] 65/72 Arithmetic tests pass
- [ ] Zero regressions

---

### Task 4: Complete Math Functions (100%)
**Task ID**: SP-010-004
**Priority**: Medium
**Estimated Effort**: 4h (0.5 days)
**Current State**: 27/28 tests (96.4%)
**Target State**: 28/28 tests (100%)
**Expected Gain**: +1 test

**Scope**:
- Identify and fix the single failing math test
- Verify all math functions
- Achieve category excellence

**Success Criteria**:
- [ ] All 28 math tests pass
- [ ] Category at 100%
- [ ] Zero regressions

---

### Task 5: Improve String Functions
**Task ID**: SP-010-005
**Priority**: Medium
**Estimated Effort**: 12-16h (1.5-2 days)
**Current State**: 51/65 tests (78.5%)
**Target State**: 58/65 tests (89.2%)
**Expected Gain**: +7 tests

**Scope**:
- Implement `upper()`, `lower()`, `trim()`
- Fix string function edge cases
- Improve string handling robustness

**Success Criteria**:
- [ ] Missing functions implemented
- [ ] 58/65 String tests pass
- [ ] Zero regressions

---

## Sprint Timeline

### Week 1 (Days 1-5): High Priority Fixes
- **Days 1-2**: SP-010-001 (Path Navigation)
- **Days 3-5**: SP-010-002 (Comments/Syntax)

**Checkpoint**: Review progress, adjust if needed

### Week 2 (Days 6-10): Remaining Tasks
- **Days 6-8**: SP-010-003 (Arithmetic Operators)
- **Day 9**: SP-010-004 (Math Functions)
- **Days 9-10**: SP-010-005 (String Functions)

**Checkpoint**: Measure actual compliance gain

### Week 3 (Days 11-15): Validation & Documentation
- **Days 11-12**: Comprehensive testing and validation
- **Days 13-14**: Documentation and review
- **Day 15**: Sprint 010 completion and Sprint 011 planning

---

## Success Metrics

### Quantitative Targets

| Category | Baseline | Target | Gain |
|----------|----------|--------|------|
| **Path Navigation** | 20% (2/10) | 80% (8/10) | +8 tests |
| **Comments/Syntax** | 46.9% (15/32) | 87.5% (28/32) | +17 tests |
| **Arithmetic Operators** | 50% (36/72) | 90% (65/72) | +36 tests |
| **Math Functions** | 96.4% (27/28) | 100% (28/28) | +1 test |
| **String Functions** | 78.5% (51/65) | 89.2% (58/65) | +7 tests |
| **OVERALL** | **64.99% (607/934)** | **72.4% (676/934)** | **+69 tests** |

### Quality Targets
- [ ] Zero regressions (607 tests continue passing)
- [ ] Architecture compliance maintained (thin dialects)
- [ ] Performance maintained (<10ms average)
- [ ] Multi-database compatibility maintained

### Sprint 009 Success Defined As:
- ✅ Achieve 70-75% compliance (target: 72.4%)
- ✅ Complete all 5 refocus tasks
- ✅ Build foundation for Sprint 010
- ✅ Document honest progress

---

## Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Tasks take longer than estimated | Medium | Medium | Prioritize tasks 1-3, defer 4-5 if needed |
| Regressions introduced | Low | High | Comprehensive regression testing after each task |
| Path navigation more complex | Medium | Medium | Focus on common cases, defer edge cases |
| Comment validation ambiguous | Low | Medium | Reference FHIRPath spec closely |

### Schedule Risks
- **Timeline pressure**: 2-3 weeks for 64-76h of work
- **Mitigation**: Focus on tasks 1-3 as minimum viable, tasks 4-5 are polish
- **Fallback**: Achieve 70% instead of 72.4% if timeline tight

---

## Architecture Compliance

**Non-Negotiable Requirements**:
- ✅ Thin Dialect Pattern maintained
- ✅ No business logic in database-specific code
- ✅ Population-first design preserved
- ✅ Multi-database compatibility maintained

**Review Gates**:
- Each task requires senior architect code review
- Architecture compliance verified before merge
- Regression testing mandatory

---

## Testing Protocol

**Correct Test Harness**: `tests/integration/fhirpath/official_test_runner.py`

**Testing Requirements for Each Task**:
1. Run official test runner before changes (baseline)
2. Run official test runner after changes (validation)
3. Document actual test results (not aspirational)
4. Verify zero regressions in other categories
5. Test on both DuckDB and PostgreSQL

**Reporting Standard**:
- Include actual test execution logs
- Report both pass/fail counts and percentages
- Document any unexpected results
- No claims without evidence

---

## Documentation Requirements

### Task-Level Documentation
- [ ] Each task document updated with actual results
- [ ] Implementation notes and challenges documented
- [ ] Test results recorded with evidence
- [ ] Lessons learned captured

### Sprint-Level Documentation
- [ ] Sprint refocus plan (this document)
- [ ] Actual vs. expected progress tracking
- [ ] Compliance measurements with evidence
- [ ] Sprint 009 completion summary

---

## Phase 4 Task Disposition

**ALL Phase 4 tasks (SP-009-022 through SP-009-031) remain DEFERRED to Sprint 010.**

**Rationale**:
- These tasks assume 100% compliance
- Premature at projected 72% compliance
- Better to defer than execute on false premises

**Alternative Consideration**:
- Could execute SP-009-022 (integration testing) with corrected scope
- Focus: Validate 676 passing tests for consistency
- Decision: Defer to Sprint 010 for cleaner sprint boundary

---

## Sprint 010 Planning Implications

**Sprint 010 Starting Point**: ~72% compliance (676/934 tests)

**Sprint 010 Recommended Goals**:
1. **Address Type Functions** (41.4% → 70%) - The critical gap deferred from Option A
2. **Complete Collection Functions** (58.9% → 80%)
3. **Target**: 80-85% compliance by end of Sprint 010

**Sprint 011 Goals** (if needed):
1. **Final push to 100%**
2. **PEP-003 completion**
3. **Comprehensive validation**

---

## Communication Plan

### Daily Updates
- Progress on current task
- Blockers encountered
- Actual test results (with evidence)

### Weekly Reviews
- **End of Week 1**: Review Tasks 1-2 completion
- **End of Week 2**: Review Tasks 3-5 completion
- **End of Week 3**: Sprint 009 completion review

### Milestone Checkpoints
- **70% Compliance Achieved**: Celebrate progress
- **All 5 Tasks Complete**: Validate collective impact
- **Sprint 009 Complete**: Honest assessment and Sprint 010 planning

---

## Accountability

**Junior Developer Responsibilities**:
- Execute tasks 1-5 according to specifications
- Use correct test harness for all validation
- Report actual results (not aspirational)
- Seek help when blocked

**Senior Architect Responsibilities**:
- Review all task implementations
- Verify architecture compliance
- Support junior developer
- Maintain testing protocol discipline

**Shared Commitment**:
- Honest reporting of actual state
- Evidence-based claims
- No pressure to claim success without validation
- Quality over speed

---

## Success Definition

**Sprint 010 is SUCCESSFUL if**:
- ✅ Achieve 70%+ compliance (target 72.4%)
- ✅ Complete minimum 3 of 5 tasks (preferably all 5)
- ✅ Zero regressions introduced
- ✅ Architecture compliance maintained
- ✅ Foundation built for Sprint 011 progress
- ✅ Honest documentation of actual achievements

**Sprint 010 would be OUTSTANDING if**:
- 🌟 Achieve 72-75% compliance
- 🌟 Complete all 5 tasks
- 🌟 Exceed expected test gains
- 🌟 Identify additional quick wins for Sprint 010

---

## Appendices

### Appendix A: Task Dependencies
```
SP-010-001 (Path Nav) → [No dependencies]
SP-010-002 (Comments) → [Independent, can run parallel]
SP-010-003 (Arithmetic) → [Independent, can run parallel]
SP-010-004 (Math) → [Independent, quick win]
SP-010-005 (String) → [Independent]
```

**Recommendation**: Execute in priority order (1→2→3→4→5) for maximum impact sequence.

### Appendix B: Quick Reference

**Current Compliance**: 64.99% (607/934)
**Target Compliance**: 72.4% (676/934)
**Expected Gain**: +69 tests (+7.4%)
**Timeline**: 2-3 weeks
**Tasks**: 5 tasks, 64-76h estimated effort

**Test Runner**: `tests/integration/fhirpath/official_test_runner.py`
**Correction Doc**: `CRITICAL-CORRECTION-SP-009-compliance-reality.md`
**Gap Analysis**: `SP-010-critical-gap-prioritization.md`

---

**Plan Created**: 2025-10-17 by Senior Solution Architect/Engineer
**Plan Status**: Approved for Execution
**Next Action**: Begin SP-010-001 (Fix Path Navigation Basics)

---

*This refocus plan provides a realistic, achievable path to meaningful compliance improvement in Sprint 009, building foundation for continued progress in Sprint 010.*
