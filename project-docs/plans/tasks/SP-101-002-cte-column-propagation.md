# Task: SP-101-002 - CTE Column Propagation

**Created**: 2026-01-25
**Status**: Pending
**Priority**: P1-B (High)
**Estimated Effort**: 20-30 hours

---

## Task Description

Resolve CTE column reference propagation issues in collection function chains. Currently, chained operations like `Patient.name.first().given` fail with "Referenced column 'name_item' not found" errors.

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

1. **Column alias registry**: Track and propagate CTE column aliases through chains
2. **Dependency tracking**: Ensure CTE dependencies are tracked correctly
3. **Chain context**: Maintain context across chained operations
4. **Nested access**: Support nested field access on CTE results
5. **Standardization**: Document column naming conventions

### Use Cases

```fhirpath
# Nested field access after collection function
Patient.name.first().given

# Chained slicing
name.take(2).family

# Multiple chained operations
Patient.name.where(use='official').first().given
```

## Implementation Plan

### Step 1: Add Column Alias Registry to TranslationContext

```python
class TranslationContext:
    def __init__(self):
        # ... existing initialization ...
        self.cte_column_aliases: Dict[str, str] = {}

    def register_column_alias(self, old_name: str, new_name: str) -> None:
        """Register that old_name has been renamed to new_name in current CTE."""
        self.cte_column_aliases[new_name] = old_name

    def resolve_column_alias(self, column_name: str) -> str:
        """Resolve a column name through the alias registry."""
        return self.cte_column_aliases.get(column_name, column_name)
```

### Step 2: Update _traverse_expression_chain()

```python
def _traverse_expression_chain(self, node, target_path):
    # After creating a CTE with a result column, register the alias
    if fragment.requires_unnest and fragment.metadata.get("result_alias"):
        self.context.register_column_alias(
            original_name=self.context.current_table,
            new_name=fragment.metadata["result_alias"]
        )
```

### Step 3: Fix Nested Field Access

Update field access resolution to check the column alias registry:
```python
# When accessing a field on a collection result
if self.context.current_table in self.context.cte_column_aliases:
    # This is an aliased column, use the alias
    actual_table = self.context.resolve_column_alias(self.context.current_table)
```

## Acceptance Criteria

1. ✅ Collection slicing chains work correctly
2. ✅ All chained operation tests pass (~20 tests)
3. ✅ No regression on single operations
4. ✅ Both dialects supported
5. ✅ Column naming conventions documented
6. ✅ Zero regression on existing 468 passing tests

## Location

**Files**:
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py` (main translator)
- `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/context.py` (context)

## Dependencies

None - can be implemented independently

## Testing Strategy

### Unit Tests

Create unit tests in `tests/unit/fhirpath/sql/test_cte_column_propagation.py`:
- Single operation baseline tests
- Two-level chains (first().given, take(2).family)
- Three-level chains
- Edge cases: empty collections, null values

### Integration Tests

Run official test suite with chain filter:
```bash
python -m tests.integration.fhirpath.official_test_runner --test_filter "first\(\)|take\(\)|\.given|\.family"
```

### Regression Testing

Before and after changes:
```bash
# Baseline
python -m pytest tests/ -k "not failing" --maxfail=1

# After changes
python -m pytest tests/ -k "not failing" --maxfail=1
```

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: May help resolve other collection function tests
