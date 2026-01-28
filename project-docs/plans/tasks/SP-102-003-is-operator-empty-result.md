# Task SP-102-003: is() Operator Empty Result Handling

**Priority:** P0 (CRITICAL)
**Estimated Effort:** 3-4 hours
**Dependencies:** None
**Tests Fixed:** 1 directly, 5+ indirectly
**Status:** Pending

---

## Task Description

Fix the `is()` operator to return an empty result set (not `false`) when checking if a non-polymorphic property is of a specific type. This aligns with FHIRPath R4 specification behavior.

## Failing Test

- `testPolymorphismIsA3`: `Observation.issued is instant`

**Expected:** Empty result set (no match)
**Actual:** Returns `false`

## Root Cause Analysis

**Current Behavior:**
The type checking logic returns a boolean `false` when the type doesn't match, instead of returning an empty collection.

**Expected Behavior:**
According to FHIRPath R4 spec, the `is` operator should:
- Return empty collection if the type doesn't match
- Return singleton true if type matches
- Return singleton false only in specific edge cases

**Specification Reference:**
FHIRPath R4 specification: "is : Determines if the value of the left operand is of the type specified as the right operand."

## Implementation Strategy

### Phase 1: Understand Type Checking Logic

**File:** `fhir4ds/main/fhirpath/sql/translator.py`

1. Review `visit_type_operation()` method
2. Understand current `is` operator implementation
3. Trace how type checking results are generated

### Phase 2: Fix Return Value Logic

**Current Code (likely):**
```python
# Returns false for non-matching types
if not is_polymorphic or type_does_not_match:
    return SQLFragment(expression="false", ...)
```

**Fixed Code:**
```python
# Return empty result set for non-matching types
if not is_polymorphic or type_does_not_match:
    # Return empty collection (not false)
    return SQLFragment(
        expression="SELECT NULL WHERE FALSE",  # Returns no rows
        is_empty=True
    )

# Return true for matching types
if type_matches:
    return SQLFragment(expression="true", ...)
```

### Phase 3: Test Type System

**Test Cases:**
1. Polymorphic property matches type: `Observation.value is Quantity`
2. Polymorphic property doesn't match: `Observation.value is string`
3. Non-polymorphic property: `Observation.issued is instant`
4. Nested type checks: `Observation.component.value is integer`

## Acceptance Criteria

- [ ] `testPolymorphismIsA3` passes
- [ ] All type checking follows FHIRPath spec
- [ ] Empty collections returned appropriately
- [ ] Boolean values returned only when correct
- [ ] Works in both DuckDB and PostgreSQL
- [ ] No architectural violations

## Architectural Requirements

### MUST (Non-Negotiable)
- **FHIRPath Spec Compliance:** Match spec behavior exactly
- **Type System Consistency:** Consistent with other type operations
- **Thin Dialects:** No business logic in dialect layer

### SHOULD (High Priority)
- Clear type checking logic
- Efficient SQL generation
- Proper null handling

## Testing Commands

```bash
# Unit tests
python3 -m pytest tests/unit/fhirpath/sql/test_translator_type_operations.py -v

# Compliance tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py::TestOfficial::testPolymorphismIsA3 -v
```

## Risk Assessment

**Risk Level:** LOW-MEDIUM

**Risks:**
1. May affect other type operations (ofType, as)
2. Could break existing type checks

**Mitigation:**
1. Test all type operations
2. Check for regressions

## Dependencies

**Blocks:** None

**Blocked By:** None

## Notes

- Lower complexity than P0-1 and P0-2
- Critical for type system completeness
- Good candidate for quick win

---

**Task Status:** Pending
**Assigned To:** Unassigned
**Review Status:** Not Started
**Completion Date:** TBD
