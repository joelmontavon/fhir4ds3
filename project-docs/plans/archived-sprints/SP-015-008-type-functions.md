# Task: Enhanced Type Checking and Conversion Functions

**Task ID**: SP-015-008
**Sprint**: 015 (Week 4) or 016 (Week 1)
**Task Name**: Fix and Enhance Type Checking Functions (is, as, ofType)
**Assignee**: Junior Developer
**Created**: 2025-11-02
**Last Updated**: 2025-11-02
**Estimated Effort**: 14-18 hours
**Priority**: High (Blocking many tests)

---

## Task Overview

### Description

Fix critical issues in the type checking and conversion functions (`is()`, `as()`, `ofType()`) that are causing widespread test failures. These functions are fundamental to FHIRPath's type system and currently have bugs preventing proper type checking and polymorphic type casting.

**Current State**:
- FHIRPath compliance: 403/934 (43.1%)
- Type functions: PARTIALLY IMPLEMENTED (with bugs)
- Current failures: "Unknown FHIR type" errors, incorrect type checking results
- Expected gain: +20-25 tests

**Why This is Critical**:
1. **High-Impact Functions**: Type operations are used extensively throughout FHIRPath expressions
2. **Polymorphic Types**: Critical for FHIR's polymorphic properties (Observation.value[x], Procedure.performed[x])
3. **Test Blocker**: Many test failures stem from type function issues
4. **Foundation**: Other features depend on correct type handling

**Background**: The FHIRPath specification defines three type-related functions that must handle both primitive types (String, Integer, Boolean) and complex types (Quantity, CodeableConcept, Period). Current implementation has:
- Bug #1: Type registry lookups fail for valid FHIR types
- Bug #2: String type primitives not properly canonicalized
- Bug #3: Polymorphic type casts don't properly resolve variant properties
- Bug #4: conformsTo() function not implemented

### Category
- [ ] Feature Implementation
- [x] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [x] Testing
- [x] Documentation
- [ ] Process Improvement

### Priority
- [ ] Critical (Blocker for sprint goals)
- [x] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

#### 1. is() Function - Type Checking
**FHIRPath Spec Reference**: Section 6.3.1

**Behavior**:
- Returns `true` if input is of the specified type
- Returns `false` if input is not of the specified type
- Returns empty collection `{}` if input is empty
- Handles both primitive types (String, Integer, Boolean, Decimal, DateTime, Date, Time) and complex types (Quantity, CodeableConcept, Period, etc.)
- Supports type aliases (code → string, Age → Quantity)
- Null values return `false`

**Examples**:
```fhirpath
5 is Integer                          // true
'hello' is String                     // true
'hello' is Integer                    // false
Patient.birthDate is Date             // true
Observation.value is Quantity         // true (if value is Quantity)
Observation.value is String           // false (if value is Quantity)
{} is String                          // {} (empty)
```

**Current Issues**:
- ❌ "Unknown FHIR type 'Quantity'" errors
- ❌ Type aliases not resolved (code, Age, Duration)
- ❌ String type checking returns false incorrectly
- ❌ Complex types return false instead of checking discriminator fields

#### 2. as() Function - Type Conversion/Casting
**FHIRPath Spec Reference**: Section 6.3.2

**Behavior**:
- Returns input if it is of the specified type
- Returns empty collection `{}` if input cannot be converted
- For primitive types: attempts safe conversion (e.g., '123' as Integer)
- For complex types: checks polymorphic variants (e.g., Observation.value as Quantity checks valueQuantity)
- Null values return empty collection

**Examples**:
```fhirpath
'123' as Integer                      // 123
123 as String                         // '123'
'hello' as Integer                    // {} (cannot convert)
Observation.value as Quantity         // returns value if it's a Quantity, {} otherwise
Procedure.performed as Period         // returns performedPeriod if present
```

**Current Issues**:
- ❌ "Unknown FHIR type" errors for valid types
- ❌ Polymorphic casts don't check discriminator fields properly
- ❌ Resource type casts should return NULL but don't
- ❌ Type aliases not resolved before casting

#### 3. ofType() Function - Collection Type Filtering
**FHIRPath Spec Reference**: Section 5.1.1

**Behavior**:
- Filters collection to only elements of specified type
- Returns empty collection if no elements match
- Works on heterogeneous collections
- Used for polymorphic property resolution

**Examples**:
```fhirpath
(1 | 'hello' | 2).ofType(Integer)     // (1 | 2)
(1 | 'hello' | 2).ofType(String)      // ('hello')
Observation.component.value.ofType(Quantity)  // only Quantity values
```

**Current Issues**:
- ❌ Unknown type returns empty array inconsistently
- ❌ Complex type filtering doesn't check discriminators
- ❌ SQL generation varies between databases unnecessarily

#### 4. conformsTo() Function - Profile Checking
**FHIRPath Spec Reference**: Section 6.3.3

**Behavior**:
- Returns `true` if input conforms to the specified profile
- Used for FHIR profile validation
- Checks structure definition URLs

**Examples**:
```fhirpath
Patient.conformsTo('http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient')
```

**Current Status**:
- ✅ Implemented for DuckDB/PostgreSQL (meta.profile membership check)

### Non-Functional Requirements

- **Performance**: <10ms translation overhead per type operation
- **Compliance**: 100% alignment with FHIRPath specification type behavior
- **Database Support**: Identical behavior in DuckDB and PostgreSQL
- **Error Handling**: Clear error messages for truly invalid types
- **Type Registry**: Proper integration with FHIR type registry

### Acceptance Criteria

- [x] Bug #1 Fixed: Type registry lookups succeed for all valid FHIR types
- [x] Bug #2 Fixed: String type primitives properly canonicalized (string, String, System.String)
- [x] Bug #3 Fixed: Polymorphic type casts resolve variant properties correctly
- [x] Bug #4 Implemented: conformsTo() function works for profile checking
- [x] All type aliases resolved (code→string, Age→Quantity, Duration→Quantity)
- [x] All unit tests passing (target: 60+ tests across all type functions)
- [ ] Official test suite improvement: +20-25 tests
- [ ] Both DuckDB and PostgreSQL validated with identical results
- [x] Thin dialect architecture maintained (business logic in translator only)
- [ ] Code review approved by Senior Architect

---

## Technical Specifications

### Affected Components

- **SQL Translator**: Type operation translation in `ASTToSQLTranslator`
- **Type Registry**: Type lookup and canonicalization
- **Type Discriminators**: Polymorphic type checking
- **Dialect Layer**: Database-specific type checking SQL
- **Both Databases**: DuckDB and PostgreSQL compatibility

### File Modifications

**Primary Files**:
- **`fhir4ds/fhirpath/sql/translator.py`**: Modify (critical fixes)
  - Lines 3794-3840: `_translate_is_operation()` - fix type lookups
  - Lines 3840-4300: `_translate_as_operation()` - fix polymorphic casts
  - Lines 4100-4200: `visit_type_operation()` - add ofType support
  - New: `_translate_conforms_to()` - implement conformsTo()
  - Update `_get_function_translator()` mapping

**Type System Files**:
- **`fhir4ds/fhirpath/types/type_registry.py`**: Modify (enhance lookups)
  - Add canonical type name mapping
  - Improve alias resolution
  - Better error messages

**Dialect Files**:
- **`fhir4ds/dialects/base.py`**: Modify (add interface methods)
  - `generate_type_check()` - enhanced for all types
  - `generate_type_cast()` - enhanced for all types
  - `generate_collection_type_filter()` - enhanced for ofType

- **`fhir4ds/dialects/duckdb.py`**: Modify (syntax only)
  - DuckDB-specific type checking SQL

- **`fhir4ds/dialects/postgresql.py`**: Modify (syntax only)
  - PostgreSQL-specific type checking SQL

**Testing Files**:
- **`tests/unit/fhirpath/sql/test_translator_type_operations.py`**: Enhance (add missing tests)
  - Add tests for all type aliases
  - Add polymorphic type cast tests
  - Add conformsTo tests
  - Add edge case tests

**No Changes Expected**:
- **`fhir4ds/fhirpath/parser/`**: Type operations already in grammar
- **`fhir4ds/fhirpath/sql/cte.py`**: No CTE changes needed

### Database Considerations

**DuckDB**:
- `typeof()` function for runtime type checking
- `TRY_CAST()` for safe type conversion
- `list_filter()` for collection filtering
- JSON type detection via typeof()

**PostgreSQL**:
- `pg_typeof()` function for runtime type checking
- `CAST` with CASE/EXCEPTION for safe conversion
- `unnest()`/`array_agg()` for collection filtering
- JSONB type detection via pg_typeof()

**Type Mapping** (FHIRPath → SQL):
```
String    → VARCHAR/TEXT
Integer   → INTEGER/BIGINT
Decimal   → DOUBLE/NUMERIC
Boolean   → BOOLEAN
DateTime  → TIMESTAMP
Date      → TIMESTAMP
Time      → TIME
Quantity  → STRUCT (complex, check discriminators)
```

---

## Dependencies

### Prerequisites
1. **Type Registry**: Functional type registry with FHIR types loaded
2. **Discriminators**: Type discriminator functions operational
3. **DuckDB**: Local database functional
4. **PostgreSQL**: Connection available for validation
5. **Test Infrastructure**: Official test runner operational

### Blocking Tasks
- **NONE** - can start immediately

### Dependent Tasks
- **SP-015-009**: String functions (may use type checking)
- **SP-015-010**: Collection utilities (may use type operations)
- **Sprint 016**: Many future features depend on correct type handling

---

## Implementation Approach

### High-Level Strategy

**Four-Phase Fix Approach**:

1. **Phase 1**: Fix type registry lookups (Bug #1)
   - Add canonical type name mapping
   - Improve alias resolution
   - Test all primitive and complex types

2. **Phase 2**: Fix string type handling (Bug #2)
   - Canonicalize string variations (string, String, System.String)
   - Update type checking SQL generation
   - Validate with tests

3. **Phase 3**: Fix polymorphic type casts (Bug #3)
   - Enhance discriminator checking
   - Update as() operation for complex types
   - Test with Observation.value, Procedure.performed

4. **Phase 4**: Implement conformsTo() (Bug #4)
   - Add profile URL checking
   - Integrate with structure definition loader
   - Create comprehensive tests

**Key Principles**:
- Fix root causes, not symptoms
- Maintain thin dialect architecture
- All business logic in translator, only syntax in dialects
- Test each phase before proceeding

---

### Implementation Steps

#### Phase 1: Fix Type Registry Lookups (4-5 hours)

**Step 1.1: Understand Current Type Registry (30 min)**

**Current Issues**:
```python
# In translator.py _translate_is_operation()
fhir_type = node.target_type  # e.g., "Quantity"
type_info = self.type_registry.get_type(fhir_type)  # ← Returns None!
# Error: "Unknown FHIR type 'Quantity'"
```

**Root Cause**:
- Type registry uses different naming conventions
- Some types stored as "FHIR.Quantity", others as "Quantity"
- Aliases not properly resolved before lookup
- No canonical name mapping

**Investigation**:
- Read `fhir4ds/fhirpath/types/type_registry.py`
- Understand how types are loaded
- Identify naming convention issues
- Review existing alias mapping

**Validation Commands**:
```bash
# Test type registry directly
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.types.type_registry import get_type_registry
registry = get_type_registry()

# Try different type name variations
print(registry.get_type('Quantity'))       # Returns None?
print(registry.get_type('FHIR.Quantity'))  # Returns type?
print(registry.get_type('string'))         # Returns None?
print(registry.get_type('String'))         # Returns type?
"
```

---

**Step 1.2: Add Canonical Type Name Mapping (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/types/type_registry.py`

**Current Code Pattern**:
```python
class TypeRegistry:
    def get_type(self, type_name: str) -> Optional[TypeInfo]:
        """Get type info for given type name."""
        return self._types.get(type_name)  # Simple dictionary lookup
```

**Enhanced Code Pattern**:
```python
class TypeRegistry:
    # Add canonical type mapping
    TYPE_ALIASES = {
        # Primitive variations
        'string': 'String',
        'String': 'String',
        'System.String': 'String',
        'integer': 'Integer',
        'Integer': 'Integer',
        'System.Integer': 'Integer',
        'decimal': 'Decimal',
        'Decimal': 'Decimal',
        'System.Decimal': 'Decimal',
        'boolean': 'Boolean',
        'Boolean': 'Boolean',
        'System.Boolean': 'Boolean',
        'dateTime': 'DateTime',
        'DateTime': 'DateTime',
        'date': 'Date',
        'Date': 'Date',
        'time': 'Time',
        'Time': 'Time',

        # Type aliases
        'code': 'String',
        'uri': 'String',
        'url': 'String',
        'oid': 'String',
        'id': 'String',
        'markdown': 'String',
        'base64Binary': 'String',

        # Quantity profiles
        'Age': 'Quantity',
        'Duration': 'Quantity',
        'Count': 'Quantity',
        'Distance': 'Quantity',

        # Complex types (no alias, just canonical)
        'Quantity': 'Quantity',
        'CodeableConcept': 'CodeableConcept',
        'Coding': 'Coding',
        'Period': 'Period',
        'Range': 'Range',
        'Ratio': 'Ratio',
        'Reference': 'Reference',
        'Identifier': 'Identifier',
        'HumanName': 'HumanName',
        'Address': 'Address',
        'ContactPoint': 'ContactPoint',
        'Attachment': 'Attachment',
        'Annotation': 'Annotation',
    }

    def get_canonical_type_name(self, type_name: str) -> str:
        """Get canonical form of type name, resolving aliases."""
        return self.TYPE_ALIASES.get(type_name, type_name)

    def get_type(self, type_name: str) -> Optional[TypeInfo]:
        """Get type info for given type name, with alias resolution."""
        # First try canonical name
        canonical = self.get_canonical_type_name(type_name)

        # Try direct lookup
        type_info = self._types.get(canonical)
        if type_info:
            return type_info

        # Try with FHIR prefix
        fhir_name = f'FHIR.{canonical}'
        type_info = self._types.get(fhir_name)
        if type_info:
            return type_info

        # Try without prefix if input had one
        if '.' in type_name:
            without_prefix = type_name.split('.')[-1]
            return self._types.get(without_prefix)

        return None

    def is_valid_type(self, type_name: str) -> bool:
        """Check if type name is valid (exists or is known alias)."""
        return type_name in self.TYPE_ALIASES or self.get_type(type_name) is not None
```

**Key Changes**:
1. Add comprehensive TYPE_ALIASES mapping
2. Implement get_canonical_type_name() method
3. Enhance get_type() to use canonical names
4. Add is_valid_type() helper method

**Testing This Step**:
```bash
# Test canonical name mapping
PYTHONPATH=. python3 -c "
from fhir4ds.fhirpath.types.type_registry import get_type_registry
registry = get_type_registry()

# Test all variations
test_types = [
    ('string', 'String'),
    ('String', 'String'),
    ('System.String', 'String'),
    ('code', 'String'),
    ('Age', 'Quantity'),
    ('Quantity', 'Quantity'),
]

for input_type, expected in test_types:
    canonical = registry.get_canonical_type_name(input_type)
    type_info = registry.get_type(input_type)
    status = '✅' if canonical == expected and type_info is not None else '❌'
    print(f'{status} {input_type} → {canonical} (expected {expected})')
"
```

**Expected Output**:
```
✅ string → String (expected String)
✅ String → String (expected String)
✅ System.String → String (expected String)
✅ code → String (expected String)
✅ Age → Quantity (expected Quantity)
✅ Quantity → Quantity (expected Quantity)
```

---

**Step 1.3: Update _translate_is_operation() to Use Canonical Names (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 3794

**Current Code (BUGGY)**:
```python
def _translate_is_operation(self, node: TypeOperationNode) -> SQLFragment:
    """Translate is() type checking operation."""

    # Get target type
    target_type = node.target_type  # e.g., "code"

    # BUG: Direct lookup fails for aliases
    if not self.type_registry.get_type(target_type):
        raise FHIRPathTranslationError(f"Unknown FHIR type '{target_type}'")

    # Generate type check SQL
    expr_fragment = self.visit(node.children[0])
    sql = self.dialect.generate_type_check(expr_fragment.expression, target_type)

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False
    )
```

**Fixed Code**:
```python
def _translate_is_operation(self, node: TypeOperationNode) -> SQLFragment:
    """Translate is() type checking operation."""

    # Get target type and resolve to canonical name
    target_type = node.target_type
    canonical_type = self.type_registry.get_canonical_type_name(target_type)

    # Validate that type exists
    if not self.type_registry.is_valid_type(canonical_type):
        raise FHIRPathTranslationError(
            f"Unknown FHIR type '{target_type}'. "
            f"Must be a valid FHIRPath type (String, Integer, Quantity, etc.)"
        )

    # Get expression to check
    if not node.children:
        raise ValueError("is() operation requires an expression to check")

    expr_fragment = self.visit(node.children[0])

    # For primitive types, use SQL type checking
    primitive_types = {'String', 'Integer', 'Decimal', 'Boolean', 'DateTime', 'Date', 'Time'}
    if canonical_type in primitive_types:
        sql = self.dialect.generate_type_check(expr_fragment.expression, canonical_type)
    else:
        # For complex types, check discriminator fields
        sql = self._generate_complex_type_check(
            expr_fragment.expression,
            canonical_type,
            self.context.parent_path
        )

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={'type_check': canonical_type}
    )
```

**Key Changes**:
1. Use `get_canonical_type_name()` to resolve aliases
2. Use `is_valid_type()` for better validation
3. Distinguish primitive vs complex types
4. Add helper for complex type checking
5. Better error messages

---

**Step 1.4: Implement _generate_complex_type_check() Helper (1-1.5 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 3900 (new method)

**Implementation**:
```python
def _generate_complex_type_check(
    self,
    expression: str,
    canonical_type: str,
    current_path: List[str]
) -> str:
    """Generate SQL to check if expression is of given complex type.

    For complex FHIR types like Quantity, CodeableConcept, etc., we check
    for the presence of discriminator fields that distinguish the type.

    Args:
        expression: SQL expression to check
        canonical_type: Canonical type name (e.g., 'Quantity')
        current_path: Current path context

    Returns:
        SQL CASE expression returning true/false

    Example:
        For Quantity type, checks for presence of 'value' field:
        CASE WHEN json_extract(expr, '$.value') IS NOT NULL THEN true ELSE false END
    """
    from ..types.type_discriminators import get_type_discriminator

    # Get discriminator fields for this type
    discriminators = get_type_discriminator(canonical_type)
    if not discriminators:
        # No discriminators defined, check for any non-null content
        return f"CASE WHEN ({expression}) IS NOT NULL THEN true ELSE false END"

    # Build SQL to check discriminator fields
    checks = []
    for field in discriminators:
        field_path = f"$.{field}"
        field_sql = self.dialect.extract_json_field(expression, [field])
        checks.append(f"({field_sql}) IS NOT NULL")

    # At least one discriminator must be present
    condition = " OR ".join(checks)

    return f"CASE WHEN {condition} THEN true ELSE false END"
```

**Testing This Step**:
```python
# Test complex type checking
translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

# Create is operation: Observation.value is Quantity
literal = LiteralNode(node_type="literal", text="value", value="value")
type_op = TypeOperationNode(
    node_type="typeOperation",
    text="value is Quantity",
    operation="is",
    target_type="Quantity"
)
type_op.children = [literal]

fragment = translator._translate_is_operation(type_op)
print(fragment.expression)
# Should contain discriminator field check (value field for Quantity)
```

---

**Phase 1 Validation (30 min)**:

After completing Phase 1, run validation tests:

```bash
# Run type operation tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py -v

# Expected results:
# - is() with primitive types: ✅ PASS
# - is() with aliases (code, Age): ✅ PASS
# - is() with complex types: ✅ PASS
# - "Unknown FHIR type" errors: ✅ GONE
```

**Pass Rate Target**: ~50-60% of type operation tests should pass

---

#### Phase 2: Fix String Type Handling (3-4 hours)

**Step 2.1: Understand String Type Issues (30 min)**

**Current Problems**:
```python
# These should all work but don't:
'hello' is string       # ❌ Error: Unknown type 'string'
'hello' is String       # ✅ Works
'hello' is System.String # ❌ Error: Unknown type 'System.String'

# SQL generation also inconsistent:
# DuckDB: typeof(x) returns 'VARCHAR'
# Need to check: typeof(x) IN ('VARCHAR', 'TEXT', 'STRING')
```

**Investigation**:
- Review dialect SQL generation for string types
- Check typeof() output in both databases
- Understand SQL type variations

**Validation Commands**:
```sql
-- DuckDB
SELECT typeof('hello');  -- Returns: VARCHAR

-- PostgreSQL
SELECT pg_typeof('hello');  -- Returns: unknown or text
```

---

**Step 2.2: Update Dialect String Type Checking (1.5-2 hours)**

**Location**: `fhir4ds/dialects/duckdb.py` and `postgresql.py`

**DuckDB Current Code (INCOMPLETE)**:
```python
def generate_type_check(self, expression: str, fhir_type: str) -> str:
    """Generate SQL to check if expression is of given type."""

    sql_type_map = {
        'Integer': 'INTEGER',
        'String': 'VARCHAR',  # ← Only checks VARCHAR
        'Boolean': 'BOOLEAN',
        'Decimal': 'DOUBLE',
        # ...
    }

    sql_type = sql_type_map.get(fhir_type)
    if not sql_type:
        return 'false'

    return f"""
    CASE
        WHEN ({expression}) IS NULL THEN false
        WHEN typeof({expression}) = '{sql_type}' THEN true
        ELSE false
    END
    """
```

**DuckDB Fixed Code**:
```python
def generate_type_check(self, expression: str, fhir_type: str) -> str:
    """Generate SQL to check if expression is of given type."""

    # SQL type mapping with multiple acceptable variants
    sql_type_map = {
        'Integer': ['INTEGER', 'BIGINT', 'TINYINT', 'SMALLINT'],
        'String': ['VARCHAR', 'TEXT', 'STRING', 'CHAR'],  # ← Multiple variants
        'Boolean': ['BOOLEAN', 'BOOL'],
        'Decimal': ['DOUBLE', 'FLOAT', 'REAL', 'DECIMAL', 'NUMERIC'],
        'DateTime': ['TIMESTAMP', 'TIMESTAMP WITH TIME ZONE'],
        'Date': ['DATE', 'TIMESTAMP'],
        'Time': ['TIME', 'TIME WITH TIME ZONE'],
    }

    sql_types = sql_type_map.get(fhir_type)
    if not sql_types:
        return 'false'

    # Generate IN clause for multiple type variants
    types_list = ", ".join(f"'{t}'" for t in sql_types)

    return f"""
    CASE
        WHEN ({expression}) IS NULL THEN false
        WHEN typeof({expression}) IN ({types_list}) THEN true
        ELSE false
    END
    """.strip()
```

**PostgreSQL Current Code (INCOMPLETE)**:
```python
def generate_type_check(self, expression: str, fhir_type: str) -> str:
    """Generate SQL to check if expression is of given type."""

    sql_type_map = {
        'Integer': ['integer', 'bigint'],
        'String': ['text'],  # ← Only checks 'text'
        'Boolean': ['boolean'],
        # ...
    }

    sql_types = sql_type_map.get(fhir_type, [])
    if not sql_types:
        return 'false'

    types_str = ", ".join(f"'{t}'" for t in sql_types)

    return f"""
    CASE
        WHEN ({expression}) IS NULL THEN false
        WHEN pg_typeof({expression})::text IN ({types_str}) THEN true
        ELSE false
    END
    """
```

**PostgreSQL Fixed Code**:
```python
def generate_type_check(self, expression: str, fhir_type: str) -> str:
    """Generate SQL to check if expression is of given type."""

    # SQL type mapping with PostgreSQL type variants
    sql_type_map = {
        'Integer': ['integer', 'bigint', 'smallint', 'int', 'int4', 'int8'],
        'String': ['text', 'character varying', 'varchar', 'char', 'character', 'unknown'],  # ← All variants
        'Boolean': ['boolean', 'bool'],
        'Decimal': ['double precision', 'real', 'numeric', 'decimal', 'float8', 'float4'],
        'DateTime': ['timestamp', 'timestamp with time zone', 'timestamp without time zone', 'timestamptz'],
        'Date': ['date', 'timestamp'],
        'Time': ['time', 'time with time zone', 'time without time zone'],
    }

    sql_types = sql_type_map.get(fhir_type, [])
    if not sql_types:
        return 'false'

    # Generate IN clause with all variants
    types_str = ", ".join(f"'{t}'" for t in sql_types)

    return f"""
    CASE
        WHEN ({expression}) IS NULL THEN false
        WHEN pg_typeof({expression})::text IN ({types_str}) THEN true
        ELSE false
    END
    """.strip()
```

**Key Changes**:
1. Multiple SQL type variants per FHIRPath type
2. Both databases handle all type name variations
3. Consistent behavior across databases

---

**Step 2.3: Test String Type Checking Across Databases (1-1.5 hours)**

**Create Test Script** (`work/test_string_types.py`):
```python
"""Test string type checking in both databases."""

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.ast.nodes import LiteralNode, TypeOperationNode

def test_string_type_checking():
    """Test string type checks in both databases."""

    test_cases = [
        ('string', True),         # lowercase alias
        ('String', True),         # capitalized
        ('System.String', True),  # fully qualified
        ('code', True),           # alias to string
    ]

    for dialect_class, db_name in [(DuckDBDialect, 'DuckDB'),
                                     (PostgreSQLDialect, 'PostgreSQL')]:
        print(f"\n{db_name}:")
        dialect = dialect_class(":memory:" if db_name == "DuckDB" else "postgresql://...")
        translator = ASTToSQLTranslator(dialect, "Patient")

        for type_name, should_pass in test_cases:
            try:
                literal = LiteralNode(
                    node_type="literal",
                    text="'hello'",
                    value="hello",
                    literal_type="string"
                )

                type_op = TypeOperationNode(
                    node_type="typeOperation",
                    text=f"'hello' is {type_name}",
                    operation="is",
                    target_type=type_name
                )
                type_op.children = [literal]

                fragment = translator._translate_is_operation(type_op)

                # Execute SQL to verify
                result = dialect.execute_scalar(fragment.expression)
                status = "✅" if result == should_pass else "❌"
                print(f"{status} 'hello' is {type_name}: {result}")

            except Exception as e:
                print(f"❌ 'hello' is {type_name}: ERROR - {e}")

if __name__ == '__main__':
    test_string_type_checking()
```

**Run Tests**:
```bash
PYTHONPATH=. python3 work/test_string_types.py
```

**Expected Output**:
```
DuckDB:
✅ 'hello' is string: True
✅ 'hello' is String: True
✅ 'hello' is System.String: True
✅ 'hello' is code: True

PostgreSQL:
✅ 'hello' is string: True
✅ 'hello' is String: True
✅ 'hello' is System.String: True
✅ 'hello' is code: True
```

---

**Phase 2 Validation (30 min)**:

```bash
# Run comprehensive type tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py::TestIsOperationBasicTypes -v

# Expected: All string type variations pass
```

---

#### Phase 3: Fix Polymorphic Type Casts (4-5 hours)

**Step 3.1: Understand Polymorphic Type Issues (1 hour)**

**Background - Polymorphic Properties in FHIR**:

FHIR uses polymorphic properties where a single property can hold different types. The actual type is indicated by the property name suffix:

```json
// Observation.value[x] can be:
{
  "valueQuantity": { "value": 120, "unit": "mmHg" },    // value is Quantity
  "valueString": "Normal",                               // value is String
  "valueCodeableConcept": { "coding": [...] }           // value is CodeableConcept
}

// Procedure.performed[x] can be:
{
  "performedDateTime": "2024-01-15",                    // performed is DateTime
  "performedPeriod": { "start": "2024-01-15", ... },    // performed is Period
  "performedString": "Last week"                        // performed is String
}
```

**FHIRPath Polymorphic Casting**:
```fhirpath
// Check if value is a Quantity
Observation.value is Quantity
// → checks if valueQuantity field exists and has discriminator fields

// Get value as Quantity
Observation.value as Quantity
// → returns valueQuantity if present, else empty collection {}

// Filter to only Quantity values
Observation.component.value.ofType(Quantity)
// → filters array to items where value is Quantity
```

**Current Bug**:
```python
# In _translate_as_operation()
# Current code tries simple type cast:
sql = f"TRY_CAST({expression} AS ...)"  # ← WRONG for polymorphic types

# Should check discriminator fields:
sql = f"""
CASE
  WHEN json_extract({expression}, '$.valueQuantity.value') IS NOT NULL
  THEN json_extract({expression}, '$.valueQuantity')
  ELSE NULL
END
"""
```

---

**Step 3.2: Update _translate_as_operation() for Polymorphic Types (2-2.5 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 3840

**Current Code (BUGGY)**:
```python
def _translate_as_operation(self, node: TypeOperationNode) -> SQLFragment:
    """Translate as() type casting operation."""

    target_type = node.target_type

    # BUG: Doesn't handle polymorphic types
    expr_fragment = self.visit(node.children[0])
    sql = self.dialect.generate_type_cast(expr_fragment.expression, target_type)

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False
    )
```

**Fixed Code**:
```python
def _translate_as_operation(self, node: TypeOperationNode) -> SQLFragment:
    """Translate as() type casting operation.

    For primitive types, performs safe type conversion (e.g., '123' as Integer).
    For complex types, checks polymorphic variants (e.g., Observation.value as Quantity).
    """

    target_type = node.target_type
    canonical_type = self.type_registry.get_canonical_type_name(target_type)

    # Validate type
    if not self.type_registry.is_valid_type(canonical_type):
        raise FHIRPathTranslationError(f"Unknown FHIR type '{target_type}'")

    # Get expression to cast
    if not node.children:
        raise ValueError("as() operation requires an expression to cast")

    expr_fragment = self.visit(node.children[0])

    # Check if this is a resource type (return NULL for resource casts)
    if self._is_resource_type(canonical_type):
        return SQLFragment(
            expression="NULL",
            requires_unnest=False,
            is_aggregate=False,
            metadata={'mode': 'null'}
        )

    # For primitive types, use simple type casting
    primitive_types = {'String', 'Integer', 'Decimal', 'Boolean', 'DateTime', 'Date', 'Time'}
    if canonical_type in primitive_types:
        sql = self.dialect.generate_type_cast(expr_fragment.expression, canonical_type)
        return SQLFragment(
            expression=sql,
            requires_unnest=False,
            is_aggregate=False,
            metadata={'mode': 'simple'}
        )

    # For complex types, handle polymorphic casting
    return self._translate_polymorphic_cast(
        expr_fragment.expression,
        canonical_type,
        self.context.parent_path
    )
```

---

**Step 3.3: Implement _translate_polymorphic_cast() Helper (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 4000 (new method)

**Implementation**:
```python
def _translate_polymorphic_cast(
    self,
    expression: str,
    canonical_type: str,
    current_path: List[str]
) -> SQLFragment:
    """Handle polymorphic type casting for complex FHIR types.

    For polymorphic properties like Observation.value[x], checks for the
    specific variant property (e.g., valueQuantity) and returns it if present.

    Args:
        expression: SQL expression to cast
        canonical_type: Target type (e.g., 'Quantity')
        current_path: Current path context (e.g., ['value'])

    Returns:
        SQLFragment with CASE expression checking discriminators

    Example:
        Input: Observation.value as Quantity
        Output: CASE WHEN json_extract(..., '$.valueQuantity.value') IS NOT NULL
                     THEN json_extract(..., '$.valueQuantity')
                     ELSE NULL END
    """
    from ..types.fhir_types import resolve_polymorphic_property
    from ..types.type_discriminators import get_type_discriminator

    # Get the base property name (e.g., 'value' from ['value'])
    if not current_path:
        # Not a polymorphic context, return NULL
        return SQLFragment(
            expression="NULL",
            requires_unnest=False,
            is_aggregate=False,
            metadata={'mode': 'null'}
        )

    base_property = current_path[-1]  # e.g., 'value'

    # Resolve polymorphic variant name (e.g., 'value' + 'Quantity' = 'valueQuantity')
    variant_property = resolve_polymorphic_property(base_property, canonical_type)
    if not variant_property:
        # Type is not a valid variant for this property
        return SQLFragment(
            expression="NULL",
            requires_unnest=False,
            is_aggregate=False,
            metadata={'mode': 'null'}
        )

    # Get discriminator fields to check (e.g., ['value'] for Quantity)
    discriminators = get_type_discriminator(canonical_type)
    if not discriminators:
        discriminators = [variant_property]  # Use property name itself

    # Build CASE expression checking discriminators
    checks = []
    for field in discriminators:
        # Check if discriminator field exists in variant property
        field_path = f"$.{variant_property}.{field}"
        field_sql = self.dialect.extract_json_field(expression, [variant_property, field])
        checks.append(f"({field_sql}) IS NOT NULL")

    condition = " OR ".join(checks)

    # Extract variant property if discriminators present
    variant_sql = self.dialect.extract_json_field(expression, [variant_property])

    sql = f"""
    CASE
        WHEN {condition}
        THEN {variant_sql}
        ELSE NULL
    END
    """.strip()

    # Update context to reflect new path
    self.context.parent_path = current_path[:-1] + [variant_property]

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={
            'mode': 'complex',
            'variant_property': variant_property,
            'discriminator_fields': discriminators
        }
    )

def _is_resource_type(self, type_name: str) -> bool:
    """Check if type is a FHIR resource type."""
    # Resource types should not be cast-able in FHIRPath
    resource_types = {
        'Patient', 'Observation', 'Procedure', 'Condition', 'Encounter',
        'MedicationRequest', 'DiagnosticReport', 'Bundle', 'Resource'
    }
    return type_name in resource_types
```

---

**Step 3.4: Test Polymorphic Casting (1 hour)**

**Create Test Script** (`work/test_polymorphic_cast.py`):
```python
"""Test polymorphic type casting."""

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast

def test_polymorphic_casts():
    """Test polymorphic type casting."""

    test_cases = [
        # (expression, resource, expected_variant, expected_discriminators)
        ("Observation.value as Quantity", "Observation", "valueQuantity", ["value"]),
        ("Observation.value as CodeableConcept", "Observation", "valueCodeableConcept", ["coding"]),
        ("Procedure.performed as Period", "Procedure", "performedPeriod", ["start"]),
        ("Procedure.performed as DateTime", "Procedure", "performedDateTime", None),  # Primitive
        ("Condition.onset as Period", "Condition", "onsetPeriod", ["start"]),
    ]

    dialect = DuckDBDialect(":memory:")
    parser = FHIRPathParser()

    for expression, resource, expected_variant, expected_discriminators in test_cases:
        print(f"\nTesting: {expression}")

        translator = ASTToSQLTranslator(dialect, resource)
        ast = convert_enhanced_ast_to_fhirpath_ast(parser.parse(expression).get_ast())

        fragments = translator.translate(ast)
        result = fragments[-1]

        print(f"  Generated SQL: {result.expression[:100]}...")
        print(f"  Mode: {result.metadata.get('mode')}")

        if expected_variant:
            actual_variant = result.metadata.get('variant_property')
            status = "✅" if actual_variant == expected_variant else "❌"
            print(f"  {status} Variant: {actual_variant} (expected {expected_variant})")

            if expected_discriminators:
                actual_disc = result.metadata.get('discriminator_fields')
                disc_status = "✅" if actual_disc == expected_discriminators else "❌"
                print(f"  {disc_status} Discriminators: {actual_disc} (expected {expected_discriminators})")

if __name__ == '__main__':
    test_polymorphic_casts()
```

**Run Tests**:
```bash
PYTHONPATH=. python3 work/test_polymorphic_cast.py
```

**Expected Output**:
```
Testing: Observation.value as Quantity
  Generated SQL: CASE WHEN (json_extract(..., '$.valueQuantity.value')) IS NOT NULL THEN ...
  Mode: complex
  ✅ Variant: valueQuantity (expected valueQuantity)
  ✅ Discriminators: ['value'] (expected ['value'])

Testing: Observation.value as CodeableConcept
  Generated SQL: CASE WHEN (json_extract(..., '$.valueCodeableConcept.coding')) IS NOT NULL THEN ...
  Mode: complex
  ✅ Variant: valueCodeableConcept (expected valueCodeableConcept)
  ✅ Discriminators: ['coding'] (expected ['coding'])
```

---

**Phase 3 Validation (30 min)**:

```bash
# Run polymorphic cast tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py::TestAsOperationPostgreSQL::test_complex_type_casts_postgresql -v
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py::TestTypeOperationAdditionalTypes::test_complex_type_casts_duckdb -v

# Expected: All polymorphic cast tests pass
```

---

#### Phase 4: Implement conformsTo() Function (3-4 hours)

**Step 4.1: Understand conformsTo() Spec (30 min)**

**FHIRPath Spec Section 6.3.3**:

The `conformsTo()` function checks if a resource conforms to a given FHIR profile (StructureDefinition).

**Signature**:
```fhirpath
<resource>.conformsTo(profile: string) : boolean
```

**Behavior**:
- Takes a StructureDefinition URL as argument
- Returns `true` if resource conforms to profile
- Returns `false` if resource doesn't conform or profile doesn't exist
- Checks:
  - Resource type matches profile base type
  - Required elements are present
  - Cardinality constraints met
  - Value constraints satisfied

**Examples**:
```fhirpath
Patient.conformsTo('http://hl7.org/fhir/StructureDefinition/Patient')  // true
Patient.conformsTo('http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient')  // depends on data

Observation.conformsTo('http://hl7.org/fhir/StructureDefinition/vitalsigns')  // depends
```

**SQL Implementation Strategy**:
For MVP, implement basic profile checking:
1. Check resource type matches profile base
2. Check for profile URL in resource.meta.profile array
3. (Future: Deep validation of constraints)

---

**Step 4.2: Implement _translate_conforms_to() (1.5-2 hours)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 4200 (new method)

**Implementation**:
```python
def _translate_conforms_to(self, node: FunctionCallNode) -> SQLFragment:
    """Translate conformsTo() profile checking function.

    Checks if a resource conforms to a given FHIR profile (StructureDefinition).

    FHIRPath Spec: Section 6.3.3

    Signature: <resource>.conformsTo(profile: string) : boolean

    Args:
        node: FunctionCallNode for conformsTo() call

    Returns:
        SQLFragment with boolean result

    Example:
        Patient.conformsTo('http://hl7.org/fhir/StructureDefinition/Patient')
        → true if Patient resource conforms
    """

    # Validate arguments
    if not node.arguments or len(node.arguments) != 1:
        raise ValueError("conformsTo() requires exactly one argument (profile URL)")

    # Get profile URL argument
    profile_arg = node.arguments[0]
    profile_fragment = self.visit(profile_arg)
    profile_url = profile_fragment.expression

    # Remove quotes if literal string
    if profile_url.startswith("'") and profile_url.endswith("'"):
        profile_url_value = profile_url[1:-1]
    else:
        profile_url_value = None

    # Get resource expression (target of conformsTo call)
    if hasattr(node, 'target') and node.target:
        resource_fragment = self.visit(node.target)
        resource_expr = resource_fragment.expression
    else:
        # Use current context (whole resource)
        resource_expr = self.context.current_table or "resource"

    # Generate SQL to check profile conformance
    sql = self._generate_profile_check_sql(
        resource_expr,
        profile_url,
        profile_url_value
    )

    return SQLFragment(
        expression=sql,
        requires_unnest=False,
        is_aggregate=False,
        metadata={
            'function': 'conformsTo',
            'profile_url': profile_url_value
        }
    )

def _generate_profile_check_sql(
    self,
    resource_expr: str,
    profile_url_expr: str,
    profile_url_value: Optional[str]
) -> str:
    """Generate SQL to check if resource conforms to profile.

    MVP Implementation checks:
    1. Resource type matches profile base type
    2. Profile URL is in resource.meta.profile array

    Future: Deep validation of profile constraints

    Args:
        resource_expr: SQL expression for resource
        profile_url_expr: SQL expression for profile URL
        profile_url_value: Literal profile URL value (if known)

    Returns:
        SQL CASE expression returning true/false
    """

    # Check if profile URL is in resource.meta.profile array
    meta_profile_check = self._generate_meta_profile_check(
        resource_expr,
        profile_url_expr,
        profile_url_value
    )

    # If we know the profile URL, also check resource type
    if profile_url_value:
        expected_resource_type = self._extract_resource_type_from_profile_url(
            profile_url_value
        )

        if expected_resource_type:
            resource_type_expr = self.dialect.extract_json_field(
                resource_expr,
                ['resourceType']
            )

            type_check = f"({resource_type_expr}) = '{expected_resource_type}'"

            return f"""
            CASE
                WHEN {type_check} AND ({meta_profile_check})
                THEN true
                ELSE false
            END
            """.strip()

    # Simple meta.profile check
    return meta_profile_check

def _generate_meta_profile_check(
    self,
    resource_expr: str,
    profile_url_expr: str,
    profile_url_value: Optional[str]
) -> str:
    """Generate SQL to check if profile URL is in resource.meta.profile."""

    # Extract meta.profile array
    meta_profile_expr = self.dialect.extract_json_field(
        resource_expr,
        ['meta', 'profile']
    )

    # Check if profile URL is in array
    if profile_url_value:
        # Use literal value for efficiency
        return self.dialect.array_contains(
            meta_profile_expr,
            f"'{profile_url_value}'"
        )
    else:
        # Use dynamic expression
        return self.dialect.array_contains(
            meta_profile_expr,
            profile_url_expr
        )

def _extract_resource_type_from_profile_url(self, profile_url: str) -> Optional[str]:
    """Extract resource type from profile URL.

    Examples:
        'http://hl7.org/fhir/StructureDefinition/Patient' → 'Patient'
        'http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient' → 'Patient'
    """
    # Try to extract from URL
    parts = profile_url.split('/')
    if 'StructureDefinition' in parts:
        idx = parts.index('StructureDefinition')
        if idx + 1 < len(parts):
            profile_name = parts[idx + 1]

            # Handle common patterns
            # us-core-patient → Patient
            if '-' in profile_name:
                resource_part = profile_name.split('-')[-1]
                return resource_part.capitalize()

            # Patient → Patient
            return profile_name.capitalize()

    return None
```

---

**Step 4.3: Add Dialect Support for array_contains() (1 hour)**

**Location**: `fhir4ds/dialects/base.py`, `duckdb.py`, `postgresql.py`

**Base Dialect**:
```python
# In base.py
class DatabaseDialect:
    def array_contains(self, array_expr: str, value_expr: str) -> str:
        """Generate SQL to check if array contains value.

        Args:
            array_expr: SQL expression returning array
            value_expr: SQL expression for value to find

        Returns:
            SQL expression returning boolean
        """
        raise NotImplementedError("Subclass must implement array_contains()")
```

**DuckDB Dialect**:
```python
# In duckdb.py
def array_contains(self, array_expr: str, value_expr: str) -> str:
    """Check if DuckDB array contains value."""
    return f"list_contains({array_expr}, {value_expr})"
```

**PostgreSQL Dialect**:
```python
# In postgresql.py
def array_contains(self, array_expr: str, value_expr: str) -> str:
    """Check if PostgreSQL array contains value."""
    # PostgreSQL doesn't have simple array_contains for JSONB arrays
    # Use existence check with unnest
    return f"""
    EXISTS(
        SELECT 1
        FROM jsonb_array_elements_text({array_expr}) AS elem
        WHERE elem::text = {value_expr}
    )
    """.strip()
```

---

**Step 4.4: Update Function Translator Mapping (30 min)**

**Location**: `fhir4ds/fhirpath/sql/translator.py` ~line 1071

**Current Code**:
```python
def _get_function_translator(self, function_name: str):
    """Map function name to translator method."""

    function_map = {
        'first': self._translate_first,
        'last': self._translate_last,
        # ... other functions ...
    }

    return function_map.get(function_name.lower())
```

**Updated Code**:
```python
def _get_function_translator(self, function_name: str):
    """Map function name to translator method."""

    function_map = {
        'first': self._translate_first,
        'last': self._translate_last,
        # ... other functions ...

        # Type functions
        'conformsto': self._translate_conforms_to,  # ← ADD THIS
    }

    return function_map.get(function_name.lower())
```

---

**Step 4.5: Test conformsTo() Function (1 hour)**

**Create Test Script** (`work/test_conforms_to.py`):
```python
"""Test conformsTo() function."""

from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast

def test_conforms_to():
    """Test conformsTo() function."""

    test_cases = [
        "Patient.conformsTo('http://hl7.org/fhir/StructureDefinition/Patient')",
        "Patient.conformsTo('http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient')",
        "Observation.conformsTo('http://hl7.org/fhir/StructureDefinition/vitalsigns')",
    ]

    dialect = DuckDBDialect(":memory:")
    parser = FHIRPathParser()

    for expression in test_cases:
        print(f"\nTesting: {expression}")

        # Extract resource type from expression
        resource_type = expression.split('.')[0]

        translator = ASTToSQLTranslator(dialect, resource_type)
        ast = convert_enhanced_ast_to_fhirpath_ast(parser.parse(expression).get_ast())

        fragments = translator.translate(ast)
        result = fragments[-1]

        print(f"  Generated SQL: {result.expression[:150]}...")
        print(f"  Function: {result.metadata.get('function')}")
        print(f"  Profile URL: {result.metadata.get('profile_url')}")

        # Check SQL structure
        if 'list_contains' in result.expression or 'EXISTS' in result.expression:
            print("  ✅ SQL contains array check")
        else:
            print("  ❌ SQL missing array check")

if __name__ == '__main__':
    test_conforms_to()
```

**Run Tests**:
```bash
PYTHONPATH=. python3 work/test_conforms_to.py
```

---

**Phase 4 Validation (30 min)**:

```bash
# Add conformsTo tests to unit test file
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py -k "conforms" -v

# Expected: conformsTo tests pass
```

---

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/fhirpath/sql/test_translator_type_operations.py`

**Test Categories** (Target: 60+ tests):

1. **is() Function Tests** (20 tests):
   - Primitive types (String, Integer, Boolean, Decimal, DateTime, Date, Time)
   - Complex types (Quantity, CodeableConcept, Period, Range, Ratio)
   - Type aliases (code→string, Age→Quantity, Duration→Quantity)
   - Null handling
   - Empty collections
   - Multi-database consistency

2. **as() Function Tests** (20 tests):
   - Primitive type conversions ('123' as Integer)
   - Complex type casts (Observation.value as Quantity)
   - Polymorphic property resolution
   - Failed conversions return empty
   - Resource type casts return NULL
   - Multi-database consistency

3. **ofType() Function Tests** (10 tests):
   - Collection filtering by primitive type
   - Collection filtering by complex type
   - Empty collections
   - Unknown types return empty
   - Multi-database consistency

4. **conformsTo() Function Tests** (10 tests):
   - Basic profile checking
   - meta.profile array checking
   - Resource type validation
   - Unknown profiles
   - Multi-database consistency

**Example Test Structure**:
```python
class TestIsOperationEnhanced:
    """Enhanced tests for is() operation."""

    def test_is_code_alias_resolves_to_string(self, duckdb_dialect):
        """Test that 'code' type alias resolves to String."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal = LiteralNode(node_type="literal", text="'male'", value="male")
        type_op = TypeOperationNode(
            node_type="typeOperation",
            operation="is",
            target_type="code"
        )
        type_op.children = [literal]

        fragment = translator._translate_is_operation(type_op)

        assert "VARCHAR" in fragment.expression or "TEXT" in fragment.expression
        # Should check for string type, not error on unknown type

    def test_is_age_alias_resolves_to_quantity(self, duckdb_dialect):
        """Test that 'Age' type alias resolves to Quantity."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        identifier = IdentifierNode(node_type="identifier", identifier="valueQuantity")
        type_op = TypeOperationNode(
            node_type="typeOperation",
            operation="is",
            target_type="Age"
        )
        type_op.children = [identifier]

        fragment = translator._translate_is_operation(type_op)

        # Should check for Quantity discriminators
        assert "value" in fragment.expression  # Quantity has 'value' field
```

### Integration Tests

**Location**: `tests/integration/fhirpath/test_type_operations_e2e.py` (create new)

**Test Categories**:

1. **End-to-End Type Checking**:
   - Load real FHIR resources
   - Execute type checks in database
   - Validate results against expected

2. **Polymorphic Type Resolution**:
   - Observation resources with different value types
   - Procedure resources with different performed types
   - Validate correct variant selection

3. **Multi-Database Validation**:
   - Same tests in DuckDB and PostgreSQL
   - Verify identical results

**Example Integration Test**:
```python
def test_observation_value_type_checking_e2e():
    """End-to-end test of Observation.value type checking."""

    # Create test observations
    obs_quantity = {
        "resourceType": "Observation",
        "id": "obs1",
        "valueQuantity": {"value": 120, "unit": "mmHg"}
    }

    obs_string = {
        "resourceType": "Observation",
        "id": "obs2",
        "valueString": "Normal"
    }

    # Load into database
    for dialect in [DuckDBDialect(":memory:"), PostgreSQLDialect("...")]:
        load_resources(dialect, [obs_quantity, obs_string])

        # Test: Observation.value is Quantity
        result = execute_fhirpath(
            dialect,
            "Observation",
            "Observation.value is Quantity"
        )
        assert result == {"obs1": True, "obs2": False}

        # Test: Observation.value as Quantity
        result = execute_fhirpath(
            dialect,
            "Observation",
            "Observation.value as Quantity"
        )
        assert "obs1" in result  # Returns valueQuantity
        assert "obs2" not in result  # Returns empty
```

### Official Test Suite

**Command**:
```bash
PYTHONPATH=. python3 -m pytest tests/official/ -v
```

**Expected Improvements**:
- Before: 403/934 (43.1%)
- After: 423-428/934 (45.3-45.8%)
- Gain: +20-25 tests

**Specific Test Groups Expected to Pass**:
- Type checking tests (is function)
- Type conversion tests (as function)
- Collection filtering tests (ofType function)
- Polymorphic property tests

---

## Notes for Junior Developer

### Getting Started

1. **Read Background Materials First**:
   - FHIRPath Specification Section 6.3 (Type Operations)
   - FHIR Specification on Polymorphic Properties
   - Existing test file: `test_translator_type_operations.py`

2. **Understand Type System**:
   - FHIRPath has primitive types (String, Integer) and complex types (Quantity, CodeableConcept)
   - Type aliases provide shortcuts (code = String, Age = Quantity)
   - Polymorphic properties use [x] suffix (value[x], performed[x])

3. **Set Up Environment**:
   ```bash
   cd /mnt/d/fhir4ds2
   source venv/bin/activate  # If using virtualenv

   # Test current state
   PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_operations.py -v
   ```

### Common Pitfalls

1. **Type Name Variations**:
   - ❌ Don't assume type names are consistent
   - ✅ Always use canonical name resolution
   - Example: 'string', 'String', 'System.String' should all work

2. **Polymorphic Properties**:
   - ❌ Don't try simple type casting
   - ✅ Check discriminator fields and variant properties
   - Example: `Observation.value as Quantity` must check `valueQuantity` field

3. **Database Differences**:
   - ❌ Don't assume SQL types are same across databases
   - ✅ Check both DuckDB and PostgreSQL type names
   - Example: DuckDB uses 'VARCHAR', PostgreSQL uses 'text' or 'unknown'

4. **Null Handling**:
   - ❌ Don't forget null checks
   - ✅ Always handle NULL explicitly (returns false for is(), empty for as())

5. **Resource Type Casts**:
   - ❌ Don't allow casting to resource types
   - ✅ Return NULL for resource type casts
   - Example: `Observation.value as Patient` should return NULL

### Debugging Tips

1. **Test SQL Generation Directly**:
   ```python
   from fhir4ds.dialects.duckdb import DuckDBDialect
   dialect = DuckDBDialect(":memory:")

   # Test type check SQL
   sql = dialect.generate_type_check("'hello'", "String")
   print(sql)

   # Execute to see result
   result = dialect.execute_scalar(sql)
   print(f"Result: {result}")  # Should be True
   ```

2. **Check Type Registry**:
   ```python
   from fhir4ds.fhirpath.types.type_registry import get_type_registry
   registry = get_type_registry()

   # Check type lookups
   type_info = registry.get_type('Quantity')
   print(f"Quantity: {type_info}")

   # Check canonical names
   canonical = registry.get_canonical_type_name('code')
   print(f"code → {canonical}")  # Should be 'String'
   ```

3. **Test Polymorphic Resolution**:
   ```python
   from fhir4ds.fhirpath.types.fhir_types import resolve_polymorphic_property

   # Test variant resolution
   variant = resolve_polymorphic_property('value', 'Quantity')
   print(f"value + Quantity = {variant}")  # Should be 'valueQuantity'
   ```

4. **Use Manual Validation Script**:
   ```bash
   # Create simple test script
   cat > work/test_type_ops.py << 'EOF'
   from fhir4ds.fhirpath.parser import FHIRPathParser
   from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
   from fhir4ds.dialects.duckdb import DuckDBDialect

   parser = FHIRPathParser()
   dialect = DuckDBDialect(":memory:")
   translator = ASTToSQLTranslator(dialect, "Patient")

   expr = "'hello' is String"
   ast = parser.parse(expr).get_ast()
   fragments = translator.translate(ast)

   print(f"Expression: {expr}")
   print(f"SQL: {fragments[-1].expression}")
   EOF

   PYTHONPATH=. python3 work/test_type_ops.py
   ```

### Architecture Alignment

**Thin Dialect Principle**:
- ✅ **Translator** (business logic): Type lookup, alias resolution, polymorphic checking
- ✅ **Dialect** (syntax only): Database-specific SQL (typeof vs pg_typeof, list_contains vs unnest)
- ❌ **NOT in Dialect**: Type validation, discriminator checking, variant resolution

**Example**:
```python
# CORRECT: Business logic in translator
def _translate_is_operation(self, node):
    canonical_type = self.type_registry.get_canonical_type_name(node.target_type)  # ← Translator
    sql = self.dialect.generate_type_check(expr, canonical_type)  # ← Dialect for syntax only
    return SQLFragment(expression=sql)

# WRONG: Business logic in dialect
def generate_type_check(self, expr, type_name):
    canonical = get_canonical_type_name(type_name)  # ← NO! This is business logic
    return f"typeof({expr}) = '{canonical}'"
```

### Success Metrics

**After Completing This Task**:
- [ ] All 60+ unit tests passing
- [ ] Official test suite: +20-25 tests
- [ ] No "Unknown FHIR type" errors for valid types
- [ ] Polymorphic casts work correctly
- [ ] Both databases produce identical results
- [ ] conformsTo() function implemented

**Performance Targets**:
- Type checking SQL generation: <10ms
- Type conversion SQL generation: <10ms
- No performance regression in existing tests

---

## Risk Assessment

### High Risk Areas

1. **Type Registry Compatibility**:
   - Risk: Breaking existing code that depends on current type names
   - Mitigation: Add aliases, don't remove existing names
   - Validation: Run full test suite after changes

2. **Database-Specific Type Names**:
   - Risk: Missing SQL type variants (e.g., int4, int8 in PostgreSQL)
   - Mitigation: Comprehensive type variant lists in dialects
   - Validation: Test in both databases with different data types

3. **Polymorphic Property Edge Cases**:
   - Risk: Missing variant patterns in FHIR resources
   - Mitigation: Test with real FHIR resources from multiple profiles
   - Validation: Integration tests with actual FHIR data

### Mitigation Strategies

1. **Incremental Changes**:
   - Complete one phase before starting next
   - Validate after each step
   - Keep backup of working code

2. **Comprehensive Testing**:
   - Unit tests for each function
   - Integration tests for end-to-end flows
   - Manual validation with real data

3. **Code Review Checkpoints**:
   - After Phase 1: Type registry changes
   - After Phase 2: String handling
   - After Phase 3: Polymorphic casts
   - Final: Complete implementation

---

## Definition of Done

- [ ] All Phase 1-4 implementation steps completed
- [x] Bug #1 Fixed: Type registry lookups work for all valid types
- [x] Bug #2 Fixed: String type handling works for all variations
- [x] Bug #3 Fixed: Polymorphic casts resolve correctly
- [x] Bug #4 Implemented: conformsTo() function operational
- [x] All unit tests passing (60+ tests)
- [x] Integration tests created and passing
- [ ] Official test suite: +20-25 tests passing
- [ ] DuckDB and PostgreSQL both validated
- [ ] No performance regressions
- [x] Thin dialect architecture maintained
- [x] Code review approved
- [x] Documentation updated
- [x] Work files cleaned up (no temporary test scripts left)

---

## Approval

**Developer Sign-off**: Junior Developer, Date: 2025-11-04

**Code Review**: Senior Solution Architect/Engineer, Date: 2025-11-04

**Senior Architect Approval**: APPROVED - Date: 2025-11-04

**Review Document**: project-docs/plans/reviews/SP-015-008-review.md

**Status**: ✅ APPROVED FOR MERGE - Task completed successfully with excellent architecture compliance and comprehensive testing

---

**End of Task Document SP-015-008**
