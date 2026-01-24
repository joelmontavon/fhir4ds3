# Task: Collection Utility Functions (distinct, combine, iif)

**Task ID**: SP-015-010
**Sprint**: 016 (Week 1)
**Task Name**: Implement Collection Utility Functions
**Assignee**: Junior Developer
**Created**: 2025-11-02
**Last Updated**: 2025-11-04
**Estimated Effort**: 10-14 hours
**Priority**: Medium
**Status**: COMPLETED AND MERGED (2025-11-04)

---

## Task Overview

### Progress Updates

| Date | Status | Update | Blockers | Next Steps |
| 2025-11-03 | completed - pending review | Implemented distinct/combine/iif translation updates, added cross-dialect tests, and documented outcomes | None | Await senior architect review |
| 2025-11-04 | COMPLETED AND MERGED | Senior review approved with conditions. Merged to main branch. | None | Follow-up tasks documented in review |

### Description

Implement three essential collection utility functions that provide fundamental data manipulation capabilities for FHIRPath expressions: `distinct()` for removing duplicates, `combine()` for merging collections, and `iif()` for conditional expressions.

**Current State**:
- FHIRPath compliance: 403/934 (43.1%)
- Collection utilities: NOT IMPLEMENTED
- Expected gain: +10-15 tests

**Why This is Important**:
1. **Data Quality**: `distinct()` removes duplicate values from query results
2. **Collection Merging**: `combine()` merges multiple collections efficiently
3. **Conditional Logic**: `iif()` provides inline conditional expressions
4. **Common Patterns**: These functions are frequently used in FHIR queries
5. **Foundation**: Building blocks for more complex operations

**Background**: These three functions are part of the core FHIRPath specification and are commonly used in clinical quality measures, decision support rules, and data transformations.

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

#### 1. distinct() Function - Remove Duplicates
**FHIRPath Spec Reference**: Section 5.5.1

**Signature**: `collection.distinct() : collection`

**Behavior**:
- Returns collection with duplicate values removed
- Maintains order of first occurrence
- Works with all data types (strings, integers, booleans, complex objects)
- Empty collection returns empty collection
- Single-element collection returns unchanged
- Null values are treated as equal to other nulls (only one null kept)

**Examples**:
```fhirpath
(1 | 2 | 1 | 3).distinct()           // (1 | 2 | 3)
('a' | 'b' | 'a').distinct()         // ('a' | 'b')
(true | false | true).distinct()     // (true | false)
({}).distinct()                      // {}
(1).distinct()                       // (1)
(1 | {} | 2 | {}).distinct()         // (1 | {} | 2)  -- one null kept
Patient.name.family.distinct()       // Unique family names
Observation.code.coding.code.distinct()  // Unique codes
```

**SQL Strategy**:
- For simple types: Use SQL DISTINCT
- For collections: Use window functions or array functions
- Preserve order: Use MIN/MAX with ROW_NUMBER()

**Current Status**:
- ✅ Implemented 2025-11-03 – Translator uses JSON enumeration + ROW_NUMBER to deduplicate while preserving order; unit tests cover DuckDB/PostgreSQL SQL generation.

#### 2. combine() Function - Merge Collections
**FHIRPath Spec Reference**: Section 5.5.2

**Signature**: `collection1.combine(collection2) : collection`

**Behavior**:
- Combines two collections into one
- Maintains all elements (including duplicates)
- Order: all elements from collection1, then all from collection2
- Empty collection handling: `empty.combine(X)` = `X`, `X.combine(empty)` = `X`
- Equivalent to union operation that keeps duplicates

**Examples**:
```fhirpath
(1 | 2).combine(3 | 4)               // (1 | 2 | 3 | 4)
(1 | 2).combine(2 | 3)               // (1 | 2 | 2 | 3)  -- keeps duplicates
({}).combine(1 | 2)                  // (1 | 2)
(1 | 2).combine({})                  // (1 | 2)
('a').combine('b')                   // ('a' | 'b')
Patient.name.given.combine(Patient.name.family)  // All name parts
```

**SQL Strategy**:
- Use UNION ALL (not UNION) to keep duplicates
- For arrays: Use array concatenation functions

**Current Status**:
- ✅ Implemented 2025-11-03 – `_compose_union_expression` re-used for ordered concatenation and dialect-level array concatenation validated via unit tests.

#### 3. iif() Function - Inline Conditional
**FHIRPath Spec Reference**: Section 5.6.1

**Signature**: `iif(condition: boolean, true-result: collection, false-result: collection) : collection`

**Behavior**:
- Evaluates condition
- Returns true-result if condition is true
- Returns false-result if condition is false
- Returns empty collection if condition is empty
- Short-circuits: only evaluates the result branch that will be returned
- All three parameters are expressions (not just values)

**Examples**:
```fhirpath
iif(true, 'yes', 'no')               // 'yes'
iif(false, 'yes', 'no')              // 'no'
iif({}, 'yes', 'no')                 // {}
iif(1 > 2, 'greater', 'not')         // 'not'
iif(Patient.active, 'Active', 'Inactive')
iif(Observation.value > 120, 'High', 'Normal')
Patient.name.select(iif(use = 'official', family, given))
```

**SQL Strategy**:
- Use SQL CASE expression
- Handle short-circuiting via CASE structure
- Empty condition returns NULL

**Current Status**:
- ✅ Implemented 2025-11-03 – CASE translation now handles empty conditions, enforces boolean semantics, and applies dialect-specific JSON cardinality guards; regression tests added.

### Non-Functional Requirements

- **Performance**: <5ms translation overhead per function
- **Compliance**: 100% alignment with FHIRPath specification
- **Database Support**: Identical behavior in DuckDB and PostgreSQL
- **Error Handling**: Clear error messages for invalid operations
- **Memory Efficiency**: Handle large collections efficiently

### Acceptance Criteria

- [x] distinct() function fully implemented and tested
- [x] combine() function fully implemented and tested
- [x] iif() function fully implemented and tested
- [x] All unit tests passing (target: 35+ tests across functions)
- [ ] Official test suite improvement: +10-15 tests
- [x] Both DuckDB and PostgreSQL validated with identical results
- [x] Thin dialect architecture maintained
- [ ] Large collection handling verified (performance)
- [ ] Code review approved by Senior Architect

---

## Technical Specifications

### Affected Components

- **SQL Translator**: Collection utility function translation
- **Dialect Layer**: Database-specific collection operations
- **Both Databases**: DuckDB and PostgreSQL compatibility

### File Modifications

**Primary Files**:
- **`fhir4ds/fhirpath/sql/translator.py`**: Refined `_translate_iif()` to handle empty conditions, reuse dialect-specific array length checks, deduplicate dependencies, and tag metadata.
- **`fhir4ds/fhirpath/parser_core/semantic_validator.py`**: Registered `iif` as a recognised function to unblock parsing.
- **`fhir4ds/fhirpath/evaluator/functions.py`**: Added runtime `combine`/`iif` helpers and `_coerce_to_collection()` utility to maintain evaluator parity.

**Testing Files**:
- **`tests/unit/fhirpath/sql/test_translator_conditionals.py`**: New test suite covering iif() happy path, validation errors, and cross-dialect SQL generation.

**No Changes Expected**:
- **`fhir4ds/fhirpath/parser/`**: Functions already in grammar
- **`fhir4ds/fhirpath/sql/cte.py`**: No CTE changes needed

### Database Considerations

**DuckDB Collection Operations**:
```sql
-- distinct: DISTINCT keyword or list_unique()
SELECT DISTINCT value FROM collection;
SELECT list_unique(array_column) FROM table;

-- combine: list_concat() or UNION ALL
SELECT list_concat(array1, array2);
SELECT * FROM collection1 UNION ALL SELECT * FROM collection2;

-- iif: CASE expression
SELECT CASE WHEN condition THEN true_value ELSE false_value END;
```

**PostgreSQL Collection Operations**:
```sql
-- distinct: DISTINCT keyword or array_agg(DISTINCT)
SELECT DISTINCT value FROM collection;
SELECT array_agg(DISTINCT elem) FROM unnest(array_column) AS elem;

-- combine: array concatenation || or UNION ALL
SELECT array1 || array2;
SELECT * FROM collection1 UNION ALL SELECT * FROM collection2;

-- iif: CASE expression
SELECT CASE WHEN condition THEN true_value ELSE false_value END;
```

---

## Dependencies

### Prerequisites
1. **Set Operations**: Union/intersect/except foundations from SP-015-002
2. **DuckDB**: Local database functional
3. **PostgreSQL**: Connection available for validation
4. **Test Infrastructure**: Official test runner operational

### Blocking Tasks
- **NONE** - can start immediately

### Dependent Tasks
- **Sprint 016**: Future collection operations may build on these
- **Quality Measures**: CQL measures use these functions

---

## Implementation Approach

### High-Level Strategy

**Three-Phase Implementation**:

1. **Phase 1**: Implement distinct() function
   - Add translator method
   - Add dialect methods
   - Create comprehensive tests

2. **Phase 2**: Implement combine() function
   - Add translator method
   - Add dialect methods
   - Create comprehensive tests

3. **Phase 3**: Implement iif() function and validate
   - Add translator method
   - Create comprehensive tests
   - Run full integration validation

**Key Principles**:
- Leverage SQL native operations (DISTINCT, UNION ALL, CASE)
- Handle edge cases per FHIRPath specification
- Maintain thin dialect architecture
- Efficient handling of large collections

---

### Implementation Steps

#### Phase 1: Implement distinct() Function (3-4 hours)

**Step 1.1: Understand SQL DISTINCT Semantics (30 min)**

**SQL DISTINCT Behavior**:
- Removes duplicate rows from result set
- Operates on entire row (all columns)
- Maintains one occurrence of each unique value
- NULL values considered equal (one NULL kept)

**FHIRPath Requirements**:
- Remove duplicates from collection
- Maintain order of first occurrence
- Works on any type (primitives and complex objects)

**Validation**:
```sql
-- DuckDB
SELECT DISTINCT value FROM (VALUES (1), (2), (1), (3)) AS t(value);
-- Result: 1, 2, 3

SELECT DISTINCT value FROM (VALUES (1), (NULL), (2), (NULL)) AS t(value);
-- Result: 1, NULL, 2

-- PostgreSQL (same behavior)
SELECT DISTINCT value FROM (VALUES (1), (2), (1), (3)) AS t(value);
```

---

**Step 1.2: Implement _translate_distinct() Method (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 6000 (new method)

**Implementation**:
```python
def _translate_distinct(self, node: FunctionCallNode) -> SQLFragment:
    """Translate distinct() collection function.

    FHIRPath Spec: Section 5.5.1

    Signature: collection.distinct() : collection

    Returns collection with duplicate values removed, maintaining order
    of first occurrence.

    Args:
        node: FunctionCallNode for distinct()

    Returns:
        SQLFragment with distinct operation

    Example:
        (1 | 2 | 1 | 3).distinct() → (1 | 2 | 3)
    """

    # Get collection expression
    if hasattr(node, 'target') and node.target:
        # Method call: collection.distinct()
        collection_fragment = self.visit(node.target)
        collection_expr = collection_fragment.expression
        requires_unnest = collection_fragment.requires_unnest
    else:
        # Use current context
        collection_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )
        requires_unnest = True

    # Generate SQL for distinct operation
    sql = self.dialect.generate_distinct(
        collection_expr,
        requires_unnest
    )

    return SQLFragment(
        expression=sql,
        requires_unnest=False,  # Result is already a collection
        is_aggregate=False,
        metadata={'function': 'distinct'}
    )
```

---

**Step 1.3: Implement Dialect Methods for distinct() (1-1.5 hours)**

**DuckDB Dialect**:

**Location**: `fhir4ds/dialects/duckdb.py` ~line 900 (new method)

```python
def generate_distinct(self, collection_expr: str, requires_unnest: bool) -> str:
    """Generate SQL for distinct() in DuckDB.

    Args:
        collection_expr: SQL expression for collection
        requires_unnest: Whether collection needs to be unnested

    Returns:
        SQL expression with distinct values

    Example:
        For array: list_unique([1, 2, 1, 3]) → [1, 2, 3]
        For query: SELECT DISTINCT ... FROM ...
    """

    # Check if collection_expr is an array or a subquery
    if requires_unnest or self._is_array_expression(collection_expr):
        # For arrays, use list_unique() function
        return f"list_unique({collection_expr})"
    else:
        # For subqueries, wrap with DISTINCT
        # Assume collection_expr is a SELECT statement
        if collection_expr.strip().upper().startswith('SELECT'):
            # Inject DISTINCT into SELECT
            return collection_expr.replace('SELECT', 'SELECT DISTINCT', 1)
        else:
            # Wrap in subquery with DISTINCT
            return f"""
            (SELECT DISTINCT value
             FROM (SELECT unnest({collection_expr}) AS value))
            """.strip()

def _is_array_expression(self, expr: str) -> bool:
    """Check if expression represents an array."""
    # Simple heuristic: starts with [ or contains list_ functions
    return (expr.strip().startswith('[') or
            'list_' in expr or
            'array' in expr.lower())
```

**PostgreSQL Dialect**:

**Location**: `fhir4ds/dialects/postgresql.py` ~line 900 (new method)

```python
def generate_distinct(self, collection_expr: str, requires_unnest: bool) -> str:
    """Generate SQL for distinct() in PostgreSQL.

    Args:
        collection_expr: SQL expression for collection
        requires_unnest: Whether collection needs to be unnested

    Returns:
        SQL expression with distinct values
    """

    # For JSONB arrays, need to unnest, distinct, then aggregate back
    if requires_unnest or self._is_array_expression(collection_expr):
        return f"""
        (SELECT array_agg(DISTINCT elem ORDER BY elem)
         FROM unnest({collection_expr}) AS elem)
        """.strip()
    else:
        # For subqueries, wrap with DISTINCT
        if collection_expr.strip().upper().startswith('SELECT'):
            return collection_expr.replace('SELECT', 'SELECT DISTINCT', 1)
        else:
            return f"""
            (SELECT DISTINCT value
             FROM (SELECT unnest({collection_expr}) AS value) AS t)
            """.strip()

def _is_array_expression(self, expr: str) -> bool:
    """Check if expression represents an array."""
    return (expr.strip().startswith('ARRAY[') or
            'array_agg' in expr or
            'jsonb_array' in expr)
```

---

**Step 1.4: Create Tests for distinct() (30-45 min)**

**Location**: `tests/unit/fhirpath/sql/test_translator_set_operations.py`

**Add Tests**:
```python
class TestDistinctFunction:
    """Tests for distinct() function."""

    def test_distinct_integers(self, duckdb_dialect):
        """Test distinct() with integer collection."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # (1 | 2 | 1 | 3).distinct()
        # Expected: (1 | 2 | 3)

        parser = FHIRPathParser()
        ast = parser.parse("(1 | 2 | 1 | 3).distinct()").get_ast()
        fragments = translator.translate(ast)

        sql = fragments[-1].expression
        assert 'DISTINCT' in sql or 'list_unique' in sql

    def test_distinct_strings(self, duckdb_dialect):
        """Test distinct() with string collection."""
        # ('a' | 'b' | 'a').distinct() → ('a' | 'b')

    def test_distinct_empty_collection(self, duckdb_dialect):
        """Test distinct() with empty collection."""
        # ({}).distinct() → {}

    def test_distinct_single_element(self, duckdb_dialect):
        """Test distinct() with single element."""
        # (1).distinct() → (1)

    def test_distinct_with_nulls(self, duckdb_dialect):
        """Test distinct() with NULL values."""
        # (1 | {} | 2 | {}).distinct() → (1 | {} | 2)

    def test_distinct_preserves_order(self, duckdb_dialect):
        """Test distinct() maintains order of first occurrence."""
        # (3 | 1 | 2 | 1).distinct() → (3 | 1 | 2)

    def test_distinct_postgresql(self, postgresql_dialect):
        """Test distinct() on PostgreSQL."""
        # Same tests as DuckDB
```

---

**Phase 1 Validation (30 min)**:

```bash
# Run distinct tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_set_operations.py::TestDistinctFunction -v

# Manual testing
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator

parser = FHIRPathParser()
dialect = DuckDBDialect(':memory:')
translator = ASTToSQLTranslator(dialect, 'Patient')

# Test distinct
expr = '(1 | 2 | 1 | 3).distinct()'
ast = parser.parse(expr).get_ast()
fragments = translator.translate(ast)
print('SQL:', fragments[-1].expression)
"
```

---

#### Phase 2: Implement combine() Function (3-4 hours)

**Step 2.1: Understand SQL UNION ALL vs Array Concatenation (30 min)**

**SQL Strategies**:

1. **UNION ALL** (for subqueries):
```sql
-- Combines results from two queries, keeps duplicates
SELECT * FROM collection1
UNION ALL
SELECT * FROM collection2
```

2. **Array Concatenation** (for arrays):
```sql
-- DuckDB: list_concat()
SELECT list_concat([1, 2], [2, 3]);  -- [1, 2, 2, 3]

-- PostgreSQL: || operator
SELECT ARRAY[1, 2] || ARRAY[2, 3];   -- {1, 2, 2, 3}
```

---

**Step 2.2: Implement _translate_combine() Method (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 6100 (new method)

**Implementation**:
```python
def _translate_combine(self, node: FunctionCallNode) -> SQLFragment:
    """Translate combine() collection function.

    FHIRPath Spec: Section 5.5.2

    Signature: collection1.combine(collection2) : collection

    Combines two collections, maintaining all elements including duplicates.

    Args:
        node: FunctionCallNode for combine()

    Returns:
        SQLFragment with combined collection

    Example:
        (1 | 2).combine(3 | 4) → (1 | 2 | 3 | 4)
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("combine() requires exactly 1 argument (collection to combine)")

    # Get first collection
    if hasattr(node, 'target') and node.target:
        # Method call: collection1.combine(collection2)
        collection1_fragment = self.visit(node.target)
        collection1_expr = collection1_fragment.expression
    else:
        # Use current context
        collection1_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )

    # Get second collection
    collection2_fragment = self.visit(node.arguments[0])
    collection2_expr = collection2_fragment.expression

    # Generate SQL for combine operation
    sql = self.dialect.generate_array_concat(
        collection1_expr,
        collection2_expr
    )

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'function': 'combine'}
    )
```

---

**Step 2.3: Implement Dialect Methods for combine() (1-1.5 hours)**

**DuckDB Dialect**:

**Location**: `fhir4ds/dialects/duckdb.py` ~line 950 (new method)

```python
def generate_array_concat(self, array1_expr: str, array2_expr: str) -> str:
    """Generate SQL for array concatenation in DuckDB.

    Args:
        array1_expr: SQL expression for first array
        array2_expr: SQL expression for second array

    Returns:
        SQL expression with concatenated arrays

    Example:
        list_concat([1, 2], [3, 4]) → [1, 2, 3, 4]
    """
    return f"list_concat({array1_expr}, {array2_expr})"
```

**PostgreSQL Dialect**:

**Location**: `fhir4ds/dialects/postgresql.py` ~line 950 (new method)

```python
def generate_array_concat(self, array1_expr: str, array2_expr: str) -> str:
    """Generate SQL for array concatenation in PostgreSQL.

    Args:
        array1_expr: SQL expression for first array
        array2_expr: SQL expression for second array

    Returns:
        SQL expression with concatenated arrays

    Example:
        ARRAY[1, 2] || ARRAY[3, 4] → {1, 2, 3, 4}
    """
    return f"({array1_expr} || {array2_expr})"
```

---

**Step 2.4: Create Tests for combine() (30-45 min)**

**Location**: `tests/unit/fhirpath/sql/test_translator_set_operations.py`

**Add Tests**:
```python
class TestCombineFunction:
    """Tests for combine() function."""

    def test_combine_integers(self, duckdb_dialect):
        """Test combine() with integer collections."""
        # (1 | 2).combine(3 | 4) → (1 | 2 | 3 | 4)

    def test_combine_keeps_duplicates(self, duckdb_dialect):
        """Test combine() maintains duplicates."""
        # (1 | 2).combine(2 | 3) → (1 | 2 | 2 | 3)

    def test_combine_empty_first(self, duckdb_dialect):
        """Test combine() with empty first collection."""
        # ({}).combine(1 | 2) → (1 | 2)

    def test_combine_empty_second(self, duckdb_dialect):
        """Test combine() with empty second collection."""
        # (1 | 2).combine({}) → (1 | 2)

    def test_combine_both_empty(self, duckdb_dialect):
        """Test combine() with both collections empty."""
        # ({}).combine({}) → {}

    def test_combine_strings(self, duckdb_dialect):
        """Test combine() with string collections."""
        # ('a').combine('b') → ('a' | 'b')

    def test_combine_postgresql(self, postgresql_dialect):
        """Test combine() on PostgreSQL."""
```

---

**Phase 2 Validation (30 min)**:

```bash
# Run combine tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_set_operations.py::TestCombineFunction -v
```

---

#### Phase 3: Implement iif() Function (3-4 hours)

**Step 3.1: Understand CASE Expression Semantics (30 min)**

**SQL CASE Expression**:
```sql
-- Simple form
CASE
    WHEN condition THEN true_result
    ELSE false_result
END

-- With multiple conditions
CASE
    WHEN condition1 THEN result1
    WHEN condition2 THEN result2
    ELSE default_result
END

-- Handling NULLs
CASE
    WHEN condition IS NULL THEN NULL
    WHEN condition THEN true_result
    ELSE false_result
END
```

**FHIRPath iif() Semantics**:
- Three arguments: condition, true-result, false-result
- Short-circuits: only evaluates relevant branch
- Empty condition returns empty

---

**Step 3.2: Implement _translate_iif() Method (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 6200 (new method)

**Implementation**:
```python
def _translate_iif(self, node: FunctionCallNode) -> SQLFragment:
    """Translate iif() conditional function.

    FHIRPath Spec: Section 5.6.1

    Signature: iif(condition: boolean, true-result, false-result)

    Returns true-result if condition is true, false-result if false,
    empty if condition is empty.

    Args:
        node: FunctionCallNode for iif()

    Returns:
        SQLFragment with conditional result

    Example:
        iif(true, 'yes', 'no') → 'yes'
        iif(false, 'yes', 'no') → 'no'
        iif({}, 'yes', 'no') → {}
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 3:
        raise ValueError(
            "iif() requires exactly 3 arguments: "
            "condition, true-result, false-result"
        )

    # Translate condition
    condition_fragment = self.visit(node.arguments[0])
    condition_expr = condition_fragment.expression

    # Translate true-result
    true_fragment = self.visit(node.arguments[1])
    true_expr = true_fragment.expression

    # Translate false-result
    false_fragment = self.visit(node.arguments[2])
    false_expr = false_fragment.expression

    # Generate CASE expression
    # Handle empty condition (returns NULL/empty)
    sql = f"""
    CASE
        WHEN ({condition_expr}) IS NULL THEN NULL
        WHEN ({condition_expr}) THEN ({true_expr})
        ELSE ({false_expr})
    END
    """.strip()

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'function': 'iif'}
    )
```

---

**Step 3.3: Create Tests for iif() (1-1.5 hours)**

**Location**: `tests/unit/fhirpath/sql/test_translator_conditionals.py` (create new file)

**Implementation**:
```python
"""Unit tests for conditional function translation (iif).

Tests the iif() conditional function implementation for SQL generation.

Module: tests.unit.fhirpath.sql.test_translator_conditionals
Created: 2025-11-02
Task: SP-015-010
"""

import pytest
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for testing"""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for testing"""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestIifFunction:
    """Tests for iif() conditional function."""

    def test_iif_true_condition(self, duckdb_dialect):
        """Test iif() with true condition."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        parser = FHIRPathParser()

        # iif(true, 'yes', 'no')
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("iif(true, 'yes', 'no')").get_ast()
        )

        fragments = translator.translate(ast)
        sql = fragments[-1].expression

        assert 'CASE' in sql
        assert 'WHEN' in sql
        assert 'THEN' in sql
        assert "'yes'" in sql
        assert "'no'" in sql

    def test_iif_false_condition(self, duckdb_dialect):
        """Test iif() with false condition."""
        # iif(false, 'yes', 'no') → should evaluate to 'no'

    def test_iif_empty_condition(self, duckdb_dialect):
        """Test iif() with empty condition."""
        # iif({}, 'yes', 'no') → should return NULL/empty

    def test_iif_with_comparison(self, duckdb_dialect):
        """Test iif() with comparison condition."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        parser = FHIRPathParser()

        # iif(1 > 2, 'greater', 'not greater')
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("iif(1 > 2, 'greater', 'not greater')").get_ast()
        )

        fragments = translator.translate(ast)
        sql = fragments[-1].expression

        assert 'CASE' in sql
        assert '>' in sql

    def test_iif_with_field_access(self, duckdb_dialect):
        """Test iif() with field access in condition."""
        # iif(Patient.active, 'Active', 'Inactive')

    def test_iif_nested(self, duckdb_dialect):
        """Test nested iif() expressions."""
        # iif(x > 10, 'high', iif(x > 5, 'medium', 'low'))

    def test_iif_with_complex_results(self, duckdb_dialect):
        """Test iif() with complex result expressions."""
        # iif(Patient.active, Patient.name.family, Patient.name.given)

    def test_iif_short_circuit_behavior(self, duckdb_dialect):
        """Test that iif() short-circuits evaluation."""
        # Only the branch that will be returned should be evaluated
        # This is automatically handled by CASE expression

    def test_iif_postgresql(self, postgresql_dialect):
        """Test iif() on PostgreSQL."""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        parser = FHIRPathParser()

        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("iif(true, 'yes', 'no')").get_ast()
        )

        fragments = translator.translate(ast)
        sql = fragments[-1].expression

        assert 'CASE' in sql

    def test_iif_wrong_argument_count(self, duckdb_dialect):
        """Test iif() with wrong number of arguments."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        parser = FHIRPathParser()

        # This should raise ValueError during translation
        # (parser may catch it first)
        # iif(true, 'yes')  -- missing third argument


class TestIifIntegration:
    """Integration tests for iif() function."""

    def test_iif_in_select_expression(self, duckdb_dialect):
        """Test iif() used in select() expression."""
        # Patient.name.select(iif(use = 'official', family, given))

    def test_iif_in_where_filter(self, duckdb_dialect):
        """Test iif() used in where() filter."""
        # Patient.where(iif(active, id.exists(), false))

    def test_iif_with_aggregation(self, duckdb_dialect):
        """Test iif() combined with aggregation."""
        # Patient.name.select(iif(use = 'official', family, given)).distinct()
```

---

**Step 3.4: Update Function Translator Mapping (15 min)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 1071

**Update**:
```python
function_map = {
    # ... existing functions ...

    # Collection utilities
    'distinct': self._translate_distinct,
    'combine': self._translate_combine,

    # Conditional
    'iif': self._translate_iif,
}
```

---

**Phase 3 Validation (1 hour)**:

```bash
# Run all collection utility tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_set_operations.py -v
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_conditionals.py -v

# Run official test suite
PYTHONPATH=. python3 -m pytest tests/official/ -v

# Expected improvement: +10-15 tests
```

---

## Testing Strategy

### Unit Tests

**Test Coverage** (Target: 35+ tests):

1. **distinct() Tests** (12 tests):
   - Basic types (integers, strings, booleans)
   - Empty collection
   - Single element
   - With nulls
   - Order preservation
   - Large collections
   - Multi-database

2. **combine() Tests** (10 tests):
   - Basic combination
   - Keeps duplicates
   - Empty collections
   - String/integer types
   - Multi-database

3. **iif() Tests** (13 tests):
   - True condition
   - False condition
   - Empty condition
   - With comparisons
   - With field access
   - Nested iif
   - Complex results
   - Short-circuit behavior
   - Multi-database

### Integration Tests

**Create**: `tests/integration/fhirpath/test_collection_utilities_e2e.py`

```python
def test_distinct_with_real_data():
    """Test distinct() with real FHIR data."""
    # Load Patient resources with duplicate names
    # Query: Patient.name.family.distinct()
    # Verify unique family names returned

def test_combine_multiple_fields():
    """Test combine() merging multiple fields."""
    # Patient.name.given.combine(Patient.name.family)
    # Verify all name parts returned

def test_iif_conditional_logic():
    """Test iif() in real query."""
    # Patient.select(iif(active, 'Active: ' + name.family, 'Inactive'))
    # Verify conditional results
```

### Official Test Suite

**Expected Improvements**:
- Before: 403/934 (43.1%)
- After: 413-418/934 (44.2-44.7%)
- Gain: +10-15 tests

---

## Notes for Junior Developer

### Getting Started

1. **Read FHIRPath Spec Sections**:
   - Section 5.5 (Collection Functions)
   - Section 5.6 (Conditional Functions)

2. **Understand SQL Equivalents**:
   - distinct() → DISTINCT or list_unique()
   - combine() → UNION ALL or array concatenation
   - iif() → CASE expression

3. **Test Each Function Independently**:
   ```bash
   # Test distinct
   PYTHONPATH=. pytest -k "test_distinct" -v

   # Test combine
   PYTHONPATH=. pytest -k "test_combine" -v

   # Test iif
   PYTHONPATH=. pytest -k "test_iif" -v
   ```

### Common Pitfalls

1. **distinct() Order**:
   - ❌ Using DISTINCT without ORDER BY may not preserve order
   - ✅ Use window functions or MIN/MAX with ORDER BY

2. **combine() vs union()**:
   - ❌ Using UNION (removes duplicates)
   - ✅ Using UNION ALL (keeps duplicates)

3. **iif() Short-Circuiting**:
   - ✅ CASE expressions naturally short-circuit
   - ⚠️ All expressions are evaluated during planning, but only executed branch runs

4. **NULL Handling**:
   - ❌ Forgetting NULL checks
   - ✅ Explicit NULL handling in all functions

### Debugging Tips

1. **Test SQL Directly**:
   ```sql
   -- DuckDB distinct
   SELECT list_unique([1, 2, 1, 3]);  -- [1, 2, 3]

   -- PostgreSQL combine
   SELECT ARRAY[1, 2] || ARRAY[3, 4];  -- {1,2,3,4}

   -- CASE expression
   SELECT CASE WHEN true THEN 'yes' ELSE 'no' END;  -- 'yes'
   ```

2. **Print Generated SQL**:
   ```python
   fragments = translator.translate(ast)
   print("Generated SQL:", fragments[-1].expression)
   ```

### Architecture Alignment

**Thin Dialect Principle**:
- ✅ **Translator**: Function logic, validation
- ✅ **Dialect**: Database-specific syntax only
- ❌ **NOT in Dialect**: Business logic

### Success Metrics

**After Completing This Task**:
- [x] All 35+ unit tests passing
- [ ] Official test suite: +10-15 tests
- [x] All three functions working
- [x] Both databases validated
- [ ] Performance acceptable

---

## Risk Assessment

### Risks

1. **Performance with Large Collections**: distinct() on huge arrays
   - Mitigation: Test with large datasets, optimize SQL

2. **Order Preservation**: distinct() maintaining order
   - Mitigation: Use ORDER BY or ROW_NUMBER()

3. **iif() Short-Circuit**: Ensuring only one branch evaluates
   - Mitigation: CASE naturally short-circuits

---

## Definition of Done

- [x] All Phase 1-3 steps completed
- [x] distinct() implemented and tested
- [x] combine() implemented and tested
- [x] iif() implemented and tested
- [x] All unit tests passing (35+ tests)
- [ ] Integration tests passing
- [ ] Official test suite: +10-15 tests
- [x] Both databases validated
- [ ] Performance verified
- [ ] Code review approved
- [x] Documentation updated

---

## Approval

**Developer Sign-off**: _________________ Date: _________

**Code Review**: _________________ Date: _________

**Senior Architect Approval**: _________________ Date: _________

---

**End of Task Document SP-015-010**
