# Task: Implement FHIRPath Polymorphic Field Navigation

**Task ID**: SP-021-004-POLYMORPHISM-SUPPORT
**Sprint**: Current Sprint
**Task Name**: Implement Polymorphic Field Navigation (value[x] Pattern)
**Assignee**: TBD
**Created**: 2025-11-28
**Last Updated**: 2025-11-28
**Status**: NOT STARTED
**Priority**: **HIGH** (Third-highest compliance impact: +20-30 tests)

---

## Task Overview

### Description

Implement proper handling for FHIR polymorphic fields following the `value[x]` pattern, where a single logical field can have multiple type-specific representations (e.g., `valueString`, `valueInteger`, `valueBoolean`).

Currently, ~30 compliance tests fail when accessing polymorphic fields like:
```
Observation.value  // Should resolve to valueString, valueInteger, etc.
```

With errors like:
```
Error: Field 'value' not found in Observation
Error: Cannot determine type for polymorphic field
```

This task is identified as **Priority 3** from the SP-021-001 investigation findings, with projected compliance improvement of +20-30 tests.

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation

### Priority
- [ ] Critical (Blocker for compliance progress)
- [x] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Polymorphic fields are common in FHIR resources (Observation.value, extension.value, etc.) and block ~30 compliance tests.

---

## Requirements

### Functional Requirements

1. **Polymorphic Field Resolution**: Resolve `value[x]` pattern to concrete types
   - Example: `Observation.value` should check `valueString`, `valueInteger`, `valueQuantity`, etc.

2. **Type Discrimination**: Return the actual value regardless of which type variant is present
   - If `valueString` exists, return it
   - If `valueInteger` exists, return it
   - Return first non-null variant

3. **FHIR Type Metadata**: Use StructureDefinition data to identify polymorphic fields
   - Leverage existing TypeRegistry
   - Identify fields with `[x]` suffix in definitions

4. **Multi-Database Support**: Ensure identical behavior in DuckDB and PostgreSQL

### Acceptance Criteria

- [ ] Polymorphic field navigation works (e.g., `Observation.value`)
- [ ] Correct type returned based on actual data
- [ ] Compliance reaches 424+ tests passing (minimum +20 tests improvement)
- [ ] Zero regressions in existing tests
- [ ] Both DuckDB and PostgreSQL produce identical results

---

## Technical Specifications

### Affected Components

- **TypeRegistry** (`fhir4ds/fhirpath/fhir_types/type_registry.py`): Add polymorphic field detection
- **ASTToSQLTranslator** (`fhir4ds/fhirpath/sql/translator.py`): Handle polymorphic field navigation
- **DatabaseDialect** (`fhir4ds/dialects/base.py`): May need COALESCE patterns for multiple fields

### Implementation Approach

**SQL Pattern Example**:
```sql
-- For Observation.value (polymorphic)
SELECT COALESCE(
  json_extract(resource, '$.valueString'),
  json_extract(resource, '$.valueInteger'),
  json_extract(resource, '$.valueBoolean'),
  json_extract(resource, '$.valueQuantity')
  -- ... other value[x] variants
) AS value
```

### Implementation Steps

1. **TypeRegistry Enhancement** (3-4 hours): Identify polymorphic fields from StructureDefinition
2. **Field Resolution** (4-5 hours): Implement polymorphic field expansion logic
3. **SQL Generation** (3-4 hours): Generate COALESCE expressions for polymorphic fields
4. **Unit Tests** (2-3 hours): Test various polymorphic scenarios
5. **Compliance Testing** (2 hours): Validate improvement

---

## Estimation

- **Total Estimate**: 14-18 hours
- **Confidence Level**: Medium (70-89%)
- **Expected Impact**: +20-30 tests (from 404/934 to 424-434/934, 45.4-46.5% compliance)

---

## References

- **Investigation Findings**: `work/SP-021-001-INVESTIGATION-FINDINGS.md` (Priority 3)
- **FHIR Specification**: Polymorphic Elements (choice[x] pattern)
- **FHIRPath Specification**: Type resolution for polymorphic fields
- **Predecessor**: SP-021-002, SP-021-003 recommended first

---

**Task Created**: 2025-11-28
**Priority**: HIGH (Third-highest compliance impact)
**Estimated Impact**: +20-30 tests
