# Sprint SP-102: FHIRPath 100% Compliance

**Created:** 2026-01-25
**Sprint Goal:** Achieve 100% FHIRPath official test compliance
**Current Compliance:** 50.7% (474/934 passing)
**Target Compliance:** 100% (934/934 passing)
**Compliance Gap:** 49.3 percentage points (460 tests)

---

## Sprint Vision

Achieve complete FHIRPath R4 specification compliance by systematically addressing all failing tests in the official test suite. This sprint represents the final push to 100% compliance, building on the foundation laid by SP-100 and SP-101.

### Strategic Alignment

This sprint aligns with the **FHIR4DS Core Principle #7: Standards Compliance Goals**:
- 100% FHIRPath specification compliance
- Validation against official test cases
- Production-ready SQL translation pathway

---

## Gap Analysis Summary

### Current Status

**Main Test Suite (50 tests):**
- Passing: 42/50 (84.0%)
- Failing: 8/50 (16.0%)

**Official Test Suite (934 tests):**
- Passing: 474/934 (50.7%)
- Failing: 460/934 (49.3%)

### Critical Gap Categories

#### P0 - CRITICAL (Blocks Core Functionality)

1. **$this Variable Context Propagation**
   - **Tests:** testDollarThis1, testDollarThis2
   - **Root Cause:** Variable binding not properly propagated in nested lambda contexts
   - **Impact:** Blocks all lambda expressions and complex filtering operations
   - **Architecture Violation:** Breaks unified FHIRPath variable scoping

2. **skip() Function CTE Column Propagation**
   - **Tests:** testDollarOrderAllowed, testDollarOrderAllowedA
   - **Root Cause:** CTE column reference failure after skip() operation
   - **Impact:** Breaks collection navigation and ordered operations
   - **Architecture Violation:** Violates CTE-first design principles

3. **is() Operator Empty Result Handling**
   - **Tests:** testPolymorphismIsA3
   - **Root Cause:** Polymorphic type checking returns false instead of empty for non-matching types
   - **Impact:** Type system incompleteness
   - **Architecture Violation:** Breaks type system consistency

#### P1 - HIGH (Specification Compliance)

4. **Semantic Validation for Invalid Expressions**
   - **Tests:** testComment7, testComment8, testLiteralIntegerNegative1Invalid
   - **Root Cause:** Parser accepting syntactically/semantically invalid expressions
   - **Impact:** Specification compliance violations
   - **Architecture Consideration:** Requires semantic validator enhancements

5. **Collection Functions**
   - **Current:** 4/8 passing (50%)
   - **Impact:** Core FHIRPath functionality incomplete
   - **Dependencies:** Depends on P0 fixes ($this, skip)

#### P2 - MEDIUM (Edge Cases)

6. **Arithmetic Type Coercion**
   - **Tests:** 1 failing
   - **Impact:** Edge case handling

7. **convertsTo Function Enhancements**
   - **Tests:** Multiple failures across type system
   - **Impact:** Type conversion completeness

---

## Prioritized Implementation Strategy

### Phase 1: Foundation Fixes (P0)

**Goal:** Unblock core functionality and enable subsequent fixes

#### Task SP-102-001: $this Variable Context Propagation
**Priority:** P0
**Estimated Effort:** 6-8 hours
**Dependencies:** None
**Tests Fixed:** 2 (directly), 50+ (indirectly via unblocking lambdas)

**Implementation Strategy:**
- Fix `VariableBinding` propagation in `TranslationContext`
- Ensure `$this` is accessible in nested lambda scopes
- Update CTE generation to include variable references
- Test with lambda expressions (where, select, all, any)

**Architectural Requirements:**
- Maintain unified FHIRPath variable scoping rules
- Ensure population-first design (no single-patient workarounds)
- Support both DuckDB and PostgreSQL dialects

#### Task SP-102-002: skip() CTE Column Propagation
**Priority:** P0
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Tests Fixed:** 2 (directly), 10+ (indirectly)

**Implementation Strategy:**
- Fix CTE column reference tracking after skip() operation
- Ensure column aliases propagate through CTE chain
- Update `CTEBuilder` to handle skip() context changes
- Test with chained operations: `skip().select()`, `skip().where()`

**Architectural Requirements:**
- CTE-first design: skip() must generate proper CTE structure
- Thin dialects: Only syntax differences in dialect layer
- No business logic in dialect implementations

#### Task SP-102-003: is() Operator Empty Result Handling
**Priority:** P0
**Estimated Effort:** 3-4 hours
**Dependencies:** None
**Tests Fixed:** 1 (directly), 5+ (indirectly)

**Implementation Strategy:**
- Fix polymorphic type resolution to return empty set (not false)
- Update type checking logic in type operation visitor
- Ensure consistent behavior across all type operations
- Test with various type combinations

**Architectural Requirements:**
- Consistent type system behavior
- Alignment with FHIRPath R4 specification

### Phase 2: Validation & Collection Functions (P1)

**Goal:** Complete core FHIRPath functionality

#### Task SP-102-004: Semantic Validation for Invalid Expressions
**Priority:** P1
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Tests Fixed:** 3

**Implementation Strategy:**
- Enhance semantic validator to reject invalid expressions
- Add validation for incomplete operators (e.g., `2 + 2 /`)
- Add validation for unterminated comments
- Fix negative literal validation in convertsTo context
- Ensure proper error reporting

**Architectural Requirements:**
- Clear separation between parse and validation errors
- Proper error type classification

#### Task SP-102-005: Collection Functions Comprehensive Fix
**Priority:** P1
**Estimated Effort:** 8-12 hours
**Dependencies:** SP-102-001 ($this), SP-102-002 (skip)
**Tests Fixed:** 50+

**Implementation Strategy:**
- Comprehensive audit of all collection functions
- Fix where(), select(), all(), any(), exists()
- Fix aggregate operations: aggregate(), repeat(), distinct()
- Ensure consistent context management across functions
- Add comprehensive test coverage

**Architectural Requirements:**
- Population-first design for all collection operations
- CTE-first structure for complex queries
- Proper variable scoping in lambdas

### Phase 3: Type System & Edge Cases (P2)

**Goal:** Complete type system and handle edge cases

#### Task SP-102-006: Arithmetic Type Coercion
**Priority:** P2
**Estimated Effort:** 2-3 hours
**Dependencies:** None
**Tests Fixed:** 1

#### Task SP-102-007: convertsTo Function Enhancements
**Priority:** P2
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Tests Fixed:** 5+

---

## Success Criteria

### Must Have (Definition of Done)
- ✅ All 8 main test suite tests passing (100%)
- ✅ All 460 official test suite failures addressed
- ✅ 100% compliance achieved (934/934 passing)
- ✅ All code reviewed and approved
- ✅ No architectural violations
- ✅ Multi-database parity (DuckDB + PostgreSQL)

### Should Have
- ✅ Comprehensive test coverage for fixed functionality
- ✅ Documentation updates
- ✅ Performance regression checks

### Could Have
- ✅ Additional edge case tests
- ✅ Performance optimizations

---

## Risk Assessment

### High Risk Items
1. **$this Variable Context** - High complexity, foundational to lambdas
   - **Mitigation:** Incremental testing with simple lambdas first

2. **skip() Column Propagation** - May require CTE builder refactoring
   - **Mitigation:** Isolate changes to CTE column tracking only

### Medium Risk Items
1. **Collection Functions** - Large scope, depends on P0 fixes
   - **Mitigation:** Break into sub-tasks per function

2. **Semantic Validation** - May affect parser behavior
   - **Mitigation:** Comprehensive testing of valid expressions

### Low Risk Items
1. **Type System Edge Cases** - Isolated changes
   - **Mitigation:** Standard testing procedures

---

## Testing Strategy

### Test Execution
1. **Unit Tests:** Run for each fix
2. **Integration Tests:** Cross-function validation
3. **Compliance Tests:** Full official test suite after each phase
4. **Database Parity:** Test both DuckDB and PostgreSQL

### Test Commands
```bash
# Unit tests
python3 -m pytest tests/unit/fhirpath/sql/ -v

# Compliance tests (50 tests)
python3 -m pytest tests/integration/fhirpath/official_test_runner.py -v

# Full official suite (934 tests)
python3 tests/integration/fhirpath/official_test_runner.py

# Multi-database validation
python3 -m pytest tests/integration/test_cross_database_dialect_compatibility.py -v
```

---

## Git Workflow

### Branch Strategy
```bash
# Create sprint worktree
git worktree add ../sprint-SP-102 sprint/SP-102

# Per-task workflow
git checkout -b SP-102-001-this-context
# ... implement ...
git commit -m "fix(SP-102-001): $this variable context propagation"

git checkout sprint-SP-102
git merge SP-102-001-this-context --no-ff
```

### Commit Message Format
- `fix(SP-102-XXX): brief description`
- `feat(SP-102-XXX): new feature`
- `refactor(SP-102-XXX): refactoring`

---

## Timeline Estimate

- **Phase 1 (P0):** 3 tasks × 6 hours = 18 hours
- **Phase 2 (P1):** 2 tasks × 10 hours = 20 hours
- **Phase 3 (P2):** 2 tasks × 4 hours = 8 hours
- **Testing & Validation:** 6 hours
- **Buffer:** 8 hours

**Total Estimated Effort:** 60 hours (~1.5 weeks sprint)

---

## Dependencies

### Internal Dependencies
- SP-102-005 depends on SP-102-001 ($this)
- SP-102-005 depends on SP-102-002 (skip)
- All tasks depend on SP-100 and SP-101 completion

### External Dependencies
- None (self-contained sprint)

---

## Rollout Plan

1. **Phase 1a:** Fix $this context (SP-102-001)
2. **Phase 1b:** Fix skip() propagation (SP-102-002)
3. **Phase 1c:** Fix is() operator (SP-102-003)
4. **Validation Point:** 1-3 should unblock many tests
5. **Phase 2a:** Fix semantic validation (SP-102-004)
6. **Phase 2b:** Comprehensive collection functions (SP-102-005)
7. **Validation Point:** Should reach 90%+ compliance
8. **Phase 3:** Type system and edge cases (SP-102-006, SP-102-007)
9. **Final Validation:** 100% compliance target

---

## Sprint Retrospective Questions

1. What was the biggest blocker to 100% compliance?
2. Which architectural patterns helped/hindered progress?
3. What can be automated in the compliance testing process?
4. What lessons learned for future specification compliance efforts?

---

**Sprint Status:** Planning Complete
**Next Step:** Create detailed task documents and begin execution
**Approval Required:** Proceed with Phase 1 implementation?
