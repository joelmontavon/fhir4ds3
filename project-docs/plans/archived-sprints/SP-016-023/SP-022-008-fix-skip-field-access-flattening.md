# Task: Fix skip() + Field Access Array Flattening

**Task ID**: SP-022-008
**Sprint**: 022
**Task Name**: Fix skip() + Field Access Array Flattening
**Assignee**: Junior Developer
**Created**: 2025-12-29
**Last Updated**: 2025-12-30

---

## Task Overview

### Description
When `skip(n)` is followed by field access on an array field (e.g., `.given`), the result returns the nested JSON array string instead of flattening/unnesting the array values. This is an extension of the SP-022-004 fix which addressed subset functions but didn't fully handle the case where the accessed field is itself an array.

**Current Behavior (WRONG):**
```
Expression: Patient.name.skip(1).given

Patient data:
  name[0] = {"given": ["Peter", "James"]}
  name[1] = {"given": ["Jim"]}

Current result: ['["Jim"]']  -- JSON array string, not flattened
Expected result: ['Jim']     -- Flattened individual values
```

**Generated SQL (Current):**
```sql
cte_3 AS (
    SELECT cte_2.id, cte_2.resource, cte_1_order,
           json_extract_string(result, '$.given') AS result  -- Returns ["Jim"] as string
    FROM cte_2
)
```

**Expected SQL:**
```sql
cte_3 AS (
    SELECT cte_2.id, cte_2.resource, cte_1_order, cte_3_order, given_item AS result
    FROM cte_2, LATERAL UNNEST(json_extract(result, '$.given[*]')) AS given_item
)
```

### Category
- [x] Bug Fix

### Priority
- [x] Medium (Valuable but not essential)

---

## Requirements

### Functional Requirements
1. **skip() + array field**: `Patient.name.skip(1).given` should flatten the given array
2. **take() + array field**: `Patient.name.take(1).given` should flatten similarly
3. **first() + array field**: `Patient.name.first().given` should flatten similarly
4. **last() + array field**: `Patient.name.last().given` should flatten similarly
5. **Array detection**: Field access after subset should check if field is array type

### Acceptance Criteria
- [x] `Patient.name.skip(1).given` returns flattened values (e.g., `['Jim']` not `['["Jim"]']`)
- [x] `Patient.name.take(1).given` returns flattened values
- [x] `Patient.name.first().given` returns flattened values
- [x] `Patient.name.last().given` returns flattened values
- [x] Works with both DuckDB and PostgreSQL
- [x] All existing passing tests continue to pass

---

## Technical Specifications

### Root Cause Analysis

SP-022-004 added `current_element_column` and `current_element_type` tracking so that field access after `skip()`/`first()` uses the result column. However, there were two issues:

1. **element_type was not being set**: The `target_path` was `None` when `_get_element_type_for_path()` was called, resulting in `element_type = None`
2. **Array field access used `json_extract_string()`**: Even with element_type available, array fields need UNNEST, not json_extract_string

**The fix (two parts):**
1. Derive `element_type` from the UNNEST fragment's `source_path` metadata when `target_path` is unavailable
2. In `visit_identifier`, check if the accessed field is an array type and generate UNNEST fragment instead of simple extraction

### Files Modified

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modified `_translate_first()`: Added SP-022-008 fallback to derive element_type from UNNEST source_path
   - Modified `_translate_last()`: Added SP-022-008 fallback to derive element_type from UNNEST source_path
   - Modified `_translate_skip()`: Added SP-022-008 fallback to derive element_type from UNNEST source_path
   - Modified `_translate_tail()`: Added SP-022-008 fallback to derive element_type from UNNEST source_path
   - Modified `_translate_take()`: Added SP-022-008 fallback to derive element_type from UNNEST source_path
   - Modified `visit_identifier()` (when `current_element_column` is set): Added array detection and UNNEST fragment generation

---

## Implementation Summary

### Changes Made

1. **Element Type Resolution Fix**:
   When `target_path` is not available (which happens after translation clears the context), we now fall back to parsing the UNNEST fragment's `source_path` metadata (e.g., `$.name[*]`) to derive the element type (e.g., `HumanName`).

2. **Array Field Detection in visit_identifier**:
   When `current_element_column` is set and we're accessing a field, we now check if that field is an array using `type_registry.is_array_element()`. If it is, we generate a fragment with `requires_unnest=True` instead of using `json_extract_string()`.

### Affected Functions
- `_translate_first()`
- `_translate_last()`
- `_translate_skip()`
- `_translate_tail()`
- `_translate_take()`
- `visit_identifier()`

---

## Testing

### Verified Test Cases

**DuckDB:**
- ✅ `Patient.name.skip(1).given` - returns flattened `"Jim"`
- ✅ `Patient.name.take(1).given` - returns flattened `"Peter"`, `"James"`
- ✅ `Patient.name.tail().given` - returns flattened `"Jim"`
- ✅ `Patient.name.first().given` - returns flattened `"Peter"`, `"James"`
- ✅ `Patient.name.last().given` - returns flattened `"Jim"`
- ✅ `Patient.name.first().family` - still works for scalar fields

**PostgreSQL:**
- ✅ `Patient.name.skip(1).given` - returns flattened values
- ✅ `Patient.name.take(1).given` - returns flattened values
- ✅ `Patient.name.first().given` - returns flattened values
- ✅ `Patient.name.last().given` - returns flattened values

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Array detection incorrect | Low | Medium | Uses TypeRegistry with comprehensive FHIR R4 definitions |
| UNNEST breaks scalar fields | Low | High | Only applies to detected array fields; scalar fields continue using json_extract |
| Element type derivation fails | Low | Medium | Falls back to None, preserving existing behavior |

---

## Success Metrics

### Quantitative Measures
- All subset function + array field access expressions now correctly flatten arrays
- Cross-database compatibility maintained (DuckDB and PostgreSQL)

### Compliance Impact
- **Before**: Result is nested array `["Jim"]` as a JSON string
- **After**: Result is individual flattened value `"Jim"`

---

## Dependencies

### Prerequisites
- SP-022-004 (Fix collection subset functions) - Already completed

---

## Progress Tracking

### Status
- [x] Completed and Merged to main

### Completion Checklist
- [x] Root cause confirmed with debugging
- [x] Element type derivation from UNNEST source_path implemented
- [x] Array detection logic implemented in visit_identifier
- [x] UNNEST used for array fields after subset
- [x] All subset functions fixed (first, last, skip, tail, take)
- [x] DuckDB tests passing
- [x] PostgreSQL tests passing
- [x] No regressions in existing tests (pre-existing failures unchanged)

---

**Task Created**: 2025-12-29
**Task Completed**: 2025-12-30
**Merged to main**: 2025-12-30
**Status**: Completed and Merged
