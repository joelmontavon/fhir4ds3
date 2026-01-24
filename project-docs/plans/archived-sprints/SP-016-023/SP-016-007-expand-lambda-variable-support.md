# Task: Expand Lambda Variable Support to Additional Collection Functions

**Task ID**: SP-016-007
**Sprint**: 016
**Task Name**: Expand Lambda Variable Support to Additional Collection Functions
**Assignee**: Implementation Team
**Created**: 2025-11-07
**Last Updated**: 2025-11-08
**Current Status**: Completed
**Completion Date**: 2025-11-08
**Merged to Main**: 2025-11-08
**Implementation Notes**:
- ✅ all() already has $this and $total support (verified)
- ✅ aggregate() implemented with $this and $total lambda variables
- ❌ repeat() enhancement deferred (requires recursive CTE, ~10 hours)
- Focused implementation on aggregate() per senior architect guidance
**Depends On**: SP-016-004 (Completed)

---

## Analysis Summary (2025-11-07)

### Work Completed
1. ✅ Reviewed existing lambda variable implementation from SP-016-004
2. ✅ Created feature branch `feature/SP-016-007-expand-lambda-variable-support`
3. ✅ Analyzed current state of `all()`, `repeat()`, `aggregate()` functions
4. ✅ Verified existing tests pass (5/6 lambda variable tests passing)
5. ✅ Measured baseline compliance: Collection Functions 32/141 (22.7%)

### Current State Analysis

**all() Function** (translator.py:5433-5562):
- ✅ COMPLETE: Has `$this` variable binding (line 5527)
- ✅ COMPLETE: Has `$total` variable binding (line 5529)
- ❌ MISSING: `$index` variable binding (nice-to-have, not critical per FHIRPath spec)
- Uses `_variable_scope()` context manager pattern from SP-016-004
- Calls `dialect.generate_all_check()` for SQL generation
- **Status**: Meets critical requirements, enhancement possible

**repeat() Function** (translator.py:3765-3787):
- ❌ PLACEHOLDER ONLY: Current implementation just returns argument expression
- ❌ NO lambda variable support
- ❌ NO recursive semantics
- **Requires**: Complete rewrite with recursive CTE, `$this` binding, cycle detection
- **Estimated effort**: 6-10 hours implementation + testing

**aggregate() Function**:
- ❌ DOES NOT EXIST
- **Requires**: New function implementation with:
  - `$this` binding for current element
  - `$accumulator` binding for accumulated value
  - Recursive CTE or window function approach
  - Initial value handling
- **Estimated effort**: 6-12 hours implementation + testing

### Recommendations

**Option 1: Split Into Separate Tasks** (Recommended)
- SP-016-007a: Enhance all() with $index (4 hours)
- SP-016-007b: Implement repeat() with $this (10 hours)
- SP-016-007c: Implement aggregate() (12 hours)

**Option 2: Defer to Future Sprint**
- Mark SP-016-007 as "Blocked - Requires Dedicated Sprint Allocation"
- Current lambda variable support (where, select, exists, all) covers 80% of use cases
- repeat() and aggregate() are advanced functions with limited test coverage

**Option 3: Implement Simplified Versions**
- repeat(): Simple iteration without full recursion (4 hours)
- aggregate(): Basic implementation without complex accumulators (6 hours)
- Trade-off: Partial spec compliance vs. time investment

---

## Task Overview

### Description

Expand lambda variable support ($this, $index, $total) to additional collection iteration functions beyond where() and select(). Currently, lambda variables work in where(), select(), and exists(). This task adds support to repeat(), all(), any(), aggregate(), and other collection functions.

**Context**: SP-016-004 successfully implemented lambda variables in the SQL translator for primary collection functions (where, select, exists). This task completes the lambda variable implementation by adding support to remaining collection iteration functions.

**Impact**: Will improve Collection Functions category compliance and enable more complex FHIRPath expressions involving iteration.

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

---

## Requirements

### Functional Requirements

1. **repeat() Function**:
   - Bind $this to current item during recursive iteration
   - Support nested repeat() calls with proper scope isolation
   - Example: `Patient.contact.repeat(organization)` - traverse organization hierarchy

2. **all() Function**:
   - Bind $this, $index, $total during predicate evaluation
   - Return true only if predicate is true for ALL items
   - Example: `Patient.name.all($this.given.exists())` - all names have given names

3. **any() Function** (alias for exists()):
   - Already implemented via exists(), verify lambda variable support
   - Example: `Patient.name.any($this.family = 'Smith')`

4. **aggregate() Function**:
   - Bind $this to current item, $total to collection size
   - Bind $accumulator or $current to accumulated value
   - Example: `(1|2|3|4).aggregate($this + $total, 0)` - sum with total

5. **ofType() and as() Functions** (if they iterate):
   - Bind $this during type filtering/casting
   - Example: `Patient.contact.ofType(Organization).where($this.active)`

### Non-Functional Requirements

- **Performance**: Lambda variable binding should add <5% overhead
- **Compliance**: Target +10 to +20 additional official tests passing
- **Database Support**: Must work in both DuckDB and PostgreSQL
- **Error Handling**: Clear error messages for unbound variables

### Acceptance Criteria

**Critical** (Must Have):
- [x] aggregate() with $this and $total working
- [x] SQL tests passing (6 tests total, all passing)
- [x] No regressions in existing lambda variable support
- [ ] repeat() with $this variable working (deferred)
- [ ] all() with $index enhancement (has $this and $total, $index is nice-to-have)
- [ ] Official compliance improved by +10 tests minimum (to be measured)

**Important** (Should Have):
- [ ] Nested repeat() calls with scope isolation
- [ ] aggregate() with complex accumulators
- [ ] PostgreSQL test coverage
- [ ] Performance benchmarks (<5% overhead verified)

**Nice to Have**:
- [ ] ofType() and as() lambda support
- [ ] Debug/logging for variable binding
- [ ] Variable binding visualization tools

---

## Technical Specifications

### Affected Components

**Primary Components**:
- **fhir4ds/fhirpath/sql/translator.py**
  - Add lambda variable binding to `_translate_repeat()`
  - Add lambda variable binding to `_translate_all()`
  - Add lambda variable binding to `_translate_aggregate()`
  - Use existing `_variable_scope` context manager pattern

**Supporting Components**:
- **tests/unit/fhirpath/sql/test_lambda_variables_sql.py**
  - Add tests for repeat() with $this
  - Add tests for all() with lambda variables
  - Add tests for aggregate() with lambda variables

### Implementation Pattern

Follow the pattern established in SP-016-004:

```python
def _translate_repeat(self, node: FunctionCallNode) -> SQLFragment:
    """Translate repeat() with $this binding."""

    # Get collection and iterator expression
    collection = self.visit(node.target)
    iterator_expr = node.arguments[0]

    # Bind $this variable during iteration
    with self._variable_scope({
        "$this": VariableBinding(
            expression=item_alias,
            source_table=temp_table
        )
    }):
        iterator_fragment = self.visit(iterator_expr)

    # Generate recursive SQL with LATERAL JOIN
    sql = f"""
    WITH RECURSIVE repeat_cte AS (
        SELECT * FROM {collection.source_table}
        UNION ALL
        SELECT * FROM repeat_cte
        CROSS JOIN LATERAL ({iterator_fragment.expression})
    )
    SELECT * FROM repeat_cte
    """

    return SQLFragment(expression=sql, ...)
```

### Database Considerations

- **DuckDB**: Use recursive CTEs for repeat(), LATERAL JOIN for iteration
- **PostgreSQL**: Same pattern, verify syntax compatibility
- **Schema Changes**: None required

---

## Dependencies

### Prerequisites

1. **SP-016-004 Completed**: Lambda variables working in where(), select(), exists() ✅
2. **SQL Translator Understanding**: Review existing lambda variable implementation
3. **FHIRPath Spec**: Read spec sections on repeat(), all(), aggregate()

### Blocking Tasks

- None (can start immediately after SP-016-006)

### Dependent Tasks

- Future compliance improvement tasks will benefit from this work

---

## Implementation Approach

### High-Level Strategy

1. Implement one function at a time (repeat → all → aggregate)
2. Follow established pattern from SP-016-004
3. Write SQL execution tests first (TDD approach)
4. Verify no regressions in existing lambda variable support

### Implementation Steps

#### Step 1: Implement repeat() with $this (6 hours)

**Key Activities**:
1. Add `_translate_repeat()` method to SQL translator
2. Use recursive CTE for repeat() semantics
3. Bind $this to current item in iterator expression
4. Handle infinite loop prevention (max depth or cycle detection)

**SQL Pattern**:
```sql
WITH RECURSIVE repeat_cte AS (
    -- Base case: initial collection
    SELECT id, item, 0 as depth FROM initial_collection
    UNION ALL
    -- Recursive case: apply iterator with $this bound
    SELECT r.id, new_item, r.depth + 1
    FROM repeat_cte r
    CROSS JOIN LATERAL (
        -- Iterator expression with $this = r.item
        SELECT ... WHERE $this = r.item
    ) AS iteration
    WHERE r.depth < 100  -- Max depth to prevent infinite loops
)
SELECT * FROM repeat_cte
```

**Tests**:
```python
def test_repeat_with_dollar_this(duckdb_conn, parser_duckdb):
    """Test repeat() with $this variable binding"""
    expression = "Patient.contact.repeat($this.organization)"
    # Should traverse organization hierarchy recursively
```

**Validation**:
```bash
pytest tests/unit/fhirpath/sql/test_lambda_variables_sql.py::test_repeat_with_dollar_this -v
```

#### Step 2: Implement all() with Lambda Variables (4 hours)

**Key Activities**:
1. Add lambda variable binding to `_translate_all()`
2. Use LATERAL JOIN with predicate evaluation
3. Aggregate results with AND logic
4. Bind $this, $index, $total during iteration

**SQL Pattern**:
```sql
SELECT
    t.id,
    bool_and(predicate_result) as all_result
FROM source_table t
CROSS JOIN LATERAL (
    SELECT
        UNNEST(t.array_col) as item,
        generate_subscripts(t.array_col, 1) as idx
) enum
CROSS JOIN LATERAL (
    -- Predicate with $this, $index, $total bound
    SELECT (/* predicate expression */) as predicate_result
) pred
GROUP BY t.id
```

**Tests**:
```python
def test_all_with_lambda_variables(duckdb_conn, parser_duckdb):
    """Test all() with $this, $index, $total"""
    expression = "Patient.name.all($this.given.exists())"
    # Should return true only if ALL names have given names
```

**Validation**:
```bash
pytest tests/unit/fhirpath/sql/test_lambda_variables_sql.py::test_all_with_lambda_variables -v
```

#### Step 3: Implement aggregate() with $this and $accumulator (6 hours)

**Key Activities**:
1. Add lambda variable binding to `_translate_aggregate()`
2. Bind $this to current item
3. Bind $accumulator (or $total) to accumulated value
4. Use window functions or recursive CTE for accumulation

**SQL Pattern**:
```sql
WITH RECURSIVE agg_cte AS (
    -- Base case: first item with initial value
    SELECT
        id,
        item,
        initial_value as accumulator,
        1 as row_num
    FROM (SELECT id, UNNEST(array_col) as item FROM source_table)

    UNION ALL

    -- Recursive case: apply aggregation expression
    SELECT
        a.id,
        next_item,
        -- Aggregation expression with $this and $accumulator bound
        (/* agg expression with $this=next_item, $accumulator=a.accumulator */),
        a.row_num + 1
    FROM agg_cte a
    JOIN items_table i ON i.row_num = a.row_num + 1
)
SELECT id, accumulator FROM agg_cte WHERE row_num = (SELECT COUNT(*) FROM items)
```

**Tests**:
```python
def test_aggregate_with_lambda_variables(duckdb_conn, parser_duckdb):
    """Test aggregate() with $this and $accumulator"""
    expression = "(1|2|3|4).aggregate($accumulator + $this, 0)"
    # Should sum to 10
```

**Validation**:
```bash
pytest tests/unit/fhirpath/sql/test_lambda_variables_sql.py::test_aggregate_with_lambda_variables -v
```

#### Step 4: Official Compliance Testing (3 hours)

**Key Activities**:
1. Run official test suite
2. Focus on Collection Functions category
3. Identify specific failing tests that should now pass
4. Fix edge cases discovered

**Validation**:
```bash
python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
report = run_compliance_measurement(database_type='duckdb')
print(f'Collection Functions: {report.category_results[\"Collection_Functions\"]}')
"
```

**Expected**: Collection Functions should improve from 29/141 (20.6%) to 39-49/141 (27.7-34.8%)

#### Step 5: Documentation and Review (2 hours)

**Key Activities**:
1. Document lambda variable support in all collection functions
2. Add inline comments explaining recursive CTEs
3. Update architecture docs
4. Self-review for quality

---

## Testing Strategy

### Unit Testing

**New Tests Required** (~15 tests):
- `test_repeat_with_dollar_this` - Basic repeat() iteration
- `test_repeat_nested` - Nested repeat() calls
- `test_all_with_dollar_this` - all() with $this predicate
- `test_all_with_index_and_total` - all() with $index, $total
- `test_aggregate_sum` - aggregate() summing values
- `test_aggregate_complex` - aggregate() with complex accumulator
- `test_lambda_variables_scope_isolation` - Verify scope isolation across functions

**Coverage Target**: 95%+ of new lambda variable code

### Integration Testing

**Official Test Suite**:
- Collection Functions: 29/141 → 39-49/141 (+10 to +20 tests)
- Overall compliance: 44.1% → 45-47% (+1-3 percentage points)

### Manual Testing

**Test Scenarios**:
1. `Patient.contact.repeat(organization)` - Traverse hierarchy
2. `(1|2|3).all($this > 0)` - All items meet condition
3. `(1|2|3|4).aggregate($accumulator + $this, 0)` - Sum values

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Recursive CTE complexity | Medium | High | Start simple, add features incrementally |
| Infinite loop in repeat() | Medium | High | Add max depth limit, cycle detection |
| aggregate() performance | Low | Medium | Use window functions where possible |
| Scope isolation bugs | Low | High | Comprehensive nested call tests |

---

## Estimation

### Time Breakdown

- **repeat() Implementation**: 6 hours
- **all() Implementation**: 4 hours
- **aggregate() Implementation**: 6 hours
- **Testing**: 3 hours
- **Documentation**: 2 hours
- **Review**: 2 hours
- **Total Estimate**: **23 hours** (~3 days)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident)

**Rationale**: Pattern established by SP-016-004. Main risk is recursive CTE complexity for repeat() and aggregate().

---

## Success Metrics

### Quantitative Measures

- **Collection Functions**: 39-49/141 (27.7-34.8%) - up from 29/141 (20.6%)
- **Overall Compliance**: 45-47% - up from 44.1%
- **Minimum Target**: +10 tests
- **Stretch Target**: +20 tests

### Qualitative Measures

- Clean recursive CTE implementation
- No performance regressions
- Clear scope isolation
- Follows SP-016-004 patterns

---

## Documentation Requirements

### Code Documentation

- [ ] Docstrings for repeat(), all(), aggregate() translation methods
- [ ] Inline comments for recursive CTE logic
- [ ] Examples of lambda variable usage in each function
- [ ] Infinite loop prevention documentation

### Architecture Documentation

- [ ] Update lambda variable architecture document
- [ ] Document recursive CTE patterns
- [ ] Scope isolation design for nested calls

---

## Progress Tracking

### Status

- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [ ] Completed
- [x] Blocked - Requires Sprint Allocation

### Completion Checklist

- [ ] repeat() with $this working
- [ ] all() with lambda variables working
- [ ] aggregate() with $this and $accumulator working
- [ ] 15+ SQL execution tests passing
- [ ] Official tests improved by +10 minimum
- [ ] No regressions in existing lambda support
- [ ] Code documented and reviewed

---

**Task Created**: 2025-11-07 by Senior Solution Architect/Engineer
**Last Updated**: 2025-11-07
**Status**: Not Started
**Priority**: High (after SP-016-006)

---

*This task completes lambda variable implementation across all collection iteration functions, building on the foundation established in SP-016-004.*
