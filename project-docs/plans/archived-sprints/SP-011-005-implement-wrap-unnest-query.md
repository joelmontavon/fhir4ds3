# Task SP-011-005: Implement `_wrap_unnest_query()` in CTEBuilder

**Task ID**: SP-011-005
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Implement `_wrap_unnest_query()` in CTEBuilder
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `_wrap_unnest_query()` method in the CTEBuilder class to handle LATERAL UNNEST operations for array flattening in FHIRPath expressions. This method wraps SQL fragments that require array unnesting (e.g., `Patient.name`, `Patient.telecom`) in proper CTE structure with LATERAL UNNEST syntax, enabling population-scale array navigation.

The implementation is the core of Phase 2 (Array UNNEST Support) and unblocks 60-70% of Path Navigation functionality. This method delegates database-specific UNNEST syntax to dialect methods (implemented in SP-011-006 and SP-011-007), maintaining the thin dialect architecture principle.

**Context**: Currently, `_wrap_unnest_query()` exists as a stub that raises `NotImplementedError`. This task implements the full functionality, enabling expressions like `Patient.name.given` to properly flatten arrays and return all values across the patient population.

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

1. **UNNEST Query Generation**: Implement `_wrap_unnest_query()` method that:
   - Accepts SQLFragment with `requires_unnest=True`
   - Extracts array path from fragment metadata
   - Generates LATERAL UNNEST SQL via dialect method
   - Returns properly formatted CTE query string

2. **Metadata Extraction**: Extract UNNEST-specific metadata from SQLFragment:
   - `array_column`: The column containing the JSON array to unnest
   - `result_alias`: Alias for unnested items (defaults to "item")
   - `id_column`: Patient/resource ID column to preserve (defaults to "{source}.id")

3. **Dialect Method Delegation**: Call `dialect.generate_lateral_unnest()` for database-specific syntax:
   - Pass source table (previous CTE name or base table)
   - Pass array column reference
   - Pass item alias for unnested elements
   - Return generated UNNEST SQL fragment

4. **SELECT Statement Wrapping**: Construct complete SELECT with:
   - ID column to preserve patient/resource identity across population
   - LATERAL UNNEST operation for array flattening
   - Proper column aliases for downstream CTEs
   - FROM clause referencing source table/CTE

5. **Population-First Design**: Maintain population-scale capability:
   - No LIMIT 1 anti-patterns
   - Preserve all patient IDs through UNNEST
   - Process entire arrays across all resources
   - Enable bulk result sets

### Non-Functional Requirements

- **Performance**: UNNEST query generation <5ms per fragment
- **Compliance**: Implements PEP-004 Section 2.2 (CTEBuilder._wrap_unnest_query)
- **Database Support**: Works with both DuckDB and PostgreSQL via dialect abstraction
- **Error Handling**: Clear ValueError for missing metadata or invalid fragments

### Acceptance Criteria

- [ ] `_wrap_unnest_query()` method implemented in CTEBuilder class (fhir4ds/fhirpath/sql/cte.py:448-465)
- [ ] Method signature matches PEP-004: `_wrap_unnest_query(self, fragment: SQLFragment, source_table: str) -> str`
- [ ] Extracts `array_column`, `result_alias`, and `id_column` from fragment metadata
- [ ] Calls `dialect.generate_lateral_unnest()` with correct parameters
- [ ] Returns properly formatted SELECT statement with LATERAL UNNEST
- [ ] Preserves patient/resource ID column in SELECT
- [ ] Validates fragment has `requires_unnest=True` flag
- [ ] Raises clear ValueError for missing metadata (array_column)
- [ ] Comprehensive docstring with Args, Returns, Raises, and example
- [ ] Code passes lint checks (type hints, style)
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/cte.py**: Modify CTEBuilder class
  - Implement `_wrap_unnest_query()` method (currently NotImplementedError stub)
  - Update method from stub to full implementation

### File Modifications

- **fhir4ds/fhirpath/sql/cte.py** (MODIFY):
  - Replace `_wrap_unnest_query()` stub implementation (lines 448-465)
  - Add metadata extraction logic
  - Add dialect method call for UNNEST generation
  - Add SELECT statement construction
  - Add comprehensive docstring

### Database Considerations

- **DuckDB**: Uses `LATERAL UNNEST(array) AS alias` syntax (handled by dialect)
- **PostgreSQL**: Uses `LATERAL jsonb_array_elements(array) AS alias` syntax (handled by dialect)
- **Schema Changes**: None (CTE infrastructure only)

---

## Dependencies

### Prerequisites

1. **SP-011-001**: ✅ Complete (CTE dataclass with requires_unnest flag)
2. **SP-011-002**: ✅ Complete (CTEBuilder class with _wrap_unnest_query stub)
3. **SP-011-003**: ✅ Complete (CTEAssembler class)
4. **SP-011-004**: ✅ Complete (Phase 1 unit tests validating stub raises NotImplementedError)
5. **Dialect Interface**: ✅ Complete (DatabaseDialect base class from PEP-003)

### Blocking Tasks

- **SP-011-004**: Phase 1 unit tests (validates current stub behavior)

### Dependent Tasks

- **SP-011-006**: DuckDB dialect `generate_lateral_unnest()` implementation (required for DuckDB execution)
- **SP-011-007**: PostgreSQL dialect `generate_lateral_unnest()` implementation (required for PostgreSQL execution)
- **SP-011-008**: Unit tests for UNNEST generation (validates this implementation)

---

## Implementation Approach

### High-Level Strategy

Implement `_wrap_unnest_query()` by following the same pattern as `_wrap_simple_query()` but with LATERAL UNNEST support. Extract array metadata from the fragment, delegate UNNEST syntax generation to the dialect, and construct a SELECT statement that preserves patient IDs while flattening arrays.

**Key Design Decisions**:
1. **Metadata-Driven**: All UNNEST configuration comes from fragment metadata (no hardcoding)
2. **Dialect Delegation**: Database-specific UNNEST syntax handled by dialect methods (thin dialect principle)
3. **Population-First**: SELECT preserves patient IDs and processes all rows
4. **Clear Validation**: Explicit error messages for missing/invalid metadata

### Implementation Steps

1. **Replace Stub Implementation** (1 hour)
   - Remove existing NotImplementedError stub
   - Add method signature: `def _wrap_unnest_query(self, fragment: SQLFragment, source_table: str) -> str:`
   - Add type hints for parameters and return value
   - **Validation**: Method signature correct, import statements present

2. **Add Metadata Extraction Logic** (2 hours)
   - Extract `array_column` from `fragment.metadata.get("array_column")`
   - Extract `result_alias` with default: `fragment.metadata.get("result_alias", "item")`
   - Extract `id_column` with default: `fragment.metadata.get("id_column", f"{source_table}.id")`
   - Validate `array_column` is present (raise ValueError if missing)
   - **Validation**: Metadata extraction working, validation raises appropriate errors

3. **Implement Dialect Method Call** (2 hours)
   - Call `self.dialect.generate_lateral_unnest(source_table, array_column, result_alias)`
   - Store result in `unnest_clause` variable
   - Handle any dialect method exceptions with clear error messages
   - **Validation**: Dialect method called with correct parameters

4. **Construct SELECT Statement** (3 hours)
   - Build SELECT clause: `SELECT {id_column}, {result_alias}`
   - Build FROM clause: `FROM {source_table}, {unnest_clause}`
   - Format properly with newlines for readability
   - Ensure population-first design (no LIMIT, process all rows)
   - **Validation**: Generated SQL structure correct, readable formatting

5. **Add Comprehensive Docstring** (1.5 hours)
   - Document method purpose: "Wrap fragment with UNNEST in proper CTE structure"
   - Document parameters:
     - `fragment`: SQLFragment with requires_unnest=True
     - `source_table`: Table/CTE containing array data
   - Document returns: Complete SELECT statement with LATERAL UNNEST
   - Document raises: ValueError for missing array_column metadata
   - Add example showing typical usage and generated SQL
   - **Validation**: Docstring complete, follows project standards

6. **Add Validation and Error Handling** (1.5 hours)
   - Check `fragment.requires_unnest` is True (document in docstring)
   - Validate `array_column` present in metadata
   - Validate `source_table` is non-empty string
   - Clear error messages referencing fragment metadata structure
   - **Validation**: All error paths tested, messages clear

7. **Code Review and Refinement** (1 hour)
   - Run type checker (mypy) on modified code
   - Check code style (matches _wrap_simple_query pattern)
   - Verify thin dialect principle maintained (no business logic in dialect calls)
   - Request senior architect code review
   - **Validation**: Code quality approved, architecture compliant

**Estimated Time**: 12h total

### Alternative Approaches Considered

- **Inline UNNEST Generation**: Generate UNNEST SQL directly in CTEBuilder - **Rejected** (violates thin dialect principle)
- **Multiple Dialect Methods**: Separate methods for different UNNEST scenarios - **Rejected** (premature complexity, single method sufficient for MVP)
- **Template-Based Generation**: Use SQL templates with placeholders - **Rejected** (less flexible, harder to maintain)

---

## Testing Strategy

### Unit Testing

**New Tests Required** (will be implemented in SP-011-008):
- `test_wrap_unnest_query_basic()`: Basic UNNEST query generation
- `test_wrap_unnest_query_with_custom_alias()`: Custom result alias
- `test_wrap_unnest_query_with_custom_id_column()`: Custom ID column
- `test_wrap_unnest_query_missing_array_column()`: ValueError when array_column missing
- `test_wrap_unnest_query_preserves_patient_id()`: Patient ID in SELECT
- `test_wrap_unnest_query_calls_dialect_method()`: Verifies dialect.generate_lateral_unnest() called

**Modified Tests**: Phase 1 tests expecting NotImplementedError will be updated in SP-011-008

**Coverage Target**: 100% coverage of `_wrap_unnest_query()` method

### Integration Testing

**Integration with Dialect Methods** (SP-011-006, SP-011-007):
- DuckDB dialect generates correct UNNEST syntax
- PostgreSQL dialect generates correct UNNEST syntax
- Multi-database parity: identical business logic, different syntax

**Integration with CTEBuilder Chain**:
- UNNEST CTEs properly reference previous CTE
- Dependencies tracked correctly
- CTE names incremented properly

### Compliance Testing

**FHIRPath Specification**:
- Array navigation semantics preserved (flattening, not filtering)
- Collection operations maintain FHIRPath semantics
- Population-scale results (all resources, not single resource)

### Manual Testing

**Test Scenarios**:
1. Single-level array (Patient.name)
2. Nested arrays (Patient.name.given)
3. Multiple arrays in sequence (Patient.name, then Patient.telecom)
4. Empty arrays (verify no results, not errors)

**Edge Cases**:
- Missing array_column metadata (should raise ValueError)
- Empty source_table (should raise ValueError)
- Fragment with requires_unnest=False (documented as invalid input)

**Error Conditions**:
- Invalid metadata structure
- Dialect method exceptions
- Malformed fragment

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| UNNEST syntax differs unexpectedly between dialects | Low | Medium | Use dialect methods, comprehensive testing in SP-011-008 |
| Metadata structure incomplete from translator | Low | High | Clear error messages, validate in SP-011-008 integration tests |
| ID column not preserved correctly | Low | High | Explicit ID column in SELECT, test validation |
| Performance degradation with large arrays | Low | Medium | Benchmark in SP-011-008, accept for MVP (optimization in future) |

### Implementation Challenges

1. **Metadata Extraction Complexity**: SQLFragment metadata structure may vary by translator
   - **Approach**: Use `get()` with defaults, clear validation errors

2. **Dialect Method Integration**: Ensuring correct parameters passed to dialect
   - **Approach**: Follow PEP-004 spec exactly, validate in SP-011-008

3. **SQL Formatting Consistency**: Matching _wrap_simple_query formatting style
   - **Approach**: Review existing method, maintain same pattern

### Contingency Plans

- **If metadata structure changes**: Update extraction logic, coordinate with PEP-003 team
- **If dialect methods not ready**: Implement stubs in SP-011-006/007 first, then complete this task
- **If performance issues discovered**: Document in SP-011-008, defer optimization to future sprint

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 1h (review PEP-004, _wrap_simple_query pattern, metadata structure)
- **Implementation**: 9h (metadata extraction, dialect call, SELECT construction, docstring)
- **Testing**: 1h (manual validation with mock dialect)
- **Review and Refinement**: 1h (code review, style cleanup, senior review)
- **Total Estimate**: 12h

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Similar complexity to `_wrap_simple_query()` which is already implemented. Clear PEP-004 specification. Pattern established in Phase 1. Main risk is metadata structure discovery, but PEP-003 translator already provides SQLFragment with metadata.

### Factors Affecting Estimate

- **Metadata Structure Complexity**: +1-2h if metadata more complex than expected
- **Dialect Method Interface**: +1h if dialect interface needs adjustments
- **SQL Formatting Decisions**: +0.5h for ensuring consistency with existing code

---

## Success Metrics

### Quantitative Measures

- **Implementation Complete**: `_wrap_unnest_query()` method fully implemented
- **Code Quality**: 0 lint errors, 100% type hint coverage
- **Docstring Complete**: Args, Returns, Raises, Example all documented
- **Error Handling**: 3+ validation checks with clear error messages

### Qualitative Measures

- **Code Quality**: Clean, readable, follows CTEBuilder patterns
- **Architecture Alignment**: Thin dialect principle maintained (delegates to dialect.generate_lateral_unnest())
- **Maintainability**: Easy to understand and extend for future UNNEST scenarios

### Compliance Impact

- **Specification Compliance**: Implements PEP-004 Section 2.2 (CTEBuilder)
- **FHIRPath Semantics**: Enables array navigation with proper collection flattening
- **Population-First Design**: Maintains population-scale capability

---

## Documentation Requirements

### Code Documentation

- [x] Comprehensive method docstring (purpose, args, returns, raises, example)
- [x] Inline comments for complex metadata extraction logic
- [x] Type hints for all parameters and return value
- [ ] Example in docstring showing typical usage and generated SQL

### Architecture Documentation

- [ ] No ADR needed (implements existing PEP-004 specification)
- [ ] Update PEP-004 implementation status (Phase 2 in progress)

### User Documentation

Not applicable for internal method (called by CTEBuilder.build_cte_chain(), not public API).

---

## Progress Tracking

### Status
- [ ] Not Started
- [x] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [x] Completed
- [ ] Blocked

**Current Status**: Completed - merged to main

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | Awaiting Phase 1 completion (SP-011-004 merged) | Begin implementation after Phase 1 review |
| 2025-10-20 | In Development | Implemented `_wrap_unnest_query` with metadata extraction, dialect delegation, and docstring | Dialect UNNEST methods not yet delivered (SP-011-006/007) | Align with dialect owners once interfaces are ready |
| 2025-10-20 | In Testing | Added unit coverage for metadata validation and SQL generation using mocked dialect | Await dialect implementations for end-to-end DB verification | Run integration tests once dialect features land |
| 2025-10-20 | Completed | Senior review approved, merged to main branch | None | Proceed with SP-011-006, SP-011-007, and SP-011-008 |

### Completion Checklist

- [x] NotImplementedError stub removed
- [x] Metadata extraction logic implemented
- [x] Dialect method call implemented
- [x] SELECT statement construction implemented
- [x] Comprehensive docstring added
- [x] Validation and error handling complete
- [x] Type hints complete
- [x] Code passes lint checks (clean implementation)
- [x] Manual testing with mock dialect successful
- [x] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches PEP-004 specification (Section 2.2)
- [x] Thin dialect principle maintained (no business logic in dialect call)
- [x] Population-first design preserved (no LIMIT patterns)
- [x] Error handling comprehensive with clear messages
- [x] Code follows CTEBuilder patterns (_wrap_simple_query style)
- [x] Documentation complete and accurate

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-20
**Review Status**: ✅ APPROVED
**Review Comments**: See project-docs/plans/reviews/SP-011-005-review.md for complete review

**Key Findings**:
- ⭐⭐⭐⭐⭐ 5/5 Overall Rating
- Architecture Compliance: EXCELLENT (perfect thin dialect implementation)
- Code Quality: EXCELLENT (clean, well-documented, properly validated)
- Documentation: EXCELLENT (comprehensive docstring with example)
- 2 expected test failures in legacy tests (to be updated in SP-011-008)

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-20
**Status**: ✅ APPROVED AND MERGED
**Comments**: Exemplary implementation that sets excellent standard for future dialect work. Merged to main branch.

---

## Related Tasks

### Prerequisite Tasks

- **SP-011-001**: CTE dataclass (provides requires_unnest flag) ✅ Complete
- **SP-011-002**: CTEBuilder class structure (provides _wrap_unnest_query stub) ✅ Complete
- **SP-011-004**: Phase 1 unit tests (validates stub behavior) ✅ Complete

### Parallel Tasks

- **SP-011-006**: DuckDB dialect `generate_lateral_unnest()` (can be implemented in parallel)
- **SP-011-007**: PostgreSQL dialect `generate_lateral_unnest()` (can be implemented in parallel)

### Follow-up Tasks

- **SP-011-008**: Unit tests for UNNEST generation (validates this implementation)

---

## Implementation Example

### Input (SQLFragment from PEP-003 Translator)

```python
fragment = SQLFragment(
    expression="json_extract(resource, '$.name')",
    source_table="patient_resources",
    requires_unnest=True,
    metadata={
        "array_column": "json_extract(resource, '$.name')",
        "result_alias": "name_item",
        "id_column": "patient_resources.id"
    }
)
```

### Expected Output (Generated CTE Query)

```sql
SELECT patient_resources.id, name_item
FROM patient_resources, LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
```

### Method Call

```python
builder = CTEBuilder(dialect=DuckDBDialect())
source_table = "patient_resources"
query = builder._wrap_unnest_query(fragment, source_table)
# Returns SQL shown above
```

### Error Case Example

```python
# Missing array_column metadata
fragment = SQLFragment(
    expression="json_extract(resource, '$.name')",
    source_table="patient_resources",
    requires_unnest=True,
    metadata={
        "result_alias": "name_item"  # Missing array_column!
    }
)

query = builder._wrap_unnest_query(fragment, "patient_resources")
# Raises: ValueError("SQLFragment metadata must contain 'array_column' for UNNEST operations")
```

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Not Started (Awaiting Phase 1 Completion)

---

*This task implements the core of Phase 2 (Array UNNEST Support), enabling FHIRPath expressions with arrays to properly flatten collections and return population-scale results.*
