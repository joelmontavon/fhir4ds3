# Task SP-102-002: skip() CTE Column Propagation

**Priority:** P0 (CRITICAL)
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Tests Fixed:** 2 directly, 10+ indirectly
**Status:** Pending

---

## Task Description

Fix the CTE column propagation issue that causes `Binder Error` when using `skip()` followed by field access. The error occurs because column references are not properly tracked after `skip()` operation.

## Failing Tests

- `testDollarOrderAllowed`: `Patient.name.skip(1).given`
- `testDollarOrderAllowedA`: `Patient.name.skip(3).given`

## Root Cause Analysis

**Current Behavior:**
After `skip()` generates a CTE, subsequent field access tries to reference columns that don't exist in the new CTE. The error message shows:

```
Binder Error: Referenced column "name_item" not found in FROM clause!
Candidate bindings: "cte_1_order", "result"
```

This indicates that after `skip()`, the code tries to unnest from `name_item` but that column no longer exists in the current scope.

**Expected Behavior:**
- `skip()` should preserve the collection structure in the CTE
- Subsequent operations should reference the correct CTE output columns
- The column alias tracking should work across CTE boundaries

**Architecture Violation:**
Violates CTE-first design - skip() should create proper CTE structure that maintains column references.

## Implementation Strategy

### Phase 1: Understand skip() Implementation

**File:** `fhir4ds/main/fhirpath/sql/translator.py`

1. Review `_translate_skip()` method
2. Understand how skip() generates CTEs
3. Trace column reference tracking
4. Identify where column alias is lost

### Phase 2: Fix Column Tracking

**Issue:** After skip() creates a CTE, the next operation needs to know:
- What is the output column name from skip()'s CTE?
- What table should be used for the next unnest operation?

**Solution:**
1. Update `skip()` to return a fragment with correct column metadata
2. Ensure the fragment's `source_table` points to the skip CTE
3. Update context to track the current collection item column

**Example Fix:**
```python
def _translate_skip(self, node: FunctionCallNode) -> SQLFragment:
    # ... existing skip logic ...

    # CRITICAL: Update context to reference skip CTE output
    skip_cte_name = f"cte_{self._internal_alias_counter}"

    # The skip CTE outputs a column with the collection items
    # Subsequent operations need to reference this
    fragment = SQLFragment(
        expression=skip_query,
        source_table=skip_cte_name,
        # Preserve the item column name for next operation
        item_column=self.context.current_item_column
    )

    # Update context for next operation
    self.context.set_current_collection(
        table=skip_cte_name,
        item_column=self.context.current_item_column
    )

    return fragment
```

### Phase 3: Test Chained Operations

Ensure these patterns work:
1. `skip().field` - Basic case
2. `skip().where()` - Skip then filter
3. `skip().select()` - Skip then project
4. `skip().skip()` - Multiple skips
5. `field.skip().field` - Navigate, skip, navigate

### Phase 4: CTE Chain Validation

Verify CTE structure:
```sql
-- Expected structure for Patient.name.skip(1).given

WITH cte_1 AS (
  SELECT id, json_extract(resource, '$.name[*]') AS name_item
  FROM resource
),
cte_1_order AS (
  SELECT id, name_item
  FROM cte_1
  ORDER BY id
),
cte_2 AS (
  SELECT id, name_item
  FROM cte_1_order
  LIMIT -1 OFFSET 1  -- skip(1)
),
result AS (
  SELECT
    cte_2.id,
    json_extract(cte_2.name_item, '$.given[*]') AS given_item
  FROM cte_2,
  LATERAL UNNEST(json_extract(cte_2.name_item, '$.given[*]')) AS given_item
)
SELECT id, given_item FROM result
```

## Acceptance Criteria

- [ ] `testDollarOrderAllowed` passes
- [ ] `testDollarOrderAllowedA` passes
- [ ] All skip() operations work correctly
- [ ] Chained operations with skip() work
- [ ] CTE column references are correct
- [ ] Works in both DuckDB and PostgreSQL
- [ ] No architectural violations
- [ ] CTE-first design maintained

## Architectural Requirements

### MUST (Non-Negotiable)
- **CTE-First Design:** skip() generates proper CTE structure
- **Thin Dialects:** No business logic in dialect layer
- **Column Tracking:** Accurate metadata across CTE boundaries

### SHOULD (High Priority)
- Efficient CTE generation (no unnecessary CTEs)
- Clear error messages for column reference errors
- Support for all collection navigation patterns

### COULD (Nice to Have)
- Optimization for consecutive skip operations
- Debug logging for column tracking

## Testing Commands

```bash
# Unit tests
python3 -m pytest tests/unit/fhirpath/sql/test_translator.py -v -k "skip"

# Compliance tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py::TestOfficial::testDollarOrderAllowed -v
python3 -m pytest tests/integration/fhirpath/official_test_runner.py::TestOfficial::testDollarOrderAllowedA -v

# Integration tests
python3 -m pytest tests/integration/fhirpath/test_end_to_end_execution.py -v
```

## Risk Assessment

**Risk Level:** MEDIUM

**Risks:**
1. Complex CTE column tracking
2. May affect other collection functions
3. Could break existing navigation patterns

**Mitigation:**
1. Test with simple cases first
2. Check for regressions in other functions
3. Comprehensive test coverage

## Rollback Plan

If implementation fails:
1. Revert changes to translator.py
2. Document specific issues encountered
3. Consider alternative approach to column tracking

## Dependencies

**Blocks:** SP-102-005 (Collection Functions)

**Blocked By:** None

## Notes

- This is a high-priority task
- Closely related to context management
- Success will unblock many collection operations
- Consider refactoring column tracking into a separate module

---

**Task Status:** Pending
**Assigned To:** Unassigned
**Review Status:** Not Started
**Completion Date:** TBD
