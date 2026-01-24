# Sprint 018 Plan: Foundational Compliance Fixes

**Sprint**: 018 - Foundational Compliance Fixes
**Duration**: 2025-11-12 - 2025-12-09 (4 weeks)
**Sprint Lead**: Senior Solution Architect/Engineer
**Developer**: Junior Developer

---

## Sprint Goals

### Primary Objectives

1. **Fix Literal Evaluation in SQL Translator**: Resolve critical bug preventing literals from being evaluated, affecting all test categories
2. **Implement Type Conversion Functions**: Add full convertsToX() and toX() function family for FHIRPath specification compliance
3. **Fix Union Operator and Core Functions**: Implement missing collection union operator and critical functions (not(), today(), now())
4. **Achieve 60-70% FHIRPath Compliance**: Improve from current 42.2% to 60-70% through targeted fixes

### Success Criteria

- [x] Literal evaluation bug fixed - all literal types (numbers, strings, dates, booleans, quantities) working
- [x] Type conversion functions implemented - 12+ functions (convertsToBoolean, toBoolean, convertsToInteger, toInteger, etc.)
- [x] Union operator working for all collection types
- [x] Core functions implemented (not(), today(), now(), Boolean aggregates)
- [x] FHIRPath compliance: 42.2% → 60-70% (+170-260 tests passing)
- [x] Zero regressions in existing passing tests
- [x] Both DuckDB and PostgreSQL validated

### Alignment with Architecture Goals

This sprint directly supports **100% FHIRPath specification compliance** by fixing the most foundational issue (literal evaluation) and implementing high-value functions. The literal bug fix alone could unlock 100-150 additional passing tests across all categories. These fixes maintain the "thin dialect" principle - all business logic in the SQL translator, only syntax differences in dialect implementations.

---

## Task Breakdown

### High Priority Tasks (Critical Path)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| **SP-018-002** | Fix Literal Evaluation in SQL Translator | Junior | 20-25h | None | All literal types evaluate correctly, +100-150 tests passing |
| **SP-018-003** | Implement Type Conversion Functions | Junior | 15-18h | SP-018-002 | 12 type conversion functions working, +40-50 tests passing |
| **SP-018-004** | Implement Union Operator and Core Functions | Junior | 10-15h | SP-018-002 | Union operator working, not()/today()/now() implemented, +30-40 tests passing |

### Medium Priority Tasks

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| **SP-018-005** | Complete Easy Win Categories to 100% | Junior | 8-12h | SP-018-002, SP-018-003, SP-018-004 | DateTime, Path Navigation, Math, Boolean Logic at 100% |
| **SP-018-006** | Multi-Database Validation | Junior | 4-6h | All prior tasks | All fixes validated on both DuckDB and PostgreSQL |

### Low Priority Tasks (Stretch Goals)

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| **SP-018-007** | Documentation: Compliance Improvement Report | Junior | 3-4h | All tasks | Comprehensive compliance analysis document created |
| **SP-018-008** | Fix Pre-Existing Test Failures | Junior | 6-8h | None | 6 pre-existing test failures resolved |

**Total Sprint Capacity**: 66-88 hours (4-week sprint)

---

## Compliance Focus Areas

### Target Specifications

- **FHIRPath Official Specification**: 42.2% (394/934) → **60-70%** (560-654/934)
- **Expected Gain**: +166-260 tests passing
- **Focus Categories**:
  - All categories (literal bug affects everything)
  - Type_Functions: 25.9% → 60-70%
  - Collection_Functions: 22.7% → 40-50%
  - Comparison_Operators: 57.7% → 70-75%
  - Arithmetic_Operators: 13.9% → 25-30%

### Compliance Activities

1. **Literal Evaluation Fix** (SP-018-002): Foundational bug fix affecting all 13 test categories. Expected impact: +100-150 tests.
2. **Type Conversion Implementation** (SP-018-003): Complete convertsToX() and toX() family. Expected impact: +40-50 tests.
3. **Collection Operations** (SP-018-004): Union operator and core functions. Expected impact: +30-40 tests.
4. **Category Completion** (SP-018-005): Finish 4 near-complete categories. Expected impact: +15 tests.

### Compliance Metrics

- **Test Suite Execution**: Daily runs of official FHIRPath suite during development, full validation before each commit
- **Performance Benchmarks**: Maintain <5% performance regression, measure literal evaluation performance improvement
- **Regression Prevention**: All existing 394 passing tests must continue passing; automated regression testing

---

## Technical Focus

### Architecture Components

**Primary Components**: SQL Translator and Type System

- **SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`):
  - Fix literal evaluation (`visit_literal` method)
  - Implement type conversion functions
  - Add union operator support
  - Add missing core functions

- **Type System** (`fhir4ds/fhirpath/types/`):
  - Type registry enhancements for conversion functions
  - FHIR type checking improvements

- **Parser** (`fhir4ds/fhirpath/parser_core/`):
  - Ensure literal parsing is correct (likely already working)
  - Verify type conversion function signatures

### Database Dialects

- **DuckDB** (`fhir4ds/dialects/duckdb.py`):
  - Type conversion syntax (CAST operations)
  - Date/time literal formatting
  - Quantity literal support

- **PostgreSQL** (`fhir4ds/dialects/postgresql.py`):
  - PostgreSQL-specific type conversion syntax
  - Date/time literal formatting
  - Quantity literal support

**Critical**: All business logic in SQL translator. Dialects contain ONLY syntax differences.

### Integration Points

- **Official Test Runner** (`tests/integration/fhirpath/official_test_runner.py`): Already updated to SQL-only execution (SP-018-001), will measure compliance improvements
- **Type Registry**: Integration between type conversion functions and FHIR type system
- **Literal Handling**: Parser → AST → SQL Translator → Dialect → SQL execution flow

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|-------------------|
| Literal fix more complex than expected | Medium | High | Allocate full 25h budget; can extend to 2nd week if needed; isolate literal handling code first |
| Type conversions require type system refactor | Medium | Medium | Start with simple types (Boolean, Integer, String); defer complex types (Quantity) if needed |
| Union operator requires CTE changes | Low | Medium | Union is collection combining, should be straightforward SQL UNION; test incrementally |
| Literal fix breaks existing tests | Low | High | Comprehensive testing after each change; backup main branch state; rollback capability |

### Dependencies and Blockers

1. **No External Dependencies**: All work is internal to SQL translator
2. **No Blocking Tasks**: All tasks can start immediately (SP-018-001 already merged)
3. **Parallel Work Possible**: Type conversions and union operator can be developed in parallel after literal fix

### Contingency Plans

- **If literal fix takes >25h**: Extend sprint to 5 weeks OR reduce scope (defer type conversions to Sprint 019)
- **If compliance gain < 60%**: Still valuable progress; document findings for Sprint 019 planning
- **If critical bugs discovered**: Pause feature work, fix bugs, reassess sprint goals

---

## Testing Strategy

### Unit Testing

- **Coverage Target**: 90%+ for all new code
- **New Test Requirements**:
  - Literal evaluation tests for all types (numbers, strings, dates, booleans, quantities)
  - Type conversion function tests (12+ functions × multiple test cases)
  - Union operator tests (various collection types)
  - Core function tests (not(), today(), now(), Boolean aggregates)
- **Test Enhancement**: Add edge cases for existing literal handling if gaps found

### Integration Testing

- **Database Testing**: CRITICAL - ALL changes must be validated on both DuckDB and PostgreSQL
  - Literal evaluation in both databases
  - Type conversions in both databases
  - Union operator in both databases
  - Performance comparison between databases
- **End-to-End Testing**: Run full official FHIRPath test suite (934 tests) after each major fix
- **Performance Testing**: Measure literal evaluation performance before/after fix

### Compliance Testing

- **Official Test Suites**: FHIRPath R4 official tests (934 tests) - run daily during development
- **Regression Testing**: All 394 currently passing tests must continue passing
- **Custom Test Development**: Create targeted tests for literal edge cases discovered during debugging

### Manual Testing

- **Literal Evaluation**: Manual verification of literal SQL generation for each type
- **Type Conversions**: Manual testing of edge cases (invalid conversions, type mismatches)
- **Union Operator**: Manual verification of collection combining behavior

---

## Definition of Done

### Code Quality Requirements

- [x] All code passes ruff lint checks
- [x] All code passes mypy type checks
- [x] Unit test coverage ≥90% for new code
- [x] All tests pass in both DuckDB and PostgreSQL environments
- [x] Code review completed and approved by Senior Solution Architect/Engineer
- [x] Documentation updated for all changes (inline comments, docstrings)

### Compliance Requirements

- [x] FHIRPath official test suite passing rate: 42.2% → 60-70%
- [x] Zero regressions in existing 394 passing tests
- [x] Performance maintained or improved (no significant slowdown)
- [x] Both database dialects produce identical results

### Documentation Requirements

- [x] Code comments for complex literal evaluation logic
- [x] Docstrings for all new functions (type conversions, core functions)
- [x] Architecture documentation updated if structural changes made
- [x] Sprint status documentation kept current (task progress, blocker notes)

---

## Communication Plan

### Daily Updates

- **Format**: Brief status update in task markdown files (Progress Updates section)
- **Content**: What was completed, any blockers, next steps, estimated completion
- **Timing**: End of each work session

### Weekly Reviews

- **Schedule**: End of each week (Fridays)
- **Participants**: Senior Solution Architect/Engineer, Junior Developer
- **Agenda**:
  - Progress review (tasks completed, compliance gains)
  - Technical challenges and solutions
  - Planning adjustments for following week
  - Code review of completed work

### Sprint Ceremonies

- **Sprint Planning**: 2025-11-12 (2 hours) - Detailed task walkthrough, environment setup verification
- **Mid-Sprint Check-in**: 2025-11-25 (1 hour) - Progress assessment, course corrections if needed
- **Sprint Review**: 2025-12-06 (1.5 hours) - Demo compliance improvements, technical review
- **Sprint Retrospective**: 2025-12-09 (1 hour) - Lessons learned, process improvements

---

## Resource Requirements

### Development Environment

- **Database Access**:
  - DuckDB (local, already configured)
  - PostgreSQL (`postgresql://postgres:postgres@localhost:5432/postgres`)
- **Testing Infrastructure**: Official FHIRPath test suite (already integrated)
- **Development Tools**: Python 3.10+, pytest, ruff, mypy (already configured)

### External Dependencies

- **Specification Updates**: Monitor FHIRPath specification for any updates (unlikely during sprint)
- **Third-Party Libraries**: No new dependencies expected; existing libraries sufficient
- **Community Resources**: FHIRPath official test suite (already integrated), FHIRPath specification documentation

---

## Success Measurement

### Quantitative Metrics

- **Task Completion Rate**: Target 100% for high-priority tasks, 80% for medium-priority
- **Test Coverage**: Target 90%+ for new code
- **Compliance Improvement**: 42.2% → 60-70% (+166-260 tests)
- **Performance**: Maintain <5% performance regression

### Qualitative Assessments

- **Code Quality**: Clean, maintainable code following established patterns; no band-aid fixes
- **Architecture Alignment**: Thin dialect adherence; all business logic in SQL translator
- **Knowledge Transfer**: Junior developer understands literal evaluation, type system, SQL generation
- **Process Improvement**: Faster compliance improvement velocity established

---

## Sprint Retrospective Planning

### Areas for Evaluation

1. **What went well**:
   - Effectiveness of compliance-driven development approach
   - Literal fix impact on test pass rate
   - Parallel task execution efficiency

2. **What could be improved**:
   - Estimation accuracy for literal fix complexity
   - Testing strategy effectiveness
   - Communication and coordination

3. **Action items**:
   - Process improvements for Sprint 019
   - Tooling enhancements identified during sprint
   - Documentation gaps discovered

4. **Lessons learned**:
   - Literal evaluation patterns and edge cases
   - Type conversion implementation approaches
   - SQL generation best practices

### Retrospective Format

- **Duration**: 1 hour
- **Facilitation**: Senior Solution Architect/Engineer
- **Documentation**: Captured in `project-docs/plans/retrospectives/SPRINT-018-RETROSPECTIVE.md`
- **Follow-up**: Action items tracked in Sprint 019 planning

---

**Plan Created**: 2025-11-11
**Last Updated**: 2025-11-11
**Next Review**: 2025-11-18 (Mid-sprint check-in)

---

*This sprint plan supports systematic progress toward 100% FHIRPath compliance by fixing foundational issues (literal evaluation) and implementing high-value functions (type conversions, union operator). Emphasis on quality, architecture compliance, and predictable delivery.*
