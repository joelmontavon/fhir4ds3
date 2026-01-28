# SP-106-001: Fix Executor Column Selection Bug

**Priority:** CRITICAL
**Estimated Effort:** 1 hour
**Test Impact:** Unblocks all other tests (273+ tests)

## Problem Statement

The FHIRPath SQL executor has a critical column selection bug that causes it to select only the first column from CTEs instead of properly propagating all required columns through the execution chain. This prevents tests from passing even when the underlying logic is correct.

## Root Cause Analysis

The issue is in the column selection logic in the SQL executor/translator. When building CTEs, the executor fails to:
1. Track which columns are needed by downstream operations
2. Select all required columns when materializing intermediate results
3. Preserve columns that are referenced in subsequent expressions

## Architecture Alignment

This fix aligns with the unified FHIRPath architecture by ensuring:
- Proper CTE column propagation through the execution pipeline
- Correct SQL generation that references all needed columns
- No loss of intermediate results needed for subsequent operations

## Implementation Plan

1. **Locate column selection logic**
   - Find where CTE SELECT clauses are generated
   - Identify column tracking mechanism
   - Trace column propagation through execution chain

2. **Fix column selection**
   - Ensure all required columns are selected from CTEs
   - Preserve columns needed by parent expressions
   - Update column tracking to include dependencies

3. **Test validation**
   - Run existing test suite to verify fix
   - Ensure no regressions in column handling

## Testing Strategy

- Run full FHIRPath compliance test suite
- Verify that tests previously blocked by this issue now pass
- Check for any new failures introduced by the fix

## Success Criteria

- [ ] All FHIRPath tests can execute without column selection errors
- [ ] Intermediate results are properly accessible in subsequent operations
- [ ] No regression in existing passing tests

## Dependencies

- Blocks: All other SP-106 tasks (unblocks testing)
- Depends on: None (foundational fix)

## Notes

This is the highest priority task as it unblocks all other testing. Even though estimated at 1 hour, it has maximum leverage for the sprint.
