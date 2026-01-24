# Sprint 012 Week 2 - Task Summary for Junior Developer

**Created**: 2025-10-24
**Sprint**: Sprint 012 - PostgreSQL Execution and FHIRPath Compliance Growth
**Timeframe**: Week 2 (Days 8-14)

---

## Overview

Congratulations on completing Week 1! You successfully:
- ✅ Enabled PostgreSQL live execution (SP-012-001)
- ✅ Fixed type registry issues (SP-012-004 and sub-tasks)
- ✅ Reduced test failures by 79% (28 → 6 failures)

Week 2 focuses on **cleaning up remaining issues** and **validating our progress** before sprint completion.

---

## Week 2 Tasks (3 Tasks)

### Task 1: SP-012-005 - Resolve Final 6 Unit Test Failures ⭐ START HERE

**Priority**: High
**Estimated Time**: 6.5 hours (≈1 day)
**File**: `project-docs/plans/tasks/SP-012-005-resolve-final-unit-test-failures.md`

**What You'll Do**:
Fix the last 6 unit test failures to achieve a completely clean test suite.

**Current Status**: 1,936 passing, 6 failing (98.2% pass rate)
**Target**: 1,942 passing, 0 failing (100% pass rate)

**The 6 Failures**:
1. **Cosmetic** (1 test): Function call text field empty in AST adapter
2. **SQL Formatting** (1 test): Extra AS clause in CTE builder
3. **Type Operations** (2 tests): May already be fixed by SP-012-004-A
4. **Variable Handling** (2 tests): `$this` and `$total` context variables

**Proven Methodology** (from SP-012-004-C):
1. Fix ONE test at a time
2. Understand root cause before coding
3. Make minimal changes
4. Test immediately after each fix
5. Document what you did and why

**Why This Matters**:
- Clean test suite enables accurate compliance measurement
- Demonstrates thoroughness and attention to detail
- Sets strong foundation for PostgreSQL CTE work

**Start Here**: Read the full task file, then begin with Step 1 (categorization).

---

### Task 2: SP-012-006 - PostgreSQL CTE Execution Fixes

**Priority**: Critical
**Estimated Time**: 10 hours (≈1.25 days)
**File**: `project-docs/plans/tasks/SP-012-006-postgresql-cte-execution-fixes.md`

**What You'll Do**:
Fix 29 PostgreSQL CTE test errors by implementing PostgreSQL-specific LATERAL UNNEST syntax in the dialect.

**Current Status**: 29 errors in `test_cte_data_structures.py`
**Target**: 0 errors, 100% multi-database parity

**Key Technical Work**:
1. Understand PostgreSQL LATERAL UNNEST syntax (differs from DuckDB)
2. Add dialect methods to base and PostgreSQL dialects
3. Update CTE assembler to use dialect methods
4. Validate identical results in DuckDB and PostgreSQL

**CRITICAL Architecture Principle**:
- **Dialects contain ONLY syntax differences**
- **NO business logic in dialect classes**
- **Method overriding approach** - not regex or conditionals

**Example**:
```python
# PostgreSQL Dialect (CORRECT - syntax only)
def generate_lateral_unnest(self, json_expr: str, alias: str) -> str:
    return f"CROSS JOIN LATERAL jsonb_array_elements({json_expr}) AS {alias}"

# Anti-pattern (INCORRECT - business logic)
def generate_lateral_unnest(self, json_expr: str, alias: str) -> str:
    if self.should_use_unnest:  # ❌ Business decision in dialect!
        return "..."
```

**Why This Matters**:
- Completes multi-database story started in SP-012-001
- Validates Sprint 011 CTE infrastructure works in PostgreSQL
- Critical for architectural integrity (thin dialects)

**Dependencies**: Recommended to complete SP-012-005 first (clean test suite), but can proceed independently.

---

### Task 3: SP-012-007 - Final Sprint 012 Compliance Validation

**Priority**: Critical (Sprint Completion)
**Estimated Time**: 12.5 hours (≈1.5-2 days)
**File**: `project-docs/plans/tasks/SP-012-007-final-sprint-compliance-validation.md`

**What You'll Do**:
Execute official FHIRPath test suites, measure actual compliance, create sprint completion report.

**NO CODE CHANGES** - This is testing and documentation only.

**Key Activities**:
1. Run official FHIRPath R4 test suite in DuckDB
2. Run official FHIRPath R4 test suite in PostgreSQL
3. Compare results (should be 100% identical)
4. Analyze results against Sprint 012 goals
5. Create sprint completion report with evidence
6. Document lessons learned

**Sprint 012 Success Criteria** (to validate):
- Overall compliance: 72% → 82%+ (target)
- Type Functions: 41% → 70%+ (target)
- PostgreSQL execution: 0% → 100% ✅
- Multi-database parity: 100% ✅
- Zero regressions ✅

**Evidence-Based Reporting**:
- Report ACTUAL results, not aspirations
- Provide test logs and data to support claims
- Explain shortfalls honestly (learning opportunities)
- Give actionable recommendations for Sprint 013

**Why This Matters**:
- Required for sprint completion
- Provides data for Sprint 013 planning
- Demonstrates professional reporting skills
- Shows what was really accomplished (vs. hoped for)

**Dependencies**: Should complete SP-012-005 and SP-012-006 first for clean validation.

---

## Week 2 Progress Updates

- **2025-10-26**: Completed implementation of SP-012-007 arithmetic edge-case fixes with new DuckDB/PostgreSQL regression tests; awaiting senior review and compliance validation sign-off.

---

## Week 2 Timeline (Recommended)

### Days 8-9: SP-012-005 (Unit Test Cleanup)
**Time**: 6.5 hours

- Day 8 AM: Categorize failures, fix cosmetic/formatting issues (3 hours)
- Day 8 PM: Fix variable handling issues (2 hours)
- Day 9 AM: Final validation, documentation (1.5 hours)

**Outcome**: Clean unit test suite (1,942 passing, 0 failing)

---

### Days 10-12: SP-012-006 (PostgreSQL CTE Fixes)
**Time**: 10 hours

- Day 10 AM: Analyze errors, research PostgreSQL syntax (2 hours)
- Day 10 PM: Design dialect interface (2 hours)
- Day 11 AM: Implement dialect methods (3 hours)
- Day 11 PM: Fix CTE assembly (2 hours)
- Day 12 AM: Validate and document (1 hour)

**Outcome**: PostgreSQL CTE tests passing, multi-database parity validated

---

### Days 13-14: SP-012-007 (Compliance Validation)
**Time**: 12.5 hours

- Day 13 AM: Run DuckDB tests (2 hours)
- Day 13 PM: Run PostgreSQL tests, benchmarks (3 hours)
- Day 14 AM: Analyze results, root cause gaps (3.5 hours)
- Day 14 PM: Create reports, lessons learned (4 hours)

**Outcome**: Sprint 012 completion report ready for review

---

## Success Criteria for Week 2

By end of Week 2, you should have:

### Technical Deliverables
- [ ] All 1,942 unit tests passing (zero failures)
- [ ] All 29 PostgreSQL CTE errors resolved
- [ ] Multi-database parity: 100% (DuckDB = PostgreSQL)
- [ ] Performance within targets (<10ms CTE, <20% database variance)

### Documentation Deliverables
- [ ] SP-012-005 implementation summary
- [ ] SP-012-006 implementation summary
- [ ] Sprint 012 completion report
- [ ] Detailed compliance results
- [ ] Lessons learned document

### Sprint 012 Outcome
- [ ] Sprint goals validated (success, partial, or continuation needed)
- [ ] Compliance measured with evidence
- [ ] Sprint 013 recommendations provided

---

## Key Principles for Week 2

### 1. Quality Over Speed
- Take time to understand root causes
- Don't rush through fixes
- Test thoroughly after each change
- Document as you go

### 2. Evidence-Based Work
- Capture actual test output
- Don't guess at compliance - measure it
- Support all claims with data
- Be honest about shortfalls

### 3. Architecture First
- **NO business logic in dialects** (critical for SP-012-006)
- Maintain thin dialect principle
- Follow established patterns
- Ask if unsure about architecture

### 4. Communication
- Document progress in task files
- Update this/total variables task status
- Flag blockers immediately
- Ask questions when stuck (after 2 hours)

---

## Getting Help

### When to Ask for Help
- Stuck on a fix for >2 hours
- Unsure if approach violates architecture
- Test results surprising or confusing
- Unclear about what counts as "business logic"

### How to Ask
1. Describe what you tried
2. Show actual error messages/output
3. Explain your hypothesis about the issue
4. Ask specific question

### Example Good Question
> "I'm working on SP-012-006 Step 4. I've implemented the PostgreSQL dialect method for LATERAL UNNEST, but I'm unsure if this helper function `_convert_json_path()` counts as business logic or syntax transformation. It takes `$.field.subfield` and converts it to `->'field'->'subfield'`. Here's the code: [paste code]. Is this appropriate for a dialect, or should this live in the CTE assembler?"

---

## Resources

### Task Files (Read These Thoroughly!)
- `project-docs/plans/tasks/SP-012-005-resolve-final-unit-test-failures.md`
- `project-docs/plans/tasks/SP-012-006-postgresql-cte-execution-fixes.md`
- `project-docs/plans/tasks/SP-012-007-final-sprint-compliance-validation.md`

### Reference Materials
- `CLAUDE.md`: Core development principles (re-read thin dialects section!)
- `project-docs/process/coding-standards.md`: Coding standards
- `project-docs/plans/current-sprint/sprint-012-postgresql-and-compliance.md`: Sprint plan

### Similar Completed Work (Learn from These!)
- `project-docs/plans/tasks/SP-012-004-C-remaining-translator-issues.md`: Proven methodology
- `project-docs/plans/reviews/SP-012-004-C-review.md`: What good work looks like

### PostgreSQL Resources (for SP-012-006)
- PostgreSQL LATERAL documentation
- PostgreSQL JSON functions documentation
- PostgreSQL JSONB operators reference

---

## Checklist for Starting Week 2

Before you begin:
- [ ] Read this summary document completely
- [ ] Read SP-012-005 task file thoroughly
- [ ] Review SP-012-004-C approach (proven methodology)
- [ ] Ensure clean git state (on main branch, all recent merges)
- [ ] Run baseline tests to confirm current status
- [ ] Create feature branch for SP-012-005

---

## Final Notes

**Week 2 Focus**: Clean up, validate, document

**Week 1 Achievements**: You accomplished a lot! PostgreSQL is live, tests are mostly clean, architecture is solid.

**Week 2 Goals**: Finish strong with zero known issues, validated compliance data, and clear Sprint 013 roadmap.

**Attitude**: This is the "polish and validate" phase. Take pride in thoroughness and attention to detail.

---

## Questions to Consider

As you work through Week 2 tasks:

1. **SP-012-005**: What patterns from SP-012-004-C can I apply? Which fixes are related?
2. **SP-012-006**: Is this method pure syntax transformation, or does it make business decisions?
3. **SP-012-007**: What do the actual test results tell us? Where did we succeed? Where did we fall short?

---

**Good luck with Week 2! You've got this. 🚀**

**Remember**: Quality, evidence, architecture, communication.

---

**Document Created**: 2025-10-24
**Last Updated**: 2025-10-24
**Status**: Week 2 Ready to Begin

**Next Action**: Read SP-012-005 task file and begin Step 1 (categorization).
