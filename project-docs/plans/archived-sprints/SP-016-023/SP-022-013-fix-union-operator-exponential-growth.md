# Task: Fix Union Operator Exponential SQL Growth

**Task ID**: SP-022-013
**Sprint**: 022
**Task Name**: Fix Union Operator Exponential SQL Growth
**Assignee**: Junior Developer
**Created**: 2025-12-30
**Last Updated**: 2025-12-31
**Status**: ✅ COMPLETED AND MERGED

---

## Task Overview

### Description
The union operator (`|`) generates SQL that grows exponentially with each additional element. This causes Out of Memory (OOM) errors for expressions with more than ~5 elements and blocks 4 compliance tests.

**Before Fix (BROKEN):**
```
Expression: (1|2|3|4|5)
SQL Size: 1,358,754 characters (1.4 MB)

Expression: (1|2|3|4|5|6|7|8|9)
SQL Size: ~136 GB (estimated) → OOM CRASH
```

**After Fix (SOLVED):**
```
Expression: (1|2|3|4|5)
SQL Size: 1,403 characters (~280 chars/element)

Expression: (1|2|3|4|5|6|7|8|9)
SQL Size: 2,431 characters (~270 chars/element) → WORKS!
```

**Growth Comparison:**
| Elements | Before (chars) | After (chars) | Improvement |
|----------|----------------|---------------|-------------|
| 2 | 1,224 | 632 | 2x smaller |
| 3 | 13,454 | 889 | 15x smaller |
| 4 | 135,754 | 1,146 | 118x smaller |
| 5 | 1,358,754 | 1,403 | 968x smaller |
| 9 | ~136 GB (OOM) | 2,431 | Works! |

### Category
- [x] Bug Fix
- [x] Performance Optimization

### Priority
- [x] Critical (Blocker for sprint goals)

---

## Requirements

### Functional Requirements
1. **Linear SQL growth**: Union of N elements should produce O(N) SQL, not O(10^N)
2. **Correct semantics**: Union must preserve order and handle duplicates per FHIRPath spec
3. **Null handling**: Empty collections in unions must be handled correctly
4. **Type preservation**: Union of mixed types must work correctly

### Non-Functional Requirements
- **Performance**: SQL generation must complete in < 1 second for any reasonable union size
- **Memory**: SQL generation must use < 100 MB for unions up to 100 elements
- **Database Support**: Must work identically on DuckDB and PostgreSQL
- **Compliance**: Must pass all 4 blocked aggregate tests (268-271)

### Acceptance Criteria
- [x] `(1|2|3|4|5|6|7|8|9)` generates SQL in < 1 second
- [x] `(1|2|3|4|5|6|7|8|9)` SQL is < 10 KB (actual: 2.4 KB)
- [ ] `(1|2|3|4|5|6|7|8|9).aggregate($this+$total, 0)` returns 45 (blocked by aggregate function bug, separate task)
- [ ] All 4 previously skipped aggregate tests pass (blocked by aggregate function bug, separate task)
- [x] No regressions in existing union tests
- [x] Works with both DuckDB and PostgreSQL (SQL generation verified, PostgreSQL not available for runtime test)

**Note**: The aggregate tests still fail due to a pre-existing bug in the aggregate function that doesn't properly use the input collection expression from the previous fragment. This is a separate issue and should be tracked in a new task.

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: `_translate_binary_operator()`, `_translate_union_chain()` methods
- **Dialect Classes**: Uses existing `enumerate_json_array()` and `aggregate_to_json_array()` methods

### File Modifications

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modified `_translate_binary_operator()` to intercept union operators before visiting children
   - Added `_translate_union_chain()` method for linear-growth union handling
   - Added `_collect_union_operands()` helper to flatten chained unions
   - Added `_build_linear_union_sql()` helper to generate O(N) SQL

### Root Cause Analysis

The old implementation at `_translate_union_operator()` was called AFTER children were visited, meaning by the time we handled the union, both operands were already fully translated to SQL. The CASE WHEN structure then duplicated each operand expression 6+ times, causing exponential growth.

For `(1|2|3|4)` which parses as `(((1|2)|3)|4)`:
1. `(1|2)` → produces SQL_12 (~1KB)
2. `(SQL_12|3)` → SQL_12 duplicated 6+ times (~10KB)
3. `((SQL_12|3)|4)` → the ~10KB SQL duplicated 6+ times (~100KB)

Each level multiplied by ~10x, causing exponential growth.

### Solution Implemented

**Key Insight**: Intercept union operators BEFORE visiting children in `_translate_binary_operator()`.

**New Approach**:
1. When we encounter a union operator, call `_translate_union_chain()` instead of the normal binary operator path
2. `_collect_union_operands()` walks the AST to collect ALL operands from the chain (flattening nested unions)
3. Each operand is translated exactly ONCE
4. `_build_linear_union_sql()` generates a single UNION ALL query combining all operands

**Generated SQL Example** for `(1|2|3)`:
```sql
(COALESCE((SELECT json_group_array(union_val ORDER BY union_src, union_idx)
  FROM (
    SELECT union_val, 0 AS union_src, union_idx
    FROM (SELECT key AS union_idx, value AS union_val FROM json_each(json_array(1))) AS operand_0
    UNION ALL
    SELECT union_val, 1 AS union_src, union_idx
    FROM (SELECT key AS union_idx, value AS union_val FROM json_each(json_array(2))) AS operand_1
    UNION ALL
    SELECT union_val, 2 AS union_src, union_idx
    FROM (SELECT key AS union_idx, value AS union_val FROM json_each(json_array(3))) AS operand_2
  ) AS union_combined), json_array()))
```

This produces O(N) SQL growth (~270 chars per element).

---

## Dependencies

### Prerequisites
- Understanding of current union translation logic
- Familiarity with CTE patterns in the codebase

### Blocking Tasks
- None

### Dependent Tasks
- This blocks tests 268-271 (aggregate tests) - **Note**: These tests still fail due to a separate bug in the aggregate function

---

## Implementation Summary

### Completed Steps

1. **Root cause analysis** ✓
   - Identified the duplication in CASE WHEN statements
   - Documented the exponential growth pattern

2. **Solution design** ✓
   - Intercept union operators before child translation
   - Collect all operands from AST
   - Translate each operand once
   - Build linear-growth SQL using UNION ALL

3. **Implementation** ✓
   - Added early return for union operators in `_translate_binary_operator()`
   - Implemented `_translate_union_chain()` for the new approach
   - Implemented `_collect_union_operands()` to flatten nested unions
   - Implemented `_build_linear_union_sql()` for O(N) SQL generation

4. **Testing** ✓
   - Verified linear SQL growth (270 chars/element vs 10x exponential)
   - Tested correctness with DuckDB (all union tests pass)
   - Verified order preservation: `(3|1|2)` → `[3, 1, 2]`
   - Verified duplicate preservation: `(1|2|2|3)` → `[1, 2, 2, 3]`
   - No regressions in existing operator tests (38 passed)

---

## Progress Tracking

### Status
- [x] Completed - reviewed and merged to main (2025-12-31)

### Completion Checklist
- [x] Root cause fully understood
- [x] Solution design reviewed and approved
- [x] `_collect_union_operands()` helper implemented
- [x] `_translate_union_chain()` implemented
- [x] `_build_linear_union_sql()` implemented
- [x] SQL size is O(N) not O(10^N)
- [x] `(1|2|3|4|5|6|7|8|9)` works without OOM
- [x] DuckDB tests passing
- [x] PostgreSQL SQL generation verified (runtime not available)
- [x] No regressions in existing tests

### Known Limitations
- Aggregate tests 268-271 still fail due to a separate bug in the aggregate function that doesn't use the input collection from the previous fragment
- PostgreSQL runtime testing not available in this environment (SQL generation verified)

---

## Test Results

### SQL Growth Verification
```
Elements: 2, SQL Length: 632 chars (316 chars/element)
Elements: 3, SQL Length: 889 chars (296 chars/element)
Elements: 4, SQL Length: 1,146 chars (286 chars/element)
Elements: 5, SQL Length: 1,403 chars (280 chars/element)
Elements: 6, SQL Length: 1,660 chars (276 chars/element)
Elements: 7, SQL Length: 1,917 chars (273 chars/element)
Elements: 8, SQL Length: 2,174 chars (271 chars/element)
Elements: 9, SQL Length: 2,431 chars (270 chars/element)

Target: Linear growth means chars/element should be roughly constant ✓
```

### Correctness Verification
```
✓ PASS: (1|2) → [1, 2]
✓ PASS: (1|2|3) → [1, 2, 3]
✓ PASS: (1|2|3|4|5) → [1, 2, 3, 4, 5]
✓ PASS: (1|2|3|4|5|6|7|8|9) → [1, 2, 3, 4, 5, 6, 7, 8, 9]
✓ PASS: (1|2|2|3) → [1, 2, 2, 3] (duplicates preserved)
✓ PASS: (3|1|2) → [3, 1, 2] (order preserved)
```

---

**Task Created**: 2025-12-30
**Reviewed**: 2025-12-31
**Merged to main**: 2025-12-31
**Status**: ✅ COMPLETED AND MERGED

### Review Summary
- **Reviewer**: Senior Solution Architect
- **Review Document**: `project-docs/plans/reviews/SP-022-013-review.md`
- **Result**: APPROVED - Fix correctly addresses exponential SQL growth with proper architecture compliance
