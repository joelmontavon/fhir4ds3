# Task SP-011-004: Unit Tests for CTE Data Structures

**Task ID**: SP-011-004
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Unit Tests for CTE Data Structures
**Assignee**: Junior Developer
**Created**: 2025-10-19
**Last Updated**: 2025-10-19

---

## Task Overview

### Description

Create comprehensive unit tests for Phase 1 CTE infrastructure components: CTE dataclass, CTEBuilder class, and CTEAssembler class. This test suite validates the foundational data structures and class scaffolding before proceeding to Phase 2 (UNNEST support).

The test suite will be created in `tests/unit/fhirpath/sql/test_cte_data_structures.py` and will achieve 90%+ code coverage for all Phase 1 code. Tests follow pytest conventions and validate both happy paths and error cases.

This task completes the Week 1 quality gate, ensuring the Phase 1 foundation is solid before proceeding to Phase 2 array operations.

### Category
- [ ] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [x] Testing
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

1. **Test File Creation**: Create `tests/unit/fhirpath/sql/test_cte_data_structures.py`
2. **CTE Dataclass Tests**: 20+ tests covering:
   - Basic instantiation
   - Field defaults
   - Validation logic
   - Helper methods (add_dependency, set/get_metadata)
   - Error cases (empty name, invalid SQL identifier, etc.)
3. **CTEBuilder Tests**: 15+ tests covering:
   - Class instantiation
   - CTE name generation (uniqueness, incrementing)
   - Simple query wrapping
   - Fragment-to-CTE conversion
   - CTE chain building
4. **CTEAssembler Tests**: 15+ tests covering:
   - Class instantiation
   - WITH clause generation (single CTE, multiple CTEs)
   - Final SELECT generation
   - Complete query assembly
   - Error cases (empty CTE list)
5. **Coverage Target**: 90%+ coverage for all Phase 1 code

### Non-Functional Requirements

- **Performance**: Test suite execution <5 seconds for all 50+ tests
- **Compliance**: Tests follow pytest conventions and project testing standards
- **Database Support**: Tests run against both DuckDB and PostgreSQL where applicable
- **Error Handling**: Clear test failure messages with helpful diagnostic information

### Acceptance Criteria

- [ ] Test file created: `tests/unit/fhirpath/sql/test_cte_data_structures.py`
- [ ] 50+ unit tests implemented
- [ ] All tests passing (100% pass rate)
- [ ] Code coverage: 90%+ for Phase 1 CTE infrastructure
- [ ] Tests cover all public methods and helper methods
- [ ] Error cases tested (validation failures, empty inputs, etc.)
- [ ] Tests execute in <5 seconds
- [ ] No test flakiness (consistent results)
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

- **tests/unit/fhirpath/sql/** (NEW DIRECTORY): Create directory for CTE tests
- **tests/unit/fhirpath/sql/test_cte_data_structures.py** (NEW): Main test file

### File Modifications

- **tests/unit/fhirpath/sql/test_cte_data_structures.py**: Create new file with 50+ tests

### Database Considerations

- **DuckDB**: Test CTE infrastructure with DuckDB dialect
- **PostgreSQL**: Test CTE infrastructure with PostgreSQL dialect
- **Schema Changes**: None (tests only, no schema changes)

---

## Dependencies

### Prerequisites

1. **SP-011-001**: ✅ Must be complete (CTE dataclass)
2. **SP-011-002**: ✅ Must be complete (CTEBuilder class)
3. **SP-011-003**: ✅ Must be complete (CTEAssembler class)
4. **pytest**: ✅ Available (project testing framework)
5. **pytest-cov**: ✅ Available (coverage reporting)

### Blocking Tasks

- **SP-011-001**: CTE dataclass
- **SP-011-002**: CTEBuilder class
- **SP-011-003**: CTEAssembler class

### Dependent Tasks

- **SP-011-005**: Phase 2 UNNEST implementation requires passing Phase 1 tests
- Phase 1 quality gate requires all tests passing

---

## Implementation Approach

### High-Level Strategy

Create a comprehensive pytest test suite that validates all Phase 1 functionality. Organize tests into logical sections (CTE dataclass, CTEBuilder, CTEAssembler) with fixtures for common test data. Use parametrize for testing multiple scenarios efficiently.

### Implementation Steps

1. **Create Test File and Directory Structure** (0.5 hours)
   - Create `tests/unit/fhirpath/sql/` directory if needed
   - Create `test_cte_data_structures.py`
   - Add imports: pytest, CTE, CTEBuilder, CTEAssembler, dialects
   - **Validation**: File imports correctly

2. **Create Test Fixtures** (1 hour)
   - Fixture for DuckDB dialect instance
   - Fixture for PostgreSQL dialect instance
   - Fixture for sample SQLFragments (simple and UNNEST)
   - Fixture for sample CTEs (single, chain of 3)
   - **Validation**: Fixtures work correctly

3. **Implement CTE Dataclass Tests** (3 hours)
   - **Test class**: `TestCTEDataclass`
   - Tests (20+):
     - `test_cte_basic_creation`: Basic instantiation
     - `test_cte_with_all_fields`: All fields populated
     - `test_cte_field_defaults`: Verify default values
     - `test_cte_add_dependency`: add_dependency() method
     - `test_cte_add_dependency_duplicate`: Duplicate prevention
     - `test_cte_set_metadata`: set_metadata() method
     - `test_cte_get_metadata`: get_metadata() method
     - `test_cte_get_metadata_default`: Default value behavior
     - `test_cte_validation_empty_name`: Empty name raises ValueError
     - `test_cte_validation_empty_query`: Empty query raises ValueError
     - `test_cte_validation_invalid_identifier`: Invalid SQL identifier raises ValueError
     - `test_cte_validation_depends_on_type`: depends_on must be list
     - `test_cte_validation_metadata_type`: metadata must be dict
     - `test_cte_repr`: __repr__ output is useful
     - `test_cte_requires_unnest_default`: Default is False
     - `test_cte_requires_unnest_true`: Can set to True
     - `test_cte_source_fragment_optional`: source_fragment is Optional
     - `test_cte_metadata_extensibility`: Metadata supports various types
     - `test_cte_depends_on_list`: depends_on maintains order
     - Additional edge cases
   - **Validation**: All CTE dataclass tests passing

4. **Implement CTEBuilder Tests** (3.5 hours)
   - **Test class**: `TestCTEBuilder`
   - Tests (15+):
     - `test_ctebuilder_instantiation`: Basic instantiation with dialect
     - `test_ctebuilder_counter_initialization`: Counter starts at 0
     - `test_generate_cte_name_uniqueness`: CTE names are unique
     - `test_generate_cte_name_sequential`: Names increment (cte_1, cte_2, cte_3)
     - `test_wrap_simple_query_basic`: Basic query wrapping
     - `test_wrap_simple_query_with_source`: Query with source table
     - `test_fragment_to_cte_simple`: Simple fragment conversion
     - `test_fragment_to_cte_with_dependency`: Dependency tracking
     - `test_fragment_to_cte_requires_unnest_flag`: UNNEST flag propagated
     - `test_build_cte_chain_single`: Single fragment chain
     - `test_build_cte_chain_multiple`: Multiple fragment chain (3 fragments)
     - `test_build_cte_chain_dependency_tracking`: Dependencies tracked correctly
     - `test_build_cte_chain_counter_increments`: Counter increments for each CTE
     - `test_ctebuilder_with_duckdb_dialect`: Works with DuckDB
     - `test_ctebuilder_with_postgresql_dialect`: Works with PostgreSQL
     - Additional edge cases
   - **Validation**: All CTEBuilder tests passing

5. **Implement CTEAssembler Tests** (3.5 hours)
   - **Test class**: `TestCTEAssembler`
   - Tests (15+):
     - `test_cteassembler_instantiation`: Basic instantiation with dialect
     - `test_generate_with_clause_single_cte`: Single CTE WITH clause
     - `test_generate_with_clause_multiple_ctes`: Multiple CTEs WITH clause
     - `test_generate_with_clause_formatting`: Proper SQL formatting
     - `test_generate_with_clause_empty_list`: Empty list raises ValueError
     - `test_generate_final_select_basic`: Basic SELECT generation
     - `test_generate_final_select_formatting`: Proper SQL formatting
     - `test_assemble_query_single_cte`: Complete query with single CTE
     - `test_assemble_query_multiple_ctes`: Complete query with multiple CTEs
     - `test_assemble_query_sql_validity`: Generated SQL is valid
     - `test_assemble_query_newline_formatting`: WITH and SELECT on separate sections
     - `test_order_ctes_passthrough`: Phase 1 passthrough (no reordering yet)
     - `test_cteassembler_with_duckdb_dialect`: Works with DuckDB
     - `test_cteassembler_with_postgresql_dialect`: Works with PostgreSQL
     - `test_assembled_query_executes_duckdb`: Generated SQL executes in DuckDB
     - `test_assembled_query_executes_postgresql`: Generated SQL executes in PostgreSQL
     - Additional edge cases
   - **Validation**: All CTEAssembler tests passing

6. **Run Coverage Analysis** (0.5 hours)
   - Execute: `pytest tests/unit/fhirpath/sql/test_cte_data_structures.py --cov=fhir4ds/fhirpath/sql/cte --cov-report=term-missing`
   - Verify 90%+ coverage
   - Identify untested lines and add tests if needed
   - **Validation**: Coverage target met

7. **Review and Refinement** (1 hour)
   - Run full test suite
   - Fix any failing tests
   - Improve test clarity and documentation
   - Request senior architect code review
   - **Validation**: All tests passing, review approved

**Estimated Time**: 12h total

### Alternative Approaches Considered

- **Separate test files**: Could split into test_cte.py, test_builder.py, test_assembler.py - rejected for Phase 1 (all related)
- **Integration tests only**: Rejected - unit tests provide faster feedback and better isolation
- **Manual testing only**: Rejected - automated tests enable regression prevention

---

## Testing Strategy

### Unit Testing

This task IS the unit testing implementation for Phase 1.

**Test Organization**:
```python
# tests/unit/fhirpath/sql/test_cte_data_structures.py

import pytest
from fhir4ds.fhirpath.sql.cte import CTE, CTEBuilder, CTEAssembler
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.dialects.postgresql import PostgreSQLDialect

@pytest.fixture
def duckdb_dialect():
    return DuckDBDialect()

@pytest.fixture
def postgresql_dialect():
    return PostgreSQLDialect()

class TestCTEDataclass:
    def test_cte_basic_creation(self):
        """Test basic CTE instantiation."""
        cte = CTE(name="cte_1", query="SELECT * FROM patient")
        assert cte.name == "cte_1"
        assert cte.query == "SELECT * FROM patient"
        assert cte.depends_on == []
        assert cte.requires_unnest is False

    # ... 19 more tests

class TestCTEBuilder:
    def test_ctebuilder_instantiation(self, duckdb_dialect):
        """Test CTEBuilder instantiation."""
        builder = CTEBuilder(duckdb_dialect)
        assert builder.dialect is not None
        assert builder.cte_counter == 0

    # ... 14 more tests

class TestCTEAssembler:
    def test_cteassembler_instantiation(self, duckdb_dialect):
        """Test CTEAssembler instantiation."""
        assembler = CTEAssembler(duckdb_dialect)
        assert assembler.dialect is not None

    # ... 14 more tests
```

### Integration Testing

Integration testing will be performed in SP-011-008 (Phase 2) and SP-011-012 (Phase 3).

### Compliance Testing

Not applicable for this task (unit tests only).

### Manual Testing

Not applicable (automated test suite replaces manual testing).

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Coverage target not met | Low | Medium | Add tests for uncovered lines, focus on critical paths |
| Tests too slow (>5 seconds) | Low | Low | Use fixtures efficiently, avoid unnecessary database operations |
| Test flakiness | Low | Medium | Ensure tests are deterministic, avoid timing dependencies |
| SQL execution tests fail | Medium | Medium | Validate SQL syntax manually first, test both dialects |

### Implementation Challenges

1. **Achieving 90%+ Coverage**: Some edge cases may be hard to test
   - **Approach**: Focus on critical paths first, add edge case tests if time permits
2. **Multi-Database Testing**: Ensuring tests work for both DuckDB and PostgreSQL
   - **Approach**: Use fixtures for dialects, test both where applicable

### Contingency Plans

- **If coverage <90%**: Identify untested critical paths, add targeted tests
- **If tests fail**: Debug systematically, use pytest -v for detailed output
- **If timeline extends**: Prioritize CTE dataclass and CTEBuilder tests, defer some CTEAssembler tests

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review SP-011-001/002/003, plan test structure)
- **Implementation**: 10h (50+ tests across 3 test classes)
- **Coverage Analysis**: 0.5h (run coverage, add missing tests)
- **Review and Refinement**: 1h (review, fix failures, senior review)
- **Total Estimate**: 12h

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Unit testing is straightforward. Similar to other test suites in project. 50+ tests at ~12-15 minutes per test average.

### Factors Affecting Estimate

- Complexity of SQL execution tests: Could add 1-2h if database setup is complex
- Coverage target: Could add 1h if many uncovered edge cases discovered

---

## Success Metrics

### Quantitative Measures

- **Test Count**: 50+ tests implemented
- **Test Pass Rate**: 100% (all tests passing)
- **Code Coverage**: 90%+ for Phase 1 CTE infrastructure
- **Test Execution Time**: <5 seconds for full suite

### Qualitative Measures

- **Test Quality**: Clear, well-documented tests with good assertions
- **Architecture Alignment**: Tests validate PEP-004 specification compliance
- **Maintainability**: Easy to add new tests in Phase 2-4

### Compliance Impact

- **Specification Compliance**: Tests validate foundation for CTE infrastructure
- **Test Suite Results**: 50+ new tests, all passing
- **Performance Impact**: Fast test execution enables frequent testing

---

## Documentation Requirements

### Code Documentation

- [x] Test docstrings explaining what each test validates
- [x] Fixture documentation
- [x] Test organization comments

### Architecture Documentation

- [ ] No ADR needed (test implementation)
- [ ] No architecture changes

### User Documentation

Not applicable for test code.

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

**Current Status**: Completed - Merged to Main

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-19 | Not Started | Task document created | Awaiting SP-011-001/002/003 completion | Begin test implementation after Phase 1 code complete |
| 2025-10-20 | Completed - Pending Review | Implemented 69 pytest cases covering CTE dataclass, builder, and assembler with 99% coverage; verified DuckDB execution and PostgreSQL compatibility harness | None | Await senior architect review |
| 2025-10-20 | Completed - Merged to Main | Senior review completed with approval; 69 tests, 99% coverage, 0.84s execution; merged to main branch | None | Phase 1 complete, proceed to Phase 2 |

### Completion Checklist

- [x] Test directory created
- [x] Test file created with imports
- [x] Fixtures implemented
- [x] CTE dataclass tests (20+) implemented and passing
- [x] CTEBuilder tests (15+) implemented and passing
- [x] CTEAssembler tests (15+) implemented and passing
- [x] Coverage analysis shows 90%+ coverage
- [x] All tests passing (100% pass rate)
- [x] Test execution time <5 seconds
- [x] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] 50+ tests implemented
- [x] All tests passing
- [x] Coverage target (90%+) achieved
- [x] Tests validate PEP-004 specification requirements
- [x] Tests cover both happy paths and error cases
- [x] Test execution is fast (<5 seconds)

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-20
**Review Status**: Approved
**Review Comments**: Outstanding implementation exceeding all expectations. 69 tests (38% above requirement), 99% coverage (exceeding 90%+ target), 0.84s execution (83% faster than 5s requirement). Comprehensive multi-database testing with real DuckDB execution and sophisticated PostgreSQL mocking. See project-docs/plans/reviews/SP-011-004-review.md for complete review.

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-20
**Status**: ✅ Approved and Merged
**Comments**: Exceptional work completing Phase 1 quality gate. Test suite provides rock-solid foundation for Phase 2-4. Architecture validated through comprehensive testing. Ready to proceed to Phase 2 (UNNEST Support).

---

**Task Created**: 2025-10-19 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-19
**Status**: Not Started (Awaiting SP-011-001/002/003 Completion)

---

*This task creates comprehensive unit tests for Phase 1 CTE infrastructure, ensuring the foundation is solid before proceeding to Phase 2 array operations.*
