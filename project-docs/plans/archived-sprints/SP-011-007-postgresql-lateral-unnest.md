# Task SP-011-007: Add `generate_lateral_unnest()` to PostgreSQL Dialect

**Task ID**: SP-011-007
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Add `generate_lateral_unnest()` to PostgreSQL Dialect
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `generate_lateral_unnest()` method in the PostgreSQLDialect class to generate PostgreSQL-specific LATERAL UNNEST syntax for array flattening operations using `jsonb_array_elements()`. This method is called by CTEBuilder._wrap_unnest_query() to produce database-specific SQL, maintaining the thin dialect architecture principle where dialects provide ONLY syntax differences, not business logic.

**PostgreSQL UNNEST Syntax**: `LATERAL jsonb_array_elements({array_expression}) AS {alias}`

This task implements the second of two dialect-specific methods required for Phase 2 UNNEST support (the other being SP-011-006 for DuckDB). The implementation must produce syntactically correct PostgreSQL UNNEST SQL that can be embedded in SELECT statements for JSON array flattening.

**Context**: PostgreSQL requires `jsonb_array_elements()` for unnesting JSONB arrays, which differs from DuckDB's simpler `UNNEST()` function. Both implementations maintain identical business logic (array flattening) with only syntax differences.

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

1. **Method Implementation**: Add `generate_lateral_unnest()` method to PostgreSQLDialect class:
   - Method signature: `def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str`
   - Returns PostgreSQL LATERAL UNNEST SQL fragment using `jsonb_array_elements()`
   - No business logic (syntax only)

2. **PostgreSQL Syntax Generation**: Generate correct PostgreSQL UNNEST syntax:
   - Format: `LATERAL jsonb_array_elements({array_column}) AS {alias}`
   - Example: `LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item`

3. **Parameter Handling**:
   - `source_table`: Table/CTE name (not used in PostgreSQL UNNEST, kept for interface consistency)
   - `array_column`: Full SQL expression for JSONB array column
   - `alias`: Alias for unnested items (e.g., "name_item")

4. **Type Safety**: Full type hints for parameters and return value

5. **Documentation**: Comprehensive docstring with Args, Returns, and Example

### Non-Functional Requirements

- **Performance**: Syntax generation <1ms (simple string formatting)
- **Compliance**: Implements PEP-004 Appendix C (PostgreSQL UNNEST Syntax)
- **Database Support**: Syntax valid for PostgreSQL 12+ (project minimum version)
- **Error Handling**: No validation needed (CTEBuilder validates inputs)

### Acceptance Criteria

- [ ] `generate_lateral_unnest()` method added to PostgreSQLDialect class
- [ ] Method signature matches interface: `(source_table: str, array_column: str, alias: str) -> str`
- [ ] Returns correct PostgreSQL syntax: `LATERAL jsonb_array_elements({array_column}) AS {alias}`
- [ ] Full type hints present
- [ ] Comprehensive docstring with Args, Returns, Example
- [ ] No business logic (thin dialect principle maintained)
- [ ] Code passes lint checks
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

- **fhir4ds/dialects/postgresql.py**: Add `generate_lateral_unnest()` method to PostgreSQLDialect class

### File Modifications

- **fhir4ds/dialects/postgresql.py** (MODIFY):
  - Add new method `generate_lateral_unnest()` to PostgreSQLDialect class
  - Add imports if needed (typing)
  - Add comprehensive docstring

### Database Considerations

- **PostgreSQL**: LATERAL UNNEST syntax using `jsonb_array_elements()`
  - Syntax: `LATERAL jsonb_array_elements(jsonb_column) AS alias`
  - Works with JSONB arrays from resource data
  - Comma-separated in FROM clause (implicit CROSS JOIN)
  - Returns JSONB elements (not text)
- **DuckDB**: Not affected (separate task SP-011-006)
- **Schema Changes**: None (dialect method only)

---

## Dependencies

### Prerequisites

1. **PostgreSQLDialect Class**: ✅ Exists (from PEP-003)
2. **DatabaseDialect Interface**: ✅ Complete (PEP-003 base class)
3. **SP-011-005**: ✅ Can be implemented in parallel (calls this method)
4. **PostgreSQL Driver** (psycopg2): ✅ Available (project dependency)

### Blocking Tasks

None - can be implemented in parallel with SP-011-005 and SP-011-006

### Dependent Tasks

- **SP-011-005**: CTEBuilder._wrap_unnest_query() implementation (calls this method)
- **SP-011-008**: Unit tests for UNNEST generation (validates this method)

---

## Implementation Approach

### High-Level Strategy

Add a simple method to PostgreSQLDialect that returns a formatted string with PostgreSQL's LATERAL `jsonb_array_elements()` syntax. The implementation is straightforward string formatting with no business logic, maintaining the thin dialect principle.

**Key Design Decisions**:
1. **Use jsonb_array_elements()**: PostgreSQL function for JSONB array unnesting
2. **Simple String Formatting**: No validation, no logic, just syntax generation
3. **source_table Unused**: Keep parameter for interface consistency with DuckDB
4. **LATERAL Keyword**: PostgreSQL requires LATERAL for correlated subqueries

### Implementation Steps

1. **Locate PostgreSQLDialect Class** (0.5 hours)
   - Open `fhir4ds/dialects/postgresql.py`
   - Identify PostgreSQLDialect class definition
   - Review existing methods for style consistency
   - **Validation**: Class located, existing patterns understood

2. **Add Method Signature** (0.5 hours)
   - Add method: `def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:`
   - Add type hints for all parameters
   - Add return type hint: `-> str`
   - **Validation**: Method signature correct with type hints

3. **Implement PostgreSQL UNNEST Syntax** (1 hour)
   - Return statement: `return f"LATERAL jsonb_array_elements({array_column}) AS {alias}"`
   - No validation needed (CTEBuilder handles that)
   - No business logic (syntax only)
   - **Validation**: Syntax generation correct

4. **Add Comprehensive Docstring** (1 hour)
   - Purpose: "Generate PostgreSQL LATERAL UNNEST syntax using jsonb_array_elements()"
   - Args:
     - `source_table`: Not used in PostgreSQL syntax, kept for interface consistency
     - `array_column`: SQL expression for JSONB array
     - `alias`: Alias for unnested JSONB elements
   - Returns: PostgreSQL LATERAL UNNEST SQL fragment
   - Note: Uses `jsonb_array_elements()` which returns JSONB (not text)
   - Example showing typical usage and output
   - **Validation**: Docstring complete, follows project standards

5. **Verify Type Hints and Style** (0.5 hours)
   - Run mypy on modified file
   - Check code style matches existing PostgreSQLDialect methods
   - Ensure no business logic added
   - **Validation**: Type checking passes, style consistent

6. **Manual Testing** (1 hour)
   - Create PostgreSQLDialect instance
   - Call `generate_lateral_unnest()` with sample parameters
   - Verify output matches expected PostgreSQL syntax
   - Test with various JSONB array expressions
   - **Validation**: Generated SQL is correct PostgreSQL syntax

7. **Code Review** (0.5 hours)
   - Request senior architect review
   - Verify thin dialect principle maintained
   - Confirm parity with DuckDB dialect (same business logic, different syntax)
   - **Validation**: Architecture compliance approved

**Estimated Time**: 5h total (same as SP-011-006)

### Alternative Approaches Considered

- **Use json_array_elements()**: Use JSON version instead of JSONB - **Rejected** (JSONB is more efficient, project uses JSONB)
- **Add CAST to TEXT**: Cast results to text - **Rejected** (keep as JSONB for downstream operations)
- **Validation in Dialect Method**: Validate parameters - **Rejected** (violates thin dialect, CTEBuilder handles validation)

---

## Testing Strategy

### Unit Testing

**New Tests Required** (implemented in SP-011-008):
- `test_postgresql_generate_lateral_unnest_basic()`: Basic UNNEST generation
- `test_postgresql_generate_lateral_unnest_complex_array_expr()`: Complex array expression
- `test_postgresql_generate_lateral_unnest_custom_alias()`: Custom alias
- `test_postgresql_generate_lateral_unnest_ignores_source_table()`: Verifies source_table not in output
- `test_postgresql_vs_duckdb_unnest_business_logic_parity()`: Verifies identical business logic, different syntax

**Coverage Target**: 100% coverage of `generate_lateral_unnest()` method

### Integration Testing

**Integration with CTEBuilder** (SP-011-008):
- CTEBuilder calls PostgreSQL dialect method correctly
- Generated UNNEST embedded in SELECT statement
- Multi-level UNNEST (nested arrays)

**Database Execution** (SP-011-008):
- Execute generated SQL in real PostgreSQL database (or mocked connection)
- Verify array flattening works correctly
- Compare results with DuckDB (identical business logic)

### Compliance Testing

**PostgreSQL Syntax Validation**:
- Generated SQL is valid PostgreSQL 12+ syntax
- `jsonb_array_elements()` works with JSONB arrays
- Results match PostgreSQL documentation examples

**Multi-Database Parity** (SP-011-008):
- DuckDB and PostgreSQL generate equivalent results
- Only syntax differs, business logic identical

### Manual Testing

**Test Scenarios**:
1. Simple array: `json_extract(resource, '$.name')`
2. Nested path: `json_extract(name_item, '$.given')`
3. Various aliases: "item", "name_item", "telecom_item"

**Edge Cases**:
- Very long array expressions
- JSONB vs JSON compatibility

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PostgreSQL syntax changes in future versions | Low | Low | Use documented syntax, test with project's minimum PostgreSQL version |
| JSONB vs JSON compatibility issues | Low | Medium | Use JSONB consistently (project standard) |
| Performance issues with large arrays | Low | Medium | Accept for MVP, PostgreSQL handles optimization |

### Implementation Challenges

1. **PostgreSQL Version Compatibility**: Ensure `jsonb_array_elements()` available in PostgreSQL 12+
   - **Approach**: Test with PostgreSQL 12+ (project minimum), verify in SP-011-008

2. **JSONB Element Type**: Ensure downstream operations work with JSONB elements
   - **Approach**: Consistent JSONB usage throughout pipeline

### Contingency Plans

- **If jsonb_array_elements() unavailable**: Check PostgreSQL version, use alternative function if needed
- **If performance issues arise**: Document in SP-011-008, defer optimization to future sprint

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review PostgreSQL docs, existing dialect methods)
- **Implementation**: 3h (method signature, syntax generation, docstring)
- **Testing**: 1h (manual testing with PostgreSQL)
- **Review and Refinement**: 0.5h (code review, parity check with DuckDB)
- **Total Estimate**: 5h (same as SP-011-006)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Very similar to SP-011-006 (DuckDB), just different syntax. PostgreSQL `jsonb_array_elements()` is well-documented and stable. Same pattern as DuckDB dialect.

### Factors Affecting Estimate

- **PostgreSQL Documentation Review**: +0.5h if syntax more complex than expected
- **JSONB Compatibility**: +0.5h if JSONB element handling requires adjustments

---

## Success Metrics

### Quantitative Measures

- **Implementation Complete**: `generate_lateral_unnest()` method added to PostgreSQLDialect
- **Code Quality**: 0 lint errors, 100% type hint coverage
- **Syntax Correctness**: Generated SQL valid in PostgreSQL 12+
- **Multi-Database Parity**: Identical business logic with DuckDB (SP-011-006)

### Qualitative Measures

- **Code Quality**: Clean, simple, follows PostgreSQLDialect patterns
- **Architecture Alignment**: Thin dialect principle maintained (syntax only, no business logic)
- **Maintainability**: Easy to understand and modify if PostgreSQL syntax changes

### Compliance Impact

- **Specification Compliance**: Implements PEP-004 Appendix C (PostgreSQL UNNEST Syntax)
- **Dialect Parity**: Completes multi-database support for UNNEST operations

---

## Documentation Requirements

### Code Documentation

- [x] Comprehensive method docstring (purpose, args, returns, note about JSONB, example)
- [x] Type hints for all parameters and return value
- [x] Example in docstring showing typical usage and output

### Architecture Documentation

- [ ] No ADR needed (implements PEP-004 specification)
- [ ] Update PEP-004 implementation status (PostgreSQL dialect extension complete)

### User Documentation

Not applicable for internal dialect method.

---

## Progress Tracking

### Status
- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [x] In Testing
- [ ] In Review
- [x] Completed
- [ ] Blocked

**Current Status**: completed - pending review

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | None | Begin implementation |
| 2025-10-20 | In Development | Implemented dialect `generate_lateral_unnest()` with unit test | None | Run broader dialect regressions |
| 2025-10-20 | In Testing | Ran targeted pytest for dialect UNNEST generation | Live PostgreSQL instance unavailable for manual verification | Coordinate with SP-011-008 for integration tests |
| 2025-10-20 | Completed - Pending Review | Ready for senior architect review after doc/test updates | Manual DB verification deferred until PostgreSQL environment available | Await review feedback and rerun manual check when environment returns |

### Completion Checklist

- [x] PostgreSQLDialect class located
- [x] `generate_lateral_unnest()` method signature added
- [x] PostgreSQL UNNEST syntax implementation complete
- [x] Comprehensive docstring added (including JSONB note)
- [x] Type hints complete
- [x] Code passes lint checks
- [ ] Manual testing successful *(deferred: PostgreSQL environment unavailable 2025-10-20)*
- [x] Parity with DuckDB verified (same business logic)
- [ ] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches PEP-004 Appendix C
- [x] Thin dialect principle maintained (no business logic)
- [x] PostgreSQL syntax correct per documentation
- [x] Business logic identical to DuckDB (only syntax differs)
- [x] Code follows PostgreSQLDialect patterns
- [x] Documentation complete and accurate

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

## Implementation Example

### Method Implementation

```python
def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:
    """
    Generate PostgreSQL LATERAL UNNEST syntax using jsonb_array_elements().

    Args:
        source_table: Table/CTE name (not used in PostgreSQL syntax, kept for interface consistency)
        array_column: SQL expression for JSONB array to unnest
        alias: Alias for unnested JSONB elements

    Returns:
        PostgreSQL LATERAL UNNEST SQL fragment

    Note:
        Uses jsonb_array_elements() which returns JSONB elements (not text).
        For text extraction, downstream operations can use json_extract_text() or similar.

    Example:
        >>> dialect = PostgreSQLDialect()
        >>> unnest_sql = dialect.generate_lateral_unnest(
        ...     source_table="patient_resources",
        ...     array_column="json_extract(resource, '$.name')",
        ...     alias="name_item"
        ... )
        >>> print(unnest_sql)
        LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item
    """
    return f"LATERAL jsonb_array_elements({array_column}) AS {alias}"
```

### Usage Example (Called by CTEBuilder)

```python
# In CTEBuilder._wrap_unnest_query()
dialect = PostgreSQLDialect()
unnest_clause = dialect.generate_lateral_unnest(
    source_table="patient_resources",
    array_column="json_extract(resource, '$.name')",
    alias="name_item"
)
# unnest_clause = "LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item"

# Embed in SELECT statement
sql = f"""SELECT patient_resources.id, name_item
FROM patient_resources, {unnest_clause}"""

# Result:
# SELECT patient_resources.id, name_item
# FROM patient_resources, LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item
```

### Multi-Database Parity

```python
# DuckDB (SP-011-006)
duckdb_sql = duckdb_dialect.generate_lateral_unnest(
    source_table="patient_resources",
    array_column="json_extract(resource, '$.name')",
    alias="name_item"
)
# Result: "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"

# PostgreSQL (this task)
postgresql_sql = postgresql_dialect.generate_lateral_unnest(
    source_table="patient_resources",
    array_column="json_extract(resource, '$.name')",
    alias="name_item"
)
# Result: "LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item"

# Same business logic (array flattening), different syntax
# Both preserve patient IDs, both flatten arrays, both return population-scale results
```

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Not Started

---

*This task implements PostgreSQL-specific UNNEST syntax generation, completing multi-database support for array flattening while maintaining the thin dialect architecture principle.*
