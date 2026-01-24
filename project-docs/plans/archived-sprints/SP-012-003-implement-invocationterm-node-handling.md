# Task SP-012-003: Implement InvocationTerm Node Handling

**Task ID**: SP-012-003
**Sprint**: Sprint 012 - PostgreSQL Execution and Compliance Advancement
**Task Name**: Implement InvocationTerm Node Handling
**Assignee**: Junior Developer
**Created**: 2025-10-22
**Last Updated**: 2025-10-22

---

## Task Overview

### Description

Implement support for `InvocationTerm` AST nodes in the FHIRPath SQL translator to enable polymorphic property access. This is the **highest-impact gap** from SP-010, responsible for 68 failing Type Functions tests (58.6% failure rate).

**Context**: FHIRPath supports polymorphic types where a property like `Observation.value` can refer to different typed properties (`valueQuantity`, `valueString`, `valueCodeableConcept`, etc.). When accessing properties on polymorphic values (e.g., `Observation.value.unit`), the parser generates `InvocationTerm` nodes. Our current AST adapter doesn't handle these nodes, causing "Unexpected evaluation outcome" errors.

**Example Failing Test**:
```
testPolymorphismA: Observation.value.unit
Error: InvocationTerm node type not handled in visit_expression
```

**What This Fixes**:
- Polymorphic property access: `Observation.value.unit` → check `valueQuantity.unit`
- Type-specific property resolution: automatically try all possible typed properties
- InvocationTerm AST node translation to SQL

**Scope**: This task implements the AST adapter changes and basic SQL generation for InvocationTerm nodes. Type casting (`as Quantity`) is handled in SP-012-004.

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

**Rationale**: This is the #2 gap from SP-010 gap prioritization (after Path Navigation, which Sprint 011 solved). Expected gain: **+68 tests (+7.3% compliance)**.

---

## Requirements

### Functional Requirements

1. **Handle InvocationTerm AST Nodes**:
   - Add `visit_invocationTerm` method to AST adapter
   - Extract function name from InvocationTerm
   - Handle arguments (if any)
   - Translate to SQL fragment

2. **Implement Polymorphic Property Access**:
   - When accessing property on polymorphic type (e.g., `value.unit`), check all typed variants
   - Example: `Observation.value.unit` → try `valueQuantity.unit`, `valueString.unit`, etc.
   - Return first non-null result (COALESCE pattern)
   - Support common FHIR polymorphic properties

3. **Generate SQL for Property Access**:
   - Simple property access: `someProperty` → JSON extraction
   - Chained property access: `value.unit` → nested JSON extraction
   - Polymorphic resolution: generate COALESCE with all variants
   - Handle missing properties gracefully (return null)

4. **Support Common FHIR Polymorphic Types**:
   - `value[x]` properties (Observation.value → valueQuantity, valueString, etc.)
   - `onset[x]` properties (Condition.onset → onsetDateTime, onsetAge, etc.)
   - `deceased[x]` properties (Patient.deceased → deceasedBoolean, deceasedDateTime)
   - Other polymorphic properties as identified

### Non-Functional Requirements

- **Performance**: Polymorphic resolution should not significantly impact query performance (use COALESCE, not subqueries)
- **Compliance**: Target +30-40 Type Functions tests passing (partial fix, type casting in SP-012-004)
- **Database Support**: Must work identically on both DuckDB and PostgreSQL
- **Error Handling**: Invalid property access returns null (not error)
- **Maintainability**: Clean, well-documented polymorphic resolution logic

### Acceptance Criteria

- [ ] `InvocationTerm` AST nodes handled without errors
- [ ] `visit_invocationTerm` method implemented in AST adapter
- [ ] Polymorphic property access working for common FHIR types
- [ ] `Observation.value.unit` resolves correctly (polymorphic access)
- [ ] SQL generated correctly for both DuckDB and PostgreSQL
- [ ] Unit tests passing (30+ new tests for InvocationTerm handling)
- [ ] Integration tests passing (Type Functions subset)
- [ ] Official test suite shows improvement (+30-40 tests)
- [ ] Zero regressions in existing tests
- [ ] Code review approved by senior architect

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/ast_adapter.py**: Main implementation file
  - Add `visit_invocationTerm` method
  - Implement polymorphic property resolution
  - Generate SQL fragments for property access

- **fhir4ds/fhirpath/types/fhir_types.py**: Type registry
  - Add polymorphic type mappings
  - Document common polymorphic properties
  - Provide type resolution helpers

- **fhir4ds/fhirpath/sql/translator.py**: SQL translator (minor)
  - May need updates to support polymorphic fragments
  - Handle COALESCE generation for polymorphic access

### File Modifications

- **fhir4ds/fhirpath/sql/ast_adapter.py**: MODIFY (~100-150 lines)
  - Add `visit_invocationTerm` method (~40 lines)
  - Add polymorphic property resolution helper (~40 lines)
  - Add property access SQL generation (~30 lines)
  - Add unit tests integration

- **fhir4ds/fhirpath/types/fhir_types.py**: MODIFY (~50-80 lines)
  - Add `POLYMORPHIC_PROPERTIES` dictionary (~30 lines)
  - Add `resolve_polymorphic_property` helper (~20 lines)
  - Add type variant mapping (~20 lines)

- **tests/unit/fhirpath/sql/test_ast_adapter_invocation.py**: NEW (~120-150 lines)
  - Test InvocationTerm node handling
  - Test polymorphic property resolution
  - Test SQL generation
  - Test both DuckDB and PostgreSQL

- **tests/integration/fhirpath/test_polymorphic_access.py**: NEW (~80-100 lines)
  - Integration tests for polymorphic property access
  - Test with real FHIR data
  - Verify both databases
  - Test common use cases

### Database Considerations

**DuckDB**:
- JSON extraction: `json_extract(resource, '$.valueQuantity.unit')`
- COALESCE for polymorphic: `COALESCE(json_extract(..., '$.valueQuantity.unit'), json_extract(..., '$.valueString.unit'))`
- Maintain existing behavior

**PostgreSQL**:
- JSONB extraction: `jsonb_extract_path_text(resource, 'valueQuantity', 'unit')`
- COALESCE for polymorphic: `COALESCE(jsonb_extract_path_text(..., 'valueQuantity', 'unit'), jsonb_extract_path_text(..., 'valueString', 'unit'))`
- Use thin dialect methods

**Key Insight**: Polymorphic resolution generates identical COALESCE pattern for both databases, just with different JSON extraction syntax (handled by dialect).

---

## Dependencies

### Prerequisites

1. **Sprint 011 CTE Infrastructure**: ✅ Complete
   - AST adapter framework operational
   - SQL translator working
   - Fragment generation established

2. **Type Registry**: ✅ Available
   - FHIR type definitions available
   - Type hierarchy established
   - Can extend with polymorphic mappings

3. **FHIRPath Parser**: ✅ Generates InvocationTerm nodes
   - Parser already creates InvocationTerm nodes
   - Just need to handle them in AST adapter

4. **Test Data**: ✅ Available
   - Observation resources with polymorphic values
   - Patient resources with polymorphic properties
   - Official FHIRPath test suite

### Blocking Tasks

- None (can start immediately after SP-012-002)

### Dependent Tasks

- **SP-012-004**: Type casting builds on this foundation
- **SP-012-005**: Complete Type Functions depends on this

---

## Implementation Approach

### High-Level Strategy

**Approach**: Implement polymorphic property access by generating COALESCE SQL that checks all possible typed property variants.

**Key Decisions**:
1. **COALESCE Pattern**: Use SQL COALESCE to check multiple property variants (first non-null wins)
2. **Thin Dialect**: Polymorphic logic in AST adapter, dialect provides only JSON extraction syntax
3. **Type Registry**: Centralize polymorphic property mappings in type registry
4. **Graceful Degradation**: Unknown properties return null (not error)

**Architecture Alignment**:
- Polymorphic resolution is business logic → belongs in AST adapter (not dialect)
- Dialects provide only syntax differences (JSON extraction methods)
- CTE infrastructure handles SQL generation (use existing fragments)

### Implementation Steps

1. **Add Polymorphic Property Mappings to Type Registry** (2.0 hours)
   - Estimated Time: 2 hours
   - Key Activities:
     - Research FHIR polymorphic properties (value[x], onset[x], deceased[x], etc.)
     - Create `POLYMORPHIC_PROPERTIES` dictionary mapping base property → typed variants
     - Add `resolve_polymorphic_property()` helper method
     - Document mappings with examples
   - Validation:
     - Unit test polymorphic property resolution
     - Verify all common FHIR polymorphic properties included
     - Test with Observation.value, Condition.onset, Patient.deceased

   **Example Mapping**:
   ```python
   POLYMORPHIC_PROPERTIES = {
       'value': ['valueQuantity', 'valueCodeableConcept', 'valueString',
                 'valueBoolean', 'valueInteger', 'valueRange', 'valueRatio',
                 'valueSampledData', 'valueTime', 'valueDateTime', 'valuePeriod'],
       'onset': ['onsetDateTime', 'onsetAge', 'onsetPeriod', 'onsetRange', 'onsetString'],
       'deceased': ['deceasedBoolean', 'deceasedDateTime'],
       # ... other polymorphic properties
   }
   ```

2. **Implement visit_invocationTerm in AST Adapter** (3.0 hours)
   - Estimated Time: 3 hours
   - Key Activities:
     - Add `visit_invocationTerm` method to ast_adapter.py
     - Extract function/property name from InvocationTerm
     - Handle arguments (for functions like `where()`, `select()`)
     - Determine if invocation is property access or function call
     - Delegate to appropriate handler
   - Validation:
     - Unit test InvocationTerm node parsing
     - Test with simple property access: `someProperty`
     - Test with chained access: `value.unit`
     - Test with function calls: `where($this.code = 'x')`

   **Pseudocode**:
   ```python
   def visit_invocationTerm(self, ctx):
       # Extract invocation name
       invocation_name = ctx.identifier().getText()

       # Check if it's a function call (has arguments) or property access
       if ctx.invocationExpression():
           # Function call - handle arguments
           return self.visit_function_invocation(ctx, invocation_name)
       else:
           # Property access - may be polymorphic
           return self.visit_property_access(ctx, invocation_name)
   ```

3. **Implement Polymorphic Property Resolution** (3.0 hours)
   - Estimated Time: 3 hours
   - Key Activities:
     - Implement `resolve_polymorphic_property()` method
     - Check if property is polymorphic (in POLYMORPHIC_PROPERTIES)
     - Generate SQL COALESCE with all typed variants
     - Use dialect JSON extraction methods for each variant
     - Return SQLFragment with COALESCE expression
   - Validation:
     - Unit test polymorphic resolution
     - Test with Observation.value.unit → COALESCE(valueQuantity.unit, ...)
     - Verify SQL generated correctly for both databases
     - Test non-polymorphic properties (should pass through unchanged)

   **Pseudocode**:
   ```python
   def resolve_polymorphic_property(self, base_property, nested_property, context):
       # Check if property is polymorphic
       if base_property in POLYMORPHIC_PROPERTIES:
           # Get all typed variants
           variants = POLYMORPHIC_PROPERTIES[base_property]

           # Generate COALESCE with all variants
           variant_fragments = []
           for variant in variants:
               # Generate JSON extraction for this variant
               path = f"{variant}.{nested_property}"
               fragment = self.dialect.extract_json_field(context.table, path)
               variant_fragments.append(fragment)

           # Combine with COALESCE
           return f"COALESCE({', '.join(variant_fragments)})"
       else:
           # Not polymorphic, simple property access
           return self.dialect.extract_json_field(context.table, f"{base_property}.{nested_property}")
   ```

4. **Add SQL Fragment Generation** (2.0 hours)
   - Estimated Time: 2 hours
   - Key Activities:
     - Implement SQL generation for property access fragments
     - Handle simple property: `property` → JSON extraction
     - Handle nested property: `property.nested` → nested JSON extraction
     - Handle polymorphic property: generate COALESCE pattern
     - Create SQLFragment objects with correct metadata
   - Validation:
     - Unit test SQL fragment generation
     - Verify DuckDB SQL syntax correct
     - Verify PostgreSQL SQL syntax correct
     - Test with complex nesting: `value.coding[0].system`

5. **Write Comprehensive Unit Tests** (1.5 hours)
   - Estimated Time: 1.5 hours
   - Key Activities:
     - Create test_ast_adapter_invocation.py
     - Test InvocationTerm node handling (10+ tests)
     - Test polymorphic property resolution (10+ tests)
     - Test SQL generation (10+ tests)
     - Test both databases (DuckDB + PostgreSQL)
   - Validation:
     - All unit tests passing
     - Coverage ≥90% for new code
     - Both databases tested

6. **Run Official Test Suite and Measure Improvement** (0.5 hours)
   - Estimated Time: 0.5 hours
   - Key Activities:
     - Run official FHIRPath test suite
     - Measure Type Functions compliance improvement
     - Document results (before/after comparison)
     - Verify no regressions
   - Validation:
     - Type Functions: 48/116 → 75-85/116 (target: +27-37 tests)
     - Overall compliance: 72% → ~76% (+4%)
     - Zero regressions in existing 1901 passing tests

### Alternative Approaches Considered

- **Subquery Approach**: Use subqueries to check each typed property
  - **Why Not Chosen**: Performance impact, complex SQL, harder to maintain

- **Runtime Type Checking**: Check resource type at runtime, select appropriate property
  - **Why Not Chosen**: Requires multiple queries, breaks population-first design

- **Hardcode Property Mappings**: Embed polymorphic mappings in AST adapter
  - **Why Not Chosen**: Not maintainable, violates separation of concerns, type registry is proper location

---

## Testing Strategy

### Unit Testing

- **New Tests Required**: 30+ tests
  - InvocationTerm node handling (10 tests)
  - Polymorphic property resolution (10 tests)
  - SQL fragment generation (10 tests)
  - Edge cases (polymorphic + nested, unknown properties)

- **Test File**: `tests/unit/fhirpath/sql/test_ast_adapter_invocation.py`

- **Coverage Target**: ≥90% for new code

**Test Cases**:
1. `test_invocationterm_simple_property` - property access without nesting
2. `test_invocationterm_nested_property` - property.nested access
3. `test_invocationterm_polymorphic_property` - Observation.value.unit
4. `test_polymorphic_resolution_all_variants` - all typed variants included
5. `test_polymorphic_resolution_coalesce_order` - correct variant order
6. `test_non_polymorphic_property_passthrough` - non-polymorphic unchanged
7. `test_sql_generation_duckdb` - correct DuckDB SQL
8. `test_sql_generation_postgresql` - correct PostgreSQL SQL
9. `test_missing_property_returns_null` - graceful handling
10. `test_complex_nesting_polymorphic` - value.coding[0].system

### Integration Testing

- **Database Testing**: Execute on both DuckDB and PostgreSQL
- **Test File**: `tests/integration/fhirpath/test_polymorphic_access.py`
- **Test Data**: Observation resources with polymorphic values

**Integration Test Cases**:
1. Execute `Observation.value.unit` on real data → verify results
2. Execute `Observation.value.code` (CodeableConcept) → verify results
3. Execute `Patient.deceased` → verify Boolean or DateTime
4. Verify identical results across DuckDB and PostgreSQL

### Compliance Testing

- **Official Test Suite**: Run Type Functions category
- **Baseline**: 48/116 passing (41.4%)
- **Target**: 75-85/116 passing (65-73%) - partial fix, complete in SP-012-005
- **Measurement**: Use official test runner, document results

### Manual Testing

- **Test Scenarios**:
  1. Parse FHIRPath: `Observation.value.unit`
  2. Verify AST includes InvocationTerm nodes
  3. Translate to SQL
  4. Execute on test database
  5. Verify results match expected values

- **Edge Cases**:
  - Polymorphic property with no matching typed property → null
  - Non-polymorphic property misidentified → should still work
  - Deeply nested polymorphic access → `value.period.start`

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Incomplete polymorphic property mapping | Medium | Medium | Research FHIR spec thoroughly, add mappings iteratively |
| Performance impact from COALESCE | Low | Medium | Benchmark queries, optimize if needed (should be fast) |
| Dialect differences in COALESCE handling | Low | High | Test both databases extensively, verify identical behavior |
| Breaking existing tests | Low | High | Comprehensive regression testing after each change |
| Parser generates unexpected InvocationTerm structures | Medium | High | Analyze parser output carefully, handle all variants |

### Implementation Challenges

1. **Identifying All Polymorphic Properties**:
   - **Description**: FHIR has many polymorphic properties, easy to miss some
   - **Approach**: Research FHIR spec, cross-reference official tests, add iteratively
   - **Validation**: Official test suite will reveal missing mappings

2. **Generating Correct SQL COALESCE**:
   - **Description**: COALESCE must check all variants in correct order
   - **Approach**: Generate from type registry, ensure consistent ordering
   - **Validation**: Unit tests verify all variants included

3. **Multi-Database Compatibility**:
   - **Description**: DuckDB and PostgreSQL may handle COALESCE differently
   - **Approach**: Use dialect methods, test both databases thoroughly
   - **Validation**: Integration tests on both databases

### Contingency Plans

- **If polymorphic mappings incomplete**:
  - Add mappings iteratively as tests fail
  - Prioritize common properties (value, onset, deceased)
  - Document known gaps for future work

- **If performance impact significant**:
  - Profile queries to identify bottlenecks
  - Consider caching polymorphic resolutions
  - Defer optimization to future sprint if needed

- **If compliance gain less than expected**:
  - Analyze failing tests to understand gaps
  - Identify if type casting (SP-012-004) is needed first
  - Adjust expectations, document findings

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 1.0 hour (research polymorphic properties, plan implementation)
- **Implementation**: 10.0 hours (type registry, AST adapter, SQL generation)
- **Testing**: 2.0 hours (unit tests, integration tests, official suite)
- **Documentation**: 0.5 hours (code comments, docstrings)
- **Review and Refinement**: 0.5 hours (self-review, address feedback)
- **Total Estimate**: 14.0 hours (~12h estimate + 2h buffer)

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**:
- Clear requirements and examples from official tests
- Well-defined scope (InvocationTerm handling only)
- Existing infrastructure (AST adapter, type registry)
- Risk: Parser may generate unexpected structures, polymorphic mappings may be incomplete

### Factors Affecting Estimate

- **Positive**: Existing infrastructure, clear examples, focused scope
- **Risk**: Unknown parser behaviors, incomplete FHIR knowledge, multi-database complexity
- **Buffer**: 2h buffer (17%) for unexpected issues

---

## Success Metrics

### Quantitative Measures

- **Type Functions Compliance**: 48/116 → 75-85/116 (+27-37 tests, 65-73%)
- **Overall Compliance**: 72% → ~76% (+4%)
- **New Unit Tests**: 30+ tests, 100% passing
- **Integration Tests**: 4+ tests, 100% passing
- **Zero Regressions**: 1901 passing tests maintained

### Qualitative Measures

- **Code Quality**: Clean, well-documented polymorphic resolution logic
- **Architecture Alignment**: Business logic in AST adapter, syntax in dialect
- **Maintainability**: Easy to add new polymorphic properties
- **Performance**: COALESCE pattern performs well (no noticeable slowdown)

### Compliance Impact

- **Type Functions**: Major improvement (41% → 65%+)
- **Overall FHIRPath**: Moderate improvement (72% → 76%+)
- **Foundation**: Enables SP-012-004 and SP-012-005 (complete Type Functions)

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments for polymorphic resolution logic
- [x] Function/method documentation for visit_invocationTerm
- [x] POLYMORPHIC_PROPERTIES dictionary documented with examples
- [x] Example usage in docstrings

### Architecture Documentation

- [ ] Document polymorphic property resolution pattern
- [ ] Explain COALESCE approach and rationale
- [ ] Diagram: FHIRPath → InvocationTerm → SQL COALESCE
- [ ] Performance characteristics of polymorphic resolution

### User Documentation

- [ ] How polymorphic properties work in FHIRPath
- [ ] Examples of polymorphic property access
- [ ] Troubleshooting polymorphic resolution issues
- [ ] List of supported polymorphic properties

---

## Progress Tracking

### Status

- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [x] In Testing
- [ ] In Review
- [ ] Completed
- [ ] Blocked

### Progress Updates

| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-10-22 | Not Started | Task created, awaiting start | SP-012-002 prerequisite | Begin polymorphic property research |
| 2025-10-22 | In Development | Implemented polymorphic properties dictionary, InvocationTerm handler, path expression polymorphic marking | None | Test and validate |
| 2025-10-22 | In Testing | All AST adapter unit tests passing, polymorphic marking verified | None | Integration testing and commit |

### Completion Checklist

- [ ] POLYMORPHIC_PROPERTIES dictionary created
- [ ] resolve_polymorphic_property() helper implemented
- [ ] visit_invocationTerm() method implemented
- [ ] SQL fragment generation working
- [ ] COALESCE pattern generated correctly
- [ ] Both databases supported (DuckDB + PostgreSQL)
- [ ] Unit tests written and passing (30+ tests)
- [ ] Integration tests passing (4+ tests)
- [ ] Official test suite shows improvement (+27-37 tests)
- [ ] Zero regressions verified
- [ ] Code reviewed and approved
- [ ] Documentation complete

---

## Review and Sign-off

### Self-Review Checklist

- [ ] InvocationTerm nodes handled without errors
- [ ] Polymorphic property resolution correct
- [ ] SQL generated correctly for both databases
- [ ] All unit tests passing (30+ tests)
- [ ] Integration tests passing on both databases
- [ ] Official compliance improved (+27-37 tests)
- [ ] Zero regressions in existing tests
- [ ] Code follows thin dialect architecture
- [ ] Documentation complete and accurate

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [Pending]
**Review Status**: Pending
**Review Comments**: [To be completed after implementation]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [Pending]
**Status**: Pending
**Comments**: [To be completed after review]

---

## Post-Completion Analysis

### Actual vs. Estimated

- **Time Estimate**: 12 hours
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
**Status**: Not Started

---

*This task addresses the #2 critical gap from SP-010, enabling polymorphic property access and unblocking 68 Type Functions tests. Expected compliance improvement: +27-37 tests (+4% overall compliance).*
