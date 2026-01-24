# Task: Implement collection Flag Support for ViewDefinition Columns

**Task ID**: SP-020-004
**Sprint**: 020
**Task Name**: Implement collection=true/false Flag in ViewDefinition Column Definitions
**Assignee**: Junior Developer
**Created**: 2025-11-15
**Last Updated**: 2025-11-15

---

## Task Overview

### Description

Implement support for the `collection` flag in SQL-on-FHIR ViewDefinition column definitions. The collection flag controls whether a column returns a single value or an array of values.

**SQL-on-FHIR Specification**: https://build.fhir.org/ig/FHIR/sql-on-fhir-v2/StructureDefinition-ViewDefinition.html#collection

**Collection Flag Behavior**:
- **`collection: false`** (default): Return first element only (scalar value)
- **`collection: true`**: Return all elements as array (collection)

**Example ViewDefinition with collection**:
```json
{
  "resource": "Patient",
  "select": [{
    "column": [
      {"name": "first_family", "path": "name.family", "collection": false},
      {"name": "all_families", "path": "name.family", "collection": true}
    ]
  }]
}
```

**Expected Result**:
```
| first_family | all_families        |
|--------------|---------------------|
| "Smith"      | ["Smith", "Jones"]  |
```

**Current State**: collection flag ignored, 5 tests failing
**Expected State**: collection flag fully functional, 5 tests passing

**Impact**: Unblocks 5 SQL-on-FHIR compliance tests, enables array vs scalar control

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
- [ ] High (Important for sprint success)
- [x] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **Parse collection Flag**: Extract `collection` property from column definitions
   - Default value: `false` (scalar)
   - Valid values: `true` (array), `false` (scalar)
   - Invalid values should raise error or use default

2. **Scalar Extraction (collection: false)**: Return first element only
   - For arrays: Use `[0]` indexing or `.first()` equivalent
   - For scalars: Return value as-is
   - Null handling: Empty arrays return null

3. **Array Extraction (collection: true)**: Return all elements as array
   - For arrays: Return entire array
   - For scalars: Return as single-element array
   - Database representation: JSON array string

4. **Integration with forEach**: collection flag interacts with forEach context
   - `collection: false` in forEach: First element of forEach-relative path
   - `collection: true` in forEach: All elements of forEach-relative path

### Non-Functional Requirements
- **Performance**: collection flag should not significantly impact query performance
- **Compliance**: 100% SQL-on-FHIR specification compliance for collection flag
- **Database Support**: Must work on DuckDB (primary) and PostgreSQL (structure)
- **Error Handling**: Clear errors for invalid collection values

### Acceptance Criteria
- [ ] collection flag parsed from column definitions
- [ ] `collection: false` returns scalar (first element) - default behavior
- [ ] `collection: true` returns array (all elements)
- [ ] collection works with regular columns
- [ ] collection works with forEach columns
- [ ] Null handling: empty arrays return null for collection: false
- [ ] All 5 collection compliance tests passing
- [ ] Zero regressions in existing tests

---

## Technical Specifications

### Affected Components
- **SQLGenerator**: Modify JSON extraction to handle collection flag
- **Column Extraction Logic**: Different SQL for collection: true vs false
- **forEach Integration**: collection flag in forEach context

### File Modifications
- **`fhir4ds/sql/generator.py`**: Modify (add collection flag handling)
- **`tests/unit/test_sql_generator.py`**: Add collection flag tests

### Database Considerations

**DuckDB collection Implementations**:
```sql
-- collection: false (scalar - first element only)
json_extract_string(resource, '$.name[0].family')

-- collection: true (array - all elements)
json_extract(resource, '$.name[*].family')
-- OR
list_transform(json_extract(resource, '$.name'), x -> json_extract_string(x, '$.family'))
```

**PostgreSQL collection Implementations**:
```sql
-- collection: false (scalar - first element)
resource->'name'->0->>'family'

-- collection: true (array - all elements)
jsonb_path_query_array(resource, '$.name[*].family')
```

---

## Dependencies

### Prerequisites
1. **SP-019-004 Completed**: SQLGenerator multi-column fixes (DONE ✅)
2. **SP-020-003 Completed** (Optional): forEach support enhances collection behavior
3. **JSON Array Functions**: Database JSON array manipulation functions

### Blocking Tasks
None - can start immediately (though forEach integration is enhanced if SP-020-003 done)

### Dependent Tasks
None - this is a standalone feature

---

## Implementation Approach

### High-Level Strategy

**Approach**: Extend SQLGenerator column extraction to detect `collection` flag and generate different JSON extraction SQL based on flag value.

**Key Insight**: collection flag primarily affects JSON path construction:
- `collection: false` → `$.path[0]` (first element)
- `collection: true` → `$.path[*]` (all elements) or array aggregation

**Simple Implementation**: Start with basic collection support, enhance for forEach later

### Implementation Steps

#### Step 1: Analyze collection Requirements (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Study SQL-on-FHIR collection specification
  - Review test cases in `tests/compliance/sql_on_fhir/official_tests/tests/collection.json`
  - Research database JSON array extraction functions
  - Design collection SQL generation approach

- **Key Concepts**:
  ```
  # collection: false (default)
  # "name.family" with collection: false
  # → Return first family name only
  # SQL: json_extract_string(resource, '$.name[0].family')

  # collection: true
  # "name.family" with collection: true
  # → Return all family names as array
  # SQL: json_extract(resource, '$.name[*].family')
  # OR: list_transform(json_extract(resource, '$.name'), x -> json_extract_string(x, '$.family'))
  ```

- **Database Function Research**:
  ```sql
  -- DuckDB: Test array extraction
  SELECT json_extract('{"name": [{"family": "A"}, {"family": "B"}]}', '$.name[*].family');

  -- PostgreSQL: Test array extraction
  SELECT jsonb_path_query_array('{"name": [{"family": "A"}, {"family": "B"}]}'::jsonb, '$.name[*].family');
  ```

- **Validation**: Understand collection semantics and database functions

#### Step 2: Parse collection Flag from Column Definitions (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Modify column extraction to read `collection` property
  - Default to `false` if not specified
  - Validate collection value (boolean)

- **Code Pattern**:
  ```python
  # In generate_sql() method, when processing columns
  for column in columns:
      name = column["name"]
      path = column["path"]
      column_type = column.get("type", "string")
      is_collection = column.get("collection", False)  # NEW: Get collection flag

      # Pass is_collection to extraction logic
      extract_expr = self._generate_column_extract(
          column,
          context="resource",
          is_collection=is_collection  # NEW parameter
      )
  ```

- **Validation**: collection flag correctly parsed

#### Step 3: Implement Scalar Extraction (collection: false) (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Ensure current implementation handles collection: false correctly
  - This is the default behavior (first element only)
  - May already be working due to SP-019-004 fixes

- **Implementation Note**:
  ```python
  # collection: false is the DEFAULT and already implemented
  # For "name.family" with collection: false:
  # → "$.name[0].family" (already done in SP-019-004)

  # Minimal or no changes needed for collection: false
  ```

- **Validation**: collection: false works (likely already working)

#### Step 4: Implement Array Extraction (collection: true) for DuckDB (2 hours)
- **Estimated Time**: 2 hours
- **Key Activities**:
  - Generate array extraction SQL for collection: true
  - Use DuckDB JSON array functions
  - Handle different column types (string arrays, integer arrays, etc.)

- **Implementation**:
  ```python
  def _generate_column_extract(self, column: dict, context: str = "resource", is_collection: bool = False) -> str:
      """
      Generate JSON extraction expression for a column.

      Args:
          column: Column definition with name, path, type, collection
          context: Context to extract from (resource or forEach alias)
          is_collection: Whether to return array (true) or scalar (false)

      Returns:
          SQL extraction expression
      """
      path = column["path"]
      column_type = column.get("type", "string")

      if is_collection:
          # collection: true - return array
          return self._generate_array_extraction(path, column_type, context)
      else:
          # collection: false - return scalar (first element)
          return self._generate_scalar_extraction(path, column_type, context)

  def _generate_array_extraction(self, path: str, column_type: str, context: str) -> str:
      """Generate SQL for array extraction (collection: true)."""

      # Convert path to JSON array path
      # "name.family" → "$.name[*].family"
      json_path = self._convert_path_to_array_path(path)

      if self.dialect.lower() == "duckdb":
          # DuckDB: Use json_extract with [*] wildcard
          # This returns a JSON array
          if column_type == "string":
              # For string arrays, extract and return as JSON array
              # Option 1: Simple wildcard (may return JSON array of strings)
              return f"json_extract(resource, '{json_path}')"

              # Option 2: Transform (more explicit)
              # base_path = path.split('.')[0]  # e.g., "name"
              # field = '.'.join(path.split('.')[1:])  # e.g., "family"
              # return f"list_transform(json_extract(resource, '$.{base_path}'), x -> json_extract_string(x, '$.{field}'))"

          elif column_type in ["integer", "decimal", "boolean"]:
              # For other types, similar approach
              return f"json_extract(resource, '{json_path}')"

      elif self.dialect.lower() == "postgresql":
          # PostgreSQL: Use jsonb_path_query_array
          clean_path = json_path.lstrip('$.')
          return f"jsonb_path_query_array(resource, '$.{clean_path}')"

      return f"json_extract(resource, '{json_path}')"

  def _convert_path_to_array_path(self, path: str) -> str:
      """
      Convert FHIRPath to JSON array path.

      Args:
          path: FHIRPath like "name.family"

      Returns:
          JSON path like "$.name[*].family"

      Example:
          >>> gen._convert_path_to_array_path("name.family")
          "$.name[*].family"

          >>> gen._convert_path_to_array_path("contact.telecom.value")
          "$.contact[*].telecom[*].value"
      """
      # Simple approach: Replace dots with [*].
      # "name.family" → "$.name[*].family"
      # But need to be smarter about which fields are arrays

      # SIMPLE VERSION (may need refinement):
      # Assume first segment is array, rest are fields
      parts = path.split('.')
      if len(parts) == 1:
          return f"$.{parts[0]}[*]"
      else:
          # "name.family" → "$.name[*].family"
          return f"$.{parts[0]}[*].{'.'.join(parts[1:])}"

      # TODO: For nested arrays like "contact.telecom.value",
      # may need schema knowledge to know that both contact and telecom are arrays
      # For now, start simple and enhance based on test failures
  ```

- **Validation**:
  ```bash
  # Test array extraction
  python3 -c "
  from fhir4ds.sql.generator import SQLGenerator
  gen = SQLGenerator('duckdb')
  view_def = {
      'resource': 'Patient',
      'select': [{
          'column': [
              {'name': 'families', 'path': 'name.family', 'collection': True}
          ]
      }]
  }
  sql = gen.generate_sql(view_def)
  print(sql)
  # Should see array extraction (wildcard [*] or list_transform)
  "
  ```

#### Step 5: Handle Null Cases (Empty Arrays) (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Ensure empty arrays return null for collection: false
  - Ensure empty arrays return empty array [] for collection: true
  - Test edge cases

- **Edge Cases**:
  ```python
  # Patient with no names
  {"id": "pt1", "name": []}

  # collection: false → name.family should return null (no first element)
  # collection: true → name.family should return [] (empty array)
  ```

- **Implementation**: May need COALESCE or conditional logic

- **Validation**: Null handling tests passing

#### Step 6: Integrate with forEach Context (1 hour)
- **Estimated Time**: 1 hour (skip if SP-020-003 not done yet)
- **Key Activities**:
  - Ensure collection flag works within forEach columns
  - collection: false in forEach → first element relative to forEach context
  - collection: true in forEach → all elements relative to forEach context

- **Example**:
  ```json
  {
    "forEach": "name",
    "column": [
      {"name": "first_given", "path": "given", "collection": false},
      {"name": "all_given", "path": "given", "collection": true}
    ]
  }
  ```

- **Expected**: Within forEach "name", extract first vs all given names

- **Validation**: collection works in forEach context

#### Step 7: Create Unit Tests (2 hours)
- **Estimated Time**: 2 hours
- **Key Activities**:
  - Test collection: false (scalar extraction)
  - Test collection: true (array extraction)
  - Test with different types
  - Test null cases
  - Test with forEach (if implemented)

- **Test Examples**:
  ```python
  class TestSQLGeneratorCollection:
      def test_collection_false_scalar(self):
          """Test collection: false returns scalar."""
          generator = SQLGenerator(dialect="duckdb")
          view_def = {
              "resource": "Patient",
              "select": [{
                  "column": [{
                      "name": "family",
                      "path": "name.family",
                      "collection": False
                  }]
              }]
          }

          sql = generator.generate_sql(view_def)

          # Should extract first element only (scalar)
          assert "[0]" in sql or "first" in sql.lower()

      def test_collection_true_array(self):
          """Test collection: true returns array."""
          generator = SQLGenerator(dialect="duckdb")
          view_def = {
              "resource": "Patient",
              "select": [{
                  "column": [{
                      "name": "families",
                      "path": "name.family",
                      "collection": True
                  }]
              }]
          }

          sql = generator.generate_sql(view_def)

          # Should extract array (wildcard or transform)
          assert "[*]" in sql or "list_transform" in sql

      def test_collection_default_is_false(self):
          """Test that collection defaults to false if not specified."""
          generator = SQLGenerator(dialect="duckdb")
          view_def = {
              "resource": "Patient",
              "select": [{
                  "column": [{
                      "name": "family",
                      "path": "name.family"
                      # No collection specified - should default to false
                  }]
              }]
          }

          sql = generator.generate_sql(view_def)

          # Should behave like collection: false (scalar)
          assert "[0]" in sql or "first" in sql.lower()

      def test_collection_with_foreach(self):
          """Test collection flag in forEach context."""
          generator = SQLGenerator(dialect="duckdb")
          view_def = {
              "resource": "Patient",
              "select": [{
                  "forEach": "name",
                  "column": [
                      {"name": "first_given", "path": "given", "collection": False},
                      {"name": "all_given", "path": "given", "collection": True}
                  ]
              }]
          }

          sql = generator.generate_sql(view_def)

          # Both columns should be present
          assert "first_given" in sql
          assert "all_given" in sql
  ```

- **Validation**:
  ```bash
  PYTHONPATH=. pytest tests/unit/test_sql_generator.py::TestSQLGeneratorCollection -v
  ```

#### Step 8: Run Compliance Tests (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Run collection compliance tests
  - Debug and fix issues
  - Verify all 5 tests passing

- **Test Commands**:
  ```bash
  # Run collection tests
  PYTHONPATH=. pytest tests/compliance/sql_on_fhir/test_sql_on_fhir_compliance.py -k "collection" -v --tb=short

  # Run all compliance tests
  PYTHONPATH=. pytest tests/compliance/sql_on_fhir/test_sql_on_fhir_compliance.py -v --tb=short
  ```

- **Expected Results**:
  - collection tests: 5/5 passing
  - Zero regressions

- **Validation**: All collection tests passing

#### Step 9: Update Documentation (1 hour)
- **Estimated Time**: 1 hour
- **Key Activities**:
  - Document collection flag behavior
  - Add usage examples
  - Update SQLGenerator docstring

- **Validation**: Documentation is clear

### Alternative Approaches Considered

- **Option A: Always return arrays, let application filter** - Rejected (not per spec, bad UX)
- **Option B: Use FHIRPath .first() for scalar** - Rejected (mixing concerns, complex)
- **Option C: JSON path with [0] vs [*]** - Selected (simple, efficient, SQL-native)

---

## Testing Strategy

### Unit Testing
- **New Tests Required**:
  - `test_collection_false_scalar()` - Scalar extraction
  - `test_collection_true_array()` - Array extraction
  - `test_collection_default_is_false()` - Default behavior
  - `test_collection_with_different_types()` - Integer, boolean arrays
  - `test_collection_null_handling()` - Empty arrays
  - `test_collection_with_foreach()` - collection in forEach context

- **Coverage Target**: 90%+ coverage for collection code paths

### Integration Testing
- **Database Testing**:
  - Run on DuckDB with real data
  - Verify arrays returned correctly
  - Verify scalars returned correctly

### Compliance Testing
- **SQL-on-FHIR collection Tests**: 5 tests expected to pass
  - collection: false
  - collection: true
  - collection in forEach context

- **Regression Testing**:
  - All existing passing tests must still pass

### Manual Testing
- **Test Scenarios**:
  ```python
  # Scenario 1: Scalar (collection: false)
  column: {"name": "family", "path": "name.family", "collection": false}

  # Scenario 2: Array (collection: true)
  column: {"name": "families", "path": "name.family", "collection": true}

  # Scenario 3: Default (no collection specified)
  column: {"name": "family", "path": "name.family"}
  # Should behave like collection: false

  # Scenario 4: In forEach
  forEach: "name"
  column: {"name": "given", "path": "given", "collection": true}
  ```

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database array functions complex | Medium | Medium | Research functions early, test with simple cases |
| Array type handling difficult | Low | Medium | Start with strings, add other types incrementally |
| Nested arrays (collection in forEach) | Medium | Medium | Test simple case first, add forEach integration later |
| PostgreSQL syntax different | Low | Low | Focus on DuckDB, PostgreSQL structure only |

### Implementation Challenges

1. **Array Path Construction**: Knowing which fields are arrays
   - **Approach**: Use simple heuristics, refine based on test failures

2. **Type Handling**: Arrays of different types (string, integer, etc.)
   - **Approach**: Handle string arrays first, add others incrementally

### Contingency Plans

- **If array extraction complex**: Implement collection: false only, defer collection: true
- **If timeline extends**: Skip forEach integration, focus on basic collection support
- **If database functions insufficient**: Use alternative SQL patterns

---

## Estimation

### Time Breakdown
- **Analysis and Design**: 1 hour
- **Implementation**: 6 hours (parse: 1h, scalar: 1h, array: 2h, null: 1h, forEach: 1h)
- **Testing**: 3 hours (unit: 2h, compliance: 1h)
- **Documentation**: 1 hour
- **Review and Refinement**: 1 hour
- **Total Estimate**: 12 hours (~1.5 days)

### Confidence Level
- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: High confidence because:
- Feature is well-scoped (collection flag in columns) ✅
- Clear examples in compliance tests ✅
- Limited to JSON path manipulation ✅
- Builds on existing column extraction logic ✅

### Factors Affecting Estimate
- **Array Function Complexity**: If DuckDB array functions difficult, add 1-2 hours
- **forEach Integration**: If complex interaction with forEach, add 1-2 hours
- **Type Handling**: If multiple types problematic, add 1 hour

---

## Success Metrics

### Quantitative Measures
- **SQL-on-FHIR Compliance**: +5 tests passing
- **collection Tests**: 5/5 passing
- **Zero Regressions**: All existing tests still passing

### Qualitative Measures
- **Code Quality**: Clean collection flag handling
- **Feature Completeness**: Both collection: true and false work
- **Maintainability**: Easy to understand array vs scalar logic

### Compliance Impact
- **Specification Compliance**: Correct collection flag semantics
- **Feature Support**: Critical for returning arrays vs scalars

---

## Documentation Requirements

### Code Documentation
- [x] Inline comments for collection flag handling
- [x] Docstrings for array extraction methods
- [x] Examples showing collection: true vs false

### Architecture Documentation
- [ ] collection flag implementation notes
- [ ] Array vs scalar extraction approach

### User Documentation
- [ ] None required (follows SQL-on-FHIR spec)

---

## Progress Tracking

### Status
- [x] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [ ] Completed
- [ ] Blocked

### Progress Updates
| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-11-15 | Not Started | Task created | None | Analyze collection requirements |

### Completion Checklist
- [ ] collection flag parsed from column definitions
- [ ] collection: false returns scalar (first element)
- [ ] collection: true returns array (all elements)
- [ ] Default behavior (no collection specified) is scalar
- [ ] Null handling for empty arrays correct
- [ ] collection works with forEach (if SP-020-003 done)
- [ ] 6+ unit tests created and passing
- [ ] All 5 collection compliance tests passing
- [ ] Zero regressions in existing tests
- [ ] Code reviewed and approved
- [ ] Documentation completed

---

## Review and Sign-off

### Self-Review Checklist
- [ ] collection flag implementation correct
- [ ] Both collection: true and false work
- [ ] All collection tests pass
- [ ] Code is clean and maintainable
- [ ] No performance degradation
- [ ] Documentation complete

### Peer Review
**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [Date]
**Review Status**: [Pending/Approved/Changes Requested]
**Review Comments**: [Detailed feedback]

### Final Approval
**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [Date]
**Status**: [Approved/Conditionally Approved/Not Approved]
**Comments**: [Final approval comments]

---

## Post-Completion Analysis

### Actual vs. Estimated
- **Time Estimate**: 12 hours
- **Actual Time**: [To be filled]
- **Variance**: [To be filled]

### Lessons Learned
- [To be filled after completion]

### Future Improvements
- **Technical**: Could add schema-aware array detection
- **Architecture**: Could optimize array extraction for large datasets
- **Testing**: Could add more edge cases

---

**Task Created**: 2025-11-15 by Senior Solution Architect/Engineer
**Last Updated**: 2025-11-15
**Status**: Not Started - Ready for Junior Developer

---

## Additional Guidance for Junior Developer

### Key Concepts

**collection Flag**:
- Controls whether to return scalar (first element) or array (all elements)
- Default is `false` (scalar)
- Important for flexibility in ViewDefinition output

**Database Array Extraction**:
- DuckDB: Use `[*]` wildcard or `list_transform()`
- PostgreSQL: Use `jsonb_path_query_array()`

### Debugging Tips

1. **Test Database Functions**:
   ```sql
   -- DuckDB: Test array extraction
   SELECT json_extract('{"name": [{"family": "A"}, {"family": "B"}]}', '$.name[*].family');
   ```

2. **Print JSON Paths**: See what paths are generated
   ```python
   print(f"Array path: {array_path}")
   ```

3. **Test Incrementally**: Implement collection: false first, then collection: true

### Common Pitfalls

1. **Don't Forget Default**: collection defaults to false if not specified
2. **Array Path Syntax**: [*] for all elements vs [0] for first
3. **Type Handling**: Different types may need different extraction
4. **Null Cases**: Empty arrays should return null for scalar, [] for array

### Success Looks Like

```bash
# Before implementation:
pytest tests/compliance/sql_on_fhir/ -k "collection" -q
# Result: 5 failed

# After implementation:
pytest tests/compliance/sql_on_fhir/ -k "collection" -q
# Result: 5 passed
```

This is a focused feature - implement incrementally and test frequently! 📦
