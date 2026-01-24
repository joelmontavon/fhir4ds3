# Sprint 010: PEP-004 CTE Infrastructure Implementation (PRIORITY)

**Sprint**: Sprint 010
**Priority**: ⚠️ **CRITICAL - TOP PRIORITY**
**Duration**: 3-4 weeks
**Strategy**: Implement PEP-004 to unblock path navigation and achieve Sprint 010 compliance target

---

## Executive Summary

**Goal**: Implement PEP-004 (CTE Infrastructure) to complete the documented architectural pipeline and unblock 60-70% of Path Navigation functionality.

**Current State**:
- Compliance: 36-65% (below Sprint 010 target of 72%)
- Path Navigation: 0/9 tests (0%) ← **CRITICAL BLOCKER**
- Architectural Gap: Missing CTE infrastructure (Layers 3 & 4)

**Expected Outcome**:
- Compliance: 70-75% (Sprint 010 target achieved)
- Path Navigation: 8/10 tests (80%+)
- Architecture: Complete execution pipeline
- Future Features: Unblocked (SQL-on-FHIR, CQL, quality measures)

---

## Critical Context

### Why PEP-004 is Mandatory

**From Sprint 009 Analysis**:

> "Path Navigation test failures are caused by missing CTE infrastructure (PEP-004), not by missing StructureDefinition metadata. The StructureDefinition metadata from SP-009-033 is available and integrated, but cannot be fully utilized without CTE support."

**Architectural Reality**:
```
Parser (PEP-002) ✅ → Translator (PEP-003) ✅ → ??? ❌ → Database Execution ✅
                                                      ↑
                                         Missing: CTE Infrastructure (PEP-004)
```

**Current Blocker**:
- PEP-003 generates SQL fragments
- No component converts fragments to executable SQL
- Path Navigation requires array flattening via LATERAL UNNEST
- LATERAL UNNEST requires CTE structure
- **Result**: 67% of Path Navigation tests blocked

### Alternatives Considered and Rejected

**Alternative 1: Python-based row-by-row processing (fhirpathpy)**
- ❌ **Rejected**: Violates population-first architecture
- ❌ **Impact**: 100x+ performance degradation
- ❌ **Status**: Explicitly prohibited in architecture docs

**Alternative 2: Workarounds without proper CTE structure**
- ❌ **Rejected**: Creates technical debt
- ❌ **Impact**: Only achieves 30-40% compliance
- ❌ **Status**: Senior architect rejected in SP-010-001 review

**Alternative 3: Defer to later sprint**
- ❌ **Rejected**: Delays critical functionality
- ❌ **Impact**: Sprint 010 goal (72%) unachievable
- ❌ **Status**: Architectural gap remains unfilled

**CONCLUSION**: PEP-004 implementation is **the only acceptable path forward**.

---

## PEP-004 Overview

### Purpose

Implement CTE (Common Table Expression) Infrastructure that transforms SQL fragments from PEP-003 translator into executable, monolithic SQL queries optimized for population-scale healthcare analytics.

### Components

**1. CTEBuilder**:
- Wraps SQL fragments in CTE structures
- Handles LATERAL UNNEST for array flattening
- Generates unique CTE names with dependency tracking

**2. CTEAssembler**:
- Combines CTEs into monolithic SQL queries
- Dependency-ordered WITH clauses
- Final SELECT statement generation

### Example: `Patient.name.given`

**Input** (from PEP-003):
```python
fragments = [
    SQLFragment("json_extract(resource, '$.name')"),
    SQLFragment("... LATERAL UNNEST ...", requires_unnest=True),
    SQLFragment("json_extract(name_item, '$.given')")
]
```

**Processing** (PEP-004):
```python
builder = CTEBuilder(dialect=duckdb_dialect)
ctes = builder.build_cte_chain(fragments)

assembler = CTEAssembler(dialect=duckdb_dialect)
sql = assembler.assemble_query(ctes)
```

**Output** (Executable SQL):
```sql
WITH
  cte_1 AS (
    SELECT id, json_extract(resource, '$.name') as names
    FROM patient_resources
  ),
  cte_2 AS (
    SELECT cte_1.id, name_item
    FROM cte_1, LATERAL UNNEST(cte_1.names) AS name_item
  ),
  cte_3 AS (
    SELECT id, json_extract(name_item, '$.given') as given_array
    FROM cte_2
  )
SELECT * FROM cte_3;
```

**Result**: Population-scale flattened array of all given names from all patients

---

## Sprint 010 Implementation Plan

### Phase 1: CTE Data Structures (Week 1)

**Tasks**:
- Create `fhir4ds/fhirpath/sql/cte.py` module
- Implement `CTE` dataclass (name, query, dependencies, metadata)
- Implement `CTEBuilder` class structure
- Implement `CTEAssembler` class structure
- Unit tests for data structures (50+ test cases)

**Deliverable**: CTE data structures with comprehensive unit tests

**Success Criteria**:
- [ ] CTE dataclass complete with all fields
- [ ] CTEBuilder class structure defined
- [ ] CTEAssembler class structure defined
- [ ] 50+ unit tests passing
- [ ] Documentation for CTE data model

### Phase 2: Array UNNEST Support (Week 2)

**Tasks**:
- Implement `_wrap_unnest_query()` in CTEBuilder
- Add `generate_lateral_unnest()` to dialect interface
- Implement DuckDB UNNEST dialect method
- Implement PostgreSQL UNNEST dialect method
- Unit tests for UNNEST generation (40+ test cases)
- Integration tests with PEP-003 translator output

**Deliverable**: Array flattening capability for both databases

**Success Criteria**:
- [ ] UNNEST query generation working
- [ ] DuckDB dialect method implemented
- [ ] PostgreSQL dialect method implemented
- [ ] 40+ unit tests passing
- [ ] Integration with translator validated

### Phase 3: CTE Assembly and Dependencies (Week 3)

**Tasks**:
- Implement `_order_ctes_by_dependencies()` with topological sort
- Implement `_generate_with_clause()`
- Implement `_generate_final_select()`
- Handle circular dependency detection
- Unit tests for assembly logic (50+ test cases)
- Integration tests with real FHIRPath expressions

**Deliverable**: Complete CTE assembly with dependency resolution

**Success Criteria**:
- [ ] Topological sort implemented
- [ ] WITH clause generation working
- [ ] Final SELECT generation working
- [ ] Circular dependency detection working
- [ ] 50+ unit tests passing
- [ ] Real FHIRPath expressions execute successfully

### Phase 4: Integration, Testing, Documentation (Week 4)

**Tasks**:
- Integration with PEP-003 translator output
- End-to-end testing with Path Navigation expressions
- Validate against official FHIRPath test suite
- Performance benchmarking and optimization
- API documentation and usage examples
- Architecture documentation updates
- Developer guide for extending CTE infrastructure

**Deliverable**: Production-ready CTE infrastructure with comprehensive documentation

**Success Criteria**:
- [ ] Path Navigation tests: 8/10 (80%+)
- [ ] Integration tests passing
- [ ] Performance <10ms for CTE generation
- [ ] API documentation complete
- [ ] Architecture docs updated

---

## Success Metrics

### Primary Metrics

| Metric | Baseline | Target | Success Criterion |
|--------|----------|--------|-------------------|
| Path Navigation Compliance | 0% (0/9) | 80%+ (8/10) | Critical for sprint |
| Overall Compliance | 36-65% | 72%+ | Sprint 010 goal |
| CTE Generation Time | N/A | <10ms | Performance target |
| Multi-Database Consistency | N/A | 100% | Architecture requirement |

### Secondary Metrics

- Test Coverage: 90%+ for CTE infrastructure module
- Memory Efficiency: <100MB for complex multi-CTE expressions
- Integration Success: Zero PEP-003 translator changes required
- Documentation: API docs, integration guides, examples

### Quality Gates

- [ ] All 140+ unit tests passing
- [ ] All integration tests passing
- [ ] Zero regressions in existing functionality
- [ ] Architecture compliance validated (thin dialects)
- [ ] Multi-database parity confirmed (DuckDB + PostgreSQL)
- [ ] Performance targets met

---

## Timeline

| Week | Phase | Milestone | Owner |
|------|-------|-----------|-------|
| 1 | Phase 1 | CTE data structures complete | Developer |
| 2 | Phase 2 | Array UNNEST support working | Developer |
| 3 | Phase 3 | CTE assembly complete | Developer |
| 4 | Phase 4 | Integration and documentation | Developer |
| 5 | SP-010-001 | Path Navigation unblocked | Developer |

**Total Duration**: 4-5 weeks

**Sprint 010 Completion**: Week 5

---

## Deferred Work (SP-010 Option B Tasks)

**The following SP-010 tasks are DEFERRED until PEP-004 is complete**:

- SP-010-001: Fix Path Navigation Basics ← **BLOCKED by missing PEP-004**
- SP-010-002: Fix Comments/Syntax Validation ← Can proceed independently
- SP-010-003: Fix Arithmetic Operators ← Can proceed independently
- SP-010-004: Complete Math Functions ← Can proceed independently
- SP-010-005: Improve String Functions ← Can proceed independently

**Decision**:
- **Priority 1**: PEP-004 implementation (Weeks 1-4)
- **Priority 2**: SP-010-002 through SP-010-005 (can be worked in parallel if resources available)
- **Priority 3**: SP-010-001 (Week 5, after PEP-004 complete)

**Rationale**:
- PEP-004 has highest impact (unblocks 60-70% of Path Navigation)
- Other tasks can proceed independently without PEP-004
- SP-010-001 must wait for PEP-004 (architectural blocker)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| UNNEST syntax complexity across dialects | Medium | Medium | Use dialect methods, comprehensive testing |
| CTE dependency ordering edge cases | Low | Medium | Standard topological sort algorithm |
| Integration with PEP-003 output | Low | High | PEP-003 already outputs SQLFragment structure |
| Performance of CTE generation | Low | Medium | Benchmarking, <10ms target reasonable |

### Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Implementation takes longer than 4 weeks | Medium | Medium | MVP scope focused on essentials |
| Path Navigation more complex than expected | Low | Low | Focus on 8/10 tests, defer 2 edge cases |
| Testing reveals architectural issues | Low | High | Comprehensive unit testing catches early |

**Overall Risk**: 🟡 **MEDIUM** - Well-defined problem, clear design patterns

### Mitigation Strategies

1. **MVP Scope**: Focus on single-expression CTEs, defer multi-expression (CQL) support
2. **Incremental Testing**: Comprehensive unit tests at each phase catch issues early
3. **Dialect Abstraction**: Use existing pattern from PEP-003 for database differences
4. **Senior Review**: Mandatory architecture review at each phase completion

---

## Architecture Compliance

### Non-Negotiable Requirements

✅ **Thin Dialect Pattern**:
- All business logic in CTEBuilder/CTEAssembler
- Dialects contain ONLY syntax differences (UNNEST syntax)
- Zero exceptions allowed

✅ **Population-First Design**:
- All CTEs support population-scale operations
- No row-by-row processing patterns
- Array operations via LATERAL UNNEST (population-friendly)

✅ **Multi-Database Consistency**:
- 100% identical behavior on DuckDB and PostgreSQL
- Comprehensive validation for all CTE operations
- Zero dialect-specific business logic

✅ **CTE-First SQL Generation**:
- Follow documented architecture (5-layer pipeline)
- Monolithic queries for optimization
- Proper dependency ordering

### Review Gates

Each phase requires:
- [ ] Senior architect code review
- [ ] Architecture compliance verification
- [ ] Multi-database testing validation
- [ ] Regression testing confirmation

---

## Dependencies

### Required (Already Complete)

✅ **PEP-002 (Parser)**: Provides AST structures
✅ **PEP-003 (Translator)**: Provides SQL fragments
✅ **SP-009-033 (StructureDefinition Loader)**: Provides type metadata
✅ **Dialect Infrastructure**: Database abstraction layer

### Enables (Future Work)

- **SP-010-001**: Path Navigation (unblocked after PEP-004)
- **SQL-on-FHIR v2.0**: Requires CTE-based execution
- **CQL Framework**: Depends on multi-expression CTE assembly
- **Quality Measures**: Needs monolithic query performance

---

## Testing Strategy

### Unit Testing (140+ tests total)

**Phase 1 Tests** (50 tests):
- CTE dataclass serialization
- Dependency tracking
- Metadata handling

**Phase 2 Tests** (40 tests):
- UNNEST query generation
- Dialect method correctness
- Array flattening logic

**Phase 3 Tests** (50 tests):
- Topological sort
- WITH clause generation
- Final SELECT generation
- Circular dependency detection

### Integration Testing (50+ tests)

- PEP-003 translator → CTE infrastructure
- Database execution (DuckDB + PostgreSQL)
- Path Navigation expressions (all 10 tests)
- Array operations (nested arrays, multi-level UNNEST)
- Dialect consistency (identical results)

### Performance Testing

- CTE generation speed: <10ms target
- Query execution: Validate 10x+ improvement
- Memory usage: <100MB for complex CTEs
- Scalability: Handle 10+ CTEs without degradation

### Compliance Testing

- Official FHIRPath Path Navigation tests: 8/10 minimum
- Array semantics validation
- Result validation against expected behavior

---

## Documentation Plan

### New Documentation

- [ ] **API Documentation**: CTEBuilder, CTEAssembler, CTE dataclass
- [ ] **Integration Guide**: Using CTE infrastructure with PEP-003
- [ ] **Dialect Extension Guide**: Adding UNNEST support for new databases
- [ ] **CTE Examples**: Common FHIRPath patterns and generated CTEs
- [ ] **Troubleshooting Guide**: Common issues and debugging

### Existing Documentation Updates

- [ ] **Architecture Overview**: Update pipeline diagram (add Layers 3 & 4)
- [ ] **FHIRPath Engine Documentation**: Add CTE-based execution docs
- [ ] **Database Dialect Guide**: Document `generate_lateral_unnest()` method
- [ ] **Testing Guide**: Add CTE infrastructure testing patterns

---

## Sprint 010 Success Definition

**Sprint 010 is SUCCESSFUL if**:
- ✅ PEP-004 implementation complete (all 4 phases)
- ✅ Path Navigation: 8/10 tests (80%+)
- ✅ Overall compliance: 72%+ (Sprint 010 target)
- ✅ Zero regressions introduced
- ✅ Architecture compliance: 100% maintained
- ✅ Documentation complete
- ✅ Foundation ready for SQL-on-FHIR and CQL

**Sprint 010 would be OUTSTANDING if**:
- 🌟 Path Navigation: 10/10 tests (100%)
- 🌟 Overall compliance: 75%+
- 🌟 Performance exceeds targets
- 🌟 Early start on SP-010-002 through SP-010-005

---

## Communication Plan

### Daily Updates

- Progress on current phase
- Blockers encountered
- Test results (unit + integration)
- Architecture compliance verification

### Weekly Reviews

- **End of Week 1**: Phase 1 complete, architecture review
- **End of Week 2**: Phase 2 complete, UNNEST validation
- **End of Week 3**: Phase 3 complete, CTE assembly working
- **End of Week 4**: Phase 4 complete, integration validated
- **End of Week 5**: SP-010-001 complete, Sprint 010 review

### Milestone Checkpoints

- **PEP-004 Complete**: Celebrate architectural completion
- **Path Navigation 80%+**: Validate unblocking success
- **Sprint 010 Goal Achieved**: 72%+ compliance confirmed

---

## Accountability

**Junior Developer Responsibilities**:
- Execute PEP-004 implementation phases systematically
- Comprehensive testing at each phase
- Report actual progress (not aspirational)
- Seek senior architect guidance when needed

**Senior Architect Responsibilities**:
- PEP-004 design review and approval
- Architecture compliance verification at each phase
- Support junior developer with complex design decisions
- Final approval before SP-010-001 proceeds

**Shared Commitment**:
- Quality over speed
- Architecture compliance non-negotiable
- Evidence-based progress reporting
- No workarounds that violate documented architecture

---

## Conclusion

**PEP-004 implementation is the CRITICAL PRIORITY for Sprint 010.**

**Why**:
1. Unblocks 60-70% of Path Navigation (from 0% to 80%+)
2. Completes documented architectural pipeline
3. Enables Sprint 010 compliance target (72%)
4. Prevents technical debt accumulation
5. Unblocks future features (SQL-on-FHIR, CQL)

**Timeline**: 4-5 weeks for complete implementation and integration

**Expected Outcome**: Sprint 010 goal achieved, foundation complete for continued progress

---

**Plan Status**: Approved for Execution
**Priority**: ⚠️ **CRITICAL - TOP PRIORITY**
**Next Action**: PEP-004 Phase 1 implementation (Week 1)
**Owner**: Junior Developer (with Senior Architect support)

---

*This plan establishes PEP-004 implementation as the mandatory priority for Sprint 010, replacing the original "broader coverage" strategy with the architecturally-correct foundation-first approach.*
