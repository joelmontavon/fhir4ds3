# Task SP-011-012: Unit Tests for Assembly Logic and Integration

**Task ID**: SP-011-012
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Unit Tests for Assembly Logic and Integration
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Create comprehensive unit tests for Phase 3 CTE assembly logic, validating the complete pipeline from topological sorting through WITH clause generation to final SELECT statement assembly. This test suite ensures correct query assembly, validates integration between assembly components, tests end-to-end FHIRPath expression execution, and confirms multi-database parity. The tests will extend the existing `tests/unit/fhirpath/sql/test_cte_data_structures.py` file to include Phase 3 validation alongside Phase 1 (data structures) and Phase 2 (UNNEST) tests.

**Context**: This task completes Phase 3 (CTE Assembly and Dependencies) by validating SP-011-009 (topological sort), SP-011-010 (WITH clause generation), and SP-011-011 (final SELECT generation). This is the critical validation layer ensuring that all Phase 3 components work together correctly to produce executable SQL queries. Tests will validate both individual components and their integration, including execution of generated queries on real databases.

**Test Suite Scope**:
- **Component Tests**: Topological sort, WITH clause, final SELECT (covered in SP-011-009, SP-011-010, SP-011-011)
- **Integration Tests**: assemble_query() pipeline, multi-component interactions
- **End-to-End Tests**: Real FHIRPath expressions → executable SQL → query execution
- **Multi-Database Tests**: DuckDB and PostgreSQL parity validation
- **Total**: 50+ new tests for Phase 3 assembly logic

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

1. **Component Integration Tests** (15+ tests): Validate component interactions
   - assemble_query() with ordered CTEs
   - Topological sort → WITH clause integration
   - WITH clause → final SELECT integration
   - Complete pipeline from CTEs to executable SQL

2. **End-to-End Expression Tests** (10+ tests): Real FHIRPath expressions
   - Simple path expressions (Patient.name)
   - Array navigation (Patient.name.given)
   - Multi-level UNNEST (Patient.name.given.first())
   - Complex dependency chains
   - Query execution validation

3. **Multi-Database Parity Tests** (8+ tests): DuckDB vs PostgreSQL
   - Identical query structure
   - Identical execution results
   - Business logic consistency
   - Only syntax differs (UNNEST vs jsonb_array_elements)

4. **Error Handling Tests** (5+ tests): Assembly error cases
   - Empty CTE list handling
   - Invalid CTE structures
   - Circular dependency detection (from topological sort)
   - Missing dependency detection (from topological sort)

5. **Real Database Execution Tests** (12+ tests): Execute generated queries
   - DuckDB real execution (in-memory database)
   - PostgreSQL mock execution (capture SQL)
   - Verify query syntax validity
   - Validate result correctness

### Non-Functional Requirements

- **Performance**: Test suite execution <10 seconds for all 50+ tests
- **Compliance**: Validates PEP-004 Phase 3 implementation
- **Coverage**: 95%+ coverage for Phase 3 assembly code
- **Maintainability**: Clear test names, good organization, reusable fixtures

### Acceptance Criteria

- [ ] 50+ new tests added for Phase 3 assembly logic
- [ ] All tests passing (100% pass rate)
- [ ] Code coverage: 95%+ for Phase 3 assembly code
- [ ] Component integration tests complete (assemble_query pipeline)
- [ ] End-to-end expression tests complete (real FHIRPath)
- [ ] Multi-database parity validated (DuckDB and PostgreSQL)
- [ ] Real database execution tests successful (DuckDB)
- [ ] Mock database execution tests successful (PostgreSQL)
- [ ] Error cases tested (empty, invalid, circular deps)
- [ ] Tests execute in <10 seconds
- [ ] No test flakiness (consistent results)
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

- **tests/unit/fhirpath/sql/test_cte_data_structures.py**: Add Phase 3 assembly tests
  - New test class: `TestCTEAssemblerIntegration`
  - New test class: `TestCTEAssemblyEndToEnd`
  - New test class: `TestCTEAssemblyMultiDatabase`
  - New test class: `TestCTEAssemblyExecution`

### File Modifications

- **tests/unit/fhirpath/sql/test_cte_data_structures.py** (MODIFY):
  - Add Phase 3 test classes (4 new classes)
  - Add fixtures for complex CTE chains
  - Add fixtures for FHIRPath expression simulation
  - Add real database execution helpers

### Database Considerations

- **DuckDB**: Real execution tests using in-memory DuckDB database
- **PostgreSQL**: Mock connection tests capturing generated SQL
- **Schema Changes**: None (tests only, may need test data setup)

---

## Dependencies

### Prerequisites

1. **SP-011-004**: ✅ Complete (Phase 1 unit tests provide foundation and patterns)
2. **SP-011-008**: ✅ Complete (Phase 2 unit tests provide UNNEST fixtures)
3. **SP-011-009**: Must be complete (topological sort implementation to test)
4. **SP-011-010**: Must be complete (WITH clause generation to test)
5. **SP-011-011**: Must be complete (final SELECT generation to test)
6. **pytest**: ✅ Available (project testing framework)
7. **pytest-cov**: ✅ Available (coverage reporting)

### Blocking Tasks

- **SP-011-009**: Topological sort implementation
- **SP-011-010**: WITH clause generation implementation
- **SP-011-011**: Final SELECT generation implementation

### Dependent Tasks

- **SP-011-013**: End-to-end integration with PEP-003 translator (Phase 4)
- **SP-011-014**: Official FHIRPath test suite validation (Phase 4)

---

## Implementation Approach

### High-Level Strategy

Extend the existing test file with comprehensive Phase 3 tests organized into logical test classes. Follow the same patterns established in Phase 1 and Phase 2 testing for consistency. Use fixtures for complex CTE chains and FHIRPath expression simulation. Include both component-level tests (individual methods) and integration tests (complete pipeline). Execute real database queries on DuckDB and mock queries on PostgreSQL.

**Key Design Decisions**:
1. **Extend Existing File**: Add to `test_cte_data_structures.py` for consolidation
2. **New Test Classes**: Separate classes for integration, end-to-end, multi-database, execution
3. **Fixture Reuse**: Leverage Phase 1 and Phase 2 fixtures where possible
4. **Real + Mock Testing**: DuckDB real execution, PostgreSQL mocked (same as Phase 2)

### Implementation Steps

1. **Create Complex CTE Chain Fixtures** (2 hours)
   - Fixture for 3-CTE chain with dependencies
   - Fixture for 5-CTE chain with complex dependencies
   - Fixture simulating real FHIRPath expression CTEs
   - Fixture for CTEs with UNNEST operations
   - **Validation**: Fixtures create valid CTE chains

2. **Implement TestCTEAssemblerIntegration Class** (4 hours)
   - **Test class**: `TestCTEAssemblerIntegration`
   - Tests (15+):
     - `test_assemble_query_single_cte()`: Simplest case
     - `test_assemble_query_multiple_ctes()`: Chain of 3 CTEs
     - `test_assemble_query_with_dependencies()`: Complex deps
     - `test_assemble_query_with_unnest()`: Include UNNEST CTEs
     - `test_assemble_query_has_with_clause()`: WITH present
     - `test_assemble_query_has_final_select()`: SELECT present
     - `test_assemble_query_semicolon_terminated()`: Ends with ;
     - `test_assemble_query_ctes_ordered()`: Correct order from topological sort
     - `test_assemble_query_formatting()`: Clean, readable output
     - `test_assemble_query_empty_list_raises()`: ValueError for empty
     - `test_assemble_query_preserves_cte_names()`: Names correct
     - `test_assemble_query_preserves_queries()`: Queries intact
     - `test_assemble_query_independent_ctes()`: Multiple roots
     - `test_assemble_query_complex_chain()`: 5+ CTEs
     - `test_assemble_query_mixed_simple_and_unnest()`: Both types
   - **Validation**: All integration tests passing

3. **Implement TestCTEAssemblyEndToEnd Class** (4 hours)
   - **Test class**: `TestCTEAssemblyEndToEnd`
   - Tests (10+):
     - `test_end_to_end_simple_path()`: Patient.birthDate equivalent
     - `test_end_to_end_array_path()`: Patient.name equivalent
     - `test_end_to_end_nested_array()`: Patient.name.given equivalent
     - `test_end_to_end_first_function()`: Patient.name.first() equivalent
     - `test_end_to_end_where_clause()`: Patient.name.where(...) equivalent
     - `test_end_to_end_complex_expression()`: Multi-operation expression
     - `test_end_to_end_multiple_unnests()`: Multiple array navigations
     - `test_end_to_end_sql_validity()`: Generated SQL is syntactically valid
     - `test_end_to_end_result_correctness()`: Query returns expected data
     - `test_end_to_end_population_scale()`: Works on multiple patients
     - Additional real-world scenarios
   - **Validation**: End-to-end expressions working

4. **Implement TestCTEAssemblyMultiDatabase Class** (3 hours)
   - **Test class**: `TestCTEAssemblyMultiDatabase`
   - Tests (8+):
     - `test_duckdb_vs_postgresql_same_structure()`: WITH structure identical
     - `test_duckdb_vs_postgresql_same_order()`: CTE order identical
     - `test_duckdb_vs_postgresql_same_final_select()`: SELECT identical
     - `test_duckdb_vs_postgresql_different_unnest_syntax()`: UNNEST differs
     - `test_duckdb_vs_postgresql_same_business_logic()`: Logic identical
     - `test_duckdb_vs_postgresql_formatting_consistent()`: Format consistent
     - `test_multi_database_integration_results()`: Results consistent
     - `test_multi_database_performance_parity()`: Performance similar
     - Additional parity tests
   - **Validation**: Multi-database parity confirmed

5. **Implement TestCTEAssemblyExecution Class** (4 hours)
   - **Test class**: `TestCTEAssemblyExecution`
   - Tests (12+):
     - `test_execution_duckdb_simple_query()`: Execute simple CTE query
     - `test_execution_duckdb_with_unnest()`: Execute UNNEST query
     - `test_execution_duckdb_complex_chain()`: Execute multi-CTE query
     - `test_execution_duckdb_returns_results()`: Verify results returned
     - `test_execution_duckdb_result_count()`: Check result count
     - `test_execution_duckdb_result_structure()`: Verify column structure
     - `test_execution_postgresql_sql_captured()`: Mock captures SQL
     - `test_execution_postgresql_syntax_valid()`: SQL syntactically valid
     - `test_execution_postgresql_with_clause()`: WITH clause in captured SQL
     - `test_execution_postgresql_unnest_syntax()`: jsonb_array_elements present
     - `test_execution_error_handling()`: Invalid SQL handled gracefully
     - `test_execution_empty_results()`: Handle no results case
     - Additional execution scenarios
   - **Validation**: Database execution working correctly

6. **Add Error Handling Tests** (2 hours)
   - Test empty CTE list raises ValueError
   - Test invalid CTE structure handling
   - Test circular dependency detection (from topological sort)
   - Test missing dependency detection (from topological sort)
   - Test malformed query handling
   - **Validation**: Error cases handled correctly

7. **Run Coverage Analysis** (1 hour)
   - Execute: `pytest tests/unit/fhirpath/sql/test_cte_data_structures.py --cov=fhir4ds.fhirpath.sql.cte --cov-report=term-missing`
   - Verify 95%+ coverage for Phase 3 code
   - Identify untested lines and add tests if needed
   - **Validation**: Coverage target met

8. **Review and Refinement** (2 hours)
   - Run full test suite (Phase 1 + Phase 2 + Phase 3)
   - Fix any failing tests
   - Improve test clarity and documentation
   - Optimize test performance (<10 seconds total)
   - Request senior architect code review
   - **Validation**: All tests passing, review approved

**Estimated Time**: 22h total (increased from 16h in sprint plan for comprehensive Phase 3 validation)

### Alternative Approaches Considered

- **Separate Test File for Phase 3**: Create new test file - **Rejected** (consolidate in single file for CTE infrastructure)
- **Only Mock Testing**: Skip real DuckDB execution - **Rejected** (real execution validates SQL correctness)
- **Minimal Integration Tests**: Focus on unit tests only - **Rejected** (integration critical for Phase 3 validation)

---

## Testing Strategy

### Unit Testing

This task IS the unit testing implementation for Phase 3.

**Test Organization** (extending existing file structure):
```python
# tests/unit/fhirpath/sql/test_cte_data_structures.py

# ... Phase 1 tests from SP-011-004 ...
# ... Phase 2 tests from SP-011-008 ...

# Phase 3 CTE Assembly Tests

@pytest.fixture
def complex_cte_chain() -> List[CTE]:
    """Complex CTE chain with dependencies for integration testing."""
    return [
        CTE(name="cte_1", query="SELECT id, resource FROM patient_resources", depends_on=[]),
        CTE(name="cte_2", query="SELECT id, json_extract(...) FROM cte_1", depends_on=["cte_1"]),
        CTE(name="cte_3", query="SELECT cte_2.id, name_item FROM cte_2, LATERAL UNNEST(...)",
            depends_on=["cte_2"], requires_unnest=True)
    ]

class TestCTEAssemblerIntegration:
    """Validate CTEAssembler component integration."""
    def test_assemble_query_single_cte(self, assembler):
        """Single CTE assembles into complete query."""
        ctes = [CTE(name="cte_1", query="SELECT * FROM resource", depends_on=[])]
        sql = assembler.assemble_query(ctes)
        assert "WITH" in sql
        assert "cte_1 AS (" in sql
        assert "SELECT * FROM cte_1;" in sql

    # ... 14 more integration tests

class TestCTEAssemblyEndToEnd:
    """Validate end-to-end FHIRPath expression assembly."""
    def test_end_to_end_simple_path(self, duckdb_builder, duckdb_assembler):
        """Patient.birthDate equivalent assembles and executes."""
        # Simulate translator output for Patient.birthDate
        fragments = [
            SQLFragment(
                expression="json_extract(resource, '$.birthDate')",
                source_table="patient_resources"
            )
        ]
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)

        # Verify structure
        assert "WITH" in sql
        assert "SELECT * FROM" in sql

        # Execute on DuckDB
        result = duckdb_assembler.dialect.execute_query(sql)
        assert result is not None  # Query executed successfully

    # ... 9 more end-to-end tests

class TestCTEAssemblyMultiDatabase:
    """Validate DuckDB and PostgreSQL parity."""
    def test_duckdb_vs_postgresql_same_structure(self, complex_cte_chain,
                                                   duckdb_assembler, postgresql_assembler):
        """Query structure identical across databases."""
        duckdb_sql = duckdb_assembler.assemble_query(complex_cte_chain)
        pg_sql = postgresql_assembler.assemble_query(complex_cte_chain)

        # Same WITH structure
        assert duckdb_sql.count("WITH") == pg_sql.count("WITH") == 1
        # Same number of CTEs
        assert duckdb_sql.count("AS (") == pg_sql.count("AS (")
        # Same final SELECT
        assert "SELECT * FROM cte_3;" in duckdb_sql
        assert "SELECT * FROM cte_3;" in pg_sql

    # ... 7 more parity tests

class TestCTEAssemblyExecution:
    """Validate real database execution."""
    def test_execution_duckdb_simple_query(self, duckdb_assembler, duckdb_dialect):
        """Execute simple CTE query on DuckDB."""
        # Create test data
        duckdb_dialect.execute_query("CREATE TABLE test_patients (id INT, name VARCHAR)")
        duckdb_dialect.execute_query("INSERT INTO test_patients VALUES (1, 'Alice'), (2, 'Bob')")

        # Assemble and execute query
        ctes = [CTE(name="cte_1", query="SELECT * FROM test_patients", depends_on=[])]
        sql = duckdb_assembler.assemble_query(ctes)
        results = duckdb_dialect.execute_query(sql)

        # Verify results
        assert len(results) == 2
        assert results[0][1] in ['Alice', 'Bob']

    # ... 11 more execution tests
```

### Integration Testing

- **Complete Pipeline**: CTEBuilder → CTEAssembler → executable SQL
- **With Translator**: Simulate PEP-003 translator output
- **Real Expressions**: FHIRPath-equivalent CTE chains
- **Database Execution**: Execute on both DuckDB and PostgreSQL

### Compliance Testing

- **FHIRPath Semantics**: Verify correct expression evaluation
- **Population-First**: Ensure queries support population-scale analytics
- **Multi-Database Consistency**: Identical behavior across databases

### Manual Testing

Not applicable - automated test suite is comprehensive.

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test suite too slow (>10 seconds) | Medium | Medium | Optimize fixtures, use in-memory databases, minimize setup |
| DuckDB execution tests flaky | Low | High | Use in-memory database, clean setup/teardown, deterministic data |
| PostgreSQL mock complexity | Low | Medium | Follow Phase 2 mock pattern, validate SQL structure |
| Coverage target not met | Low | Medium | Add tests for uncovered lines, focus on critical paths |
| Integration complexity | Medium | High | Break into smaller tests, use good fixtures |

### Implementation Challenges

1. **End-to-End Test Complexity**: Simulating full FHIRPath expressions
   - **Approach**: Create CTE chains manually that simulate translator output, focus on key patterns

2. **Real Database Execution**: Setting up test data and executing queries
   - **Approach**: Use in-memory DuckDB, create minimal test data, clean up after tests

3. **Multi-Database Parity**: Maintaining identical test scenarios across dialects
   - **Approach**: Share fixtures, parameterize tests where possible

### Contingency Plans

- **If coverage <95%**: Identify critical uncovered code, add targeted tests
- **If tests fail**: Debug systematically, use pytest -v for detailed output
- **If timeline extends**: Prioritize integration and end-to-end tests, defer some execution tests
- **If performance poor**: Optimize fixtures, reduce database operations, parallelize where possible

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 2h (review Phase 3 code, plan test structure, design fixtures)
- **Implementation**: 17h (50+ tests across 4 test classes, fixtures, helpers)
- **Coverage Analysis**: 1h (run coverage, add missing tests)
- **Performance Optimization**: 1h (ensure <10 second execution)
- **Review and Refinement**: 2h (self-review, fix failures, senior review)
- **Total Estimate**: 23h (increased from 16h for comprehensive Phase 3 validation)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Similar to SP-011-004 (Phase 1 tests, 12h) and SP-011-008 (Phase 2 tests, 12h) but with more integration complexity. Phase 3 requires validating components working together, which adds complexity but follows established patterns.

### Factors Affecting Estimate

- **Integration Test Complexity**: +3h if end-to-end scenarios more complex than expected
- **Database Execution Issues**: +2h if real execution tests require extensive debugging
- **Coverage Target**: +2h if many uncovered edge cases discovered
- **Performance Optimization**: +2h if test suite exceeds 10-second target

---

## Success Metrics

### Quantitative Measures

- **Test Count**: 50+ tests implemented for Phase 3 assembly
- **Test Pass Rate**: 100% (all tests passing)
- **Code Coverage**: 95%+ for Phase 3 assembly code
- **Test Execution Time**: <10 seconds for all Phase 3 tests
- **Total Suite**: 234+ tests (69 Phase 1 + 115 Phase 2 + 50 Phase 3)

### Qualitative Measures

- **Test Quality**: Clear, well-documented tests with good assertions
- **Integration Validation**: Components work together correctly
- **Real-World Readiness**: End-to-end tests prove production viability

### Compliance Impact

- **Specification Compliance**: Tests validate PEP-004 Phase 3 implementation
- **Multi-Database Parity**: Confirms identical behavior across DuckDB/PostgreSQL
- **FHIRPath Semantics**: Validates correct expression assembly and execution

---

## Documentation Requirements

### Code Documentation

- [x] Test docstrings explaining what each test validates
- [x] Fixture documentation for complex CTE chains
- [x] Test organization comments
- [x] Helper function documentation

### Architecture Documentation

- [ ] No ADR needed (test implementation)
- [ ] No architecture changes

### User Documentation

Not applicable for test code.

---

## Progress Tracking

### Status
- [x] Not Started
- [x] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [ ] Completed
- [ ] Blocked

**Current Status**: Completed - Pending Review

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | Awaiting SP-011-009/010/011 completion | Begin test implementation after Phase 3 components complete |
| 2025-10-21 | Completed - Pending Review | Added comprehensive Phase 3 CTE assembly tests and achieved 100% coverage on `cte.py` | None | Await senior architect review |

### Completion Checklist

- [x] Complex CTE chain fixtures created
- [x] TestCTEAssemblerIntegration class implemented (15+ tests)
- [x] TestCTEAssemblyEndToEnd class implemented (10+ tests)
- [x] TestCTEAssemblyMultiDatabase class implemented (8+ tests)
- [x] TestCTEAssemblyExecution class implemented (12+ tests)
- [x] Error handling tests implemented (5+ tests)
- [x] Coverage analysis shows 95%+ coverage
- [x] All tests passing (100% pass rate)
- [x] Test execution time <10 seconds
- [x] Performance optimized
- [ ] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] 50+ tests implemented
- [x] All tests passing
- [x] Coverage target (95%+) achieved
- [x] Tests validate PEP-004 Phase 3 requirements
- [x] Integration tests prove components work together
- [x] End-to-end tests validate real FHIRPath expressions
- [x] Multi-database parity confirmed
- [x] Real execution tests successful
- [x] Test execution is fast (<10 seconds)

**Notes**: 200-test suite exercises integration, end-to-end execution, and multi-database parity; coverage run confirms 100% of `fhir4ds.fhirpath.sql.cte`.

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [Pending]
**Review Status**: Pending
**Review Comments**: [To be completed during review]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [Pending]
**Status**: Pending
**Comments**: [To be completed upon approval]

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Not Started (Awaiting SP-011-009/010/011 Completion)

---

*This task creates comprehensive unit tests for Phase 3 CTE assembly logic, validating topological sorting, WITH clause generation, final SELECT generation, and end-to-end query assembly with multi-database parity confirmation.*
