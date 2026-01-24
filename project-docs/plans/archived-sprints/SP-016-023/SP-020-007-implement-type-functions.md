# Task: Implement FHIRPath Type Functions

**Task ID**: SP-020-007
**Sprint**: 020
**Task Name**: Implement FHIRPath Type Functions for SQL Translator
**Assignee**: Junior Developer
**Created**: 2025-11-18
**Last Updated**: 2025-11-18
**Priority**: High (Second Highest Impact - Would improve compliance from 42.4% to ~52%)
**Estimated Effort**: 60-80 hours (1.5-2 weeks)

---

## Task Overview

### Description

Implement the missing FHIRPath type functions in the SQL translator to improve specification compliance. This task addresses the **second largest gap** in FHIRPath compliance, with 88 of 116 type function tests currently failing.

**Current State**: 28/116 tests passing (24.1%)
**Target State**: 100+/116 tests passing (85%+)
**Impact**: +9-10% overall FHIRPath compliance (second biggest single improvement)

**Key Functions to Implement**:
1. `.is()` - Check if value is of specified type
2. `.as()` - Cast value to specified type
3. `.ofType()` - Filter collection by type (enhance existing)
4. `.conformsTo()` - Check profile conformance
5. `.hasValue()` - Check if value exists
6. `.toInteger()`, `.toDecimal()`, `.toString()`, `.toBoolean()` - Type conversions
7. `.toDate()`, `.toDateTime()`, `.toTime()` - Temporal conversions
8. `.convertsToInteger()`, `.convertsToDecimal()`, etc. - Test if convertible

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
- [x] High (Important for sprint success - SECOND HIGHEST IMPACT)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **`.is()` Function - Type Checking**
   - Check if value is exactly of specified type (not subtype)
   - Example: `Patient.gender.is(string)` → true
   - Example: `Observation.value.is(Quantity)` → true if value is Quantity
   - Must support all FHIR primitive and complex types
   - Must work with polymorphic elements (e.g., `value[x]`)

2. **`.as()` Function - Type Casting**
   - Cast value to specified type if possible, otherwise return empty
   - Example: `Observation.value.as(Quantity).value` → numeric value
   - Example: `Observation.value.as(string)` → empty if value is Quantity
   - Must perform safe casting with validation
   - Must return empty (not error) for invalid casts

3. **`.ofType()` Function Enhancement** (partial - extend from SP-020-006)
   - Filter collection to elements of specified type
   - Support type hierarchy (subtypes match)
   - Example: `Bundle.entry.resource.ofType(DomainResource)` → all domain resources
   - Must handle polymorphic elements correctly

4. **`.hasValue()` Function**
   - Check if element has actual value (not just exists)
   - Example: `Patient.active.hasValue()` → true if active field has boolean value
   - Must distinguish between null, empty string, and missing

5. **Type Conversion Functions**
   - `.toInteger()`: Convert to integer if possible
   - `.toDecimal()`: Convert to decimal number
   - `.toString()`: Convert to string representation
   - `.toBoolean()`: Convert to boolean
   - `.toDate()`, `.toDateTime()`, `.toTime()`: Temporal conversions
   - Must return empty for unconvertible values

6. **Conversion Test Functions**
   - `.convertsToInteger()`, `.convertsToDecimal()`, `.convertsToString()`, `.convertsToBoolean()`
   - `.convertsToDate()`, `.convertsToDateTime()`, `.convertsToTime()`
   - Test if value can be converted without performing conversion
   - Example: `'123'.convertsToInteger()` → true
   - Example: `'abc'.convertsToInteger()` → false

7. **`.conformsTo()` Function** (Future/Deferred)
   - Check if resource conforms to specified profile
   - Requires StructureDefinition support
   - May defer to future sprint if too complex

### Non-Functional Requirements

- **Performance**: Type checks must be fast (<10ms per operation)
- **Compliance**: Target 85%+ on FHIRPath type function tests (100+/116)
- **Database Support**: Must work identically on DuckDB and PostgreSQL
- **Error Handling**: Return empty (not error) for invalid type operations
- **Type Safety**: Integrate with TypeRegistry for FHIR type validation

### Acceptance Criteria

- [ ] `.is()` function: All 20+ official tests passing
- [ ] `.as()` function: All 20+ official tests passing
- [ ] `.hasValue()` function: All 8+ official tests passing
- [ ] Type conversion functions: All 30+ official tests passing
- [ ] Conversion test functions: All 20+ official tests passing
- [ ] Overall type functions: 100+/116 tests passing (85%+)
- [ ] Zero regressions in existing translator tests
- [ ] Both DuckDB and PostgreSQL support validated
- [ ] Performance: <50ms average per type function test

---

## Technical Specifications

### Affected Components

- **FHIRPath SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): Core implementation
- **Type Registry** (`fhir4ds/fhirpath/types/type_registry.py`): FHIR type system integration
- **Dialect Classes** (`fhir4ds/dialects/`): Database-specific type checking/casting
- **Type Converter** (`fhir4ds/fhirpath/types/type_converter.py`): Type conversion logic

### File Modifications

- **`fhir4ds/fhirpath/sql/translator.py`**: Add ~1,000-1,500 lines
  - `_translate_is()` - new method (~150 lines)
  - `_translate_as()` - new method (~200 lines)
  - `_translate_hasvalue()` - new method (~100 lines)
  - `_translate_tointeger()`, `_translate_todecimal()`, etc. - new methods (~300 lines)
  - `_translate_convertstointeger()`, etc. - new methods (~250 lines)
  - Helper methods for type validation (~200 lines)

- **`fhir4ds/fhirpath/types/type_registry.py`**: Enhance existing
  - Add type hierarchy navigation (~100 lines)
  - Add primitive type validation (~150 lines)
  - Add conversion validation (~100 lines)

- **`fhir4ds/dialects/duckdb.py`**: Add dialect-specific SQL (~150 lines)
  - Type checking expressions
  - Type conversion functions

- **`fhir4ds/dialects/postgresql.py`**: Add dialect-specific SQL (~150 lines)
  - JSONB type checking
  - Type conversion with PostgreSQL functions

- **`tests/unit/fhirpath/sql/test_translator_type_functions.py`**: New test file (~600 lines)
  - Comprehensive unit tests for all type functions
  - Type hierarchy testing
  - Multi-database validation

### Database Considerations

**DuckDB**:
- Use `typeof()` for type checking
- Use `TRY_CAST()` for safe conversions
- Use `json_type()` for JSON element types

**PostgreSQL**:
- Use `jsonb_typeof()` for type checking
- Use type-specific extraction functions for conversions
- Use pattern matching for string conversions

**Type Mapping**:
```
FHIR Type → Database Type
string → text/varchar
integer → bigint
decimal → numeric/decimal
boolean → boolean
date → date
dateTime → timestamp
Quantity → jsonb (complex type)
```

---

## Dependencies

### Prerequisites

1. **Type Registry**: FHIR type system (SP-012-013) ✅
2. **Parser Support**: Type name parsing ✅
3. **SP-020-005 Complete**: Compositional function pattern ✅
4. **SP-020-006 Helpful**: `.ofType()` foundation (can proceed in parallel)

### Blocking Tasks

None - can start immediately (parallel with SP-020-006)

### Dependent Tasks

- **CQL Type Operations**: CQL uses extensive type checking
- **SQL-on-FHIR**: Type conversions in column definitions
- **Quality Measures**: Type checks for safety

---

## Implementation Approach

### High-Level Strategy

**Approach**: Implement type functions leveraging TypeRegistry for FHIR type semantics, using database-native type operations where possible.

**Key Architectural Principles**:
1. **Type Registry Integration**: Use TypeRegistry for all FHIR type information
2. **Safe Conversions**: Return empty for failed conversions (no errors)
3. **Thin Dialects**: Database differences only in SQL syntax
4. **Performance**: Use database-native type checking where possible
5. **Spec Compliance**: Follow FHIRPath type semantics exactly

**Implementation Order** (by dependency):
1. Foundation: `.hasValue()`, `.is()` (simple, no dependencies)
2. Core: Type conversion functions (`.toInteger()`, `.toString()`, etc.)
3. Advanced: Conversion test functions (`.convertsToInteger()`, etc.)
4. Complex: `.as()` casting with validation
5. Defer: `.conformsTo()` (requires StructureDefinition support)

### Implementation Steps

#### Step 1: Implement `.hasValue()` and `.is()` Functions (12-16 hours)

**Activities**:
- Implement `_translate_hasvalue(node)` method
  - Check if field exists and has non-null, non-empty value
  - Distinguish null, empty string, and missing field
  - Use database-specific null/empty checks

- Implement `_translate_is(node)` method
  - Extract type name from argument
  - Validate type with TypeRegistry
  - Generate type checking SQL
  - Handle primitives vs complex types differently

**Example SQL Generation**:
```sql
-- DuckDB: Patient.active.hasValue()
(json_extract(resource, '$.active') IS NOT NULL
 AND json_extract(resource, '$.active') != ''
 AND json_type(json_extract(resource, '$.active')) != 'NULL')

-- PostgreSQL: Patient.gender.is(string)
(jsonb_typeof(resource->'gender') = 'string')

-- DuckDB: Observation.value.is(Quantity)
(json_type(json_extract(resource, '$.value')) = 'OBJECT'
 AND json_extract_string(json_extract(resource, '$.value'), '$.unit') IS NOT NULL)
```

**Validation**:
- Run: `pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -k "hasvalue or is_type"`
- Expect: 28+ tests passing
- Test all primitive types and key complex types

**Time**: 12-16 hours

---

#### Step 2: Implement Type Conversion Functions (16-20 hours)

**Functions**: `.toInteger()`, `.toDecimal()`, `.toString()`, `.toBoolean()`, `.toDate()`, `.toDateTime()`, `.toTime()`

**Activities**:
- Create base `_translate_type_conversion()` helper
- Implement each specific conversion function
- Handle conversion failures (return empty, not error)
- Use database TRY_CAST where available

**Conversion Patterns**:
```python
def _translate_tointeger(self, node: FunctionCallNode) -> SQLFragment:
    """Translate toInteger() - convert to integer."""
    source = self.visit(node.target)

    # Use TRY_CAST for safe conversion
    sql = f"TRY_CAST({source.expression} AS BIGINT)"

    return SQLFragment(expression=sql, ...)

def _translate_tostring(self, node: FunctionCallNode) -> SQLFragment:
    """Translate toString() - convert to string."""
    source = self.visit(node.target)

    # Use CAST to string
    sql = f"CAST({source.expression} AS VARCHAR)"

    return SQLFragment(expression=sql, ...)

def _translate_todatetime(self, node: FunctionCallNode) -> SQLFragment:
    """Translate toDateTime() - convert to datetime."""
    source = self.visit(node.target)

    # Use dialect-specific datetime parsing
    sql = self.dialect.parse_datetime(source.expression)

    return SQLFragment(expression=sql, ...)
```

**Example SQL Generation**:
```sql
-- DuckDB: '123'.toInteger()
TRY_CAST('123' AS BIGINT)
-- Result: 123

-- DuckDB: 'abc'.toInteger()
TRY_CAST('abc' AS BIGINT)
-- Result: NULL (empty)

-- PostgreSQL: Patient.birthDate.toDateTime()
(resource->>'birthDate')::timestamp

-- DuckDB: true.toString()
CAST(TRUE AS VARCHAR)
-- Result: 'true'
```

**Validation**:
- Run: `pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -k "to_type"`
- Expect: 30+ tests passing
- Test successful conversions and failures

**Time**: 16-20 hours

---

#### Step 3: Implement Conversion Test Functions (12-16 hours)

**Functions**: `.convertsToInteger()`, `.convertsToDecimal()`, `.convertsToString()`, `.convertsToBoolean()`, `.convertsToDate()`, `.convertsToDateTime()`, `.convertsToTime()`

**Activities**:
- Test if conversion would succeed WITHOUT performing it
- Return boolean instead of converted value
- Use same conversion logic as Step 2 but check for NULL

**Test Conversion Pattern**:
```python
def _translate_convertstointeger(self, node: FunctionCallNode) -> SQLFragment:
    """Translate convertsToInteger() - test if convertible to integer."""
    source = self.visit(node.target)

    # Check if TRY_CAST would succeed
    sql = f"(TRY_CAST({source.expression} AS BIGINT) IS NOT NULL)"

    return SQLFragment(expression=sql, ...)

def _translate_convertstostring(self, node: FunctionCallNode) -> SQLFragment:
    """Translate convertsToString() - test if convertible to string."""
    # Everything converts to string in SQL
    sql = "TRUE"

    return SQLFragment(expression=sql, ...)
```

**Example SQL Generation**:
```sql
-- DuckDB: '123'.convertsToInteger()
(TRY_CAST('123' AS BIGINT) IS NOT NULL)
-- Result: true

-- DuckDB: 'abc'.convertsToInteger()
(TRY_CAST('abc' AS BIGINT) IS NOT NULL)
-- Result: false

-- DuckDB: '2023-01-15'.convertsToDate()
(TRY_CAST('2023-01-15' AS DATE) IS NOT NULL)
-- Result: true

-- PostgreSQL: value.convertsToDecimal()
((value->>'value')::numeric IS NOT NULL)
```

**Validation**:
- Run: `pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -k "converts_to"`
- Expect: 20+ tests passing
- Test edge cases and all supported conversions

**Time**: 12-16 hours

---

#### Step 4: Implement `.as()` Type Casting (16-20 hours)

**Activities**:
- Parse target type from argument
- Validate type with TypeRegistry
- Generate safe casting SQL
- Return empty for invalid casts
- Handle both primitive and complex type casts

**Casting Pattern**:
```python
def _translate_as(self, node: FunctionCallNode) -> SQLFragment:
    """Translate as() - safe type casting."""

    source = self.visit(node.target)
    target_type = self._extract_type_argument(node.arguments[0])

    # Validate type
    if not self.type_registry.is_valid_type(target_type):
        raise ValueError(f"Unknown type: {target_type}")

    # For primitives, use conversion
    if self.type_registry.is_primitive(target_type):
        cast_sql = self._generate_primitive_cast(
            source.expression,
            target_type
        )
    else:
        # For complex types, check resourceType field
        cast_sql = self._generate_complex_type_cast(
            source.expression,
            target_type
        )

    # Wrap in CASE to return empty on failure
    sql = f"""CASE
        WHEN {self._can_cast(source.expression, target_type)}
        THEN {cast_sql}
        ELSE NULL
    END"""

    return SQLFragment(expression=sql, ...)
```

**Example SQL Generation**:
```sql
-- DuckDB: value.as(Quantity)
CASE
    WHEN json_type(value) = 'OBJECT'
         AND json_extract_string(value, '$.unit') IS NOT NULL
    THEN value
    ELSE NULL
END

-- PostgreSQL: Observation.value.as(Quantity).value
CASE
    WHEN jsonb_typeof(resource->'value') = 'object'
         AND (resource->'value'->>'unit') IS NOT NULL
    THEN (resource->'value'->>'value')::numeric
    ELSE NULL
END

-- DuckDB: '123'.as(integer)
CASE
    WHEN TRY_CAST('123' AS BIGINT) IS NOT NULL
    THEN CAST('123' AS BIGINT)
    ELSE NULL
END
```

**Validation**:
- Run: `pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -k "as_type"`
- Expect: 20+ tests passing
- Test primitive casts, complex type casts, invalid casts

**Time**: 16-20 hours

---

#### Step 5: Integration Testing and Refinement (8-12 hours)

**Activities**:
- Run full FHIRPath compliance suite
- Verify 100+/116 type tests passing
- Fix any regressions in other test categories
- Optimize SQL generation for performance
- Test on both DuckDB and PostgreSQL

**Testing Commands**:
```bash
# Run type function tests
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -v

# Run full official test suite
PYTHONPATH=. python3 -m tests.integration.fhirpath.official_test_runner

# Test on PostgreSQL
DB_TYPE=postgresql pytest tests/unit/fhirpath/sql/test_translator_type_functions.py -v
```

**Validation**:
- Type functions: 100+/116 passing (85%+)
- Overall FHIRPath compliance: 48-52% (up from 42.4%)
- Zero regressions in other categories
- Both databases passing all tests

**Time**: 8-12 hours

---

## Testing Strategy

### Unit Testing

**New Test File**: `tests/unit/fhirpath/sql/test_translator_type_functions.py`

**Test Categories**:
1. **Type Checking** (`.is()`, `.hasValue()`)
   - Primitive types: string, integer, decimal, boolean
   - Complex types: Quantity, HumanName, CodeableConcept
   - Edge cases: null, empty, missing fields

2. **Type Conversions** (`.toInteger()`, `.toString()`, etc.)
   - Valid conversions: '123' → 123, true → 'true'
   - Invalid conversions: 'abc' → empty, {} → empty
   - Temporal conversions: string → date/datetime

3. **Conversion Tests** (`.convertsToInteger()`, etc.)
   - Test returns boolean
   - Test accuracy: only true if conversion succeeds
   - All supported type pairs

4. **Type Casting** (`.as()`)
   - Safe casting with validation
   - Return empty for invalid casts
   - Polymorphic element handling

**Coverage Target**: 95%+ for new type function code

### Integration Testing

**Database Testing**:
- DuckDB: All type functions
- PostgreSQL: All type functions
- Result parity: Identical outputs across databases

**Component Integration**:
- Type functions with collection operations
- Type checks in `.where()` filters
- Type conversions in `.select()` transformations

**End-to-End Testing**:
- Real FHIR resources with polymorphic elements
- Type hierarchy (subtypes, supertypes)
- Type conversions in complex expressions

### Compliance Testing

**Official Test Suites**:
```bash
# Run FHIRPath compliance (target: 48-52%)
PYTHONPATH=. python3 -m tests.integration.fhirpath.official_test_runner

# Expected improvement:
# Before: 396/934 (42.4%)
# After:  448-485/934 (48-52%)
```

**Regression Testing**:
- Run full unit test suite
- Verify zero new failures
- Check performance hasn't degraded

### Manual Testing

**Test Scenarios**:
1. Type checking: `Observation.value.is(Quantity)` on mixed observations
2. Type conversion: `.toInteger()` on string fields
3. Safe casting: `.as(Quantity)` on polymorphic value[x]
4. Type hierarchy: `.ofType(DomainResource)` on Bundle entries

**Edge Cases**:
- Null values at each step
- Empty strings vs missing fields
- Invalid type names
- Circular type relationships (if any)

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Type system complexity | Medium | High | Leverage TypeRegistry, implement incrementally |
| Polymorphic element handling | Medium | Medium | Test extensively with real FHIR data |
| Database type differences | Low | Medium | Abstract in dialect classes |
| Performance overhead | Low | Low | Use native database type operations |

### Implementation Challenges

1. **FHIR Type Semantics**
   - **Challenge**: FHIR has complex type hierarchy and rules
   - **Approach**: Rely on TypeRegistry as source of truth, validate against spec

2. **Polymorphic Elements**
   - **Challenge**: Elements like `value[x]` can be any type
   - **Approach**: Check resourceType field, support all valid types

3. **Database Type Mapping**
   - **Challenge**: FHIR types don't map 1:1 to database types
   - **Approach**: Use JSON for complex types, primitives for simple types

### Contingency Plans

- **If type hierarchy is too complex**: Implement flat type checking first, add hierarchy later
- **If `.conformsTo()` is too difficult**: Defer to future sprint (low test count)
- **If performance is poor**: Cache type checks, optimize SQL patterns
- **If timeline extends**: Prioritize `.is()`, `.as()`, and conversion functions

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 6 hours
- **Implementation**: 64-84 hours
  - Step 1: `.hasValue()` and `.is()`: 12-16 hours
  - Step 2: Type conversions: 16-20 hours
  - Step 3: Conversion tests: 12-16 hours
  - Step 4: `.as()` casting: 16-20 hours
  - Step 5: Integration and refinement: 8-12 hours
- **Testing**: 16-20 hours
- **Documentation**: 6-8 hours
- **Review and Refinement**: 6-8 hours

**Total Estimate**: 98-126 hours (2.5-3.2 weeks)
**Conservative Estimate**: 120 hours (3 weeks)

### Confidence Level
- [x] Medium (70-89% confident)

**Rationale**: Medium confidence because:
- ✅ TypeRegistry provides FHIR type information
- ✅ Database type operations are well-documented
- ⚠️ FHIR type semantics can be subtle
- ⚠️ Polymorphic elements add complexity

---

## Success Metrics

### Quantitative Measures

- **Compliance Improvement**: 396 → 448-485 passing tests (42.4% → 48-52%)
- **Type Functions**: 28 → 100+ passing tests (24.1% → 85%+)
- **Test Coverage**: 95%+ for new type function code
- **Performance**: <50ms average per type function test

### Qualitative Measures

- **Code Quality**: Clean, well-documented, follows patterns
- **Architecture Alignment**: Integrates with TypeRegistry properly
- **Maintainability**: Easy to add new type operations

### Compliance Impact

**Before This Task**:
- FHIRPath compliance: 42.4% (396/934)
- Type functions: 24.1% (28/116)

**After This Task** (Target):
- FHIRPath compliance: 48-52% (448-485/934)
- Type functions: 85%+ (100+/116)

**Impact**: +6-10% overall FHIRPath specification compliance

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments for type checking logic
- [x] Function documentation with FHIR type examples
- [x] Type conversion rules documented
- [x] Example usage for each type function

### Architecture Documentation

- [x] Update `project-docs/architecture/translator-architecture.md`
- [x] Document type system integration
- [x] Create `project-docs/guides/type-functions-guide.md`

---

## Progress Tracking

### Status
- [x] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] Completed

### Completion Checklist

- [ ] All functional requirements implemented
- [ ] 100+/116 type tests passing
- [ ] Overall compliance: 48-52%
- [ ] Code reviewed and approved
- [ ] Documentation completed
- [ ] Zero regressions

---

**Task Created**: 2025-11-18 by Senior Solution Architect/Engineer
**Last Updated**: 2025-11-18
**Status**: Not Started
**Priority**: High - Second highest impact (+6-10% compliance)

---

*This task will deliver the second largest improvement to FHIRPath specification compliance and enable proper type safety for quality measures.*
