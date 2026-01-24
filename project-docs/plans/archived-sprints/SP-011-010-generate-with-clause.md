# Task SP-011-010: Implement `_generate_with_clause()` Method

**Task ID**: SP-011-010
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Implement `_generate_with_clause()` Method
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `_generate_with_clause()` method in the CTEAssembler class to generate properly formatted WITH clauses from ordered CTE lists. This method takes topologically sorted CTEs and produces the WITH clause portion of the monolithic SQL query, handling multi-line CTE definitions, proper indentation, comma separation, and formatting consistency across database dialects.

**Context**: This task is the second component of Phase 3 (CTE Assembly and Dependencies). After SP-011-009 provides topologically sorted CTEs, this method formats them into the SQL WITH clause structure. The WITH clause is the first part of the monolithic query that defines all CTEs before the final SELECT statement. Proper formatting is critical for readability, debugging, and maintaining the thin dialect architecture.

**Example Output**:
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
    SELECT id, json_extract(name_item, '$.given') as result
    FROM cte_2
  )
```

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

1. **WITH Clause Generation**: Generate standard SQL WITH clause from CTE list
   - Start with "WITH" keyword
   - Format each CTE as: `cte_name AS (query)`
   - Separate CTEs with commas and newlines
   - No trailing comma after last CTE

2. **Multi-Line Query Formatting**: Handle multi-line CTE queries with proper indentation
   - Indent query body (4 spaces per level)
   - Preserve query structure (newlines, whitespace)
   - Ensure closing parenthesis on new line

3. **Empty CTE Handling**: Handle edge case of empty CTE list
   - Return empty string (no WITH clause needed)
   - Allow downstream code to handle gracefully

4. **Formatting Consistency**: Maintain consistent formatting across database dialects
   - Same indentation rules for DuckDB and PostgreSQL
   - Same comma/newline structure
   - Database-agnostic formatting (thin dialect principle)

5. **Query Trimming**: Remove extraneous whitespace from CTE queries
   - Strip leading/trailing whitespace from each query
   - Preserve internal query structure
   - Ensure clean, readable output

### Non-Functional Requirements

- **Performance**: O(N) time complexity where N = total characters across all CTE queries
- **Readability**: Generated SQL should be human-readable for debugging
- **Consistency**: Identical formatting across database dialects
- **Maintainability**: Simple, clear implementation easy to modify

### Acceptance Criteria

- [x] `_generate_with_clause()` method implemented in CTEAssembler
- [x] WITH keyword correctly positioned
- [x] CTEs formatted as `name AS (query)` with proper indentation
- [x] Commas correctly placed between CTEs (no trailing comma)
- [x] Multi-line queries indented consistently (4 spaces)
- [x] Empty CTE list returns empty string
- [x] Query whitespace trimmed appropriately
- [x] Unit tests written and passing (10+ tests)
- [x] Integration tests with topological sort passing
- [ ] Code review approved by Senior Solution Architect/Engineer
- [x] No business logic in dialect classes (formatting is database-agnostic)

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/cte.py**: Implement `_generate_with_clause()` in CTEAssembler class
  - Method signature: `def _generate_with_clause(self, ctes: List[CTE]) -> str`
  - Returns formatted WITH clause string (or empty string)
  - No error raising (assumes valid input from topological sort)

### File Modifications

- **fhir4ds/fhirpath/sql/cte.py** (MODIFY):
  - Implement `_generate_with_clause()` method body
  - Add helper for query indentation
  - Update docstrings with formatting examples

### Database Considerations

- **DuckDB**: No database-specific formatting (standard SQL WITH clause)
- **PostgreSQL**: No database-specific formatting (standard SQL WITH clause)
- **Schema Changes**: None (formatting implementation only)

---

## Dependencies

### Prerequisites

1. **SP-011-001**: ✅ Complete (CTE dataclass with name and query fields)
2. **SP-011-003**: ✅ Complete (CTEAssembler class structure)
3. **SP-011-009**: Must be complete (provides ordered CTEs for formatting)
4. **Python Standard Library**: ✅ Available (string manipulation)

### Blocking Tasks

- **SP-011-009**: Topological sort (provides ordered CTE input)

### Dependent Tasks

- **SP-011-011**: `_generate_final_select()` (combines WITH clause with SELECT)
- **SP-011-012**: Assembly unit tests (validates WITH clause formatting)

---

## Implementation Approach

### High-Level Strategy

Implement a straightforward string formatting approach that iterates through CTEs, formats each as `name AS (query)`, and joins them with commas and newlines. Focus on readability of generated SQL by using consistent indentation (4 spaces) for query bodies. The implementation should be simple, clear, and maintainable.

**Key Design Decisions**:
1. **Indentation**: Use 4 spaces per indent level (Python standard)
2. **Comma Placement**: Commas after CTEs except the last one
3. **Empty Handling**: Return empty string (not "WITH" with no CTEs)
4. **No Validation**: Trust topological sort output (validation done elsewhere)

### Implementation Steps

1. **Implement Empty CTE Handling** (0.5 hours)
   - Check if CTE list is empty
   - Return empty string immediately
   - **Validation**: Empty list returns "", not "WITH"

2. **Implement Query Indentation Helper** (1.5 hours)
   - Create helper method `_indent_query(query: str) -> str`
   - Split query by newlines
   - Add 4-space indent to each line
   - Handle empty lines (don't add trailing spaces)
   - **Validation**: Multi-line queries indented correctly

3. **Implement CTE Formatting** (2 hours)
   - For each CTE, format as: `{name} AS (\n{indented_query}\n)`
   - Strip whitespace from query before indenting
   - Ensure closing parenthesis on separate line
   - Collect formatted CTEs in list
   - **Validation**: Each CTE formatted correctly

4. **Implement Comma Joining** (1 hour)
   - Join formatted CTEs with ",\n"
   - Ensures comma after each CTE except last
   - **Validation**: Comma placement correct, no trailing comma

5. **Implement WITH Prefix** (0.5 hours)
   - Prepend "WITH\n" to joined CTEs
   - Use two-space indent for CTE definitions (standard SQL style)
   - **Validation**: WITH keyword positioned correctly

6. **Add Comprehensive Tests** (2 hours)
   - Test single CTE formatting
   - Test multiple CTE formatting
   - Test multi-line query indentation
   - Test empty CTE list
   - Test whitespace trimming
   - Test comma placement
   - **Validation**: 10+ tests passing

7. **Integration Testing** (1 hour)
   - Test with topologically sorted CTEs from SP-011-009
   - Verify formatting with real UNNEST CTEs from Phase 2
   - Test with CTEAssembler.assemble_query() integration
   - **Validation**: End-to-end WITH clause generation working

8. **Code Review and Refinement** (0.5 hours)
   - Self-review for code clarity
   - Check formatting consistency
   - Verify docstrings complete
   - Request senior architect code review
   - **Validation**: Code review approved

**Estimated Time**: 9h total (increased from 8h in sprint plan for comprehensive testing)

### Alternative Approaches Considered

- **Template-Based Formatting**: Use string templates - **Rejected** (less flexible, harder to maintain)
- **SQL Library**: Use sqlparse or similar - **Rejected** (adds dependency, overkill for simple formatting)
- **Dialect-Specific Formatting**: Different formatting per database - **Rejected** (violates thin dialect principle)

---

## Testing Strategy

### Unit Testing

**Test Organization** (in `tests/unit/fhirpath/sql/test_cte_data_structures.py`):

```python
class TestCTEAssemblerWithClause:
    """Validate WITH clause generation formatting."""

    def test_generate_with_clause_single_cte(self, assembler):
        """Single CTE formatted correctly."""
        ctes = [CTE(name="cte_1", query="SELECT * FROM resource", depends_on=[])]
        with_clause = assembler._generate_with_clause(ctes)
        expected = """WITH
  cte_1 AS (
    SELECT * FROM resource
  )"""
        assert with_clause == expected

    def test_generate_with_clause_multiple_ctes(self, assembler):
        """Multiple CTEs with comma separation."""
        ctes = [
            CTE(name="cte_1", query="SELECT id FROM resource", depends_on=[]),
            CTE(name="cte_2", query="SELECT id FROM cte_1", depends_on=["cte_1"])
        ]
        with_clause = assembler._generate_with_clause(ctes)
        assert "cte_1 AS (" in with_clause
        assert "cte_2 AS (" in with_clause
        assert with_clause.count(",") == 1  # One comma between two CTEs
        assert not with_clause.endswith(",")  # No trailing comma

    def test_generate_with_clause_multiline_query(self, assembler):
        """Multi-line query indented correctly."""
        query = """SELECT id, name
FROM resource
WHERE active = true"""
        ctes = [CTE(name="cte_1", query=query, depends_on=[])]
        with_clause = assembler._generate_with_clause(ctes)
        # Each line of query should be indented with 4 spaces
        assert "    SELECT id, name" in with_clause
        assert "    FROM resource" in with_clause
        assert "    WHERE active = true" in with_clause

    def test_generate_with_clause_empty_list(self, assembler):
        """Empty CTE list returns empty string."""
        with_clause = assembler._generate_with_clause([])
        assert with_clause == ""

    def test_generate_with_clause_strips_query_whitespace(self, assembler):
        """Leading/trailing whitespace removed from queries."""
        ctes = [CTE(name="cte_1", query="  SELECT * FROM resource  ", depends_on=[])]
        with_clause = assembler._generate_with_clause(ctes)
        # Should not have extra whitespace
        assert "  SELECT" not in with_clause  # No double-space indent
        assert "    SELECT" in with_clause      # Only 4-space indent

    # ... 5 more tests for edge cases, formatting consistency, etc.
```

**Test Coverage Requirements**:
- **Happy Path**: Single CTE, multiple CTEs, complex chains (5 tests)
- **Formatting**: Multi-line queries, indentation, comma placement (5 tests)
- **Edge Cases**: Empty list, single-line queries, whitespace handling (3 tests)
- **Integration**: With topological sort, with real UNNEST CTEs (2 tests)

### Integration Testing

- **With Topological Sort**: Order CTEs then generate WITH clause
- **With CTEAssembler**: Full assembly pipeline including WITH clause
- **With Real CTEs**: Use Phase 2 UNNEST CTEs for realistic testing

### Compliance Testing

- **SQL Standard**: Verify WITH clause follows SQL standard syntax
- **Multi-Database**: Ensure identical output for DuckDB and PostgreSQL
- **No Regression**: Existing tests continue passing

### Manual Testing

Not applicable - automated test suite is comprehensive.

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Indentation complexity | Low | Low | Use simple 4-space indent, comprehensive tests |
| Comma placement errors | Low | Medium | Explicit tests for comma count and placement |
| Multi-line query issues | Low | Medium | Test various query structures, preserve newlines |
| Whitespace handling bugs | Low | Low | Strip before indenting, test edge cases |

### Implementation Challenges

1. **Consistent Indentation**: Ensuring all query lines indented uniformly
   - **Approach**: Split by newline, indent each line, rejoin

2. **Comma Placement**: Avoiding trailing comma after last CTE
   - **Approach**: Use join(",\n") which naturally handles this

### Contingency Plans

- **If formatting proves complex**: Start with simple case (single-line queries), enhance later
- **If indentation difficult**: Use simpler formatting initially, improve in refinement
- **If timeline extends**: Defer perfect formatting, focus on correct SQL generation first

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review SQL WITH clause standards)
- **Implementation**: 5.5h (empty handling, indentation, formatting, joining)
- **Testing**: 2h (unit tests, edge cases, integration tests)
- **Documentation**: 0.5h (docstrings, formatting examples)
- **Review and Refinement**: 0.5h (self-review, senior review)
- **Total Estimate**: 9h (increased from 8h for comprehensive testing)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: String formatting is straightforward in Python. Primary work is in handling multi-line queries and ensuring consistent indentation. Testing will be thorough but simple.

### Factors Affecting Estimate

- **Edge Case Discovery**: +1h if testing reveals formatting edge cases
- **Indentation Complexity**: +1h if multi-line query handling more complex than expected
- **Integration Issues**: +1h if topological sort output requires special handling

---

## Success Metrics

### Quantitative Measures

- **Test Count**: 10+ tests implemented for WITH clause generation
- **Test Pass Rate**: 100% (all tests passing)
- **Code Coverage**: 100% for `_generate_with_clause()` method
- **Performance**: <1ms for typical CTE chains (<20 CTEs)
- **Formatting Consistency**: Identical output for DuckDB and PostgreSQL

### Qualitative Measures

- **Code Quality**: Clean, readable string formatting implementation
- **SQL Readability**: Generated WITH clauses easy to read and debug
- **Maintainability**: Simple implementation easy to modify

### Compliance Impact

- **Specification Compliance**: Generates standard SQL WITH clause syntax
- **Architecture Alignment**: Maintains thin dialect principle (database-agnostic)
- **Sprint Goal**: Critical component for Phase 3 completion

---

## Documentation Requirements

### Code Documentation

- [x] Method docstring with formatting examples
- [x] Inline comments for indentation logic
- [x] Helper method documentation
- [x] Example input/output in docstring

### Architecture Documentation

- [x] No ADR needed (standard SQL formatting)
- [x] No architecture changes

### User Documentation

Not applicable for internal formatting method.

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

**Current Status**: Completed - Pending Review (2025-10-20)

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | Awaiting SP-011-009 completion | Begin implementation after topological sort ready |
| 2025-10-20 | Completed - Pending Review | Implemented WITH clause formatting helpers, added 10 targeted unit tests, ran full CTE data structure suite | None | Await senior architect review and feedback |

### Completion Checklist

- [x] Empty CTE list handling implemented
- [x] Query indentation helper implemented
- [x] CTE formatting logic implemented
- [x] Comma joining implemented
- [x] WITH prefix implemented
- [x] 10+ unit tests written and passing
- [x] Integration tests passing
- [x] Code coverage 100% for method
- [x] Formatting consistent across dialects
- [x] Self-review complete
- [ ] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation follows SQL WITH clause standards
- [x] Indentation consistent (4 spaces)
- [x] Comma placement correct (no trailing comma)
- [x] Empty CTE list handled correctly
- [x] Multi-line queries formatted properly
- [x] Code is clean, readable, well-documented
- [x] Unit tests cover all formatting scenarios
- [x] Integration with topological sort working
- [x] No business logic in dialect classes

**Notes**: Implementation validated with comprehensive unit coverage and integration tests in the CTE data structure suite.

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
**Status**: Not Started (Awaiting SP-011-009 Completion)

---

*This task implements WITH clause generation for CTE assembly, formatting topologically sorted CTEs into standard SQL WITH clause structure with proper indentation and comma separation.*
