# Sprint 007: FHIRPath Function Completion - Path to 70%

**Sprint**: Sprint 007 - Complete High-Value Functions
**Duration**: 06-10-2025 - 27-10-2025 (3 weeks)
**Sprint Lead**: Senior Solution Architect/Engineer
**Developer**: Mid-Level Developer (promoted from Junior)
**Context**: Complete remaining high-value FHIRPath functions to achieve 70% official test coverage milestone

---

## Sprint Goals

### Primary Objectives
1. **Complete String Functions**: Implement missing string operations to achieve 70%+ category coverage
2. **Complete Type Functions**: Implement ofType() to finish type function category
3. **Path Navigation Investigation**: Identify and fix quick wins in path navigation
4. **Integration Validation**: Complete pending validation tasks from Sprint 006
5. **Achieve 70% Official Test Coverage**: Reach 654+/934 tests passing (70%+ milestone)

### Success Criteria
- [x] String functions: 16.3% → 70%+ (35+/49 tests)
- [x] Type functions: 74.8% → 80%+ (ofType complete)
- [x] Path navigation: 19.8% → 30%+ (quick wins)
- [x] Official test coverage: 62.5% → 70%+ (654+/934 tests)
- [x] Healthcare test coverage: 95%+ maintained
- [x] Multi-database consistency: 100% maintained
- [x] Integration validation complete (SP-006-022, 023, 024)

### Context from Sprint 006

**Sprint 006 Achievements**:
- 62.5% official test coverage (584/934 tests) ✅
- **26-28 tasks completed** (74-80% completion rate) ✅
- Math functions: 100% coverage ✅
- Type functions: 74.8% coverage ✅
- Boolean logic: 83.3% coverage ✅
- **Critical bugs fixed**: Type dispatch (+94 tests), string signatures (+6 tests) ✅
- **SP-006-029 MERGED**: Type function dispatch fix ✅
- **100% architecture compliance**: Thin dialect pattern maintained ✅

**Identified Gaps** (Strategic deferrals for bug fixes):
- String functions: 16.3% (gap: ~27 tests) - **PRIORITY 1**
- ofType() function: Not started - **PRIORITY 2**
- Path navigation: 19.8% (needs investigation) - **PRIORITY 3**
- count() aggregation: Partial implementation - **PRIORITY 4**
- Integration validation: Deferred from SP-006 - **PRIORITY 5**

---

## Task Breakdown

### Phase 1: Complete High-Value Functions (Week 1)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria | Status |
|---------|-----------|----------|----------|--------------|------------------|--------|
| SP-007-001 | Implement matches() regex function | Mid-Level Dev | 8h | None | Regex matching works in both DBs | ✅ MERGED |
| SP-007-002 | Implement replaceMatches() function | Mid-Level Dev | 8h | SP-007-001 | Regex replacement works | ✅ MERGED |
| SP-007-003 | Implement contains() function | Mid-Level Dev | 4h | None | Substring detection works | ✅ MERGED |
| SP-007-004 | Implement startsWith()/endsWith() | Mid-Level Dev | 6h | None | Prefix/suffix detection works | ✅ MERGED |
| SP-007-005 | Implement upper()/lower()/trim() | Mid-Level Dev | 6h | None | Case conversion and trimming works | ✅ MERGED |
| SP-007-006 | Implement toChars() function | Mid-Level Dev | 4h | None | String to char array conversion | ✅ MERGED |
| SP-007-007 | Unit tests for new string functions | Mid-Level Dev | 8h | SP-007-006 | 90%+ coverage, all tests pass | ✅ MERGED |

**Phase 1 Success Metrics**:
- [ ] String functions: 16.3% → 70%+ (35+/49 tests)
- [ ] +27 tests to overall coverage
- [ ] Multi-database consistency maintained
- [ ] Performance: <10ms per string operation

**Estimated Impact**: +27 tests (584 → 611, ~65.4%)

---

### Phase 2: Complete Type and Collection Functions (Week 1-2)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria | Status |
|---------|-----------|----------|----------|--------------|------------------|--------|
| SP-007-008 | Complete ofType() implementation | Mid-Level Dev | 8h | None | Type filtering works correctly | ✅ MERGED |
| SP-007-009 | Complete count() aggregation | Mid-Level Dev | 4h | None | Aggregation works on all collections | ✅ MERGED |
| SP-007-010 | Unit tests for ofType()/count() | Mid-Level Dev | 6h | SP-007-009 | 90%+ coverage, all pass | ✅ MERGED |

**Phase 2 Success Metrics**:
- [ ] Type functions: 74.8% → 80%+ (85+/107 tests)
- [ ] Collection functions: improved count() support
- [ ] +15 tests to overall coverage
- [ ] ofType() working in both databases

**Estimated Impact**: +15 tests (611 → 626, ~67.0%)

---

### Phase 3: Path Navigation Investigation and Quick Wins (Week 2)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria | Status |
|---------|-----------|----------|----------|--------------|------------------|--------|
| SP-007-011 | Investigate path navigation failures | Mid-Level Dev | 12h | None | Root causes identified | ✅ MERGED |
| SP-007-012 | Implement path navigation quick wins | Mid-Level Dev | 12h | SP-007-011 | +20-30 tests passing | ✅ MERGED |
| SP-007-013 | Analyze convertsTo*() vs core FHIRPath | Mid-Level Dev | 6h | SP-007-011 | Clear categorization | ⏳ Pending |
| SP-007-014 | Unit tests for path navigation fixes | Mid-Level Dev | 6h | SP-007-012 | 90%+ coverage | ⏳ Pending |

**Phase 3 Success Metrics**:
- [ ] Path navigation: 19.8% → 30%+ (40+/131 tests)
- [ ] +20-30 tests to overall coverage
- [ ] Clear understanding of remaining gaps
- [ ] Implementation plan for Sprint 008

**Estimated Impact**: +25 tests (626 → 651, ~69.7%)

---

### Phase 4: Integration Validation and Documentation (Week 3)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria | Status |
|---------|-----------|----------|----------|--------------|------------------|--------|
| SP-007-015 | Complete SP-006-022: Healthcare coverage validation | Mid-Level Dev | 6h | None | Healthcare tests analyzed | ✅ Complete |
| SP-007-016 | Complete SP-006-023: Multi-DB consistency | Mid-Level Dev | 8h | None | 100% consistency validated | ⏳ Pending |
| SP-007-017 | Complete SP-006-024: Performance benchmarking | Mid-Level Dev | 8h | SP-007-016 | Benchmarks documented | ⏳ Pending |
| SP-007-018 | Complete SP-006-025: Update documentation | Mid-Level Dev | 8h | SP-007-017 | Docs updated, reports current | ⏳ Pending |
| SP-007-019 | Re-run official test suite | Mid-Level Dev | 4h | SP-007-014 | Coverage metrics updated | ⏳ Pending |
| SP-007-020 | Sprint 007 review and retrospective | Senior + Mid-Level | 4h | SP-007-019 | Sprint documented | ⏳ Pending |

**Phase 4 Success Metrics**:
- [ ] Healthcare coverage: 95%+ maintained
- [ ] Multi-database consistency: 100% validated
- [ ] Performance benchmarks: Comprehensive suite complete
- [ ] Documentation: All reports updated
- [ ] Official test coverage: 70%+ achieved 🎯

**Final Sprint Target**: 70%+ (654+/934 tests)

---

## Compliance Focus Areas

### Target Specifications
- **FHIRPath R4 Translation**: 62.5% → 70%+ (focus on string, type, path navigation)
- **Healthcare Use Cases**: 95%+ → maintained
- **Multi-Database Parity**: 100% maintained (no divergence allowed)

### Function Coverage Targets

**String Functions** (49 tests):
- Current: 8 passing (16.3%)
- Target: 35+ passing (70%+)
- Gap: ~27 tests
- Priority: CRITICAL (Week 1)

**Type Functions** (107 tests):
- Current: 80 passing (74.8%)
- Target: 85+ passing (80%+)
- Gap: ~5 tests (ofType completion)
- Priority: HIGH (Week 1-2)

**Path Navigation** (131 tests):
- Current: 26 passing (19.8%)
- Target: 40+ passing (30%+)
- Gap: ~14+ tests (quick wins)
- Priority: MEDIUM (Week 2)

---

## Architecture Alignment

### Unified FHIRPath Principles

**Thin Dialect Architecture** (100% compliance maintained):
- All business logic in translator
- Dialects contain ONLY syntax differences
- Zero divergence in translation logic between databases
- Pattern enforcement mandatory for all new tasks

**Population-First Design** (100% compliance maintained):
- All functions maintain population-scale capability
- No row-by-row processing patterns
- Proper array/collection handling throughout
- CTE-friendly SQL generation

**Multi-Database Support**:
- DuckDB and PostgreSQL parity maintained
- Identical business logic, syntax-only differences
- Comprehensive multi-DB testing for all new functions

### Integration Points

**From Sprint 006**:
- ✅ Type functions implemented and working
- ✅ Math functions 100% complete
- ✅ Boolean logic 83% complete
- ✅ Collection functions 64.6% complete

**For Sprint 007**:
- Complete string function library
- Finish type function category (ofType)
- Identify path navigation patterns
- Validate multi-database consistency

**For Sprint 008** (planned):
- Deep dive path navigation implementation
- Conversion function analysis (convertsTo*)
- Advanced collection edge cases

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation Strategy | Owner |
|------|--------|-------------|---------------------|-------|
| String regex complexity in SQL | Medium | Medium | Research database regex support early, plan fallbacks | Mid-Level Dev |
| Path navigation deeper complexity | High | Medium | Investigation task SP-007-011 to understand scope | Mid-Level Dev |
| Performance impact of new functions | Medium | Low | Continuous benchmarking, optimize if >10ms | Mid-Level Dev |
| Multi-DB regex differences | High | Medium | Test regex in both databases immediately | Mid-Level Dev |

### Mitigation Actions

**Week 1**:
1. Research regex support in DuckDB and PostgreSQL (Day 1)
2. Prototype matches()/replaceMatches() in both databases (Day 2)
3. Validate performance benchmarks for string functions (Day 5)

**Week 2**:
1. Complete path navigation investigation (Days 6-8)
2. Implement and test quick wins (Days 9-10)
3. Validate multi-database consistency (Day 10)

**Week 3**:
1. Run comprehensive integration tests (Days 11-12)
2. Complete performance benchmarking (Days 13-14)
3. Final validation and documentation (Day 15)

---

## Sprint Execution Plan

### Week 1: High-Value Function Implementation

**Days 1-2**: String regex functions (SP-007-001, 002)
- Research database regex support
- Implement matches() and replaceMatches()
- Multi-database testing

**Days 3-4**: String utility functions (SP-007-003, 004, 005, 006)
- Implement contains(), startsWith(), endsWith()
- Implement upper(), lower(), trim(), toChars()
- Unit testing

**Day 5**: String function testing and ofType start (SP-007-007, 008)
- Complete string function unit tests
- Begin ofType() implementation

### Week 2: Type Functions and Path Navigation

**Days 6-7**: Complete type functions (SP-007-008, 009, 010)
- Complete ofType() implementation
- Complete count() aggregation
- Unit testing

**Days 8-10**: Path navigation investigation (SP-007-011, 012, 013, 014)
- Analyze 105 failing tests
- Identify quick wins vs complex work
- Implement quick wins
- Unit testing

### Week 3: Integration and Validation

**Days 11-12**: Healthcare and multi-DB validation (SP-007-015, 016)
- Validate healthcare coverage
- Confirm multi-database consistency

**Days 13-14**: Performance and documentation (SP-007-017, 018)
- Comprehensive benchmarking
- Update all documentation and reports

**Day 15**: Final validation and sprint review (SP-007-019, 020)
- Re-run official test suite
- Sprint retrospective
- Plan Sprint 008

---

## Developer Guidance

### For Mid-Level Developer

**Congratulations on promotion!** You demonstrated outstanding performance in Sprint 006. Sprint 007 leverages your proven skills while introducing new challenges.

**Focus Areas**:
1. **Regex Implementation**: Research database regex carefully, test thoroughly
2. **Path Navigation**: Investigation mindset - understand before implementing
3. **Performance**: Continue <10ms translation target for all functions
4. **Architecture**: Maintain 100% thin dialect compliance

**New Responsibilities**:
- Lead technical decisions within sprint scope
- Mentor junior developers (if assigned to sprint)
- Contribute to architecture discussions
- Propose process improvements

**Support Available**:
- Senior architect for architectural guidance
- Pair programming for complex problems
- Code review for quality assurance
- Weekly 1:1 for support and feedback

---

## Deliverables and Acceptance Criteria

### Primary Deliverables

1. **String Function Library** (SP-007-001 to 007)
   - Acceptance: 70%+ string function coverage (35+/49 tests)
   - Quality: 90%+ unit test coverage, multi-DB consistency
   - Performance: <10ms translation per operation

2. **Type Function Completion** (SP-007-008 to 010)
   - Acceptance: ofType() working, 80%+ type function coverage
   - Quality: 90%+ unit test coverage, clean implementation
   - Performance: <10ms translation per operation

3. **Path Navigation Analysis** (SP-007-011 to 014)
   - Acceptance: +20-30 tests passing, clear implementation plan
   - Quality: Root cause analysis documented, quick wins implemented
   - Deliverable: Sprint 008 path navigation plan

4. **Integration Validation** (SP-007-015 to 018)
   - Acceptance: Healthcare validated, multi-DB confirmed, benchmarks complete
   - Quality: Comprehensive test reports, updated documentation
   - Deliverable: 70%+ official test coverage achieved 🎯

### Secondary Deliverables

1. **Performance Benchmark Suite**: Comprehensive timing data for all functions
2. **Path Navigation Roadmap**: Detailed plan for Sprint 008 deep dive
3. **Architecture Validation Report**: Thin dialect compliance confirmation

---

## Success Metrics

### Sprint-Level Metrics

**Test Coverage**:
- Official tests: 62.5% → 70%+ (584 → 654+ tests)
- String functions: 16.3% → 70%+ (8 → 35+ tests)
- Type functions: 74.8% → 80%+ (80 → 85+ tests)
- Path navigation: 19.8% → 30%+ (26 → 40+ tests)

**Quality Metrics**:
- Unit test coverage: 92%+ maintained
- Multi-database consistency: 100% maintained
- Performance: <10ms average maintained
- Architecture compliance: 100% maintained

**Productivity Metrics**:
- Tasks completed: 20/20 (100%)
- Sprint velocity: ~70 hours actual
- Bug rate: <5% of completed tasks
- Code review cycles: <2 per task

### Milestone-Level Metrics

**Progress Toward M004 Completion**:
- Before Sprint 007: ~75% complete
- After Sprint 007: ~85% complete
- Remaining for M004: 1-2 sprints (path navigation deep dive)

---

## Sprint Timeline

| Week | Focus | Key Deliverables | Milestone |
|------|-------|------------------|-----------|
| **Week 1** | High-value functions | String functions complete, ofType() | ~67% coverage |
| **Week 2** | Path navigation | Investigation complete, quick wins | ~70% coverage 🎯 |
| **Week 3** | Integration validation | All validation tasks complete | 70%+ validated |

**Critical Path**: String functions (Week 1) → ofType (Week 1-2) → Path navigation (Week 2) → Validation (Week 3)

---

## Sprint Review Preparation

### Demo Preparation (Week 3)

**Demo 1**: String Function Showcase
- Live demo: matches(), replaceMatches(), contains()
- Performance comparison: DuckDB vs PostgreSQL
- Healthcare use case examples

**Demo 2**: Type Function Completion
- ofType() filtering demonstration
- Multi-type collection handling
- Real-world FHIR data examples

**Demo 3**: Path Navigation Progress
- Investigation findings presentation
- Quick wins demonstration
- Sprint 008 roadmap preview

**Demo 4**: 70% Milestone Achievement**
- Coverage metrics dashboard
- Category-by-category progress
- Architectural compliance validation

---

## Retrospective Topics

### What Went Well (Capture During Sprint)
- Track effective investigation approaches
- Note particularly clean implementations
- Document performance wins

### What to Improve (Capture During Sprint)
- Identify estimation accuracy
- Note any architectural challenges
- Document process improvements

### Action Items for Sprint 008
- Carry forward lessons learned
- Apply process improvements
- Refine path navigation approach

---

## Appendix: Detailed Task Specifications

### SP-007-001: Implement matches() Regex Function

**Description**: Implement FHIRPath matches() function for regex pattern matching

**Technical Approach**:
```python
# Translator (business logic)
def _translate_matches(self, node: FunctionCallNode) -> SQLFragment:
    # Validate arguments: matches(pattern)
    # Extract string expression and regex pattern
    # Use dialect method for regex matching

# Dialect methods (syntax only)
# DuckDB: regexp_matches(string, pattern)
# PostgreSQL: string ~ pattern
```

**Acceptance Criteria**:
- [ ] matches(pattern) translates correctly
- [ ] Regex syntax works in both databases
- [ ] Edge cases handled (null, empty, invalid regex)
- [ ] Unit tests: 90%+ coverage
- [ ] Multi-database consistency: 100%

**Estimated Effort**: 8 hours

### SP-007-008: Complete ofType() Implementation

**Description**: Implement FHIRPath ofType() function for type-based collection filtering

**Technical Approach**:
```python
# Translator (business logic)
def _translate_oftype(self, node: TypeOperationNode) -> SQLFragment:
    # Extract collection and target type
    # Filter collection elements by type
    # Use dialect method for type filtering

# Dialect methods (syntax only)
# DuckDB: list_filter with type checking
# PostgreSQL: array filtering with type casting
```

**Acceptance Criteria**:
- [ ] ofType(Type) translates correctly
- [ ] Type filtering works on all FHIR types
- [ ] Multi-value collections handled
- [ ] Unit tests: 90%+ coverage
- [ ] +10-15 tests to coverage

**Estimated Effort**: 8 hours

### SP-007-011: Investigate Path Navigation Failures

**Description**: Comprehensive investigation of 105 failing path navigation tests

**Investigation Plan**:
1. Categorize failures by type (convertsTo*, complex paths, etc.)
2. Identify quick wins (simple fixes, <2h each)
3. Identify complex work (requires deeper implementation)
4. Create Sprint 008 implementation plan

**Deliverables**:
- Investigation report document
- Quick win task list (for SP-007-012)
- Sprint 008 path navigation plan
- Effort estimates for remaining work

**Acceptance Criteria**:
- [x] All 105 failures analyzed and categorized
- [x] Quick wins identified (28 tests identified)
- [x] Complex work scoped and estimated
- [x] Clear Sprint 008 plan created

**Status Update (2025-10-08)**: Investigation complete, senior review approved, merged to main. Report: `project-docs/investigations/2025-10-07-path-navigation-failures.md`. Ready for SP-007-012 quick wins implementation.

**Estimated Effort**: 12 hours

---

**Sprint 007 Plan Created**: 2025-10-05
**Plan Owner**: Senior Solution Architect/Engineer
**Next Review**: End of Week 1 (13-10-2025)

---
