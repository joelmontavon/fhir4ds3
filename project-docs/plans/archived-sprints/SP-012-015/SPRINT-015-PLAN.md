# Sprint 015: Collection Functions Foundation

**Sprint Number**: 015
**Sprint Goal**: Implement core collection functions to achieve 45% FHIRPath compliance
**Duration**: 4 weeks (28 days)
**Start Date**: 2025-11-01
**End Date**: 2025-11-28
**Team**: Junior Developer (primary), Senior Architect (advisory)

---

## Sprint Objectives

### Primary Goal
Increase FHIRPath compliance from **39.9% to 45.3%** (+50 tests) by implementing foundational collection functions that enable advanced FHIR resource querying.

### Secondary Goals
1. Build critical infrastructure (union operator, lambda enhancement)
2. Establish collection function patterns for future sprints
3. Maintain architectural integrity (thin dialects, SQL-first)
4. Ensure DuckDB and PostgreSQL parity

---

## Sprint Metrics

### Success Criteria

| Metric | Baseline | Target | Stretch |
|--------|----------|--------|---------|
| **Overall Compliance** | 373/934 (39.9%) | 423/934 (45.3%) | 435/934 (46.6%) |
| **Collection Functions** | 27/141 (19.1%) | 77/141 (54.6%) | 85/141 (60.3%) |
| **Tests Added** | - | +50 tests | +60 tests |
| **Unit Test Coverage** | 90% | >90% | >95% |
| **Performance Impact** | Baseline | <5% overhead | <3% overhead |

### Key Performance Indicators (KPIs)

- ✅ All 4 weekly tasks completed
- ✅ DuckDB and PostgreSQL results within ±2 tests
- ✅ No regressions in existing 373 passing tests
- ✅ All unit tests passing (target: 2100+ tests)
- ✅ Code review approval on all PRs

---

## Sprint Backlog

### Week 1: Union Operator Implementation
**Task**: SP-015-001
**Goal**: Implement `|` (union) operator for collection combination
**Effort**: 12-15 hours
**Expected Gain**: +15-20 tests
**Status**: Ready to start

**Deliverables**:
- [ ] Union operator in parser
- [ ] SQL translation for union (UNION ALL)
- [ ] Dialect-specific implementations
- [ ] Comprehensive unit tests
- [ ] Integration with official test suite

---

### Week 2: Set Operations
**Task**: SP-015-002
**Goal**: Implement distinct, isDistinct, intersect, exclude
**Effort**: 12-15 hours
**Expected Gain**: +20-25 tests
**Status**: Blocked by Week 1

**Deliverables**:
- [ ] `distinct()` function - remove duplicates
- [ ] `isDistinct()` function - check for duplicates
- [ ] `intersect()` function - set intersection
- [ ] `exclude()` function - set difference
- [ ] SQL translation for all four functions
- [ ] Edge case handling (empty collections, mixed types)

---

### Week 3: Navigation Functions
**Task**: SP-015-003
**Goal**: Implement last, tail, skip, take functions
**Effort**: 8-10 hours
**Expected Gain**: +10-12 tests
**Status**: Completed - Pending Review

**Deliverables**:
- [x] `last()` function - get last element
- [x] `tail()` function - all except first
- [x] `skip(n)` function - skip first n elements
- [x] `take(n)` function - take first n elements
- [x] SQL translation with LIMIT/OFFSET
- [x] Boundary condition handling

---

### Week 4: Testing and Refinement
**Task**: SP-015-004
**Goal**: Validate, optimize, and prepare for Sprint 016
**Effort**: 8-10 hours
**Expected Gain**: +5 tests (refinement)
**Status**: Blocked by Week 3

**Deliverables**:
- [ ] Full official test suite validation (DuckDB + PostgreSQL)
- [ ] Performance benchmarking report
- [ ] Bug fixes for any edge cases discovered
- [ ] Sprint 015 completion summary
- [ ] Sprint 016 preparation and planning

---

## Technical Architecture

### Infrastructure Enhancements Required

#### 1. Union Operator (`|`) - Week 1
**Location**: Parser + Translator
**Complexity**: Medium
**Priority**: CRITICAL (blocks other collection functions)

**Technical Approach**:
```python
# Parser: Recognize | as binary operator
BINARY_OPERATORS = {
    '+': 'add', '-': 'subtract',
    '|': 'union',  # ADD THIS
}

# Translator: Generate SQL UNION ALL
def translate_union(left, right):
    return f"""
    SELECT * FROM ({left_sql})
    UNION ALL
    SELECT * FROM ({right_sql})
    """
```

**Why Critical**: Union operator is used extensively in FHIRPath expressions and blocks many collection tests.

---

#### 2. Lambda Expression Enhancement - Week 1
**Location**: Evaluator + Context
**Complexity**: Medium-High
**Priority**: HIGH (needed for advanced functions)

**Technical Approach**:
```python
# Add lambda variable support
class EvaluationContext:
    def __init__(self):
        self.variables = {}  # $this, $total, $index

    def set_variable(self, name, value):
        self.variables[name] = value

    def get_variable(self, name):
        return self.variables.get(name)
```

**Scope**: Implement `$this` variable support in Week 1. Advanced variables (`$total`, `$index`) deferred to Sprint 016.

---

### Collection Function Patterns

All collection functions follow this pattern:

```python
class FunctionLibrary:
    @fhirpath_function('functionName', min_args=0, max_args=1)
    def fn_function_name(self, context_data, args, context):
        """
        Function description per FHIRPath spec

        Args:
            context_data: Input collection
            args: Function arguments
            context: Evaluation context

        Returns:
            Transformed collection
        """
        # 1. Validate input
        # 2. Apply operation
        # 3. Return result
```

**SQL Translation**:
```python
class ASTToSQLTranslator:
    def translate_function_call(self, node):
        if node.function_name == 'functionName':
            return self._translate_function_name(node)
```

---

## Risk Management

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Union operator breaks existing operators | Medium | High | Comprehensive regression testing |
| Lambda variables scope incorrectly | Medium | Medium | Incremental implementation, extensive unit tests |
| SQL translation performance issues | Low | Medium | Benchmark early, optimize as needed |
| DuckDB/PostgreSQL divergence | Low | High | Test both databases continuously |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Week 1 infrastructure takes longer | Medium | High | Front-load time, pair programming if stuck |
| Complex edge cases discovered | Medium | Medium | Allocate Week 4 for refinement |
| PostgreSQL compatibility issues | Low | Medium | Test both databases from Week 1 |

### Mitigation Strategies

1. **Front-Load Infrastructure**: Complete union operator and lambda enhancement in Week 1 before starting collection functions
2. **Continuous Testing**: Run official test suite after each function implementation
3. **Early Database Testing**: Test PostgreSQL from Day 1, not just Week 4
4. **Incremental Lambda Support**: Start with `$this`, defer advanced variables to Sprint 016

---

## Dependencies

### Prerequisites
- ✅ SP-014-006-C (PostgreSQL fix) MUST be complete before Sprint 015
- ✅ Main branch at 373/934 tests (39.9% baseline)
- ✅ Both databases working with parity

### Blocking Dependencies
- Week 2 blocked by Week 1 (union operator needed)
- Week 3 blocked by Week 2 (set operations foundation)
- Week 4 blocked by Week 3 (all functions implemented)

### External Dependencies
- DuckDB and PostgreSQL instances available
- Official FHIRPath R4 test suite accessible
- CI/CD pipeline functional

---

## Sprint Schedule

### Week 1 (Nov 1-7): Union Operator + Lambda
**Focus**: Critical infrastructure
**Effort**: 12-15 hours

**Daily Plan**:
- **Day 1-2** (6-8h): Implement union operator
  - Day 1 AM: Parser changes (recognize `|` operator)
  - Day 1 PM: Translator SQL generation
  - Day 2 AM: Dialect implementations
  - Day 2 PM: Unit tests + integration testing

- **Day 3-5** (6-7h): Lambda variable support
  - Day 3: Context variable storage
  - Day 4: `$this` variable resolution
  - Day 5: Testing and validation

**Milestone**: Union operator working, `$this` variable supported

---

### Week 2 (Nov 8-14): Set Operations
**Focus**: Core collection manipulation
**Effort**: 12-15 hours

**Daily Plan**:
- **Day 1-2** (6-7h): `distinct()` and `isDistinct()`
  - Implement Python logic
  - SQL translation (SELECT DISTINCT)
  - Unit tests

- **Day 3-4** (6-8h): `intersect()` and `exclude()`
  - Set intersection logic
  - Set difference logic
  - SQL translation (INTERSECT, EXCEPT)
  - Handle edge cases (empty sets, mixed types)

**Milestone**: 4 set operations working in both databases

---

### Week 3 (Nov 15-21): Navigation Functions
**Focus**: Collection navigation
**Effort**: 8-10 hours

**Daily Plan**:
- **Day 1-2** (4-5h): `last()` and `tail()`
  - Implement reverse indexing
  - SQL translation (ORDER BY ... DESC LIMIT 1)
  - Unit tests

- **Day 2-3** (4-5h): `skip()` and `take()`
  - Implement offset/limit logic
  - SQL translation (OFFSET/LIMIT)
  - Boundary conditions (skip > count, take < 0)

**Milestone**: All navigation functions working

---

### Week 4 (Nov 22-28): Testing and Refinement
**Focus**: Validation and optimization
**Effort**: 8-10 hours

**Daily Plan**:
- **Day 1** (3h): Full test suite validation
  - Run official tests on DuckDB
  - Run official tests on PostgreSQL
  - Document results

- **Day 2** (2-3h): Performance benchmarking
  - Measure overhead vs Sprint 014 baseline
  - Profile slow operations
  - Optimize if needed

- **Day 3** (2-3h): Bug fixes and edge cases
  - Address any test failures
  - Fix edge cases discovered in testing

- **Day 4** (2h): Sprint completion
  - Sprint 015 summary report
  - Code review and cleanup
  - Sprint 016 preparation

**Milestone**: 45% compliance achieved, ready for Sprint 016

---

## Definition of Done

### Code Complete
- [ ] All 10-12 collection functions implemented
- [ ] Union operator fully functional
- [ ] Lambda variable support working
- [ ] SQL translation for all functions (DuckDB + PostgreSQL)
- [ ] No hardcoded values in implementation

### Testing Complete
- [ ] Unit tests: >90% coverage of new code
- [ ] Integration tests passing on both databases
- [ ] Official test suite: 423/934+ tests passing (45.3%+)
- [ ] DuckDB and PostgreSQL within ±2 tests
- [ ] No regressions in existing 373 passing tests
- [ ] Performance overhead <5%

### Documentation Complete
- [ ] All functions have docstrings with examples
- [ ] Architecture docs updated (if needed)
- [ ] Sprint summary report created
- [ ] Lessons learned documented
- [ ] Sprint 016 tasks drafted

### Review Complete
- [ ] Code review by Senior Architect
- [ ] All PR comments addressed
- [ ] Merge conflicts resolved
- [ ] Git history clean (no WIP commits)

---

## Communication Plan

### Daily Standups (Async)
**When**: Every morning, 9 AM
**Format**: Slack/Email update

**Template**:
- Yesterday: What I completed
- Today: What I'm working on
- Blockers: Any impediments

### Weekly Check-ins (Sync)
**When**: End of each week (Friday 2 PM)
**Duration**: 30 minutes
**Attendees**: Junior Dev + Senior Architect

**Agenda**:
- Week review: What shipped
- Next week: What's planned
- Risks: Any concerns
- Support needed: Guidance requests

### Sprint Review (End of Sprint)
**When**: Nov 28, 3 PM
**Duration**: 1 hour
**Attendees**: Full team

**Agenda**:
- Demo new functionality
- Show compliance metrics (39.9% → 45.3%)
- Lessons learned
- Sprint 016 preview

---

## Sprint Retrospective Questions

### What Went Well?
- What did we do well this sprint?
- What infrastructure improvements helped?
- What should we keep doing?

### What Didn't Go Well?
- What blocked progress?
- What took longer than expected?
- What should we stop doing?

### What Should We Improve?
- How can we work more effectively?
- What tools/processes would help?
- What should we start doing?

---

## Success Metrics Tracking

### Daily Tracking
- Tests passing count (target: +50 total)
- Code coverage percentage
- Build status (passing/failing)

### Weekly Tracking
- Compliance percentage trend
- Velocity (planned vs actual)
- Technical debt items created

### Sprint Tracking
- Sprint goal achieved (45.3% reached)
- All tasks completed
- Zero P0/P1 bugs remaining
- Team satisfaction score

---

## Carry-Over to Sprint 016

### Planned Carry-Over (if needed)
- Advanced lambda variables (`$total`, `$index`) - deferred to Sprint 016
- Performance optimizations - defer if <10% overhead
- Nice-to-have collection functions - defer to Sprint 016

### Unplanned Carry-Over (minimize)
- Any incomplete tasks from Week 4
- Critical bugs discovered in testing
- Technical debt requiring immediate attention

**Goal**: Minimize carry-over to <5% of sprint capacity

---

## Resources

### Documentation
- FHIRPath Specification: http://hl7.org/fhirpath/
- Collection operators: FHIRPath spec section 5.6
- Official test suite: tests/fixtures/FHIRPath-R4/tests-fhir-r4.xml

### Tools
- DuckDB documentation: https://duckdb.org/docs/
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/functions-json.html
- Python unittest: Standard library

### Support
- Senior Architect: Available for pairing, code review, unblocking
- Documentation: project-docs/architecture/
- Templates: project-docs/plans/templates/

---

## Approval

**Sprint Plan Approved By**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-29
**Sprint Status**: READY TO START
**Next Action**: Create detailed task documents for each week

---

**Sprint 015 Plan Created**: 2025-10-29
**Author**: Senior Solution Architect/Engineer
**Status**: Approved - Ready for Kickoff
**Next Review**: End of Week 1 (Nov 7)
