# Task SP-109-004: Collection Functions - CTE Column Preservation

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 72 tests (48.9% → 100%, +7.7% overall)
**Effort:** 20-24 hours
**Priority:** P0 (Most Complex)
**Status:** Pending

---

## Objective

Implement comprehensive CTE column preservation and complete collection function implementations to achieve 100% compliance in this category. This is the most complex task requiring architectural improvements.

---

## Current State

**Collection Functions: 48.9% (69/141 tests passing)**

### Key Issues Identified

1. **Column Reference Errors in CTEs**
   - `name.take(2).first()` fails: "Referenced column 'name_item' not found"
   - Intermediate columns not preserved through CTE chain
   - Nested collection operations lose context

2. **Set Comparison Functions Not Implemented**
   - `supersetOf()` not implemented
   - `subsetOf()` not implemented
   - Need set operation logic in SQL

3. **`select()` with Lambda Variables**
   - Lambda variable scope issues in projection
   - `Patient.name.select(given | family)` fails
   - Context not preserved through select

4. **`repeat()` with Non-JSON Values**
   - `Patient.name.repeat('test')` fails
   - String literals treated as JSON
   - Type conversion needed

5. **`single()` Collection Validation**
   - `Patient.name.single()` not implemented
   - Need to validate single-item collections
   - Error handling for non-single collections

6. **Quantifiers Not Implemented**
   - `allTrue()` not implemented
   - `anyTrue()` not implemented
   - Need boolean aggregation logic

---

## Implementation Plan

### Step 1: Implement Comprehensive CTE Column Preservation (6-8 hours)

**Problem:** Intermediate columns lost in nested operations

**Solution:**
1. Audit CTE builder column tracking
2. Implement column dependency analysis
3. Track all referenced columns through CTE chain
4. Preserve columns needed by subsequent operations
5. Add column pruning to optimize performance

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/cte.py`
- `fhir4ds/main/fhirpath/sql/context.py`

**Key Changes:**
- Add `ColumnDependencyAnalyzer` class
- Track column usage through expression tree
- Modify CTE builder to preserve required columns
- Add optimization to remove unused columns

### Step 2: Implement Set Comparison Functions (4-5 hours)

**Problem:** `supersetOf()` and `subsetOf()` not implemented

**Solution:**
1. Implement `supersetOf()` in SQL
2. Implement `subsetOf()` in SQL
3. Use EXISTS or array containment logic
4. Test with various collection types

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/sql/test_translator_set_operations.py`

**SQL Logic:**
```sql
-- subsetOf: A.subsetOf(B)
SELECT ... WHERE NOT EXISTS (
    SELECT 1 FROM unnest(A) AS a_elem
    WHERE a_elem NOT IN (SELECT * FROM unnest(B))
)

-- supersetOf: A.supersetOf(B)
SELECT ... WHERE B.subsetOf(A)
```

### Step 3: Fix `select()` Lambda Variable Scope (3-4 hours)

**Problem:** Lambda variables not tracked correctly in projection

**Solution:**
1. Review lambda variable context tracking
2. Fix scope handling in `select()`
3. Preserve context through projection
4. Test nested lambda expressions

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/main/fhirpath/sql/context.py`

### Step 4: Implement `repeat()` Type Conversion (2-3 hours)

**Problem:** String literals not converted to JSON

**Solution:**
1. Detect non-JSON values in `repeat()`
2. Convert string literals to JSON values
3. Handle other types (numbers, booleans)
4. Test `repeat()` with various types

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`

### Step 5: Implement `single()` Validation (2-3 hours)

**Problem:** `single()` not implemented

**Solution:**
1. Implement `single()` in SQL
2. Validate collection has exactly one item
3. Return error or empty collection for invalid input
4. Test edge cases

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`

**SQL Logic:**
```sql
-- single()
SELECT ... WHERE COUNT(*) = 1
```

### Step 6: Implement Quantifiers (3-4 hours)

**Problem:** `allTrue()` and `anyTrue()` not implemented

**Solution:**
1. Implement `allTrue()` in SQL
2. Implement `anyTrue()` in SQL
3. Use boolean aggregation logic
4. Test with various boolean collections

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`

**SQL Logic:**
```sql
-- allTrue()
SELECT ... WHERE bool_and(value)

-- anyTrue()
SELECT ... WHERE bool_or(value)
```

---

## Testing Strategy

### Unit Tests
1. Test CTE column preservation
2. Test set comparison functions
3. Test lambda variable scope
4. Test `repeat()` type conversion
5. Test `single()` validation
6. Test quantifiers

### Integration Tests
1. Test nested collection operations
2. Test collection functions with CTEs
3. Test collection functions across databases
4. Test complex collection expressions

### Compliance Tests
1. Run full collection_functions test suite
2. Verify 100% pass rate
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All 141 collection_functions tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 86.2%+

---

## Risk Assessment

**Risk Level:** High

**Risks:**
- CTE architecture changes are complex
- Column preservation may affect performance
- Set operations may be database-specific
- Lambda scope may have subtle bugs

**Mitigation:**
- Start with isolated column preservation
- Test CTE structure changes thoroughly
- Use standard SQL where possible
- Add comprehensive logging for debugging
- Consider performance implications early

---

## Dependencies

- None (can start immediately, but most complex)

---

## Notes

- This is the most complex task in the sprint
- CTE column preservation is a foundational improvement
- Will benefit many other operations
- Take time to get architecture right
- Performance testing is important
- May need multiple iterations to get correct
