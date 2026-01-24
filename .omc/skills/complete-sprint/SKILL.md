---
name: complete-sprint
description: Complete sprint review, documentation, and provide worktree cleanup guidance
triggers:
  - complete sprint
  - finish sprint
  - close sprint
  - sprint completion
argument-hint: "[SPRINT-ID]"
---

# Complete Sprint Skill

**Primary Agent**: `oh-my-claudecode:architect`
**Supporting Agents**: `oh-my-claudecode:qa-tester`, `oh-my-claudecode:code-reviewer`, `oh-my-claudecode:security-reviewer`, `oh-my-claudecode:writer`

## Purpose

Conduct comprehensive sprint completion review, update documentation, and provide worktree cleanup guidance.

## When to Activate

When user says:
- "complete sprint SP-001"
- "finish sprint SP-001"
- "close sprint SP-001"

## Workflow

### Sprint Analysis

1. **Completion Assessment:**
   - Review all tasks in `project-docs/plans/tasks/` for current sprint
   - Analyze completion rates against original sprint plan
   - Identify completed, partial, and deferred work
   - Assess sprint goals achievement

2. **Quality Metrics:**
   - Evaluate test coverage improvements
   - Assess specification compliance advancement
   - Review architectural principle adherence
   - Measure performance impact

### Documentation Updates

1. **Sprint Summary:**
   - Update `project-docs/plans/current-sprint/sprint-XXX-summary.md`
   - Document completed work, challenges, lessons learned
   - Include metrics: tasks completed, test coverage, compliance progress

2. **Milestone Progress:**
   - Update milestone documentation in `project-docs/plans/milestones/`
   - Assess progress toward milestone completion
   - Identify critical path items for next sprint

3. **Task Documentation:**
   - Ensure all completed tasks are properly documented
   - Archive completed task documentation if appropriate
   - Update task dependencies and follow-up items

### PEP Progress Assessment (if final sprint for PEP)

1. **PEP Completion Review:**
   - Evaluate PEP success criteria achievement
   - Assess architectural goals fulfillment
   - Review specification compliance improvements

2. **Architecture Impact:**
   - Conduct comprehensive architecture review
   - Verify unified FHIRPath architecture implementation
   - Confirm thin dialect patterns
   - Validate population-first design adoption

3. **PEP Documentation:**
   - Move completed PEP to `project-docs/peps/summaries/pep-XXX-[name]/`
   - Create implementation summary
   - Document outcomes, metrics, lessons learned

### Next Sprint Preparation

1. **Sprint Planning:**
   - Identify next priority PEP or continuation work
   - Create new sprint plan if starting new PEP
   - Update current sprint folder with new active sprint

2. **Team Guidance:**
   - Update orientation materials if new patterns established
   - Provide architectural guidance for upcoming work
   - Document process improvements discovered

### Compliance and Quality Gates
1. Run comprehensive compliance assessment
2. Validate multi-database functionality
3. Assess progress toward 100% specification compliance
4. Document technical debt or architectural concerns

### Worktree Cleanup Guidance

**After sprint merge to main:**
```bash
# Navigate to main directory from sprint worktree
cd ../[main-directory-name]

# List all worktrees
git worktree list

# Remove sprint worktree
git worktree remove ../sprint-SP-XXX

# Remove any task worktrees
git worktree list | grep task-SP-XXX | awk '{print $1}' | xargs -I {} git worktree remove {}

# Prune stale worktree metadata
git worktree prune
```

## Deliverables

- Updated sprint documentation with completion metrics
- Milestone progress assessment
- PEP completion documentation (if applicable)
- Architectural review summary
- Recommendations for next sprint
- Worktree cleanup instructions

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Architecture review | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Quick architecture lookups | `oh-my-claudecode:architect-low` | haiku |
| Comprehensive QA testing | `oh-my-claudecode:qa-tester` | sonnet |
| Production-ready QA | `oh-my-claudecode:qa-tester-high` | opus |
| Code quality review | `oh-my-claudecode:code-reviewer` | opus |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Codebase exploration | `oh-my-claudecode:explore` | haiku |
| Documentation updates | `oh-my-claudecode:writer` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |
