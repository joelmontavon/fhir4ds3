# Task: Implement FHIRPath Variable Binding ($this, $index, $total)

**Task ID**: SP-021-002-VARIABLE-BINDING-IMPLEMENTATION
**Sprint**: Current Sprint
**Task Name**: Implement FHIRPath Variable Binding for Lambda Expressions
**Assignee**: Junior Developer (AI Assistant)
**Created**: 2025-11-28
**Last Updated**: 2025-11-28
**Status**: COMPLETED - MERGED (2025-11-28)
**Review**: project-docs/plans/reviews/SP-021-002-review.md
**Priority**: **CRITICAL** (Highest compliance impact: +30-50 tests projected)

---

## Task Overview

### Description

Implement proper variable binding for FHIRPath lambda expression contexts, specifically `$this`, `$index`, and `$total` variables. These variables are essential for collection iteration functions like `where()`, `select()`, `all()`, `exists()`, and others.

Currently, these variables are not bound during expression evaluation, causing ~50 compliance test failures with errors like:
```
Error: "Unbound FHIRPath variable referenced: $this"
```

This task is identified as **Priority 1** from the SP-021-001 investigation findings, with the highest projected compliance improvement (+30-50 tests).

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [x] Critical (Blocker for compliance progress)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Variable binding is blocking ~50 compliance tests. This is the single highest-impact improvement opportunity identified in the SP-021-001 investigation.

---

## Requirements

### Functional Requirements

1. **$this Variable Binding**: Bind `$this` to the current item in collection iteration contexts
   - Example: `Patient.name.given.where($this.startsWith('J'))` should bind `$this` to each given name

2. **$index Variable Binding**: Bind `$index` to the zero-based index of the current item
   - Example: `(1 | 2 | 3).where($index > 0)` should bind `$index` to 0, 1, 2

3. **$total Variable Binding**: Bind `$total` to the total count of items in the collection
   - Example: `(1 | 2 | 3).where($index < $total - 1)` should bind `$total` to 3

4. **Nested Context Support**: Handle nested lambda expressions with proper variable scoping
   - Inner lambdas should shadow outer variables
   - Variables should be restored after exiting lambda context

5. **Multi-Database Support**: Ensure identical behavior in DuckDB and PostgreSQL

### Non-Functional Requirements

- **Performance**: Variable binding must not degrade population-scale query performance
- **Compliance**: Target +30-50 tests passing (from 404/934 to 434-454/934, 46-49% compliance)
- **Database Support**: Both DuckDB and PostgreSQL with identical results
- **Error Handling**: Clear error messages for unbound variable references

### Acceptance Criteria

- [ ] `$this` correctly bound in `where()`, `select()`, `all()`, `exists()` contexts
- [ ] `$index` correctly bound with zero-based indexing
- [ ] `$total` correctly bound to collection size
- [ ] Nested lambda expressions handle variable scoping correctly
- [ ] Compliance reaches 434+ tests passing (minimum +30 tests improvement)
- [ ] Zero regressions in existing tests (all 404 currently passing tests still pass)
- [ ] Both DuckDB and PostgreSQL produce identical results
- [ ] Unit tests validate all three variable types
- [ ] Integration tests validate nested contexts

---

## Technical Specifications

### Affected Components

- **ASTToSQLTranslator** (`fhir4ds/fhirpath/sql/translator.py`): Add variable binding logic for lambda contexts
- **SQLContext** (`fhir4ds/fhirpath/sql/context.py`): Extend to track lambda variable bindings
- **FunctionTranslation** (`fhir4ds/fhirpath/sql/translator.py`): Modify `where()`, `select()`, `all()`, `exists()` to bind variables
- **DatabaseDialect** (`fhir4ds/dialects/base.py`): May need SQL generation helpers for row numbering

### Implementation Approach

#### High-Level Strategy

1. **Extend SQLContext**: Add variable binding stack to track lambda contexts
2. **Modify Lambda Functions**: Update `where()`, `select()`, etc. to bind variables before evaluating predicates
3. **SQL Generation**: Generate SQL that provides row number and collection size for binding
4. **Variable Resolution**: Resolve `$this`, `$index`, `$total` to SQL expressions during translation

#### SQL Pattern Example

**FHIRPath Expression**:
```
Patient.name.given.where($this.startsWith('J'))
```

**Generated SQL** (conceptual):
```sql
WITH name_unnest AS (
  SELECT id,
         ROW_NUMBER() OVER (PARTITION BY id) - 1 AS row_index,
         COUNT(*) OVER (PARTITION BY id) AS total_count,
         given_value
  FROM patient_resources,
       LATERAL UNNEST(json_extract(resource, '$.name[*].given[*]')) AS given_value
)
SELECT id, given_value
FROM name_unnest
WHERE substring(given_value, 1, 1) = 'J'  -- $this bound to given_value
```

### File Modifications

- **`fhir4ds/fhirpath/sql/context.py`**: Add variable binding stack
- **`fhir4ds/fhirpath/sql/translator.py`**: Modify lambda function translations
- **`tests/unit/fhirpath/sql/test_translator_variables.py`**: Add comprehensive variable binding tests
- **`tests/integration/fhirpath/test_lambda_variables.py`**: New integration tests

---

## Dependencies

### Prerequisites

1. **SP-021-001**: ✅ Completed (primitive extraction for array contexts)
2. **CTE Infrastructure**: ✅ Available (supports complex query patterns)
3. **SQLContext**: ✅ Available (needs extension for variable binding)

### Blocking Tasks

None - all prerequisites are complete.

### Dependent Tasks

- **SP-021-003**: Operators (may benefit from variable binding for testing)
- **SP-021-005**: Type Functions (some type functions use lambda contexts)

---

## Implementation Steps

### Step 1: Extend SQLContext for Variable Binding (2-3 hours)

**File**: `fhir4ds/fhirpath/sql/context.py`

Add variable binding stack to track lambda contexts:

```python
@dataclass
class LambdaContext:
    """Represents a lambda expression context with variable bindings."""
    this_expr: Optional[str] = None
    index_expr: Optional[str] = None
    total_expr: Optional[str] = None

class SQLContext:
    def __init__(self, ...):
        # ... existing fields ...
        self.lambda_stack: List[LambdaContext] = []

    def push_lambda_context(self, this_expr: str, index_expr: str, total_expr: str):
        """Enter a lambda expression context with variable bindings."""
        self.lambda_stack.append(LambdaContext(this_expr, index_expr, total_expr))

    def pop_lambda_context(self):
        """Exit the current lambda context."""
        if self.lambda_stack:
            self.lambda_stack.pop()

    def get_variable_binding(self, var_name: str) -> Optional[str]:
        """Get SQL expression for a lambda variable ($this, $index, $total)."""
        if not self.lambda_stack:
            return None

        context = self.lambda_stack[-1]
        if var_name == "$this":
            return context.this_expr
        elif var_name == "$index":
            return context.index_expr
        elif var_name == "$total":
            return context.total_expr
        return None
```

### Step 2: Modify Variable Resolution (1-2 hours)

**File**: `fhir4ds/fhirpath/sql/translator.py`

Update variable resolution to check lambda context:

```python
def visit_variable(self, node: VariableNode) -> SQLFragment:
    """Translate variable reference (e.g., $this, $index, $total)."""
    var_name = node.name

    # Check lambda context first
    binding = self.context.get_variable_binding(var_name)
    if binding:
        return SQLFragment(
            expression=binding,
            dependencies=set(),
            context_mode=ContextMode.SCALAR
        )

    # Fall back to other variable types (parameters, etc.)
    # ... existing variable resolution logic ...
```

### Step 3: Modify Lambda Functions to Bind Variables (4-6 hours)

**File**: `fhir4ds/fhirpath/sql/translator.py`

Update `where()`, `select()`, `all()`, `exists()` to bind variables:

```python
def _translate_where_function(self, node: FunctionCallNode) -> SQLFragment:
    """Translate where() function with proper variable binding."""
    collection_expr, deps, _, _ = self._resolve_function_target(node)
    predicate_node = node.arguments[0]

    # Generate CTE with row numbering for variable binding
    cte_name = self._generate_cte_name("where_context")

    # SQL pattern:
    # WITH cte AS (
    #   SELECT
    #     ROW_NUMBER() OVER () - 1 AS row_index,
    #     COUNT(*) OVER () AS total_count,
    #     item
    #   FROM UNNEST(collection_expr) AS item
    # )

    item_alias = "item"
    index_expr = f"{cte_name}.row_index"
    total_expr = f"{cte_name}.total_count"
    this_expr = f"{cte_name}.{item_alias}"

    # Push lambda context
    self.context.push_lambda_context(this_expr, index_expr, total_expr)

    try:
        # Translate predicate with variables bound
        predicate_fragment = self.visit(predicate_node)

        # Generate WHERE clause SQL
        sql = f"""
        WITH {cte_name} AS (
          SELECT
            ROW_NUMBER() OVER () - 1 AS row_index,
            COUNT(*) OVER () AS total_count,
            {item_alias}
          FROM LATERAL UNNEST({collection_expr}) AS {item_alias}
        )
        SELECT {item_alias}
        FROM {cte_name}
        WHERE {predicate_fragment.expression}
        """

        return SQLFragment(expression=sql, dependencies=deps)
    finally:
        # Always pop lambda context
        self.context.pop_lambda_context()
```

### Step 4: Unit Tests (3-4 hours)

**File**: `tests/unit/fhirpath/sql/test_translator_variables.py`

```python
def test_this_variable_in_where(duckdb_dialect):
    """Test that $this is bound in where() context."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    ast = parse_fhirpath("name.given.where($this.startsWith('J'))")
    fragments = translator.translate(ast)

    sql = fragments[-1].expression
    # Should reference bound variable, not raise unbound error
    assert "$this" not in sql.lower()  # Should be replaced with SQL expression

def test_index_variable_in_where(duckdb_dialect):
    """Test that $index is bound in where() context."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    ast = parse_fhirpath("name.where($index > 0)")
    fragments = translator.translate(ast)

    sql = fragments[-1].expression
    assert "row_index" in sql.lower() or "row_number" in sql.lower()

def test_total_variable_in_where(duckdb_dialect):
    """Test that $total is bound in where() context."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    ast = parse_fhirpath("name.where($index < $total - 1)")
    fragments = translator.translate(ast)

    sql = fragments[-1].expression
    assert "total_count" in sql.lower() or "count(*)" in sql.lower()

def test_nested_lambda_variable_scoping(duckdb_dialect):
    """Test that nested lambdas properly scope variables."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
    # Nested where: outer $this should be shadowed by inner $this
    ast = parse_fhirpath("name.where($this.given.where($this.startsWith('J')).exists())")
    fragments = translator.translate(ast)

    # Should generate valid SQL with proper scoping
    assert len(fragments) > 0
```

### Step 5: Integration Tests (2-3 hours)

**File**: `tests/integration/fhirpath/test_lambda_variables.py`

Create integration tests with real data:

```python
def test_where_this_filters_correctly(test_db_connection):
    """Test that where($this...) filters collection correctly."""
    patient = {
        "resourceType": "Patient",
        "name": [{
            "given": ["John", "Jane", "Bob"]
        }]
    }

    evaluator = FHIRPathEvaluator(test_db_connection)
    result = evaluator.evaluate("name.given.where($this.startsWith('J'))", patient)

    assert result == ["John", "Jane"]

def test_where_index_filters_by_position(test_db_connection):
    """Test that where($index...) filters by position."""
    patient = {
        "resourceType": "Patient",
        "name": [
            {"given": ["First"]},
            {"given": ["Second"]},
            {"given": ["Third"]}
        ]
    }

    evaluator = FHIRPathEvaluator(test_db_connection)
    result = evaluator.evaluate("name.where($index > 0)", patient)

    # Should return all but first name
    assert len(result) == 2
```

### Step 6: Compliance Testing (2-3 hours)

Run compliance tests and validate improvement:

```bash
PYTHONPATH=. DB_TYPE=duckdb python3 -c "
from tests.compliance.fhirpath.test_runner import measure_compliance
report = measure_compliance(database_type='duckdb')
print(f'Overall: {report.total_passing}/{report.total_tests} ({report.pass_rate:.1f}%)')
"
```

**Expected Results**:
- **Before SP-021-002**: 404/934 (43.3%)
- **After SP-021-002**: 434-454/934 (46-49%)
- **Improvement**: +30-50 tests

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SQL row numbering differs across databases | Medium | Medium | Test both DuckDB and PostgreSQL extensively; use dialect methods |
| Nested lambda complexity | High | High | Implement incrementally; test single-level first, then nested |
| Variable scoping errors | Medium | High | Comprehensive unit tests for scoping edge cases |
| Performance degradation with ROW_NUMBER | Low | Medium | Benchmark population-scale queries; optimize if needed |

### Implementation Challenges

1. **SQL Generation Complexity**: Generating CTEs with row numbering and proper variable references
   - **Approach**: Use existing CTE infrastructure; add helpers for row numbering patterns

2. **Variable Scoping**: Correctly handling nested lambda contexts with variable shadowing
   - **Approach**: Stack-based context management; pop contexts in finally blocks

3. **Multi-Function Support**: Applying to all lambda functions (`where`, `select`, `all`, `exists`, etc.)
   - **Approach**: Create reusable helper for lambda context setup; apply across functions

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 1 hour (investigation already complete)
- **SQLContext Extension**: 2-3 hours
- **Variable Resolution**: 1-2 hours
- **Lambda Function Modifications**: 4-6 hours
- **Unit Tests**: 3-4 hours
- **Integration Tests**: 2-3 hours
- **Compliance Testing**: 2-3 hours
- **Documentation**: 1-2 hours
- **Review and Refinement**: 2 hours
- **Total Estimate**: 18-26 hours

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Variable binding is well-understood in FHIRPath spec, but SQL generation complexity and multi-database testing add uncertainty. Stack-based context management is straightforward, but nested lambda testing may reveal edge cases.

---

## Success Metrics

### Quantitative Measures

- **Compliance Improvement**: 434+/934 tests passing (46%+ compliance)
- **Test Increase**: +30 to +50 additional passing tests
- **Zero Regressions**: All 404 currently passing tests still pass
- **Code Coverage**: 100% of new code paths covered by tests

### Qualitative Measures

- **Code Quality**: Clean, maintainable variable binding infrastructure
- **Architecture Alignment**: Stack-based context management follows best practices
- **Maintainability**: Easy to extend for additional lambda variables if needed

---

## References

- **Investigation Findings**: `work/SP-021-001-INVESTIGATION-FINDINGS.md`
- **Senior Review**: `project-docs/plans/reviews/SP-021-001-review.md`
- **FHIRPath Specification**: Variables in lambda expressions (Section 5.2)
- **Architecture Guide**: `CLAUDE.md` (Population Analytics, CTE-First Design)
- **Coding Standards**: `project-docs/process/coding-standards.md`

---

**Task Created**: 2025-11-28
**Priority**: CRITICAL (Highest compliance impact)
**Estimated Impact**: +30-50 tests (46-49% compliance)
**Predecessor**: SP-021-001 (completed)

---

*This task addresses the #1 priority issue identified in SP-021-001 investigation, with the highest projected compliance improvement of all identified opportunities.*
