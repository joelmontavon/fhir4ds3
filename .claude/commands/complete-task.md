# Complete Task

**Primary Agent**: oh-my-claudecode:executor
**Situation**: Implementing and completing an assigned task
**Usage**: Include task ID (e.g., "complete task SP-001-003")

Complete the specified task following the full development workflow:

**Orientation and Setup:**
1. Review files in `project-docs/plans/orientation/` for current project guidance
2. Study task requirements in `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
3. Understand success criteria, dependencies, and acceptance conditions
4. Review `project-docs/process/coding-standards.md` for implementation standards

**Git Worktree Workflow:**
1. **Project Structure**: Work from main directory, use worktrees for task branches
2. **Check for sprint worktree**:
   ```bash
   # Check if sprint worktree exists
   ls ../sprint-SP-XXX 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
   ```
3. **If sprint worktree exists**:
   ```bash
   cd ../sprint-SP-XXX
   git pull origin sprint/SP-XXX
   ```
4. **If no sprint worktree**: Create from main
   ```bash
   # From main directory, create sprint worktree
   git worktree add ../sprint-SP-XXX sprint/SP-XXX
   cd ../sprint-SP-XXX
   ```
5. **For individual task worktrees** (optional, for complex tasks):
   ```bash
   # From sprint worktree, create task worktree
   git worktree add ../task-SP-XXX-YYY SP-XXX-YYY-[task-name]
   cd ../task-SP-XXX-YYY
   ```
6. **Naming Conventions**:
   - Sprint worktrees: `../sprint-SP-XXX`
   - Task worktrees: `../task-SP-XXX-YYY`
   - Branch names: `sprint/SP-XXX`, `SP-XXX-YYY-[task-name]`

**Implementation:**
1. Follow unified FHIRPath architecture principles:
   - No business logic in database dialects (syntax only)
   - Population-first design patterns
   - CTE-first SQL generation approach
   - Single execution foundation for all specifications

2. **Code Quality Requirements:**
   - Write comprehensive tests (90%+ coverage target)
   - Ensure compatibility with both DuckDB and PostgreSQL
   - Follow population-scale analytics patterns
   - Update relevant documentation

3. **Testing Requirements:**
   - Run all tests before commit
   - Verify specification compliance impact
   - Test in both database environments
   - Validate performance implications

**Documentation Updates:**
1. Update task status in `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
2. Document any architectural decisions or patterns used
3. Update relevant architecture documentation if needed
4. Note any dependencies or blockers discovered

**Completion Workflow:**
1. **Code Cleanup:**
   - Remove all dead code and unused imports
   - Delete temporary files (e.g., `work/backup_*.py`, debug scripts)
   - Clean up any exploratory or test files not needed for production
   - Remove commented-out code blocks unless they serve documentation purposes
   - Ensure no hardcoded values or development artifacts remain

2. **Pre-commit Validation:**
   - All tests passing
   - Code follows standards
   - Documentation complete
   - No hardcoded values introduced
   - Working directory clean of temporary files

3. **Commit (Conventional Commit format):**
   - Single-line descriptive commit message: `type(scope): description (Task: SP-XXX-YYY)`
   - Types: `feat`, `fix`, `docs`, `arch`, `compliance`, `dialect`, `test`, `refactor`
   - Do not mention AI assistance or personal identifiers
   - Commit to sprint branch
   - No individual task push to GitHub needed

4. **Worktree Management:**
   - If using task worktree: Commit changes, return to sprint worktree
   - Keep sprint worktree active for sprint duration
   - Do NOT remove worktrees - cleanup happens after sprint merge

5. **Status Updates:**
   - Mark task as "completed" in task documentation
   - Update sprint progress if tracking spreadsheet exists
   - Notify that task is complete and committed to sprint branch

**Worktree Cleanup (After Sprint Merge):**
- Wait for sprint to be merged to main
- Then remove worktrees:
  ```bash
  # Remove task worktrees
  cd ../task-SP-XXX-YYY
  git worktree remove ../task-SP-XXX-YYY

  # Remove sprint worktree (after sprint complete)
  cd ../[main-directory]
  git worktree remove ../sprint-SP-XXX
  git worktree prune
  ```

**Quality Focus:**
Ensure all work advances FHIR4DS toward 100% specification compliance while maintaining architectural integrity and population-scale performance.

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Simple implementation | `oh-my-claudecode:executor` | sonnet |
| Quick/low-complexity changes | `oh-my-claudecode:executor-low` | haiku |
| Complex refactoring | `oh-my-claudecode:executor-high` | opus |
| Build errors | `oh-my-claudecode:build-fixer` | sonnet |
| Simple build fixes | `oh-my-claudecode:build-fixer-low` | haiku |
| TDD guidance | `oh-my-claudecode:tdd-guide` | sonnet |
| Quick test suggestions | `oh-my-claudecode:tdd-guide-low` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |
