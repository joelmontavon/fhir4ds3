# FHIRPath Compliance Roadmap - Corrected

**Date**: 2025-12-05 (Evening)
**Status**: Active
**Current Compliance**: 452/934 tests (48.4%)
**Target**: 55-60% compliance

---

## Executive Summary

This roadmap replaces the original roadmap which included the invalid SP-021-015 task.

### Changes from Original
- ❌ Removed SP-021-015 (parser double-quote support) - NOT A BUG
- ✅ Kept 3 valid tasks with evidence-based impact estimates
- ✅ More conservative compliance targets based on actual bugs

### Key Finding
**FHIRPath specification ONLY supports single-quoted strings.** Our parser correctly rejects double quotes. The SP-021-015 task was based on a false premise and has been deleted. See `CORRECTION-SP-021-015-INVALID.md` for details.

---

## Current Status (Baseline)

**Date**: 2025-12-05 (After REGEXP fix)
**Total Tests**: 934
**Passing**: 452 (48.4%)
**Failing**: 482 (51.6%)

### Recent Accomplishments ✅
1. Fixed REGEXP syntax bug → +4 tests
2. Added error visibility → Can see actual errors now
3. Replaced test fixtures → Using official HL7 data
4. Validated architecture → No fundamental issues

### Category Breakdown
| Category | Passing | Total | Percentage |
|----------|---------|-------|------------|
| Type_Functions | 37/116 | 31.9% | ⚠️ Low |
| Path_Navigation | 9/10 | 90.0% | ✅ Good |
| String_Functions | 46/65 | 70.8% | ✅ Good |
| Math_Functions | 22/28 | 78.6% | ✅ Good |
| DateTime_Functions | 0/6 | 0.0% | ❌ Failing |
| Polymorphism | 9/10 | 90.0% | ✅ Good |

---

## Identified Issues (Evidence-Based)

### Issue #1: Partial Timestamp Conversion ⚠️
**Evidence**:
```
Error: ConversionException: invalid timestamp field format: "2015-02-04 14"
Expression: @2015-02-04T14.is(DateTime)
```

**Root Cause**: DuckDB requires full TIMESTAMP format, but FHIRPath allows partial precision.

**Impact Estimate**: ~10-20 tests
**Priority**: MEDIUM
**Task**: SP-021-016

---

### Issue #2: DateTime Type Check Logic ⚠️
**Evidence**:
```
Expression: @2015-02-04T14:34:28.is(DateTime)
Expected: true
Actual: false
```

**Root Cause**: Regex pattern or type check logic incorrect (REGEXP syntax is now fixed, but logic still wrong).

**Impact Estimate**: ~20-30 tests
**Priority**: MEDIUM
**Task**: SP-021-017

---

### Issue #3: Date Comparison Type Mismatch ⚠️
**Evidence**:
```
Error: BinderException: Cannot compare TIMESTAMP WITH TIME ZONE and VARCHAR
Expression: now() > Patient.birthDate
```

**Root Cause**: JSON extraction returns VARCHAR, needs explicit cast to TIMESTAMP for comparison.

**Impact Estimate**: ~15-25 tests
**Priority**: MEDIUM
**Task**: SP-021-018

---

## Roadmap Phases

### Phase 1: Fix DateTime Type Check Logic (SP-021-017)
**Objective**: Make `.is(DateTime)` return correct results

**Estimated Effort**: 8-16 hours
**Expected Impact**: +20-30 tests
**Target Compliance**: 472-482/934 (50.5-51.6%)

**Why First**:
- Clear root cause identified
- Localized fix (regex pattern)
- Unblocks other datetime tests

**Deliverables**:
- [ ] Fix regex pattern for DateTime type matching
- [ ] Unit tests for type checking
- [ ] Compliance verification
- [ ] Both DuckDB and PostgreSQL working

---

### Phase 2: Fix Partial Timestamp Conversion (SP-021-016)
**Objective**: Support FHIRPath partial precision timestamps

**Estimated Effort**: 8-16 hours
**Expected Impact**: +10-20 tests
**Target Compliance**: 482-502/934 (51.6-53.7%)

**Why Second**:
- Builds on type check fixes
- More complex than type checking
- Affects datetime literal handling

**Deliverables**:
- [ ] Detect timestamp precision levels
- [ ] Pad or handle partial timestamps
- [ ] Unit tests for all precision levels
- [ ] Compliance verification

---

### Phase 3: Fix Date Comparison Casting (SP-021-018)
**Objective**: Add automatic type casting for temporal comparisons

**Estimated Effort**: 4-8 hours
**Expected Impact**: +15-25 tests
**Target Compliance**: 497-527/934 (53.2-56.4%)

**Why Third**:
- Benefits from prior datetime fixes
- Clearer to implement after understanding datetime handling
- Smaller effort estimate

**Deliverables**:
- [ ] Type detection for comparison operands
- [ ] Automatic casting logic
- [ ] Unit tests for various comparisons
- [ ] Compliance verification

---

## Revised Compliance Targets

### Conservative Estimate
```
Current:  452/934 (48.4%)
+ Phase 1: +20 tests → 472/934 (50.5%)
+ Phase 2: +10 tests → 482/934 (51.6%)
+ Phase 3: +15 tests → 497/934 (53.2%)

Total gain: +45 tests
Final: 53.2% compliance
```

### Optimistic Estimate
```
Current:  452/934 (48.4%)
+ Phase 1: +30 tests → 482/934 (51.6%)
+ Phase 2: +20 tests → 502/934 (53.7%)
+ Phase 3: +25 tests → 527/934 (56.4%)

Total gain: +75 tests
Final: 56.4% compliance
```

### Target Range
**Realistic Target**: **53-56% compliance** (497-527 tests passing)

**Timeline**: 20-40 hours total effort across all phases

---

## Success Metrics

### Phase Completion Criteria
Each phase must achieve:
- [ ] All unit tests passing
- [ ] Minimum impact threshold met (conservative estimate)
- [ ] No regressions in existing tests
- [ ] Both DuckDB and PostgreSQL working
- [ ] Code review approved

### Overall Success Criteria
- [ ] Reach 53% compliance minimum (497/934 tests)
- [ ] All 3 identified issues resolved
- [ ] Architecture remains sound
- [ ] Both dialects maintained

---

## What Changed from Original Roadmap

### Original Roadmap (INVALID)
```
Phase 1: Parser Quote Fix (SP-021-015) → +50-100 tests
Phase 2: DateTime Conversion → +30-50 tests
Phase 3: Type Check Logic → +20-40 tests
Phase 4: Comparison Casting → +15-25 tests
Target: 65-70% compliance
```

### Corrected Roadmap
```
Phase 1: DateTime Type Check (SP-021-017) → +20-30 tests
Phase 2: Partial Timestamps (SP-021-016) → +10-20 tests
Phase 3: Comparison Casting (SP-021-018) → +15-25 tests
Target: 53-56% compliance
```

### Key Differences
1. ❌ Removed SP-021-015 (-50-100 fake tests)
2. ✅ Reordered phases by dependency and impact
3. ✅ More conservative estimates based on actual evidence
4. ✅ Lower but realistic compliance target (53-56% vs 65-70%)

---

## Risk Assessment

### Technical Risks

**LOW**: All issues have clear root causes
- ✅ Error visibility now shows actual problems
- ✅ Evidence from official compliance tests
- ✅ No architecture rework needed

**MEDIUM**: Impact estimates may be off
- **Mitigation**: Conservative estimates used
- **Mitigation**: Each phase can be reassessed
- **Mitigation**: No commitment to specific numbers

### Process Risks

**LOW**: Lessons learned from SP-021-015 error
- ✅ Always verify specification claims
- ✅ Test actual official test cases
- ✅ Junior developer review process
- ✅ More careful with estimates

---

## Dependencies

### Phase Dependencies
- Phase 2 (partial timestamps) slightly easier after Phase 1 (type checks)
- Phase 3 (comparison casting) benefits from Phase 1 & 2 insights
- But all phases CAN be done independently if needed

### External Dependencies
- None - all issues are in our codebase
- Official test suite provides validation
- Both databases (DuckDB, PostgreSQL) available for testing

---

## Long-Term Considerations

### Beyond 56% Compliance

After completing these 3 phases, need to investigate:
1. **String function compliance** - Some failing despite 70.8% pass rate
2. **Remaining type function failures** - Even after fixes, ~50 tests may still fail
3. **Collection operations** - Need deeper investigation
4. **Arithmetic operations** - Check for similar type casting issues

### Architecture Validation

After each phase:
- [ ] Verify no architecture violations
- [ ] Check both dialects remain thin (syntax only, no business logic)
- [ ] Ensure CTE-first design maintained
- [ ] Validate performance not degraded

---

## Task Documentation

### Created Tasks (Ready to Start)
1. **SP-021-016**: Fix Partial Timestamp Conversion
   - File: `project-docs/plans/tasks/SP-021-016-fix-partial-timestamp-conversion.md`
   - Comprehensive implementation plan with 4 phases
   - Unit test examples included

2. **SP-021-017**: Fix DateTime Type Check Logic
   - File: `project-docs/plans/tasks/SP-021-017-fix-datetime-type-check.md`
   - Investigation + design + implementation + testing
   - Detailed regex pattern analysis

3. **SP-021-018**: Fix Date Comparison Type Casting
   - File: `project-docs/plans/tasks/SP-021-018-fix-date-comparison-casting.md`
   - Type detection + casting rules
   - Multi-database support design

### Deleted Tasks
1. ~~**SP-021-015**: Fix Parser Double Quote Support~~ ❌ DELETED
   - Reason: FHIRPath spec only supports single quotes
   - Parser behavior is CORRECT
   - See: `CORRECTION-SP-021-015-INVALID.md`

---

## Next Steps

### Immediate Actions
1. **Review this roadmap** - Validate approach and estimates
2. **Assign Phase 1** - Start with SP-021-017 (DateTime type check)
3. **Set up tracking** - Create progress dashboard if needed

### Phase 1 Kickoff (SP-021-017)
When ready to start:
1. Read task document: `SP-021-017-fix-datetime-type-check.md`
2. Begin with investigation phase
3. Report findings before implementation
4. Execute stepwise with testing at each step

---

## Lessons Learned

### From SP-021-015 Error
1. ✅ **Always verify specifications** - Don't assume, verify with official docs
2. ✅ **Check actual test data** - See what tests actually use, not what we think
3. ✅ **Junior developer review valuable** - Fresh eyes catch errors
4. ✅ **Conservative estimates better** - Over-promising leads to disappointment
5. ✅ **Evidence-based planning** - Base estimates on actual error logs, not theory

### Process Improvements
- **Before creating tasks**: Verify claims against official specifications
- **Before estimating impact**: Analyze actual failing tests, not assumed patterns
- **Before implementing**: Have another developer review the approach
- **After fixing**: Document actual results vs estimates for calibration

---

## Success Definition

### Minimum Success (Must Achieve)
- ✅ Reach 53% compliance (497/934 tests passing)
- ✅ All 3 identified issues resolved
- ✅ No architecture violations
- ✅ Both databases working

### Target Success (Ideal)
- ✅ Reach 56% compliance (527/934 tests passing)
- ✅ All tasks complete with optimistic estimates met
- ✅ Confidence in remaining issues identified
- ✅ Clear path to 60%+ compliance documented

### Stretch Success (Bonus)
- ✅ Exceed 56% compliance
- ✅ Identify and fix additional issues discovered during work
- ✅ Improve development process and estimation accuracy

---

**Prepared by**: Senior Solution Architect/Engineer
**Date**: 2025-12-05
**Status**: Active - Ready for Phase 1
**Replaces**: Original roadmap with invalid SP-021-015
**Next**: Assign SP-021-017 and begin Phase 1
