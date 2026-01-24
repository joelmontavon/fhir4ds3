# Task: SP-014-007 - Fix String Comparison Case Sensitivity

**Task ID**: SP-014-007
**Sprint**: Sprint 014 - Regression Analysis and Recovery
**Task Name**: Fix String Comparison Case Sensitivity for FHIRPath Compliance
**Assignee**: Junior Developer
**Created**: 2025-10-28
**Last Updated**: 2025-10-28

---

## Task Overview

### Description

Fix string comparison operations to be case-sensitive as required by the FHIRPath specification. Currently, string comparisons may be case-insensitive due to database collation defaults, causing FHIRPath tests to fail when comparing strings like `'ABC' = 'abc'` (which should return false but may return true).

**Context from SP-014-002**: String comparison operations (=, !=, <, >, <=, >=) are failing approximately 30 tests in the official FHIRPath R4 test suite. The FHIRPath specification requires case-sensitive string comparisons, but database default collations (especially in certain PostgreSQL configurations) may use case-insensitive comparison.

**Example Failing Test Cases**:
```fhirpath
'ABC' = 'abc'           // Should return false (case-sensitive)
'ABC' = 'ABC'           // Should return true
'hello' != 'HELLO'      // Should return true (different case)
'test  ' = 'test'       // Should return false (trailing space matters)
```

**Impact**: Implementing case-sensitive collation will improve compliance from 50.0% to approximately 52-55%, a gain of +30 tests, primarily in string comparison and string function categories.

### Category
- [ ] Feature Implementation
- [x] Bug Fix
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

**Rationale**: Medium-impact fix that addresses specification compliance without blocking other work. Affects 30 tests but does not cause system instability like list bounds errors.

---

## Requirements

### Functional Requirements

1. **Case-Sensitive String Comparison**: All string comparison operators (=, !=, <, >, <=, >=) must be case-sensitive
   - `'ABC' = 'abc'` must return false
   - `'ABC' = 'ABC'` must return true
   - `'hello' != 'HELLO'` must return true

2. **Consistent Behavior Across Dialects**: DuckDB and PostgreSQL must produce identical results for string comparisons
   - DuckDB: Use `COLLATE binary` for case-sensitive comparison
   - PostgreSQL: Use `COLLATE "C"` for case-sensitive comparison

3. **Apply to All String Comparison Operations**: Collation must be applied consistently across all comparison operators:
   - Equality: `=`
   - Inequality: `!=`, `~=`, `<>`
   - Ordering: `<`, `>`, `<=`, `>=`

4. **Preserve NULL Handling**: NULL comparison semantics must remain unchanged
   - `NULL = 'abc'` returns NULL (not false)
   - `NULL = NULL` returns NULL (not true)

### Non-Functional Requirements

- **Performance**: Collation specification should have minimal performance impact (< 5% overhead)
- **Compliance**: Must pass all 30 string comparison tests from official FHIRPath R4 test suite
- **Database Support**: Must work identically in both DuckDB and PostgreSQL
- **Error Handling**: Should handle edge cases: empty strings, NULL values, unicode characters

### Acceptance Criteria

- [ ] String comparisons are case-sensitive: `'ABC' = 'abc'` returns false
- [ ] String comparisons work correctly: `'ABC' = 'ABC'` returns true
- [ ] Inequality works correctly: `'hello' != 'HELLO'` returns true
- [ ] Whitespace is significant: `'test  ' = 'test'` returns false
- [ ] All comparison operators affected: =, !=, <, >, <=, >=
- [ ] Both DuckDB and PostgreSQL implementations working identically
- [ ] At least 25 of 30 string comparison tests passing (83% target)
- [ ] No regressions in other test categories
- [ ] Performance impact < 5% for string comparison operations

---

## Technical Specifications

### Affected Components

- **Database Dialects** (`fhir4ds/dialects/`): Add collation to comparison SQL generation
  - Base class: Define collation property interface
  - DuckDB dialect: Implement binary collation
  - PostgreSQL dialect: Implement C collation

- **SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): May need updates to pass type information to dialect for string-specific collation

### File Modifications

**Analysis Phase** (identify exact locations):
- **MODIFY**: `fhir4ds/dialects/base.py` - Update `generate_comparison()` method documentation to mention collation
- **MODIFY**: `fhir4ds/dialects/duckdb.py` - Add collation to string comparisons in `generate_comparison()`
- **MODIFY**: `fhir4ds/dialects/postgresql.py` - Add collation to string comparisons in `generate_comparison()`
- **CREATE**: `tests/unit/dialects/test_string_comparison_collation.py` - Unit tests for collation behavior
- **MODIFY**: `tests/unit/dialects/test_duckdb_dialect.py` - Add collation test cases
- **MODIFY**: `tests/unit/dialects/test_postgresql_dialect.py` - Add collation test cases

**Note**: Exact modification approach depends on whether type information is available at comparison generation time.

### Database Considerations

#### DuckDB Collation

**Binary Collation Syntax**:
```sql
-- Case-sensitive string comparison
SELECT 'ABC' = 'abc' COLLATE binary;  -- Returns false

-- Without collation (may be case-insensitive depending on settings)
SELECT 'ABC' = 'abc';  -- May return true

-- Applied to both operands (safest approach)
SELECT 'ABC' COLLATE binary = 'abc' COLLATE binary;  -- Returns false
```

**DuckDB Collation Behavior**:
- Default collation may be case-insensitive (locale-dependent)
- `COLLATE binary` performs byte-by-byte comparison (case-sensitive)
- Collation can be applied to one or both operands
- Unicode handling: Binary collation compares UTF-8 byte sequences

#### PostgreSQL Collation

**C Collation Syntax**:
```sql
-- Case-sensitive string comparison
SELECT 'ABC' = 'abc' COLLATE "C";  -- Returns false

-- Without collation (uses database default, may be case-insensitive)
SELECT 'ABC' = 'abc';  -- Depends on database collation setting

-- Applied to both operands (recommended)
SELECT 'ABC' COLLATE "C" = 'abc' COLLATE "C";  -- Returns false
```

**PostgreSQL Collation Behavior**:
- Default collation set at database creation time (often `en_US.UTF-8` which is case-insensitive)
- `COLLATE "C"` uses C locale (case-sensitive, byte-by-byte)
- `COLLATE "POSIX"` similar to "C" (alternative)
- Unicode handling: C collation compares byte sequences directly

#### Type Handling Considerations

**When is Type Information Available?**:
- Current `generate_comparison()` signature: `(left_expr: str, operator: str, right_expr: str) -> str`
- Type information may not be available at SQL generation time
- Need to investigate if translator knows operand types when calling `generate_comparison()`

**Potential Approaches**:

1. **Conservative Approach**: Apply collation to all comparisons
   - Pro: Simple, guaranteed case-sensitivity for strings
   - Con: May apply collation to non-string comparisons (minimal impact)

2. **Type-Aware Approach**: Apply collation only to string comparisons
   - Pro: Precise, only affects string operations
   - Con: Requires type information at comparison generation time

3. **Hybrid Approach**: Apply collation if type information available, otherwise apply universally
   - Pro: Best of both worlds
   - Con: More complex implementation

**Recommendation**: Start with **Conservative Approach** (apply to all comparisons), then optimize if performance issues arise.

---

## Dependencies

### Prerequisites

1. **SP-014-001 Complete**: Baseline validation confirms ~30 string comparison failures
2. **SP-014-002 Complete**: Root cause analysis identifies collation as likely issue
3. **Database Access**: Both DuckDB and PostgreSQL test environments available
4. **FHIRPath Specification**: Section 6.3 (String Operators) defines case-sensitive behavior

### Blocking Tasks

- None (this is an independent fix)

### Dependent Tasks

- **SP-014-006 (Type Conversion)**: String type conversions should maintain case-sensitivity
- **SP-014-008 (String Functions)**: String functions (contains, startsWith, endsWith) should be case-sensitive

---

## Implementation Approach

### High-Level Strategy

**Approach**: Modify dialect-level `generate_comparison()` methods to include database-specific collation clauses for case-sensitive string comparison. Use dialect properties to define collation strings, then apply them in comparison SQL generation.

**Key Decisions**:
1. **Dialect Property**: Add `string_collation` property to each dialect class
2. **Conservative Application**: Apply collation to all comparisons (simple, safe)
3. **Both Operands**: Apply collation to both left and right operands for consistency
4. **Incremental Testing**: Test in DuckDB first, then PostgreSQL

**Rationale**: Dialect property approach maintains thin dialect architecture (syntax-only differences) while providing clean, maintainable implementation.

### Implementation Steps

#### Step 1: Investigate Current String Comparison Behavior (1 hour)

**Objective**: Confirm that string comparisons are currently case-insensitive and understand the scope of the issue.

**Key Activities**:

1. **Test Current Behavior in DuckDB**:
   ```python
   import duckdb
   conn = duckdb.connect(':memory:')

   # Test case-insensitive behavior (current)
   result = conn.execute("SELECT 'ABC' = 'abc' as result").fetchone()
   print(f"DuckDB: 'ABC' = 'abc' → {result[0]}")  # Expect: True (case-insensitive)

   # Test with binary collation (desired)
   result = conn.execute("SELECT 'ABC' COLLATE binary = 'abc' COLLATE binary as result").fetchone()
   print(f"DuckDB with binary: 'ABC' = 'abc' → {result[0]}")  # Expect: False (case-sensitive)
   ```

2. **Test Current Behavior in PostgreSQL**:
   ```python
   import psycopg2
   conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
   cursor = conn.cursor()

   # Test case-insensitive behavior (current, depends on database collation)
   cursor.execute("SELECT 'ABC' = 'abc' as result")
   result = cursor.fetchone()
   print(f"PostgreSQL: 'ABC' = 'abc' → {result[0]}")  # May be True or False

   # Test with C collation (desired)
   cursor.execute("SELECT 'ABC' COLLATE \"C\" = 'abc' COLLATE \"C\" as result")
   result = cursor.fetchone()
   print(f"PostgreSQL with C: 'ABC' = 'abc' → {result[0]}")  # Expect: False (case-sensitive)
   ```

3. **Identify where comparisons are generated**:
   - Search for `generate_comparison` method calls in translator
   - Review current implementation in `fhir4ds/dialects/duckdb.py` and `postgresql.py`
   - Document current SQL output format

4. **Create investigation report**:
   ```markdown
   ## String Comparison Investigation Results

   ### DuckDB
   - Default behavior: [case-sensitive/insensitive]
   - With COLLATE binary: [case-sensitive/insensitive]
   - Current SQL output: (age = 18)

   ### PostgreSQL
   - Default behavior: [case-sensitive/insensitive]
   - Database collation: [en_US.UTF-8/C/other]
   - With COLLATE "C": [case-sensitive/insensitive]
   - Current SQL output: (age = 18)

   ### Translator Usage
   - Method: dialect.generate_comparison(left_expr, operator, right_expr)
   - Called from: translator.py line [X]
   - Type information available: [yes/no]
   ```

**Validation**:
- Documented current behavior for both databases
- Confirmed collation syntax works correctly
- Identified all locations where `generate_comparison()` is called
- Understanding of type information availability

**Expected Output**: Investigation report with clear understanding of current state and required changes

---

#### Step 2: Add Collation Property to Dialect Classes (30 minutes)

**Objective**: Define collation strings as dialect properties to maintain clean separation of database-specific syntax.

**Key Activities**:

1. **Add property to BaseDialect class** (`fhir4ds/dialects/base.py`):
   ```python
   class DatabaseDialect(ABC):
       """Abstract base class for database dialect implementations."""

       def __init__(self):
           """Initialize dialect with common properties."""
           self.name = self.__class__.__name__.replace('Dialect', '').upper()
           self.supports_jsonb = False
           self.supports_json_functions = True
           self.json_type = "JSON"
           self.cast_syntax = "::"
           self.quote_char = '"'
           # Add collation property for case-sensitive string comparison
           self.string_collation = ""  # Empty by default, subclasses override
   ```

2. **Set collation in DuckDBDialect** (`fhir4ds/dialects/duckdb.py`):
   ```python
   def __init__(self, connection: Optional[Any] = None, database: str = ":memory:"):
       """Initialize DuckDB dialect."""
       super().__init__()

       # DuckDB-specific settings
       self.name = "DUCKDB"
       self.supports_jsonb = False
       self.supports_json_functions = True
       self.json_type = "JSON"
       self.cast_syntax = "::"
       self.quote_char = '"'
       self.string_collation = "binary"  # DuckDB binary collation for case-sensitive comparison
   ```

3. **Set collation in PostgreSQLDialect** (`fhir4ds/dialects/postgresql.py`):
   ```python
   def __init__(self, connection_string: str, pool_size: int = 5, ...):
       """Initialize PostgreSQL dialect with connection pooling."""
       super().__init__()

       # PostgreSQL-specific settings
       self.name = "POSTGRESQL"
       self.supports_jsonb = True
       self.supports_json_functions = True
       self.json_type = "JSONB"
       self.cast_syntax = "::"
       self.quote_char = '"'
       self.string_collation = '"C"'  # PostgreSQL C collation for case-sensitive comparison (note quotes)
   ```

4. **Document the property**:
   - Add docstring explaining purpose of `string_collation` property
   - Note that empty string means no collation (uses database default)
   - Document that collation applies to string comparison operations

**Validation**:
- Property added to base class with empty default
- DuckDB dialect sets `string_collation = "binary"`
- PostgreSQL dialect sets `string_collation = '"C"'` (note the quotes)
- No syntax errors, dialects instantiate correctly

**Expected Output**: Dialect classes have collation property defined

---

#### Step 3: Update generate_comparison() Methods (1.5 hours)

**Objective**: Modify comparison SQL generation to include collation clauses for case-sensitive comparison.

**Key Activities**:

1. **Update DuckDB generate_comparison()** (`fhir4ds/dialects/duckdb.py`):

   **Current implementation (lines 925-939)**:
   ```python
   def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
       """Generate SQL comparison operation for DuckDB.

       Args:
           left_expr: Left operand SQL expression
           operator: Comparison operator (=, !=, <, >, <=, >=)
           right_expr: Right operand SQL expression

       Returns:
           DuckDB comparison expression

       Example:
           ('age', '>=', '18') → '(age >= 18)'
       """
       return f"({left_expr} {operator} {right_expr})"
   ```

   **New implementation with collation**:
   ```python
   def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
       """Generate SQL comparison operation for DuckDB with case-sensitive collation.

       Applies binary collation to ensure case-sensitive string comparisons
       as required by FHIRPath specification. The collation is applied to both
       operands for consistent behavior.

       Args:
           left_expr: Left operand SQL expression
           operator: Comparison operator (=, !=, <, >, <=, >=)
           right_expr: Right operand SQL expression

       Returns:
           DuckDB comparison expression with collation

       Example:
           ('name', '=', "'John'") → "(name COLLATE binary = 'John' COLLATE binary)"
           ('age', '>=', '18') → "(age COLLATE binary >= 18 COLLATE binary)"

       Note:
           FHIRPath requires case-sensitive string comparison. Binary collation
           ensures 'ABC' = 'abc' returns false as required by specification.
       """
       if self.string_collation:
           # Apply collation to both operands for case-sensitive comparison
           return f"({left_expr} COLLATE {self.string_collation} {operator} {right_expr} COLLATE {self.string_collation})"
       else:
           # No collation specified, use database default
           return f"({left_expr} {operator} {right_expr})"
   ```

2. **Update PostgreSQL generate_comparison()** (`fhir4ds/dialects/postgresql.py`):

   **Current implementation (lines 1143-1157)**:
   ```python
   def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
       """Generate SQL comparison operation for PostgreSQL.

       Args:
           left_expr: Left operand SQL expression
           operator: Comparison operator (=, !=, <, >, <=, >=)
           right_expr: Right operand SQL expression

       Returns:
           PostgreSQL comparison expression

       Example:
           ('age', '>=', '18') → '(age >= 18)'
       """
       return f"({left_expr} {operator} {right_expr})"
   ```

   **New implementation with collation**:
   ```python
   def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
       """Generate SQL comparison operation for PostgreSQL with case-sensitive collation.

       Applies C collation to ensure case-sensitive string comparisons as required
       by FHIRPath specification. The collation is applied to both operands for
       consistent behavior.

       Args:
           left_expr: Left operand SQL expression
           operator: Comparison operator (=, !=, <, >, <=, >=)
           right_expr: Right operand SQL expression

       Returns:
           PostgreSQL comparison expression with collation

       Example:
           ('name', '=', "'John'") → "(name COLLATE \"C\" = 'John' COLLATE \"C\")"
           ('age', '>=', '18') → "(age COLLATE \"C\" >= 18 COLLATE \"C\")"

       Note:
           FHIRPath requires case-sensitive string comparison. C collation ensures
           'ABC' = 'abc' returns false as required by specification. PostgreSQL
           default collation depends on database settings (often case-insensitive).
       """
       if self.string_collation:
           # Apply collation to both operands for case-sensitive comparison
           return f"({left_expr} COLLATE {self.string_collation} {operator} {right_expr} COLLATE {self.string_collation})"
       else:
           # No collation specified, use database default
           return f"({left_expr} {operator} {right_expr})"
   ```

3. **Handle edge cases**:
   - NULL values: Collation doesn't affect NULL handling (NULL = 'abc' still returns NULL)
   - Numeric comparisons: Collation is no-op for numbers (safe to apply universally)
   - Empty strings: Collation handles correctly ('' = '' returns true with any collation)
   - Unicode: Binary/C collation compares byte sequences (consistent behavior)

4. **Test SQL generation manually**:
   ```python
   from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

   # Test DuckDB
   duckdb_dialect = DuckDBDialect()
   sql = duckdb_dialect.generate_comparison("'ABC'", "=", "'abc'")
   print(f"DuckDB SQL: {sql}")
   # Expected: ('ABC' COLLATE binary = 'abc' COLLATE binary)

   # Test PostgreSQL
   pg_dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
   sql = pg_dialect.generate_comparison("'ABC'", "=", "'abc'")
   print(f"PostgreSQL SQL: {sql}")
   # Expected: ('ABC' COLLATE "C" = 'abc' COLLATE "C")
   ```

**Validation**:
- Both dialect methods updated with collation logic
- SQL includes COLLATE clause when `string_collation` is set
- Falls back to original behavior if collation is empty
- Manual SQL tests confirm correct syntax

**Expected Output**: Updated `generate_comparison()` methods with collation support

---

#### Step 4: Write Comprehensive Unit Tests (1.5 hours)

**Objective**: Create unit tests covering all string comparison scenarios with case-sensitivity validation.

**Test Categories**:

1. **Basic Case-Sensitive Comparison Tests**:

   **DuckDB Tests** (`tests/unit/dialects/test_duckdb_dialect.py`):
   ```python
   def test_string_comparison_case_sensitive_equal(self, dialect):
       """Test case-sensitive string equality returns false for different case."""
       sql = dialect.generate_comparison("'ABC'", "=", "'abc'")
       assert "COLLATE binary" in sql
       # Execute to verify behavior
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == False  # 'ABC' != 'abc' (case-sensitive)

   def test_string_comparison_case_sensitive_same_case(self, dialect):
       """Test case-sensitive string equality returns true for same case."""
       sql = dialect.generate_comparison("'ABC'", "=", "'ABC'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # 'ABC' = 'ABC'

   def test_string_comparison_case_sensitive_not_equal(self, dialect):
       """Test case-sensitive string inequality for different case."""
       sql = dialect.generate_comparison("'hello'", "!=", "'HELLO'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # 'hello' != 'HELLO' (case-sensitive)
   ```

   **PostgreSQL Tests** (`tests/unit/dialects/test_postgresql_dialect.py`):
   ```python
   def test_string_comparison_case_sensitive_equal(self, dialect):
       """Test case-sensitive string equality returns false for different case."""
       sql = dialect.generate_comparison("'ABC'", "=", "'abc'")
       assert "COLLATE" in sql
       assert '"C"' in sql
       # Execute to verify behavior
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == False  # 'ABC' != 'abc' (case-sensitive)

   def test_string_comparison_case_sensitive_same_case(self, dialect):
       """Test case-sensitive string equality returns true for same case."""
       sql = dialect.generate_comparison("'ABC'", "=", "'ABC'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # 'ABC' = 'ABC'

   def test_string_comparison_case_sensitive_not_equal(self, dialect):
       """Test case-sensitive string inequality for different case."""
       sql = dialect.generate_comparison("'hello'", "!=", "'HELLO'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # 'hello' != 'HELLO' (case-sensitive)
   ```

2. **All Comparison Operators**:
   ```python
   @pytest.mark.parametrize("operator,left,right,expected", [
       ("=", "'ABC'", "'abc'", False),   # Equality different case
       ("=", "'ABC'", "'ABC'", True),    # Equality same case
       ("!=", "'hello'", "'HELLO'", True),  # Inequality different case
       ("!=", "'hello'", "'hello'", False), # Inequality same case
       ("<", "'Apple'", "'apple'", True),   # Less than (A < a in binary/C collation)
       (">", "'apple'", "'Apple'", True),   # Greater than (a > A in binary/C collation)
       ("<=", "'ABC'", "'ABC'", True),      # Less or equal same case
       (">=", "'ABC'", "'ABC'", True),      # Greater or equal same case
   ])
   def test_string_comparison_operators_case_sensitive(self, dialect, operator, left, right, expected):
       """Test all comparison operators with case-sensitive behavior."""
       sql = dialect.generate_comparison(left, operator, right)
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == expected
   ```

3. **Edge Cases**:
   ```python
   def test_string_comparison_empty_strings(self, dialect):
       """Test comparison with empty strings."""
       sql = dialect.generate_comparison("''", "=", "''")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # Empty strings are equal

   def test_string_comparison_whitespace_significant(self, dialect):
       """Test that whitespace is significant in comparisons."""
       sql = dialect.generate_comparison("'test  '", "=", "'test'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == False  # Trailing space matters

   def test_string_comparison_null_handling(self, dialect):
       """Test NULL comparison behavior (should be unchanged)."""
       sql = dialect.generate_comparison("NULL", "=", "'abc'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] is None  # NULL = 'abc' returns NULL

   def test_string_comparison_unicode(self, dialect):
       """Test unicode character comparison."""
       sql = dialect.generate_comparison("'café'", "=", "'café'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True  # Unicode strings equal

       sql = dialect.generate_comparison("'café'", "=", "'CAFÉ'")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == False  # Unicode case-sensitive
   ```

4. **Numeric Comparison (Collation Should Be No-Op)**:
   ```python
   def test_numeric_comparison_unaffected(self, dialect):
       """Test that numeric comparisons work correctly with collation applied."""
       # Collation on numbers should be no-op or safely ignored
       sql = dialect.generate_comparison("42", "=", "42")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True

       sql = dialect.generate_comparison("42", "<", "100")
       result = dialect.execute_query(f"SELECT {sql} as result")
       assert result[0][0] == True
   ```

5. **Cross-Dialect Consistency Tests** (`tests/unit/dialects/test_string_comparison_collation.py`):
   ```python
   import pytest
   from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

   class TestStringComparisonCollationConsistency:
       """Test that DuckDB and PostgreSQL produce identical results for string comparison."""

       @pytest.fixture
       def duckdb_dialect(self):
           return DuckDBDialect()

       @pytest.fixture
       def postgresql_dialect(self):
           return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")

       @pytest.mark.parametrize("left,operator,right,expected", [
           ("'ABC'", "=", "'abc'", False),
           ("'ABC'", "=", "'ABC'", True),
           ("'hello'", "!=", "'HELLO'", True),
           ("'test'", "=", "'test'", True),
       ])
       def test_cross_dialect_consistency(self, duckdb_dialect, postgresql_dialect,
                                         left, operator, right, expected):
           """Verify DuckDB and PostgreSQL produce identical results."""
           # Generate and execute in DuckDB
           duckdb_sql = duckdb_dialect.generate_comparison(left, operator, right)
           duckdb_result = duckdb_dialect.execute_query(f"SELECT {duckdb_sql} as result")

           # Generate and execute in PostgreSQL
           pg_sql = postgresql_dialect.generate_comparison(left, operator, right)
           pg_result = postgresql_dialect.execute_query(f"SELECT {pg_sql} as result")

           # Results should match
           assert duckdb_result[0][0] == pg_result[0][0] == expected
   ```

**Validation**:
- All test categories implemented
- Tests pass for both DuckDB and PostgreSQL
- Cross-dialect consistency verified
- Edge cases handled correctly

**Expected Output**: Comprehensive test suite for string comparison collation

---

#### Step 5: Validate Against Official Test Suite (1 hour)

**Objective**: Run official FHIRPath R4 test suite and measure compliance improvement.

**Key Activities**:

1. **Run official test suite**:
   ```bash
   # Run full FHIRPath R4 official test suite
   PYTHONPATH=. python3 tests/integration/fhirpath/run_official_tests.py

   # Run specific string comparison tests if available
   PYTHONPATH=. python3 tests/integration/fhirpath/run_official_tests.py --filter=string
   ```

2. **Measure compliance improvement**:
   - **Baseline** (before fix): 50.0% (467/934 tests passing)
   - **Target** (after fix): 52-55% (+25-30 tests, 83-100% of string comparison tests)
   - **Optimistic** (all 30 tests): 53.2% (497/934 tests passing)

3. **Analyze results by category**:
   ```python
   # Expected improvements in these categories:
   # - string_operators: Significant improvement
   # - string_functions: Some improvement (if they use comparisons)
   # - comparison_operators: Moderate improvement
   ```

4. **Document failing tests**:
   ```markdown
   ## Official Test Suite Results

   ### Overall Results
   - Before: 467/934 passing (50.0%)
   - After: [X]/934 passing ([Y]%)
   - Improvement: +[Z] tests ([W]% increase)

   ### String Comparison Tests
   - Expected: 30 tests total
   - Passing: [X] tests ([Y]%)
   - Failing: [Z] tests

   ### Failing Test Examples
   1. Test ID: [X]
      Expression: [FHIRPath expression]
      Expected: [value]
      Actual: [value]
      Reason: [analysis]
   ```

5. **Verify no regressions**:
   - Compare pass counts for all categories before and after
   - Ensure no previously passing tests now fail
   - Investigate any unexpected failures

**Validation**:
- Compliance improves to at least 52% (conservative target)
- At least 25 of 30 string comparison tests passing (83%)
- No regressions in other test categories
- Failing tests documented with root cause analysis

**Expected Output**: Official test suite validation report with compliance metrics

---

#### Step 6: Performance Impact Assessment (30 minutes)

**Objective**: Measure performance impact of adding collation clauses to all comparisons.

**Key Activities**:

1. **Benchmark simple comparisons**:
   ```python
   import time
   from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

   def benchmark_comparisons(dialect, iterations=10000):
       """Benchmark comparison performance with collation."""
       start = time.time()
       for i in range(iterations):
           sql = dialect.generate_comparison(f"'{i}'", "=", f"'{i}'")
           dialect.execute_query(f"SELECT {sql}")
       elapsed = time.time() - start
       return elapsed

   # Test DuckDB
   duckdb_dialect = DuckDBDialect()
   duckdb_time = benchmark_comparisons(duckdb_dialect, 1000)
   print(f"DuckDB: {duckdb_time:.2f}s for 1000 comparisons")

   # Test PostgreSQL
   pg_dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
   pg_time = benchmark_comparisons(pg_dialect, 1000)
   print(f"PostgreSQL: {pg_time:.2f}s for 1000 comparisons")
   ```

2. **Compare with and without collation**:
   ```python
   # Temporarily disable collation to measure baseline
   duckdb_dialect.string_collation = ""  # Disable
   baseline_time = benchmark_comparisons(duckdb_dialect, 1000)

   duckdb_dialect.string_collation = "binary"  # Enable
   collation_time = benchmark_comparisons(duckdb_dialect, 1000)

   overhead = ((collation_time - baseline_time) / baseline_time) * 100
   print(f"Collation overhead: {overhead:.1f}%")
   ```

3. **Test complex queries**:
   ```sql
   -- Multiple comparisons in WHERE clause
   SELECT * FROM patient_resources
   WHERE json_extract_string(resource, '$.name[0].family') = 'Smith'
     AND json_extract_string(resource, '$.gender') = 'male'
     AND json_extract_string(resource, '$.address[0].city') = 'Boston'
   ```

4. **Document performance results**:
   ```markdown
   ## Performance Impact Assessment

   ### Simple Comparisons (1000 iterations)
   - DuckDB without collation: [X]s
   - DuckDB with collation: [Y]s
   - Overhead: [Z]% (acceptable if < 5%)

   - PostgreSQL without collation: [X]s
   - PostgreSQL with collation: [Y]s
   - Overhead: [Z]% (acceptable if < 5%)

   ### Complex Queries
   - Multi-comparison query: [X]s baseline, [Y]s with collation
   - Overhead: [Z]%

   ### Conclusion
   - Performance impact: [Negligible/Acceptable/Concerning]
   - Recommendation: [Proceed/Optimize/Reconsider]
   ```

**Validation**:
- Performance overhead < 5% for typical comparisons
- Complex queries not significantly impacted
- Both databases show similar performance characteristics

**Expected Output**: Performance impact report confirming acceptable overhead

---

### Alternative Approaches Considered

**Alternative 1: Type-Aware Collation Application**
- **Approach**: Only apply collation when operand types are known to be strings
- **Pros**: More precise, minimal impact on non-string comparisons
- **Cons**: Requires type information at SQL generation time, complex implementation
- **Rejected Because**: Type information may not be available; conservative approach is simpler and safer

**Alternative 2: Post-Processing with Case Folding**
- **Approach**: Implement case-sensitive comparison in Python post-processing
- **Pros**: No database changes required
- **Cons**: Violates CTE-first architecture, negates performance benefits of SQL
- **Rejected Because**: Against architectural principles (SQL-first approach)

**Alternative 3: Database-Level Collation Change**
- **Approach**: Change database default collation to case-sensitive
- **Pros**: Affects all string operations automatically
- **Cons**: Requires database recreation, impacts other queries, not portable
- **Rejected Because**: Too invasive, not compatible with existing databases

**Alternative 4: Operator-Level Collation**
- **Approach**: Add new case-sensitive comparison operators (e.g., `=~`)
- **Pros**: Preserves existing behavior, explicit case-sensitivity
- **Cons**: Not FHIRPath compliant (FHIRPath requires `=` to be case-sensitive)
- **Rejected Because**: Doesn't fix FHIRPath compliance, introduces non-standard operators

---

## Testing Strategy

### Unit Testing

**New Tests Required**:
- `tests/unit/dialects/test_string_comparison_collation.py`: Cross-dialect consistency tests
- Extended tests in `test_duckdb_dialect.py`: Collation-specific tests
- Extended tests in `test_postgresql_dialect.py`: Collation-specific tests

**Test Coverage**:
- Basic case-sensitive comparisons (=, !=, <, >, <=, >=)
- Edge cases (empty strings, whitespace, NULL, unicode)
- Numeric comparisons (collation should be no-op)
- Cross-dialect consistency
- Performance benchmarks

**Coverage Target**: >95% coverage of updated `generate_comparison()` methods

### Integration Testing

**Database Testing**:

1. **DuckDB**: Run full test suite with DuckDB backend
   ```bash
   PYTHONPATH=. python3 -m pytest tests/unit/dialects/test_duckdb_dialect.py -v
   PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k comparison
   ```

2. **PostgreSQL**: Run full test suite with PostgreSQL backend
   ```bash
   DATABASE_TYPE=postgresql PYTHONPATH=. python3 -m pytest tests/unit/dialects/test_postgresql_dialect.py -v
   DATABASE_TYPE=postgresql PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k comparison
   ```

3. **Consistency Check**: Verify identical results from both databases
   ```bash
   # Run comparison tests with detailed output
   PYTHONPATH=. python3 tests/unit/dialects/test_string_comparison_collation.py -v
   ```

**Component Integration**:
- Test string comparisons in FHIRPath expressions: `Patient.name.family = 'Smith'`
- Test comparisons in WHERE clauses: `Patient.where(gender = 'male')`
- Test comparisons in conditional expressions: `iif(status = 'active', 1, 0)`

**End-to-End Testing**:
- Execute complete FHIRPath queries with string comparisons
- Verify results match FHIRPath specification expectations
- Test with real FHIR data (Patient, Observation resources)

### Compliance Testing

**Official Test Suites**:
- Run FHIRPath R4 official test suite (all 934 tests)
- Focus on string comparison tests (~30 tests)
- Target: At least 25 passing (83% of string comparison tests)
- Stretch: 30 passing (100% of string comparison tests)

**Regression Testing**:
- Run full test suite before and after implementation
- Compare pass counts for each category
- Ensure no previously passing tests now fail
- Document any unexpected changes

**Performance Validation**:
- Benchmark string comparison operations
- Compare performance before and after collation
- Target: < 5% performance overhead
- Test with large datasets (1000+ comparisons)

### Manual Testing

**Test Scenarios**:

1. **Basic Case-Sensitive Comparison**:
   ```sql
   -- DuckDB
   SELECT 'ABC' COLLATE binary = 'abc' COLLATE binary;  -- Should return false

   -- PostgreSQL
   SELECT 'ABC' COLLATE "C" = 'abc' COLLATE "C";  -- Should return false
   ```

2. **Multiple Comparisons**:
   ```fhirpath
   Patient.where(name.family = 'Smith' and name.given.first() = 'John')
   ```

3. **Unicode Handling**:
   ```sql
   SELECT 'café' COLLATE binary = 'CAFÉ' COLLATE binary;  -- Should return false
   ```

4. **Empty and Whitespace**:
   ```sql
   SELECT '' COLLATE binary = '' COLLATE binary;  -- Should return true
   SELECT 'test  ' COLLATE binary = 'test' COLLATE binary;  -- Should return false
   ```

**Edge Cases**:
1. **NULL Operands**: `NULL = 'abc'` returns NULL (unchanged by collation)
2. **Numeric Strings**: `'123' = '123'` returns true (collation applies but doesn't affect numbers)
3. **Mixed Types**: Numeric comparison `42 = 42` works correctly (collation is no-op on numbers)
4. **Very Long Strings**: Test performance with strings > 1000 characters

**Error Conditions**:
1. **Invalid Collation**: Test graceful handling if collation property set incorrectly
2. **Database-Specific Failures**: Verify error messages are clear if database doesn't support collation

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Collation breaks numeric comparisons | Low | Medium | Conservative testing on numeric types; collation should be no-op |
| Performance degradation > 5% | Low | Medium | Benchmark early; optimize or revert if needed |
| PostgreSQL database uses incompatible collation | Medium | High | Test on target PostgreSQL instances; document collation requirements |
| Unicode handling differs between databases | Low | Medium | Test with unicode strings; document behavior differences |
| Type information not available at comparison time | Low | Low | Conservative approach applies collation universally (safe) |

### Implementation Challenges

1. **Database Collation Configuration**: PostgreSQL databases may have different default collations
   - **Approach**: Use explicit `COLLATE "C"` to override database default
   - **Testing**: Test on databases with various collation settings
   - **Documentation**: Document collation requirements for PostgreSQL setup

2. **Performance Impact on Large Queries**: Collation may slow down queries with many comparisons
   - **Approach**: Benchmark with realistic query loads (10+ comparisons)
   - **Fallback**: If impact > 5%, implement type-aware collation application

3. **Cross-Database Ordering Differences**: Binary and C collation may order strings differently
   - **Approach**: Test ordering operations (<, >, <=, >=) thoroughly
   - **Documentation**: Document any ordering behavior differences

### Contingency Plans

- **If performance impact > 5%**: Implement type-aware collation (only apply to string operands)
- **If PostgreSQL collation fails**: Fall back to alternative collations (POSIX, case-insensitive with LOWER())
- **If test improvement < 20 tests**: Investigate specific failing tests; may need additional fixes beyond collation
- **If cross-database inconsistency**: Document differences; may need dialect-specific handling for ordering operations

---

## Estimation

### Time Breakdown

- **Step 1: Investigate Current Behavior**: 1 hour
- **Step 2: Add Collation Property**: 0.5 hours
- **Step 3: Update generate_comparison() Methods**: 1.5 hours
- **Step 4: Write Unit Tests**: 1.5 hours
- **Step 5: Official Test Validation**: 1 hour
- **Step 6: Performance Assessment**: 0.5 hours
- **Total Estimate**: 6 hours

**Buffer for Junior Developer**: 7-8 hours (add 15% for learning and unexpected issues)

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Straightforward dialect modification with clear implementation path. Collation syntax is well-documented for both databases. Main uncertainty is exact number of tests that will pass (25-30 range).

### Factors Affecting Estimate

- **Database-Specific Issues**: If PostgreSQL collation configuration varies across instances: +1-2 hours
- **Type Information Availability**: If type-aware approach needed: +2-3 hours
- **Performance Optimization**: If collation overhead exceeds 5%: +2-4 hours
- **Unicode Edge Cases**: If unicode handling requires special logic: +1-2 hours

---

## Success Metrics

### Quantitative Measures

- **Test Pass Count**: At least +25 tests passing (conservative target: 83% of 30 string comparison tests)
- **Compliance Improvement**: 50.0% → 52-55% (optimistic: 53.2% if all 30 tests pass)
- **Performance Impact**: < 5% overhead for string comparison operations
- **Category Improvements**:
  - string_operators: +15-20 tests
  - comparison_operators: +5-10 tests
  - string_functions: +0-5 tests (if they use comparisons internally)
- **Code Coverage**: >95% coverage of updated `generate_comparison()` methods

### Qualitative Measures

- **Code Quality**: Collation implementation is clean, maintainable, follows dialect architecture principles
- **Architecture Alignment**: Solution maintains thin dialect architecture (syntax-only differences in dialects)
- **Maintainability**: Future developers can understand collation approach and modify if needed
- **Specification Compliance**: Implementation matches FHIRPath specification requirements exactly

### Compliance Impact

- **Specification Compliance**: Significant step toward FHIRPath string operation compliance
- **Test Suite Results**:
  - Baseline: 467/934 passing (50.0%)
  - Conservative Target: 492/934 passing (52.7%)
  - Realistic Target: 495/934 passing (53.0%)
  - Optimistic Target: 497/934 passing (53.2%)
- **Performance Impact**: Negligible (< 5% overhead for typical queries)

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments explaining collation property in dialect __init__ methods
- [x] Function/method documentation for updated `generate_comparison()` methods
- [x] Docstring examples showing SQL output with collation
- [x] Comment explaining FHIRPath specification requirement for case-sensitivity

### Architecture Documentation

- [ ] Update dialect architecture documentation with collation approach
- [ ] Document collation property pattern for future dialect additions
- [ ] Add note to FHIRPath compliance tracking about string comparison fix
- [ ] Document performance impact in architectural decision records

### User Documentation

- [ ] Update troubleshooting guide with collation-related issues
- [ ] Document PostgreSQL collation requirements for deployment
- [ ] Add FHIRPath string comparison behavior to user guide
- [ ] Include collation configuration in database setup documentation

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
| 2025-10-28 | Not Started | Task created and documented | None | Begin implementation in Week 2 Day 8 |

### Completion Checklist

- [ ] Collation property added to dialect classes
- [ ] DuckDB `generate_comparison()` updated with binary collation
- [ ] PostgreSQL `generate_comparison()` updated with C collation
- [ ] Unit tests written and passing for both dialects
- [ ] Cross-dialect consistency tests passing
- [ ] Official test suite validation complete (+25 tests minimum)
- [ ] Performance impact measured and acceptable (< 5%)
- [ ] No regressions in other test categories
- [ ] Code reviewed and approved
- [ ] Documentation completed

---

## Review and Sign-off

### Self-Review Checklist

- [ ] Implementation follows thin dialect architecture (syntax-only in dialects)
- [ ] All tests pass in both DuckDB and PostgreSQL
- [ ] Code follows established patterns (dialect property, method override)
- [ ] Case-sensitive comparison verified: `'ABC' = 'abc'` returns false
- [ ] No regressions introduced in other test categories
- [ ] Performance impact < 5% for string comparison operations
- [ ] Documentation is complete and accurate
- [ ] Cross-dialect behavior is consistent

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

- **Time Estimate**: 6-8 hours
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

**Task Created**: 2025-10-28 by Senior Solution Architect/Engineer (based on SP-014-002 analysis)
**Last Updated**: 2025-10-28
**Status**: Not Started - Ready for Week 2 Implementation

---

*This task implements a medium-impact fix to improve FHIRPath string comparison compliance. Successful completion will improve compliance by 2-5 percentage points (approximately 25-30 tests) and ensure case-sensitive string operations as required by FHIRPath specification.*
