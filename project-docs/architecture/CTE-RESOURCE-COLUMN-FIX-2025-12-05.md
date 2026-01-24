# CTE Resource Column Propagation Fix

**Date**: 2025-12-05 (Evening)
**Issue**: Critical architectural bug blocking ~100-150 compliance tests
**Status**: FIXED - Testing in progress
**Impact**: High - Fixes fundamental CTE chain issue

---

## Executive Summary

Fixed critical bug where the `resource` column was not being propagated through CTE chains, causing "Referenced column 'resource' not found" errors in multi-step FHIRPath expressions.

**Before Fix**: 452/934 tests (48.4%)
**After Fix**: Testing in progress...

---

## The Problem

### Error Pattern

Hundreds of compliance tests were failing with:
```
BinderException: Referenced column "resource" not found in FROM clause!
Candidate bindings: "cte_1_order", "cte_2_order"
```

### Root Cause

When building CTE chains for multi-step FHIRPath expressions like `Patient.name.empty()`:

1. **CTE_1** would select from `resource` table and extract data
2. **CTE_2** would select from CTE_1 and try to reference `resource`... **but CTE_1 didn't include `resource` in its SELECT list!**

### Example Failing Expression

**Expression**: `Patient.name.empty()`

**Generated SQL** (BEFORE FIX):
```sql
WITH
  cte_1 AS (
    SELECT resource.id, ROW_NUMBER() OVER () AS cte_1_order, name_item.unnest AS name_item
    FROM resource, LATERAL UNNEST(json_extract(resource, '$.name[*]')) AS name_item
    --  ❌ No 'resource' column in SELECT list!
  ),
  cte_2 AS (
    SELECT cte_1.id, cte_1_order,
      (CASE WHEN json_extract(resource, '$.name') IS NULL ...
      -- ❌ ERROR: 'resource' not found in cte_1!
    FROM cte_1
  )
SELECT * FROM cte_2;
```

---

## The Fix

### Location

`fhir4ds/fhirpath/sql/cte.py`
- Modified: `CTEBuilder._wrap_simple_query()` (lines 460-515)
- Modified: `CTEBuilder._wrap_unnest_query()` (lines 517-642)

### Changes Made

**Added resource column to SELECT lists in both methods:**

```python
# Build column list: id, resource (if available), ordering columns, result
columns = [id_column]

# FIX: Include resource column to propagate it through CTE chain
# This fixes "Referenced column 'resource' not found" errors
if source_table == "resource":
    # First CTE selecting from resource table
    columns.append("resource")
elif source_table and not source_table.startswith("cte_"):
    # Selecting from some other table (not a CTE)
    columns.append(f"{source_table}.resource")
else:
    # Selecting from a previous CTE - pass through resource if it has it
    columns.append(f"{source_table}.resource")

columns.extend(ordering_columns)
columns.append(f"{expression} AS {result_alias}")
```

### Generated SQL (AFTER FIX)

```sql
WITH
  cte_1 AS (
    SELECT resource.id, resource, ROW_NUMBER() OVER () AS cte_1_order, name_item.unnest AS name_item
    FROM resource, LATERAL UNNEST(json_extract(resource, '$.name[*]')) AS name_item
    --  ✅ 'resource' column now included!
  ),
  cte_2 AS (
    SELECT cte_1.id, cte_1.resource, cte_1_order,
      (CASE WHEN json_extract(resource, '$.name') IS NULL ...
      --  ✅ 'resource' now available from cte_1!
    FROM cte_1
  )
SELECT * FROM cte_2;
```

---

## Testing

### Manual Test

**Expression**: `Patient.name.empty()`

**Before Fix**:
```
Binder Error: Referenced column "resource" not found in FROM clause!
```

**After Fix**:
```
✅ SQL EXECUTED SUCCESSFULLY!
Result: [(1, '{"resourceType": "Patient", ...}', 1, False)]
```

### Compliance Suite

**Running**: Full 934-test compliance suite to measure impact

**Expected Impact**: +80-120 tests (estimate based on error frequency)

**Baseline**: 452/934 (48.4%)

**Target**: 530-570 (57-61%)

---

## Files Modified

1. `fhir4ds/fhirpath/sql/cte.py`
   - Lines 460-515: `_wrap_simple_query()` - Added resource column propagation
   - Lines 517-642: `_wrap_unnest_query()` - Added resource column propagation

---

## Impact Analysis

### Categories Expected to Improve

**Collection Functions** (currently 35/141 = 24.8%):
- `Patient.name.empty()` tests
- `Patient.name.count()` tests
- `.not()`, `.exists()` tests on collections

**Function Calls** (currently 48/113 = 42.5%):
- Multi-step function chains
- Functions operating on extracted data

**Comparison Operators** (currently 217/338 = 64.2%):
- Comparisons after extraction steps

### Root Cause Categories

These errors all shared the same root cause:
- ❌ `Patient.name.empty() = false`
- ❌ `Patient.name.count() = 3`
- ❌ `Patient.name.given.count() = 5`
- ❌ `Patient.link.empty()`
- ❌ `Patient.name.empty().not()`

All failed with "Referenced column 'resource' not found"

---

## Why This Happened

### Design Oversight

The CTE builder was designed to create minimal SELECT lists to reduce query size:
- Only included `id` column
- Only included `ordering` columns for UNNEST operations
- Only included `result` column for the expression

**Missing**: The `resource` column itself!

### Why It Wasn't Caught Earlier

1. **Simple tests passed**: Single-step expressions like `Patient.name` worked fine
2. **First CTE has resource**: The problem only manifested in CTE chains
3. **Error was generic**: "Column not found" could be many things

---

## Lessons Learned

### What Worked ✅

1. **Deep investigation paid off** - Traced entire SQL generation process
2. **Tested with real expressions** - Generated actual SQL to see the problem
3. **Simple fix once understood** - Only ~20 lines of code changed
4. **Immediate verification** - Tested fix before running full suite

### Process Improvements 💡

1. **Test CTE chains** - Unit tests should cover multi-step expressions
2. **Validate column propagation** - Ensure required columns pass through CTEs
3. **Better error messages** - Could detect missing `resource` earlier

### User Insight Was Correct ✅

User said: "there must be something more fundamental wrong"

**They were right!** This wasn't about datetime types or parser bugs - it was a fundamental architectural issue in how CTEs were assembled.

---

## Next Steps

### Immediate
- [ ] Wait for compliance test results
- [ ] Document before/after metrics
- [ ] Create git commit with fix

### Follow-up
- [ ] Add unit tests for resource column propagation
- [ ] Review other column propagation (are we missing anything else?)
- [ ] Consider adding validation to CTE assembler

---

## Compliance Metrics

### Before Fix
```
Total: 934 tests
Passed: 452 (48.4%)
Failed: 482 (51.6%)

Categories:
- Collection_Functions: 35/141 (24.8%)  ← Expected improvement
- Function_Calls: 48/113 (42.5%)       ← Expected improvement
- Comparison_Operators: 217/338 (64.2%) ← Expected improvement
- Type_Functions: 37/116 (31.9%)
- String_Functions: 46/65 (70.8%)
- Math_Functions: 22/28 (78.6%)
- Path_Navigation: 9/10 (90.0%)
```

### After Fix
```
Testing in progress...
```

---

## Technical Details

### Column Order in SELECT

The fix maintains this column order:
1. `id` column (for row identification)
2. `resource` column (for downstream references)
3. Ordering columns (for UNNEST operations)
4. Result column (MUST BE LAST - test runner expects this)

### Source Table Detection

The fix handles three cases:
1. **`source_table == "resource"`**: First CTE, select from `resource` table
2. **Non-CTE source**: Some other table (add qualified column)
3. **CTE source**: Previous CTE (pass through `{cte}.resource`)

---

**Prepared by**: Senior Solution Architect/Engineer (with AI assistance)
**Date**: 2025-12-05
**Status**: Fix implemented, testing in progress
**Credit**: User correctly identified "something more fundamental wrong"
