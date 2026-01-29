# Task SP-108-003: Collection Functions - Core Operations

**Created:** 2026-01-28
**Sprint:** SP-108
**Category:** Collection Functions
**Impact:** 76 tests (46.1% → 100%, +8.1% overall compliance)
**Effort:** 16-20 hours
**Priority:** P1

---

## Task Description

Complete the collection functions category to achieve 100% compliance. Currently at 46.1% (65/141 tests passing) with 76 failing tests covering collection manipulation, filtering, and aggregation operations.

---

## Current State

**Passing Tests:** 65/141 (46.1%)
**Failing Tests:** 76
**Gap:** 53.9%

### Key Collection Functions in FHIRPath

1. **Filtering & Selection:**
   - `where(condition)` - Filter collection by condition
   - `select(projection)` - Transform collection elements
   - `repeat(projection)` - Transform and flatten

2. **Quantifiers:**
   - `exists()` - Test if collection has elements
   - `all(condition)` - Test if all elements satisfy condition
   - `subset(subset)` - Test if subset is contained
   - `superset(set)` - Test if superset contains collection

3. **Aggregation:**
   - `aggregate(init, expression)` - Aggregate collection
   - `count()` - Count elements
   - `sum()`, `min()`, `max()`, `avg()` - Statistical functions

4. **Manipulation:**
   - `distinct()` - Remove duplicates
   - `union(other)` - Combine collections
   - `intersect(other)` - Find common elements
   - `exclude(other)` - Remove elements

5. **Navigation:**
   - `first()`, `last()` - Get first/last element
   - `tail()` - All except first
   - `skip(n)` - Skip first n elements
   - `take(n)` - Take first n elements

---

## Root Cause Analysis

### 1. `where()` Clause Evaluation
**Issue:** Filtering collections by condition may not work correctly

**Test Cases:** Various `where()` expressions
**Expected:** Collection filtered by condition
**Actual:** Incorrect filtering or missing elements

**Location:** Collection function implementation in SQL translator

**Fix Strategy:**
- Review `where()` SQL generation
- Ensure proper subquery or CTE handling
- Fix predicate evaluation logic
- Test with complex conditions

### 2. `select()` Projection
**Issue:** Transforming collection elements may not work

**Test Cases:** Various `select()` expressions
**Expected:** Collection with transformed elements
**Actual:** Incorrect transformation or SQL errors

**Location:** Collection function implementation

**Fix Strategy:**
- Review `select()` SQL generation
- Ensure proper projection logic
- Handle nested expressions correctly
- Test with complex transformations

### 3. Quantifier Functions
**Issue:** `all()`, `exists()`, `subset()`, `superset()` may have issues

**Test Cases:** Quantifier expressions
**Expected:** Correct boolean results
**Actual:** Incorrect boolean values or errors

**Location:** Quantifier function implementations

**Fix Strategy:**
- Implement missing quantifier functions
- Fix evaluation logic for existing ones
- Handle empty collections correctly
- Test edge cases

### 4. `aggregate()` Operations
**Issue:** Aggregation may not work for all cases

**Test Cases:** `aggregate()` with various expressions
**Expected:** Correct aggregation results
**Actual:** Incorrect results or missing implementation

**Location:** Aggregation function implementation

**Fix Strategy:**
- Implement `aggregate()` function
- Handle init value correctly
- Support custom aggregation expressions
- Test with various aggregations

### 5. Collection Type Handling
**Issue:** Type inference and handling may be incorrect

**Test Cases:** Collections of complex types
**Expected:** Correct type handling
**Actual:** Type errors or incorrect results

**Location:** Type system and SQL translator

**Fix Strategy:**
- Review collection type inference
- Ensure proper SQL type handling
- Fix type coercion for collections
- Test with various collection types

---

## Implementation Plan

### Step 1: Fix `where()` Clause (3-4 hours)
1. Review current `where()` implementation
2. Identify SQL generation issues
3. Fix predicate evaluation logic
4. Ensure proper CTE/subquery handling
5. Test with various conditions

### Step 2: Fix `select()` Projection (3-4 hours)
1. Review current `select()` implementation
2. Fix projection SQL generation
3. Handle nested expressions correctly
4. Ensure proper column handling
5. Test with various transformations

### Step 3: Implement Quantifiers (3-4 hours)
1. Implement missing quantifiers:
   - `all(condition)`
   - `subset(subset)`
   - `superset(set)`
2. Fix existing `exists()` if needed
3. Handle empty collections correctly
4. Test all quantifiers

### Step 4: Implement `aggregate()` (2-3 hours)
1. Implement `aggregate(init, expression)`
2. Handle init value correctly
3. Support custom aggregation expressions
4. Test with various aggregations

### Step 5: Fix Collection Type Handling (2-3 hours)
1. Review collection type inference
2. Fix SQL type handling for collections
3. Ensure proper type coercion
4. Test with various collection types

### Step 6: Comprehensive Testing (3-4 hours)
1. Run all collection function tests
2. Group remaining failures by root cause
3. Fix remaining issues
4. Verify 100% compliance
5. Test both DuckDB and PostgreSQL

---

## Testing Strategy

### Unit Tests
```bash
# Run collection function tests
pytest tests/unit/fhirpath/functions/test_collection_functions.py -v
```

### Compliance Tests
```bash
# Run official collection function tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py -k "collection" -v
```

### Verification
- All 141 collection function tests passing
- No regressions in other categories
- Both DuckDB and PostgreSQL passing

---

## Success Criteria

- [ ] All 141 collection function tests passing (100%)
- [ ] `where()` filtering working correctly
- [ ] `select()` projection working correctly
- [ ] All quantifiers implemented and working
- [ ] `aggregate()` operations working
- [ ] Collection type handling correct
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both database dialects passing

---

## Files to Modify

**Likely Targets:**
- `fhir4ds/main/fhirpath/functions/collection_functions.py` - Collection function implementations
- `fhir4ds/main/fhirpath/sql/translator.py` - SQL generation for collections
- `fhir4ds/main/fhirpath/sql/cte/` - CTE building for collections
- `fhir4ds/main/fhirpath/types/type_registry.py` - Collection type handling

---

## Collection Function Priority

**High Priority (Core):**
- `where()` - Essential for filtering
- `select()` - Essential for transformation
- `exists()` - Essential for testing
- `count()`, `first()`, `last()` - Already mostly working

**Medium Priority (Common):**
- `all()`, `subset()`, `superset()` - Useful quantifiers
- `distinct()` - Common operation
- `aggregate()` - Custom aggregations

**Low Priority (Advanced):**
- `repeat()` - Complex transformation
- `union()`, `intersect()`, `exclude()` - Set operations

---

## Notes

- Collection functions operate on collections (multi-value results)
- Single values are treated as single-element collections
- Empty collections are valid results
- `where()` and `select()` should preserve order
- Quantifiers should return boolean, not collection
- `aggregate()` init value is used for empty collections

---

## References

- FHIRPath Specification: Collection Functions
- Compliance Report: `compliance_report_sp107_official.json`
- Previous Work: SP-105 (Collection column preservation)
