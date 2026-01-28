# Task SP-107-005: string_functions - Quick Wins

**Created:** 2026-01-27
**Sprint:** SP-107
**Priority:** P1
**Status:** Pending
**Estimated Effort:** 4-6 hours

---

## Objective

Fix the easiest 10 failing tests in string_functions category to improve compliance from 69.2% to ~84%.

## Current State

**Category:** string_functions
**Status:** 69.2% (45/65 passing)
**Gap:** 20 failing tests
**Target:** Fix 10/20 failures → 55/65 (84.6%)

## Acceptance Criteria

- [ ] At least 55 string_functions tests passing (84%+)
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Compliance report shows significant improvement

## Implementation Plan

### Step 1: Analyze All 20 Failures
Run compliance tests and categorize all string function failures.

```bash
python3 tests/compliance/fhirpath/test_runner.py > /tmp/string_failures.json 2>&1
# Group by function type and complexity
```

### Step 2: Prioritize by Ease
Categorize failures by root cause complexity:
- **Easy:** Simple fixes (1-2 hours) - prioritize these
- **Medium:** Moderate fixes (2-3 hours) - include if time allows
- **Hard:** Complex fixes (4+ hours) - defer to future sprint

Target functions: substring, indexOf, length, lower/upper, replace, matches, etc.

### Step 3: Implement Fixes
For each prioritized failure:
1. Identify root cause
2. Implement minimal fix
3. Ensure string operations follow FHIRPath spec
4. Verify unicode handling if relevant
5. Test edge cases (empty strings, null, whitespace)

### Step 4: Validate
- Run full compliance suite
- Verify at least 55/65 string_functions tests passing
- Check for regressions

## Expected Impact

**Compliance Improvement:** +1.1 percentage points (10 tests)
**Category Improvement:** string_functions 69% → 84%

## Common String Function Issues

- Index out of bounds handling
- Empty string edge cases
- Null input handling
- Case sensitivity
- Whitespace handling
- Unicode character support
- Regex pattern matching issues

## Notes

String functions are well-defined in the spec. Focus on:
1. Functions with partial implementation
2. Edge case handling issues
3. Type conversion problems
4. SQL dialect differences in string operations

Target the 10 easiest fixes to maximize compliance gain per hour of effort.
