# Task SP-107-001: path_navigation Final Fix

**Created:** 2026-01-27
**Sprint:** SP-107
**Priority:** P0
**Status:** Pending
**Estimated Effort:** 1-2 hours

---

## Objective

Fix the last failing test in path_navigation category to achieve 100% compliance (9/10 → 10/10).

## Current State

**Category:** path_navigation
**Status:** 90.0% (9/10 passing)
**Gap:** 1 failing test

## Acceptance Criteria

- [ ] All 10 path_navigation tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Compliance report shows 100% for path_navigation

## Implementation Plan

### Step 1: Identify Failing Test
Run compliance tests and identify which specific path_navigation test is failing.

```bash
python3 tests/compliance/fhirpath/test_runner.py > /tmp/path_nav_failures.json 2>&1
# Filter for path_navigation failures
```

### Step 2: Root Cause Analysis
- Extract failing test expression and expected result
- Trace through parser → SQL translation → execution
- Identify specific failure point

### Step 3: Implement Fix
- Make minimal, targeted fix to address root cause
- Ensure fix aligns with FHIRPath specification
- Verify CTE-first design principles

### Step 4: Validate
- Run full compliance suite
- Verify 10/10 path_navigation tests passing
- Check for regressions

## Expected Impact

**Compliance Improvement:** +0.1 percentage points (1 test)
**Category Completion:** path_navigation 90% → 100%

## Notes

This is a quick win - the category is nearly complete, so the last failure should have a clear, fixable root cause.
