# Sprint 016: Critical Blockers and DateTime Foundation

**Sprint Number**: 016
**Sprint Goal**: Fix critical FHIRPath blockers and establish datetime foundation for 80%+ compliance
**Duration**: 4 weeks (28 days)
**Start Date**: 2025-11-05
**End Date**: 2025-12-02
**Team**: Junior Developer (primary), Senior Architect (advisory)

---

## Sprint Objectives

### Primary Goal
Increase FHIRPath compliance from **~75% to 80-85%** (+40-50 tests) by fixing critical blockers (path navigation, basic expressions) and implementing datetime foundation that unblocks clinical quality measure use cases.

### Secondary Goals
1. **Fix Critical Blockers**: Path navigation and basic expression evaluation (currently broken)
2. **DateTime Foundation**: Establish date/time literal parsing and basic operations
3. **Lambda Variables**: Implement `$this`, `$index`, `$total` for advanced collection operations
4. **Maintain Excellence**: 100% architecture compliance, zero regressions, full DB parity

### Strategic Importance
Sprint 016 addresses the **most critical gaps** in FHIRPath compliance:
- **Path navigation (10% passing)** - Most fundamental FHIRPath feature
- **Basic expressions (0% passing)** - Foundation for all evaluation
- **DateTime (16.7% passing)** - Essential for clinical quality measures

Without these foundational capabilities, many downstream features cannot work.

---

## Sprint Metrics

### Success Criteria

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| **Overall Compliance** | ~707/934 (75.7%) | 753/934 (80.6%) | 770/934 (82.4%) |
| **Path Navigation** | 1/10 (10.0%) | 10/10 (100.0%) | 10/10 (100.0%) |
| **Basic Expressions** | 0/2 (0.0%) | 2/2 (100.0%) | 2/2 (100.0%) |
| **DateTime Functions** | 1/6 (16.7%) | 15/6 (est 25%+) | 25/52 (48%) |
| **Lambda Tests** | 0 est | +15-20 tests | +25 tests |
| **Unit Test Coverage** | 90% | >90% | >95% |

### Key Performance Indicators (KPIs)

- ✅ Path navigation 100% working (CRITICAL - unblocks other features)
- ✅ Basic expression evaluation fixed (CRITICAL - foundation)
- ✅ DateTime literals parsing correctly
- ✅ Lambda variables ($this, $index, $total) functional
- ✅ DuckDB and PostgreSQL parity maintained
- ✅ Zero regressions in existing ~707 passing tests
- ✅ All unit tests passing (target: 2300+ tests)
- ✅ Code review approval on all tasks

---

## Sprint Backlog

### Week 1: Critical Blocker #1 - Path Navigation (HIGHEST PRIORITY)

**Task**: SP-016-001
**Goal**: Fix FHIR resource path navigation (currently 10% → 100%)
**Effort**: 15-20 hours
**Expected Gain**: +9 tests
**Status**: Ready to start
**Priority**: 🔴 **CRITICAL BLOCKER**

**Why This Matters**:
Path navigation is the **most fundamental FHIRPath feature**. Without it:
- Cannot access resource fields (`Patient.birthDate`)
- Cannot traverse nested structures (`Patient.name.given`)
- Cannot iterate collections (`Patient.telecom.use`)
- Blocks hundreds of downstream tests

**Deliverables**:
- [x] Investigation: Understand current context loading mechanism
- [ ] Fix: FHIR resource → evaluation context conversion
- [ ] Enable: Simple field access (`Patient.birthDate`)
- [ ] Enable: Nested path navigation (`Patient.name.given`)
- [ ] Enable: Collection element access (`Patient.telecom.use`)
- [ ] Validate: All 10 path navigation tests passing
- [ ] Validate: Both DuckDB and PostgreSQL working

**Root Cause (from Sprint 008)**:
- Evaluation engine uses `fhirpathpy` but context loading incomplete
- JSON fixtures not properly parsed into evaluable FHIRPath context
- May be architectural separation needed between SQL translator (working) and evaluator

---

### Week 1-2: Critical Blocker #2 - Basic Expressions

**Task**: SP-016-002
**Goal**: Fix basic expression evaluation (currently 0% → 100%)
**Effort**: 5-8 hours
**Expected Gain**: +2 tests
**Status**: Blocked by path navigation investigation
**Priority**: 🔴 **CRITICAL BLOCKER**

**Why This Matters**:
Basic expression evaluation is the **foundation** for all FHIRPath functionality. These 2 tests represent core parsing and evaluation that everything depends on.

**Deliverables**:
- [ ] Debug: Identify why basic expressions failing
- [ ] Fix: Core expression parser/evaluator issues
- [ ] Validate: Both basic expression tests passing
- [ ] Ensure: No regressions in existing functionality

---

### Week 2-3: DateTime Literals and Basic Operations

**Task**: SP-016-003
**Goal**: Implement datetime foundation (16.7% → 25%+ of datetime category)
**Effort**: 12-15 hours
**Expected Gain**: +10-15 tests initially, foundation for +52 total
**Status**: Can start after blockers fixed
**Priority**: 🎯 **HIGH** (clinical quality measures depend on this)

**Why This Matters**:
Clinical quality measures heavily use temporal filtering:
- "All observations in the last 6 months"
- "Patients born before 1990"
- "Encounters during the measurement period"

**Deliverables**:
- [ ] Date literal parsing (`@2020-01-01`)
- [ ] DateTime literal parsing (`@2020-01-01T12:00:00`)
- [ ] Time literal parsing (`@T12:00:00`)
- [ ] `today()` function implementation
- [ ] `now()` function implementation
- [ ] Basic date comparison operators (=, !=, <, >, <=, >=)
- [ ] Proper date/datetime/time type system integration
- [ ] Cross-dialect date literal handling

**Technical Approach**:
- Research Python date/time libraries (datetime, dateutil, pendulum)
- Implement FHIRPath date/time type system
- SQL translation: dialect-specific date literal generation
- Edge cases: Timezone handling, precision, partial dates

---

### Week 3-4: Lambda Variables Implementation

**Task**: SP-016-004
**Goal**: Implement lambda variables for advanced collection operations
**Effort**: 15-18 hours
**Expected Gain**: +15-20 tests
**Status**: Can start after path navigation fixed
**Priority**: 🎯 **HIGH** (unlocks where, select, repeat, aggregate)

**Why This Matters**:
Lambda variables enable advanced FHIRPath patterns:
- `where($this.value > 5)` - filter with context
- `select($this.code)` - projection with context
- `repeat($this.contained)` - recursive expansion
- `aggregate($this + $total)` - custom aggregation with accumulator

**Deliverables**:
- [ ] `$this` variable - current iteration item
- [ ] `$index` variable - iteration index (0-based)
- [ ] `$total` variable - accumulator in aggregate()
- [ ] Evaluation context enhancement - variable storage
- [ ] Update: where() to provide $this
- [ ] Update: select() to provide $this and $index
- [ ] Update: repeat() to provide $this
- [ ] Update: aggregate() to provide $this and $total
- [ ] SQL translation: variable resolution
- [ ] Cross-dialect testing

**Technical Approach**:
- Extend EvaluationContext with variable scoping
- Implement variable resolution in expression evaluator
- SQL translation: CTE-based variable binding where possible
- Ensure proper scoping (nested where/select)

---

## Compliance Focus Areas

### Target Specifications

**FHIRPath R4 Specification**:
- **Current**: ~707/934 tests (75.7%)
- **Target**: 753/934 tests (80.6%)
- **Stretch**: 770/934 tests (82.4%)

### Compliance Activities

1. **Path Navigation Repair** (Week 1)
   - Fix context loading for FHIR resources
   - Enable field access, nested paths, collections
   - Expected: +9 tests, unblocks many downstream tests

2. **Basic Expression Repair** (Week 1-2)
   - Fix foundational evaluation issues
   - Expected: +2 tests

3. **DateTime Foundation** (Week 2-3)
   - Implement literals and basic functions
   - Expected: +10-15 tests, foundation for +37 more in Sprint 017

4. **Lambda Variables** (Week 3-4)
   - Enable advanced collection operations
   - Expected: +15-20 tests

### Compliance Metrics Tracking

- **Daily**: Run official path navigation subset (10 tests)
- **Weekly**: Run full official FHIRPath suite (934 tests)
- **Sprint End**: Comprehensive compliance report
- **Regression Prevention**: Monitor existing 707 tests remain passing

---

## Technical Focus

### Architecture Components

**Primary Components**:
- **Evaluator Context Loading** (fhir4ds/fhirpath/evaluator/)
  - Fix FHIR resource → context conversion
  - Enable proper path resolution

- **DateTime Type System** (fhir4ds/fhirpath/types/)
  - Implement Date, DateTime, Time types
  - Literal parsing and type checking

- **Variable Scoping** (fhir4ds/fhirpath/evaluator/context.py)
  - Add variable storage and resolution
  - Implement scoping for nested contexts

- **SQL Translation** (fhir4ds/fhirpath/sql/translator.py)
  - Date literal generation (dialect-specific)
  - Variable resolution in SQL context

### Database Dialects

**DuckDB**:
- Date literal format: `DATE '2020-01-01'`
- DateTime literal: `TIMESTAMP '2020-01-01 12:00:00'`
- Time literal: `TIME '12:00:00'`
- Current date: `CURRENT_DATE`
- Current timestamp: `CURRENT_TIMESTAMP`

**PostgreSQL**:
- Date literal format: `'2020-01-01'::DATE`
- DateTime literal: `'2020-01-01 12:00:00'::TIMESTAMP`
- Time literal: `'12:00:00'::TIME`
- Current date: `CURRENT_DATE`
- Current timestamp: `CURRENT_TIMESTAMP`

**Dialect Separation**:
- All syntax differences handled via method overriding
- No business logic in dialect classes
- Maintain 100% thin-dialect compliance

### Integration Points

- **Parser → Evaluator**: Date/time literal parsing
- **Evaluator → Type System**: Date type handling
- **Evaluator Context**: Variable storage and scoping
- **Translator → Dialects**: Date literal SQL generation
- **Official Tests**: Path navigation and datetime test suites

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Path navigation requires architectural refactor | Medium | High | Allocate 2 weeks if needed; consider SQL translator vs evaluator split |
| DateTime library dependencies complex | Medium | Medium | Research early; use Python stdlib datetime first |
| Context loading more broken than expected | Medium | High | Thorough investigation in Week 1; escalate if fundamental |
| Lambda variables interact poorly with SQL | Low | Medium | Focus on evaluator first; SQL translation stretch goal |
| Timezone handling adds complexity | Medium | Low | Start with UTC/naive datetime; defer timezone to Sprint 017 |

### Dependencies and Blockers

**Current Blockers**:
1. **Path navigation** - Must fix before other features can properly test
2. **Basic expressions** - Foundation for everything

**External Dependencies**:
- Python datetime library (stdlib - no new dependencies preferred)
- FHIRPath specification for date/time semantics
- Official test suite access

**Internal Dependencies**:
- SP-016-002 depends on SP-016-001 investigation insights
- SP-016-003 can proceed in parallel after blockers fixed
- SP-016-004 needs path navigation working for proper testing

### Contingency Plans

**If path navigation takes >2 weeks**:
- Extend SP-016-001 to full sprint
- Defer SP-016-004 (lambda variables) to Sprint 017
- Still achieve datetime foundation

**If datetime library research reveals complexity**:
- Start with basic literals only (no arithmetic)
- Defer complex operations to Sprint 017
- Focus on literal parsing and comparison

**If lambda variables prove too complex**:
- Implement $this only (most critical)
- Defer $index and $total to Sprint 017
- Reduce scope but maintain quality

---

## Testing Strategy

### Unit Testing

**Coverage Target**: >90% for all new code

**New Test Requirements**:
- Path navigation: 15+ tests (field access, nested paths, collections)
- Basic expressions: 5+ tests (ensure foundation solid)
- DateTime: 25+ tests (literals, today(), now(), comparison)
- Lambda variables: 30+ tests ($this, $index, $total, scoping)

**Test Enhancement**:
- Add edge cases for date boundary conditions
- Test variable scoping in nested contexts
- Cross-dialect date literal format validation

### Integration Testing

**Database Testing** (Both DuckDB and PostgreSQL):
- Path navigation with real FHIR resources
- Date literal SQL generation and execution
- Variable resolution in SQL context
- Full workflow: parse → evaluate → SQL → execute

**End-to-End Testing**:
- Load FHIR Patient resource
- Navigate to nested field
- Apply where() with $this variable
- Compare dates in filter
- Verify results match expectations

### Compliance Testing

**Official Test Suites**:
- Path navigation subset (10 tests) - Daily
- Basic expressions subset (2 tests) - After SP-016-002
- DateTime subset (6 initial tests) - After SP-016-003
- Full FHIRPath R4 suite (934 tests) - Weekly
- Regression suite (existing 707 tests) - Daily

**Regression Prevention**:
- Run existing test suite before and after each task
- Monitor for any compliance degradation
- Automated regression testing in CI/CD

**Performance Validation**:
- Benchmark path navigation performance
- Ensure date operations don't add >5% overhead
- Profile variable resolution impact

---

## Definition of Done

### Code Quality Requirements
- [ ] All code passes ruff, mypy, and formatting checks
- [ ] Unit test coverage >90% for new code
- [ ] All tests pass in both DuckDB and PostgreSQL environments
- [ ] Path navigation 100% working (10/10 tests)
- [ ] Basic expressions 100% working (2/2 tests)
- [ ] DateTime literals parsing correctly (>= 10 tests passing)
- [ ] Lambda variables functional ($this at minimum)
- [ ] Code review completed and approved by Senior Solution Architect/Engineer
- [ ] Documentation updated for all changes

### Compliance Requirements
- [ ] Official FHIRPath test suite shows improvement (Target: 753+/934)
- [ ] Path navigation: 10/10 tests passing (CRITICAL)
- [ ] Basic expressions: 2/2 tests passing (CRITICAL)
- [ ] DateTime category: >15 tests passing (target 25% of 52)
- [ ] No regression in existing ~707 tests
- [ ] Performance overhead <5% for new features
- [ ] Both databases achieve identical results

### Documentation Requirements
- [ ] Code comments added for complex logic (especially context loading)
- [ ] DateTime type system documented
- [ ] Lambda variable scoping documented
- [ ] Architecture documentation updated for any structural changes
- [ ] Sprint completion summary created
- [ ] Each task has completion documentation

### Architecture Requirements
- [ ] 100% thin-dialect compliance maintained
- [ ] Zero business logic in database dialect classes
- [ ] All database differences via method overriding
- [ ] Clean separation of concerns maintained
- [ ] Type system properly integrated

---

## Communication Plan

### Daily Updates
- **Format**: Async status update via Git commits + task document updates
- **Content**:
  - Yesterday: What was completed
  - Today: What's being worked on
  - Blockers: Any impediments or questions
- **Timing**: End of each development day

### Weekly Reviews
- **Schedule**: Every Friday, 2:00 PM
- **Participants**: Senior Solution Architect/Engineer, Junior Developer
- **Duration**: 30-45 minutes
- **Agenda**:
  - Review: Week's accomplishments
  - Blockers: Discuss any technical challenges
  - Compliance: Review test suite results
  - Planning: Adjust next week's focus if needed
  - Questions: Technical guidance and architecture alignment

### Sprint Ceremonies

**Sprint Planning**:
- **Date**: Nov 5, 2025 (Sprint start)
- **Duration**: 1 hour
- **Output**: Finalized task breakdown and sequence

**Mid-Sprint Check-in**:
- **Date**: Nov 19, 2025 (Week 2 end)
- **Duration**: 45 minutes
- **Output**: Progress assessment, risk mitigation adjustments

**Sprint Review**:
- **Date**: Dec 2, 2025 (Sprint end)
- **Duration**: 1 hour
- **Output**: Demonstration of working features, compliance metrics

**Sprint Retrospective**:
- **Date**: Dec 2, 2025 (after review)
- **Duration**: 45 minutes
- **Output**: Lessons learned, process improvements for Sprint 017

---

## Resource Requirements

### Development Environment

**Database Access**:
- DuckDB: Local file-based or in-memory (already available)
- PostgreSQL: `postgresql://postgres:postgres@localhost:5432/postgres`

**Testing Infrastructure**:
- Official FHIRPath test suite: `tests/compliance/fhirpath/official_tests.xml`
- FHIR resource fixtures: `tests/fixtures/fhir/`
- Unit test framework: pytest (already configured)

**Development Tools**:
- Python 3.10+
- ruff (linting and formatting)
- mypy (type checking)
- Git (version control)

### External Dependencies

**Specification References**:
- FHIRPath R4 Specification: http://hl7.org/fhirpath/
- FHIR R4 Specification: http://hl7.org/fhir/R4/
- FHIRPath official tests: Track any updates

**Python Libraries** (prefer stdlib):
- datetime (stdlib - date/time handling)
- dateutil (if needed for advanced parsing - evaluate first)
- fhirpathpy (current evaluator - may need fixes)

**Community Resources**:
- FHIRPath community forums (for specification clarification)
- HL7 FHIR community (for FHIR resource questions)

---

## Success Measurement

### Quantitative Metrics

**Task Completion**:
- SP-016-001 (Path Navigation): 100% complete
- SP-016-002 (Basic Expressions): 100% complete
- SP-016-003 (DateTime Literals): 100% complete
- SP-016-004 (Lambda Variables): 100% complete

**Compliance Improvement**:
- Overall: 75.7% → 80.6%+ (Target: +46 tests)
- Path Navigation: 10% → 100% (+9 tests)
- Basic Expressions: 0% → 100% (+2 tests)
- DateTime: 16.7% → 25%+ (+10-15 tests)
- Lambda-dependent tests: +15-20 tests

**Test Coverage**:
- Unit tests: >90% coverage maintained
- Integration tests: 100% passing
- Regression tests: 0 failures

**Performance**:
- Overhead: <5% for new features
- Path navigation: <100ms for typical resource
- Date operations: <10ms per comparison

### Qualitative Assessments

**Code Quality**:
- Architecture compliance: 100% (thin dialects)
- Code review: All approved
- Documentation: Complete and clear
- Maintainability: High (consistent patterns)

**Architecture Alignment**:
- Thin dialect principle: Maintained
- Population-first design: Maintained
- CTE-first SQL: Maintained
- Type system coherence: Improved

**Knowledge Transfer**:
- Context loading architecture understood
- DateTime type system documented
- Lambda variable patterns established
- Junior developer can explain approach

**Process Improvement**:
- Blocker resolution process refined
- Investigation tasks prove valuable
- Testing infrastructure enhanced

---

## Sprint Retrospective Planning

### Areas for Evaluation

**What went well**:
- Blocker prioritization
- Investigation before implementation
- Cross-database testing discipline
- Architecture compliance maintenance

**What could be improved**:
- Earlier identification of fundamental issues
- Better estimation for complex fixes
- More proactive performance testing

**Action items for Sprint 017**:
- Apply blocker-first approach
- Invest in better compliance tracking tools
- Earlier performance baseline establishment

**Lessons learned**:
- Context loading architecture critical
- DateTime requires careful type system design
- Lambda variables more complex than expected
- Testing infrastructure investment pays off

### Retrospective Format
- **Duration**: 45 minutes
- **Facilitation**: Senior Solution Architect/Engineer
- **Documentation**: Retrospective document in project-docs/plans/retrospectives/
- **Follow-up**: Action items tracked in Sprint 017 plan

---

## Sprint 016 Schedule

### Week 1 (Nov 5-11): Critical Blocker - Path Navigation

**Monday-Tuesday**: SP-016-001 Investigation
- Understand current context loading
- Identify root cause of path navigation failures
- Design fix approach

**Wednesday-Friday**: SP-016-001 Implementation
- Fix context loading
- Implement field access
- Test nested paths and collections

**Milestone**: Path navigation tests passing (10/10)

---

### Week 2 (Nov 12-18): Basic Expressions + DateTime Start

**Monday-Tuesday**: SP-016-002 Basic Expressions
- Fix core evaluation issues
- Validate foundation solid

**Wednesday-Friday**: SP-016-003 DateTime (Part 1)
- Implement date literal parsing
- Start datetime literal parsing
- today() function

**Milestone**: Basic expressions fixed, datetime literals parsing

---

### Week 3 (Nov 19-25): DateTime Complete + Lambda Start

**Monday-Tuesday**: SP-016-003 DateTime (Part 2)
- Complete datetime/time literals
- now() function
- Date comparison

**Wednesday-Friday**: SP-016-004 Lambda (Part 1)
- $this variable implementation
- Update where() and select()

**Milestone**: DateTime foundation complete, $this working

---

### Week 4 (Nov 26-Dec 2): Lambda Complete + Validation

**Monday-Wednesday**: SP-016-004 Lambda (Part 2)
- $index and $total variables
- Update repeat() and aggregate()
- Comprehensive testing

**Thursday-Friday**: Sprint Validation
- Full compliance suite run
- Performance validation
- Documentation completion
- Sprint review preparation

**Milestone**: 80%+ compliance achieved, Sprint 016 complete

---

## Alignment with Overall Roadmap

Sprint 016 is **Week 1-4 of the 6-8 sprint roadmap to 100% compliance**.

**Roadmap Position**:
- Sprint 015: 75.7% (Collection/String/Type functions) ✅ **COMPLETE**
- **Sprint 016**: 80.6% (Blockers + DateTime foundation) ⬅️ **YOU ARE HERE**
- Sprint 017: 91.8% (Types + Arithmetic + DateTime arithmetic)
- Sprint 018: 98.6% (Collections + Quantities)
- Sprint 019: 99.7% (Edge cases)
- Sprint 020: 100.0% (Final gaps)

**Critical Path Dependencies**:
- Sprint 016 fixes **must complete** before Sprint 017 can build on them
- Path navigation is **prerequisite** for most downstream features
- DateTime foundation enables Sprint 017's datetime arithmetic
- Lambda variables unlock Sprint 018's advanced collections

**Success Criteria for Roadmap**:
- Stay on schedule (1 sprint = 4 weeks)
- Maintain quality (100% architecture compliance)
- Hit targets (80.6% compliance this sprint)
- Build foundation (datetime, lambda for future sprints)

---

## Approval

**Sprint Plan Created By**: Senior Solution Architect/Engineer
**Creation Date**: 2025-11-04
**Sprint Status**: READY TO START
**Next Action**: Create SP-016-001 detailed task document

---

**Sprint 016: Critical Blockers and DateTime Foundation**
*Fixing fundamentals to enable the path to 100% FHIRPath compliance*

---

**Plan Last Updated**: 2025-11-04
