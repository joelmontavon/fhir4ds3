# PEP-004 Implementation Orientation Guide

**PEP**: PEP-004 - CTE Infrastructure for Population-Scale FHIRPath Execution
**Implementation Duration**: 21-10-2025 to 15-11-2025 (4 weeks, Sprint 011)
**Your Role**: Junior Developer (with Senior Architect support)
**Lead**: Senior Solution Architect/Engineer

---

## Welcome to CTE Infrastructure Implementation

You are implementing **PEP-004: CTE Infrastructure for Population-Scale FHIRPath Execution** - a **CRITICAL** architectural component that completes the FHIRPath execution pipeline.

**What This PEP Does**: Transforms SQL fragments from the translator (PEP-003) into executable, monolithic SQL queries optimized for population-scale healthcare analytics.

**Why It's Critical**: This PEP fills the documented architectural gap (Layers 3 & 4) between the Translator and Database Execution, unblocking 60-70% of Path Navigation functionality and enabling the promised 10x+ performance improvements.

**Your Impact**: This implementation will increase FHIRPath compliance from 36-65% to 72%+, unblock Path Navigation from 0% to 80%+, and provide the foundation required for SQL-on-FHIR and CQL implementations.

---

## 1. Initial Review and Context

### Required Reading (in order)

1. **CLAUDE.md** - Development workflow and principles (READ FIRST - includes "Document As You Go" and "Keep Workspace Tidy")
2. **project-docs/peps/accepted/pep-004-cte-infrastructure.md** - The PEP you're implementing (CRITICAL - read thoroughly)
3. **project-docs/plans/current-sprint/sprint-011-pep-004-cte-infrastructure.md** - Sprint 011 plan
4. **project-docs/plans/milestones/milestone-M004-cte-infrastructure.md** - Overall milestone context
5. **project-docs/plans/tasks/SP-011-ALL-TASKS-SUMMARY.md** - Comprehensive task reference
6. **project-docs/architecture/** - Architecture goals and unified FHIRPath principles

### Key Concepts to Understand

- **Common Table Expressions (CTEs)**: WITH clauses in SQL that enable modular, optimized query construction
- **Population-First Design**: Default to queries that operate on entire patient populations, not row-by-row processing
- **Thin Dialects**: Database-specific code contains ONLY syntax differences, ZERO business logic
- **LATERAL UNNEST**: SQL operation for flattening arrays (Patient.name → individual name records)
- **Topological Sort**: Algorithm for ordering CTEs based on dependencies (ensure CTEs defined before referenced)
- **SQL Fragments**: Output from PEP-003 translator, input to CTE infrastructure (List[SQLFragment])

---

## 2. Your CTE Infrastructure Implementation Tasks

### Phase 1: CTE Data Structures (Week 1, Days 1-6)

1. **SP-011-001**: Create CTE dataclass and module structure (8h) - **CRITICAL - DETAILED TASK AVAILABLE**
2. **SP-011-002**: Implement CTEBuilder class structure (10h)
3. **SP-011-003**: Implement CTEAssembler class structure (10h)
4. **SP-011-004**: Unit tests for CTE data structures (12h)

**Phase 1 Goal**: Foundational CTE data structures with 50+ unit tests passing

### Phase 2: Array UNNEST Support (Week 2, Days 7-12)

5. **SP-011-005**: Implement `_wrap_unnest_query()` in CTEBuilder (12h)
6. **SP-011-006**: Add `generate_lateral_unnest()` to DuckDB dialect (8h)
7. **SP-011-007**: Add `generate_lateral_unnest()` to PostgreSQL dialect (8h)
8. **SP-011-008**: Unit tests for UNNEST generation and integration (12h)

**Phase 2 Goal**: Array flattening working for both DuckDB and PostgreSQL

### Phase 3: CTE Assembly and Dependencies (Week 3, Days 13-18)

9. **SP-011-009**: Implement topological sort for CTE dependencies (10h)
10. **SP-011-010**: Implement `_generate_with_clause()` (8h)
11. **SP-011-011**: Implement `_generate_final_select()` (6h)
12. **SP-011-012**: Unit tests for assembly logic and integration (16h)

**Phase 3 Goal**: Complete CTE assembly with end-to-end FHIRPath expression execution

### Phase 4: Integration, Testing, Documentation (Week 4, Days 19-25)

13. **SP-011-013**: End-to-end integration with PEP-003 translator (10h)
14. **SP-011-014**: Validate against official FHIRPath test suite (8h) - **CRITICAL GATE**
15. **SP-011-015**: Performance benchmarking and optimization (8h)
16. **SP-011-016**: API documentation and architecture docs updates (12h)

**Phase 4 Goal**: Production-ready CTE infrastructure, 8/10 Path Navigation tests, 72%+ overall compliance

### Task Locations

- **Detailed tasks**: `project-docs/plans/tasks/SP-011-XXX-[task-name].md`
- **Task summary**: `project-docs/plans/tasks/SP-011-ALL-TASKS-SUMMARY.md` (comprehensive reference)

---

## 3. Development Workflow

### Branch Management

- Create a new branch for each task: `SP-011-XXX-task-name`
- Example: `SP-011-001-create-cte-dataclass`
- Follow git workflow in `project-docs/process/git-workflow.md`

### Progress Tracking Requirements

**For EVERY task, update these documents as you work:**

#### A. Task Document Updates

Location: `project-docs/plans/tasks/SP-011-XXX-[task-name].md`
- Update "Progress Updates" table daily
- Mark checklist items completed: `- [x] Item`
- Update "Status" section through the workflow
- Document blockers immediately

#### B. Sprint Plan Updates

Location: `project-docs/plans/current-sprint/sprint-011-pep-004-cte-infrastructure.md`
- Update task status in "Task Breakdown" tables
- Note timeline changes or blockers
- Update phase completion checkboxes

#### C. Daily Progress Format

```
| 2025-10-21 | In Development | Implemented CTE dataclass fields | None | Add validation methods next |
```

---

## 4. Implementation Guidelines

### Code Quality Standards (from CLAUDE.md)

- **No hardcoded values**: Use configuration for all parameters
- **Multi-database support**: Test against both DuckDB AND PostgreSQL (mandatory)
- **Population-first design**: Default to population-scale queries (no LIMIT 1, use [0] indexing)
- **Thin dialects**: ONLY syntax differences in dialect classes, ZERO business logic
- **Error handling**: Comprehensive error handling with clear error messages

### Testing Requirements

- **Unit Tests**: 90%+ coverage for all CTE infrastructure code (140+ tests total)
- **Integration Tests**: Multi-database consistency validation (DuckDB vs PostgreSQL must be identical)
- **Compliance Tests**: Official FHIRPath Path Navigation test suite (target 8/10 minimum)
- **Performance**: CTE generation <10ms, query execution 10x+ improvement

### Documentation Standards

- **Inline comments**: Complex logic must have explanatory comments
- **Function/method docs**: Comprehensive docstrings with examples
- **Type hints**: All functions and methods have Python 3.10+ type hints
- **Update all docs**: Architecture diagrams, API docs, integration guides

---

## 5. CTE Infrastructure Implementation Success Criteria

### Primary Objectives (Must Complete)

- [ ] CTEBuilder component complete with 100% unit tests passing
- [ ] CTEAssembler component complete with 100% unit tests passing
- [ ] LATERAL UNNEST support for DuckDB and PostgreSQL (both dialects)
- [ ] Path Navigation tests: 8/10 passing minimum (80%+ target)
- [ ] Overall FHIRPath compliance: 72%+ achieved
- [ ] Architecture compliance: 100% (thin dialects verified, population-first design maintained)
- [ ] Multi-database parity: 100% (DuckDB and PostgreSQL identical behavior)
- [ ] Documentation complete (API docs, architecture docs, integration guide)

### Quality Gates (End of Each Week)

**Week 1 Gate**:
- [ ] Architecture review approved for all class structures
- [ ] 50+ unit tests passing
- [ ] No linting errors (ruff, mypy)

**Week 2 Gate**:
- [ ] UNNEST working for both databases
- [ ] 90+ total unit tests passing
- [ ] Multi-database parity validated

**Week 3 Gate**:
- [ ] End-to-end FHIRPath expressions executing
- [ ] 140+ total unit tests passing
- [ ] CTE assembly working correctly

**Week 4 Gate** (CRITICAL):
- [ ] 8/10 Path Navigation tests passing
- [ ] 72%+ overall compliance
- [ ] Documentation complete
- [ ] Senior architect final approval

### Compliance Targets

- **FHIRPath R4 Path Navigation**: 0% (0/9) → 80%+ (8/10)
- **FHIRPath R4 Overall**: 36-65% → 72%+
- **SQL-on-FHIR Foundation**: Not started → Ready (architecture complete)
- **CQL Foundation**: Not started → Ready (architecture complete)

---

## 6. Resources and References

### Official Test Suite Locations

- **FHIRPath R4 Tests**: `tests/integration/fhirpath/official_test_runner.py` (MUST USE THIS - not the stub)
- **Test Data**: Loaded in both DuckDB (embedded) and PostgreSQL (`localhost:5432`)
- **Compliance Report**: Generated after test execution with detailed results

### Development Environment

- **Python**: 3.10+ (project standard)
- **Databases**: DuckDB (primary) + PostgreSQL (validation) - BOTH REQUIRED
- **Testing**: pytest with coverage reporting (`pytest-cov`)
- **Quality**: ruff (linting), mypy (type checking)

### Critical Resources for CTE Implementation

- **PEP-003 Translator**: Provides `List[SQLFragment]` input - review `fhir4ds/fhirpath/sql/translator.py`
- **SQLFragment Structure**: Review `fhir4ds/fhirpath/sql/data_structures.py` to understand fragment format
- **Dialect Base Class**: Review `fhir4ds/fhirpath/dialects/base.py` for dialect method patterns
- **StructureDefinition Loader**: SP-009-033 provides type metadata - see `fhir4ds/fhirpath/types/structure_loader.py`

### NO Archived Code to Reference

**Important**: This is a NEW architectural component with no prior implementation. You are building from the PEP-004 specification directly.

**What to Reference Instead**:
- **PEP-003 Patterns**: Review translator implementation for visitor pattern, dialect usage
- **Dataclass Patterns**: Review existing dataclasses in codebase for structure
- **Dialect Patterns**: Review how DuckDB and PostgreSQL dialects currently work

---

## 7. Communication and Support

### Daily Updates

- **Format**: Update task documentation daily
- **Content**: Progress, current focus, blockers, next steps
- **Timing**: End of day updates in task progress table

### Weekly Reviews

- **Schedule**: End of each week (Weeks 1-4)
- **Participants**: You + Senior Solution Architect/Engineer
- **Agenda**: Phase review, architecture compliance, planning adjustments

### Getting Help

- **Blockers**: Document in task immediately, continue where possible
- **Questions**: Add to task documentation, note in daily update
- **Escalation**: If blocked >2 hours, notify Senior Solution Architect/Engineer
- **Architecture Questions**: Always consult senior architect before making architectural decisions

---

## 8. Completion Process

### For Each Task

1. **Validate**: Ensure all acceptance criteria met
2. **Test**: Run complete test suite (both databases)
3. **Document**: Update all progress tracking
4. **Self-Review**: Use task completion checklist
5. **Commit**: Descriptive single-line commit message
6. **Request Review**: Notify Senior Solution Architect/Engineer

### Commit Message Format

- **Format**: `feat(cte): [brief description]` or `test(cte): [brief description]`
- **Examples**:
  - `feat(cte): implement CTE dataclass with all metadata fields`
  - `feat(cte): add LATERAL UNNEST support for DuckDB dialect`
  - `test(cte): add 50+ unit tests for CTE data structures`
- **Guidelines**: Single line, describe accomplishment, use conventional commit types

### Final Sprint 011 Review

- All 16 tasks completed
- 8/10 Path Navigation tests passing
- 72%+ overall compliance achieved
- Documentation updated and comprehensive
- Lessons learned documented
- Sprint retrospective participation

---

## 9. Success Tips

### Best Practices

- **Read PEP-004 thoroughly** before starting - understand WHY, not just WHAT
- **Follow phase sequence** - don't skip ahead, phases build on each other
- **Test both databases early** - don't wait until end to discover dialect issues
- **Ask architecture questions early** - thin dialects principle is non-negotiable
- **Document as you implement** - much easier than documenting later

### Common Pitfalls to Avoid

- ❌ Skipping unit tests until the end (write tests as you implement)
- ❌ Testing only DuckDB (PostgreSQL validation is mandatory)
- ❌ Putting business logic in dialect classes (violates thin dialect principle)
- ❌ Using LIMIT 1 instead of [0] indexing (violates population-first design)
- ❌ Not updating task documentation daily (makes reviews difficult)
- ❌ Hardcoding CTE names or parameters (use configuration)

### PEP-004 Specific Tips

- **Understand Topological Sort**: Before implementing SP-011-009, review standard algorithms (Kahn's algorithm or DFS-based)
- **UNNEST Syntax Differences**: DuckDB uses `UNNEST()`, PostgreSQL uses `jsonb_array_elements()` - this is THE example of thin dialects
- **CTE Naming**: Use simple sequential names (cte_1, cte_2, etc.) - don't overcomplicate
- **Fragment Dependencies**: PEP-003 fragments have `depends_on` field - use it for topological sort
- **Performance First**: CTE generation is fast by design - focus on correctness first, optimize if needed

---

## 10. CTE Infrastructure Impact

Your work implementing this PEP creates the foundation for:

- **Architectural Completion**: Fills documented gap in 5-layer FHIRPath execution pipeline (Layers 3 & 4)
- **Path Navigation Functionality**: Unblocks 60-70% of Path Navigation tests (enables `Patient.name.given` expressions)
- **Population-Scale Analytics**: Enables 10x+ performance improvements through monolithic query generation
- **Future Specifications**: Required prerequisite for SQL-on-FHIR and CQL implementations
- **Quality Measures**: Foundation for eCQI Framework quality measure calculation
- **Compliance Progress**: Advances from 36-65% to 72%+ overall FHIRPath specification compliance

**Broader Context**: This PEP completes the core FHIRPath execution architecture. Without it, FHIR4DS cannot deliver on its promise of population-scale healthcare analytics, cannot implement higher-level specifications (SQL-on-FHIR, CQL), and cannot achieve 100% FHIRPath compliance.

Your implementation directly enables the next phase of FHIR4DS evolution toward becoming the definitive platform for healthcare interoperability and population analytics.

---

**Ready to Begin**: Start with SP-011-001 (Create CTE Dataclass) after completing your document review
**Questions**: Document in task progress and continue where possible
**Success**: Measured by 8/10 Path Navigation tests, 72%+ compliance, and architecture compliance validation

---

*This orientation guide ensures you have everything needed to successfully implement PEP-004 and complete the FHIRPath execution pipeline for FHIR4DS.*
