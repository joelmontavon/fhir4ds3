# Sprint 011: All Tasks Summary (PEP-004 Implementation)

**Sprint**: Sprint 011
**PEP**: PEP-004 (CTE Infrastructure)
**Total Tasks**: 16 tasks across 4 phases
**Total Effort**: 168 hours (4 weeks)

---

## Task Overview Table

| Task ID | Task Name | Phase | Assignee | Estimate | Dependencies |
|---------|-----------|-------|----------|----------|--------------|
| SP-011-001 | Create CTE dataclass and module structure | Phase 1 | Junior Dev | 8h | None |
| SP-011-002 | Implement CTEBuilder class structure | Phase 1 | Junior Dev | 10h | SP-011-001 |
| SP-011-003 | Implement CTEAssembler class structure | Phase 1 | Junior Dev | 10h | SP-011-001 |
| SP-011-004 | Unit tests for CTE data structures | Phase 1 | Junior Dev | 12h | SP-011-001 |
| SP-011-005 | Implement `_wrap_unnest_query()` in CTEBuilder | Phase 2 | Junior Dev | 12h | SP-011-002 |
| SP-011-006 | Add `generate_lateral_unnest()` to DuckDB dialect | Phase 2 | Junior Dev | 8h | SP-011-005 |
| SP-011-007 | Add `generate_lateral_unnest()` to PostgreSQL dialect | Phase 2 | Junior Dev | 8h | SP-011-005 |
| SP-011-008 | Unit tests for UNNEST generation and integration | Phase 2 | Junior Dev | 12h | SP-011-005-007 |
| SP-011-009 | Implement topological sort for CTE dependencies | Phase 3 | Junior Dev | 10h | SP-011-003 |
| SP-011-010 | Implement `_generate_with_clause()` | Phase 3 | Junior Dev | 8h | SP-011-009 |
| SP-011-011 | Implement `_generate_final_select()` | Phase 3 | Junior Dev | 6h | SP-011-010 |
| SP-011-012 | Unit tests for assembly logic and integration | Phase 3 | Junior Dev | 16h | SP-011-009-011 |
| SP-011-013 | End-to-end integration with PEP-003 translator | Phase 4 | Junior Dev | 10h | SP-011-012 |
| SP-011-014 | Validate against official FHIRPath test suite | Phase 4 | Junior Dev | 8h | SP-011-013 |
| SP-011-015 | Performance benchmarking and optimization | Phase 4 | Junior Dev | 8h | SP-011-013 |
| SP-011-016 | API documentation and architecture docs updates | Phase 4 | Junior Dev | 12h | SP-011-013 |

**Total Estimated Hours**: 168h (approximately 4 weeks @ 40-42 hours per week)

---

## Phase 1: CTE Data Structures (Week 1, Days 1-6)

### SP-011-001: Create CTE Dataclass and Module Structure ✅ DETAILED TASK CREATED

**Estimate**: 8h
**Description**: Create `CTE` dataclass in `fhir4ds/fhirpath/sql/cte.py` with all required fields (name, query, depends_on, requires_unnest, source_fragment, metadata). Comprehensive docstrings and type hints.

**Key Deliverables**:
- `CTE` dataclass with all fields
- Module-level documentation
- Type hints and validation

**Acceptance Criteria**:
- CTE dataclass instantiates correctly
- All fields documented
- Architecture review approved

---

### SP-011-002: Implement CTEBuilder Class Structure

**Estimate**: 10h
**Description**: Create `CTEBuilder` class in `fhir4ds/fhirpath/sql/cte.py` with method stubs for building CTE chains from SQL fragments. Includes `__init__`, `build_cte_chain()`, `_fragment_to_cte()`, and placeholder methods for UNNEST operations.

**Key Deliverables**:
- `CTEBuilder` class structure
- Method signatures and docstrings
- Dialect injection via constructor

**Acceptance Criteria**:
- Class instantiates with dialect parameter
- Method signatures match PEP-004 specification
- Docstrings explain each method's purpose
- Architecture review approved

**Implementation Notes**:
```python
class CTEBuilder:
    def __init__(self, dialect: DatabaseDialect):
        self.dialect = dialect
        self.cte_counter = 0

    def build_cte_chain(self, fragments: List[SQLFragment]) -> List[CTE]:
        """Convert sequence of SQL fragments into CTE chain."""
        pass  # To be implemented in Phase 2-3

    def _fragment_to_cte(self, fragment: SQLFragment, previous_cte: Optional[str]) -> CTE:
        """Convert single fragment to CTE."""
        pass  # To be implemented in Phase 2-3
```

---

### SP-011-003: Implement CTEAssembler Class Structure

**Estimate**: 10h
**Description**: Create `CTEAssembler` class in `fhir4ds/fhirpath/sql/cte.py` with method stubs for assembling CTEs into monolithic SQL queries. Includes `__init__`, `assemble_query()`, `_order_ctes_by_dependencies()`, `_generate_with_clause()`, and `_generate_final_select()`.

**Key Deliverables**:
- `CTEAssembler` class structure
- Method signatures and docstrings
- Dialect injection via constructor

**Acceptance Criteria**:
- Class instantiates with dialect parameter
- Method signatures match PEP-004 specification
- Docstrings explain assembly process
- Architecture review approved

**Implementation Notes**:
```python
class CTEAssembler:
    def __init__(self, dialect: DatabaseDialect):
        self.dialect = dialect

    def assemble_query(self, ctes: List[CTE]) -> str:
        """Assemble CTE chain into complete SQL query."""
        pass  # To be implemented in Phase 3

    def _order_ctes_by_dependencies(self, ctes: List[CTE]) -> List[CTE]:
        """Topological sort of CTEs by dependencies."""
        pass  # To be implemented in Phase 3
```

---

### SP-011-004: Unit Tests for CTE Data Structures

**Estimate**: 12h
**Description**: Create comprehensive unit tests for `CTE` dataclass, `CTEBuilder` structure, and `CTEAssembler` structure in `tests/unit/fhirpath/sql/test_cte_data_structures.py`. Tests verify dataclass behavior, field defaults, and class instantiation.

**Key Deliverables**:
- 50+ unit tests covering CTE dataclass
- Tests for field defaults and validation
- Tests for class instantiation

**Acceptance Criteria**:
- 50+ tests passing
- 90%+ coverage for Phase 1 code
- All dataclass fields tested
- No regressions

**Test Categories**:
- CTE dataclass creation (10 tests)
- Field defaults and mutations (10 tests)
- CTEBuilder instantiation (10 tests)
- CTEAssembler instantiation (10 tests)
- Edge cases and validation (10+ tests)

---

## Phase 2: Array UNNEST Support (Week 2, Days 7-12)

### SP-011-005: Implement `_wrap_unnest_query()` in CTEBuilder

**Estimate**: 12h
**Description**: Implement `_wrap_unnest_query()` method in `CTEBuilder` that wraps SQL fragments requiring array flattening in LATERAL UNNEST operations. Calls dialect methods for database-specific UNNEST syntax.

**Key Deliverables**:
- `_wrap_unnest_query()` implementation
- UNNEST SQL generation logic
- Dialect method calls

**Acceptance Criteria**:
- UNNEST queries generated correctly
- Calls dialect `generate_lateral_unnest()` method
- Handles simple and nested arrays
- Integration with `build_cte_chain()` working

**Implementation Strategy**:
1. Extract array path from fragment metadata
2. Generate unique CTE name and array alias
3. Call dialect method for UNNEST syntax
4. Wrap in SELECT with FROM and LATERAL clauses
5. Return SQLFragment with UNNEST query

---

### SP-011-006: Add `generate_lateral_unnest()` to DuckDB Dialect

**Estimate**: 8h
**Description**: Add `generate_lateral_unnest()` method to DuckDB dialect (`fhir4ds/fhirpath/dialects/duckdb.py`) that generates DuckDB-specific LATERAL UNNEST syntax.

**Key Deliverables**:
- `generate_lateral_unnest()` method in DuckDB dialect
- Correct DuckDB UNNEST syntax
- Unit tests for method

**Acceptance Criteria**:
- Method generates correct DuckDB syntax: `LATERAL UNNEST(array) AS alias`
- Handles JSON array unnesting
- Tests passing (DuckDB-specific)

**DuckDB Syntax Example**:
```sql
SELECT id, name_item
FROM cte_1, LATERAL UNNEST(cte_1.names) AS name_item
```

---

### SP-011-007: Add `generate_lateral_unnest()` to PostgreSQL Dialect

**Estimate**: 8h
**Description**: Add `generate_lateral_unnest()` method to PostgreSQL dialect (`fhir4ds/fhirpath/dialects/postgresql.py`) that generates PostgreSQL-specific LATERAL UNNEST syntax.

**Key Deliverables**:
- `generate_lateral_unnest()` method in PostgreSQL dialect
- Correct PostgreSQL UNNEST syntax
- Unit tests for method

**Acceptance Criteria**:
- Method generates correct PostgreSQL syntax: `LATERAL jsonb_array_elements(array) AS alias`
- Handles JSONB array unnesting
- Tests passing (PostgreSQL-specific)

**PostgreSQL Syntax Example**:
```sql
SELECT id, name_item
FROM cte_1, LATERAL jsonb_array_elements(cte_1.names) AS name_item
```

---

### SP-011-008: Unit Tests for UNNEST Generation and Integration

**Estimate**: 12h
**Description**: Create comprehensive unit tests for UNNEST generation in `tests/unit/fhirpath/sql/test_cte_unnest.py`. Tests cover both DuckDB and PostgreSQL UNNEST syntax, simple and nested arrays, and integration with CTEBuilder.

**Key Deliverables**:
- 40+ unit tests for UNNEST generation
- Multi-database validation tests
- Integration tests with CTEBuilder

**Acceptance Criteria**:
- 40+ tests passing
- Both dialects validated
- Simple and nested array cases covered
- Integration with PEP-003 fragments validated

**Test Categories**:
- DuckDB UNNEST syntax (10 tests)
- PostgreSQL UNNEST syntax (10 tests)
- Simple array unnesting (5 tests)
- Nested array unnesting (5 tests)
- Integration with CTEBuilder (10+ tests)

---

## Phase 3: CTE Assembly and Dependencies (Week 3, Days 13-18)

### SP-011-009: Implement Topological Sort for CTE Dependencies

**Estimate**: 10h
**Description**: Implement `_order_ctes_by_dependencies()` method in `CTEAssembler` using topological sort algorithm. Ensures CTEs are ordered such that dependencies are defined before being referenced. Includes circular dependency detection.

**Key Deliverables**:
- Topological sort implementation
- Circular dependency detection
- Dependency graph construction

**Acceptance Criteria**:
- CTEs ordered correctly by dependencies
- Circular dependencies detected and reported
- Works with complex dependency graphs
- Unit tests passing

**Algorithm**: Standard topological sort with cycle detection (Kahn's algorithm or DFS-based)

---

### SP-011-010: Implement `_generate_with_clause()`

**Estimate**: 8h
**Description**: Implement `_generate_with_clause()` method in `CTEAssembler` that generates the WITH clause from ordered CTEs. Formats multiple CTEs with proper SQL syntax.

**Key Deliverables**:
- `_generate_with_clause()` implementation
- Proper WITH clause formatting
- Handles single and multiple CTEs

**Acceptance Criteria**:
- WITH clause syntax correct
- Multiple CTEs formatted properly (comma-separated)
- Single CTE case handled
- Unit tests passing

**Output Format**:
```sql
WITH
  cte_1 AS (query1),
  cte_2 AS (query2),
  cte_3 AS (query3)
```

---

### SP-011-011: Implement `_generate_final_select()`

**Estimate**: 6h
**Description**: Implement `_generate_final_select()` method in `CTEAssembler` that generates the final SELECT statement from the last CTE in the chain.

**Key Deliverables**:
- `_generate_final_select()` implementation
- SELECT statement generation

**Acceptance Criteria**:
- Final SELECT syntax correct: `SELECT * FROM <last_cte>`
- Handles empty CTE list gracefully
- Unit tests passing

---

### SP-011-012: Unit Tests for Assembly Logic and Integration

**Estimate**: 16h
**Description**: Create comprehensive unit tests for CTE assembly logic in `tests/unit/fhirpath/sql/test_cte_assembly.py` and `tests/integration/fhirpath/test_cte_integration.py`. Tests cover topological sort, WITH clause generation, final SELECT, and end-to-end CTE assembly.

**Key Deliverables**:
- 50+ unit tests for assembly logic
- Integration tests with real FHIRPath expressions
- End-to-end validation

**Acceptance Criteria**:
- 50+ tests passing
- Topological sort tested thoroughly
- WITH clause generation validated
- Real FHIRPath expressions execute successfully
- Both DuckDB and PostgreSQL tested

**Test Categories**:
- Topological sort correctness (15 tests)
- Circular dependency detection (5 tests)
- WITH clause formatting (10 tests)
- Final SELECT generation (5 tests)
- End-to-end assembly (15+ tests)

---

## Phase 4: Integration, Testing, Documentation (Week 4, Days 19-25)

### SP-011-013: End-to-End Integration with PEP-003 Translator

**Estimate**: 10h
**Description**: Implement complete integration between PEP-003 translator output (`List[SQLFragment]`) and CTE infrastructure. Validate all Path Navigation FHIRPath expressions execute successfully end-to-end.

**Key Deliverables**:
- Complete integration working
- All Path Navigation expressions execute
- Multi-step expression handling

**Acceptance Criteria**:
- PEP-003 translator → CTEBuilder → CTEAssembler → SQL execution pipeline working
- 10/10 Path Navigation expressions attempt execution
- Both DuckDB and PostgreSQL validated
- Integration tests passing

---

### SP-011-014: Validate Against Official FHIRPath Test Suite

**Estimate**: 8h
**Description**: Execute official FHIRPath test suite Path Navigation category (10 tests) and validate results. Target 8/10 tests passing minimum for Sprint 011 success.

**Key Deliverables**:
- Official test suite execution results
- Pass/fail analysis for all 10 tests
- Documentation of failures (if any)

**Acceptance Criteria**:
- 8/10 Path Navigation tests passing minimum
- Overall FHIRPath compliance: 72%+ achieved
- Zero regressions in other categories
- Test results documented with evidence

**Test Runner**: `PYTHONPATH=. python3 tests/integration/fhirpath/official_test_runner.py`

---

### SP-011-015: Performance Benchmarking and Optimization

**Estimate**: 8h
**Description**: Execute performance benchmarking suite for CTE generation and query execution. Validate <10ms CTE generation target and 10x+ execution improvement.

**Key Deliverables**:
- Performance benchmark results
- CTE generation time measurements
- Query execution time comparisons

**Acceptance Criteria**:
- CTE generation: <10ms for typical expressions
- Query execution: 10x+ improvement vs. row-by-row (if measurable)
- Memory usage: <100MB for complex CTEs
- Performance regression tests passing

---

### SP-011-016: API Documentation and Architecture Docs Updates

**Estimate**: 12h
**Description**: Create comprehensive API documentation for CTE infrastructure and update architecture documentation with CTE infrastructure diagrams and integration guides.

**Key Deliverables**:
- API documentation (CTEBuilder, CTEAssembler, CTE)
- Architecture documentation updates
- Integration guide for developers
- Usage examples and tutorials

**Acceptance Criteria**:
- API documentation complete for all public classes and methods
- Architecture diagrams updated with CTE infrastructure (Layers 3 & 4)
- Integration guide created showing PEP-003 → CTE → Database pipeline
- Usage examples demonstrate common scenarios
- Documentation review approved

---

## Task Dependencies Diagram

```
Phase 1:
SP-011-001 (CTE dataclass)
    ├── SP-011-002 (CTEBuilder structure)
    ├── SP-011-003 (CTEAssembler structure)
    └── SP-011-004 (Unit tests Phase 1)

Phase 2:
SP-011-002 (CTEBuilder) → SP-011-005 (wrap_unnest_query)
                              ├── SP-011-006 (DuckDB UNNEST)
                              ├── SP-011-007 (PostgreSQL UNNEST)
                              └── SP-011-008 (Unit tests Phase 2)

Phase 3:
SP-011-003 (CTEAssembler) → SP-011-009 (Topological sort)
                                → SP-011-010 (WITH clause)
                                    → SP-011-011 (Final SELECT)
                                        → SP-011-012 (Unit tests Phase 3)

Phase 4:
SP-011-012 (Integration tests) → SP-011-013 (End-to-end integration)
                                      ├── SP-011-014 (Official tests)
                                      ├── SP-011-015 (Performance)
                                      └── SP-011-016 (Documentation)
```

---

## Critical Path

**Critical Path Tasks** (must complete on schedule):
1. SP-011-001: CTE dataclass (Day 1-2)
2. SP-011-002: CTEBuilder structure (Day 2-3)
3. SP-011-005: UNNEST implementation (Day 7-8)
4. SP-011-009: Topological sort (Day 13-14)
5. SP-011-013: End-to-end integration (Day 19-20)
6. SP-011-014: Official test validation (Day 21-22)

**Buffer Tasks** (can compress if needed):
- SP-011-004: Unit tests Phase 1 (can reduce test count if time-constrained)
- SP-011-015: Performance benchmarking (can defer minor optimizations)
- SP-011-016: Documentation (core docs required, polish can defer)

---

## Quality Gates

### Phase 1 Quality Gate (End of Week 1)
- [ ] Architecture review approved for all classes
- [ ] 50+ unit tests passing
- [ ] No linting errors
- [ ] Senior architect sign-off

### Phase 2 Quality Gate (End of Week 2)
- [ ] UNNEST working for both DuckDB and PostgreSQL
- [ ] 90+ total unit tests passing
- [ ] Multi-database parity validated
- [ ] Senior architect sign-off

### Phase 3 Quality Gate (End of Week 3)
- [ ] End-to-end FHIRPath expressions executing
- [ ] 140+ total unit tests passing
- [ ] CTE assembly working correctly
- [ ] Senior architect sign-off

### Phase 4 Quality Gate (End of Week 4)
- [ ] 8/10 Path Navigation tests passing minimum
- [ ] 72%+ overall FHIRPath compliance
- [ ] Documentation complete
- [ ] Sprint 011 goals achieved
- [ ] Senior architect final approval

---

## Risk Mitigation by Task

| Task | Primary Risk | Mitigation | Contingency |
|------|-------------|------------|-------------|
| SP-011-005 | UNNEST complexity | Incremental implementation, senior review | DuckDB first, PostgreSQL as Phase 2.5 |
| SP-011-009 | Topological sort bugs | Standard algorithm, comprehensive tests | Use library implementation if needed |
| SP-011-013 | Integration issues | PEP-003 output format validated | Adapter layer if format mismatch |
| SP-011-014 | Path Navigation tests fail | Focus on 8/10 minimum, not all 10 | Defer 2 edge cases to Sprint 012 |

---

**Document Created**: 2025-10-19 by Senior Solution Architect/Engineer
**Purpose**: Comprehensive task reference for Sprint 011 PEP-004 implementation
**Usage**: Reference for task breakdown, dependencies, and success criteria

---

*This task summary provides a complete overview of all 16 Sprint 011 tasks, enabling systematic implementation of PEP-004 CTE infrastructure.*
