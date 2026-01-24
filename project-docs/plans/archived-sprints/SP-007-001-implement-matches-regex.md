# Task: Implement matches() Regex Function

**Task ID**: SP-007-001 | **Sprint**: 007 | **Estimate**: 8h | **Priority**: High
**Status**: ✅ MERGED TO MAIN
**Phase**: 1 - High-Value String Functions (Week 1)
**Completed**: 2025-10-05
**Merged**: 2025-10-05
**Review**: project-docs/plans/reviews/SP-007-001-review.md

---

## Overview

Implement the FHIRPath `matches()` function for regular expression pattern matching on strings. This is a critical string function that enables complex text validation and extraction patterns in healthcare queries.

## Context from Sprint 006

**Current String Function Coverage**: 16.3% (8/49 tests)
**Target**: 70%+ coverage (35+/49 tests)
**Gap**: ~27 tests, ~8 missing functions

**matches() is HIGH PRIORITY** because:
- Used in 6+ official tests
- Required for clinical text validation
- Foundation for replaceMatches() (SP-007-002)
- Common in real-world healthcare queries

## FHIRPath Specification

### matches() Function Semantics

**Signature**: `matches(regex: String) : Boolean`

**Description**: Returns true if the input string matches the regular expression pattern.

**Behavior**:
- Input: String to test
- Argument: Regular expression pattern (string)
- Returns: Boolean (true if matches, false if not)
- Empty input: Returns empty (null)
- Invalid regex: Returns empty (null) or error

**Type Rules**:
- Operates on String type only
- Takes exactly 1 argument (regex pattern)
- Returns Boolean type
- Null-safe: empty input → empty output

**Examples**:
```fhirpath
'hello world'.matches('hello.*')  → true
'hello'.matches('\\d+')           → false
'123'.matches('\\d+')             → true
name.family.matches('[A-Z][a-z]+') → true/false
```

## Technical Approach

### 1. Translator Implementation (Business Logic)

**File**: `fhir4ds/fhirpath/sql/translator.py`

```python
def _translate_matches(self, node: FunctionCallNode) -> SQLFragment:
    """Translate matches() function to SQL for regex matching.

    FHIRPath: string.matches(regex)
    SQL: regexp_matches(string, regex) [DuckDB]
          string ~ regex [PostgreSQL]

    Handles:
    - String validation against regex patterns
    - NULL handling (null input → null output)
    - Invalid regex handling (return null)
    """
    # Validate arguments
    if len(node.arguments) != 1:
        raise ValueError(
            f"matches() function requires exactly 1 argument (regex pattern), "
            f"got {len(node.arguments)}"
        )

    # Get target string expression
    # For chained expressions like "name.family.matches('[A-Z]+')"
    target_path = self.context.get_json_path()
    target_expr = self.dialect.extract_json_field(
        column=self.context.current_table,
        path=target_path
    )

    # Get regex pattern argument
    regex_pattern_node = node.arguments[0]
    regex_fragment = self.visit(regex_pattern_node)
    regex_pattern = regex_fragment.expression

    # Generate regex matching SQL using dialect
    matches_sql = self.dialect.generate_regex_match(
        target_expr,
        regex_pattern
    )

    logger.debug(f"Generated matches() SQL: {matches_sql}")

    return SQLFragment(
        expression=matches_sql,
        source_table=self.context.current_table,
        requires_unnest=False,
        is_aggregate=False,
        dependencies=[]
    )
```

### 2. Dialect Methods (Syntax Only)

**File**: `fhir4ds/dialects/base.py`

```python
@abstractmethod
def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
    """Generate regex matching SQL.

    Returns boolean expression indicating if string matches regex pattern.

    Args:
        string_expr: SQL expression evaluating to string
        regex_pattern: SQL expression for regex pattern (string literal or variable)

    Returns:
        SQL expression returning boolean

    Example:
        DuckDB: regexp_matches(string_expr, regex_pattern)
        PostgreSQL: (string_expr ~ regex_pattern)

    Note: This is a thin dialect method - contains ONLY syntax differences.
    """
    pass
```

**File**: `fhir4ds/dialects/duckdb.py`

```python
def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
    """Generate regex matching SQL for DuckDB.

    Uses DuckDB's regexp_matches() function.
    """
    return f"regexp_matches({string_expr}, {regex_pattern})"
```

**File**: `fhir4ds/dialects/postgresql.py`

```python
def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
    """Generate regex matching SQL for PostgreSQL.

    Uses PostgreSQL's ~ regex operator.
    """
    return f"({string_expr} ~ {regex_pattern})"
```

### 3. Edge Case Handling

**NULL String Handling**:
```sql
-- Both databases handle NULL consistently
regexp_matches(NULL, 'pattern') → NULL  -- DuckDB
(NULL ~ 'pattern') → NULL               -- PostgreSQL
```

**Invalid Regex Pattern**:
```python
# FHIRPath spec: Invalid regex returns empty (null)
# Database behavior: Invalid regex causes error
# Solution: Validate regex in translator OR wrap in TRY_CAST/exception handling

# Option 1: Pre-validation (if pattern is literal)
if regex_pattern is literal:
    try:
        re.compile(regex_pattern)
    except re.error:
        return SQLFragment(expression="NULL", ...)

# Option 2: Database-level handling (if pattern is dynamic)
# DuckDB: Use try_regexp_matches() if available
# PostgreSQL: Use regex validation function
```

**Empty Collection Handling**:
```python
# If target is collection, extract first element
if target_expr.context_mode == ContextMode.COLLECTION:
    first_elem = self.dialect.extract_first_element(target_expr.expression)
    matches_sql = self.dialect.generate_regex_match(first_elem, regex_pattern)
```

### 4. Database Regex Compatibility

**Research Required** (Day 1):
1. Test regex syntax compatibility between DuckDB and PostgreSQL
2. Identify any regex dialect differences (PCRE vs POSIX)
3. Document supported regex features
4. Plan fallback for unsupported patterns

**Known Differences**:
- DuckDB: Uses PCRE (Perl-compatible) regex
- PostgreSQL: Uses POSIX regex (more limited)
- May need regex translation layer for compatibility

## Implementation Steps

### Step 1: Research Database Regex Support (2h)

**Day 1 Morning**:
1. Research DuckDB regex syntax and limitations
2. Research PostgreSQL regex syntax and limitations
3. Test common regex patterns on both databases:
   - Character classes: `[A-Z]`, `[0-9]`, `\d`, `\w`
   - Quantifiers: `*`, `+`, `?`, `{n,m}`
   - Anchors: `^`, `$`
   - Groups: `()`, `(?:)`
   - Escaping: `\\.`, `\\d`, `\\s`
4. Document compatibility matrix
5. Decide on regex subset to support

### Step 2: Add matches() to Translator (3h)

**Day 1 Afternoon**:
1. Add `"matches"` to function dispatch in `visit_function_call()`
2. Implement `_translate_matches()` method
3. Add argument validation
4. Handle string extraction from context
5. Handle regex pattern extraction
6. Call dialect method for SQL generation
7. Add comprehensive error handling
8. Add debug logging

### Step 3: Implement Dialect Methods (2h)

**Day 2 Morning**:
1. Add `generate_regex_match()` to base dialect (abstract method)
2. Implement for DuckDB dialect
3. Implement for PostgreSQL dialect
4. Test regex syntax on both databases
5. Handle any compatibility issues
6. Document regex limitations

### Step 4: Unit Testing (1h)

**Day 2 Afternoon**:
1. Create `tests/unit/fhirpath/sql/test_translator_matches.py`
2. Test basic regex patterns
3. Test edge cases (null, empty, invalid regex)
4. Test multi-database consistency
5. Target: 90%+ coverage

## Acceptance Criteria

### Functional Requirements
- [x] matches(regex) translates to correct SQL
- [x] Regex patterns work on both DuckDB and PostgreSQL
- [x] NULL input returns NULL (not error)
- [x] Invalid regex handled gracefully
- [x] Empty collections handled correctly
- [x] String fields extracted properly

### Quality Requirements
- [x] Unit tests: 90%+ coverage (12+ tests)
- [x] Multi-database consistency: 100%
- [x] Integration with official tests: +6 tests minimum
- [x] Performance: <10ms translation
- [x] Architecture: 100% thin dialect compliance

### Documentation Requirements
- [x] Regex compatibility documented
- [x] Edge cases documented
- [x] Examples in docstrings
- [x] Limitations documented

## Testing Strategy

### Unit Tests

**File**: `tests/unit/fhirpath/sql/test_translator_matches.py`

```python
class TestMatchesBasicTranslation:
    """Test basic matches() translation"""

    def test_matches_simple_pattern_duckdb(self, duckdb_dialect):
        """Test: 'hello'.matches('hello.*')"""

    def test_matches_simple_pattern_postgresql(self, postgresql_dialect):
        """Test: 'hello'.matches('hello.*')"""

    def test_matches_digit_pattern(self, duckdb_dialect):
        """Test: '123'.matches('\\d+')"""

    def test_matches_field_pattern(self, duckdb_dialect):
        """Test: Patient.name.family.matches('[A-Z][a-z]+')"""

class TestMatchesEdgeCases:
    """Test matches() edge cases"""

    def test_matches_null_input(self):
        """Test: (null as String).matches('pattern') → null"""

    def test_matches_empty_collection(self):
        """Test: {}.matches('pattern') → {}"""

    def test_matches_invalid_regex(self):
        """Test: 'text'.matches('[') → null (invalid regex)"""

class TestMatchesMultiDatabase:
    """Test matches() cross-database consistency"""

    @pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
    def test_matches_consistency(self, dialect):
        """Test matches() produces same results in both databases"""

class TestMatchesErrorHandling:
    """Test matches() error cases"""

    def test_matches_no_arguments(self):
        """Test: 'text'.matches() should raise error"""

    def test_matches_multiple_arguments(self):
        """Test: 'text'.matches('a', 'b') should raise error"""
```

**Target**: 12-15 comprehensive tests, 90%+ coverage

### Integration Testing

**Validate Against Official Tests**:
```bash
# Re-run string function tests
pytest tests/integration/fhirpath/test_real_expressions_integration.py \
  -k "matches" -v

# Expected: +6 tests passing
# String functions: 8/49 → 14/49 (16.3% → 28.6%)
```

### Manual Database Testing

**DuckDB Validation**:
```sql
-- Test regex patterns in DuckDB
SELECT regexp_matches('hello', 'hello.*');  -- Expected: true
SELECT regexp_matches('123', '\d+');        -- Expected: true
SELECT regexp_matches('abc', '[A-Z]+');     -- Expected: false
```

**PostgreSQL Validation**:
```sql
-- Test regex patterns in PostgreSQL
SELECT 'hello' ~ 'hello.*';   -- Expected: true
SELECT '123' ~ '\d+';          -- Expected: true
SELECT 'abc' ~ '[A-Z]+';       -- Expected: false
```

## Dependencies

**Depends On**:
- None (can start immediately)

**Blocks**:
- SP-007-002 (replaceMatches - uses same regex engine)

**Related**:
- SP-007-003 (contains - simpler string function)
- SP-007-004 (startsWith/endsWith - can use regex or simpler methods)

## Success Metrics

- [x] matches() implementation complete
- [x] Regex compatibility documented
- [x] +6 tests to official coverage (minimum)
- [x] String functions: 16.3% → 28.6%+
- [x] Multi-database: 100% consistency
- [x] Performance: <10ms per match operation
- [x] Architecture: Thin dialect compliance

## Files to Modify

1. **fhir4ds/fhirpath/sql/translator.py** - Add _translate_matches()
2. **fhir4ds/dialects/base.py** - Add generate_regex_match() abstract method
3. **fhir4ds/dialects/duckdb.py** - Implement generate_regex_match()
4. **fhir4ds/dialects/postgresql.py** - Implement generate_regex_match()
5. **tests/unit/fhirpath/sql/test_translator_matches.py** (NEW) - Unit tests

## Architecture Alignment

- ✅ **Thin Dialect**: Regex logic in translator, syntax in dialects
- ✅ **Population-First**: Regex matching on entire columns
- ✅ **CTE-First Ready**: Returns proper SQLFragment
- ✅ **Multi-Database**: Tested on DuckDB and PostgreSQL

## Risk Assessment

**Risks**:
1. **Regex dialect differences** (Medium probability, High impact)
   - Mitigation: Research Day 1, document limitations

2. **Invalid regex handling** (Low probability, Medium impact)
   - Mitigation: Validate literals, handle runtime errors

3. **Performance with complex regex** (Low probability, Low impact)
   - Mitigation: Benchmark, document performance characteristics

## References

- **FHIRPath R4 Specification**: String functions - matches()
- **DuckDB Documentation**: regexp_matches() function
- **PostgreSQL Documentation**: POSIX regex operators
- **Regex Compatibility**: PCRE vs POSIX differences

---

**Created**: 2025-10-05
**Owner**: Mid-Level Developer
**Estimated Effort**: 8 hours
**Actual Effort**: TBD
