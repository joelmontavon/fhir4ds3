# Task: Fix Arithmetic Operator Bugs

**Task ID**: SP-021-007
**Status**: TODO
**Priority**: CRITICAL
**Estimated Impact**: +53 tests
**Estimated Effort**: 20-30 hours

## Description

Fix parser bugs causing failures when handling negative numbers with unit suffixes (e.g., `-5.5'mg'`).

**Root Cause**: Parser treats minus as unary operator but fails to handle unit suffix, causing "list index out of range" errors.

**Source**: SP-021-003 investigation - see `work/SP-021-003-INVESTIGATION-REPORT.md` for full details.

## Impact

- Arithmetic_Operators category: 19/72 → 60/72+ (26.4% → 83%+)
- Overall compliance: 404 → 457 tests (43.3% → 48.9%)

## See Also

- Full investigation: `work/SP-021-003-INVESTIGATION-REPORT.md`
- Roadmap: `project-docs/plans/roadmaps/SP-021-compliance-improvement.md`
- Part of Phase 1 quick wins

