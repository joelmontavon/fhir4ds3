# Task SP-109-006: Quick Wins - Edge Cases

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 20 tests (various → 100%, +2.1% overall)
**Effort:** 6-8 hours
**Priority:** P2
**Status:** Pending

---

## Objective

Fix remaining edge cases in high-pass-rate categories to achieve 100% compliance in these categories, providing a final polish to the implementation.

---

## Current State

### Quick Win Categories

| Category | Pass Rate | Failed | Impact |
|----------|-----------|--------|--------|
| math_functions | 96.4% | 1 | +0.1% |
| path_navigation | 90.0% | 1 | +0.1% |
| datetime_functions | 83.3% | 1 | +0.1% |
| string_functions | 75.4% | 16 | +1.7% |

---

## Implementation Plan

### Step 1: Fix Math Function Edge Case (1 hour)

**Problem:** 1 test failing in math_functions

**Solution:**
1. Identify the failing test
2. Investigate root cause
3. Implement fix
4. Test all math functions

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/sql/test_translator_math_functions.py`

### Step 2: Fix Path Navigation Edge Case (1 hour)

**Problem:** 1 test failing in path_navigation

**Solution:**
1. Identify the failing test
2. Investigate root cause
3. Implement fix
4. Test all path navigation

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/integration/fhirpath/test_path_navigation.py`

### Step 3: Fix Datetime Function Edge Case (1 hour)

**Problem:** 1 test failing in datetime_functions

**Solution:**
1. Identify the failing test
2. Investigate root cause
3. Implement fix
4. Test all datetime functions

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/sql/test_translator_datetime_functions.py`

### Step 4: Fix String Function Issues (3-5 hours)

**Problem:** 16 tests failing in string_functions (75.4% passing)

**Solution:**
1. Audit all failing string function tests
2. Group failures by root cause
3. Fix each root cause systematically
4. Test all string functions

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `tests/unit/fhirpath/sql/test_translator_string_integration.py`

**Potential Issues:**
- Regex edge cases
- String encoding issues
- Empty string handling
- Null handling in string operations

---

## Testing Strategy

### Unit Tests
1. Test math function edge case
2. Test path navigation edge case
3. Test datetime function edge case
4. Test all string function fixes

### Integration Tests
1. Test functions in expressions
2. Test functions with CTEs
3. Test functions across databases
4. Test edge cases thoroughly

### Compliance Tests
1. Run full compliance suite
2. Verify all quick win categories at 100%
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All math_functions tests passing (100%)
- [ ] All path_navigation tests passing (100%)
- [ ] All datetime_functions tests passing (100%)
- [ ] All string_functions tests passing (100%)
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 97.7%+

---

## Risk Assessment

**Risk Level:** Low

**Risks:**
- Edge cases may be obscure
- String functions may have hidden complexity
- Fixes may uncover other issues

**Mitigation:**
- Investigate each failure thoroughly
- Test comprehensively after each fix
- Document all edge cases found
- Keep changes minimal and targeted

---

## Dependencies

- All other tasks (do this last)

---

## Notes

- This is the final polish task
- Should be done after all other tasks
- Focus on getting to 100% in these categories
- Each fix may be simple or complex
- Take time to understand root causes
- Document edge cases for future reference
- Celebrate reaching 97.7% compliance!
