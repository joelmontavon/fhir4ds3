# Task SP-011-017: Array Navigation - Translator Array Detection

**Task ID**: SP-011-017
**Renamed From**: SP-011-013-part-2
**Parent Task**: SP-011-013 (End-to-End Integration with PEP-003 Translator)
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-31
**Status**: Completed - Pending Review

---

## Task Overview

### Description

Implement array path detection in the PEP-003 translator to enable the remaining 7/10 Path Navigation expressions. The CTE infrastructure (CTEBuilder with LATERAL UNNEST support) is **already complete and merged** (SP-011-005 through SP-011-012). This task focuses solely on updating the translator to **detect array paths** and set the `requires_unnest=True` flag that the CTEBuilder already knows how to process.

**Key Architectural Insight**:
- **PEP-004 CTEBuilder** (✅ Complete): Handles LATERAL UNNEST generation when `requires_unnest=True`
- **PEP-003 Translator** (❌ Incomplete): Does not detect array paths or set the flag
- **This Task**: Add array detection to translator so CTEBuilder can do its job

**Current Blocker**:
```python
# Current translator behavior for array paths like Patient.name:
FHIRPathTranslationError: [FP040] Array flattening for path '$.name' requires
UNNEST support. Full implementation pending PEP-004 CTE infrastructure.
```

**Root Cause**: Error message is misleading - PEP-004 infrastructure EXISTS. The translator just doesn't detect arrays.

### Category
- [x] Feature Implementation (Translator Enhancement)
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation

### Priority
- [x] High (Unblocks 70% of Path Navigation functionality)
- [ ] Medium
- [ ] Low

---

## Requirements

### Functional Requirements

1. **Array Path Detection** (Primary)
   - Translator detects when a FHIRPath identifier refers to an array field (0..* cardinality)
   - Uses existing StructureDefinition metadata from SP-009-033
   - Sets `requires_unnest=True` flag on SQLFragment
   - Adds metadata needed by CTEBuilder (array_column, result_alias)

2. **SQLFragment Metadata Contract**
   - When `requires_unnest=True`, fragment includes:
     - `metadata['array_column']`: JSON path to array (e.g., 'name', 'telecom')
     - `metadata['result_alias']`: Alias for unnested items (e.g., 'name_item')
     - `metadata['source_path']`: Full JSON path for context (e.g., '$.name')

3. **Array Path Expressions** (7 total)
   - **Array fields** (4 expressions):
     - `Patient.name` → Detects array, sets flag
     - `Patient.telecom` → Detects array, sets flag
     - `Patient.address` → Detects array, sets flag
     - `Patient.identifier` → Detects array, sets flag

   - **Nested array navigation** (3 expressions):
     - `Patient.name.given` → Detects name as array, then given within each name
     - `Patient.name.family` → Detects name as array, then family within each name
     - `Patient.address.line` → Detects address as array, then line within each address

4. **Integration with Existing CTEBuilder**
   - No changes to CTEBuilder required (already handles `requires_unnest=True`)
   - CTEBuilder calls `dialect.generate_lateral_unnest()` (already implemented)
   - Translator just needs to provide correct metadata

### Non-Functional Requirements

- **Performance**: Array detection adds <1ms to translation time
- **Compatibility**: No breaking changes to existing scalar path translation
- **Testing**: 15+ unit tests for array detection logic
- **Documentation**: Update translator documentation with array detection behavior

### Acceptance Criteria

- [x] Translator detects array paths using StructureDefinition metadata
- [x] SQLFragment objects have `requires_unnest=True` for array fields
- [x] All 7 array/nested expressions execute successfully on DuckDB
- [x] All 7 array/nested expressions execute successfully on PostgreSQL
- [x] Integration tests extended to cover all 10 Path Navigation expressions (3 scalar + 7 array)
- [x] Unit tests: 15+ tests for array detection and metadata generation
- [ ] Code coverage: 90%+ for translator array detection code
- [x] Multi-database parity: Identical results for all array expressions
- [ ] Performance: <1ms overhead for array detection per expression
- [ ] Senior architect code review approved

---

## Technical Specifications

### Affected Components

1. **fhir4ds/fhirpath/sql/translator.py** (PRIMARY - ~100 lines added):
   - Add `_is_array_path()` method to detect array cardinality
   - Update `visit_identifier()` to check array status and set flag
   - Add `_generate_array_metadata()` for CTEBuilder metadata
   - Integration with existing StructureDefinition loader

2. **tests/unit/fhirpath/sql/test_translator.py** (EXPAND - ~150 lines added):
   - Add 15+ unit tests for array detection
   - Test `requires_unnest` flag setting
   - Test metadata generation
   - Test nested array detection

3. **tests/integration/fhirpath/test_end_to_end_execution.py** (EXPAND - ~100 lines added):
   - Remove xfail markers from array navigation tests
   - Add 7 new integration tests for array expressions
   - Validate CTEBuilder integration works correctly

### Implementation Details

#### 1. Array Detection Method

```python
def _is_array_path(self, identifier: str) -> bool:
    """
    Check if identifier refers to an array field using StructureDefinition metadata.

    Uses SP-009-033 StructureDefinition loader to check cardinality.
    """
    # Get current resource type from context
    resource_type = self.context.current_resource_type

    # Build full path for lookup
    full_path = f"{resource_type}.{identifier}"

    # Query StructureDefinition metadata
    element_definition = self.structure_loader.get_element_definition(full_path)

    if not element_definition:
        return False  # Unknown path, treat as scalar

    # Check cardinality max value
    max_cardinality = element_definition.get('max')

    # Array if max is '*' or a number > 1
    return max_cardinality == '*' or (
        max_cardinality and
        max_cardinality.isdigit() and
        int(max_cardinality) > 1
    )
```

#### 2. Updated visit_identifier Method

```python
def visit_identifier(self, node: IdentifierNode) -> SQLFragment:
    """
    Translate identifier to SQLFragment, detecting array paths.

    UPDATED: Now detects arrays and sets requires_unnest flag.
    """
    identifier = node.identifier

    # Root resource reference (no-op)
    if identifier == self.context.current_resource_type:
        return SQLFragment(
            expression=self.context.current_table,
            source_table=self.context.current_table
        )

    # Build JSON path from context
    self.context.push_path(identifier)
    json_path = "$." + ".".join(self.context.parent_path)

    # Check if this is an array path
    is_array = self._is_array_path(identifier)

    # Call dialect method for extraction
    sql_expr = self.dialect.extract_json_field(
        column=self.context.current_table,
        path=json_path
    )

    # Create fragment with array flag if needed
    fragment = SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table,
        requires_unnest=is_array  # ← NEW: Set flag for CTEBuilder
    )

    # Add metadata for CTEBuilder if array
    if is_array:
        fragment.metadata.update({
            'array_column': identifier,
            'result_alias': f"{identifier}_item",
            'source_path': json_path
        })

    return fragment
```

#### 3. Metadata Generation

```python
def _generate_array_metadata(self, identifier: str, json_path: str) -> dict:
    """
    Generate metadata required by CTEBuilder for UNNEST operations.

    Returns:
        dict with keys: array_column, result_alias, source_path
    """
    return {
        'array_column': identifier,
        'result_alias': f"{identifier}_item",
        'source_path': json_path,
        'unnest_depth': len(self.context.parent_path)  # Track nesting level
    }
```

### Integration with CTEBuilder

**No CTEBuilder changes needed!** The existing code already handles this:

```python
# In CTEBuilder._fragment_to_cte (ALREADY EXISTS from SP-011-005)
if fragment.requires_unnest:
    query = self._wrap_unnest_query(fragment, previous_cte)
    # Uses fragment.metadata['array_column'] and fragment.metadata['result_alias']
```

**Existing CTEBuilder._wrap_unnest_query** (from SP-011-005):
```python
def _wrap_unnest_query(self, fragment: SQLFragment, source_table: str) -> str:
    """
    Wrap fragment with UNNEST in proper CTE structure.

    ALREADY IMPLEMENTED - just needs translator to set the flag!
    """
    array_column = fragment.metadata.get('array_column')
    result_alias = fragment.metadata.get('result_alias')

    # Generate LATERAL UNNEST using dialect method
    unnest_expr = self.dialect.generate_lateral_unnest(
        source_table=source_table,
        array_column=array_column,
        alias=result_alias
    )

    return f"""
        SELECT {source_table}.id, {result_alias}
        FROM {source_table}, {unnest_expr}
    """
```

---

## Dependencies

### Prerequisites

1. **SP-011-012**: ✅ Complete (CTE assembly infrastructure)
2. **SP-011-007**: ✅ Complete (PostgreSQL LATERAL UNNEST dialect method)
3. **SP-011-006**: ✅ Complete (DuckDB LATERAL UNNEST dialect method)
4. **SP-011-005**: ✅ Complete (CTEBuilder UNNEST wrapping)
5. **SP-009-033**: ✅ Complete (StructureDefinition loader for cardinality metadata)
6. **SP-011-013**: ✅ Complete (Executor integration for scalar paths)

### Blocking Tasks

**None** - All dependencies complete! Ready to implement.

### Dependent Tasks

- **SP-011-014**: Official FHIRPath test suite validation (needs this for array tests)
- **SP-011-015**: Performance benchmarking (needs this for full expression coverage)

---

## Implementation Approach

### High-Level Strategy

**Key Insight**: This is NOT a large infrastructure task. The infrastructure (CTEBuilder, UNNEST support, dialect methods) is **already complete**. This task adds ~100 lines to the translator to detect arrays and set a flag.

**Implementation Steps**:

1. **Add StructureDefinition Integration** (1 hour)
   - Import StructureDefinition loader (already exists from SP-009-033)
   - Add `structure_loader` to translator initialization
   - **Validation**: Loader accessible, can query element definitions

2. **Implement Array Detection** (2 hours)
   - Add `_is_array_path()` method
   - Add `_generate_array_metadata()` helper
   - Add unit tests (10 tests)
   - **Validation**: Correctly detects array vs scalar paths

3. **Update visit_identifier** (1 hour)
   - Add array detection call
   - Set `requires_unnest=True` when array
   - Add metadata to fragment
   - **Validation**: Fragments have correct flags and metadata

4. **Update Unit Tests** (2 hours)
   - Remove translator error expectations for array paths
   - Add tests for `requires_unnest` flag setting
   - Add tests for metadata generation
   - Test nested array detection (name.given)
   - **Validation**: 15+ new tests passing

5. **Update Integration Tests** (1 hour)
   - Remove xfail markers from array navigation tests
   - Add remaining array expression tests (if not already present)
   - **Validation**: 7 array expression tests passing

6. **Multi-Database Validation** (1 hour)
   - Execute all 10 expressions on DuckDB
   - Execute all 10 expressions on PostgreSQL
   - Compare results (should be identical)
   - **Validation**: 100% parity confirmed

7. **Performance Testing** (30 minutes)
   - Measure array detection overhead
   - Ensure <1ms impact per expression
   - **Validation**: Performance targets met

8. **Documentation** (30 minutes)
   - Update translator documentation
   - Document array detection behavior
   - Update task progress
   - **Validation**: Documentation complete

**Estimated Time**: 8-10 hours total (much simpler than original 24h estimate)

### Alternative Approaches Considered

**Alternative 1: Hardcode Array Paths**
- **Rejected**: Not extensible, breaks when FHIR spec changes
- **This Solution**: Uses StructureDefinition metadata (dynamic, correct)

**Alternative 2: Detect Arrays at Runtime During Execution**
- **Rejected**: Too late, CTEBuilder needs flag during translation
- **This Solution**: Detect during translation phase

**Alternative 3: Add UNNEST Generation to Translator**
- **Rejected**: Violates separation of concerns, duplicates CTEBuilder
- **This Solution**: Translator sets flag, CTEBuilder handles UNNEST

---

## Testing Strategy

### Unit Testing

**Translator Array Detection Tests** (15 tests):
```python
class TestTranslatorArrayDetection:
    def test_detect_array_field_name(self):
        """Patient.name detected as array (0..*)"""
        fragment = translator.visit_identifier(IdentifierNode('name'))
        assert fragment.requires_unnest is True
        assert fragment.metadata['array_column'] == 'name'

    def test_detect_scalar_field_birthdate(self):
        """Patient.birthDate detected as scalar (0..1)"""
        fragment = translator.visit_identifier(IdentifierNode('birthDate'))
        assert fragment.requires_unnest is False

    def test_nested_array_detection(self):
        """Patient.name.given - both name and given are arrays"""
        # First visit name
        name_fragment = translator.visit_identifier(IdentifierNode('name'))
        assert name_fragment.requires_unnest is True

        # Then visit given (context now at name)
        given_fragment = translator.visit_identifier(IdentifierNode('given'))
        assert given_fragment.requires_unnest is True
```

**Coverage Target**: 90%+ for array detection code

### Integration Testing

**End-to-End Array Expression Tests** (7 tests):
```python
class TestArrayNavigationExecution:
    def test_patient_name_array(self, duckdb_executor, patient_records):
        """Patient.name returns all HumanName objects across population"""
        results = duckdb_executor.execute("Patient.name")
        # Should have more results than patients (multiple names per patient)
        assert len(results) >= len(patient_records)

    def test_patient_name_given_nested(self, duckdb_executor, patient_records):
        """Patient.name.given flattens nested arrays correctly"""
        results = duckdb_executor.execute("Patient.name.given")
        # Validate flattening: multiple given names from multiple name entries
        assert len(results) > len(patient_records)
        assert all(isinstance(r[1], str) for r in results)  # Given names are strings
```

**Multi-Database Parity Tests** (7 tests):
```python
class TestMultiDatabaseArrayParity:
    def test_name_parity(self, duckdb_executor, postgresql_executor):
        """Patient.name returns identical results on both databases"""
        duckdb_results = duckdb_executor.execute("Patient.name")
        pg_results = postgresql_executor.execute("Patient.name")
        assert len(duckdb_results) == len(pg_results)
```

### Manual Testing

1. **Interactive Translation Inspection**:
   - Translate array expressions and inspect SQLFragments
   - Verify `requires_unnest=True` set correctly
   - Check metadata includes array_column and result_alias

2. **SQL Quality Review**:
   - Review generated SQL for LATERAL UNNEST clauses
   - Verify CTE structure correct for nested arrays
   - Check alias naming consistency

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| StructureDefinition metadata incomplete | Low | Medium | SP-009-033 provides comprehensive metadata; validated in tests |
| Nested array detection edge cases | Medium | Low | Comprehensive test coverage; context tracking already works |
| CTEBuilder metadata contract mismatch | Low | High | Integration tests validate end-to-end; metadata contract documented |
| Performance overhead from metadata lookup | Low | Low | Metadata lookup is in-memory hash; <1ms validated |

### Implementation Challenges

1. **StructureDefinition Integration**:
   - **Challenge**: Correctly querying element definitions for cardinality
   - **Mitigation**: SP-009-033 provides tested API; examples in codebase

2. **Nested Array Detection**:
   - **Challenge**: Tracking context for nested paths (name.given)
   - **Mitigation**: Context stack already works for scalar paths; extend pattern

3. **Metadata Contract**:
   - **Challenge**: Ensuring CTEBuilder gets what it needs
   - **Mitigation**: Review SP-011-005 implementation; integration tests validate

---

## Estimation

### Time Breakdown

- **StructureDefinition Integration**: 1h
- **Array Detection Implementation**: 2h
- **visit_identifier Update**: 1h
- **Unit Tests**: 2h
- **Integration Tests**: 1h
- **Multi-Database Validation**: 1h
- **Performance Testing**: 0.5h
- **Documentation**: 0.5h
- **Total Estimate**: 9h

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium
- [ ] Low

**Rationale**:
- Small, focused change (~100 lines)
- All infrastructure already exists
- Clear integration contract with CTEBuilder
- StructureDefinition API well-documented
- Similar pattern already works for scalars

---

## Success Metrics

### Quantitative Measures

- **Expression Coverage**: 10/10 Path Navigation expressions (100%)
- **Array Detection Accuracy**: 100% (all array paths correctly flagged)
- **Test Count**: 15+ unit tests, 7+ integration tests passing
- **Code Coverage**: 90%+ for translator array detection code
- **Performance**: <1ms overhead for array detection
- **Multi-Database Parity**: 100% result consistency

### Qualitative Measures

- **Code Quality**: Clean, maintainable array detection logic
- **Architecture Alignment**: Proper separation (translator detects, CTEBuilder handles)
- **Maintainability**: Easy to extend for new FHIR resource types
- **Integration Quality**: Seamless integration with existing CTEBuilder

### Compliance Impact

- **FHIRPath Path Navigation**: 30% (3/10) → 100% (10/10) ✅
- **Overall FHIRPath Compliance**: Enables Sprint 011 72%+ target
- **Architecture Completion**: Completes PEP-003 + PEP-004 integration

---

## Progress Tracking

### Status
- [x] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [x] In Review
- [ ] Completed

**Current Status**: Completed - pending review (awaiting senior sign-off)

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task created with corrected scope | None (all infrastructure complete) | Begin implementation |
| 2025-10-31 | In Review | Implemented translator array detection, metadata, and multi-db tests | None | Prepare hand-off for review |

### Completion Checklist

**Implementation**:
- [x] StructureDefinition loader integrated into translator
- [x] `_is_array_path()` method implemented
- [x] `_generate_array_metadata()` helper implemented
- [x] `visit_identifier()` updated to detect arrays and set flag
- [x] SQLFragment metadata includes array_column, result_alias

**Testing**:
- [x] 15+ unit tests for array detection passing
- [x] 7 integration tests for array expressions passing
- [x] All 10 Path Navigation expressions execute on DuckDB
- [x] All 10 Path Navigation expressions execute on PostgreSQL
- [x] Multi-database parity validated (100% consistency)
- [ ] Performance validated (<1ms overhead)

**Documentation**:
- [ ] Translator documentation updated
- [ ] Array detection behavior documented
- [x] Task progress updated
- [ ] Sprint documentation updated

**Review**:
- [ ] Code coverage 90%+ achieved
- [x] Self-review completed
- [ ] Senior architect code review approved

---

## Documentation Requirements

### Code Documentation

- [ ] `_is_array_path()` method docstring
- [ ] `_generate_array_metadata()` method docstring
- [ ] `visit_identifier()` docstring updated with array detection behavior
- [ ] Inline comments explaining StructureDefinition integration

### Architecture Documentation

- [ ] Update translator documentation with array detection section
- [ ] Document metadata contract with CTEBuilder
- [ ] Add examples of array path translation

---

## Review and Sign-off

### Self-Review Checklist

- [ ] All 10 Path Navigation expressions execute successfully
- [ ] Both DuckDB and PostgreSQL tested with identical results
- [ ] Unit and integration test coverage comprehensive
- [ ] Array detection uses StructureDefinition metadata correctly
- [ ] No changes needed to CTEBuilder (validates clean integration)
- [ ] Performance overhead <1ms
- [ ] Code follows established patterns
- [ ] Documentation complete and accurate

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: Pending
**Review Status**: Pending
**Review Comments**: [To be completed during review]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: Pending
**Status**: Pending
**Comments**: [To be completed upon approval]

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Ready to Start

---

*This task completes the PEP-003 translator integration with PEP-004 CTE infrastructure, enabling full Path Navigation functionality (10/10 expressions) through simple array detection logic.*
