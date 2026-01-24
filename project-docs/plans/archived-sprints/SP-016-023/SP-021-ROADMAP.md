# SP-021 Compliance Improvement Roadmap

**Created**: 2025-11-28
**Status**: Active
**Current Baseline**: 404/934 tests passing (43.3% compliance)
**Target**: 519-584/934 tests passing (55.5-62.5% compliance)
**Potential Improvement**: +115-180 tests

---

## Overview

This roadmap documents the systematic approach to improving FHIRPath compliance based on empirical investigation of test failures from SP-021-001. Rather than theoretical projections, these tasks are based on actual test failure analysis.

### Completed Tasks

| Task | Description | Expected Impact | Actual Impact | Status |
|------|-------------|-----------------|---------------|--------|
| SP-021 | FHIR Primitive Extraction (scalar) | +160-250 tests | +8 tests | ✅ Merged |
| SP-021-001 | FHIR Primitive Extraction (arrays) | +146-246 tests | +0 tests | ✅ Merged |

**Key Insight**: Both primitive extraction tasks showed minimal compliance impact because the official test suite uses simple primitives without extensions. However, both provide **production value** for real-world FHIR data.

---

## Pending Tasks (Prioritized by Investigation)

### SP-021-002: Variable Binding ⭐ **PRIORITY 1**

**Status**: Not Started
**Task File**: `SP-021-002-variable-binding-implementation.md`

**Description**: Implement `$this`, `$index`, and `$total` variable binding for lambda expressions (where, select, all, exists, etc.)

**Current Failures**: ~50 tests fail with "Unbound FHIRPath variable referenced"

**Impact Projection**:
- **Estimated Improvement**: +30-50 tests
- **Target Compliance**: 434-454/934 (46-49%)
- **Estimated Effort**: 18-26 hours
- **Confidence**: Medium (70-89%)

**Example Failing Tests**:
```
Patient.name.given.where($this.startsWith('J'))
  → Error: Unbound FHIRPath variable referenced: $this
```

**Implementation Complexity**: Medium
- Stack-based lambda context management
- SQL generation with ROW_NUMBER() for $index
- Multi-function support (where, select, all, exists)

**Recommendation**: **Start here** - Highest priority, unblocks many other tests

---

### SP-021-003: Operator Implementation ⭐ **PRIORITY 2**

**Status**: Not Started
**Task File**: `SP-021-003-operator-implementation.md`

**Description**: Implement missing unary operators and fix operator parameter handling

**Current Failures**: ~20 tests fail with "Unknown unary operator" errors

**Impact Projection**:
- **Estimated Improvement**: +15-20 tests
- **Target Compliance**: 419-424/934 (45-45.4%)
- **Estimated Effort**: 10-14 hours
- **Confidence**: High (90%+)

**Example Failing Tests**:
```
-5  → Error: Unknown unary operator: -
```

**Implementation Complexity**: Low
- Parser updates for unary operators
- Translator extensions
- Parameter validation improvements

**Recommendation**: Good follow-up to SP-021-002, relatively straightforward

---

### SP-021-004: Polymorphism Support ⭐ **PRIORITY 3**

**Status**: Not Started
**Task File**: `SP-021-004-polymorphism-support.md`

**Description**: Implement polymorphic field navigation for FHIR choice[x] pattern (e.g., Observation.value → valueString | valueInteger | etc.)

**Current Failures**: ~30 tests fail with "Field 'value' not found" errors

**Impact Projection**:
- **Estimated Improvement**: +20-30 tests
- **Target Compliance**: 424-434/934 (45.4-46.5%)
- **Estimated Effort**: 14-18 hours
- **Confidence**: Medium (70-89%)

**Example Failing Tests**:
```
Observation.value  → Error: Field 'value' not found in Observation
  (Should resolve to valueString, valueInteger, valueQuantity, etc.)
```

**Implementation Complexity**: Medium-High
- TypeRegistry integration for polymorphic field detection
- SQL COALESCE patterns for multiple field variants
- StructureDefinition metadata usage

**Recommendation**: Implement after SP-021-002 and SP-021-003

---

### SP-021-005: Type Functions ⭐⭐ **HIGHEST IMPACT**

**Status**: Not Started
**Task File**: `SP-021-005-type-functions-implementation.md`

**Description**: Implement type checking and casting functions: `is(type)`, `as(type)`, `ofType(type)`

**Current Failures**: ~80 tests fail with "Function not implemented" errors

**Impact Projection**:
- **Estimated Improvement**: +50-80 tests (🎯 **Largest single improvement**)
- **Target Compliance**: 454-484/934 (48.6-51.8%) (**50% milestone possible**)
- **Estimated Effort**: 23-31 hours
- **Confidence**: Medium (70-89%)

**Example Failing Tests**:
```
value.is(String)           → Error: Function 'is' not implemented
value.as(Integer)          → Error: Function 'as' not implemented
resources.ofType(Patient)  → Error: Function 'ofType' not implemented
```

**Implementation Complexity**: High
- FHIR type system integration
- TypeRegistry extensions
- SQL type detection (JSON type checking)
- Resource type filtering

**Recommendation**:
- **Highest numeric impact** (potential to reach 50% compliance)
- Implement after SP-021-002 (many tests use type functions with lambda variables)
- Consider prioritizing despite being "Priority 4" in investigation

---

## Cumulative Impact Projection

### Conservative Estimate (Lower Bound)

| Milestone | Tasks Completed | Tests Passing | Compliance % | Improvement |
|-----------|----------------|---------------|--------------|-------------|
| **Baseline** | SP-021, SP-021-001 | 404/934 | 43.3% | - |
| **Milestone 1** | + SP-021-002 | 434/934 | 46.5% | +30 |
| **Milestone 2** | + SP-021-003 | 449/934 | 48.1% | +15 |
| **Milestone 3** | + SP-021-004 | 469/934 | 50.2% | +20 |
| **Milestone 4** | + SP-021-005 | 519/934 | 55.5% | +50 |

**Total Conservative Impact**: +115 tests (+12.2 percentage points)

### Optimistic Estimate (Upper Bound)

| Milestone | Tasks Completed | Tests Passing | Compliance % | Improvement |
|-----------|----------------|---------------|--------------|-------------|
| **Baseline** | SP-021, SP-021-001 | 404/934 | 43.3% | - |
| **Milestone 1** | + SP-021-002 | 454/934 | 48.6% | +50 |
| **Milestone 2** | + SP-021-003 | 474/934 | 50.7% | +20 |
| **Milestone 3** | + SP-021-004 | 504/934 | 54.0% | +30 |
| **Milestone 4** | + SP-021-005 | 584/934 | 62.5% | +80 |

**Total Optimistic Impact**: +180 tests (+19.2 percentage points)

---

## Recommended Implementation Order

### Option A: Priority Order (As Investigated)

**Order**: SP-021-002 → SP-021-003 → SP-021-004 → SP-021-005

**Rationale**:
- Follows investigation priority
- Builds foundation with variables first
- Incremental complexity increase

**Timeline**: ~65-89 hours total

**Pros**:
- Systematic approach
- Variables enable other features
- Lower risk

**Cons**:
- Highest impact (type functions) comes last
- Longer time to reach 50% milestone

### Option B: Impact Order (Maximize Results)

**Order**: SP-021-005 → SP-021-002 → SP-021-004 → SP-021-003

**Rationale**:
- Tackle highest-impact task first
- Reach 50% compliance faster
- Build momentum with visible wins

**Timeline**: ~65-89 hours total (same)

**Pros**:
- Fastest path to 50% compliance
- Highest visibility improvement first
- Strong morale boost

**Cons**:
- Higher complexity upfront
- Some type function tests may need variables (SP-021-002)
- More dependencies to manage

### Option C: Hybrid Approach (Balanced) ⭐ **RECOMMENDED**

**Order**: SP-021-002 → SP-021-005 → SP-021-004 → SP-021-003

**Rationale**:
- Variables first (unblocks many tests)
- Type functions second (highest remaining impact)
- Polymorphism third (complements type functions)
- Operators last (lowest complexity, good cleanup task)

**Timeline**: ~65-89 hours total (same)

**Pros**:
- Balanced complexity curve
- Variables enable type function tests
- Reaches 50% compliance by task 2
- Good progression for learning

**Cons**:
- None significant

**Milestones with Hybrid Approach**:
1. After SP-021-002: 434-454/934 (46-49%) - Variables working
2. After SP-021-005: 484-534/934 (52-57%) - **50% milestone achieved!** 🎯
3. After SP-021-004: 504-564/934 (54-60%) - Polymorphism working
4. After SP-021-003: 519-584/934 (56-63%) - All operators working

---

## Risk Assessment

### Task-Level Risks

| Task | Complexity | Uncertainty | Database Compatibility | Overall Risk |
|------|-----------|-------------|------------------------|--------------|
| SP-021-002 | Medium | Medium | Medium | **Medium** |
| SP-021-003 | Low | Low | Low | **Low** |
| SP-021-004 | High | Medium | Medium | **Medium-High** |
| SP-021-005 | High | High | Medium | **High** |

### Project-Level Risks

1. **Estimation Accuracy (Medium Risk)**
   - Impact projections based on test failure analysis
   - Some tests may fail for multiple reasons (fixing one may not pass the test)
   - Mitigation: Conservative estimates provided

2. **Task Dependencies (Low-Medium Risk)**
   - Some tests use multiple features (e.g., variables + type functions)
   - May need multiple tasks complete to pass certain tests
   - Mitigation: Hybrid implementation order addresses dependencies

3. **Database Compatibility (Low Risk)**
   - All tasks require DuckDB + PostgreSQL support
   - Thin dialect architecture reduces risk
   - Mitigation: Thorough multi-database testing

4. **FHIR Type System Complexity (Medium Risk)**
   - SP-021-004 and SP-021-005 require deep FHIR type understanding
   - TypeRegistry may need extensions
   - Mitigation: Leverage existing StructureDefinition infrastructure

---

## Success Metrics

### Quantitative Targets

| Metric | Conservative | Optimistic | Stretch Goal |
|--------|--------------|------------|--------------|
| **Final Compliance** | 519/934 (55.5%) | 584/934 (62.5%) | 650+/934 (70%+) |
| **Tests Improved** | +115 | +180 | +246+ |
| **Zero Regressions** | Required | Required | Required |

### Qualitative Goals

- ✅ **Architecture Integrity**: All tasks maintain thin dialect architecture
- ✅ **Code Quality**: All code meets coding standards
- ✅ **Documentation**: Comprehensive documentation for all features
- ✅ **Production Value**: Features work with real-world FHIR data

---

## Lessons from SP-021 and SP-021-001

### What We Learned

1. **Test Suite vs. Production Data**
   - Official tests may not exercise all real-world scenarios
   - Primitive extraction provides production value despite +0 test improvement

2. **Empirical Validation Essential**
   - Theoretical projections can be wrong
   - SP-021: Expected +160-250, actual +8
   - SP-021-001: Expected +146-246, actual +0
   - Investigation-based projections (SP-021-002 through 005) more reliable

3. **Root Cause Analysis Needs Validation**
   - Examine actual test failures, not just theoretical causes
   - Multiple root causes may block single test
   - Priority by actual failure frequency, not theoretical importance

4. **Architectural Correctness Still Matters**
   - Even with +0 compliance impact, implementations can provide value
   - Production FHIR data differs from test suite data
   - Future-proofing has strategic value

### How These Tasks Are Different

1. **Based on Actual Test Failures**: Examined compliance test output to identify exact errors
2. **Frequency-Based Prioritization**: Counted how many tests fail for each reason
3. **Conservative Estimates**: Learned from SP-021/SP-021-001 to be more conservative
4. **Clear Dependencies**: Identified which features depend on others
5. **Validated Approach**: Investigation findings peer-reviewed and approved

---

## Timeline Estimates

### Full Roadmap (All 4 Tasks)

- **Conservative**: 65 hours (~8.1 work days, ~2 weeks with context switching)
- **Optimistic**: 89 hours (~11.1 work days, ~2.5 weeks with context switching)
- **Realistic**: 75 hours (~9.4 work days, ~2 weeks with context switching)

### By Task

| Task | Effort Range | % of Total |
|------|--------------|------------|
| SP-021-002 | 18-26 hours | 28-29% |
| SP-021-003 | 10-14 hours | 15-16% |
| SP-021-004 | 14-18 hours | 22% |
| SP-021-005 | 23-31 hours | 35% |

### Sprint Planning Recommendations

**Option 1: Single Sprint (Aggressive)**
- All 4 tasks in one sprint
- Requires ~75 hours of focused development
- High risk, high reward
- Recommended only if dedicated resource available

**Option 2: Two Sprints (Balanced)** ⭐ **RECOMMENDED**
- **Sprint 1**: SP-021-002 + SP-021-003 (28-40 hours)
  - Achieves 449-474/934 (48-51%)
  - Reaches 50% milestone
  - Lower complexity tasks

- **Sprint 2**: SP-021-004 + SP-021-005 (37-49 hours)
  - Achieves 519-584/934 (56-63%)
  - Higher complexity tasks
  - Time to learn from Sprint 1

**Option 3: Four Sprints (Conservative)**
- One task per sprint
- Lowest risk approach
- Longest timeline (~8-10 weeks)
- Good for learning/junior developers

---

## Next Steps

### Immediate Actions

1. **Review and Approve Roadmap**: Senior architect approval
2. **Select Implementation Order**: Choose Option A, B, or C (recommend C)
3. **Assign First Task**: Assign SP-021-002 to developer
4. **Set Sprint Goals**: Define sprint boundaries and milestones

### Before Starting Each Task

1. Review task documentation
2. Study relevant FHIRPath specification sections
3. Examine actual test failures for that category
4. Create small proof-of-concept if needed
5. Confirm multi-database testing approach

### After Completing Each Task

1. Run full compliance test suite
2. Validate actual vs. projected improvement
3. Document lessons learned
4. Update roadmap projections if needed
5. Conduct senior review before merge

---

## References

- **SP-021-001 Investigation**: `work/SP-021-001-INVESTIGATION-FINDINGS.md`
- **SP-021-001 Review**: `project-docs/plans/reviews/SP-021-001-review.md`
- **FHIRPath Specification**: http://hl7.org/fhirpath/
- **Architecture Guide**: `CLAUDE.md`
- **Coding Standards**: `project-docs/process/coding-standards.md`

---

## Summary

This roadmap provides a **data-driven, empirically validated approach** to improving FHIRPath compliance from 43.3% to 55.5-62.5%. Unlike earlier projections, these estimates are based on actual test failure analysis and account for lessons learned from SP-021 and SP-021-001.

**Key Insight**: While primitive extraction tasks showed minimal compliance impact, the investigation revealed the actual blockers: variable binding, operators, polymorphism, and type functions. Addressing these systematically has the potential to increase compliance by 12-19 percentage points.

**Recommended Path**: Hybrid implementation order (SP-021-002 → SP-021-005 → SP-021-004 → SP-021-003) across two sprints, reaching the 50% compliance milestone after completing just the first two tasks.

---

**Roadmap Created**: 2025-11-28
**Status**: Active
**Next Task**: SP-021-002 (Variable Binding)
**Target Milestone**: 50% compliance (after SP-021-002 + SP-021-005)
