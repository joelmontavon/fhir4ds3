# Task: SP-101-001 - Arithmetic Type Coercion

**Created**: 2026-01-25
**Status**: Pending
**Priority**: P1-A (High)
**Estimated Effort**: 15-20 hours

---

## Task Description

Implement FHIRPath spec-compliant type coercion for arithmetic operators. Currently, mixed-type arithmetic operations fail due to incomplete type promotion rules.

**Current Compliance**: 25% (18/72 arithmetic operator tests passing)

## Requirements

### Functional Requirements

1. **Type Inference**: Add helper to infer operand types dynamically
2. **Type Promotion Rules**: Implement FHIRPath spec rules:
   - `integer + integer` → `integer`
   - `integer + decimal` → `decimal`
   - `decimal + decimal` → `decimal`
   - `integer - integer` → `integer`
   - `integer * integer` → `integer`
   - `integer / integer` → `decimal` (division always returns decimal)
   - `integer mod integer` → `integer`
3. **Division Semantics**: Fix division to always return decimal per spec
4. **Modulo Edge Cases**: Handle modulo operation edge cases
5. **Implicit Coercion**: Handle type coercion in function arguments

### Examples

| FHIRPath Expression | Expected Type |
|---------------------|---------------|
| `1 + 2` | `integer` |
| `1 + 2.5` | `decimal` |
| `10 / 3` | `decimal` (3.333...) |
| `5 mod 3` | `integer` (2) |

## Implementation Plan

### Step 1: Add Type Inference Helper

```python
def _infer_operand_type(self, expression: str, metadata: dict) -> str:
    """Infer the type of an expression from metadata and SQL analysis."""
    # Check metadata for explicit type hints
    if metadata.get("is_literal"):
        return metadata.get("literal_type", "string")

    # Check SQL expression patterns
    expr_upper = expression.upper().strip()
    if expr_upper.startswith("CAST("):
        # Extract type from CAST expression
        # CAST(expr AS TYPE)
        import re
        match = re.search(r'AS\s+(\w+)', expr_upper)
        if match:
            return match.group(1).lower()

    # Default to string for JSON-extracted values
    return "string"
```

### Step 2: Implement Type Promotion Logic

```python
def _get_promoted_type(self, left_type: str, right_type: str, operator: str) -> str:
    """Get the result type for binary arithmetic operation per FHIRPath spec."""

    # Division always returns decimal
    if operator in ("/", "div"):
        return "decimal"

    # If both types are the same, return that type
    if left_type == right_type:
        return left_type

    # integer + decimal → decimal
    if {left_type, right_type} == {"integer", "decimal"}:
        return "decimal"

    # Default: try to coerce to the more general type
    type_rank = {"integer": 1, "decimal": 2, "string": 3}
    return left_type if type_rank[left_type] >= type_rank[right_type] else right_type
```

### Step 3: Update Arithmetic Operator Visitors

Modify `_translate_addition()`, `_translate_subtraction()`, etc. to:
1. Infer operand types
2. Apply type promotion rules
3. Generate explicit casts when needed

## Acceptance Criteria

1. ✅ Arithmetic operators achieve 70%+ compliance (50/72 tests)
2. ✅ Type coercion matches FHIRPath spec behavior
3. ✅ Division always returns decimal
4. ✅ All edge cases handled (modulo, mixed types)
5. ✅ Both DuckDB and PostgreSQL produce consistent results
6. ✅ No regression on existing tests

## Location

**File**: `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`
**Lines**: 2284-2921 (arithmetic operator section)

## Dependencies

None - can be implemented independently

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_type_coercion.py`:
- Type promotion for all operator combinations
- Division semantics
- Modulo edge cases
- Mixed-type collections

### Integration Tests

Run official test suite with arithmetic filter:
```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter "arithmetic|operator|divide|mod"
```

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: None
