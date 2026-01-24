# Complete Sprint

**Primary Agent**: oh-my-claudecode:architect
**Supporting Agents**: oh-my-claudecode:qa-tester, oh-my-claudecode:code-reviewer, oh-my-claudecode:security-reviewer, oh-my-claudecode:writer
**Situation**: Completing sprint and updating all documentation
**Usage**: Include sprint ID (e.g., "complete sprint SP-001")

Conduct comprehensive sprint completion review and documentation updates:

**Sprint Analysis:**
1. **Completion Assessment:**
   - Review all tasks in `project-docs/plans/tasks/` for current sprint
   - Analyze completion rates against original sprint plan
   - Identify completed, partial, and deferred work
   - Assess sprint goals achievement

2. **Quality Metrics:**
   - Evaluate test coverage improvements
   - Assess specification compliance advancement
   - Review architectural principle adherence
   - Measure performance impact of changes

**Documentation Updates:**
1. **Sprint Summary:**
   - Update `project-docs/plans/current-sprint/sprint-XXX-summary.md`
   - Document completed work, challenges, and lessons learned
   - Include metrics: tasks completed, test coverage, compliance progress
   - Note any architectural decisions or patterns established

2. **Milestone Progress:**
   - Update relevant milestone documentation in `project-docs/plans/milestones/`
   - Assess progress toward milestone completion
   - Identify critical path items for next sprint
   - Update timeline estimates if needed

3. **Task Documentation:**
   - Ensure all completed tasks are properly documented
   - Archive completed task documentation if appropriate
   - Update task dependencies and follow-up items

**PEP Progress Assessment (if final sprint for PEP):**
1. **PEP Completion Review:**
   - Evaluate PEP success criteria achievement
   - Assess architectural goals fulfillment
   - Review specification compliance improvements
   - Document lessons learned and implementation insights

2. **Architecture Impact:**
   - Conduct comprehensive architecture review
   - Verify unified FHIRPath architecture implementation
   - Confirm thin dialect patterns (no business logic in dialects)
   - Validate population-first design adoption
   - Check CTE-first SQL generation effectiveness

3. **PEP Documentation:**
   - Move completed PEP to `project-docs/peps/summaries/pep-XXX-[name]/`
   - Create implementation summary using completion template
   - Document outcomes, metrics, and lessons learned
   - Update PEP status and completion metadata

**Next Sprint Preparation:**
1. **Sprint Handoff:**
   - Notify that sprint documentation is complete
   - Execute sprint merge to main
   - Handle sprint branch cleanup

2. **Sprint Planning:**
   - Identify next priority PEP or continuation work
   - Create new sprint plan if starting new PEP
   - Update current sprint folder with new active sprint

3. **Team Guidance:**
   - Update orientation materials if new patterns established
   - Provide architectural guidance for upcoming work
   - Document any process improvements discovered

**Compliance and Quality Gates:**
1. Run comprehensive compliance assessment
2. Validate multi-database functionality integrity
3. Assess progress toward 100% specification compliance goals
4. Document any technical debt or architectural concerns

**Worktree Cleanup (After Sprint Merge):**
After sprint merge to main, execute cleanup:

```bash
# Navigate to main directory from sprint worktree
cd ../[main-directory-name]

# List all worktrees
git worktree list

# Remove sprint worktree
git worktree remove ../sprint-SP-XXX

# Remove any task worktrees for this sprint
git worktree list | grep task-SP-XXX | awk '{print $1}' | xargs -I {} git worktree remove {}

# Prune stale worktree metadata
git worktree prune

# Verify cleanup
git worktree list
```

**Deliverables:**
- Updated sprint documentation with completion metrics
- Milestone progress assessment
- PEP completion documentation (if applicable)
- Architectural review summary
- Recommendations for next sprint or PEP
- Instructions for worktree cleanup after merge

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Architecture review | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Quick architecture lookups | `oh-my-claudecode:architect-low` | haiku |
| Comprehensive QA testing | `oh-my-claudecode:qa-tester` | sonnet |
| Production-ready QA | `oh-my-claudecode:qa-tester-high` | opus |
| Code quality review | `oh-my-claudecode:code-reviewer` | opus |
| Quick code checks | `oh-my-claudecode:code-reviewer-low` | haiku |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Quick security scan | `oh-my-claudecode:security-reviewer-low` | haiku |
| Codebase exploration | `oh-my-claudecode:explore` | haiku |
| Thorough codebase search | `oh-my-claudecode:explore-medium` | sonnet |
| Deep architectural search | `oh-my-claudecode:explore-high` | opus |
| Documentation updates | `oh-my-claudecode:writer` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |
