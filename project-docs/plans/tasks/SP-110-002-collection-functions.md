# Task SP-110-002: Collection Functions - CTE Architecture

**Created:** 2026-01-30
**Sprint:** SP-110
**Task Type:** Feature Implementation
**Complexity:** VERY_HIGH
**Priority:** P0
**Estimated Effort:** 20-30 hours

---

## Task Description

Implement comprehensive CTE column preservation and complete set comparison functions to achieve 100% pass rate in collection_functions category.

## Current State

**Category:** collection_functions
**Current Pass Rate:** 48.9% (69/141 tests passing)
**Gap:** 72 failing tests
**Impact:** +7.7% overall compliance

## Key Issues

### 1. Column Reference Errors in CTEs
- `take()`, `first()`, `last()` lose column references
- Nested CTEs don't preserve columns
- JSON structure lost in CTE chains

### 2. Set Comparison Functions Not Implemented
- `supersetOf()` - missing
- `subsetOf()` - missing
- Set equivalence comparisons

### 3. Lambda Variable Scope in `select()`
- Lambda variables not properly scoped
- Variable shadowing issues
- Context passing to lambda expressions

### 4. `repeat()` with Non-JSON Values
- Non-JSON values cause JSON serialization errors
- Type conversion before repeat
- Empty collection handling

### 5. `single()` Collection Validation
- Collection size validation
- Error handling for non-singleton collections
- Null handling

### 6. Quantifiers Not Implemented
- `allTrue()` - missing
- `anyTrue()` - missing
- Boolean logic across collections

## Implementation Plan

**ARCHITECTURAL NOTE:** DO NOT modify `parser_core/fhirpath_py/FHIRPath.g4`. All fixes go in the translator layer.

### Step 1: Implement Comprehensive CTE Column Preservation
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Ensure column preservation through CTE chains:
- Track all input columns in translation context
- Preserve JSON structure in SELECT clauses
- Fix `take()`, `first()`, `last()` column reference handling

### Step 2: Add Set Comparison Functions
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Implement set comparison function translation:
- Add `supersetOf()` translation logic
- Add `subsetOf()` translation logic
- Handle collection-to-set conversion for comparison

### Step 3: Fix Lambda Variable Scope
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Ensure lambda variables are properly scoped:
- Track lambda variable bindings in translation context
- Handle variable shadowing correctly
- Pass context properly to lambda expressions

### Step 4: Implement `repeat()` with Type Conversion
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Fix `repeat()` function translation:
- Handle non-JSON values with proper type conversion
- Handle null values correctly
- Generate appropriate SQL for repetition

### Step 5: Add `single()` Validation
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Implement `single()` function translation:
- Add collection size validation
- Generate SQL for singleton extraction
- Handle error cases appropriately

### Step 6: Implement Quantifiers
**Location:** `fhir4ds/main/fhirpath/sql/translator.py`

Implement quantifier function translation:
- Add `allTrue()` translation logic
- Add `anyTrue()` translation logic
- Handle boolean conversion across collections

## Testing Strategy

1. **Unit Tests:** Test each function independently
2. **Integration Tests:** Test CTE column preservation
3. **Compliance Tests:** Run full collection_functions suite
4. **Edge Cases:** Empty collections, null values, large collections

## Success Criteria

- [ ] All 72 collection_functions tests passing
- [ ] CTE column preservation working
- [ ] Set comparison functions implemented
- [ ] Lambda variable scope fixed
- [ ] `repeat()` handles all types
- [ ] `single()` validates correctly
- [ ] Quantifiers working
- [ ] No regressions
- [ ] Code reviewed and approved

## Dependencies

- None (but benefits from completion of other tasks)

## Related Files

**Primary:** `fhir4ds/main/fhirpath/sql/translator.py` - Collection function translation (FIX LOCATION)
**Supporting:**
- `fhir4ds/main/fhirpath/sql/cte.py` - CTE management
- `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - AST metadata
- `tests/compliance/fhirpath/` - Compliance tests

**DO NOT MODIFY:**
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar

## Notes

- This is a VERY_HIGH complexity task
- CTE architecture changes are foundational
- Consider adding comprehensive logging for debugging
- May require refactoring of existing CTE logic
- Test thoroughly with different database dialects

## Expected Compliance Impact

**Before:** 72.6% (678/934)
**After:** 80.3% (750/934)
**Improvement:** +7.7%
