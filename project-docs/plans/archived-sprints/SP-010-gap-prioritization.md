# Sprint 010: Critical Gap Prioritization

**Document Type**: Sprint Refocus Plan
**Date**: 2025-10-17
**Context**: Correction of false 100% compliance claims - Actual 64.99%
**See**: `CRITICAL-CORRECTION-SP-009-compliance-reality.md` for background

---

## Situation

**Actual Compliance**: 64.99% (607/934 tests passing)
**Gap**: 327 failing tests (35% of specification)
**Sprint Time Remaining**: ~2-3 weeks (assuming 3-week sprint duration)

**Critical Decision**: What should we focus on for the remainder of Sprint 009?

---

## Gap Analysis by Priority

### Tier 1: CRITICAL BLOCKERS (Fix First)

These gaps prevent basic FHIRPath functionality and block large numbers of tests:

#### 1. Path Navigation - 80% Failing (2/10 passing)
**Impact**: CRITICAL - Basic FHIRPath functionality
**Failing Tests**: 8 tests
**Root Causes**:
- Escaped identifiers not working (`` `given` ``)
- Context validation failures
- Basic path traversal issues

**Example Failures**:
- `testPatientHasBirthDate`: `birthDate` - "Unexpected evaluation outcome"
- `testSimple`: `name.given` - "Unexpected evaluation outcome"
- `testEscapedIdentifier`: `` name.`given` `` - "Unexpected evaluation outcome"

**Recommended Action**: HIGH PRIORITY FIX
- **Estimated Effort**: 1-2 days
- **Impact**: Foundational - unblocks other features
- **Expected Gain**: +8 tests (+0.9%)

---

#### 2. Type Functions - 58.6% Failing (48/116 passing)
**Impact**: CRITICAL - Type system functionality
**Failing Tests**: 68 tests
**Root Causes**:
- `InvocationTerm` node type not handled
- Type casting issues (`as Quantity`, `as Period`)
- Type validation failures

**Example Failures**:
- `testPolymorphismA`: `Observation.value.unit` - "Unexpected evaluation outcome"
- `testPolymorphismB`: `Observation.valueQuantity.unit` - "Expected semantic failure"
- Unknown FHIRPath type errors for `Quantity`, `Period`

**Recommended Action**: HIGH PRIORITY FIX
- **Estimated Effort**: 3-4 days
- **Impact**: Major - enables polymorphic types
- **Expected Gain**: +68 tests (+7.3%)

---

### Tier 2: HIGH-VALUE IMPROVEMENTS

These gaps affect significant functionality but have workarounds:

#### 3. Collection Functions - 41.1% Failing (83/141 passing)
**Impact**: HIGH - Common FHIRPath operations
**Failing Tests**: 58 tests
**Root Causes**:
- Missing functions: `children()`, `descendants()`, `last()`
- Missing set operations: `distinct()`, `union()`, `intersect()`
- Missing aggregations: `aggregate()`, `sort()`

**Recommended Action**: MEDIUM PRIORITY
- **Estimated Effort**: 4-5 days
- **Impact**: High - common operations
- **Expected Gain**: +58 tests (+6.2%)

---

#### 4. Comments/Syntax - 53.1% Failing (15/32 passing)
**Impact**: MEDIUM - Edge case handling
**Failing Tests**: 17 tests
**Root Causes**:
- Incomplete comment validation
- Multi-line comment edge cases
- Semantic validation gaps

**Example Failures**:
- `testComment8`: `2 + 2 /* not finished` - "Expected semantic failure"

**Recommended Action**: MEDIUM PRIORITY
- **Estimated Effort**: 2-3 days
- **Impact**: Medium - improves robustness
- **Expected Gain**: +17 tests (+1.8%)

---

#### 5. Arithmetic Operators - 50% Failing (36/72 passing)
**Impact**: MEDIUM - Math operations
**Failing Tests**: 36 tests
**Root Causes**:
- Unary operator issues (`+x`, `-x`)
- Division edge cases
- Type coercion failures

**Recommended Action**: MEDIUM PRIORITY
- **Estimated Effort**: 2-3 days
- **Impact**: Medium - math robustness
- **Expected Gain**: +36 tests (+3.9%)

---

### Tier 3: NICE-TO-HAVE IMPROVEMENTS

These gaps affect less common functionality:

#### 6. Function Calls - 36.3% Failing (72/113 passing)
**Impact**: MEDIUM - Various functions
**Failing Tests**: 41 tests
**Includes conversion functions, string functions, etc.**

**Recommended Action**: LOWER PRIORITY
- **Estimated Effort**: 3-4 days
- **Impact**: Medium - incremental improvements
- **Expected Gain**: +41 tests (+4.4%)

---

#### 7. Comparison Operators - 23.1% Failing (260/338 passing)
**Impact**: LOW - Already 77% passing
**Failing Tests**: 78 tests
**Status**: Good baseline, edge cases remaining

**Recommended Action**: POLISH LATER
- **Estimated Effort**: 2-3 days
- **Impact**: Polish - already functional
- **Expected Gain**: +78 tests (+8.3%)

---

### Tier 4: STRENGTHS (Maintain)

These categories are already excellent:

- ✅ **Math Functions**: 96.4% (27/28) - 1 test from perfect
- ✅ **Datetime Functions**: 100% (6/6) - Complete
- ✅ **String Functions**: 78.5% (51/65) - Good baseline

---

## Recommended Sprint 010 Strategy

### Option A: Address Critical Blockers (RECOMMENDED)

**Focus**: Fix Tier 1 issues (Path Navigation + Type Functions)

**Tasks**:
1. **Fix Path Navigation** (1-2 days)
   - Implement escaped identifier handling
   - Fix context validation
   - Basic path traversal fixes
   - **Target**: 8/10 passing (80%)

2. **Fix InvocationTerm Handling** (3-4 days)
   - Implement `InvocationTerm` node type
   - Add type casting support (Quantity, Period, etc.)
   - Fix polymorphic type handling
   - **Target**: 80/116 passing (69%)

**Expected Outcome**:
- Starting: 607/934 (64.99%)
- After fixes: ~683/934 (73.1%)
- **Net Gain**: +76 tests (+8.1%)

**Sprint 009 Completion Criteria** (Revised):
- ✅ Critical blockers resolved (Path Nav, Type Functions)
- ✅ Compliance: 70-75% achieved
- ✅ Foundation laid for Sprint 010 to reach 85-90%
- ❌ PEP-003 completion: Deferred to Sprint 010
- ❌ 100% compliance: Target for Sprint 010-011

---

### Option B: Broader Coverage (Alternative)

**Focus**: Fix multiple medium-impact areas

**Tasks**:
1. Fix Path Navigation (1-2 days) → +8 tests
2. Fix Comments/Syntax (2-3 days) → +17 tests
3. Fix Arithmetic Operators (2-3 days) → +36 tests
4. Polish Math Functions (0.5 days) → +1 test
5. Improve String Functions (1-2 days) → +7 tests

**Expected Outcome**:
- Starting: 607/934 (64.99%)
- After fixes: ~676/934 (72.4%)
- **Net Gain**: +69 tests (+7.4%)

**Trade-off**: More breadth, but leaves Type Functions critical gap unresolved.

---

### Option C: Category Excellence (Alternative)

**Focus**: Bring strong categories to 100%, ignore weak areas temporarily

**Tasks**:
1. Complete Math Functions (0.5 days) → 28/28 (100%)
2. Complete String Functions (2-3 days) → 65/65 (100%)
3. Improve Comparison Operators (2-3 days) → 300/338 (89%)

**Expected Outcome**:
- Starting: 607/934 (64.99%)
- After fixes: ~652/934 (69.8%)
- **Net Gain**: +45 tests (+4.8%)

**Trade-off**: Polish existing strengths but doesn't address critical gaps.

---

## Recommendation: OPTION A

**Rationale**:
1. **Addresses Root Causes**: Path Navigation and Type Functions are foundational
2. **Unblocks Future Work**: These fixes enable other features
3. **Maximum Impact**: 8.1% improvement focused on critical areas
4. **Sustainable Progress**: Builds solid foundation for Sprint 010

**Sprint 009 Revised Success Definition**:
- ✅ Achieve 70-75% compliance (from 65%)
- ✅ Resolve critical Path Navigation blockers
- ✅ Resolve critical Type Function gaps
- ✅ Maintain architecture compliance
- ✅ Document honest progress for Sprint 010 planning

---

## Phase 4 Task Disposition

**ALL Phase 4 tasks (SP-009-022 through SP-009-031) DEFERRED to Sprint 010.**

**Rationale**:
- These tasks assume 100% compliance achievement
- Premature at 65-75% compliance
- Would create false documentation
- Better to defer than to execute based on false premises

**Deferred Tasks**:
- SP-009-022: Comprehensive integration testing
- SP-009-023: Healthcare coverage validation
- SP-009-024: Multi-database consistency validation
- SP-009-025: Performance benchmarking
- SP-009-026: Official test suite final execution
- SP-009-027: PEP-003 implementation summary
- SP-009-028: Move PEP-003 to implemented/
- SP-009-029: Architecture documentation updates
- SP-009-030: Sprint 009 completion documentation
- SP-009-031: PEP-004 preparation

**Alternative**: Execute SP-009-022 with corrected scope:
- Validate 607 passing tests for multi-database consistency
- Performance benchmark passing tests
- Architecture compliance verification
- Document actual state honestly

---

## Sprint 010 Planning Implications

With Sprint 009 ending at ~70-75% compliance, Sprint 010 should target:

**Sprint 010 Goals**:
1. **Complete Collection Functions** (+58 tests → 78%)
2. **Address remaining Type Functions** (if any)
3. **Complete Arithmetic Operators** (+36 tests → 82%)
4. **Address remaining gaps** (target 85-90%)

**Sprint 011 Goals** (if needed):
1. **Final push to 100%** (remaining 10-15%)
2. **PEP-003 completion** (when actual 100% achieved)
3. **Comprehensive validation and documentation**

---

## Next Steps (Immediate)

### For Junior Developer:
1. ✅ Review this refocus plan
2. ✅ Propose specific tasks for Option A approach
3. ✅ Create SP-009-NEW-001: Fix Path Navigation basics
4. ✅ Create SP-009-NEW-002: Implement InvocationTerm handling
5. ✅ Estimate effort and create task breakdown

### For Senior Architect:
1. ✅ Review and approve refocus plan
2. ✅ Support junior dev with task creation
3. ✅ Establish improved testing protocol
4. ✅ Update milestone tracking with realistic targets

---

## Metrics for Success

**Sprint 009 Completion Metrics** (Revised):

| Metric | Target | Stretch Goal |
|--------|--------|--------------|
| **Compliance %** | 70-75% | 75-78% |
| **Tests Passing** | 654-701 | 701-730 |
| **Path Navigation** | 80%+ (8/10) | 100% (10/10) |
| **Type Functions** | 69%+ (80/116) | 75%+ (87/116) |
| **Architecture Compliance** | 100% | 100% |

**Sprint 009 Success = Achieving revised targets above.**

---

## Conclusion

Sprint 009 should refocus on:
1. **Honest assessment** of current 65% compliance state ✅
2. **Critical gap resolution** (Path Nav + Type Functions)
3. **Realistic progress** toward 70-75% compliance
4. **Foundation building** for Sprint 010 to continue progress

**PEP-003 completion and 100% compliance remain important goals - but deferred to Sprint 010-011 when actually achievable.**

---

**Document Owner**: Senior Solution Architect/Engineer
**Approval Status**: Pending Junior Developer + Senior Architect agreement
**Implementation**: Upon approval, create new task breakdown

---

*This refocus plan establishes realistic, achievable goals based on actual compliance data rather than aspirational targets.*
