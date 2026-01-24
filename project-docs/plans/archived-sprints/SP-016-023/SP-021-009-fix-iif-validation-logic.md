# Task: Fix iif() Function Validation Logic

**Task ID**: SP-021-009
**Status**: TODO
**Priority**: MEDIUM
**Estimated Impact**: +8 tests
**Estimated Effort**: 8-12 hours

## Description

Fix iif() function to validate criterion as boolean at evaluation time rather than AST parsing time.

**Root Cause**: Validation happens at AST level instead of value level, incorrectly rejecting valid expressions like `(5 + 5).iif(true, 'a', 'b')`.

**Source**: SP-021-003 investigation - see `work/SP-021-003-INVESTIGATION-REPORT.md` for full details.

## Impact

- Function_Calls category: 47/113 → 52/113+ (41.6% → 46%+)
- Overall compliance: 480 → 488 tests (51.4% → 52.2%)

## See Also

- Full investigation: `work/SP-021-003-INVESTIGATION-REPORT.md`
- Roadmap: `project-docs/plans/roadmaps/SP-021-compliance-improvement.md`
- Part of Phase 1 quick wins

