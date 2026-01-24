---
name: review-task
description: Review completed work, manage merges, and handle sprint validation
triggers:
  - review task
  - review and merge
  - validate task
  - review sprint
argument-hint: "[TASK-ID or sprint]"
---

# Review Task Skill

**Primary Agent**: `oh-my-claudecode:code-reviewer`
**Supporting Agents**: `oh-my-claudecode:architect`, `oh-my-claudecode:qa-tester`, `oh-my-claudecode:security-reviewer`

## Purpose

Review completed work and manage merges for individual tasks or entire sprints.

## When to Activate

When user says:
- "review task SP-001-003"
- "review and merge SP-001-003"
- "review sprint SP-025"
- "validate sprint"

## Workflow

### For Individual Task Review

**Pre-Review Setup:**
1. Review process documents in `project-docs/plans/process/`
2. Review PEP orientation documents in `project-docs/plans/orientation/`
3. Check task requirements in `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`

**Navigate to Worktree:**
```bash
cd ../sprint-SP-XXX
```

**Code Review Process:**
1. **Architecture Compliance:**
   - Verify unified FHIRPath architecture adherence
   - Confirm thin dialect implementation
   - Validate population-first design patterns
   - Check CTE-first SQL generation approach

2. **Code Quality Assessment:**
   - Review adherence to coding standards
   - Verify test coverage (90%+ target)
   - Check documentation completeness
   - Assess error handling and logging

3. **Specification Compliance:**
   - Validate impact on FHIRPath, SQL-on-FHIR, CQL
   - Ensure compatibility with DuckDB and PostgreSQL
   - Check performance implications

**Testing Validation:**
1. Run comprehensive test suite
2. Execute specification compliance tests
3. Validate multi-database functionality
4. Check for regressions

**Review Documentation:**
- Create review summary: `project-docs/plans/reviews/SP-XXX-YYY-review.md`

**If APPROVED:**
- Notify that task is approved for commit
- Changes will be committed to sprint branch
- Keep worktree active until sprint completion

**If CHANGES NEEDED:**
- Provide specific feedback in review document
- Update task status to "needs revision"
- Guide with clear next steps

### For Sprint Completion Review

**Sprint Validation Process:**

1. **Review Sprint Documentation:**
   - Read sprint summary from `project-docs/plans/current-sprint/`
   - Review all completed tasks and commit messages
   - Check milestone progress and compliance metrics

2. **Navigate to Sprint Worktree:**
   ```bash
   cd ../sprint-SP-XXX
   ```

3. **Run Validation Tests:**
   ```bash
   git pull origin sprint/SP-XXX
   python -m pytest tests/
   python tests/run_compliance.py
   python tests/run_tests.py --dialect duckdb
   python tests/run_tests.py --dialect postgresql
   ```

4. **Merge Sprint to Main:**
   ```bash
   cd ../[main-directory]
   git checkout main
   git pull origin main
   git merge sprint/SP-XXX --no-ff
   git push origin main
   ```

### Post-Merge Worktree Cleanup

```bash
cd ../[main-directory]
git worktree remove ../sprint-SP-XXX
git worktree list | grep task-SP-XXX | awk '{print $1}' | xargs -I {} git worktree remove {}
git worktree prune
```

## Quality Gates

**For Tasks:**
- Zero business logic in database dialects
- All tests pass on both databases
- No hardcoded values
- 90%+ test coverage
- Documentation complete

**For Sprints:**
- All sprint tasks completed
- Full test suite passes (100%)
- Both DuckDB and PostgreSQL tested
- No regressions
- Architectural compliance verified

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Comprehensive code review | `oh-my-claudecode:code-reviewer` | opus |
| Quick code checks | `oh-my-claudecode:code-reviewer-low` | haiku |
| Architecture verification | `oh-my-claudecode:architect` | opus |
| Test validation | `oh-my-claudecode:qa-tester` | sonnet |
| Comprehensive QA | `oh-my-claudecode:qa-tester-high` | opus |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Git operations | `oh-my-claudecode:git-master` skill | - |
