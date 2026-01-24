# Array Metadata Issue - Root Cause Found

**Date**: 2025-12-05 (Late Evening)
**Status**: Diagnosed, Not Yet Fixed
**Impact**: ~80-120 tests blocked

---

## The Problem

**Error**: `ValueError: SQLFragment metadata must contain 'array_column' for UNNEST operations`

**Frequency**: ~80-120 failing tests

---

## Root Cause Identified

When the SQL translator processes **comparison operations between arrays**, it:
1. ✅ Correctly sets `requires_unnest = True`
2. ❌ **Fails to populate metadata** (leaves it empty!)

### Example

**Expression**: `name = name`

**Translator Output**:
```python
# Fragment 1: First 'name'
requires_unnest: True
metadata: {'array_column': "json_extract(resource, '$.name[*]')", ...}  # ✓ GOOD

# Fragment 2: Second 'name'
requires_unnest: True
metadata: {'array_column': "json_extract(resource, '$.name[*]')", ...}  # ✓ GOOD

# Fragment 3: Comparison 'name = name'
requires_unnest: True
metadata: {}  # ❌ EMPTY! This causes the error
```

---

## Why This Happens

The translator creates SQLFragments for:
1. Left operand extraction (has metadata)
2. Right operand extraction (has metadata)
3. **Comparison operation** (marked as UNNEST but NO metadata!)

When CTE builder tries to wrap Fragment 3, it sees `requires_unnest=True` and calls `_wrap_unnest_query()`, which requires `array_column` metadata... but the metadata is empty!

---

## The Fix Required

### Location
In the SQL translator where comparison operations are generated.

### What Needs to Happen
When creating a comparison SQLFragment with `requires_unnest=True`, the translator must:
1. Detect that operands are arrays
2. Copy the `array_column` metadata from one of the operands
3. Populate the comparison fragment's metadata properly

### Code Pattern Needed
```python
# When generating comparison of arrays:
if requires_unnest:
    # Copy metadata from left or right operand
    comparison_fragment.metadata['array_column'] = left_operand_metadata['array_column']
    comparison_fragment.metadata['result_alias'] = 'comparison_result'
    # ... other required metadata
```

---

## Impact

### Affected Operations
- Array comparisons: `name = name`, `name != name`
- Array operations after extraction: `.tail().given`, `.take(1)`
- Indexed access in some contexts: `name[0].given`

### Estimated Test Impact
~80-120 tests currently failing with this error

---

## Files to Investigate

1. **SQL Translator** - Where comparison operations are generated
2. **Operator handlers** - Where array operations set metadata
3. **SQLFragment creation** - Ensure metadata propagates

---

## Not Fixed Tonight

Due to:
1. Complexity of translator code
2. Need to understand operator handling thoroughly
3. Risk of introducing new bugs
4. Already spent significant time investigating

---

## Recommended Next Steps

1. **Find comparison operator handler** in translator
2. **Trace metadata flow** for array operations
3. **Implement metadata propagation** for comparison fragments
4. **Test fix** with `name = name` expression
5. **Run compliance suite** to measure impact

---

**Status**: Root cause identified, fix strategy clear, implementation deferred
**Priority**: HIGH - blocks ~80-120 tests
**Complexity**: MEDIUM - translator modification required
