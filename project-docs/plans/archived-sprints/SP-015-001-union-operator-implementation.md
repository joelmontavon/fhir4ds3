# Task: Union Operator Implementation

**Task ID**: SP-015-001
**Sprint**: 015
**Task Name**: Implement Union (`|`) Operator for FHIRPath Collection Combination
**Assignee**: Junior Developer
**Created**: 2025-10-30
**Last Updated**: 2025-10-30

---

## Task Overview

### Description
Implement the FHIRPath union operator (`|`) which combines two collections into one, preserving all elements from both collections including duplicates. This is a **CRITICAL** infrastructure task that unlocks many collection function tests in the official FHIRPath test suite.

The union operator is currently recognized as an "unknown binary operator" by the parser and translator. This task will add full support for parsing, translating to SQL (UNION ALL), and testing the operator across both DuckDB and PostgreSQL databases.

**Why This is Critical**:
- **Blocks 15-20 tests** in the official suite that use `|` operator
- **Foundation for Week 2**: Set operations (distinct, intersect) build on union
- **Common in FHIRPath**: Used extensively in real-world FHIR queries
- **Architecture Test**: Validates thin dialect pattern for complex operators

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [x] Architecture Enhancement
- [ ] Performance Optimization
- [x] Testing
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

1. **Parser Recognition**: Parser must recognize `|` as a valid binary operator
   - Treat `|` as a binary operator like `+`, `-`, `*`, `/`
   - Generate OperatorNode with operator type "union"
   - Preserve operator precedence (lower than arithmetic, higher than comparison)

2. **SQL Translation**: Translator must convert union operations to SQL UNION ALL
   - Generate `SELECT * FROM (left_expr) UNION ALL SELECT * FROM (right_expr)`
   - Preserve all duplicates (UNION ALL, not UNION DISTINCT)
   - Handle nested unions: `(a | b) | c` → multiple UNION ALL clauses

3. **Dialect Support**: Both DuckDB and PostgreSQL must support union operator
   - Identical SQL generation in both dialects (UNION ALL is standard SQL)
   - Validate type compatibility between left and right collections
   - Handle empty collections gracefully (empty | collection = collection)

4. **Lambda Variable Integration**: Support `$this` variable in union expressions
   - Enable expressions like: `name.select(use | given)`
   - Prepare infrastructure for future lambda enhancements (Sprint 016)

### Non-Functional Requirements

- **Performance**: Union operator should have <2% overhead vs manual SELECT UNION
- **Compliance**: Must pass all union-related tests in official FHIRPath R4 suite
- **Database Support**: Identical behavior in DuckDB and PostgreSQL (±0 test difference)
- **Error Handling**: Clear error messages for type mismatches or invalid operands

### Acceptance Criteria

- [ ] Parser recognizes `|` operator and generates correct AST node
- [ ] Translator converts simple union (`1 | 2`) to SQL UNION ALL
- [ ] Translator handles nested unions (`(1 | 2) | 3`) correctly
- [ ] DuckDB execution returns correct results for all union expressions
- [ ] PostgreSQL execution returns identical results to DuckDB
- [ ] Official test suite shows +15-20 passing tests
- [ ] Unit test coverage >95% for union operator code paths
- [ ] No regressions in existing 373 passing tests
- [ ] Documentation includes union operator examples
- [ ] Code review approved by Senior Architect

---

## Technical Specifications

### Affected Components

- **Parser (fhir4ds/fhirpath/parser.py)**: Add `|` to operator recognition
- **AST Nodes (fhir4ds/fhirpath/ast/nodes.py)**: OperatorNode handles "union" type
- **Translator (fhir4ds/fhirpath/sql/translator.py)**: SQL generation for union
- **Dialects (fhir4ds/dialects/)**: Thin methods for UNION ALL syntax
- **Context (fhir4ds/fhirpath/sql/context.py)**: Variable binding for lambda support

### File Modifications

#### 1. Parser - Operator Recognition
**File**: `fhir4ds/fhirpath/parser.py` (or `parser_core/enhanced_parser.py`)
**Changes**: Modify
**Lines**: ~200-250 (binary operator definitions)

**What to add**:
```python
# In binary operator parsing section
BINARY_OPERATORS = {
    '+': 'add',
    '-': 'subtract',
    '*': 'multiply',
    '/': 'divide',
    'div': 'integerDivide',
    'mod': 'modulo',
    '|': 'union',  # ADD THIS LINE
    # ... other operators
}
```

**How to find it**:
1. Open `fhir4ds/fhirpath/parser.py`
2. Search for "BINARY_OPERATORS" or "def parse_binary_operator"
3. Add `'|': 'union'` to the operator mapping dictionary

#### 2. Translator - SQL Generation
**File**: `fhir4ds/fhirpath/sql/translator.py`
**Changes**: Modify
**Lines**: ~600-700 (visit_operator method)

**What to add**:
```python
def visit_operator(self, node: OperatorNode) -> SQLFragment:
    """Visit operator node and generate SQL."""
    operator = node.operator.lower()

    # ... existing operators ...

    elif operator == 'union' or operator == '|':
        return self._translate_union(node)

    # ... rest of operators ...

def _translate_union(self, node: OperatorNode) -> SQLFragment:
    """Translate union operator to SQL UNION ALL.

    The union operator (|) combines two collections, preserving all
    elements from both sides including duplicates.

    FHIRPath: (1 | 2 | 3)
    SQL: SELECT * FROM (SELECT 1) UNION ALL SELECT * FROM (SELECT 2)
         UNION ALL SELECT * FROM (SELECT 3)

    Args:
        node: OperatorNode with operator='union' or '|'

    Returns:
        SQLFragment containing UNION ALL expression
    """
    # Translate left and right operands
    left_fragment = self.visit(node.left)
    right_fragment = self.visit(node.right)

    # Generate UNION ALL SQL
    # Note: Using UNION ALL (not UNION) to preserve duplicates per FHIRPath spec
    union_sql = self.dialect.generate_union_all(
        left_fragment.expression,
        right_fragment.expression
    )

    return SQLFragment(
        expression=union_sql,
        data_type=left_fragment.data_type,  # Preserve left type
        is_collection=True,  # Union always returns collection
        dependencies=left_fragment.dependencies + right_fragment.dependencies
    )
```

#### 3. Dialect - UNION ALL Syntax
**File**: `fhir4ds/dialects/base.py`
**Changes**: Modify
**Lines**: ~400-500 (add new abstract method)

**What to add**:
```python
@abstractmethod
def generate_union_all(self, left_expr: str, right_expr: str) -> str:
    """Generate SQL UNION ALL expression.

    Combines two SELECT expressions using UNION ALL to preserve duplicates.

    Args:
        left_expr: Left SELECT expression
        right_expr: Right SELECT expression

    Returns:
        SQL UNION ALL expression

    Example:
        DuckDB/PostgreSQL (identical):
        >>> dialect.generate_union_all("SELECT 1", "SELECT 2")
        'SELECT * FROM (SELECT 1) UNION ALL SELECT * FROM (SELECT 2)'
    """
    pass
```

**Files**: `fhir4ds/dialects/duckdb.py` and `fhir4ds/dialects/postgresql.py`
**Changes**: Modify both files
**Lines**: Add implementation (identical for both dialects)

**What to add** (same in both files):
```python
def generate_union_all(self, left_expr: str, right_expr: str) -> str:
    """Generate UNION ALL expression (standard SQL - identical across dialects)."""
    return f"SELECT * FROM ({left_expr}) UNION ALL SELECT * FROM ({right_expr})"
```

**Why identical?**: UNION ALL is standard SQL-92, so DuckDB and PostgreSQL use the same syntax. This validates the thin dialect principle - only syntax differences belong in dialects.

### Database Considerations

#### DuckDB
- **UNION ALL Support**: Full support, standard SQL
- **Type Handling**: Automatic type coercion for compatible types
- **Performance**: Highly optimized for UNION ALL operations
- **Testing**: Run full test suite after implementation

#### PostgreSQL
- **UNION ALL Support**: Full support, standard SQL
- **Type Handling**: Stricter type checking than DuckDB
- **Performance**: Efficient UNION ALL execution
- **Testing**: Must match DuckDB results exactly (±0 tests)

#### Schema Changes
- **No schema changes required**: Union operator operates on query results, not stored data

---

## Dependencies

### Prerequisites
1. **SP-014-006-C**: PostgreSQL fix MUST be complete before starting
   - **Status**: Verify with Senior Architect before beginning
   - **Validation**: Run `pytest tests/unit/fhirpath/ -v --tb=short` - should pass
2. **Baseline Compliance**: Main branch at 373/934 tests (39.9%)
   - **Validation**: Run official test suite - should show 373 passing
3. **Both Databases Working**: DuckDB and PostgreSQL both functional
   - **DuckDB Test**: `PYTHONPATH=. python3 -c "import duckdb; print('OK')"`
   - **PostgreSQL Test**: `PYTHONPATH=. python3 -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@localhost:5432/postgres'); print('OK')"`

### Blocking Tasks
- **None**: This is Week 1 infrastructure - no dependencies

### Dependent Tasks
- **SP-015-002**: Set Operations (Week 2) - needs union operator
- **SP-015-003**: Navigation Functions (Week 3) - may use union operator
- **All collection tests**: ~20 tests blocked waiting for union operator

---

## Implementation Approach

### High-Level Strategy

**Stepwise Implementation** (based on CLAUDE.md principles):
1. **Parse**: Add `|` operator recognition to parser
2. **Translate**: Implement SQL UNION ALL generation
3. **Test Unit**: Verify basic functionality with unit tests
4. **Test Integration**: Run official test suite, measure gains
5. **Optimize**: Address any performance or edge case issues

**Key Decision**: Use UNION ALL (not UNION) to preserve duplicates per FHIRPath specification.

**Architecture Alignment**:
- ✅ Thin Dialects: UNION ALL syntax identical across databases
- ✅ SQL-First: Direct SQL generation, no Python post-processing
- ✅ Population-Scale: UNION ALL operates efficiently on large datasets

### Implementation Steps

#### Step 1: Parser Modification
**Estimated Time**: 1-2 hours
**Key Activities**:
1. Locate binary operator parsing logic in parser
2. Add `'|': 'union'` to operator mapping dictionary
3. Verify operator precedence (should be lower than arithmetic)
4. Run parser unit tests to verify no regressions

**Validation**:
```python
# Test in Python REPL
from fhir4ds.fhirpath.parser import FHIRPathParser
parser = FHIRPathParser()
result = parser.parse("1 | 2")
# Should NOT raise "unknown binary operator" error
assert result.is_valid
print(result.ast.operator)  # Should print 'union' or '|'
```

**Files to modify**:
- `fhir4ds/fhirpath/parser.py` OR `fhir4ds/fhirpath/parser_core/enhanced_parser.py`
- Look for the grammar definition or operator mapping

**Common pitfall**: If using ANTLR grammar, you may need to regenerate parser from `.g4` file. Check with Senior Architect if you see `.g4` files in `parser_core/`.

---

#### Step 2: Translator Implementation
**Estimated Time**: 2-3 hours
**Key Activities**:
1. Add `_translate_union()` method to translator
2. Update `visit_operator()` to handle 'union' case
3. Implement SQL fragment generation with UNION ALL
4. Handle nested unions (multiple UNION ALL clauses)
5. Add error handling for type mismatches

**Validation**:
```python
# Test translator in isolation
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect

dialect = DuckDBDialect()
translator = ASTToSQLTranslator(dialect, "Patient")

# Parse and translate simple union
parser = FHIRPathParser()
ast = parser.parse("1 | 2").ast
fragments = translator.translate(ast)

print(fragments[0].expression)
# Should contain "UNION ALL" somewhere in the output
assert "UNION ALL" in fragments[0].expression
```

**Files to modify**:
- `fhir4ds/fhirpath/sql/translator.py` (main implementation)

**Edge cases to handle**:
- Empty collections: `{} | {1, 2}` → `{1, 2}`
- Single element: `1 | 2` → `{1, 2}`
- Nested unions: `(1 | 2) | 3` → `{1, 2, 3}`
- Type mismatches: `1 | 'string'` → error or type coercion?

---

#### Step 3: Dialect Implementation
**Estimated Time**: 1 hour
**Key Activities**:
1. Add `generate_union_all()` abstract method to base dialect
2. Implement identical method in DuckDB dialect
3. Implement identical method in PostgreSQL dialect
4. Verify both dialects generate same SQL

**Validation**:
```python
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

duckdb = DuckDBDialect()
postgresql = PostgreSQLDialect()

# Both should generate identical SQL
left = "SELECT 1 AS value"
right = "SELECT 2 AS value"

duckdb_sql = duckdb.generate_union_all(left, right)
postgresql_sql = postgresql.generate_union_all(left, right)

assert duckdb_sql == postgresql_sql  # Must be identical
print(duckdb_sql)
```

**Files to modify**:
- `fhir4ds/dialects/base.py` (abstract method)
- `fhir4ds/dialects/duckdb.py` (concrete implementation)
- `fhir4ds/dialects/postgresql.py` (concrete implementation)

---

#### Step 4: Unit Testing
**Estimated Time**: 3-4 hours
**Key Activities**:
1. Create comprehensive unit tests for union operator
2. Test simple unions: `1 | 2`
3. Test nested unions: `(1 | 2) | 3`
4. Test with collections: `Patient.name | Patient.telecom`
5. Test error conditions: type mismatches, invalid operands
6. Test both databases: DuckDB and PostgreSQL

**Test File**: Create `tests/unit/fhirpath/sql/test_translator_union.py`

**Test Structure**:
```python
import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect


class TestUnionOperator:
    """Test suite for FHIRPath union (|) operator."""

    @pytest.fixture
    def parser(self):
        return FHIRPathParser()

    @pytest.fixture(params=["duckdb", "postgresql"])
    def translator(self, request):
        """Test with both database dialects."""
        if request.param == "duckdb":
            dialect = DuckDBDialect()
        else:
            dialect = PostgreSQLDialect()
        return ASTToSQLTranslator(dialect, "Patient")

    def test_simple_union(self, parser, translator):
        """Test simple union: 1 | 2."""
        ast = parser.parse("1 | 2").ast
        fragments = translator.translate(ast)

        assert len(fragments) > 0
        assert "UNION ALL" in fragments[0].expression
        assert fragments[0].is_collection is True

    def test_nested_union(self, parser, translator):
        """Test nested union: (1 | 2) | 3."""
        ast = parser.parse("(1 | 2) | 3").ast
        fragments = translator.translate(ast)

        # Should have 2 UNION ALL clauses
        union_count = fragments[0].expression.count("UNION ALL")
        assert union_count == 2

    def test_union_with_paths(self, parser, translator):
        """Test union with FHIR paths: Patient.name | Patient.telecom."""
        ast = parser.parse("Patient.name | Patient.telecom").ast
        fragments = translator.translate(ast)

        assert "UNION ALL" in fragments[0].expression
        assert "name" in fragments[0].expression
        assert "telecom" in fragments[0].expression

    def test_empty_collection_union(self, parser, translator):
        """Test union with empty collection: {} | {1, 2}."""
        # This may not be directly parseable - adjust based on actual syntax
        pass  # TODO: Implement based on parser capabilities

    @pytest.mark.parametrize("dialect_name", ["duckdb", "postgresql"])
    def test_dialect_parity(self, parser, dialect_name):
        """Verify identical SQL generation across dialects."""
        if dialect_name == "duckdb":
            dialect = DuckDBDialect()
        else:
            dialect = PostgreSQLDialect()

        translator = ASTToSQLTranslator(dialect, "Patient")
        ast = parser.parse("1 | 2").ast
        fragments = translator.translate(ast)

        # Store first dialect's SQL for comparison
        if not hasattr(self, '_reference_sql'):
            self._reference_sql = fragments[0].expression
        else:
            assert fragments[0].expression == self._reference_sql
```

**Validation**:
```bash
# Run unit tests
PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/sql/test_translator_union.py -v

# Should show all tests PASSED
# Target: >95% coverage for union operator code
```

---

#### Step 5: Integration Testing
**Estimated Time**: 1-2 hours
**Key Activities**:
1. Run official FHIRPath test suite on DuckDB
2. Run official FHIRPath test suite on PostgreSQL
3. Compare results - should be identical
4. Measure test count improvement (+15-20 tests expected)
5. Document any unexpected failures

**Validation**:
```bash
# Run official test suite - DuckDB
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
results = runner.run_official_tests()
print(f'DuckDB: {results.passed_tests}/{results.total_tests} ({results.compliance_percentage:.1f}%)')
"

# Run official test suite - PostgreSQL
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='postgresql')
results = runner.run_official_tests()
print(f'PostgreSQL: {results.passed_tests}/{results.total_tests} ({results.compliance_percentage:.1f}%)')
"

# Expected results:
# DuckDB: 388-393/934 (41.5-42.0%) - up from 373 (39.9%)
# PostgreSQL: Should match DuckDB ±2 tests
```

**Success Criteria**:
- DuckDB: +15-20 tests passing (total 388-393)
- PostgreSQL: Within ±2 tests of DuckDB
- No regressions in existing 373 passing tests

---

#### Step 6: Lambda Variable Support ($this)
**Estimated Time**: 2-3 hours
**Key Activities**:
1. Review context variable infrastructure
2. Ensure `$this` variable works in union expressions
3. Test: `name.select(use | given)` pattern
4. Document lambda variable limitations for Sprint 016

**Note**: This is preparatory work. Full lambda support (`$total`, `$index`) is deferred to Sprint 016.

**Validation**:
```python
# Test $this variable in union context
parser = FHIRPathParser()
ast = parser.parse("name.select(use | given)").ast

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# Should not raise "unbound variable" error
# Should generate valid SQL with UNION ALL
```

**Files to review**:
- `fhir4ds/fhirpath/sql/context.py` (variable binding)
- `fhir4ds/fhirpath/sql/translator.py` (variable resolution)

---

#### Step 7: Performance Validation
**Estimated Time**: 1 hour
**Key Activities**:
1. Benchmark union operator vs manual UNION ALL SQL
2. Test with large collections (1000+ elements)
3. Verify <2% overhead target
4. Profile slow operations if needed

**Validation**:
```python
import time
from tests.performance.fhirpath.translator_performance_benchmarking import benchmark_expression

# Benchmark union operator
results = benchmark_expression(
    expression="Patient.name | Patient.telecom",
    iterations=1000
)

print(f"Average time: {results['avg_time_ms']:.2f}ms")
print(f"Overhead vs baseline: {results['overhead_percent']:.1f}%")

# Target: <2% overhead
assert results['overhead_percent'] < 2.0
```

---

#### Step 8: Documentation
**Estimated Time**: 1 hour
**Key Activities**:
1. Add docstrings to all new methods
2. Create usage examples in docstrings
3. Update architecture docs if needed
4. Document any limitations or edge cases

**Documentation Checklist**:
- [ ] `_translate_union()` method has comprehensive docstring
- [ ] `generate_union_all()` dialect methods documented
- [ ] Usage examples in code comments
- [ ] Edge cases documented (empty collections, type coercion)
- [ ] Sprint 015 summary includes union operator section

---

### Alternative Approaches Considered

#### Alternative 1: Use UNION DISTINCT
**Rejected**: FHIRPath specification requires preserving duplicates. UNION ALL is correct.

#### Alternative 2: Implement in Python (collect results and merge)
**Rejected**: Violates SQL-first architecture principle. Union must happen in database for performance.

#### Alternative 3: Special-case common patterns (e.g., `name | telecom`)
**Rejected**: Over-optimization. Generic UNION ALL approach is simpler and more maintainable.

---

## Testing Strategy

### Unit Testing

**New Tests Required**:
1. **Parser Tests** (`tests/unit/fhirpath/test_parser.py`):
   - Test `|` operator recognition
   - Test operator precedence
   - Test nested unions parsing

2. **Translator Tests** (`tests/unit/fhirpath/sql/test_translator_union.py`):
   - Simple union: `1 | 2`
   - Nested union: `(1 | 2) | 3`
   - Path union: `Patient.name | Patient.telecom`
   - Type handling: compatible and incompatible types
   - Empty collections: `{} | {1, 2}`
   - Error conditions: invalid operands

3. **Dialect Tests** (`tests/unit/dialects/test_duckdb_dialect.py`, `test_postgresql_dialect.py`):
   - Verify `generate_union_all()` implementation
   - Confirm identical SQL across dialects
   - Test SQL syntax correctness

**Coverage Target**: >95% for all new code

### Integration Testing

**Database Testing**:
1. **DuckDB Environment**:
   ```bash
   PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/ -v --tb=short
   # All tests should pass
   ```

2. **PostgreSQL Environment**:
   ```bash
   # Export PostgreSQL connection string
   export FHIR_DB_URL="postgresql://postgres:postgres@localhost:5432/postgres"

   PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/ -v --tb=short
   # All tests should pass (identical to DuckDB)
   ```

### Compliance Testing

**Official Test Suites**:
1. **FHIRPath R4 Tests** (target: +15-20 tests):
   ```bash
   PYTHONPATH=. python3 tests/official/fhirpath/fhirpath_r4_test_runner.py
   # Expected: 388-393/934 passing (41.5-42.0%)
   # Baseline: 373/934 (39.9%)
   ```

2. **Regression Prevention**:
   - Verify existing 373 tests still pass
   - Document any unexpected failures
   - No degradation allowed

### Manual Testing

**Test Scenarios**:
1. **Simple Union**:
   ```python
   # Expression: 1 | 2
   # Expected Result: {1, 2}
   # SQL should contain: UNION ALL
   ```

2. **Path Union**:
   ```python
   # Expression: Patient.name | Patient.telecom
   # Expected Result: All names and telecoms
   # SQL should query both paths with UNION ALL
   ```

3. **Nested Union**:
   ```python
   # Expression: (1 | 2) | 3
   # Expected Result: {1, 2, 3}
   # SQL should have 2 UNION ALL clauses
   ```

4. **With Duplicates**:
   ```python
   # Expression: (1 | 2) | (2 | 3)
   # Expected Result: {1, 2, 2, 3} - duplicates preserved
   # UNION ALL preserves duplicates per spec
   ```

**Edge Cases**:
- Empty left: `{} | {1, 2}` → `{1, 2}`
- Empty right: `{1, 2} | {}` → `{1, 2}`
- Both empty: `{} | {}` → `{}`
- Type mismatch: `1 | 'string'` → error or coercion (document behavior)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Union breaks existing operators | Medium | High | Comprehensive regression testing; run full test suite after each change |
| Type coercion differs between DuckDB and PostgreSQL | Medium | Medium | Explicit type casting in SQL; test edge cases in both databases |
| Performance degradation with large collections | Low | Medium | Benchmark early; optimize UNION ALL query structure if needed |
| Parser grammar conflicts with `|` symbol | Low | High | Review grammar carefully; coordinate with Senior Architect if conflicts arise |

### Implementation Challenges

1. **Parser Grammar Complexity**:
   - **Challenge**: May be using ANTLR grammar (`.g4` file) that needs regeneration
   - **Approach**: Check for `.g4` files first; if found, coordinate with Senior Architect

2. **Type Compatibility**:
   - **Challenge**: Determining when types can be unioned (e.g., can integer union with string?)
   - **Approach**: Follow FHIRPath spec strictly; implement runtime type checks

3. **Nested Expression Complexity**:
   - **Challenge**: `((a | b) | c) | d` generates deeply nested SQL
   - **Approach**: Flatten UNION ALL chains where possible; test with real queries

### Contingency Plans

- **If parser modification is too complex**: Fallback to translator-only approach (treat `|` as post-parse transformation)
- **If timeline extends**: Implement basic union only, defer nested unions to Week 2
- **If database divergence**: Document differences, implement workarounds in thin dialect methods

---

## Estimation

### Time Breakdown
- **Analysis and Design**: 1 hour
- **Parser Implementation**: 1-2 hours
- **Translator Implementation**: 2-3 hours
- **Dialect Implementation**: 1 hour
- **Unit Testing**: 3-4 hours
- **Integration Testing**: 1-2 hours
- **Lambda Support**: 2-3 hours
- **Performance Validation**: 1 hour
- **Documentation**: 1 hour
- **Review and Refinement**: 1-2 hours
- **Total Estimate**: 14-20 hours

### Confidence Level
- [x] Medium (70-89% confident)
- [ ] High (90%+ confident in estimate)
- [ ] Low (<70% confident - needs further analysis)

**Reasoning**: Medium confidence because parser modification complexity is unknown. If ANTLR grammar regeneration is required, could add 2-4 hours.

### Factors Affecting Estimate
- **Parser complexity**: +2-4 hours if ANTLR regeneration needed
- **Type system complexity**: +1-2 hours if extensive type checking required
- **Edge case discovery**: +1-3 hours if unexpected behaviors found during testing
- **PostgreSQL compatibility**: +2-4 hours if database differences emerge

---

## Success Metrics

### Quantitative Measures
- **Test Improvement**: +15-20 tests in official FHIRPath suite (target: 388-393/934)
- **Unit Test Coverage**: >95% for union operator code paths
- **Database Parity**: DuckDB and PostgreSQL within ±2 tests
- **Performance**: <2% overhead vs manual UNION ALL SQL
- **Regression**: 0 previously passing tests now failing

### Qualitative Measures
- **Code Quality**: Follows thin dialect pattern, no business logic in dialects
- **Architecture Alignment**: SQL-first approach, population-scale capability maintained
- **Maintainability**: Clear, documented code with comprehensive tests

### Compliance Impact
- **Specification Compliance**: 39.9% → 41.5-42.0% (target)
- **Collection Functions**: 19.1% → ~25% (estimated)
- **Test Suite Results**: 373/934 → 388-393/934

---

## Documentation Requirements

### Code Documentation
- [x] Inline comments for union operator parsing logic
- [x] `_translate_union()` method comprehensive docstring
- [x] `generate_union_all()` dialect method docstrings
- [x] Example usage in docstrings (simple, nested, path unions)

### Architecture Documentation
- [ ] Architecture Decision Record (if significant design decision made)
- [x] Update translator architecture doc with union operator pattern
- [ ] Document type coercion rules for union operator
- [ ] Performance impact documentation (if >1% overhead)

### User Documentation
- [ ] Add union operator to FHIRPath expression examples
- [ ] Update API reference with union operator support
- [ ] Document known limitations (e.g., type restrictions)
- [ ] Add troubleshooting section for common union errors

---

## Progress Tracking

### Status
- [ ] Not Started
- [ ] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [ ] Completed
- [ ] Blocked

**Current Status**: completed - pending review

### Progress Updates

| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-10-30 | Not Started | Task document created, ready to begin | None | Review with Senior Architect, then start parser analysis |
| 2025-10-31 | In Testing | Parser, translator, and dialect updates for union operator implemented with unit coverage across DuckDB/PostgreSQL; architecture doc updated | Local PostgreSQL instance unavailable for performance suite (`psycopg2.OperationalError`) | Re-run full pytest (including performance suite) once PostgreSQL is accessible, then finalize task sign-off |
| 2025-10-31 | Completed - Pending Review | Dialect helpers refactored to syntax-only wrappers, translator now owns normalization/merge logic, architecture doc updated to describe new pattern | PostgreSQL connection still unavailable for comprehensive test pass | Obtain database access, rerun full pytest, then request senior review |
| 2025-10-31 | QA Validation | Added parser regression/integration tests exercising `|` token through adapter → translator pipeline; ensured parser metadata classifies union as operator | SQL-on-FHIR generator lacks unionAll handling causing compliance suite failures | Coordinate backlog item for SQL-on-FHIR unionAll support; rerun full compliance once available |

### Completion Checklist
- [x] Parser recognizes `|` operator
- [x] Translator generates UNION ALL SQL
- [x] Both dialects implement `generate_union_all()`
- [ ] Unit tests written and passing (>95% coverage)
- [ ] Integration tests passing (DuckDB + PostgreSQL)
- [ ] Official test suite shows +15-20 tests
- [ ] No regressions in existing 373 tests
- [ ] Code reviewed and approved
- [ ] Documentation completed
- [ ] Performance validated (<2% overhead)

---

## Review and Sign-off

### Self-Review Checklist
- [x] Implementation follows thin dialect pattern (no business logic in dialects)
- [ ] All tests pass in both DuckDB and PostgreSQL
- [x] Code follows FHIR4DS coding standards (PEP 8, type hints)
- [ ] Error handling is comprehensive with clear messages
- [ ] Performance impact is acceptable (<2% overhead)
- [ ] Documentation is complete and accurate
- [x] No hardcoded values introduced
- [ ] Lambda variable infrastructure prepared for Sprint 016

### Peer Review
**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [Pending]
**Review Status**: [Pending]
**Review Comments**: [To be completed during review]

### Final Approval
**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [Pending]
**Status**: [Pending Approval]
**Comments**: [To be completed upon approval]

---

## Post-Completion Analysis

### Actual vs. Estimated
- **Time Estimate**: 14-20 hours
- **Actual Time**: [To be recorded]
- **Variance**: [To be calculated]

### Lessons Learned
1. **[Lesson]**: [To be documented after completion]
2. **[Lesson]**: [To be documented after completion]

### Future Improvements
- **Process**: [Process improvement opportunities identified]
- **Technical**: [Technical approach refinements for similar tasks]
- **Estimation**: [Estimation accuracy improvements]

---

**Task Created**: 2025-10-30 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-30
**Status**: Ready to Start - Awaiting Junior Developer Kickoff

---

*This task is the critical foundation for Sprint 015. Successful completion unlocks all Week 2-4 collection function work. Take time to understand the parser and translator architecture before beginning implementation.*
