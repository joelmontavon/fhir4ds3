# Sprint Plan: 100% FHIRPath Official Test Compliance

**Sprint ID**: SP-100-FHIRPath
**Created**: 2026-01-24
**Sprint Goal**: Achieve 100% compliance with official FHIRPath test suite (934/934 tests passing)
**Current Baseline**: 50.2% compliance (469/934 tests passing)

---

## Executive Summary

This sprint addresses the remaining 465 failing FHIRPath official tests to achieve 100% specification compliance. The implementation gaps have been categorized into 3 phases based on priority and dependencies:

- **Phase 1**: Quick wins (+30-50 tests) - Critical missing functions
- **Phase 2**: High impact (+150-200 tests) - Core functionality gaps
- **Phase 3**: Complex cases (+200-250 tests) - Edge cases and refinement

**Total Estimated Effort**: 400-580 hours
**Target Duration**: Based on team capacity
**Success Criteria**: 100% test compliance (934/934 tests passing)

---

## Current State Analysis

### Historical Compliance Trend

| Date | Compliance | Tests Passing | Notes |
|------|------------|---------------|-------|
| 2025-10-17 | 64.99% | 607/934 | Sprint 009 baseline |
| 2025-12-30 | 35.91% | 334/930 | Sprint 022 (SQL-only mode) |
| 2025-12-31 | 49.3% | 460/934 | Sprint 022 (multiple fixes) |
| 2026-01-01 | 50.2% | 469/934 | Sprint 022 (select() fix) |

### Architecture Status

**✅ COMPLIANT** - No architectural violations detected:
- CTE-first design fully implemented
- Thin dialect architecture maintained
- Population-first analytics preserved
- Multi-database parity achieved

**Gaps are due to incomplete implementation, NOT architectural issues.**

### Known Issues (from gap analysis)

**Critical (P0):**
1. Aggregation functions not implemented: `sum`, `avg`, `min`, `max` (translator.py:1835-1838)
2. Conditional expression not implemented: `iif()` (translator.py:4030)
3. Type functions marked "temporary" (translator.py:1836)
4. CTE column propagation in collection chains

**High (P1):**
1. Collection Functions: 24.8% compliance (71/106 failing)
2. Type Functions: 37.9% compliance (44/72 failing)
3. Arithmetic Operators: 25.0% compliance (36/54 failing)
4. Empty collection `{}` handling (~17 tests)

---

## Sprint Goals

### Primary Goal

**Achieve 100% official FHIRPath test suite compliance** (934/934 tests passing)

### Secondary Goals

1. Maintain architectural principles (CTE-first, thin dialects)
2. Preserve multi-database parity (DuckDB + PostgreSQL)
3. Zero regression on existing passing tests
4. Document all implementation decisions

### Non-Goals

- Performance optimization (deferred to future sprint)
- New FHIRPath features beyond test suite requirements
- SQL-on-FHIR enhancements
- CQL integration improvements

---

## Sprint Scope

### In Scope

1. **Implementation gaps** for failing FHIRPath tests
2. **Bug fixes** in existing implementations
3. **Test infrastructure** improvements for validation
4. **Documentation** of implementation decisions

### Out of Scope

1. Security vulnerability remediation (separate sprint)
2. Performance optimization
3. New feature development
4. Technical debt reduction not related to test compliance

---

## Task Breakdown

### Phase 1: Critical Missing Functions (Quick Wins)

**Estimated Impact**: +30-50 tests
**Estimated Effort**: 40-60 hours

#### Task SP-100-001: Implement Aggregation Functions

**Description**: Implement `sum()`, `avg()`, `min()`, `max()` aggregation functions

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:1835-1838`

**Implementation Requirements**:
- Add `_translate_sum()`, `_translate_avg()`, `_translate_min()`, `_translate_max()` methods
- Use SQL aggregate functions with UNNEST for array collections
- Handle edge cases: empty collections, null values, mixed types
- Ensure population-scale compatibility

**Acceptance Criteria**:
- All aggregation function tests pass
- Both DuckDB and PostgreSQL dialects supported
- CTE integration works correctly
- No regression on existing tests

**Tests Affected**: ~15-20 tests

**Dependencies**: None

---

#### Task SP-100-002: Implement Conditional Expression (iif)

**Description**: Implement `visit_conditional` for `iif()` ternary operator

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:4030-4032`

**Implementation Requirements**:
- Implement `visit_conditional()` to generate SQL CASE statements
- Handle iif(condition, true_expr, false_expr) syntax
- Support nested conditionals
- Ensure type consistency across branches (SQL CASE requirement)

**Acceptance Criteria**:
- All iif() tests pass
- Nested conditionals work correctly
- Type consistency maintained
- Both dialects supported

**Tests Affected**: ~10-15 tests

**Dependencies**: None

---

#### Task SP-100-003: Fix Empty Collection Handling

**Description**: Implement proper empty collection `{}` semantics per FHIRPath spec

**Location**: Multiple translator methods

**Implementation Requirements**:
- Create centralized empty collection handling utility
- Ensure consistent vacuous truth semantics
- Special comparison logic for empty collections
- Fix error: "Could not convert string '{}' to BOOL/INT32"

**Acceptance Criteria**:
- `true = {}` evaluates to false
- `'1.1'.toInteger() = {}` handles empty collection
- All empty collection tests pass
- Consistent behavior across functions

**Tests Affected**: ~17 tests

**Dependencies**: None

---

### Phase 2: High Impact Core Functionality

**Estimated Impact**: +150-200 tests
**Estimated Effort**: 120-180 hours

#### Task SP-100-004: Fix CTE Column Propagation

**Description**: Resolve CTE column reference propagation in collection function chains

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:1692-4009`

**Implementation Requirements**:
- Fix collection slicing chains: `Patient.name.first().given`
- Ensure alias propagation through function chains
- Fix "Referenced column 'name_item'/'result' not found" errors
- Track CTE dependencies and column references

**Acceptance Criteria**:
- Collection slicing chains work correctly
- All chained operation tests pass
- CTE column references propagate correctly
- No regression on single operations

**Tests Affected**: ~20 tests

**Dependencies**: None

---

#### Task SP-100-005: Complete Type Function Implementation

**Description**: Remove "temporary handlers" and complete type functions

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:1836-1848`

**Implementation Requirements**:
- Complete AST adapter fix (referenced as SP-007-XXX)
- Fix `is()` type checking to return correct booleans
- Correct type conversion function semantics
- Handle polymorphic type resolution

**Acceptance Criteria**:
- No "temporary handler" comments remain
- Type functions achieve 80%+ compliance
- is(), as(), ofType() work correctly for all FHIR types
- Polymorphic resolution works correctly

**Tests Affected**: ~50 tests

**Dependencies**: May require architecture validation PEP

---

#### Task SP-100-006: Arithmetic Operator Type Coercion

**Description**: Implement spec-compliant type coercion for arithmetic operators

**Location**: `fhir4ds/main/fhirpath/sql/translator.py:2284-2921`

**Implementation Requirements**:
- Implement type promotion rules per FHIRPath spec
- Handle mixed-type operations (int + decimal)
- Fix division semantics
- Handle modulo operation edge cases

**Acceptance Criteria**:
- Arithmetic operators achieve 80%+ compliance
- Type coercion matches spec behavior
- All edge cases handled
- Both dialects produce consistent results

**Tests Affected**: ~36 tests

**Dependencies**: None

---

#### Task SP-100-007: Select() Nested Array Flattening

**Description**: Implement nested array handling in select()

**Location**: `fhir4ds/main/fhirpath/sql/translator.py`

**Implementation Requirements**:
- Implement nested array flattening
- Handle union in select projection
- Fix SQL syntax issues

**Acceptance Criteria**:
- Nested arrays flatten correctly
- Union in select works
- All select() tests pass

**Tests Affected**: ~11 tests

**Dependencies**: May overlap with SP-100-004

---

### Phase 3: Complex Edge Cases

**Estimated Impact**: +200-250 tests
**Estimated Effort**: 200-300 hours

#### Task SP-100-008: Result Logic Mismatches Resolution

**Description**: Case-by-case analysis and resolution of ~184 failing tests

**Location**: Multiple translator methods

**Implementation Requirements**:
- Categorize failures by error type
- Identify patterns amenable to batch fixes
- Implement fixes by category
- Document each resolution

**Acceptance Criteria**:
- Analyze all 184 result logic mismatches
- Categorize and prioritize fixes
- Implement high-impact fixes
- Document remaining issues for future sprints

**Tests Affected**: ~184 tests (batched)

**Dependencies**: None

---

#### Task SP-100-009: XOR Operator Support

**Description**: Implement XOR operator using (a OR b) AND NOT (a AND b)

**Location**: `fhir4ds/main/fhirpath/sql/translator.py`

**Implementation Requirements**:
- Implement XOR for both dialects
- Handle boolean logic with empty collections
- Ensure spec-compliant semantics

**Acceptance Criteria**:
- XOR operator works correctly
- All XOR tests pass
- Both dialects supported

**Tests Affected**: ~9 tests

**Dependencies**: None

---

#### Task SP-100-010: Implies Operator Completeness

**Description**: Complete boolean logic with empty collection semantics

**Location**: `fhir4ds/main/fhirpath/sql/translator.py`

**Implementation Requirements**:
- Complete implies() operator for empty collections
- Ensure spec-compliant boolean logic
- Handle edge cases

**Acceptance Criteria**:
- Implies operator works correctly
- All implies tests pass
- Empty collection semantics correct

**Tests Affected**: ~7 tests

**Dependencies**: None

---

#### Task SP-100-011: Matches() Regex Semantics

**Description**: Align matches() function with FHIRPath spec behavior

**Location**: String function implementations

**Implementation Requirements**:
- Fix regex semantics differences
- Ensure spec-compliant behavior
- Handle edge cases

**Acceptance Criteria**:
- matches() aligns with spec
- All matches() tests pass
- Both dialects supported

**Tests Affected**: ~11 tests

**Dependencies**: None

---

#### Task SP-100-012: Date/Time Literal Handling

**Description**: Fix partial dates and timezone handling

**Location**: Temporal function implementations

**Implementation Requirements**:
- Handle partial dates: `@2018-03`
- Handle Z timezone suffix: `@2012-04-15T15:00:00Z`
- Fix date parsing edge cases

**Acceptance Criteria**:
- Partial dates work correctly
- Timezone handling works
- All date/time tests pass

**Tests Affected**: ~14 tests

**Dependencies**: None

---

## Task Dependencies

```
Phase 1:
SP-100-001 ─┐
SP-100-002 ─┼─→ Can run in parallel
SP-100-003 ─┘

Phase 2:
SP-100-004 ───┐
SP-100-005 ───┼─→ Can run in parallel (mostly)
SP-100-006 ───┤
SP-100-007 ───┘
                 ↓
Phase 3:
SP-100-008 ────┐
SP-100-009 ────┼─→ Can run in parallel
SP-100-010 ────┤
SP-100-011 ────┤
SP-100-012 ────┘
```

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Type system changes break existing tests | Medium | High | Comprehensive regression testing |
| CTE propagation fixes introduce regressions | Medium | High | Incremental implementation with validation |
| SQL dialect differences multiply complexity | Low | Medium | Continuous dual-dialect testing |
| "Result logic mismatches" scope creep | High | High | Break into batches, set explicit boundaries |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Underestimated effort for complex cases | Medium | Medium | Buffer time in sprint, defer low-priority items |
| Dependencies block parallel execution | Low | Medium | Order tasks to maximize parallel work |
| Unexpected architectural issues | Low | High | Create PEP for architecture validation if needed |

## Acceptance Criteria

### Sprint Success Criteria

1. **100% Test Compliance**: 934/934 official FHIRPath tests passing
2. **Zero Regressions**: All currently passing tests (469) continue to pass
3. **Dual Dialect Parity**: DuckDB and PostgreSQL show identical results
4. **Architecture Compliance**: No violations of CTE-first, thin dialect principles
5. **Documentation Complete**: All implementation decisions documented

### Quality Gates

1. **Build**: All tests pass with zero errors
2. **Compliance Report**: Automated report shows 100% compliance
3. **Code Review**: All changes reviewed by architect
4. **Multi-Database Testing**: Both DuckDB and PostgreSQL validated

---

## Timeline

### Sprint Schedule (Based on Team Capacity)

**Assumption**: 2-person team, 2-week sprint

**Week 1:**
- Days 1-2: Phase 1 tasks (quick wins)
- Days 3-5: Phase 2 start (2-3 tasks)

**Week 2:**
- Days 6-10: Phase 2 completion + Phase 3 start
- Days 11-12: Phase 3 completion
- Days 13-14: Testing, validation, documentation

### Milestones

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| M1: Quick Wins Complete | Day 2 | +30-50 tests passing |
| M2: Core Functionality Complete | Day 10 | +150-200 tests passing |
| M3: Edge Cases Complete | Day 12 | +200-250 tests passing |
| M4: 100% Compliance Achieved | Day 13 | 934/934 tests passing |

---

## Artifacts

### Deliverables

1. **Sprint Plan Document** (this file)
2. **Task Documents** for each SP-100-* task
3. **Implementation Summary** documenting all changes
4. **Compliance Report** showing 100% achievement
5. **Test Results** for both DuckDB and PostgreSQL

### Documentation Updates

1. Update compliance tracker with new results
2. Document implementation decisions in project-docs/
3. Update CLAUDE.md with any architectural notes
4. Create PEP if architectural validation needed

---

## Glossary

- **CTE**: Common Table Expression
- **AST**: Abstract Syntax Tree
- **FHIRPath**: Clinical Quality Language expression language
- **SQL-on-FHIR**: Standard for querying FHIR data with SQL
- **Thin Dialect**: Database dialects containing only syntax differences
- **Population-First**: Design pattern optimizing for population-scale analytics

---

## Appendix A: Reference Files

### Key Implementation Files

- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser.py` - Main parser entry point
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py` - SQL translator (11,000+ lines)
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/ast/nodes.py` - AST node definitions
- `/mnt/d/fhir4ds3/tests/compliance/fhirpath/official_tests.xml` - Official test suite
- `/mnt/d/fhir4ds3/tests/integration/fhirpath/official_test_runner.py` - Test runner

### Compliance References

- `/mnt/d/fhir4ds3/tests/integration/fhirpath/README.md` - Compliance test documentation
- `/mnt/d/fhir4ds3/project-docs/compliance/sprint-011-results.md` - Previous sprint results

---

**Sprint Plan Status**: DRAFT - Pending Approval
**Next Step**: Review and approve sprint plan before task creation
