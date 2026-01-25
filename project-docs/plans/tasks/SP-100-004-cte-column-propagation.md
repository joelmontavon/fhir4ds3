# Task: SP-100-004 - Fix CTE Column Propagation

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P1 (High)
**Estimated Effort**: 20-30 hours

---

## Task Description

Resolve CTE column reference propagation issues in collection function chains. Currently, chained operations like `Patient.name.first().given` fail with "Referenced column 'name_item'/'result' not found" errors.

## Current State

**Location**: `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py:1692-4009`

**Error Example**:
```
Referenced column 'name_item' not found
Referenced column 'result' not found
```

**Failing Expressions**:
- `Patient.name.first().given` (~20 tests)
- `name.take(2).given`
- Collection slicing chains

**Root Cause**: CTE column aliases are not properly propagated through function chains.

## Requirements

### Functional Requirements

1. **Column alias propagation**: Track and propagate CTE column aliases through chains
2. **Dependency tracking**: Ensure CTE dependencies are tracked correctly
3. **Chain context**: Maintain context across chained operations
4. **Nested access**: Support nested field access on collection results

## Acceptance Criteria

1. ✅ Collection slicing chains work correctly
2. ✅ All chained operation tests pass (~20 tests)
3. ✅ No regression on single operations
4. ✅ Both dialects supported

---

**Task Owner**: TBD
**Blocked By**: None
**Blocking**: Multiple collection function tests
