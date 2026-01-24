---
name: complete-task
description: Implement and complete a task following full development workflow with worktrees
triggers:
  - complete task
  - implement task
  - do task
  - finish task
argument-hint: "[TASK-ID]"
---

# Complete Task Skill

**Primary Agent**: `oh-my-claudecode:executor`
**Supporting Agents**: `oh-my-claudecode:executor-low`, `oh-my-claudecode:executor-high`, `oh-my-claudecode:build-fixer`, `oh-my-claudecode:tdd-guide`

## Purpose

Implement and complete an assigned task following the full development workflow with git worktree management.

## When to Activate

When user says:
- "complete task SP-001-003"
- "implement task SP-001-003"
- "work on task SP-001-003"

## Workflow

### Orientation and Setup
1. Review `project-docs/plans/orientation/` for current project guidance
2. Study task requirements in `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
3. Understand success criteria, dependencies, and acceptance conditions
4. Review `project-docs/process/coding-standards.md`

### Git Worktree Workflow
1. **Check for sprint worktree:**
   ```bash
   ls ../sprint-SP-XXX 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
   ```
2. **If sprint worktree exists:**
   ```bash
   cd ../sprint-SP-XXX
   git pull origin sprint/SP-XXX
   ```
3. **If no sprint worktree:** Create from main
   ```bash
   git worktree add ../sprint-SP-XXX sprint/SP-XXX
   cd ../sprint-SP-XXX
   ```
4. **For complex tasks:** Create optional task worktree
   ```bash
   git worktree add ../task-SP-XXX-YYY SP-XXX-YYY-[task-name]
   cd ../task-SP-XXX-YYY
   ```

### Implementation
1. Follow unified FHIRPath architecture principles:
   - No business logic in database dialects
   - Population-first design patterns
   - CTE-first SQL generation approach
   - Single execution foundation for all specifications
2. Write comprehensive tests (90%+ coverage target)
3. Ensure compatibility with both DuckDB and PostgreSQL
4. Update relevant documentation

### Testing
- Run all tests before commit
- Verify specification compliance impact
- Test in both database environments
- Validate performance implications

### Completion
1. **Code Cleanup:** Remove dead code, unused imports, temporary files
2. **Pre-commit Validation:** Tests passing, code follows standards, documentation complete
3. **Commit:** Conventional commit format: `type(scope): description (Task: SP-XXX-YYY)`
4. **Status Updates:** Mark task as completed in documentation

### Worktree Cleanup (After Sprint Merge)
```bash
cd ../[main-directory]
git worktree remove ../sprint-SP-XXX
git worktree prune
```

## Quality Focus

Ensure all work advances FHIR4DS toward 100% specification compliance while maintaining architectural integrity and population-scale performance.

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Simple implementation | `oh-my-claudecode:executor` | sonnet |
| Quick changes | `oh-my-claudecode:executor-low` | haiku |
| Complex refactoring | `oh-my-claudecode:executor-high` | opus |
| Build errors | `oh-my-claudecode:build-fixer` | sonnet |
| Simple build fixes | `oh-my-claudecode:build-fixer-low` | haiku |
| TDD guidance | `oh-my-claudecode:tdd-guide` | sonnet |
| Git operations | `oh-my-claudecode:git-master` skill | - |
