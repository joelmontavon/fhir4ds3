# Task: SP-101-003 - Result Logic Mismatches (Top 3 Patterns)

**Created**: 2026-01-25
**Status**: Pending
**Priority**: P2-A (Medium, High Impact)
**Estimated Effort**: 24-34 hours (includes 4h categorization)

---

## Task Description

Categorize and fix the top 3 patterns in the ~184 "result logic mismatch" test failures. This batch contains uncategorized failures that need analysis before implementation.

## Current State

**Total Tests**: ~184 failing tests categorized as "result logic mismatches"
**Issue**: Tests produce wrong values or types (not crashes/errors)
**Status**: Uncategorized - root causes unknown

---

## Known Limitations

### ANTLR Grammar Regeneration Blocked

**Issue**: Grammar changes require ANTLR tool regeneration, which is blocked by lack of Java in the current environment.

**Impact**:
- Cannot modify FHIRPath grammar files (.g4) without Java runtime
- Grammar changes would require regenerating parser/lexer files
- Workaround: Use AST transformations and enhanced parsing where possible

**Files Affected**:
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` (grammar file)

**Resolution Path**:
1. Install Java runtime environment
2. Run ANTLR tool to regenerate parser/lexer from grammar
3. Or: Find workarounds using AST post-processing

**Documented**: 2026-01-25 (SP-101 code review)

## Requirements

### Phase 1: Categorization (4 hours)

1. **Run test suite with detailed error logging**:
   ```bash
   python -m tests.integration.fhirpath.official_test_runner > test_output.log 2>&1
   ```

2. **Analyze failures by error type**:
   - Type mismatches (expected X, got Y)
   - Value mismatches (expected value, got different value)
   - Missing results (empty instead of values)
   - Extra results (values instead of empty)
   - Null handling differences

3. **Group by root cause**:
   - Function implementation bugs
   - SQL generation issues
   - Type coercion problems
   - Edge cases not handled

4. **Identify top 3 patterns** by test count

### Phase 2: Implementation (20-30 hours)

For each of the top 3 patterns:
1. Document the root cause
2. Implement fix in translator
3. Test the fix
4. Document edge cases

## Acceptance Criteria

### Categorization Phase

1. ✅ All 184 tests categorized by error type
2. ✅ Top 3 patterns identified with test counts
3. ✅ Each pattern documented with:
   - Root cause description
   - Example failing tests
   - Recommended fix approach
   - Estimated effort

### Implementation Phase

1. ✅ Fixes implemented for top 3 patterns
2. ✅ At least 60 tests from this batch now passing
3. ✅ No regression on existing tests
4. ✅ Remaining patterns documented with estimates

### Documentation

1. ✅ Categorization report in `project-docs/plans/tasks/SP-101-003-categorization.md`
2. ✅ Implementation summary for each pattern
3. ✅ Remaining patterns deferred to future sprint

## Location

**Files**: Multiple translator methods (to be determined during categorization)

## Dependencies

None - can be implemented independently

## Risk Mitigation

### Scope Creep Prevention

**Risk**: The 184 test batch could expand beyond 24-34 hours

**Mitigation**:
- **Explicit boundary**: Implement top 3 patterns only
- **Time checkpoint**: After 30 hours, stop and document remaining
- **Priority queue**: If first pattern takes too long, move to next

### Risk: Categorization reveals >10 distinct patterns

**Mitigation**:
- **Aggressive grouping**: Combine similar errors into patterns
- **Focus on high-count**: Prioritize patterns affecting 20+ tests
- **Batch by complexity**: Handle simple patterns first

## Testing Strategy

### Categorization Phase

```bash
# Run with detailed logging
python -m tests.integration.fhirpath.official_test_runner > full_output.log 2>&1

# Extract failure patterns
grep "SQL translation failed" full_output.log | sort | uniq -c | sort -rn > failure_patterns.txt
```

### Implementation Phase

For each pattern fix:
- Run subset of affected tests
- Verify fix works for all tests in pattern
- Run regression suite
- Both dialects validated

## Deliverables

1. Categorization report with top 3 patterns
2. Implementation summary for each pattern
3. Updated compliance report
4. Deferred patterns documented

---

**Task Owner**: TBD
**Reviewers**: Architect, Code Reviewer
**Blocked By**: None
**Blocking**: Remaining patterns (deferred to future sprint)
