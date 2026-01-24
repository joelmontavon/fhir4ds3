# Task: Implement FHIRPath Type Functions (is, as, ofType)

**Task ID**: SP-021-005-TYPE-FUNCTIONS-IMPLEMENTATION
**Sprint**: Current Sprint
**Task Name**: Implement FHIRPath Type Checking and Casting Functions
**Assignee**: TBD
**Created**: 2025-11-28
**Last Updated**: 2025-11-28
**Status**: NOT STARTED
**Priority**: **CRITICAL** (Largest compliance impact: +50-80 tests)

---

## Task Overview

### Description

Implement proper FHIRPath type functions for runtime type checking and casting:
- `is(type)`: Check if value is of specified type
- `as(type)`: Cast value to specified type (returns empty if not that type)
- `ofType(type)`: Filter collection to only items of specified type

Currently, ~80 compliance tests fail when using type functions with errors like:
```
Error: Function 'is' not implemented
Error: Function 'as' not properly implemented
Error: Function 'ofType' returns incorrect results
```

This task is identified as **Priority 4** from the SP-021-001 investigation findings, but has the **largest projected compliance improvement** (+50-80 tests).

### Category
- [x] Feature Implementation
- [x] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation

### Priority
- [x] Critical (Largest compliance impact)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Type functions are used extensively in FHIRPath expressions for type safety and filtering, blocking ~80 compliance tests. While listed as Priority 4, the impact is actually the largest single improvement opportunity.

---

## Requirements

### Functional Requirements

1. **is(type) Function**: Check if value matches specified type
   - Example: `Patient.name.is(HumanName)` returns true
   - Example: `5.is(Integer)` returns true
   - Returns boolean for single item, collection of booleans for collections

2. **as(type) Function**: Cast value to type or return empty
   - Example: `value.as(String)` returns value if it's a string, empty otherwise
   - Used for safe type conversion
   - Returns empty collection if types don't match

3. **ofType(type) Function**: Filter collection to items of specified type
   - Example: `bundle.entry.resource.ofType(Patient)` returns only Patient resources
   - Commonly used with polymorphic collections
   - Returns filtered collection

4. **FHIR Type System Integration**: Use TypeRegistry for FHIR type checking
   - Check structural types (HumanName, Address, etc.)
   - Check primitive types (string, integer, boolean, etc.)
   - Handle FHIR resource types (Patient, Observation, etc.)

5. **Multi-Database Support**: Ensure identical behavior in DuckDB and PostgreSQL

### Acceptance Criteria

- [ ] `is(type)` function works correctly for all FHIR types
- [ ] `as(type)` function safely casts with proper empty returns
- [ ] `ofType(type)` function filters collections correctly
- [ ] Type checking uses TypeRegistry metadata
- [ ] Compliance reaches 454+ tests passing (minimum +50 tests improvement)
- [ ] Zero regressions in existing tests
- [ ] Both DuckDB and PostgreSQL produce identical results

---

## Technical Specifications

### Affected Components

- **ASTToSQLTranslator** (`fhir4ds/fhirpath/sql/translator.py`): Implement type function translations
- **TypeRegistry** (`fhir4ds/fhirpath/fhir_types/type_registry.py`): Provide type checking utilities
- **DatabaseDialect** (`fhir4ds/dialects/base.py`): May need JSON type detection helpers

### Implementation Approach

**SQL Pattern Examples**:

**is(type)**:
```sql
-- For value.is(String)
SELECT
  CASE
    WHEN json_type(value) = 'string' THEN true
    ELSE false
  END
```

**as(type)**:
```sql
-- For value.as(String)
SELECT
  CASE
    WHEN json_type(value) = 'string' THEN value
    ELSE NULL  -- Empty in FHIRPath
  END
```

**ofType(type)**:
```sql
-- For resources.ofType(Patient)
SELECT item
FROM UNNEST(collection) AS item
WHERE json_extract(item, '$.resourceType') = 'Patient'
```

### Implementation Steps

1. **TypeRegistry Extensions** (2-3 hours): Add type checking utilities
2. **is() Function** (3-4 hours): Implement type checking logic
3. **as() Function** (3-4 hours): Implement safe casting logic
4. **ofType() Function** (4-5 hours): Implement collection filtering with type checks
5. **FHIR Type Integration** (3-4 hours): Connect to TypeRegistry for FHIR-specific types
6. **Unit Tests** (4-5 hours): Comprehensive tests for all three functions
7. **Integration Tests** (2-3 hours): Test with real FHIR data
8. **Compliance Testing** (2-3 hours): Validate improvement

---

## Estimation

- **Total Estimate**: 23-31 hours
- **Confidence Level**: Medium (70-89%)
- **Expected Impact**: +50-80 tests (from 404/934 to 454-484/934, 48.6-51.8% compliance)

**Note**: This is the largest single improvement opportunity but requires solid understanding of FHIR type system.

---

## Dependencies

### Prerequisites

1. **SP-021-002**: Variable binding (some type function tests use lambda variables)
2. **SP-021-004**: Polymorphism (type functions often used with polymorphic fields)
3. **TypeRegistry**: Existing infrastructure (needs extension)

### Recommended Order

While listed as Priority 4, this task has the **highest impact**. However:
- SP-021-002 (variables) should be implemented first (required for many type function tests)
- SP-021-004 (polymorphism) is complementary (type functions often filter polymorphic collections)

**Suggested Implementation Order**: SP-021-002 → SP-021-003 → SP-021-004 → **SP-021-005**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FHIR type system complexity | High | Medium | Leverage existing TypeRegistry; implement primitive types first |
| SQL type detection differences | Medium | Medium | Use dialect methods for type detection; test both databases |
| Resource type detection | Medium | Medium | Use resourceType field; handle missing gracefully |

---

## References

- **Investigation Findings**: `work/SP-021-001-INVESTIGATION-FINDINGS.md` (Priority 4, highest impact)
- **FHIRPath Specification**: Type functions (Section 5.4)
- **FHIR Specification**: Resource types and type system
- **Coding Standards**: `project-docs/process/coding-standards.md`

---

**Task Created**: 2025-11-28
**Priority**: CRITICAL (Largest single compliance impact: +50-80 tests)
**Estimated Impact**: +50-80 tests (potential to reach 50%+ compliance)
**Note**: Despite being "Priority 4" in investigation, this has the highest numeric impact

---

*This task has the potential to push FHIR4DS compliance past the 50% milestone, making it a critical priority for overall project success.*
