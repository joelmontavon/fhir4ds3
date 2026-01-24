# Task: SP-014-004 - Implement Union Operator

**Task ID**: SP-014-004
**Sprint**: Sprint 014 - Regression Analysis and Recovery
**Task Name**: Implement FHIRPath Union Operator (|)
**Assignee**: Junior Developer
**Created**: 2025-10-28
**Last Updated**: 2025-10-28

---

## Task Overview

### Description

Implement the FHIRPath union operator (`|`) which combines two collections into a single collection, preserving all elements including duplicates. This is the **highest-impact fix** identified in SP-014-002 root cause analysis, affecting 84 tests across multiple categories (comparison_operators, collection_functions, arithmetic_operators).

**Context from SP-014-002**: The union operator is currently unimplemented, causing immediate failures whenever `|` appears in a FHIRPath expression. Unlike mathematical set union which removes duplicates, FHIRPath union preserves all elements from both operands, making it semantically equivalent to list/array concatenation.

**Example Failing Expressions**:
```fhirpath
(1|2|3).count()                              // Should return 3
Patient.name.select(given|family).distinct()  // Should combine given and family names
(1|2).exclude(4)                             // Should return [1, 2]
```

**Impact**: Implementing this operator will improve compliance from 38.0% to approximately 46-47%, a gain of +84 tests across 3 major categories.

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

**Rationale**: Highest-impact single fix from SP-014-002 analysis. Required for FHIRPath specification compliance and blocks multiple test categories.

---

## Requirements

### Functional Requirements

1. **Parse Union Operator**: FHIRPath parser must recognize `|` as a binary operator with correct precedence
   - Precedence: Lower than arithmetic operators, higher than logical operators
   - Associativity: Left-associative (e.g., `1|2|3` evaluates as `(1|2)|3`)

2. **Handle All Operand Types**: Union must work with:
   - Literals: `1|2|3` → `[1, 2, 3]`
   - Collections: `[1,2]|[3,4]` → `[1, 2, 3, 4]`
   - Mixed scalars and collections: `1|[2,3]` → `[1, 2, 3]`
   - Path expressions: `Patient.name.given|Patient.name.family`

3. **Preserve Duplicates**: FHIRPath union preserves duplicates (unlike set union)
   - `(1|1|2)` → `[1, 1, 2]` (NOT `[1, 2]`)
   - `(1|2|2)` → `[1, 2, 2]`

4. **Generate Correct SQL**: Translate union to appropriate SQL construct
   - DuckDB: Use `list_concat()` or `array_concat()` for arrays
   - PostgreSQL: Use `array_cat()` or `||` operator for arrays
   - Ensure SQL maintains element order and duplicates

### Non-Functional Requirements

- **Performance**: Union should execute in O(n+m) time where n and m are operand sizes
- **Compliance**: Must pass all 84 union operator tests from official FHIRPath R4 test suite
- **Database Support**: Must work identically in both DuckDB and PostgreSQL
- **Error Handling**: Graceful handling of NULL operands, empty collections, type mismatches

### Acceptance Criteria

- [ ] Parser recognizes `|` operator with correct precedence
- [ ] AST adapter converts union operator to appropriate node representation
- [ ] SQL translator generates correct SQL for union operations
- [ ] Union works with literals: `(1|2|3).count() = 3`
- [ ] Union works with collections: `([1,2]|[3,4]).count() = 4`
- [ ] Union preserves duplicates: `(1|1|2).count() = 3`
- [ ] Union works in complex expressions: `Patient.name.select(given|family)`
- [ ] At least 60 of 84 union operator tests passing (70% target)
- [ ] No regressions in other test categories
- [ ] Both DuckDB and PostgreSQL implementations working

---

## Technical Specifications

### Affected Components

- **FHIRPath Parser** (`fhir4ds/fhirpath/parser.py` or grammar file): Add `|` operator to grammar
- **AST Adapter** (`fhir4ds/fhirpath/sql/ast_adapter.py`): Handle union operator AST nodes
- **SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): Generate SQL for union operations
- **Database Dialects** (`fhir4ds/fhirpath/dialects/`): Dialect-specific SQL generation

### File Modifications

**Analysis Phase** (identify exact files):
- **MODIFY**: Parser grammar or `fhir4ds/fhirpath/parser.py` - Add union operator recognition
- **MODIFY**: `fhir4ds/fhirpath/sql/ast_adapter.py` - Add `visit_union_operator` or similar method
- **MODIFY**: `fhir4ds/fhirpath/sql/translator.py` - Add union SQL generation logic
- **MODIFY**: `fhir4ds/fhirpath/dialects/duckdb.py` - DuckDB-specific array concatenation
- **MODIFY**: `fhir4ds/fhirpath/dialects/postgresql.py` - PostgreSQL-specific array concatenation
- **CREATE**: `tests/unit/fhirpath/test_union_operator.py` - Unit tests for union operator

**Note**: Exact file paths may vary based on codebase structure. Verify during implementation.

### Database Considerations

- **DuckDB**:
  - Array concatenation: `list_concat(arr1, arr2)` or `array_concat(arr1, arr2)`
  - Ensure preserves order and duplicates
  - Test with JSON arrays: `json_merge_preserve('[1,2]', '[3,4]')` might be alternative

- **PostgreSQL**:
  - Array concatenation: `array_cat(arr1, arr2)` or `arr1 || arr2`
  - JSONB arrays: Use `jsonb_concat()` or custom function
  - Ensure consistent behavior with DuckDB

- **Type Handling**: Both databases need consistent handling of:
  - NULL operands: `NULL | [1,2]` should return `[1,2]` or `NULL` based on FHIRPath spec
  - Empty collections: `[] | [1,2]` should return `[1,2]`
  - Scalar promotion: `1 | [2,3]` should promote `1` to `[1]` then concatenate

---

## Dependencies

### Prerequisites

1. **SP-014-001 Complete**: Baseline validation confirms 84 union operator failures
2. **SP-014-002 Complete**: Root cause analysis identifies union operator as critical fix
3. **FHIRPath Specification**: Section 6.5 on Collections (union operator semantics)
4. **Parser Architecture Understanding**: Know how FHIRPath parser works in fhir4ds

### Blocking Tasks

- None (this is an independent fix)

### Dependent Tasks

- **SP-014-006 (Type Conversion)**: May benefit from union operator working
- **SP-014-007 (Path Navigation)**: Some path navigation tests use union operator

---

## Implementation Approach

### High-Level Strategy

**Approach**: Implement union operator support through the full FHIRPath-to-SQL translation pipeline, from parser recognition to SQL generation, using array concatenation as the underlying SQL mechanism.

**Key Decisions**:
1. **Semantic Model**: Treat union as array concatenation (preserves duplicates, order)
2. **SQL Strategy**: Use database-native array concatenation functions
3. **Type Promotion**: Automatically promote scalars to single-element collections
4. **Incremental Development**: Start simple (literals), progressively handle complex cases

**Rationale**: Array concatenation directly matches FHIRPath union semantics and is natively supported by both target databases.

### Implementation Steps

#### Step 1: Analyze Current Parser and Identify Insertion Point (1 hour)

**Objective**: Understand how existing binary operators are handled and determine where to add union operator.

**Key Activities**:
1. Review parser code or grammar file to see how operators like `+`, `=`, `and` are defined
2. Identify operator precedence table (union should be between arithmetic and logical)
3. Locate AST adapter's binary operator handling (likely `visit_binary_expression` or similar)
4. Review existing SQL generation for other binary operators

**Validation**:
- Document parser structure in implementation notes
- Identify exact file(s) and line numbers for modifications
- Create before/after code snippets

**Expected Output**: Clear understanding of where to make changes

---

#### Step 2: Add Union Operator to Parser Grammar (1 hour)

**Objective**: Make parser recognize `|` as a valid binary operator.

**Key Activities**:
1. Add `|` to parser's operator list with correct precedence
   ```python
   # Example (actual syntax depends on parser implementation)
   UNION_OP = '|'
   # Precedence: higher than 'and'/'or', lower than '+'/'-'
   ```

2. Ensure `|` is tokenized correctly (not confused with bitwise OR if that exists)

3. Update operator precedence table if explicit table exists

4. Test parser recognition with simple expression: `1|2`

**Validation**:
- Parser doesn't throw syntax error for `1|2`
- AST shows union operator node (even if not handled yet)
- Write temporary test to verify parser accepts union expressions

**Expected Output**: Parser recognizes union operator in expressions

---

#### Step 3: Implement AST Adapter Handler for Union (2 hours)

**Objective**: Add logic to convert union operator AST nodes to SQL-ready representation.

**Key Activities**:
1. Locate binary operator visitor method (e.g., `visit_binary_expression`)

2. Add union operator case:
   ```python
   def visit_binary_expression(self, node):
       operator = node.operator  # or however operator is accessed
       if operator == '|':
           return self._visit_union_operator(node)
       elif operator == '+':
           # ... existing cases
   ```

3. Implement `_visit_union_operator`:
   ```python
   def _visit_union_operator(self, node):
       # Visit left and right operands
       left_sql = self.visit(node.left)
       right_sql = self.visit(node.right)

       # Promote scalars to collections if needed
       left_sql = self._ensure_collection(left_sql)
       right_sql = self._ensure_collection(right_sql)

       # Generate union SQL
       return self.dialect.generate_union(left_sql, right_sql)
   ```

4. Implement `_ensure_collection` helper:
   ```python
   def _ensure_collection(self, sql_expr):
       # If expression is scalar, wrap in array constructor
       # If already array/collection, return as-is
       # Implementation depends on how collections are represented in SQL
       pass
   ```

**Validation**:
- AST adapter doesn't crash on union operator
- Generates SQL (even if SQL is incorrect initially)
- Test with: `(1|2).count()`

**Expected Output**: AST adapter handles union operator, generates SQL calls

---

#### Step 4: Implement Dialect-Specific SQL Generation (2 hours)

**Objective**: Create database-specific SQL for union operations.

**Key Activities**:
1. Add `generate_union` method to base dialect class:
   ```python
   class SQLDialect:
       def generate_union(self, left_expr: str, right_expr: str) -> str:
           raise NotImplementedError("Subclass must implement generate_union")
   ```

2. Implement for DuckDB:
   ```python
   class DuckDBDialect(SQLDialect):
       def generate_union(self, left_expr: str, right_expr: str) -> str:
           # DuckDB array concatenation
           return f"list_concat({left_expr}, {right_expr})"
           # OR: array_concat, depending on what works
   ```

3. Implement for PostgreSQL:
   ```python
   class PostgreSQLDialect(SQLDialect):
       def generate_union(self, left_expr: str, right_expr: str) -> str:
           # PostgreSQL array concatenation
           return f"array_cat({left_expr}, {right_expr})"
           # OR: ({left_expr} || {right_expr})
   ```

4. Handle edge cases:
   - NULL operands: Wrap in `COALESCE(expr, '[]'::json)` or similar
   - Type consistency: Ensure both operands are same array type

**Validation**:
- Generate sample SQL for `1|2|3` and verify it's valid for each database
- Test SQL directly in DuckDB and PostgreSQL consoles
- Verify results: `[1, 2, 3]`

**Expected Output**: Database-specific SQL generation working

---

#### Step 5: Implement Scalar-to-Collection Promotion (1 hour)

**Objective**: Automatically convert scalar values to single-element collections for union operations.

**Key Activities**:
1. Detect if operand is scalar vs collection (may need type inference)

2. Implement promotion logic:
   ```python
   def _promote_to_collection(self, sql_expr, fhirpath_type):
       if self._is_scalar_type(fhirpath_type):
           # Wrap scalar in array constructor
           return f"ARRAY[{sql_expr}]"  # PostgreSQL syntax
           # OR: f"[{sql_expr}]"  # JSON array syntax
       return sql_expr
   ```

3. Apply promotion in `_ensure_collection` (from Step 3)

4. Test with mixed cases:
   - `1|[2,3]` should work
   - `[1,2]|3` should work
   - `1|2` should work (both promoted)

**Validation**:
- Mixed scalar/collection unions work correctly
- Test: `(1|[2,3]).count() = 3`
- Test: `([1,2]|3).count() = 3`

**Expected Output**: Scalar promotion working for all cases

---

#### Step 6: Write Comprehensive Unit Tests (2 hours)

**Objective**: Create unit tests covering all union operator scenarios.

**Test Categories**:

1. **Basic Literals**:
   ```python
   def test_union_literals():
       assert execute("(1|2|3).count()") == 3
       assert execute("(1|2|3)") == [1, 2, 3]
   ```

2. **Preserve Duplicates**:
   ```python
   def test_union_preserves_duplicates():
       assert execute("(1|1|2).count()") == 3
       assert execute("(1|2|2).count()") == 3
   ```

3. **Empty Collections**:
   ```python
   def test_union_empty_collections():
       assert execute("({}|{}).count()") == 0
       assert execute("({}|1).count()") == 1
       assert execute("(1|{}).count()") == 1
   ```

4. **Complex Expressions**:
   ```python
   def test_union_with_functions():
       # Assuming Patient fixture exists
       result = execute("Patient.name.select(given|family)")
       # Verify result contains both given and family names
   ```

5. **Type Mixing**:
   ```python
   def test_union_mixed_types():
       # Test behavior with mixed types
       # Spec may define this as error or coercion
   ```

**Validation**:
- All unit tests pass
- Coverage of union operator code is >90%
- Tests work in both DuckDB and PostgreSQL

**Expected Output**: Comprehensive test suite for union operator

---

#### Step 7: Validate Against Official Test Suite (1 hour)

**Objective**: Run official FHIRPath R4 test suite and measure improvement.

**Key Activities**:
1. Run official test suite with union operator implemented:
   ```bash
   PYTHONPATH=. python3 tests/integration/fhirpath/run_official_tests.py
   ```

2. Measure compliance improvement:
   - Baseline: 38.0% (355/934 tests)
   - Target: 46-47% (+60-70 tests, conservative 70% of 84)
   - Stretch: 47-48% (+80-84 tests, all union tests)

3. Identify remaining union operator failures (if any):
   - Document specific failing tests
   - Categorize by failure type (edge cases, specific scenarios)

4. Verify no regressions:
   - Compare pass counts for all categories
   - Ensure no previously passing tests now fail

**Validation**:
- Compliance improves to at least 45% (conservative target)
- At least 60 union operator tests passing
- No regressions in other categories

**Expected Output**: Official test suite validation report

---

#### Step 8: Fix Remaining Edge Cases (1-2 hours, as needed)

**Objective**: Address any remaining union operator failures from official test suite.

**Potential Edge Cases**:
1. **NULL handling**: Spec defines NULL | collection = ?
2. **Type incompatibility**: What if union mixes incompatible types?
3. **Nested unions**: `(1|(2|3))` with different operator precedence
4. **Union with other operators**: `(1|2) + 3` - does union bind correctly?

**Approach**:
- Analyze failing tests to understand edge case
- Consult FHIRPath specification for correct behavior
- Implement fix for specific edge case
- Re-run test suite to verify

**Validation**:
- Remaining edge cases resolved
- Test count increases toward 84 target

**Expected Output**: Edge cases handled, test pass rate maximized

---

### Alternative Approaches Considered

**Alternative 1: Implement Union as SQL UNION Operator**
- **Approach**: Use SQL `UNION` or `UNION ALL` to combine results
- **Rejected Because**:
  - SQL UNION works on table rows, not array elements
  - Would require complex restructuring of query generation
  - Array concatenation is simpler and more direct mapping

**Alternative 2: Implement Union in Post-Processing**
- **Approach**: Let SQL return separate results, combine in Python
- **Rejected Because**:
  - Violates CTE-first, SQL-first architecture
  - Negates performance benefits of database processing
  - Adds complexity to result handling

**Alternative 3: Defer Union Operator to Later Sprint**
- **Approach**: Focus on other fixes first, implement union later
- **Rejected Because**:
  - Highest-impact single fix (+84 tests)
  - Relatively straightforward implementation
  - Blocks progress on multiple test categories

---

## Testing Strategy

### Unit Testing

**New Tests Required**:
- `tests/unit/fhirpath/test_union_operator.py`:
  - `test_union_literals` - Basic literal unions
  - `test_union_preserves_duplicates` - Duplicate preservation
  - `test_union_empty_collections` - Empty collection handling
  - `test_union_mixed_scalars_collections` - Scalar promotion
  - `test_union_associativity` - Left-associative evaluation
  - `test_union_with_expressions` - Union in complex expressions
  - `test_union_null_handling` - NULL operand behavior

**Modified Tests**: None (new operator, shouldn't affect existing tests)

**Coverage Target**: >90% coverage of union operator code paths

### Integration Testing

**Database Testing**:
1. **DuckDB**: Run full test suite with DuckDB backend
   ```bash
   PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k union
   ```

2. **PostgreSQL**: Run full test suite with PostgreSQL backend
   ```bash
   DATABASE_TYPE=postgresql PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k union
   ```

3. **Consistency Check**: Verify identical results from both databases

**Component Integration**:
- Test union operator with other FHIRPath features:
  - With `.count()`: `(1|2|3).count()`
  - With `.where()`: `(1|2|3).where($this > 1)`
  - With `.select()`: `Patient.name.select(given|family)`
  - With arithmetic: `(1|2) + 3` (should union first, then add? Check spec)

**End-to-End Testing**:
- Test complete FHIRPath expressions from real use cases
- Verify union works in CQL context if CQL uses FHIRPath

### Compliance Testing

**Official Test Suites**:
- Run FHIRPath R4 official test suite (all 934 tests)
- Focus on union operator tests (84 tests)
- Target: At least 60 passing (70% of 84)
- Stretch: 80+ passing (95% of 84)

**Regression Testing**:
- Run full test suite before and after implementation
- Compare pass counts for each category:
  - comparison_operators
  - collection_functions
  - arithmetic_operators
  - All other categories
- Ensure no regressions (pass count doesn't decrease)

**Performance Validation**:
- Benchmark union operator performance:
  - Small collections: `(1|2|3)` should be fast (<1ms)
  - Large collections: `large_collection | large_collection` should scale linearly
- Compare performance between DuckDB and PostgreSQL

### Manual Testing

**Test Scenarios**:
1. **Simple Union**: `(1|2|3).count()` → 3
2. **Duplicates**: `(1|1|2).count()` → 3
3. **Empty**: `({}|1|{}).count()` → 1
4. **Path Expression**: `Patient.name.select(given|family)` → combined names
5. **Nested**: `(1|(2|3))` → [1, 2, 3]

**Edge Cases**:
1. **NULL operands**: `NULL | [1,2]` - check spec for expected behavior
2. **Type mixing**: `('a'|1|true)` - should this work or error?
3. **Very large collections**: Performance test with 1000+ element unions

**Error Conditions**:
1. **Invalid syntax**: `1 |` (incomplete expression) - should parser error
2. **Database-specific failures**: Test both DuckDB and PostgreSQL error handling

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Array semantics differ between databases | Medium | High | Test extensively in both databases, ensure consistent behavior |
| Scalar promotion logic complex | Low | Medium | Follow FHIRPath spec carefully, comprehensive unit tests |
| NULL handling ambiguous in spec | Medium | Medium | Research spec, check reference implementations, document decisions |
| Parser precedence conflicts | Low | High | Review parser carefully, test precedence with mixed operators |
| Performance issues with large unions | Low | Medium | Benchmark early, optimize if needed (unlikely to be bottleneck) |

### Implementation Challenges

1. **Understanding Parser Architecture**: May take time to understand existing parser
   - **Approach**: Start with thorough code review, ask for guidance if needed
   - **Time Buffer**: Add 1 hour buffer for parser learning curve

2. **Dialect Differences**: DuckDB and PostgreSQL may have different array functions
   - **Approach**: Research both databases' array functions early
   - **Testing**: Test SQL directly in both databases before full implementation

3. **Type System Integration**: Determining scalar vs collection types
   - **Approach**: Review existing type inference code
   - **Fallback**: Conservative approach - try to determine type, default to safe handling

### Contingency Plans

- **If parser proves too complex**: Focus on AST adapter and SQL generation first, ask for parser help
- **If 84 tests seems unachievable**: Target 60 tests (70%), document remaining issues for future sprint
- **If database differences significant**: Implement DuckDB fully first, PostgreSQL as stretch goal
- **If timeline extends beyond 8 hours**: Prioritize basic functionality (literals), defer complex cases

---

## Estimation

### Time Breakdown

- **Step 1: Analyze Parser**: 1 hour
- **Step 2: Add to Parser Grammar**: 1 hour
- **Step 3: AST Adapter Handler**: 2 hours
- **Step 4: Dialect SQL Generation**: 2 hours
- **Step 5: Scalar Promotion**: 1 hour
- **Step 6: Unit Tests**: 2 hours
- **Step 7: Official Test Validation**: 1 hour
- **Step 8: Edge Cases**: 1-2 hours (as needed)
- **Total Estimate**: 11-12 hours

**Adjusted for Junior Developer**: 12-14 hours (add 10% buffer for learning)

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Operator implementation is well-defined, but parser complexity is unknown. Array concatenation is straightforward. Conservative estimate accounts for unexpected challenges.

### Factors Affecting Estimate

- **Parser Complexity**: If parser is complex, could add 2-3 hours
- **Database Differences**: If significant array function differences, could add 1-2 hours
- **Edge Cases**: If many edge cases found in testing, could add 2-4 hours
- **Junior Experience**: First time implementing operator may be slower

---

## Success Metrics

### Quantitative Measures

- **Test Pass Count**: At least +60 tests passing (target +84)
- **Compliance Improvement**: 38.0% → 45-47%
- **Category Improvements**:
  - comparison_operators: Some improvement
  - collection_functions: Significant improvement
  - arithmetic_operators: Some improvement
- **Code Coverage**: >90% coverage of union operator code
- **Performance**: Union operator executes in <10ms for typical cases

### Qualitative Measures

- **Code Quality**: Union operator code is clean, well-documented, follows project patterns
- **Architecture Alignment**: Implementation aligns with FHIRPath-to-SQL translation architecture
- **Maintainability**: Future developers can understand and modify union operator code easily
- **Specification Compliance**: Implementation matches FHIRPath specification semantics exactly

### Compliance Impact

- **Specification Compliance**: Significant step toward 100% FHIRPath compliance
- **Test Suite Results**:
  - Baseline: 355/934 passing (38.0%)
  - Conservative Target: 415/934 passing (44.4%)
  - Realistic Target: 430/934 passing (46.0%)
  - Optimistic Target: 439/934 passing (47.0%)
- **Performance Impact**: Negligible (union is simple array operation)

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments for union operator logic in AST adapter
- [x] Function/method documentation for `_visit_union_operator` and helpers
- [x] Dialect method documentation for `generate_union`
- [x] Example usage in unit test docstrings

### Architecture Documentation

- [ ] Update FHIRPath operator support matrix (document union operator supported)
- [ ] Document union operator in FHIRPath-to-SQL translation guide (if exists)
- [ ] Add union operator to architectural decision records (why array concatenation approach)

### User Documentation

- [ ] Update FHIRPath expression guide with union operator examples
- [ ] Add union operator to FHIRPath operator reference
- [ ] Include union operator in troubleshooting guide (common pitfalls)

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
| 2025-10-28 | Not Started | Task created and documented | None | Begin implementation in Week 2 Day 6 |

### Completion Checklist

- [ ] Parser recognizes union operator
- [ ] AST adapter handles union operator nodes
- [ ] DuckDB dialect generates correct SQL
- [ ] PostgreSQL dialect generates correct SQL
- [ ] Scalar promotion working
- [ ] Unit tests written and passing (>90% coverage)
- [ ] Official test suite validation complete (+60 tests minimum)
- [ ] No regressions in other test categories
- [ ] Code reviewed and approved
- [ ] Documentation completed

---

## Review and Sign-off

### Self-Review Checklist

- [ ] Implementation matches FHIRPath specification exactly
- [ ] All tests pass in both DuckDB and PostgreSQL
- [ ] Code follows established patterns (dialect approach, no business logic in dialects)
- [ ] Union preserves duplicates as specified
- [ ] Scalar promotion works correctly
- [ ] Performance is acceptable (<10ms typical cases)
- [ ] Documentation is complete and accurate
- [ ] No regressions introduced

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [To be completed]
**Review Status**: Pending
**Review Comments**: [To be added by reviewer]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [To be completed]
**Status**: Pending
**Comments**: [Final approval decision]

---

## Post-Completion Analysis

### Actual vs. Estimated

- **Time Estimate**: 12-14 hours
- **Actual Time**: [To be recorded after completion]
- **Variance**: [To be calculated and analyzed]

### Lessons Learned

1. **[Lesson 1]**: [To be documented after completion]
2. **[Lesson 2]**: [To be documented after completion]

### Future Improvements

- **Process**: [To be documented after completion]
- **Technical**: [To be documented after completion]
- **Estimation**: [To be documented after completion]

---

**Task Created**: 2025-10-28 by Junior Developer (based on SP-014-002 analysis)
**Last Updated**: 2025-10-28
**Status**: Not Started - Ready for Week 2 Implementation

---

*This task implements the highest-impact fix identified in SP-014-002 root cause analysis. Successful completion will improve compliance by approximately 9 percentage points and unblock multiple test categories.*
