# Sprint 011: PEP-004 CTE Infrastructure Implementation

**Sprint**: Sprint 011 - CTE Infrastructure for Population-Scale FHIRPath Execution
**Duration**: 2025-10-21 to 2025-11-15 (4 weeks, 25 days)
**Sprint Lead**: Senior Solution Architect/Engineer
**Developer**: Junior Developer
**PEP**: PEP-004 (Accepted 2025-10-19)

---

## Sprint Goals

### Primary Objectives
1. **Implement CTE Infrastructure**: Complete CTEBuilder and CTEAssembler components as specified in PEP-004
2. **Unblock Path Navigation**: Enable 8/10 Path Navigation tests (from 0/9 currently)
3. **Achieve 72%+ Overall Compliance**: Reach Sprint 010 target through architectural completion
4. **Complete Execution Pipeline**: Fill critical gap between Translator (PEP-003) and Database Execution

### Success Criteria
- [ ] CTEBuilder component complete with 100% unit tests passing
- [ ] CTEAssembler component complete with 100% unit tests passing
- [ ] LATERAL UNNEST support for DuckDB and PostgreSQL
- [ ] Path Navigation tests: 8/10 minimum (80%+)
- [ ] Overall FHIRPath compliance: 72%+ (from 36-65% baseline)
- [ ] Zero regressions in existing functionality
- [ ] 90%+ test coverage for new CTE infrastructure code
- [ ] Architecture compliance: 100% (thin dialects, population-first)
- [ ] Multi-database parity: 100% (DuckDB and PostgreSQL identical behavior)

### Alignment with Architecture Goals
This sprint **completes the documented 5-layer FHIRPath execution pipeline**:
1. Parser (PEP-002) ✅ Complete
2. Translator (PEP-003) ✅ Complete
3. **CTE Builder (PEP-004)** ← **THIS SPRINT**
4. **CTE Assembler (PEP-004)** ← **THIS SPRINT**
5. Database Execution ✅ Complete

**Architectural Impact**: Unblocks 60-70% of Path Navigation functionality, enables population-scale analytics (10x+ performance improvements), and provides foundation for SQL-on-FHIR and CQL implementations.

---

## Task Breakdown

### Week 1: Phase 1 - CTE Data Structures (Days 1-6)

**Goal**: Establish CTE data structures and class scaffolding

| Task ID | Task Name | Assignee | Estimate | Status | Success Criteria |
|---------|-----------|----------|----------|--------|------------------|
| SP-011-001 | Create CTE dataclass and module structure | Junior Dev | 8h | ✅ **Completed** (2025-10-19) | ✅ CTE dataclass with all fields, comprehensive docstrings, merged to main |
| SP-011-002 | Implement CTEBuilder class structure | Junior Dev | 10h | ✅ **Completed** (2025-10-20) | ✅ CTEBuilder class implemented, 6 unit tests passing, 100% architecture compliance, merged to main |
| SP-011-003 | Implement CTEAssembler class structure | Junior Dev | 10h | ✅ **Completed** (2025-10-20) | ✅ CTEAssembler class implemented, architecture review approved, merged to main |
| SP-011-004 | Unit tests for CTE data structures | Junior Dev | 12h | ✅ **Completed** (2025-10-20) | ✅ 69 unit tests passing, 99% coverage, 0.84s execution, merged to main |

**Phase 1 Deliverable**: CTE data structures with comprehensive unit tests
**Success Metric**: 50+ tests passing, architecture review approved

---

### Week 2: Phase 2 - Array UNNEST Support (Days 7-12)

**Goal**: Implement LATERAL UNNEST for array flattening

| Task ID | Task Name | Assignee | Estimate | Status | Dependencies | Success Criteria |
|---------|-----------|----------|----------|--------|--------------|------------------|
| SP-011-005 | Implement `_wrap_unnest_query()` in CTEBuilder | Junior Dev | 12h | ✅ **Completed and merged** (2025-10-20) | SP-011-002 | ✅ UNNEST query generation working, approved by senior architect |
| SP-011-006 | Add `generate_lateral_unnest()` to DuckDB dialect | Junior Dev | 5h | ✅ **Completed and merged** (2025-10-20) | SP-011-005 | ✅ DuckDB UNNEST syntax correct, 96 tests passing, approved |
| SP-011-007 | Add `generate_lateral_unnest()` to PostgreSQL dialect | Junior Dev | 8h | ✅ **Completed and merged** (2025-10-20) | SP-011-005 | ✅ PostgreSQL UNNEST syntax correct, 96 tests passing, approved ⭐⭐⭐⭐⭐ (5/5) |
| SP-011-008 | Unit tests for UNNEST generation and integration | Junior Dev | 12h | 🟡 Pending Review | SP-011-005, SP-011-006, SP-011-007 | 70+ tests passing, both dialects validated |

**Phase 2 Deliverable**: Array flattening capability for both databases
**Success Metric**: 40+ tests passing, integration with PEP-003 translator validated

---

### Week 3: Phase 3 - CTE Assembly and Dependencies (Days 13-18)

**Goal**: Complete CTE assembly with dependency resolution

| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|----------|--------------|------------------|
| SP-011-009 | Implement topological sort for CTE dependencies | Junior Dev | 10h | SP-011-003 | Dependency ordering working, circular detection implemented |
| SP-011-010 | Implement `_generate_with_clause()` | Junior Dev | 8h | SP-011-009 | WITH clause generation working for multiple CTEs |
| SP-011-011 | Implement `_generate_final_select()` | Junior Dev | 6h | SP-011-010 | Final SELECT generation working |
| SP-011-012 | Unit tests for assembly logic and integration | Junior Dev | 16h | SP-011-009, SP-011-010, SP-011-011 | 50+ tests passing, real FHIRPath expressions execute |

**Status Update (2025-10-20)**:
- SP-011-011 implemented and in review; final SELECT generation, doc updates, and 6 unit tests completed.

**Status Update (2025-10-21)**:
- SP-011-012 completed; 200-unit test suite in place with 100% coverage, awaiting senior architect review.

**Status Update (2025-11-01)**:
- SP-011-014 executed curated Path Navigation compliance runner via FHIRPathExecutor; 10/10 tests passing on DuckDB and PostgreSQL with report filed.

**Phase 3 Deliverable**: Complete CTE assembly with dependency resolution
**Success Metric**: 50+ tests passing, end-to-end FHIRPath expression execution working

---

### Week 4: Phase 4 - Integration, Testing, Documentation (Days 19-25)

**Goal**: Production-ready CTE infrastructure with comprehensive validation

| Task ID | Task Name | Assignee | Estimate | Status | Dependencies | Success Criteria |
|---------|-----------|----------|----------|--------|--------------|------------------|
| SP-011-013 | End-to-end integration with PEP-003 translator (scalar paths) | Junior Dev | 10h | ✅ **Completed - Pending Review** (2025-10-21 refresh) | SP-011-012 | ✅ Scalar + array execution (10/10 expressions), multi-database parity tests refreshed, 100% test coverage |
| SP-011-017 | Complete array navigation integration (translator array detection) | Junior Dev | 9h | ✅ **Completed and merged** (2025-10-31) | SP-011-013 | ✅ Array navigation (10/10 expressions), 5/5 review rating, 100% multi-db parity |
| SP-011-014 | Validate against official FHIRPath test suite | Junior Dev | 8h | ✅ **Completed - Pending Review** (2025-11-01) | SP-011-017 | 10/10 Path Navigation tests passing, compliance report published |
| SP-011-015 | Performance benchmarking and optimization | Junior Dev | 8h | Pending | SP-011-013 | <10ms CTE generation, 10x+ execution improvement |
| SP-011-016 | API documentation and architecture docs updates | Junior Dev | 12h | ✅ Completed – pending review | SP-011-013 | Complete API docs, architecture diagrams, usage examples |

**Phase 4 Deliverable**: Production-ready CTE infrastructure
**Success Metric**: 8/10 Path Navigation tests, 72%+ overall compliance, documentation complete

---

## Compliance Focus Areas

### Target Specifications
- **FHIRPath R4 Path Navigation**: 0% (0/9) → 80%+ (8/10) - **PRIMARY TARGET**
- **FHIRPath R4 Overall**: 36-65% → 72%+ - **Sprint Goal**
- **SQL-on-FHIR Foundation**: Not started → Ready for implementation (architecture complete)
- **CQL Foundation**: Not started → Ready for implementation (architecture complete)

### Compliance Activities
1. **Path Navigation Implementation**: Enable array-based path expressions (`Patient.name.given`)
2. **Array Flattening**: LATERAL UNNEST support for nested arrays
3. **Population-Scale Queries**: Monolithic CTE generation for 10x+ performance
4. **Official Test Suite Validation**: Execute all 10 Path Navigation tests

### Compliance Metrics
- **Test Suite Execution**: Daily execution of Path Navigation tests during Phases 3-4
- **Performance Benchmarks**: CTE generation <10ms, execution 10x+ improvement
- **Regression Prevention**: Full official test suite execution before completion

---

## Technical Focus

### Architecture Components
**Primary Components**: CTE Infrastructure (Layers 3 & 4 of execution pipeline)
- **CTEBuilder**: Wraps SQL fragments in CTE structures with UNNEST support
- **CTEAssembler**: Combines CTEs into monolithic queries with dependency ordering
- **Dialect Extensions**: `generate_lateral_unnest()` for DuckDB and PostgreSQL

### Database Dialects
- **DuckDB**: LATERAL UNNEST syntax (`LATERAL UNNEST(array) AS item`)
- **PostgreSQL**: LATERAL UNNEST syntax (`LATERAL jsonb_array_elements(array) AS item`)
- **Architecture Requirement**: ONLY syntax differences, ZERO business logic in dialects

### Integration Points
- **PEP-003 Translator**: Consumes `List[SQLFragment]` output
- **Database Execution Layer**: Produces executable SQL strings
- **Type Registry**: Uses StructureDefinition metadata for array detection

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| UNNEST syntax complexity across dialects | Medium | Medium | Use dialect methods, comprehensive testing, senior review |
| CTE dependency ordering edge cases | Low | Medium | Standard topological sort algorithm, cycle detection |
| Integration with PEP-003 output format | Low | High | PEP-003 already outputs SQLFragment structure (verified) |
| Performance of CTE generation | Low | Medium | Benchmarking throughout, <10ms target is reasonable |
| Path Navigation test complexity | Medium | High | Focus on 8/10 tests minimum, defer 2 edge cases if needed |

### Dependencies and Blockers
1. **PEP-003 Translator**: ✅ Complete (no changes needed)
2. **StructureDefinition Loader**: ✅ Complete (SP-009-033)
3. **Multi-Database Test Environment**: ✅ Available (DuckDB and PostgreSQL)
4. **Official FHIRPath Test Suite**: ✅ Available

### Contingency Plans
- **If Phase 1 extends beyond Week 1**: Compress Phase 2 by 1-2 days, maintain critical path
- **If UNNEST complexity blocks progress**: Implement DuckDB first, PostgreSQL as Phase 2.5
- **If Path Navigation only achieves 7/10**: Still acceptable if overall 70%+ compliance reached
- **If performance targets not met**: Document in PEP implementation summary, optimize in Sprint 012

---

## Testing Strategy

### Unit Testing
- **Coverage Target**: 90%+ for all new CTE infrastructure code
- **New Test Requirements**:
  - Phase 1: 50+ tests for CTE data structures
  - Phase 2: 40+ tests for UNNEST generation
  - Phase 3: 50+ tests for assembly logic
  - Total: 140+ new unit tests
- **Test Enhancement**: Integration with PEP-003 translator output

### Integration Testing
- **Database Testing**: All tests must pass on both DuckDB and PostgreSQL
- **End-to-End Testing**: All 10 Path Navigation FHIRPath expressions
- **Performance Testing**: CTE generation <10ms, query execution 10x+ improvement

### Compliance Testing
- **Official Test Suites**: Path Navigation category (10 tests) - target 8/10 minimum
- **Regression Testing**: Full official test suite execution (all categories) before completion
- **Custom Test Development**: Array flattening edge cases, nested UNNEST scenarios

---

## Definition of Done

### Code Quality Requirements
- [ ] All code passes lint and format checks
- [ ] Unit test coverage ≥90% for CTE infrastructure code
- [ ] All 140+ unit tests pass in both DuckDB and PostgreSQL
- [ ] Code review completed and approved by Senior Solution Architect/Engineer
- [ ] Documentation updated for all CTE infrastructure components

### Compliance Requirements
- [ ] Path Navigation: 8/10 tests passing (80%+ minimum)
- [ ] Overall FHIRPath compliance: 72%+ (Sprint 010 target achieved)
- [ ] No regression in existing compliance levels (607+ tests still passing)
- [ ] Performance: CTE generation <10ms, execution 10x+ improvement validated

### Architecture Requirements
- [ ] Thin dialects maintained: ZERO business logic in dialect classes
- [ ] Population-first design: All CTE operations population-scale capable
- [ ] Multi-database parity: 100% identical behavior (DuckDB and PostgreSQL)
- [ ] Architecture review approved: Senior architect verification complete

### Documentation Requirements
- [ ] API documentation complete for CTEBuilder, CTEAssembler, CTE dataclass
- [ ] Architecture documentation updated with CTE infrastructure diagrams
- [ ] Integration guide created for using CTE infrastructure with PEP-003
- [ ] Sprint completion documentation with metrics and lessons learned

---

## Communication Plan

### Daily Updates
- **Format**: Brief status update in project documentation
- **Content**: Current task progress, blockers encountered, test results
- **Timing**: End of each development day

### Weekly Reviews
- **Schedule**: End of each week (Weeks 1-4)
- **Participants**: Senior Solution Architect/Engineer, Junior Developer
- **Agenda**:
  - Week 1: Phase 1 review, architecture compliance verification
  - Week 2: Phase 2 review, UNNEST validation, multi-database testing
  - Week 3: Phase 3 review, end-to-end expression execution validation
  - Week 4: Phase 4 review, compliance verification, sprint completion

### Sprint Ceremonies
- **Sprint Planning**: 2025-10-21 (Day 1) - 2 hours
- **Mid-Sprint Check-in**: 2025-11-01 (Day 11) - 1 hour
- **Sprint Review**: 2025-11-14 (Day 24) - 2 hours
- **Sprint Retrospective**: 2025-11-15 (Day 25) - 1 hour

---

## Resource Requirements

### Development Environment
- **Database Access**: DuckDB (embedded) and PostgreSQL (localhost:5432) with FHIR test data
- **Testing Infrastructure**: pytest framework, performance benchmarking tools
- **Development Tools**: Python 3.10+, VS Code, Git

### External Dependencies
- **PEP-003 Output**: SQLFragment structures (dependency satisfied - PEP-003 complete)
- **StructureDefinition Metadata**: Type information (dependency satisfied - SP-009-033 complete)
- **Official FHIRPath Tests**: Path Navigation category tests (available)

---

## Success Measurement

### Quantitative Metrics
- **Task Completion Rate**: Target 100% (16/16 tasks)
- **Test Coverage**: Target 90%+ for new code
- **Compliance Improvement**: Path Navigation 0% → 80%+, Overall 65% → 72%+
- **Performance**: CTE generation <10ms (target), execution 10x+ improvement

### Qualitative Assessments
- **Code Quality**: Clean, maintainable, well-documented CTE infrastructure
- **Architecture Alignment**: 100% compliance with thin dialects, population-first design
- **Knowledge Transfer**: Junior developer gains expertise in CTE generation patterns
- **Process Improvement**: Identify opportunities for future PEP implementation efficiency

---

## Sprint Retrospective Planning

### Areas for Evaluation
1. **What went well**: Phase completion effectiveness, testing strategy success
2. **What could be improved**: Estimation accuracy, integration challenges
3. **Action items**: Process improvements for Sprint 012
4. **Lessons learned**: CTE generation patterns, dialect abstraction best practices

### Retrospective Format
- **Duration**: 1 hour (Day 25)
- **Facilitation**: Senior Solution Architect/Engineer
- **Documentation**: Sprint completion summary document
- **Follow-up**: Action items tracked in Sprint 012 planning

---

## Phase-by-Phase Success Criteria

### Phase 1 Success (End of Week 1)
- [x] CTE dataclass complete with all required fields (SP-011-001 ✅ Completed 2025-10-19)
- [x] CTEBuilder class structure defined and architecture-approved (SP-011-002 ✅ Completed 2025-10-20)
- [x] CTEAssembler class structure defined and architecture-approved (SP-011-003 ✅ Completed 2025-10-20)
- [x] 50+ unit tests passing (SP-011-004 ✅ 69 tests, 99% coverage, 2025-10-20)
- [x] Senior architect code review approved for Phase 1 (✅ All tasks approved 2025-10-20)

**Phase 1 Status**: ✅ **COMPLETE** - All Week 1 quality gate criteria achieved

### Phase 2 Success (End of Week 2)
- [x] LATERAL UNNEST working for DuckDB (SP-011-006 ✅ Completed and merged 2025-10-20)
- [x] LATERAL UNNEST working for PostgreSQL (SP-011-007 ✅ Completed and merged 2025-10-20)
- [x] 40+ additional unit tests passing (90 total) - SP-011-008 pending
- [x] Integration with PEP-003 translator validated (SP-011-005 ✅ Completed and merged 2025-10-20)
- [x] Multi-database consistency confirmed (96/96 tests passing both dialects)

**Phase 2 Status**: 🟢 **READY FOR REVIEW** - Core UNNEST infrastructure and test suite ready; SP-011-008 awaiting senior sign-off

### Phase 3 Success (End of Week 3)
- [ ] Topological sort implemented and tested
- [ ] WITH clause generation working
- [ ] Final SELECT generation working
- [ ] 50+ additional unit tests passing (140 total)
- [ ] Real FHIRPath expressions executing end-to-end

### Phase 4 Success (End of Week 4)
- [ ] Path Navigation: 8/10 tests passing minimum
- [ ] Overall compliance: 72%+ achieved
- [ ] Performance targets met (<10ms CTE generation)
- [ ] Documentation complete
- [ ] Sprint 011 goals achieved

---

**Plan Created**: 2025-10-19
**Last Updated**: 2025-10-20
**Next Review**: 2025-10-21 (Sprint 011 Start)

---

*This sprint plan implements PEP-004 to complete the FHIRPath execution pipeline, unblock path navigation functionality, and achieve the critical 72%+ compliance milestone.*
