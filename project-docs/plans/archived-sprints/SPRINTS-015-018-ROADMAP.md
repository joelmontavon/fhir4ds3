# FHIRPath Compliance Roadmap: Sprints 015-018

**Goal**: Increase FHIRPath compliance from 39.9% to 70%
**Timeline**: 16 weeks (4 sprints @ 4 weeks each)
**Current Baseline**: 373/934 tests (39.9%)
**Target**: 654/934 tests (70.0%)
**Required Improvement**: +281 tests

---

## Executive Summary

This roadmap outlines a systematic approach to achieving 70% FHIRPath specification compliance over the next 4 sprints. Each sprint focuses on high-impact feature categories that will incrementally improve our test pass rate.

### Sprint Overview

| Sprint | Focus Area | Target Tests | Compliance | Effort | Duration |
|--------|-----------|--------------|------------|--------|----------|
| **015** | Collection Functions (Phase 1) | +50 tests | 45.3% (423/934) | 40-50h | 4 weeks |
| **016** | Arithmetic & String Functions | +65 tests | 52.2% (488/934) | 40-50h | 4 weeks |
| **017** | Type SQL Translation & Tree Nav | +90 tests | 61.9% (578/934) | 50-60h | 4 weeks |
| **018** | Collection Phase 2 & Remaining | +76 tests | 70.0% (654/934) | 40-50h | 4 weeks |

**Total Effort**: 170-210 hours over 16 weeks
**Risk Buffer**: 10-15% contingency for unexpected complexity

---

## Sprint 015: Collection Functions Foundation (45% Target)

**Duration**: 4 weeks
**Effort**: 40-50 hours
**Starting Point**: 373/934 tests (39.9%)
**Target**: 423/934 tests (45.3%)
**Expected Gain**: +50 tests

### Focus: High-Impact Collection Operations

Collection functions represent the **largest test category** (141 tests) with only 19.1% passing. Implementing core collection operations will provide maximum ROI.

### Sprint 015 Tasks

#### Week 1: Union Operator (SP-015-001)
**Priority**: CRITICAL
**Effort**: 12-15 hours
**Expected**: +15-20 tests

**Scope**:
- Implement `|` (union) operator for combining collections
- SQL translation for both DuckDB and PostgreSQL
- Handle duplicates (union preserves duplicates per FHIRPath spec)
- Support for mixed types

**Deliverables**:
- Union operator in SQL translator
- Dialect-specific SQL generation
- Comprehensive unit tests
- Integration with official test suite

**Why First**: Union operator (`|`) is used extensively in test suite and blocks many other tests.

#### Week 2: Distinct and Set Operations (SP-015-002)
**Priority**: HIGH
**Effort**: 12-15 hours
**Expected**: +20-25 tests

**Scope**:
- Implement `distinct()` function - remove duplicates
- Implement `isDistinct()` function - check for duplicates
- Implement `intersect()` - set intersection
- Implement `exclude()` - set difference

**Deliverables**:
- Four collection functions with SQL translation
- Proper handling of complex types (not just primitives)
- Performance optimization for large collections
- Tests for edge cases (empty collections, single items)

**Why Second**: Builds on union operator, high test coverage impact.

#### Week 3: Navigation Functions (SP-015-003)
**Priority**: MEDIUM
**Effort**: 8-10 hours
**Expected**: +10-12 tests

**Scope**:
- Implement `last()` function - get last element
- Implement `tail()` function - all except first
- Enhance `first()` function (may already exist, validate)
- Implement `skip(n)` and `take(n)` functions

**Deliverables**:
- Five navigation functions
- SQL translation with LIMIT/OFFSET support
- Index-based access optimization
- Boundary condition handling

**Why Third**: Moderate complexity, builds test foundation.

#### Week 4: Testing and Refinement (SP-015-004)
**Priority**: HIGH
**Effort**: 8-10 hours
**Expected**: +5 tests (catch-up)

**Scope**:
- Run full official test suite on DuckDB and PostgreSQL
- Fix any regressions from new implementations
- Performance benchmarking (ensure <10% overhead)
- Documentation and code review

**Deliverables**:
- Sprint 015 summary report
- Compliance validation (45%+ achieved)
- Performance report
- Lessons learned document

**Acceptance Criteria**:
- [ ] 423/934 tests passing (45.3% minimum)
- [ ] DuckDB and PostgreSQL within ±2 tests
- [ ] No regressions in previously passing tests
- [ ] All unit tests passing
- [ ] Performance impact <10%

---

## Sprint 016: Operators and String Functions (52% Target)

**Duration**: 4 weeks
**Effort**: 40-50 hours
**Starting Point**: 423/934 tests (45.3%)
**Target**: 488/934 tests (52.2%)
**Expected Gain**: +65 tests

### Focus: Arithmetic Operators and String Manipulation

Two categories with significant gaps and moderate implementation complexity.

### Sprint 016 Tasks

#### Week 1: Arithmetic Operators (SP-016-001)
**Priority**: HIGH
**Effort**: 12-15 hours
**Expected**: +35-40 tests

**Scope**:
- Implement unary operators: `-x` (negation), `+x` (positive)
- Implement `mod` operator (modulo)
- Implement `div` operator (integer division)
- Fix operator precedence handling
- Support for Quantity arithmetic (5 mg + 3 mg)

**Deliverables**:
- Four new operators with SQL translation
- Operator precedence parser updates
- Quantity type arithmetic support
- Comprehensive operator combination tests

**Why First**: High test volume (72 tests), clear specification, SQL-friendly.

#### Week 2: String Functions Phase 1 (SP-016-002)
**Priority**: MEDIUM
**Effort**: 10-12 hours
**Expected**: +15-18 tests

**Scope**:
- Implement `upper()` - convert to uppercase
- Implement `lower()` - convert to lowercase
- Implement `trim()` - remove whitespace
- Implement `toChars()` - string to character array

**Deliverables**:
- Four string functions with SQL translation
- Unicode handling (UTF-8 support)
- Empty string and NULL edge cases
- Cross-database consistency validation

**Why Second**: Straightforward SQL mappings, quick wins.

#### Week 3: String Functions Phase 2 (SP-016-003)
**Priority**: MEDIUM
**Effort**: 10-12 hours
**Expected**: +10-12 tests

**Scope**:
- Implement `encode(type)` - base64, hex encoding
- Implement `decode(type)` - base64, hex decoding
- Implement `escape(type)` - HTML, JSON escaping
- Implement `unescape(type)` - HTML, JSON unescaping

**Deliverables**:
- Four encoding/escaping functions
- Support for multiple encoding types
- Proper error handling for invalid input
- Security considerations documented

**Why Third**: Lower priority but fills out string function coverage.

#### Week 4: Testing and Integration (SP-016-004)
**Priority**: HIGH
**Effort**: 8-10 hours
**Expected**: +5 tests (refinement)

**Scope**:
- Full test suite validation
- Performance benchmarking
- Cross-database consistency checks
- Documentation updates

**Acceptance Criteria**:
- [ ] 488/934 tests passing (52.2% minimum)
- [ ] Arithmetic operators working correctly
- [ ] String functions handle Unicode
- [ ] No performance regressions
- [ ] Both databases consistent

---

## Sprint 017: Type Translation and Tree Navigation (62% Target)

**Duration**: 4 weeks
**Effort**: 50-60 hours
**Starting Point**: 488/934 tests (52.2%)
**Target**: 578/934 tests (61.9%)
**Expected Gain**: +90 tests

### Focus: SQL Translation for Type Functions and Tree Navigation

This sprint addresses two architectural gaps: type functions need SQL translation (currently Python-only) and tree navigation functions are missing.

### Sprint 017 Tasks

#### Week 1-2: Type Function SQL Translation (SP-017-001)
**Priority**: HIGH
**Effort**: 20-25 hours
**Expected**: +50-60 tests

**Scope**:
- Add SQL translation for `toDecimal()`, `convertsToDecimal()`
- Add SQL translation for `toQuantity()`, `convertsToQuantity()`
- Add SQL translation for `toDate()`, `convertsToDate()`
- Add SQL translation for `toDateTime()`, `convertsToDateTime()`
- Add SQL translation for `toTime()`, `convertsToTime()`
- Add SQL translation for `toInteger()`, `convertsToInteger()`

**Deliverables**:
- SQL translation layer for all type conversion functions
- Dialect-specific implementations (DuckDB CAST vs PostgreSQL ::)
- Validation and error handling in SQL
- Migration from Python-only to SQL-first with Python fallback

**Why First**: Unlocks 89 remaining type function tests, significant impact.

**Technical Approach**:
```sql
-- Example: toDecimal() SQL translation
-- DuckDB: CAST(value AS DECIMAL)
-- PostgreSQL: value::DECIMAL

-- convertsToDecimal() SQL translation
-- Try CAST, return true/false based on success
CASE
    WHEN value ~ '^-?[0-9]+(\.[0-9]+)?$' THEN true
    ELSE false
END
```

#### Week 3: Tree Navigation Functions (SP-017-002)
**Priority**: MEDIUM
**Effort**: 12-15 hours
**Expected**: +20-25 tests

**Scope**:
- Implement `children()` - get child elements of FHIR resource
- Implement `descendants()` - get all descendants recursively
- Optimize for FHIR JSON structure traversal
- Handle circular references (if applicable)

**Deliverables**:
- Two tree navigation functions
- Efficient SQL for nested JSON traversal
- Recursive CTE for descendants (PostgreSQL)
- JSON path enumeration for children

**Why Second**: Moderate complexity, important for FHIR navigation patterns.

**Technical Approach**:
```sql
-- children() - extract all direct child properties
-- Requires JSON introspection and expansion
WITH children AS (
    SELECT jsonb_object_keys(resource) as child_key
    FROM resource_table
)
SELECT resource->child_key as child_value FROM children

-- descendants() - recursive JSON traversal
-- Use recursive CTE to walk entire JSON tree
```

#### Week 4: Aggregate and Advanced Functions (SP-017-003)
**Priority**: MEDIUM
**Effort**: 12-15 hours
**Expected**: +15-20 tests

**Scope**:
- Implement `aggregate($accumulator, $init)` - custom aggregation
- Implement `combine()` - union that preserves duplicates
- Enhance `single()` - validation function
- Add trace() function for debugging (if not done)

**Deliverables**:
- Three collection aggregation functions
- Support for lambda expressions in aggregate
- Error handling for invalid aggregations
- Performance optimization

**Acceptance Criteria**:
- [ ] 578/934 tests passing (61.9% minimum)
- [ ] Type functions working in SQL
- [ ] Tree navigation efficient
- [ ] Aggregate functions tested extensively
- [ ] Documentation complete

---

## Sprint 018: Final Push to 70% (70% Target)

**Duration**: 4 weeks
**Effort**: 40-50 hours
**Starting Point**: 578/934 tests (61.9%)
**Target**: 654/934 tests (70.0%)
**Expected Gain**: +76 tests

### Focus: Complete Collection Functions and Fill Gaps

Final sprint to reach 70% milestone by completing remaining collection functions and addressing miscellaneous gaps.

### Sprint 018 Tasks

#### Week 1: Remaining Collection Functions (SP-018-001)
**Priority**: HIGH
**Effort**: 12-15 hours
**Expected**: +30-35 tests

**Scope**:
- Implement `subsetOf()` - check if collection is subset
- Implement `supersetOf()` - check if collection is superset
- Implement `sort($lambda)` - custom sorting
- Enhance `union()` if needed for complex cases
- Implement `count()` variations if missing

**Deliverables**:
- Five collection comparison and manipulation functions
- Lambda expression support for sort
- Proper type comparison (especially for Quantity, Date)
- Edge case handling

**Why First**: Fills out collection function coverage to ~80%+.

#### Week 2: DateTime and Boolean Functions (SP-018-002)
**Priority**: MEDIUM
**Effort**: 10-12 hours
**Expected**: +10-12 tests

**Scope**:
- Implement `today()` - current date
- Implement `now()` - current datetime
- Implement `timeOfDay()` - current time
- Fix boolean operators (`and`, `or`, `xor`, `implies`) if broken
- Add short-circuit evaluation for boolean operators

**Deliverables**:
- Three datetime functions
- Boolean operator fixes/enhancements
- Timezone handling (if applicable)
- SQL translation for datetime functions

**Why Second**: Small categories but fills important gaps.

#### Week 3: Edge Cases and Refinement (SP-018-003)
**Priority**: MEDIUM
**Effort**: 10-12 hours
**Expected**: +20-25 tests

**Scope**:
- Fix failing tests in existing categories
- Address operator precedence issues
- Improve error handling for invalid expressions
- Optimize performance bottlenecks
- Add missing string functions if any

**Deliverables**:
- Bug fixes for edge cases
- Performance improvements
- Better error messages
- Compliance report showing progress

**Why Third**: Catch-up and refinement to ensure we hit 70%.

#### Week 4: Final Validation and Documentation (SP-018-004)
**Priority**: HIGH
**Effort**: 8-10 hours
**Expected**: +5-10 tests (final refinement)

**Scope**:
- Run full test suite 5 times for stability
- Validate DuckDB and PostgreSQL parity
- Performance benchmarking report
- Update all architectural documentation
- Create compliance summary report

**Deliverables**:
- 70% compliance validation report
- Performance comparison (baseline vs final)
- Architecture documentation updates
- Sprint 018 completion summary
- Roadmap for 70% → 85% (if desired)

**Acceptance Criteria**:
- [ ] 654/934 tests passing (70.0% minimum, stretch: 75%)
- [ ] DuckDB and PostgreSQL within ±3 tests
- [ ] Performance within 15% of Sprint 015 baseline
- [ ] All unit tests passing (2000+ tests)
- [ ] Documentation complete and reviewed
- [ ] Architecture compliance validated

---

## Cross-Sprint Themes

### Architecture Compliance

**All work must maintain**:
- ✅ Thin dialect architecture (syntax-only in dialects)
- ✅ SQL-first execution (Python only for scalar operations)
- ✅ Population-scale design (no row-by-row processing)
- ✅ CTE-based query generation
- ✅ DuckDB and PostgreSQL parity

### Testing Standards

**Every sprint must include**:
- Comprehensive unit tests (>90% coverage)
- Integration tests on both databases
- Official test suite validation
- Performance benchmarking
- Regression testing

### Code Quality

**All code must meet**:
- Type hints on all functions
- Docstrings with examples
- Error handling with clear messages
- No hardcoded values
- Follows coding standards

### Documentation

**Each sprint must deliver**:
- Updated architecture docs
- Implementation summaries
- Lessons learned
- Performance reports
- Compliance tracking

---

## Risk Management

### Technical Risks

| Risk | Mitigation |
|------|------------|
| **SQL translation complexity** | Start with simple cases, iterate to complex |
| **Performance degradation** | Benchmark continuously, optimize early |
| **Database dialect divergence** | Test both databases every sprint |
| **Lambda expression support** | May need Python fallback for complex cases |
| **Recursive function limits** | Set reasonable recursion depth limits |

### Schedule Risks

| Risk | Mitigation |
|------|------------|
| **Underestimated complexity** | 10-15% buffer in estimates |
| **Scope creep** | Strict sprint boundaries, defer nice-to-haves |
| **Technical debt** | Allocate 10% of each sprint to refactoring |
| **Testing time** | Include testing in estimates, not afterthought |

### Resource Risks

| Risk | Mitigation |
|------|------------|
| **Developer availability** | Realistic 25-30h/week estimates |
| **Burnout** | 4-week sprints allow sustainable pace |
| **Knowledge gaps** | Pair programming for complex topics |
| **Context switching** | Focus on one feature category per week |

---

## Success Metrics

### Quantitative Goals

| Metric | Sprint 015 | Sprint 016 | Sprint 017 | Sprint 018 |
|--------|-----------|-----------|-----------|-----------|
| **Compliance %** | 45.3% | 52.2% | 61.9% | 70.0% |
| **Tests Passing** | 423/934 | 488/934 | 578/934 | 654/934 |
| **New Functions** | 10-12 | 8-10 | 12-15 | 8-10 |
| **Performance** | <5% overhead | <10% total | <15% total | <15% final |

### Qualitative Goals

- **Architecture Integrity**: All code follows unified FHIRPath architecture
- **Code Quality**: >90% test coverage, clear documentation
- **Maintainability**: Future developers can understand and extend
- **Production Ready**: Both DuckDB and PostgreSQL deployable

---

## Milestone Celebrations

### Sprint 015: 45% Milestone 🎯
**Achievement**: Collection functions foundation
**Impact**: Major functionality unlocked for FHIR navigation

### Sprint 016: 50% Milestone 🎉
**Achievement**: Half of FHIRPath specification implemented
**Impact**: Core operations complete, production-viable

### Sprint 017: 60% Milestone 🚀
**Achievement**: Type system complete, tree navigation working
**Impact**: Advanced FHIR querying capabilities

### Sprint 018: 70% Milestone 🏆
**Achievement**: 70% FHIRPath compliance
**Impact**: Industry-leading FHIR analytics platform

---

## Post-70% Roadmap (Optional)

If 70% is achieved ahead of schedule or stakeholders want to continue:

### Sprint 019-020: 70% → 85% (Stretch Goal)

**Focus Areas**:
- Remaining collection functions (100% of 141 tests)
- Path navigation enhancements
- Comments and syntax edge cases
- Error handling improvements
- Type system completeness

**Effort**: 60-80 hours over 8 weeks
**Target**: 794/934 tests (85%)

### Sprint 021+: 85% → 95% (Ambitious)

**Focus Areas**:
- Complex lambda expressions
- Advanced type coercion
- Specification edge cases
- Performance optimization
- Production hardening

**Effort**: 80-100 hours
**Target**: 887/934 tests (95%)

**Note**: Achieving 95%+ requires addressing specification ambiguities and edge cases that may have minimal practical impact.

---

## Dependency Chain

### Sprint Dependencies

```
Sprint 015 → Sprint 016: Union operator needed for arithmetic tests
Sprint 016 → Sprint 017: Operators needed for type conversion
Sprint 017 → Sprint 018: Type functions needed for collections
```

### Task Dependencies Within Sprints

**Sprint 015**:
- Week 1 (Union) → Week 2 (Set operations) → Week 3 (Navigation)

**Sprint 016**:
- Week 1 (Arithmetic) → Week 2 (Strings Phase 1) → Week 3 (Strings Phase 2)

**Sprint 017**:
- Week 1-2 (Type SQL) → Week 3 (Tree Nav) → Week 4 (Aggregate)

**Sprint 018**:
- Week 1 (Collections) → Week 2 (DateTime/Boolean) → Week 3 (Refinement)

---

## Resource Allocation

### Developer Effort

**Recommended**: 1 junior developer + 1 senior architect (advisory)

**Junior Developer** (25-30h/week):
- Implementation (60%)
- Testing (25%)
- Documentation (10%)
- Meetings/Planning (5%)

**Senior Architect** (5-10h/week):
- Code review (40%)
- Architecture guidance (30%)
- Unblocking (20%)
- Sprint planning (10%)

### Tools and Infrastructure

**Required**:
- DuckDB (local development)
- PostgreSQL instance (testing)
- CI/CD pipeline (automated testing)
- Performance monitoring
- Documentation platform

---

## Communication Plan

### Weekly Status Updates

**Every Monday**:
- Progress report (tests passing, tasks completed)
- Blockers and risks
- Plan for current week

### Sprint Reviews

**End of Each Sprint**:
- Demo of new functionality
- Compliance report
- Lessons learned
- Next sprint kickoff

### Stakeholder Updates

**Monthly**:
- Progress toward 70% goal
- Milestone achievements
- Risk assessment
- Timeline confidence

---

## Contingency Plans

### If We Fall Behind

**Option 1**: Reduce scope of current sprint
- Focus on highest-impact features only
- Defer nice-to-haves to later sprints
- Maintain quality over quantity

**Option 2**: Extend timeline
- Add 1-2 week buffer to problematic sprints
- Revise overall 70% target date
- Communicate proactively to stakeholders

**Option 3**: Increase resources
- Add second junior developer
- Pair programming for complex features
- External consultant for specialized topics

### If We Get Ahead

**Option 1**: Pull work from future sprints
- Accelerate collection function completion
- Start type SQL translation early
- Bank time for unexpected complexity

**Option 2**: Improve quality
- Refactor existing code
- Enhance performance
- Improve documentation and examples

**Option 3**: Stretch to 75-80%
- Continue momentum toward higher compliance
- Tackle harder specification areas
- Build buffer for maintenance

---

## Conclusion

This roadmap provides a clear, systematic path from 39.9% to 70% FHIRPath compliance over 16 weeks. Each sprint builds on the previous one, with realistic goals and built-in contingencies.

**Key Success Factors**:
1. Focus on high-impact categories first (collections, operators)
2. Maintain architecture integrity throughout
3. Test continuously on both databases
4. Document thoroughly for maintainability
5. Celebrate milestones to maintain momentum

**Commitment Required**:
- 170-210 hours of development effort
- 30-40 hours of senior architect time
- 16 weeks of sustained focus
- Quality over speed

**Expected Outcome**: Industry-leading FHIRPath analytics platform with 70% specification compliance, production-ready for both DuckDB and PostgreSQL environments.

---

**Roadmap Created**: 2025-10-29
**Author**: Senior Solution Architect/Engineer
**Status**: APPROVED - Ready for Sprint 015 Kickoff
**Next Review**: End of Sprint 015 (Week 4)
