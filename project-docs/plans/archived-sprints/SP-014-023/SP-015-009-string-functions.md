# Task: String Manipulation Functions

**Task ID**: SP-015-009
**Sprint**: 015 (Week 4) or 016 (Week 1)
**Task Name**: Implement String Manipulation Functions
**Assignee**: Junior Developer
**Created**: 2025-11-02
**Last Updated**: 2025-11-04
**Estimated Effort**: 12-16 hours
**Priority**: Medium-High

**Current Status**: ✅ completed - reviewed and merged

---

## Task Overview

### Description

Implement comprehensive string manipulation functions that are currently missing or incomplete in the FHIRPath translator. These functions are essential for text processing, data extraction, and string transformation in FHIR queries.

**Current State**:
- FHIRPath compliance: 403/934 (43.1%)
- String functions: PARTIALLY IMPLEMENTED
- Missing: `startsWith()`, `endsWith()`, `contains()` (improvements needed)
- Incomplete: `indexOf()`, `substring()`, `upper()`, `lower()`, `replace()` (edge cases)
- Expected gain: +15-20 tests

**Why This is Important**:
1. **Common Operations**: String functions are used extensively in FHIR queries
2. **Data Extraction**: Critical for parsing identifiers, codes, and text fields
3. **Filtering**: Essential for text-based searches and matching
4. **Quality Measures**: Many CQL quality measures use string operations

**Background**: The FHIRPath specification defines a comprehensive set of string manipulation functions. Current implementation has partial support but is missing key functions and has edge case issues.

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

### Progress Updates

| Date       | Update                                                                                           | Status                     | Notes                                                                                   |
|------------|--------------------------------------------------------------------------------------------------|----------------------------|-----------------------------------------------------------------------------------------|
| 2025-11-04 | Senior review completed - APPROVED for merge | ✅ merged to main | Review document: project-docs/plans/reviews/SP-015-009-review.md |
| 2025-11-04 | Reworked translator string predicates to handle literal targets and explicit string arguments; extended `indexOf()` support and added edge-case unit coverage | completed - pending review | DuckDB-focused unit and integration suites updated (PostgreSQL paths still rely on graceful skips when unavailable). |
| 2025-11-04 | Executed enhanced official test runner (`test_filter='string'`) and added Unicode regression tests | completed - pending review | String-focused official subset: 11/15 passing (73.3%); remaining failures tied to unsupported conversion functions. |

---

## Requirements

### Functional Requirements

#### 1. indexOf() Function - Find Substring Position
**FHIRPath Spec Reference**: Section 5.2.2

**Signature**: `string.indexOf(substring: string) : integer`

**Behavior**:
- Returns 0-based index of first occurrence of substring
- Returns -1 if substring not found
- Case-sensitive matching
- Empty string search returns 0
- Empty input returns -1

**Examples**:
```fhirpath
'hello'.indexOf('l')           // 2
'hello'.indexOf('x')           // -1
'hello'.indexOf('')            // 0
''.indexOf('h')                // -1
'hello'.indexOf('lo')          // 3
Patient.name.family.indexOf('Smith')
```

**Current Issues**:
- ✅ Implemented but needs testing
- ⚠️ Edge cases may not be handled

#### 2. substring() Function - Extract Substring
**FHIRPath Spec Reference**: Section 5.2.3

**Signature**:
- `string.substring(start: integer) : string`
- `string.substring(start: integer, length: integer) : string`

**Behavior**:
- Extracts substring starting at 0-based index
- If length omitted, extracts to end of string
- Returns empty string if start >= string length
- Returns empty string if start < 0
- Returns empty string if length <= 0

**Examples**:
```fhirpath
'hello'.substring(1)           // 'ello'
'hello'.substring(1, 2)        // 'el'
'hello'.substring(10)          // ''
'hello'.substring(-1)          // ''
'hello'.substring(0, 100)      // 'hello' (doesn't exceed length)
```

**Current Issues**:
- ✅ Implemented but needs edge case fixes
- ⚠️ Negative index handling
- ⚠️ Length exceeding string bounds

#### 3. startsWith() Function - Check String Prefix
**FHIRPath Spec Reference**: Section 5.2.4

**Signature**: `string.startsWith(prefix: string) : boolean`

**Behavior**:
- Returns `true` if string starts with prefix
- Returns `false` if string doesn't start with prefix
- Empty prefix always returns `true`
- Empty string returns `true` only for empty prefix
- Case-sensitive matching

**Examples**:
```fhirpath
'hello'.startsWith('hel')      // true
'hello'.startsWith('ello')     // false
'hello'.startsWith('')         // true
''.startsWith('')              // true
''.startsWith('h')             // false
Patient.identifier.system.startsWith('http://terminology.hl7.org')
```

**Current Status**:
- ✅ Implemented (2025-11-04)

#### 4. endsWith() Function - Check String Suffix
**FHIRPath Spec Reference**: Section 5.2.5

**Signature**: `string.endsWith(suffix: string) : boolean`

**Behavior**:
- Returns `true` if string ends with suffix
- Returns `false` if string doesn't end with suffix
- Empty suffix always returns `true`
- Empty string returns `true` only for empty suffix
- Case-sensitive matching

**Examples**:
```fhirpath
'hello'.endsWith('lo')         // true
'hello'.endsWith('hel')        // false
'hello'.endsWith('')           // true
''.endsWith('')                // true
''.endsWith('o')               // false
Patient.name.family.endsWith('son')
```

**Current Status**:
- ✅ Implemented (2025-11-04)

#### 5. contains() Function - Check Substring Presence
**FHIRPath Spec Reference**: Section 5.2.6

**Signature**: `string.contains(substring: string) : boolean`

**Behavior**:
- Returns `true` if string contains substring
- Returns `false` if string doesn't contain substring
- Empty substring always returns `true`
- Empty string returns `true` only for empty substring
- Case-sensitive matching

**Examples**:
```fhirpath
'hello'.contains('ell')        // true
'hello'.contains('x')          // false
'hello'.contains('')           // true
''.contains('')                // true
''.contains('h')               // false
Patient.name.family.contains('Sm')
```

**Current Status**:
- ✅ Enhanced (2025-11-04)

#### 6. upper() Function - Convert to Uppercase
**FHIRPath Spec Reference**: Section 5.2.7

**Signature**: `string.upper() : string`

**Behavior**:
- Returns string converted to uppercase
- Handles Unicode characters
- Empty string returns empty string
- Non-string input returns empty collection

**Examples**:
```fhirpath
'hello'.upper()                // 'HELLO'
'Hello World'.upper()          // 'HELLO WORLD'
'123'.upper()                  // '123'
''.upper()                     // ''
Patient.name.family.upper()
```

**Current Status**:
- ✅ IMPLEMENTED (needs testing)

#### 7. lower() Function - Convert to Lowercase
**FHIRPath Spec Reference**: Section 5.2.8

**Signature**: `string.lower() : string`

**Behavior**:
- Returns string converted to lowercase
- Handles Unicode characters
- Empty string returns empty string
- Non-string input returns empty collection

**Examples**:
```fhirpath
'HELLO'.lower()                // 'hello'
'Hello World'.lower()          // 'hello world'
'123'.lower()                  // '123'
''.lower()                     // ''
Patient.name.family.lower()
```

**Current Status**:
- ✅ IMPLEMENTED (needs testing)

#### 8. replace() Function - Replace Substring
**FHIRPath Spec Reference**: Section 5.2.9

**Signature**: `string.replace(pattern: string, substitution: string) : string`

**Behavior**:
- Replaces all occurrences of pattern with substitution
- Returns original string if pattern not found
- Empty pattern returns original string
- Empty substitution removes all occurrences of pattern

**Examples**:
```fhirpath
'hello'.replace('l', 'x')      // 'hexxo'
'hello'.replace('hello', 'hi') // 'hi'
'hello'.replace('x', 'y')      // 'hello'
'hello'.replace('l', '')       // 'heo'
'hello'.replace('', 'x')       // 'hello'
```

**Current Status**:
- ✅ IMPLEMENTED (needs testing)

### Non-Functional Requirements

- **Performance**: <5ms translation overhead per function
- **Compliance**: 100% alignment with FHIRPath specification
- **Database Support**: Identical behavior in DuckDB and PostgreSQL
- **Error Handling**: Clear error messages for invalid operations
- **Unicode Support**: Proper handling of Unicode characters

### Acceptance Criteria

- [ ] All 8 string functions fully implemented
- [x] startsWith() and endsWith() functions added
- [x] contains() function enhanced
- [x] Edge cases handled correctly (empty strings, out of bounds, etc.)
- [x] All unit tests passing (target: 50+ tests across functions)
- [ ] Official test suite improvement: +15-20 tests
- [ ] Both DuckDB and PostgreSQL validated with identical results
- [x] Thin dialect architecture maintained
- [x] Unicode character support verified
- [ ] Code review approved by Senior Architect

---

## Technical Specifications

### Affected Components

- **SQL Translator**: String function translation in `ASTToSQLTranslator`
- **Dialect Layer**: Database-specific string function SQL
- **Both Databases**: DuckDB and PostgreSQL compatibility

### File Modifications

**Primary Files**:
- **`fhir4ds/fhirpath/sql/translator.py`**: Added `_resolve_string_target_and_args()` helper, reworked `_translate_contains()`, `_translate_startswith()`, and `_translate_endswith()` to support literal targets and explicit string arguments, and enabled `indexOf()` to accept function-style invocations while preserving thin dialect boundaries.

**Testing Files**:
- **`tests/unit/fhirpath/sql/test_translator_contains.py`**: Added coverage for literal targets and explicit string argument usage.
- **`tests/unit/fhirpath/sql/test_translator_startswith_endswith.py`**: Expanded tests to validate literal targets and two-argument invocation patterns.
- **`tests/unit/fhirpath/sql/test_translator_string_functions.py`**: Added substring guard assertions, start-beyond-length coverage, and function-style `indexOf()` tests to lock in edge-case behaviors.

**No Changes Required**:
- **`fhir4ds/dialects/*.py`**: Existing dialect methods continue to satisfy the updated translator logic.
- **`fhir4ds/fhirpath/parser/`**, **`fhir4ds/fhirpath/sql/cte.py`**: No modifications needed.

### Database Considerations

**DuckDB String Functions**:
```sql
-- indexOf: strpos() returns 1-based, subtract 1 for 0-based
strpos('hello', 'l') - 1  -- Returns 2

-- substring: substring() with 1-based indexing
substring('hello', 2, 2)  -- Returns 'el' (start at position 2, length 2)

-- startsWith: starts_with() or prefix()
starts_with('hello', 'hel')  -- Returns true
'hello' LIKE 'hel%'          -- Alternative

-- endsWith: ends_with() or suffix()
ends_with('hello', 'lo')     -- Returns true
'hello' LIKE '%lo'           -- Alternative

-- contains: strpos() > 0 or contains()
strpos('hello', 'ell') > 0   -- Returns true
contains('hello', 'ell')     -- Returns true (if available)

-- upper/lower: UPPER()/LOWER()
UPPER('hello')               -- Returns 'HELLO'
LOWER('HELLO')               -- Returns 'hello'

-- replace: replace()
replace('hello', 'l', 'x')   -- Returns 'hexxo'
```

**PostgreSQL String Functions**:
```sql
-- indexOf: position() returns 1-based, subtract 1 for 0-based
position('l' in 'hello') - 1  -- Returns 2

-- substring: substring() with 1-based indexing
substring('hello' from 2 for 2)  -- Returns 'el'

-- startsWith: starts_with() or LIKE
starts_with('hello', 'hel')      -- Returns true (PostgreSQL 13+)
'hello' LIKE 'hel%'              -- Alternative

-- endsWith: custom or LIKE
'hello' LIKE '%lo'               -- Returns true

-- contains: position() > 0 or strpos()
position('ell' in 'hello') > 0   -- Returns true
strpos('hello', 'ell') > 0       -- Returns true

-- upper/lower: UPPER()/LOWER()
UPPER('hello')                   -- Returns 'HELLO'
LOWER('HELLO')                   -- Returns 'hello'

-- replace: replace()
replace('hello', 'l', 'x')       -- Returns 'hexxo'
```

**Index Conversion**:
- FHIRPath uses 0-based indexing
- SQL uses 1-based indexing
- Must convert: `fhirpath_index + 1 = sql_index`
- Must convert back: `sql_result - 1 = fhirpath_result` (for indexOf)

---

## Dependencies

### Prerequisites
1. **Parser**: String functions already in FHIRPath grammar
2. **DuckDB**: Local database functional
3. **PostgreSQL**: Connection available for validation
4. **Test Infrastructure**: Official test runner operational

### Blocking Tasks
- **NONE** - can start immediately

### Dependent Tasks
- **SP-015-010**: Collection utilities (may use string functions)
- **Sprint 016**: Future features may depend on string operations

---

## Implementation Approach

### High-Level Strategy

**Three-Phase Implementation**:

1. **Phase 1**: Implement missing functions (startsWith, endsWith)
   - Add translator methods
   - Add dialect implementations
   - Create comprehensive tests

2. **Phase 2**: Enhance existing functions (contains, indexOf, substring)
   - Fix edge cases
   - Improve error handling
   - Add missing tests

3. **Phase 3**: Integration validation
   - Run full official test suite
   - Validate both databases
   - Performance testing

**Key Principles**:
- Use native SQL string functions where available
- Handle edge cases per FHIRPath specification
- Maintain thin dialect architecture (syntax only in dialects)
- Comprehensive testing including Unicode

---

### Implementation Steps

#### Phase 1: Implement Missing Functions (4-5 hours)

**Step 1.1: Implement startsWith() Function (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 5800 (new method)

**Implementation**:
```python
def _translate_starts_with(self, node: FunctionCallNode) -> SQLFragment:
    """Translate startsWith() string function.

    FHIRPath Spec: Section 5.2.4

    Signature: string.startsWith(prefix: string) : boolean

    Returns true if string starts with prefix.

    Args:
        node: FunctionCallNode for startsWith()

    Returns:
        SQLFragment with boolean result

    Example:
        'hello'.startsWith('hel') → true
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("startsWith() requires exactly 1 argument (prefix string)")

    # Get string expression (target)
    if hasattr(node, 'target') and node.target:
        # Method call: 'hello'.startsWith('hel')
        string_fragment = self.visit(node.target)
        string_expr = string_fragment.expression
    elif len(node.arguments) == 2:
        # Function call: startsWith(string, prefix)
        string_fragment = self.visit(node.arguments[0])
        string_expr = string_fragment.expression
        # Get prefix from second argument
        prefix_fragment = self.visit(node.arguments[1])
    else:
        # Method call with implicit context
        string_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )

    # Get prefix argument
    if len(node.arguments) == 2:
        # Already got prefix above
        pass
    else:
        prefix_fragment = self.visit(node.arguments[0])

    prefix_expr = prefix_fragment.expression

    # Generate SQL using dialect method
    sql = self.dialect.generate_starts_with(string_expr, prefix_expr)

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'function': 'startsWith'}
    )
```

**Dialect Implementation - DuckDB**:

**Location**: `fhir4ds/dialects/duckdb.py` ~line 800 (new method)

```python
def generate_starts_with(self, string_expr: str, prefix_expr: str) -> str:
    """Generate SQL for startsWith() in DuckDB.

    DuckDB has starts_with() function.

    Args:
        string_expr: SQL expression for string
        prefix_expr: SQL expression for prefix

    Returns:
        SQL boolean expression

    Example:
        generate_starts_with("'hello'", "'hel'")
        → "starts_with('hello', 'hel')"
    """
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({prefix_expr}) IS NULL THEN false
        WHEN ({prefix_expr}) = '' THEN true
        ELSE starts_with(({string_expr})::VARCHAR, ({prefix_expr})::VARCHAR)
    END
    """.strip()
```

**Dialect Implementation - PostgreSQL**:

**Location**: `fhir4ds/dialects/postgresql.py` ~line 800 (new method)

```python
def generate_starts_with(self, string_expr: str, prefix_expr: str) -> str:
    """Generate SQL for startsWith() in PostgreSQL.

    PostgreSQL 13+ has starts_with(), fallback to LIKE for older versions.

    Args:
        string_expr: SQL expression for string
        prefix_expr: SQL expression for prefix

    Returns:
        SQL boolean expression
    """
    # Use PostgreSQL 13+ starts_with() if available, otherwise LIKE
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({prefix_expr}) IS NULL THEN false
        WHEN ({prefix_expr}) = '' THEN true
        ELSE ({string_expr})::text LIKE (({prefix_expr})::text || '%')
    END
    """.strip()
```

**Testing**:
```python
def test_starts_with_basic(duckdb_dialect):
    """Test startsWith() with basic strings."""
    translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

    # Create 'hello'.startsWith('hel')
    target = LiteralNode(node_type="literal", text="'hello'", value="hello")
    prefix = LiteralNode(node_type="literal", text="'hel'", value="hel")

    node = FunctionCallNode(
        node_type="functionCall",
        function_name="startsWith",
        arguments=[prefix],
        target=target
    )

    fragment = translator._translate_starts_with(node)

    assert "starts_with" in fragment.expression or "LIKE" in fragment.expression
    assert "'hello'" in fragment.expression
    assert "'hel'" in fragment.expression
```

---

**Step 1.2: Implement endsWith() Function (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 5900 (new method)

**Implementation**:
```python
def _translate_ends_with(self, node: FunctionCallNode) -> SQLFragment:
    """Translate endsWith() string function.

    FHIRPath Spec: Section 5.2.5

    Signature: string.endsWith(suffix: string) : boolean

    Returns true if string ends with suffix.

    Args:
        node: FunctionCallNode for endsWith()

    Returns:
        SQLFragment with boolean result

    Example:
        'hello'.endsWith('lo') → true
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("endsWith() requires exactly 1 argument (suffix string)")

    # Get string expression (same pattern as startsWith)
    if hasattr(node, 'target') and node.target:
        string_fragment = self.visit(node.target)
        string_expr = string_fragment.expression
    else:
        string_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )

    # Get suffix argument
    suffix_fragment = self.visit(node.arguments[0])
    suffix_expr = suffix_fragment.expression

    # Generate SQL using dialect method
    sql = self.dialect.generate_ends_with(string_expr, suffix_expr)

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'function': 'endsWith'}
    )
```

**Dialect Implementation - DuckDB**:

**Location**: `fhir4ds/dialects/duckdb.py` ~line 850 (new method)

```python
def generate_ends_with(self, string_expr: str, suffix_expr: str) -> str:
    """Generate SQL for endsWith() in DuckDB.

    DuckDB has ends_with() function (or suffix() in older versions).

    Args:
        string_expr: SQL expression for string
        suffix_expr: SQL expression for suffix

    Returns:
        SQL boolean expression
    """
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({suffix_expr}) IS NULL THEN false
        WHEN ({suffix_expr}) = '' THEN true
        ELSE ends_with(({string_expr})::VARCHAR, ({suffix_expr})::VARCHAR)
    END
    """.strip()
```

**Dialect Implementation - PostgreSQL**:

**Location**: `fhir4ds/dialects/postgresql.py` ~line 850 (new method)

```python
def generate_ends_with(self, string_expr: str, suffix_expr: str) -> str:
    """Generate SQL for endsWith() in PostgreSQL.

    PostgreSQL doesn't have ends_with(), use LIKE pattern.

    Args:
        string_expr: SQL expression for string
        suffix_expr: SQL expression for suffix

    Returns:
        SQL boolean expression
    """
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({suffix_expr}) IS NULL THEN false
        WHEN ({suffix_expr}) = '' THEN true
        ELSE ({string_expr})::text LIKE ('%' || ({suffix_expr})::text)
    END
    """.strip()
```

---

**Step 1.3: Update Function Translator Mapping (30 min)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 1097

**Current Code**:
```python
elif function_name in ["substring", "indexof", "length", "replace", "split"]:
    return self._translate_string_function(node)
elif function_name == "upper":
    return self._translate_upper(node)
elif function_name == "lower":
    return self._translate_lower(node)
```

**Updated Code**:
```python
elif function_name in ["substring", "indexof", "length", "replace", "split"]:
    return self._translate_string_function(node)
elif function_name == "upper":
    return self._translate_upper(node)
elif function_name == "lower":
    return self._translate_lower(node)
elif function_name == "startswith":  # ← ADD
    return self._translate_starts_with(node)
elif function_name == "endswith":    # ← ADD
    return self._translate_ends_with(node)
```

---

**Phase 1 Validation (30 min)**:

```bash
# Run string function tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_string_functions.py -k "starts_with or ends_with" -v

# Manual testing
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect

parser = FHIRPathParser()
dialect = DuckDBDialect(':memory:')
translator = ASTToSQLTranslator(dialect, 'Patient')

# Test startsWith
ast = parser.parse(\"'hello'.startsWith('hel')\").get_ast()
fragments = translator.translate(ast)
print('startsWith SQL:', fragments[-1].expression)

# Test endsWith
ast = parser.parse(\"'hello'.endsWith('lo')\").get_ast()
fragments = translator.translate(ast)
print('endsWith SQL:', fragments[-1].expression)
"
```

---

#### Phase 2: Enhance Existing Functions (4-5 hours)

**Step 2.1: Enhance contains() Function (1.5-2 hours)**

**Current Issue**: contains() may not handle all edge cases properly

**Location**: `fhir4ds/fhirpath/sql/translator.py` (find existing `_translate_contains`)

**Enhanced Implementation**:
```python
def _translate_contains(self, node: FunctionCallNode) -> SQLFragment:
    """Translate contains() string function.

    Enhanced to handle all edge cases per FHIRPath specification.

    FHIRPath Spec: Section 5.2.6

    Signature: string.contains(substring: string) : boolean

    Args:
        node: FunctionCallNode for contains()

    Returns:
        SQLFragment with boolean result
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("contains() requires exactly 1 argument (substring)")

    # Get string expression
    if hasattr(node, 'target') and node.target:
        string_fragment = self.visit(node.target)
        string_expr = string_fragment.expression
    else:
        string_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )

    # Get substring argument
    substring_fragment = self.visit(node.arguments[0])
    substring_expr = substring_fragment.expression

    # Generate SQL using dialect method
    sql = self.dialect.generate_string_contains(string_expr, substring_expr)

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'function': 'contains'}
    )
```

**Dialect Enhancement - DuckDB**:
```python
def generate_string_contains(self, string_expr: str, substring_expr: str) -> str:
    """Generate SQL for contains() in DuckDB.

    Args:
        string_expr: SQL expression for string
        substring_expr: SQL expression for substring

    Returns:
        SQL boolean expression
    """
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({substring_expr}) IS NULL THEN false
        WHEN ({substring_expr}) = '' THEN true
        ELSE strpos(({string_expr})::VARCHAR, ({substring_expr})::VARCHAR) > 0
    END
    """.strip()
```

**Dialect Enhancement - PostgreSQL**:
```python
def generate_string_contains(self, string_expr: str, substring_expr: str) -> str:
    """Generate SQL for contains() in PostgreSQL.

    Args:
        string_expr: SQL expression for string
        substring_expr: SQL expression for substring

    Returns:
        SQL boolean expression
    """
    return f"""
    CASE
        WHEN ({string_expr}) IS NULL OR ({substring_expr}) IS NULL THEN false
        WHEN ({substring_expr}) = '' THEN true
        ELSE position(({substring_expr})::text in ({string_expr})::text) > 0
    END
    """.strip()
```

---

**Step 2.2: Fix indexOf() Edge Cases (1-1.5 hours)**

**Current Issues**:
- May not handle empty strings correctly
- Return value conversion (1-based to 0-based)

**Location**: `fhir4ds/fhirpath/sql/translator.py` (in `_translate_string_function`)

**Review and Enhance**:
```python
# In _translate_string_function(), indexOf case:
if function_name == "indexof":
    # Existing implementation, ensure it handles:
    # 1. Empty substring → return 0
    # 2. Not found → return -1
    # 3. Conversion from 1-based (SQL) to 0-based (FHIRPath)

    # Get string and search substring
    if hasattr(node, 'target') and node.target:
        string_fragment = self.visit(node.target)
        string_expr = string_fragment.expression
    else:
        string_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )

    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("indexOf() requires exactly 1 argument (substring)")

    substring_fragment = self.visit(node.arguments[0])
    substring_expr = substring_fragment.expression

    # Generate SQL with proper edge case handling
    sql = f"""
    CASE
        WHEN ({string_expr}) IS NULL THEN -1
        WHEN ({substring_expr}) = '' THEN 0
        ELSE {self.dialect.generate_index_of(string_expr, substring_expr)}
    END
    """

    return SQLFragment(
        expression=sql.strip(),
        requires_unnest=False,
        is_aggregate=False
    )
```

**Dialect Methods**:
```python
# DuckDB
def generate_index_of(self, string_expr: str, substring_expr: str) -> str:
    """Generate indexOf SQL for DuckDB (convert 1-based to 0-based)."""
    return f"(strpos(({string_expr})::VARCHAR, ({substring_expr})::VARCHAR) - 1)"

# PostgreSQL
def generate_index_of(self, string_expr: str, substring_expr: str) -> str:
    """Generate indexOf SQL for PostgreSQL (convert 1-based to 0-based)."""
    return f"(position(({substring_expr})::text in ({string_expr})::text) - 1)"
```

---

**Step 2.3: Fix substring() Edge Cases (1-1.5 hours)**

**Current Issues**:
- Negative start index should return empty string
- Start beyond length should return empty string
- Length parameter edge cases

**Location**: `fhir4ds/fhirpath/sql/translator.py` (in `_translate_string_function`)

**Enhanced Implementation**:
```python
# In _translate_string_function(), substring case:
if function_name == "substring":
    # Get string expression
    if hasattr(node, 'target') and node.target:
        string_fragment = self.visit(node.target)
        string_expr = string_fragment.expression
    elif len(node.arguments) >= 2:
        # Function form: substring(string, start [, length])
        string_fragment = self.visit(node.arguments[0])
        string_expr = string_fragment.expression
        # Remove first argument from list for processing below
        args_to_process = node.arguments[1:]
    else:
        # Method form with implicit context
        string_expr = self.dialect.extract_json_field(
            self.context.current_table or "resource",
            self.context.parent_path
        )
        args_to_process = node.arguments

    # Get start and optional length
    if len(args_to_process) < 1:
        raise ValueError("substring() requires 1-2 arguments (start index [, length])")

    start_fragment = self.visit(args_to_process[0])
    start_expr = start_fragment.expression

    length_expr = None
    if len(args_to_process) >= 2:
        length_fragment = self.visit(args_to_process[1])
        length_expr = length_fragment.expression

    # Generate SQL with edge case handling
    # FHIRPath uses 0-based indexing, SQL uses 1-based
    # Convert: fhirpath_start + 1 = sql_start

    if length_expr:
        # substring(start, length)
        sql = f"""
        CASE
            WHEN ({start_expr}) < 0 THEN ''
            WHEN ({length_expr}) <= 0 THEN ''
            ELSE substring(({string_expr})::VARCHAR FROM (({start_expr}) + 1) FOR ({length_expr}))
        END
        """
    else:
        # substring(start) - to end of string
        sql = f"""
        CASE
            WHEN ({start_expr}) < 0 THEN ''
            ELSE substring(({string_expr})::VARCHAR FROM (({start_expr}) + 1))
        END
        """

    return SQLFragment(
        expression=sql.strip(),
        requires_unnest=False,
        is_aggregate=False
    )
```

---

**Phase 2 Validation (30 min)**:

```bash
# Test edge cases
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_string_functions.py::TestSubstringEdgeCases -v
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_string_functions.py::TestIndexOfEdgeCases -v

# Manual edge case testing
PYTHONPATH=. python3 work/test_string_edge_cases.py
```

---

#### Phase 3: Integration Validation (3-4 hours)

**Step 3.1: Create Comprehensive Unit Tests (2 hours)**

**Location**: `tests/unit/fhirpath/sql/test_translator_string_functions.py`

**Add Tests** (50+ total):

```python
class TestStartsWithFunction:
    """Comprehensive tests for startsWith() function."""

    def test_starts_with_basic_match(self, duckdb_dialect):
        """Test startsWith() with matching prefix."""
        # 'hello'.startsWith('hel') → true

    def test_starts_with_no_match(self, duckdb_dialect):
        """Test startsWith() with non-matching prefix."""
        # 'hello'.startsWith('lo') → false

    def test_starts_with_empty_prefix(self, duckdb_dialect):
        """Test startsWith() with empty prefix."""
        # 'hello'.startsWith('') → true

    def test_starts_with_empty_string(self, duckdb_dialect):
        """Test startsWith() with empty string."""
        # ''.startsWith('h') → false
        # ''.startsWith('') → true

    def test_starts_with_case_sensitive(self, duckdb_dialect):
        """Test startsWith() is case-sensitive."""
        # 'Hello'.startsWith('hel') → false
        # 'Hello'.startsWith('Hel') → true

    def test_starts_with_unicode(self, duckdb_dialect):
        """Test startsWith() with Unicode characters."""
        # 'café'.startsWith('caf') → true

    def test_starts_with_postgresql(self, postgresql_dialect):
        """Test startsWith() on PostgreSQL."""
        # Same tests as DuckDB

class TestEndsWithFunction:
    """Comprehensive tests for endsWith() function."""

    def test_ends_with_basic_match(self, duckdb_dialect):
        """Test endsWith() with matching suffix."""
        # 'hello'.endsWith('lo') → true

    def test_ends_with_no_match(self, duckdb_dialect):
        """Test endsWith() with non-matching suffix."""
        # 'hello'.endsWith('hel') → false

    def test_ends_with_empty_suffix(self, duckdb_dialect):
        """Test endsWith() with empty suffix."""
        # 'hello'.endsWith('') → true

    def test_ends_with_empty_string(self, duckdb_dialect):
        """Test endsWith() with empty string."""
        # ''.endsWith('o') → false
        # ''.endsWith('') → true

    def test_ends_with_case_sensitive(self, duckdb_dialect):
        """Test endsWith() is case-sensitive."""
        # 'Hello'.endsWith('LO') → false
        # 'Hello'.endsWith('lo') → true

    def test_ends_with_postgresql(self, postgresql_dialect):
        """Test endsWith() on PostgreSQL."""

class TestContainsEnhanced:
    """Enhanced tests for contains() function."""

    def test_contains_empty_substring(self, duckdb_dialect):
        """Test contains('') always returns true."""
        # 'hello'.contains('') → true
        # ''.contains('') → true

    def test_contains_null_handling(self, duckdb_dialect):
        """Test contains() with NULL values."""
        # NULL.contains('x') → false

class TestIndexOfEdgeCases:
    """Edge case tests for indexOf() function."""

    def test_indexof_empty_substring(self, duckdb_dialect):
        """Test indexOf('') returns 0."""

    def test_indexof_not_found(self, duckdb_dialect):
        """Test indexOf() returns -1 when not found."""

    def test_indexof_first_occurrence(self, duckdb_dialect):
        """Test indexOf() returns first occurrence."""
        # 'hello'.indexOf('l') → 2 (not 3)

class TestSubstringEdgeCases:
    """Edge case tests for substring() function."""

    def test_substring_negative_start(self, duckdb_dialect):
        """Test substring() with negative start returns empty."""

    def test_substring_start_beyond_length(self, duckdb_dialect):
        """Test substring() with start beyond length returns empty."""

    def test_substring_length_zero(self, duckdb_dialect):
        """Test substring() with length 0 returns empty."""

    def test_substring_length_exceeds_bounds(self, duckdb_dialect):
        """Test substring() with length exceeding string bounds."""
        # 'hello'.substring(0, 100) → 'hello' (doesn't error)
```

---

**Step 3.2: Multi-Database Integration Tests (1 hour)**

**Create Script**: `work/test_string_functions_integration.py`

```python
"""Integration tests for string functions across databases."""

import pytest
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast

def execute_string_expression(dialect, expression):
    """Execute a FHIRPath string expression and return result."""
    parser = FHIRPathParser()
    translator = ASTToSQLTranslator(dialect, "Patient")

    ast = convert_enhanced_ast_to_fhirpath_ast(parser.parse(expression).get_ast())
    fragments = translator.translate(ast)

    # Execute SQL and return result
    sql = fragments[-1].expression
    return dialect.execute_scalar(sql)

def test_all_string_functions():
    """Test all string functions in both databases."""

    test_cases = [
        # (expression, expected_result)
        ("'hello'.startsWith('hel')", True),
        ("'hello'.startsWith('lo')", False),
        ("'hello'.endsWith('lo')", True),
        ("'hello'.endsWith('hel')", False),
        ("'hello'.contains('ell')", True),
        ("'hello'.contains('x')", False),
        ("'hello'.indexOf('l')", 2),
        ("'hello'.indexOf('x')", -1),
        ("'hello'.substring(1)", 'ello'),
        ("'hello'.substring(1, 2)", 'el'),
        ("'hello'.upper()", 'HELLO'),
        ("'hello'.lower()", 'hello'),
        ("'hello'.replace('l', 'x')", 'hexxo'),
    ]

    dialects = [
        (DuckDBDialect(":memory:"), "DuckDB"),
        (PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres"), "PostgreSQL")
    ]

    results = {}
    for dialect, db_name in dialects:
        print(f"\nTesting {db_name}:")
        results[db_name] = {}

        for expression, expected in test_cases:
            try:
                result = execute_string_expression(dialect, expression)
                status = "✅" if result == expected else "❌"
                print(f"{status} {expression} = {result} (expected {expected})")
                results[db_name][expression] = result
            except Exception as e:
                print(f"❌ {expression} ERROR: {e}")
                results[db_name][expression] = None

    # Verify consistency across databases
    print("\nConsistency Check:")
    for expression, _ in test_cases:
        duckdb_result = results["DuckDB"].get(expression)
        pg_result = results["PostgreSQL"].get(expression)

        if duckdb_result == pg_result:
            print(f"✅ {expression}: Consistent")
        else:
            print(f"❌ {expression}: Inconsistent (DuckDB={duckdb_result}, PostgreSQL={pg_result})")

if __name__ == '__main__':
    test_all_string_functions()
```

**Run Integration Tests**:
```bash
PYTHONPATH=. python3 work/test_string_functions_integration.py
```

---

**Step 3.3: Official Test Suite Validation (1 hour)**

```bash
# Run official test suite
PYTHONPATH=. python3 -m pytest tests/official/ -v

# Expected improvements:
# Before: 403/934 (43.1%)
# After: 418-423/934 (44.7-45.3%)
# Gain: +15-20 tests
```

**Analyze Results**:
- Identify which string function tests now pass
- Document any remaining failures
- Create follow-up tasks if needed

---

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/fhirpath/sql/test_translator_string_functions.py`

**Test Categories** (Target: 50+ tests):

1. **startsWith() Tests** (8 tests):
   - Basic matching
   - Non-matching
   - Empty prefix/string
   - Case sensitivity
   - Unicode
   - Multi-database

2. **endsWith() Tests** (8 tests):
   - Basic matching
   - Non-matching
   - Empty suffix/string
   - Case sensitivity
   - Unicode
   - Multi-database

3. **contains() Tests** (6 tests):
   - Basic matching
   - Empty substring
   - NULL handling
   - Multi-database

4. **indexOf() Tests** (8 tests):
   - Basic search
   - Not found (-1)
   - Empty substring
   - First occurrence
   - Multi-database

5. **substring() Tests** (10 tests):
   - Basic extraction
   - With length parameter
   - Negative start
   - Beyond bounds
   - Length zero
   - Multi-database

6. **upper()/lower() Tests** (6 tests):
   - Basic conversion
   - Unicode
   - Multi-database

7. **replace() Tests** (6 tests):
   - Basic replacement
   - Multiple occurrences
   - Empty pattern/substitution
   - Multi-database

### Integration Tests

**Location**: `tests/integration/fhirpath/test_string_functions_e2e.py` (create new)

1. **End-to-End String Operations**:
   - Execute against real FHIR data
   - Validate results
   - Performance testing

2. **Multi-Database Validation**:
   - Same tests in both databases
   - Verify identical results

### Official Test Suite

**Command**:
```bash
PYTHONPATH=. python3 -m pytest tests/official/ -v
```

**Expected Improvements**:
- Before: 403/934 (43.1%)
- After: 418-423/934 (44.7-45.3%)
- Gain: +15-20 tests

---

## Notes for Junior Developer

### Getting Started

1. **Read Background Materials**:
   - FHIRPath Specification Section 5.2 (String Manipulation)
   - SQL string functions documentation (DuckDB and PostgreSQL)
   - Existing test file: `test_translator_string_functions.py`

2. **Understand Index Conversion**:
   - FHIRPath: 0-based indexing (like Python)
   - SQL: 1-based indexing
   - Always convert: `fhirpath_index + 1 = sql_index`

3. **Set Up Testing**:
   ```bash
   cd /mnt/d/fhir4ds2
   PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_string_functions.py -v
   ```

### Common Pitfalls

1. **Index Conversion**:
   - ❌ Forgetting to convert between 0-based and 1-based
   - ✅ Always add 1 when converting FHIRPath index to SQL

2. **Edge Cases**:
   - ❌ Not handling empty strings
   - ✅ Always check for empty string edge cases

3. **NULL Handling**:
   - ❌ Forgetting NULL checks
   - ✅ Always handle NULL values explicitly

4. **Database Syntax**:
   - ❌ Using DuckDB syntax in PostgreSQL
   - ✅ Use dialect methods for database-specific syntax

### Debugging Tips

1. **Test SQL Directly**:
   ```sql
   -- DuckDB
   SELECT starts_with('hello', 'hel');  -- true
   SELECT strpos('hello', 'l') - 1;     -- 2 (indexOf result)

   -- PostgreSQL
   SELECT position('l' in 'hello') - 1;  -- 2
   ```

2. **Manual Testing**:
   ```python
   from fhir4ds.fhirpath.parser import FHIRPathParser
   from fhir4ds.dialects.duckdb import DuckDBDialect

   parser = FHIRPathParser()
   dialect = DuckDBDialect(':memory:')

   # Test expression
   expr = "'hello'.startsWith('hel')"
   # ... translate and execute
   ```

3. **Use Print Debugging**:
   ```python
   # In translator method
   print(f"String expr: {string_expr}")
   print(f"Generated SQL: {sql}")
   ```

### Architecture Alignment

**Thin Dialect Principle**:
- ✅ **Translator**: Function logic, argument validation, edge case handling
- ✅ **Dialect**: Database-specific SQL syntax only
- ❌ **NOT in Dialect**: Business logic, validation

### Success Metrics

**After Completing This Task**:
- [x] All 50+ unit tests passing
- [ ] Official test suite: +15-20 tests
- [x] startsWith() and endsWith() implemented
- [x] All edge cases handled
- [ ] Both databases identical results
- [ ] Unicode support verified

---

## Risk Assessment

### High Risk Areas

1. **Index Conversion Errors**:
   - Risk: Off-by-one errors in indexOf/substring
   - Mitigation: Comprehensive testing with known values

2. **Unicode Handling**:
   - Risk: Different Unicode behavior across databases
   - Mitigation: Test with Unicode strings in both databases

3. **Edge Case Coverage**:
   - Risk: Missing edge cases causing test failures
   - Mitigation: Systematic edge case testing

### Mitigation Strategies

1. **Incremental Implementation**: Complete one function before starting next
2. **Test-Driven Development**: Write tests first, then implement
3. **Database Validation**: Test every function in both databases

---

## Definition of Done

- [ ] All Phase 1-3 steps completed
- [x] startsWith() function implemented and tested
- [x] endsWith() function implemented and tested
- [x] contains() function enhanced and tested
- [x] indexOf() edge cases fixed
- [x] substring() edge cases fixed
- [x] All unit tests passing (50+ tests)
- [x] Integration tests created and passing
- [ ] Official test suite: +15-20 tests passing
- [ ] Both databases validated
- [ ] Unicode support verified
- [ ] No performance regressions
- [x] Thin dialect architecture maintained
- [ ] Code review approved
- [x] Documentation updated

---

## Approval

**Developer Sign-off**: Junior Developer  Date: 2025-11-04

**Code Review**: Senior Solution Architect/Engineer  Date: 2025-11-04

**Senior Architect Approval**: ✅ APPROVED  Date: 2025-11-04

**Merge Status**: ✅ Merged to main (commit: bcba9c8)

---

**End of Task Document SP-015-009**
