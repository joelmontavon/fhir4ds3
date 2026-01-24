# Review Task and Merge

**Primary Agent**: oh-my-claudecode:code-reviewer
**Supporting Agents**: oh-my-claudecode:architect, oh-my-claudecode:qa-tester, oh-my-claudecode:security-reviewer
**Situation**: Reviewing completed work and managing merges
**Usage**:
- Include task ID for individual task review (e.g., "review and merge SP-001-003")
- Include sprint ID for sprint completion review and merge (e.g., "review and merge sprint SP-025")

Review the completed work and execute the appropriate workflow:

---

## For Individual Task Review

**Pre-Review Setup:**
1. Review process documents in `project-docs/plans/process/`
2. Review PEP orientation documents in `project-docs/plans/orientation/`
3. Check task requirements in `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
4. Understand acceptance criteria and success metrics

**Navigate to Worktree:**
```bash
# Sprint worktree should exist from task work
cd ../sprint-SP-XXX
```

**Code Review Process:**
1. **Architecture Compliance:**
   - Verify unified FHIRPath architecture adherence
   - Confirm thin dialect implementation (no business logic in dialects)
   - Validate population-first design patterns
   - Check CTE-first SQL generation approach

2. **Code Quality Assessment:**
   - Review adherence to `project-docs/process/coding-standards.md`
   - Verify test coverage meets 90%+ target
   - Check documentation completeness and accuracy
   - Assess error handling and logging practices

3. **Specification Compliance:**
   - Validate impact on FHIRPath, SQL-on-FHIR, CQL compliance
   - Ensure compatibility with both DuckDB and PostgreSQL
   - Check performance implications for population-scale analytics
   - Verify alignment with 100% compliance goals

**Testing Validation:**
1. Run comprehensive test suite
2. Execute specification compliance tests if applicable
3. Validate multi-database functionality
4. Check for regressions in existing functionality

**Review Documentation:**
1. Create review summary: `project-docs/plans/reviews/SP-XXX-YYY-review.md`
2. Include findings, recommendations, and approval status
3. Document any architectural insights or lessons learned

**If APPROVED - Task Approval Workflow:**
1. Notify that task is approved for commit
2. Changes will be committed to sprint branch with task ID
3. No git merge operations required for individual tasks
4. Task will merge to main as part of sprint completion
5. **Keep worktree active** - sprint worktree persists until sprint completion

**If CHANGES NEEDED:**
1. Provide specific, actionable feedback in review document
2. Update task status to "needs revision"
3. Create follow-up tasks if major changes required
4. Guide with clear next steps

---

## For Sprint Completion Review

**Trigger:** Sprint is complete and ready for merge review

**Sprint Validation Process:**

**1. Review Sprint Documentation:**
- Read sprint summary from `project-docs/plans/current-sprint/`
- Review all completed tasks and their commit messages
- Check milestone progress and compliance metrics
- Identify any concerns or issues

**2. Navigate to Sprint Worktree:**
```bash
cd ../sprint-SP-XXX
```

**3. Sprint Validation (on sprint worktree):**
```bash
# Pull latest changes
git pull origin sprint/SP-XXX

# Run validation tests
python -m pytest tests/
python tests/run_compliance.py

# Verify both databases
python tests/run_tests.py --dialect duckdb
python tests/run_tests.py --dialect postgresql
```

**4. Provide Sprint Validation Report:**
- Test results summary
- Architecture compliance findings
- Any concerns or issues discovered
- Recommendation: Approve merge or defer for fixes

**5. Merge Execution:**
```bash
# From main directory
git checkout main
git pull origin main

# Merge sprint branch
git merge sprint/SP-XXX --no-ff -m "Merge sprint/SP-XXX: [PEP description]"

# Push to remote
git push origin main
```

---

## Post-Merge Worktree Cleanup

**After sprint merge to main is complete:**

```bash
# Navigate to main directory
cd ../[main-directory-name]

# Remove sprint worktree
git worktree remove ../sprint-SP-XXX

# Remove any task worktrees (if they exist)
git worktree list | grep task-SP-XXX | awk '{print $1}' | xargs -I {} git worktree remove {}

# Prune stale worktree metadata
git worktree prune

# Verify cleanup
git worktree list
```

**Cleanup Notes:**
- Only remove worktrees AFTER sprint is successfully merged to main
- Worktree removal frees disk space and keeps workspace clean
- `git worktree prune` cleans up stale administrative files
- Verify with `git worktree list` to ensure clean state

---

## Quality Gates

Ensure all merged work maintains architectural integrity, advances specification compliance, and supports long-term maintainability of the FHIR4DS platform.

**For Tasks:**
- Zero business logic in database dialects (critical)
- All tests pass on both databases
- No hardcoded values, configuration externalized
- Root cause fixes only, no band-aid solutions
- 90%+ test coverage
- Documentation complete and accurate

**For Sprints:**
- All sprint tasks completed and committed
- Full test suite passes (100% pass rate)
- Both DuckDB and PostgreSQL tested
- Official specification tests pass
- No regressions from previous sprint
- Architectural compliance verified
- Documentation complete and accurate

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Comprehensive code review | `oh-my-claudecode:code-reviewer` | opus |
| Quick code checks | `oh-my-claudecode:code-reviewer-low` | haiku |
| Architecture verification | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Test validation | `oh-my-claudecode:qa-tester` | sonnet |
| Comprehensive QA | `oh-my-claudecode:qa-tester-high` | opus |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Quick security scan | `oh-my-claudecode:security-reviewer-low` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |
