# Task SP-011-002: Implement CTEBuilder Class Structure

**Task ID**: SP-011-002
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Implement CTEBuilder Class Structure
**Assignee**: Junior Developer
**Created**: 2025-10-19
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `CTEBuilder` class in `fhir4ds/fhirpath/sql/cte.py` with method signatures and comprehensive documentation. This class is responsible for converting SQL fragments from the PEP-003 translator into CTE (Common Table Expression) structures.

This task establishes the class structure and method scaffolding for CTEBuilder. The actual implementation of UNNEST operations will be completed in Phase 2 (SP-011-005), while the basic CTE wrapping logic is implemented here.

The CTEBuilder is a critical component in the CTE infrastructure pipeline, serving as the bridge between the translator output (`List[SQLFragment]`) and the assembler input (`List[CTE]`).

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [x] Critical (Blocker for sprint goals)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **CTEBuilder Class**: Create `CTEBuilder` class with constructor accepting `DatabaseDialect` parameter
2. **CTE Counter**: Maintain internal counter for generating unique CTE names (cte_1, cte_2, etc.)
3. **Method Signatures**: Implement method signatures for:
   - `build_cte_chain(fragments: List[SQLFragment]) -> List[CTE]`
   - `_fragment_to_cte(fragment: SQLFragment, previous_cte: Optional[str]) -> CTE`
   - `_generate_cte_name(fragment: SQLFragment) -> str`
   - `_wrap_simple_query(fragment: SQLFragment, source_table: str) -> str`
   - `_wrap_unnest_query(fragment: SQLFragment, source_table: str) -> str` (stub for Phase 2)
4. **Documentation**: Comprehensive class and method docstrings following SP-011-001 patterns
5. **Type Hints**: Complete type hints for all methods and parameters

### Non-Functional Requirements

- **Performance**: Class instantiation and CTE name generation should be <1ms
- **Compliance**: Follows PEP-004 specification for CTEBuilder component
- **Database Support**: Database-agnostic class structure (dialect injected via constructor)
- **Error Handling**: Clear error messages for invalid inputs

### Acceptance Criteria

- [ ] `CTEBuilder` class created in `fhir4ds/fhirpath/sql/cte.py`
- [ ] Constructor accepts `DatabaseDialect` parameter and initializes counter
- [ ] All method signatures match PEP-004 specification
- [ ] Comprehensive docstrings for class and all methods
- [ ] Type hints complete (100% coverage)
- [ ] `_generate_cte_name()` working and tested
- [ ] `_wrap_simple_query()` implemented with basic CTE wrapping
- [ ] `_wrap_unnest_query()` stubbed for Phase 2 implementation
- [ ] No linting errors (mypy passes)
- [ ] Architecture review approved

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/cte.py**: Add CTEBuilder class (approximately 200 lines with documentation)

### File Modifications

- **fhir4ds/fhirpath/sql/cte.py**: Modify to add CTEBuilder class after CTE dataclass

### Database Considerations

- **DuckDB**: No database-specific code (class is database-agnostic)
- **PostgreSQL**: No database-specific code (class is database-agnostic)
- **Schema Changes**: None (Python class only)

---

## Dependencies

### Prerequisites

1. **SP-011-001**: ✅ Complete (CTE dataclass available)
2. **PEP-003 SQLFragment**: ✅ Available (from existing translator)
3. **DatabaseDialect Base Class**: ✅ Available (from existing dialect infrastructure)

### Blocking Tasks

- **SP-011-001**: CTE dataclass must be complete

### Dependent Tasks

- **SP-011-005**: UNNEST implementation depends on CTEBuilder structure
- **SP-011-004**: Unit tests require CTEBuilder class

---

## Implementation Approach

### High-Level Strategy

Create a clean CTEBuilder class that follows the builder pattern. The class will maintain state (CTE counter) and provide methods for converting SQL fragments to CTEs. Phase 1 implements basic structure and simple query wrapping; Phase 2 adds UNNEST support.

### Implementation Steps

1. **Create CTEBuilder Class Structure** (2 hours)
   - Add class definition after CTE dataclass in cte.py
   - Implement `__init__(self, dialect: DatabaseDialect)`
   - Initialize `self.dialect` and `self.cte_counter = 0`
   - Add comprehensive class docstring explaining purpose and usage
   - **Validation**: Class instantiates with dialect parameter

2. **Implement CTE Name Generation** (1 hour)
   - Implement `_generate_cte_name(fragment: SQLFragment) -> str`
   - Increment counter and return f"cte_{self.cte_counter}"
   - Add docstring with examples
   - **Validation**: Unique names generated, counter increments

3. **Implement Simple Query Wrapping** (3 hours)
   - Implement `_wrap_simple_query(fragment: SQLFragment, source_table: str) -> str`
   - Wrap fragment expression in SELECT if needed
   - Handle source table references
   - Return properly formatted CTE query
   - **Validation**: Simple queries wrapped correctly

4. **Implement Fragment-to-CTE Conversion** (2 hours)
   - Implement `_fragment_to_cte(fragment: SQLFragment, previous_cte: Optional[str]) -> CTE`
   - Generate CTE name
   - Choose wrapping method based on `fragment.requires_unnest`
   - Build depends_on list from previous_cte
   - Return CTE instance
   - **Validation**: CTEs created correctly from fragments

5. **Implement Build CTE Chain** (1.5 hours)
   - Implement `build_cte_chain(fragments: List[SQLFragment]) -> List[CTE]`
   - Iterate through fragments
   - Call `_fragment_to_cte()` for each fragment
   - Track previous CTE name for dependencies
   - Return list of CTEs
   - **Validation**: CTE chains built correctly

6. **Stub UNNEST Method** (0.5 hours)
   - Create `_wrap_unnest_query()` stub with pass statement
   - Add TODO comment: "To be implemented in SP-011-005"
   - Add comprehensive docstring explaining future implementation
   - **Validation**: Method exists but not yet functional

7. **Documentation and Review** (1 hour)
   - Add usage examples to class docstring
   - Ensure all methods have complete docstrings
   - Run mypy and fix type hint issues
   - Request senior architect code review
   - **Validation**: No linting errors, review approved

**Estimated Time**: 10h total

### Alternative Approaches Considered

- **Single method for all wrapping**: Rejected - separate methods provide better separation of concerns
- **Static methods**: Rejected - instance methods allow state management (counter)
- **CTE naming strategy**: Sequential numbering chosen for simplicity (could use descriptive names later)

---

## Testing Strategy

### Unit Testing

Unit tests will be created in SP-011-004. This task focuses on implementation and manual validation.

**Manual Validation** (to be performed during development):
- Instantiate CTEBuilder with DuckDB dialect
- Call `_generate_cte_name()` and verify unique names
- Create SQLFragment and call `_wrap_simple_query()`
- Verify simple CTE wrapping works correctly

### Integration Testing

Not applicable for this task (integration tested in SP-011-004 and SP-011-008).

### Compliance Testing

Not applicable for this task (no FHIRPath expressions executed yet).

### Manual Testing

**Test Scenarios**:
1. Create CTEBuilder instance
2. Generate 5 CTE names, verify uniqueness
3. Create simple SQLFragment (no UNNEST)
4. Call `_fragment_to_cte()` and verify CTE created
5. Create list of 3 fragments and call `build_cte_chain()`
6. Verify dependency tracking (cte_2 depends on cte_1, etc.)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Method signatures don't match PEP-004 | Low | Medium | Careful review of PEP-004 Section 2.2, senior review |
| Simple query wrapping too complex | Medium | Low | Start with minimal wrapping, enhance in Phase 2 if needed |
| Dependency tracking logic incorrect | Low | Medium | Comprehensive manual testing, unit tests in SP-011-004 |

### Implementation Challenges

1. **Choosing Right Wrapping Strategy**: Determine when to wrap vs. use fragment as-is
   - **Approach**: Review PEP-003 fragment structure, consult senior architect
2. **Dependency Tracking**: Ensure previous_cte correctly passed through chain
   - **Approach**: Manual testing with 3-4 fragment chains

### Contingency Plans

- **If wrapping logic too complex**: Implement minimal version, enhance in Phase 2
- **If dependency tracking issues**: Simplify to linear dependencies only (no branches)
- **If timeline extends**: Defer _wrap_simple_query refinements to Phase 2

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review PEP-004 spec, plan class structure)
- **Implementation**: 6.5h (class structure, methods, CTE chain building)
- **Documentation**: 2h (comprehensive docstrings, examples)
- **Review and Refinement**: 1h (linting, senior review, address feedback)
- **Total Estimate**: 10h

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: CTEBuilder is well-specified in PEP-004. Most complexity deferred to Phase 2 (UNNEST). Similar to SP-011-001 dataclass implementation.

### Factors Affecting Estimate

- Senior architect availability for review: Could add 0-2h if review delayed
- Complexity of simple query wrapping: Could add 1-2h if more complex than expected

---

## Success Metrics

### Quantitative Measures

- **Lines of Code**: ~200-250 lines (including comprehensive docstrings)
- **Docstring Coverage**: 100% (class + all methods documented)
- **Type Hint Coverage**: 100% (all methods have type hints)
- **Linting Score**: 0 errors, 0 warnings (mypy)

### Qualitative Measures

- **Code Quality**: Clean, Pythonic class implementation following SP-011-001 patterns
- **Architecture Alignment**: Matches PEP-004 specification exactly
- **Maintainability**: Easy to extend with UNNEST implementation in Phase 2

### Compliance Impact

- **Specification Compliance**: Foundation for CTE infrastructure (enables Phase 2-4)
- **Test Suite Results**: No tests yet (tested in SP-011-004)
- **Performance Impact**: None (class structure only, no execution)

---

## Documentation Requirements

### Code Documentation

- [x] Class-level docstring explaining CTEBuilder purpose
- [x] Method docstrings for all public and private methods
- [x] Usage examples in class docstring
- [x] Type hints for all methods and parameters

### Architecture Documentation

- [ ] No ADR needed (follows PEP-004 specification)
- [ ] No component interaction diagrams needed yet

### User Documentation

Not applicable for internal class structure.

---

## Progress Tracking

### Status
- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [x] Completed
- [ ] Blocked

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-19 | Not Started | Task document created | None | Await SP-011-001 completion, then begin implementation |
| 2025-10-20 | In Review | Implemented CTEBuilder with population-first query wrapping and dependency tracking; added unit tests and mypy check | None | Pending senior architect review |
| 2025-10-20 | Completed | Senior architect review completed with APPROVAL; merged to main branch | None | Task complete - proceed to SP-011-003 |

### Completion Checklist

- [x] CTEBuilder class created in cte.py
- [x] Constructor implemented with dialect parameter
- [x] All method signatures implemented
- [x] _generate_cte_name() working
- [x] _wrap_simple_query() implemented
- [x] _fragment_to_cte() implemented
- [x] build_cte_chain() implemented
- [x] _wrap_unnest_query() stubbed
- [x] Comprehensive docstrings complete
- [x] Type hints complete
- [x] mypy validation passing
- [x] Manual testing successful
- [x] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches PEP-004 specification Section 2.2
- [x] All methods have correct signatures and type hints
- [x] Code follows patterns established in SP-011-001
- [x] Docstrings are comprehensive and accurate
- [x] Error handling is appropriate
- [ ] Manual testing verified all functionality

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-20
**Review Status**: Approved
**Review Comments**: See project-docs/plans/reviews/SP-011-002-review.md

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-20
**Status**: Approved - Merged to main
**Comments**: Exceptional implementation demonstrating 100% architecture compliance, outstanding code quality, comprehensive documentation, and production-ready error handling. All acceptance criteria met with zero issues. This establishes excellent foundation for Phase 2 UNNEST implementation.

---

**Task Created**: 2025-10-19 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: ✅ Completed and merged to main (2025-10-20)
**Commit**: 2f3f2dc - feat(cte): implement CTEBuilder class with population-first design

---

*This task establishes the CTEBuilder class structure, enabling conversion of SQL fragments to CTEs as specified in PEP-004.*
