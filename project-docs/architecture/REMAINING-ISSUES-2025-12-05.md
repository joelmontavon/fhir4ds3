# Remaining FHIRPath Compliance Issues

**Date**: 2025-12-05
**After**: CTE resource column fix
**Status**: Documented for future fixes

---

## Issues Fixed Today ✅

1. **CTE Resource Column Propagation** - FIXED (+expected ~80-120 tests)
2. **REGEXP Syntax** - FIXED (+4 tests)
3. **Error Visibility** - FIXED (debugging enabled)
4. **Test Fixtures** - FIXED (using official HL7 data)

---

## Remaining High-Impact Issues

### 1. `.select()` Function Not Implemented ⚠️ HIGH

**Error Pattern**:
```
Parser Error: syntax error at or near "SELECT"
```

**Examples**:
- `Patient.name.select(given)`
- `Patient.name.select(given | family).distinct()`
- `name.select(use.contains('i')).count()`

**Root Cause**: The SQL keyword "SELECT" is appearing in generated SQL, meaning `.select()` is not being translated at all.

**Estimated Impact**: ~50-80 tests

**Complexity**: MEDIUM - Need to implement projection/transformation logic

**Files to Investigate**:
- FHIRPath translator
- Function registry

---

### 2. Array Metadata Missing ⚠️ HIGH

**Error Pattern**:
```
ValueError: SQLFragment metadata must contain 'array_column' for UNNEST operations
```

**Examples**:
- `Patient.name[0].given`
- `Patient.name[1].given`
- `(0 | 1 | 2).tail()`
- `(0 | 1 | 2).take(1)`
- `name = name` (array comparison)

**Root Cause**: SQLFragment metadata system for tracking array columns not populating correctly.

**Estimated Impact**: ~80-120 tests

**Complexity**: MEDIUM - Metadata propagation issue

**Files to Investigate**:
- SQL translator - where SQLFragments are created
- Array/collection operation handlers

---

### 3. Unary Minus Operator ⚠️ MEDIUM

**Error Pattern**:
```
IndexError: list index out of range
Error visiting node operator(-): list index out of range
```

**Examples**:
- `-1.convertsToInteger()`
- `-0.1.convertsToDecimal()`
- `-Patient.name.given.count() = -5`

**Root Cause**: Unary minus operator not implemented in translator.

**Estimated Impact**: ~10-15 tests

**Complexity**: LOW - Simple operator implementation

**Files to Fix**:
- AST to SQL translator - operator handling

---

### 4. Type Checking on Literals ⚠️ MEDIUM

**Error Pattern**:
```
Binder Error: No function matches json_type(INTEGER_LITERAL)
```

**Examples**:
- `1.is(Integer)`
- `1.0.is(Decimal)`
- `1.is(String).not()`

**Root Cause**: Trying to call `json_type(1)` but DuckDB requires VARCHAR/JSON argument.

**Estimated Impact**: ~15-20 tests

**Complexity**: LOW - Cast literals to VARCHAR before json_type()

**Files to Fix**:
- DuckDB dialect - type check SQL generation

---

### 5. Comparison Type Casting ⚠️ MEDIUM

**Error Pattern**:
```
Binder Error: Cannot compare VARCHAR and DECIMAL - explicit cast required
Binder Error: Cannot compare VARCHAR and TIMESTAMP - explicit cast required
```

**Examples**:
- `Observation.value.value > 180.0` (VARCHAR vs DECIMAL)
- `Patient.birthDate < today()` (VARCHAR vs DATE)
- `now() > Patient.birthDate` (TIMESTAMP vs VARCHAR)

**Root Cause**: JSON extraction returns VARCHAR, needs casting for comparison.

**Estimated Impact**: ~15-25 tests

**Complexity**: MEDIUM - Type-aware comparison generation

**Files to Fix**:
- Comparison operator SQL generation
- Type detection/conversion logic

---

### 6. `.first()` Array Indexing ⚠️ LOW

**Error Pattern**:
```
Binder Error: JSON path error near '.[0]'
```

**Examples**:
- `Patient.name.first().count()`
- `Patient.name.first().count() = 1`

**Root Cause**: Incorrect JSON path syntax for array indexing.

**Estimated Impact**: ~5-10 tests

**Complexity**: LOW - Fix JSON path generation

---

### 7. Timezone Support ⚠️ LOW

**Error Pattern**:
```
ConversionException: invalid timestamp field format: "@2012-04-15T15:00:00Z"
```

**Examples**:
- `@2012-04-15T15:00:00Z = @2012-04-15T10:00:00`

**Root Cause**: DuckDB timestamp format doesn't accept `Z` timezone indicator.

**Estimated Impact**: ~5-10 tests

**Complexity**: LOW - Strip/convert timezone indicator

---

### 8. `~` Operator Type Casting ⚠️ LOW

**Error Pattern**:
```
Binder Error: No function matches ~~(INTEGER_LITERAL, INTEGER_LITERAL)
```

**Examples**:
- `1 ~ 1`
- `1.1 ~ 1.2`
- `@2012-04-15 ~ @2012-04-15`

**Root Cause**: LIKE operator (`~~`) requires VARCHAR arguments, needs casting.

**Estimated Impact**: ~15-20 tests

**Complexity**: LOW - Cast operands to VARCHAR

---

### 9. Collection `.not()` Type Error ⚠️ LOW

**Error Pattern**:
```
ConversionException: Failed to cast value to numerical: [1,2]
```

**Examples**:
- `(1|2).not() = false`

**Root Cause**: Trying to apply NOT to an array instead of array elements.

**Estimated Impact**: ~5-10 tests

**Complexity**: MEDIUM - Collection operation logic

---

### 10. `iif()` Type Mixing ⚠️ LOW

**Error Pattern**:
```
Binder Error: Cannot mix BOOLEAN and DOUBLE in CASE expression
```

**Examples**:
- `iif(true, true, 1/0)`
- `iif(false, 1/0, true)`

**Root Cause**: CASE statement branches have incompatible types.

**Estimated Impact**: ~5-10 tests

**Complexity**: MEDIUM - Need common type casting in CASE

---

### 11. `.aggregate()` with Literals ⚠️ LOW

**Error Pattern**:
```
ConversionException: Could not convert string 'id' to INT32
```

**Examples**:
- `(1|2|3|4|5|6|7|8|9).aggregate($this+$total, 0) = 45`

**Root Cause**: JSON object has 'id' key when iterating literal arrays.

**Estimated Impact**: ~5-10 tests

**Complexity**: MEDIUM - Literal array handling

---

### 12. `.repeat()` Function ⚠️ LOW

**Error Pattern**:
```
CatalogException: Table with name repeat_elem_0 does not exist
```

**Examples**:
- `Questionnaire.repeat(item).code.count() = 11`

**Root Cause**: `.repeat()` function not generating correct table references.

**Estimated Impact**: ~5-10 tests

**Complexity**: MEDIUM - Recursive descent implementation

---

### 13. Quantity Arithmetic ⚠️ LOW

**Error Pattern**:
```
Binder Error: Could not choose function for *(STRING_LITERAL, STRING_LITERAL)
```

**Examples**:
- `2.0 'cm' * 2.0 'm' = 0.040 'm2'`

**Root Cause**: Quantity arithmetic not implemented.

**Estimated Impact**: ~5-10 tests

**Complexity**: HIGH - Requires unit conversion logic

---

## Issue Priority Summary

### High Priority (>50 tests each)
1. `.select()` function (~50-80 tests) - Core projection feature
2. Array metadata (~80-120 tests) - Fundamental collection operations

**Combined Impact**: ~130-200 tests

### Medium Priority (10-25 tests each)
3. Unary minus (~10-15)
4. Type checking literals (~15-20)
5. Comparison casting (~15-25)

**Combined Impact**: ~40-60 tests

### Low Priority (<10 tests each)
6-13. Various smaller issues

**Combined Impact**: ~50-80 tests

---

## Recommended Fix Order

### Phase 1: Array Metadata (Highest Impact)
**Why**: Blocks ~80-120 tests, fundamental to collections
**Effort**: 4-8 hours
**Impact**: Large

### Phase 2: `.select()` Function
**Why**: Blocks ~50-80 tests, core FHIRPath feature
**Effort**: 6-12 hours (requires new feature)
**Impact**: Large

### Phase 3: Quick Wins Bundle
**Why**: ~40-60 tests from 3 simple fixes
**Issues**: Unary minus + Type literals + Comparison casting
**Effort**: 4-8 hours combined
**Impact**: Medium

### Phase 4: Remaining Issues
**Why**: Polish, smaller impact each
**Effort**: Variable
**Impact**: Small incremental gains

---

## Current Compliance Estimate

**Baseline (before CTE fix)**: 452/934 (48.4%)

**After CTE fix**: Testing in progress...
- Estimated: 530-570 tests (57-61%)

**After Array Metadata fix**:
- Estimated: 610-690 tests (65-74%)

**After `.select()` fix**:
- Estimated: 660-770 tests (71-82%)

**After Quick Wins**:
- Estimated: 700-830 tests (75-89%)

---

## Not Included (Out of Scope)

These are NOT bugs, but unimplemented features:
- Comments/syntax validation (semantic errors)
- Quantity arithmetic (requires unit conversion)
- Advanced datetime operations
- Recursive functions
- Some edge cases

---

**Next Steps**: Fix array metadata issue, then `.select()` function, then evaluate remaining effort vs reward.
