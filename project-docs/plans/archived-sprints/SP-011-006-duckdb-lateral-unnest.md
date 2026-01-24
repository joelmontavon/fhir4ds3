# Task SP-011-006: Add `generate_lateral_unnest()` to DuckDB Dialect

**Task ID**: SP-011-006
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Add `generate_lateral_unnest()` to DuckDB Dialect
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `generate_lateral_unnest()` method in the DuckDBDialect class to generate DuckDB-specific LATERAL UNNEST syntax for array flattening operations. This method is called by CTEBuilder._wrap_unnest_query() to produce database-specific SQL, maintaining the thin dialect architecture principle where dialects provide ONLY syntax differences, not business logic.

**DuckDB UNNEST Syntax**: `LATERAL UNNEST(array_expression) AS alias`

This task implements one of two dialect-specific methods required for Phase 2 UNNEST support (the other being SP-011-007 for PostgreSQL). The implementation must produce syntactically correct DuckDB UNNEST SQL that can be embedded in SELECT statements for array flattening.

**Context**: DuckDB uses a simpler UNNEST syntax compared to PostgreSQL. The method generates a SQL fragment that will be embedded in a FROM clause to flatten JSON arrays from FHIR resources.

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

1. **Method Implementation**: Add `generate_lateral_unnest()` method to DuckDBDialect class:
   - Method signature: `def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str`
   - Returns DuckDB LATERAL UNNEST SQL fragment
   - No business logic (syntax only)

2. **DuckDB Syntax Generation**: Generate correct DuckDB UNNEST syntax:
   - Format: `LATERAL UNNEST({array_column}) AS {alias}`
   - Example: `LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item`

3. **Parameter Handling**:
   - `source_table`: Table/CTE name (not used in DuckDB UNNEST, kept for interface consistency)
   - `array_column`: Full SQL expression for array column (e.g., "json_extract(resource, '$.name')")
   - `alias`: Alias for unnested items (e.g., "name_item")

4. **Type Safety**: Full type hints for parameters and return value

5. **Documentation**: Comprehensive docstring with Args, Returns, and Example

### Non-Functional Requirements

- **Performance**: Syntax generation <1ms (simple string formatting)
- **Compliance**: Implements PEP-004 Appendix C (DuckDB UNNEST Syntax)
- **Database Support**: Syntax valid for DuckDB 0.8+ (project minimum version)
- **Error Handling**: No validation needed (CTEBuilder validates inputs)

### Acceptance Criteria

- [ ] `generate_lateral_unnest()` method added to DuckDBDialect class
- [ ] Method signature matches interface: `(source_table: str, array_column: str, alias: str) -> str`
- [ ] Returns correct DuckDB syntax: `LATERAL UNNEST({array_column}) AS {alias}`
- [ ] Full type hints present
- [ ] Comprehensive docstring with Args, Returns, Example
- [ ] No business logic (thin dialect principle maintained)
- [ ] Code passes lint checks
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

- **fhir4ds/dialects/duckdb.py**: Add `generate_lateral_unnest()` method to DuckDBDialect class

### File Modifications

- **fhir4ds/dialects/duckdb.py** (MODIFY):
  - Add new method `generate_lateral_unnest()` to DuckDBDialect class
  - Add imports if needed (typing)
  - Add comprehensive docstring

### Database Considerations

- **DuckDB**: LATERAL UNNEST syntax for array unnesting
  - Syntax: `LATERAL UNNEST(array) AS alias`
  - Works with JSON arrays from `json_extract()`
  - Comma-separated in FROM clause (implicit CROSS JOIN)
- **PostgreSQL**: Not affected (separate task SP-011-007)
- **Schema Changes**: None (dialect method only)

---

## Dependencies

### Prerequisites

1. **DuckDBDialect Class**: ✅ Exists (from PEP-003)
2. **DatabaseDialect Interface**: ✅ Complete (PEP-003 base class)
3. **SP-011-005**: ✅ Can be implemented in parallel (calls this method)
4. **DuckDB Driver**: ✅ Available (project dependency)

### Blocking Tasks

None - can be implemented in parallel with SP-011-005

### Dependent Tasks

- **SP-011-005**: CTEBuilder._wrap_unnest_query() implementation (calls this method)
- **SP-011-008**: Unit tests for UNNEST generation (validates this method)

---

## Implementation Approach

### High-Level Strategy

Add a simple method to DuckDBDialect that returns a formatted string with DuckDB's LATERAL UNNEST syntax. The implementation is straightforward string formatting with no business logic, maintaining the thin dialect principle.

**Key Design Decisions**:
1. **Simple String Formatting**: No validation, no logic, just syntax generation
2. **source_table Unused**: Keep parameter for interface consistency, don't use in DuckDB syntax
3. **Direct String Return**: No intermediate variables needed for simple format

### Implementation Steps

1. **Locate DuckDBDialect Class** (0.5 hours)
   - Open `fhir4ds/dialects/duckdb.py`
   - Identify DuckDBDialect class definition
   - Review existing methods for style consistency
   - **Validation**: Class located, existing patterns understood

2. **Add Method Signature** (0.5 hours)
   - Add method: `def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:`
   - Add type hints for all parameters
   - Add return type hint: `-> str`
   - **Validation**: Method signature correct with type hints

3. **Implement DuckDB UNNEST Syntax** (1 hour)
   - Return statement: `return f"LATERAL UNNEST({array_column}) AS {alias}"`
   - No validation needed (CTEBuilder handles that)
   - No business logic (syntax only)
   - **Validation**: Syntax generation correct

4. **Add Comprehensive Docstring** (1 hour)
   - Purpose: "Generate DuckDB LATERAL UNNEST syntax for array flattening"
   - Args:
     - `source_table`: Not used in DuckDB syntax, kept for interface consistency
     - `array_column`: SQL expression for array (e.g., "json_extract(resource, '$.name')")
     - `alias`: Alias for unnested items (e.g., "name_item")
   - Returns: DuckDB UNNEST SQL fragment
   - Example showing typical usage and output
   - **Validation**: Docstring complete, follows project standards

5. **Verify Type Hints and Style** (0.5 hours)
   - Run mypy on modified file
   - Check code style matches existing DuckDBDialect methods
   - Ensure no business logic added
   - **Validation**: Type checking passes, style consistent

6. **Manual Testing** (1 hour)
   - Create DuckDBDialect instance
   - Call `generate_lateral_unnest()` with sample parameters
   - Verify output matches expected DuckDB syntax
   - Test with various array expressions
   - **Validation**: Generated SQL is correct DuckDB syntax

7. **Code Review** (0.5 hours)
   - Request senior architect review
   - Verify thin dialect principle maintained
   - **Validation**: Architecture compliance approved

**Estimated Time**: 5h total (reduced from 8h due to simplicity)

### Alternative Approaches Considered

- **Validation in Dialect Method**: Validate parameters before formatting - **Rejected** (violates thin dialect, CTEBuilder handles validation)
- **Template-Based Approach**: Use SQL templates - **Rejected** (unnecessary complexity for simple format)
- **Use source_table Parameter**: Incorporate source_table in syntax - **Rejected** (not needed in DuckDB UNNEST syntax)

---

## Testing Strategy

### Unit Testing

**New Tests Required** (implemented in SP-011-008):
- `test_duckdb_generate_lateral_unnest_basic()`: Basic UNNEST generation
- `test_duckdb_generate_lateral_unnest_complex_array_expr()`: Complex array expression
- `test_duckdb_generate_lateral_unnest_custom_alias()`: Custom alias
- `test_duckdb_generate_lateral_unnest_ignores_source_table()`: Verifies source_table not in output

**Coverage Target**: 100% coverage of `generate_lateral_unnest()` method

### Integration Testing

**Integration with CTEBuilder** (SP-011-008):
- CTEBuilder calls DuckDB dialect method correctly
- Generated UNNEST embedded in SELECT statement
- Multi-level UNNEST (nested arrays)

**Database Execution** (SP-011-008):
- Execute generated SQL in real DuckDB database
- Verify array flattening works correctly
- Compare results with expected FHIRPath semantics

### Compliance Testing

**DuckDB Syntax Validation**:
- Generated SQL is valid DuckDB syntax
- UNNEST works with JSON arrays
- Results match DuckDB documentation examples

### Manual Testing

**Test Scenarios**:
1. Simple array: `json_extract(resource, '$.name')`
2. Nested path: `json_extract(name_item, '$.given')`
3. Various aliases: "item", "name_item", "telecom_item"

**Edge Cases**:
- Very long array expressions
- Special characters in alias (should be handled by CTEBuilder validation)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DuckDB syntax changes in future versions | Low | Low | Use documented syntax, test with project's minimum DuckDB version |
| Array expression contains syntax errors | Low | Low | CTEBuilder validates before calling dialect method |
| Performance issues with large arrays | Low | Medium | Accept for MVP, DuckDB handles optimization |

### Implementation Challenges

1. **DuckDB Version Compatibility**: Ensure syntax works with project's minimum DuckDB version
   - **Approach**: Test with DuckDB 0.8+ (project minimum), verify in SP-011-008

2. **Syntax Correctness**: Ensure generated SQL is valid DuckDB
   - **Approach**: Manual testing, database execution tests in SP-011-008

### Contingency Plans

- **If DuckDB syntax proves incompatible**: Research DuckDB version-specific syntax, add version detection if needed
- **If performance issues arise**: Document in SP-011-008, defer optimization to future sprint

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review DuckDB docs, existing dialect methods)
- **Implementation**: 3h (method signature, syntax generation, docstring)
- **Testing**: 1h (manual testing with DuckDB)
- **Review and Refinement**: 0.5h (code review, style cleanup)
- **Total Estimate**: 5h (reduced from 8h - simpler than originally estimated)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Very simple string formatting method. DuckDB UNNEST syntax is well-documented and stable. No business logic or complex validation. Similar to existing dialect methods.

### Factors Affecting Estimate

- **DuckDB Documentation Review**: +0.5h if syntax more complex than expected
- **Testing Complexity**: +0.5h if manual testing reveals issues

---

## Success Metrics

### Quantitative Measures

- **Implementation Complete**: `generate_lateral_unnest()` method added to DuckDBDialect
- **Code Quality**: 0 lint errors, 100% type hint coverage
- **Syntax Correctness**: Generated SQL valid in DuckDB 0.8+

### Qualitative Measures

- **Code Quality**: Clean, simple, follows DuckDBDialect patterns
- **Architecture Alignment**: Thin dialect principle maintained (syntax only, no business logic)
- **Maintainability**: Easy to understand and modify if DuckDB syntax changes

### Compliance Impact

- **Specification Compliance**: Implements PEP-004 Appendix C (DuckDB UNNEST Syntax)
- **Dialect Parity**: Enables multi-database support for UNNEST operations

---

## Documentation Requirements

### Code Documentation

- [x] Comprehensive method docstring (purpose, args, returns, example)
- [x] Type hints for all parameters and return value
- [ ] Example in docstring showing typical usage and output

### Architecture Documentation

- [ ] No ADR needed (implements PEP-004 specification)
- [ ] Update PEP-004 implementation status (DuckDB dialect extension complete)

### User Documentation

Not applicable for internal dialect method.

---

## Progress Tracking

### Status
- [x] Not Started
- [x] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [x] Completed
- [ ] Blocked

**Current Status**: ✅ Completed and Merged (2025-10-20)

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | None | Begin implementation |
| 2025-10-20 | Completed - Pending Review | Implemented DuckDB `generate_lateral_unnest()`, added unit coverage, ran `pytest tests/unit/dialects/test_duckdb_dialect.py` | None | Await senior architect review |
| 2025-10-20 | ✅ Completed and Merged | Senior review approved, merged to main, feature branch deleted, 96 tests passing | None | Task complete - proceed to SP-011-007 |

### Completion Checklist

- [x] DuckDBDialect class located
- [x] `generate_lateral_unnest()` method signature added
- [x] DuckDB UNNEST syntax implementation complete
- [x] Comprehensive docstring added
- [x] Type hints complete
- [ ] Code passes lint checks
- [ ] Manual testing successful
- [ ] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches PEP-004 Appendix C
- [x] Thin dialect principle maintained (no business logic)
- [x] DuckDB syntax correct per documentation
- [x] Code follows DuckDBDialect patterns
- [x] Documentation complete and accurate

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-20
**Review Status**: ✅ Approved
**Review Comments**: See project-docs/plans/reviews/SP-011-006-review.md
- Perfect architecture compliance (thin dialect principle)
- Excellent documentation and testing
- 100% test pass rate (96/96 tests)
- Clean, simple implementation
- Ready for production use

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-20
**Status**: ✅ **APPROVED AND MERGED**
**Comments**: High-quality implementation that exemplifies thin dialect architecture. Merged to main branch successfully.

---

## Implementation Example

### Method Implementation

```python
def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:
    """
    Generate DuckDB LATERAL UNNEST syntax for array flattening.

    Args:
        source_table: Table/CTE name (not used in DuckDB syntax, kept for interface consistency)
        array_column: SQL expression for array to unnest (e.g., "json_extract(resource, '$.name')")
        alias: Alias for unnested items (e.g., "name_item")

    Returns:
        DuckDB LATERAL UNNEST SQL fragment

    Example:
        >>> dialect = DuckDBDialect()
        >>> unnest_sql = dialect.generate_lateral_unnest(
        ...     source_table="patient_resources",
        ...     array_column="json_extract(resource, '$.name')",
        ...     alias="name_item"
        ... )
        >>> print(unnest_sql)
        LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
    """
    return f"LATERAL UNNEST({array_column}) AS {alias}"
```

### Usage Example (Called by CTEBuilder)

```python
# In CTEBuilder._wrap_unnest_query()
dialect = DuckDBDialect()
unnest_clause = dialect.generate_lateral_unnest(
    source_table="patient_resources",
    array_column="json_extract(resource, '$.name')",
    alias="name_item"
)
# unnest_clause = "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"

# Embed in SELECT statement
sql = f"""SELECT patient_resources.id, name_item
FROM patient_resources, {unnest_clause}"""

# Result:
# SELECT patient_resources.id, name_item
# FROM patient_resources, LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
```

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Completed - Pending Review

---

*This task implements DuckDB-specific UNNEST syntax generation, maintaining the thin dialect architecture principle where dialects provide ONLY syntax differences.*
