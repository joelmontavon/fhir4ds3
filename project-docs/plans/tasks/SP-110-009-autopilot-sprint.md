# Task SP-110-009: Autopilot Sprint - 100% Compliance

**Created:** 2026-02-03
**Sprint:** SP-110
**Task:** Autopilot-driven execution to 100% compliance
**Starting Compliance:** 65.3% (610/934)
**Target:** 100% (934/934)
**Gap:** 324 tests

---

## Analysis Summary

### Current State (2026-02-03)

| Category | Pass Rate | Failures | Blocker Type |
|----------|-----------|----------|--------------|
| comparison_operators | 72.8% | 92 | Implementation |
| collection_functions | 47.5% | 74 | Implementation + Missing |
| function_calls | 56.6% | 49 | Missing Functions |
| type_functions | 59.5% | 47 | Validation + Missing |
| arithmetic_operators | 45.1% | 39 | Edge Cases |
| string_functions | 78.7% | 19 | Edge Cases |
| datetime_functions | 83.3% | 1 | Edge Case |
| boolean_logic | 66.7% | 2 | Edge Case |
| path_navigation | 90.0% | 1 | Edge Case |
| math_functions | 100.0% | 0 | DONE |
| comments_syntax | 100.0% | 0 | DONE |

### Missing Functions (High Priority)

**Hierarchy (2 functions, ~10 tests):**
- `children()` - Get direct children
- `descendants()` - Get all descendants

**Utility (9 functions, ~25 tests):**
- `trim()` - Remove whitespace
- `sort()` - Sort collection
- `trace()` - Debug output
- `encode()` - Base64/hex encoding
- `decode()` - Base64/hex decoding
- `escape()` - HTML/JSON escaping
- `unescape()` - HTML/JSON unescaping
- `matchesFull()` - Full string regex match

**iif() Function (~5 tests):**
- Type coercion for CASE expressions

### Implementation Gaps

**CTE Column Preservation (~20 tests):**
- Column alias propagation in nested CTEs
- Missing columns in `select()`, `subsetOf()`, `supersetOf()`

**DateTime/Quantity (~15 tests):**
- Timezone handling in comparisons
- DATE/TIME type compatibility
- Quantity unit conversion

---

## Execution Plan

### Round 1: Quick Wins (Parallel - 5 workers)

**Worker 1: Utility Functions** (4-6 hours)
- `trim()` - Remove leading/trailing whitespace
- `sort()` - Sort collection (numeric/string)
- `matchesFull()` - Full string regex match
- **Impact:** ~10 tests

**Worker 2: String Encoding** (4-6 hours)
- `encode()` - Base64, hex, urlbase64
- `decode()` - Base64, hex, urlbase64
- `escape()` - HTML, JSON
- `unescape()` - HTML, JSON
- **Impact:** ~10 tests

**Worker 3: iif() Type Coercion** (2-4 hours)
- Fix CASE expression type mixing
- Add explicit casting for branches
- **Impact:** ~5 tests

**Worker 4: CTE Column Preservation** (4-8 hours)
- Fix column propagation in collection functions
- Ensure all columns preserved through CTE chain
- **Impact:** ~20 tests

**Worker 5: trace() Function** (1-2 hours)
- Implement debug output function
- No-op in SQL (return value unchanged)
- **Impact:** ~5 tests

**Expected Duration:** 6-8 hours (parallel)
**Expected Improvement:** +50 tests → 70.4% compliance

### Round 2: Hierarchy Functions (Sequential - 1 worker)

**Worker 1: Hierarchy Functions** (8-12 hours)
- `children()` - Get direct child elements
- `descendants()` - Get all descendant elements
- Requires understanding FHIR resource structure
- **Impact:** ~10 tests

**Expected Duration:** 8-12 hours
**Expected Improvement:** +10 tests → 71.5% compliance

### Round 3: DateTime/Quantity Edge Cases (Sequential - 1 worker)

**Worker 1: DateTime & Quantity** (8-12 hours)
- Timezone normalization in comparisons
- DATE/TIME type compatibility
- Quantity unit conversion edge cases
- **Impact:** ~15 tests

**Expected Duration:** 8-12 hours
**Expected Improvement:** +15 tests → 73.1% compliance

### Round 4: Remaining Edge Cases (Parallel - 3 workers)

**Worker 1: Collection Functions** (4-6 hours)
- `single()` - Validate single element
- `allTrue()`, `anyTrue()` - Boolean quantifiers
- `repeat()` with type conversion
- **Impact:** ~8 tests

**Worker 2: Type Functions** (4-6 hours)
- `convertsToInteger()`, `convertsToDecimal()` edge cases
- `as()` type conversion edge cases
- `ofType()` collection filtering
- **Impact:** ~10 tests

**Worker 3: Arithmetic & Comparison** (4-6 hours)
- Unary operator precedence edge cases
- Negative number comparisons
- Mixed-type arithmetic
- **Impact:** ~10 tests

**Expected Duration:** 6-8 hours (parallel)
**Expected Improvement:** +28 tests → 76.1% compliance

---

## Implementation Guidelines

### Architecture Rules

1. **NO GRAMMAR CHANGES** - All fixes in translator.py
2. **CTE-First Design** - Use CTEs for all operations
3. **Type Coercion** - Handle at translation layer
4. **Column Preservation** - Ensure all columns propagate

### Function Template

```python
def _generate_<function_name>(self, *args) -> CTEFragment:
    """
    Generate SQL for <function_name>()

    FHIRPath: <function signature>
    SQL: <implementation approach>
    """
    # 1. Validate arguments
    # 2. Build CTE fragment with proper column names
    # 3. Handle type coercion if needed
    # 4. Return fragment with preserved columns
```

### Testing Protocol

After each fix:
1. Run compliance tests: `python run_compliance_tests.py`
2. Verify category improvement
3. Check for regressions
4. Update compliance report

---

## Success Metrics

### Target: 100% Compliance

| Phase | Baseline | Target | Tests Fixed |
|-------|----------|--------|-------------|
| Round 1 | 65.3% | 70.4% | +50 |
| Round 2 | 70.4% | 71.5% | +10 |
| Round 3 | 71.5% | 73.1% | +15 |
| Round 4 | 73.1% | 76.1% | +28 |
| Final | 76.1% | 100% | +229 |

**Note:** Based on previous sprints, fixing core issues often resolves
multiple edge cases. The actual improvement is likely higher.

---

## Risk Assessment

### Low Risk
- Utility functions (trim, sort, matchesFull)
- String encoding functions
- trace() function

### Medium Risk
- iif() type coercion
- CTE column preservation

### High Risk
- Hierarchy functions (require FHIR structure knowledge)
- DateTime timezone handling
- Quantity unit conversion

### Mitigation
- Start with low-risk tasks in Round 1
- Test after each fix
- Keep changes minimal and targeted
- Use ultrapilot for parallel execution

---

## Dependencies

### Internal
- Current compliance baseline: 65.3%
- All previous SP-110 subtasks merged

### External
- None (self-contained task)

---

## Definition of Done

- [ ] All planned functions implemented
- [ ] Compliance at 100%
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] No regressions in passing categories
- [ ] Sprint documentation complete

---

## Notes

1. **Missing functions are easier to implement than edge cases**
2. **CTE column preservation is critical for collection functions**
3. **Type coercion is the main blocker for iif()**
4. **Hierarchy functions require understanding FHIR resource structure**
5. **DateTime timezone handling is complex but well-defined**
