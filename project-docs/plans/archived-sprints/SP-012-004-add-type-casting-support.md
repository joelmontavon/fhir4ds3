# Task SP-012-004: Add Type Casting Support (as Quantity, as Period)

**Task ID**: SP-012-004
**Sprint**: Sprint 012 - PostgreSQL Execution and Compliance Advancement
**Task Name**: Add Type Casting Support (as Quantity, as Period)
**Assignee**: Junior Developer
**Created**: 2025-10-22
**Last Updated**: 2025-10-22

---

## Task Overview

### Description

Implement FHIRPath `as` operator for type casting/type assertion, enabling expressions like `Observation.value as Quantity` and `Condition.onset as Period`. This completes the Type Functions foundation started in SP-012-003.

**Context**: FHIRPath's `as` operator performs type casting (assertion). If the value is of the specified type, it returns the value; otherwise, it returns an empty collection. This is essential for working with polymorphic types: `(Observation.value as Quantity).unit` asserts that `value` is a Quantity before accessing `.unit`.

**Example Use Case**:
```fhirpath
// Access unit only if value is a Quantity
(Observation.value as Quantity).unit

// Access start only if onset is a Period
(Condition.onset as Period).start
```

**What This Implements**:
- `as` operator for type assertions
- Type checking before casting
- Empty collection return for invalid casts
- Support for common FHIR types (Quantity, Period, Coding, CodeableConcept, etc.)

**Scope**: Implements type casting in AST adapter and SQL translator. Builds on SP-012-003's InvocationTerm handling.

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [ ] Critical (Blocker for sprint goals)
- [x] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Completes Type Functions foundation. Combined with SP-012-003, expected to achieve 70%+ Type Functions compliance (48/116 → 80/116+, target +32 tests).

---

## Requirements

### Functional Requirements

1. **Implement `as` Operator Parsing**:
   - Recognize `as` operator in FHIRPath expressions
   - Extract target type from expression
   - Handle parenthesized expressions: `(value as Quantity).unit`
   - Generate AST nodes for type casting

2. **Implement Type Checking Logic**:
   - Check if value is of target type before casting
   - Return value if type matches
   - Return empty collection if type doesn't match (FHIRPath spec behavior)
   - Support common FHIR types: Quantity, Period, Coding, CodeableConcept, HumanName, Address, etc.

3. **Generate SQL for Type Casting**:
   - SQL CASE expression to check type
   - Use JSON type fields or type discriminators
   - Return value if type matches, NULL if not
   - Work with both DuckDB and PostgreSQL (thin dialect)

4. **Support Common FHIR Types**:
   - **Quantity**: value with unit (e.g., "5.5 'mg'")
   - **Period**: start and end timestamps
   - **Coding**: system, code, display
   - **CodeableConcept**: coding array + text
   - **HumanName**: family, given names
   - **Address**: line, city, state, postal code
   - **Identifier**: system, value
   - **Reference**: reference, display

### Non-Functional Requirements

- **Performance**: Type casting should not significantly impact query performance
- **Compliance**: Combined with SP-012-003, target 70%+ Type Functions compliance
- **Database Support**: Must work identically on both DuckDB and PostgreSQL
- **Error Handling**: Invalid casts return empty collection (not error)
- **Maintainability**: Easy to add new type casting rules

### Acceptance Criteria

- [ ] `as` operator recognized and parsed correctly
- [ ] Type checking logic implemented for common FHIR types
- [ ] `(Observation.value as Quantity).unit` works correctly
- [ ] `(Condition.onset as Period).start` works correctly
- [ ] Invalid casts return empty collection (not error)
- [ ] SQL generated correctly for both DuckDB and PostgreSQL
- [ ] Unit tests passing (20+ new tests for type casting)
- [ ] Integration tests passing (type casting scenarios)
- [ ] Official test suite shows improvement (combined with SP-012-003: +32 tests)
- [ ] Zero regressions in existing tests
- [ ] Code review approved by senior architect

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/ast_adapter.py**: AST adapter for `as` operator
  - Add `visit_typeExpression` or equivalent method
  - Implement type casting logic
  - Generate SQL fragments

- **fhir4ds/fhirpath/types/fhir_types.py**: Type checking helpers
  - Add `check_fhir_type()` method
  - Map FHIRPath type names to FHIR resource types
  - Provide type discriminator logic

- **fhir4ds/dialects/base.py** + **postgresql.py** + **duckdb.py**: Dialect methods
  - Add `generate_type_cast()` method (if not already present)
  - Provide database-specific type checking SQL
  - Handle type discriminators

### File Modifications

- **fhir4ds/fhirpath/sql/ast_adapter.py**: MODIFY (~80-120 lines)
  - Add `visit_typeExpression` method (~30 lines)
  - Implement type casting SQL generation (~30 lines)
  - Add type checking logic (~20 lines)
  - Integrate with polymorphic property access from SP-012-003

- **fhir4ds/fhirpath/types/fhir_types.py**: MODIFY (~40-60 lines)
  - Add `FHIR_TYPE_DISCRIMINATORS` dictionary (~20 lines)
  - Add `check_fhir_type()` helper (~20 lines)
  - Document type checking approach

- **fhir4ds/dialects/base.py**: MODIFY (~20-30 lines)
  - Add `generate_type_cast()` abstract method
  - Document type casting interface

- **fhir4ds/dialects/postgresql.py** + **duckdb.py**: MODIFY (~30-40 lines each)
  - Implement `generate_type_cast()` method
  - Database-specific type checking SQL
  - Handle JSON type fields

- **tests/unit/fhirpath/sql/test_type_casting.py**: NEW (~100-120 lines)
  - Test `as` operator parsing
  - Test type checking logic
  - Test SQL generation
  - Test both databases

- **tests/integration/fhirpath/test_type_casting_integration.py**: NEW (~60-80 lines)
  - Integration tests with real data
  - Test common FHIR type casts
  - Verify both databases

### Database Considerations

**DuckDB**:
- Type checking via JSON structure inspection
- Example: Check if `value` has `unit` field → likely Quantity
- Use JSON functions: `json_extract()`, `json_typeof()`

**PostgreSQL**:
- Type checking via JSONB structure inspection
- Example: Check if `value` has `unit` field → likely Quantity
- Use JSONB functions: `jsonb_typeof()`, `jsonb_extract_path()`

**Type Discriminator Strategy**:
- FHIR types often identifiable by structure (e.g., Quantity has `value` and `unit`)
- Use JSON field presence to discriminate types
- Fallback: Always allow cast, let null propagation handle failures

---

## Dependencies

### Prerequisites

1. **SP-012-003 (InvocationTerm Handling)**: ⏳ Required
   - Polymorphic property access must work first
   - Type casting builds on this foundation
   - Can't test `(value as Quantity).unit` without SP-012-003

2. **Sprint 011 CTE Infrastructure**: ✅ Complete
   - AST adapter framework operational
   - SQL generator working

3. **Type Registry**: ✅ Available
   - FHIR type definitions available
   - Can extend with type discriminators

4. **Dialect Infrastructure**: ✅ Available
   - `generate_type_check()` methods already exist (from SP-012-001)
   - Can extend with `generate_type_cast()` if needed

### Blocking Tasks

- **SP-012-003**: MUST be complete before starting (type casting depends on polymorphic access)

### Dependent Tasks

- **SP-012-005**: Complete Type Functions implementation (builds on SP-012-003 + SP-012-004)

---

## Implementation Approach

### High-Level Strategy

**Approach**: Implement `as` operator by generating SQL CASE expressions that check type structure before returning value.

**Key Decisions**:
1. **Structural Type Checking**: Use JSON structure to discriminate types (e.g., Quantity has `value` and `unit` fields)
2. **Empty on Failure**: Return NULL (empty collection) if type doesn't match (FHIRPath spec)
3. **Thin Dialect**: Type checking logic in AST adapter, database-specific SQL in dialect
4. **Graceful Degradation**: If type can't be determined, allow cast and let null propagation handle failures

**Architecture Alignment**:
- Type casting logic is business logic → belongs in AST adapter
- Database-specific syntax → belongs in dialect
- Use existing `generate_type_check()` methods where possible

### Implementation Steps

1. **Research FHIR Type Discriminators** (1.0 hour)
   - Estimated Time: 1 hour
   - Key Activities:
     - Research FHIR type structures (how to identify Quantity, Period, etc.)
     - Document type discriminators (unique fields for each type)
     - Create `FHIR_TYPE_DISCRIMINATORS` dictionary
     - Test type identification logic manually
   - Validation:
     - Can distinguish Quantity from CodeableConcept
     - Can distinguish Period from instant (timestamp)
     - Document discriminators clearly

   **Example Discriminators**:
   ```python
   FHIR_TYPE_DISCRIMINATORS = {
       'Quantity': {'required_fields': ['value', 'unit'], 'type_field': None},
       'Period': {'required_fields': ['start'], 'type_field': None},
       'Coding': {'required_fields': ['system', 'code'], 'type_field': None},
       'CodeableConcept': {'required_fields': ['coding'], 'type_field': None},
       'HumanName': {'required_fields': ['family'], 'type_field': None},
       'Address': {'required_fields': ['line'], 'type_field': None},
   }
   ```

2. **Implement visit_typeExpression Method** (2.0 hours)
   - Estimated Time: 2 hours
   - Key Activities:
     - Add `visit_typeExpression` method to ast_adapter.py
     - Parse `as` operator and target type
     - Extract value expression (left side of `as`)
     - Call type checking logic
     - Generate SQLFragment
   - Validation:
     - Unit test parsing `value as Quantity`
     - Verify AST structure correct
     - Test with parenthesized expressions: `(value as Quantity)`

   **Pseudocode**:
   ```python
   def visit_typeExpression(self, ctx):
       # Parse: expression 'as' type_identifier
       value_expr = self.visit(ctx.expression())
       target_type = ctx.type_identifier().getText()

       # Generate type checking SQL
       return self.generate_type_cast(value_expr, target_type)
   ```

3. **Implement Type Checking SQL Generation** (3.0 hours)
   - Estimated Time: 3 hours
   - Key Activities:
     - Implement `generate_type_cast()` method in AST adapter
     - Check type discriminators for target type
     - Generate CASE expression: if type matches → value, else → NULL
     - Use dialect methods for JSON field checking
     - Handle edge cases (unknown types, missing fields)
   - Validation:
     - Unit test type cast SQL generation
     - Verify SQL correct for Quantity, Period, Coding
     - Test both DuckDB and PostgreSQL SQL

   **Pseudocode**:
   ```python
   def generate_type_cast(self, value_expr, target_type):
       # Get type discriminator
       discriminator = FHIR_TYPE_DISCRIMINATORS.get(target_type)

       if not discriminator:
           # Unknown type - allow cast, let null propagation handle
           return value_expr

       # Generate CASE expression checking required fields
       required_fields = discriminator['required_fields']
       field_checks = []
       for field in required_fields:
           check = self.dialect.check_json_exists(value_expr.expression, f"$.{field}")
           field_checks.append(check)

       # CASE WHEN all fields exist THEN value ELSE NULL END
       condition = " AND ".join(field_checks)
       return f"CASE WHEN {condition} THEN {value_expr.expression} ELSE NULL END"
   ```

4. **Add Dialect Methods for Type Casting** (1.5 hours)
   - Estimated Time: 1.5 hours
   - Key Activities:
     - Review existing `generate_type_check()` and `generate_type_cast()` methods
     - Extend if needed for structural type checking
     - Add database-specific field existence checking
     - Document dialect methods
   - Validation:
     - DuckDB: `json_extract(value, '$.unit') IS NOT NULL` works
     - PostgreSQL: `jsonb_extract_path(value, 'unit') IS NOT NULL` works
     - Both databases generate correct SQL

5. **Write Comprehensive Unit Tests** (1.0 hour)
   - Estimated Time: 1 hour
   - Key Activities:
     - Create test_type_casting.py
     - Test `as` operator parsing (5+ tests)
     - Test type checking logic (10+ tests)
     - Test SQL generation (5+ tests)
     - Test both databases
   - Validation:
     - All unit tests passing (20+ tests)
     - Coverage ≥90% for new code
     - Both databases tested

6. **Run Official Test Suite and Measure Improvement** (0.5 hours)
   - Estimated Time: 0.5 hours
   - Key Activities:
     - Run official FHIRPath test suite (Type Functions category)
     - Measure compliance improvement (combined with SP-012-003)
     - Document results
     - Verify no regressions
   - Validation:
     - Type Functions: 48/116 → 80/116+ (target: 70%+ compliance)
     - Overall compliance: ~76% → ~77%
     - Zero regressions

### Alternative Approaches Considered

- **Always Allow Casts**: Don't check types, let null propagation handle failures
  - **Why Not Chosen**: Violates FHIRPath spec (empty collection on invalid cast), harder to debug

- **Runtime Type Checking**: Execute queries to check types at runtime
  - **Why Not Chosen**: Performance impact, breaks population-first design, requires multiple queries

- **Type Metadata Table**: Store type information in separate table
  - **Why Not Chosen**: Adds complexity, requires schema changes, not portable

---

## Testing Strategy

### Unit Testing

- **New Tests Required**: 20+ tests
  - `as` operator parsing (5 tests)
  - Type checking logic (10 tests)
  - SQL generation (5 tests)
  - Edge cases (unknown types, missing fields)

- **Test File**: `tests/unit/fhirpath/sql/test_type_casting.py`
- **Coverage Target**: ≥90% for new code

**Test Cases**:
1. `test_as_operator_simple` - `value as Quantity`
2. `test_as_operator_parenthesized` - `(value as Quantity).unit`
3. `test_type_check_quantity` - Quantity discriminator works
4. `test_type_check_period` - Period discriminator works
5. `test_type_check_coding` - Coding discriminator works
6. `test_invalid_type_returns_null` - Unknown type returns NULL
7. `test_sql_generation_duckdb` - Correct DuckDB SQL
8. `test_sql_generation_postgresql` - Correct PostgreSQL SQL
9. `test_chained_type_cast` - `(value as Quantity).unit` full chain
10. `test_type_cast_with_where` - Type cast in where clause

### Integration Testing

- **Database Testing**: Execute on both DuckDB and PostgreSQL
- **Test File**: `tests/integration/fhirpath/test_type_casting_integration.py`
- **Test Data**: Observation, Condition resources with polymorphic values

**Integration Test Cases**:
1. Execute `(Observation.value as Quantity).unit` → verify results
2. Execute `(Condition.onset as Period).start` → verify results
3. Execute `(Patient.name[0] as HumanName).family` → verify results
4. Verify identical results across DuckDB and PostgreSQL

### Compliance Testing

- **Official Test Suite**: Run Type Functions category
- **Baseline (after SP-012-003)**: 75-85/116 passing (65-73%)
- **Target (after SP-012-004)**: 80-90/116 passing (70-78%)
- **Combined Improvement**: 48/116 → 80+/116 (41% → 70%+)
- **Measurement**: Use official test runner, document results

### Manual Testing

- **Test Scenarios**:
  1. Parse: `(Observation.value as Quantity).unit`
  2. Verify AST includes type expression
  3. Translate to SQL
  4. Execute on test database
  5. Verify results match expected (unit values)

- **Edge Cases**:
  - Type cast on null value → NULL
  - Type cast on wrong type → NULL (empty collection)
  - Type cast on correct type → value
  - Chained type casts → `((x as Quantity) as Quantity)` (redundant but valid)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Type discriminators incomplete/incorrect | Medium | High | Research FHIR spec thoroughly, test with real data |
| Performance impact from type checking | Low | Medium | Benchmark queries, use simple field existence checks |
| Dialect differences in JSON field checking | Low | High | Test both databases extensively, use dialect methods |
| Breaking SP-012-003 functionality | Low | High | Integration tests verify SP-012-003 still works |

### Implementation Challenges

1. **Identifying FHIR Types Accurately**:
   - **Description**: FHIR types may be ambiguous (e.g., Period vs instant)
   - **Approach**: Use required field presence as discriminator, document edge cases
   - **Validation**: Test with real FHIR data, verify type identification correct

2. **Combining with Polymorphic Access (SP-012-003)**:
   - **Description**: `(value as Quantity).unit` requires both features working together
   - **Approach**: Integration tests verify combined functionality
   - **Validation**: Official tests exercise this pattern extensively

3. **Multi-Database SQL Generation**:
   - **Description**: DuckDB and PostgreSQL may differ in JSON field checking syntax
   - **Approach**: Use dialect abstraction, test both databases
   - **Validation**: Integration tests on both databases

### Contingency Plans

- **If type discriminators inaccurate**:
  - Refine discriminators iteratively based on test failures
  - Add explicit type field checking if available
  - Document known limitations

- **If performance impact significant**:
  - Profile queries to identify bottlenecks
  - Simplify type checking (reduce field checks)
  - Consider caching type information

- **If combined with SP-012-003 breaks**:
  - Analyze interaction between features
  - Add integration tests for combined functionality
  - Fix carefully to avoid breaking polymorphic access

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 1.0 hour (research type discriminators, plan implementation)
- **Implementation**: 6.5 hours (AST adapter, type checking, dialect methods)
- **Testing**: 1.5 hours (unit tests, integration tests, official suite)
- **Documentation**: 0.5 hours (code comments, docstrings)
- **Review and Refinement**: 0.5 hours (self-review, address feedback)
- **Total Estimate**: 10.0 hours (~8h estimate + 2h buffer)

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**:
- Clear requirements and examples
- Builds on SP-012-003 foundation
- Well-defined scope (type casting only)
- Risk: Type discriminators may be complex, integration with SP-012-003 may have issues

### Factors Affecting Estimate

- **Positive**: Clear FHIRPath spec, existing infrastructure, focused scope
- **Risk**: FHIR type complexity, integration challenges, multi-database testing
- **Buffer**: 2h buffer (25%) for unexpected issues

---

## Success Metrics

### Quantitative Measures

- **Type Functions Compliance (Combined with SP-012-003)**: 48/116 → 80-90/116 (70-78%)
- **Overall Compliance**: ~76% → ~77% (+1%)
- **New Unit Tests**: 20+ tests, 100% passing
- **Integration Tests**: 4+ tests, 100% passing
- **Zero Regressions**: All existing tests continue passing

### Qualitative Measures

- **Code Quality**: Clean, well-documented type casting logic
- **Architecture Alignment**: Type checking in AST adapter, syntax in dialect
- **Maintainability**: Easy to add new type discriminators
- **Integration**: Works seamlessly with SP-012-003 polymorphic access

### Compliance Impact

- **Type Functions**: Major improvement (combined: 41% → 70%+)
- **Overall FHIRPath**: Moderate improvement (~76% → ~77%)
- **Foundation Complete**: SP-012-003 + SP-012-004 enable SP-012-005

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments for type checking logic
- [x] Function/method documentation for visit_typeExpression
- [x] FHIR_TYPE_DISCRIMINATORS dictionary documented
- [x] Example usage in docstrings

### Architecture Documentation

- [ ] Document type casting implementation approach
- [ ] Explain type discriminator strategy
- [ ] Diagram: FHIRPath `as` → AST → SQL CASE
- [ ] Performance characteristics

### User Documentation

- [ ] How type casting works in FHIRPath
- [ ] Examples of type casting with FHIR types
- [ ] Troubleshooting type casting issues
- [ ] List of supported types and discriminators

---

## Progress Tracking

### Status

- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [x] Partially Completed (Phase 1)
- [ ] Blocked

### Progress Updates

| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-10-22 | Not Started | Task created, blocked by SP-012-003 | SP-012-003 | Wait for SP-012-003 completion |
| 2025-10-23 | In Development | Added structural discriminator map, updated translator path handling, expanded unit + integration coverage | 36 test failures | Initial review identified issues |
| 2025-10-23 | Reverted | Attempted fix made situation worse (21 failures + 29 errors) | Process failure | Revert and restart with methodology |
| 2025-10-23 | Phase 1 Complete | Fixed all 9 type registry regressions through 3 methodical commits. 56/56 type system tests passing. Zero regressions introduced. | None | Remaining work split into follow-up tasks |
| 2025-10-23 | Partially Completed | **Phase 1 MERGED to main**. Remaining work tracked in: SP-012-004-A (ofType), SP-012-004-B (math functions), SP-012-004-C (other issues) | None | Follow-up tasks for remaining failures |

### Completion Checklist

- [x] FHIR_TYPE_DISCRIMINATORS dictionary created
- [ ] visit_typeExpression() method implemented
- [x] Type checking SQL generation working
- [x] CASE expressions generated correctly
- [x] Both databases supported (DuckDB + PostgreSQL)
- [x] Unit tests written and passing (20+ tests)
- [x] Integration tests passing (4+ tests)
- [ ] Combined with SP-012-003: 70%+ Type Functions compliance
- [ ] Zero regressions verified
- [ ] Code reviewed and approved
- [ ] Documentation complete

---

## Review and Sign-off

### Self-Review Checklist

- [x] `as` operator implemented correctly
- [x] Type checking works for common FHIR types
- [x] SQL generated correctly for both databases
- [ ] Combined with SP-012-003: polymorphic access + type casting works
- [x] All unit tests passing (20+ tests)
- [ ] Integration tests passing on both databases
- [ ] Official compliance improved to 70%+ (Type Functions)
- [ ] Zero regressions in existing tests
- [ ] Code follows thin dialect architecture
- [ ] Documentation complete and accurate

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-23
**Review Status**: Phase 1 Approved
**Review Comments**: See `project-docs/plans/reviews/SP-012-004-phase-1-review.md`

**Phase 1 Assessment**:
- ✅ Excellent process adherence
- ✅ High code quality
- ✅ Zero regressions introduced
- ✅ All 9 type registry tests fixed
- ✅ Demonstrates strong learning from initial failure

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-23
**Status**: Phase 1 Approved and Merged
**Comments**: Phase 1 successfully completed. Remaining work split into follow-up tasks (SP-012-004-A, B, C) for focused resolution.

---

## Post-Completion Analysis

### Actual vs. Estimated

- **Time Estimate**: 8 hours
- **Actual Time**: [To be filled after completion]
- **Variance**: [To be calculated]

### Lessons Learned

1. [To be documented after completion]
2. [To be documented after completion]

### Future Improvements

- **Process**: [To be identified during execution]
- **Technical**: [To be identified during implementation]
- **Estimation**: [To be refined based on actual time]

---

**Task Created**: 2025-10-22 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-22
**Status**: Not Started (blocked by SP-012-003)

---

*This task completes the Type Functions foundation by implementing type casting. Combined with SP-012-003, targets 70%+ Type Functions compliance (48/116 → 80+/116) and enables SP-012-005 to achieve full Type Functions implementation.*
