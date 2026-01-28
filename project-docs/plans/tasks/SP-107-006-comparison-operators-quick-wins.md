# Task SP-107-006: comparison_operators - Quick Wins

**Created:** 2026-01-27
**Sprint:** SP-107
**Priority:** P1
**Status:** Pending
**Estimated Effort:** 6-8 hours

---

## Objective

Fix the easiest 30 failing tests in comparison_operators category to improve compliance from 69.2% to ~78%.

## Current State

**Category:** comparison_operators
**Status:** 69.2% (234/338 passing)
**Gap:** 104 failing tests
**Target:** Fix 30/104 failures → 264/338 (78.1%)

## Acceptance Criteria

- [ ] At least 264 comparison_operators tests passing (78%+)
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Compliance report shows significant improvement

## Implementation Plan

### Step 1: Analyze All 104 Failures
Run compliance tests and categorize all comparison operator failures.

```bash
python3 tests/compliance/fhirpath/test_runner.py > /tmp/comparison_failures.json 2>&1
# Group by operator type and root cause
```

### Step 2: Prioritize by Impact
Categorize failures by operator and complexity:
- **High Impact, Low Effort:** Fix first
- **High Impact, Medium Effort:** Include if time allows
- **Low Impact, Any Effort:** Defer
- **High Effort, Any Impact:** Defer

Operators: =, !=, <, <=, >, >=, ~, !~, contains, in, not in, etc.

### Step 3: Group by Root Cause
Identify common failure patterns:
- Type coercion issues (string vs number vs date)
- Collection comparison semantics
- Empty/null handling
- Case sensitivity in string comparisons
- Numeric precision issues

### Step 4: Implement Fixes by Pattern
For each root cause pattern:
1. Implement minimal fix
2. Ensure comparison operators follow FHIRPath spec
3. Verify collection comparison semantics
4. Test with different data types
5. Check SQL dialect differences

### Step 5: Validate
- Run full compliance suite
- Verify at least 264/338 comparison_operators tests passing
- Check for regressions

## Expected Impact

**Compliance Improvement:** +3.2 percentage points (30 tests)
**Category Improvement:** comparison_operators 69% → 78%

## Common Comparison Issues

- Type mismatch handling
- Collection vs singleton comparison
- Empty collection semantics
- Null/empty value handling
- Case sensitivity
- Numeric precision
- DateTime comparison timezone handling
- String comparison collation issues

## Notes

Comparison operators are the largest category (338 tests). This task focuses on the easiest 30 failures to maximize compliance gain. Remaining failures will be addressed in future sprints.

Key considerations:
1. Focus on fixes with clear, isolated root causes
2. Prioritize fixes that unblock other tests
3. Ensure SQL dialect parity (DuckDB and PostgreSQL)
4. Document any spec interpretation decisions
