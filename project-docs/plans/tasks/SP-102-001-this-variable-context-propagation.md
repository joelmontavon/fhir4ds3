# Task SP-102-001: $this Variable Context Propagation

**Priority:** P0 (CRITICAL)
**Estimated Effort:** 6-8 hours
**Dependencies:** None
**Tests Fixed:** 2 directly, 50+ indirectly (unblocks lambdas)
**Status:** Pending

---

## Task Description

Fix the `$this` variable context propagation issue that prevents lambda expressions from accessing the outer context. This is a critical blocker for all collection functions that use lambdas (where, select, all, any, exists).

## Failing Tests

- `testDollarThis1`: `Patient.name.given.where(substring($this.length()-3) = 'out')`
- `testDollarThis2`: `Patient.name.given.where(substring($this.length()-3) = 'ter')`

## Root Cause Analysis

**Current Behavior:**
The `$this` variable is bound at the translator initialization but is not properly propagated into nested lambda contexts. When a lambda function (like `where()`) creates a new scope, it shadows the global `$this` binding instead of inheriting it.

**Expected Behavior:**
- `$this` should refer to the current collection item in lambda contexts
- In `Patient.name.given.where(...)`, `$this` should reference each `given` item
- The variable binding must be propagated through the CTE chain

**Architecture Violation:**
This breaks the unified FHIRPath variable scoping rules and prevents population-scale lambda operations.

## Implementation Strategy

### Phase 1: Understand Variable Binding Flow

**File:** `fhir4ds/main/fhirpath/sql/context.py`

1. Review `VariableBinding` class
2. Understand how `bind_variable()` works
3. Trace how variables are stored and retrieved
4. Identify where lambda scopes shadow $this

### Phase 2: Fix Context Propagation

**File:** `fhir4ds/main/fhirpath/sql/translator.py`

**Option A: Explicit $this Propagation**
```python
# In visit_function_call() for lambda functions
if function_name in ('where', 'select', 'all', 'any', 'exists'):
    # Get current $this binding
    current_this = self.context.get_variable('$this')

    # Create new lambda scope
    with self.context.push_scope():
        # Re-bind $this to the lambda input item
        self.context.bind_variable('$this', VariableBinding(
            expression=item_expression,  # e.g., "given_item"
            source_table=item_table      # e.g., "cte_1"
        ))

        # Translate lambda body
        # ... lambda translation ...
```

**Option B: Automatic Scope Inheritance**
Modify `push_scope()` to automatically inherit `$this` unless explicitly overridden.

### Phase 3: CTE Integration

Ensure variable references are included in CTE generation:
- Lambda input items must be available in CTEs
- `$this` references must resolve to correct table columns
- Test with nested lambdas: `where(select(...))`

### Phase 4: Testing

**Test Cases:**
1. Simple lambda: `Patient.name.given.where($this = 'John')`
2. Function call on $this: `Patient.name.given.where(substring($this, 1) = 'oh')`
3. Nested lambdas: `Patient.name.where($this.given.exists())`
4. Chained operations: `Patient.name.where($this.family.exists()).select($this.given)`

## Acceptance Criteria

- [ ] `testDollarThis1` passes
- [ ] `testDollarThis2` passes
- [ ] All lambda functions work with $this
- [ ] Nested lambdas work correctly
- [ ] CTE generation includes variable references
- [ ] Works in both DuckDB and PostgreSQL
- [ ] No architectural violations (thin dialects)
- [ ] Population-first design maintained

## Architectural Requirements

### MUST (Non-Negotiable)
- **Unified FHIRPath Architecture:** Variable scoping must match spec
- **CTE-First Design:** Lambdas generate proper CTE structures
- **Thin Dialects:** No business logic in dialect layer
- **Population-First:** No single-patient workarounds

### SHOULD (High Priority)
- Efficient variable lookup (no excessive joins)
- Clear error messages for undefined variables
- Support for complex lambda expressions

### COULD (Nice to Have)
- Performance optimization for variable resolution
- Debug logging for variable propagation

## Testing Commands

```bash
# Unit tests for translator
python3 -m pytest tests/unit/fhirpath/sql/test_translator.py -v -k "this"

# Compliance tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py::TestOfficial::testDollarThis1 -v
python3 -m pytest tests/integration/fhirpath/official_test_runner.py::TestOfficial::testDollarThis2 -v

# Full compliance suite
python3 tests/integration/fhirpath/official_test_runner.py
```

## Risk Assessment

**Risk Level:** HIGH

**Risks:**
1. Complex variable scoping rules
2. May require refactoring of context management
3. Could break existing functionality

**Mitigation:**
1. Incremental testing with simple cases first
2. Comprehensive test coverage before committing
3. Rollback plan if critical issues found

## Rollback Plan

If implementation fails:
1. Revert changes to `context.py` and `translator.py`
2. Document specific issues encountered
3. Create follow-up task for alternative approach

## Dependencies

**Blocks:** SP-102-005 (Collection Functions)

**Blocked By:** None

## Notes

- This is the highest priority task
- Success unblocks many other tests
- Critical for FHIRPath spec compliance
- Consider creating separate variable scope manager if complexity grows

---

**Task Status:** Pending
**Assigned To:** Unassigned
**Review Status:** Not Started
**Completion Date:** TBD
