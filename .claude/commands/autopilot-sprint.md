# Autopilot Sprint

**Primary Mode**: oh-my-claudecode:ultrapilot
**Primary Agents**: planner, architect, executor, code-reviewer, qa-tester
**Supporting**: analyst, critic, explore, security-reviewer, tdd-guide, build-fixer
**Situation**: Full automated sprint workflow from gap analysis to completion
**Usage**: Include sprint name and focus area (e.g., "autopilot sprint SP-026 architectural gaps")

Fully automated sprint workflow that identifies architectural gaps or bugs, prioritizes work, creates sprint plan and tasks, executes work in parallel using ultrapilot, reviews/approves, and closes out the sprint with proper git workflow.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. GAP/BUG ANALYSIS      │ 2. PRIORITIZE   │ 3. CREATE PLAN │
│    architect + explore    │    analyst     │  planner       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CREATE TASKS        │ 5. PARALLEL EXECUTION (ULTRAPILOT)    │
│    planner             │    executor × N (5 workers)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. REVIEW & APPROVE     │ 7. TEST & VALIDATE  │ 8. CLOSE OUT  │
│    code-reviewer        │    qa-tester       │  architect     │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Phases

### Phase 1: Gap/Bug Analysis (Parallel)

Execute three parallel analyses:

**1. Deep Codebase Exploration** (`oh-my-claudecode:explore-high`):
- Search for architectural violations
- Find deviations from core principles
- Locate performance bottlenecks
- Identify specification compliance gaps
- Find bugs and error patterns

**2. Architecture Analysis** (`oh-my-claudecode:architect`):
- Verify unified FHIRPath architecture compliance
- Check thin dialect implementation (no business logic)
- Validate population-first design patterns
- Assess CTE-first SQL generation
- Review multi-database parity

**3. Security Analysis** (`oh-my-claudecode:security-reviewer`):
- Scan for security vulnerabilities
- Check input validation patterns
- Review SQL injection prevention
- Assess access control implementation

**Output:** Categorized gap/bug list:
- **Critical (P0)**: Architectural violations, security issues
- **High (P1)**: Specification compliance blockers
- **Medium (P2)**: Technical debt, performance issues
- **Low (P3)**: Code quality improvements

### Phase 2: Prioritization

**Use** `oh-my-claudecode:analyst`:

1. **Analyze Impact:** Business impact, technical complexity, dependencies, risk
2. **Apply Framework:** `Priority = (Impact × Urgency) / Effort`
3. **Select Top Items:** Choose items fitting sprint capacity
4. **Balance:** Mix of quick wins and strategic items

### Phase 3: Create Sprint Plan

**Use** `oh-my-claudecode:planner`:

1. **Strategic Vision:** Define objectives, align with 100% compliance goals
2. **Sprint Plan Document:** `project-docs/plans/current-sprint/sprint-XXX-[name].md`
3. **User Approval:** Present plan via `AskUserQuestion`, get explicit approval

### Phase 4: Create Tasks

**For each prioritized item:**

1. **Task Document:** `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
2. **Include:** Acceptance criteria, architectural requirements, dependencies, estimates
3. **Orientation Guide:** `project-docs/plans/orientation/SP-XXX-orientation.md`

### Phase 5: Parallel Execution (ULTRAPILOT)

**Activate** `oh-my-claudecode:ultrapilot`:

```bash
# Create sprint worktree
git worktree add ../sprint-SP-XXX sprint/SP-XXX
cd ../sprint-SP-XXX

# Ultrapiplot spawns up to 5 parallel executor workers
# Each worker claims and completes tasks independently
```

**Per-Task Execution:**
1. Worker claims task from shared pool
2. Create task branch: `git checkout -b SP-XXX-YYY-[task-name]`
3. Implement using `oh-my-claudecode:executor` or `oh-my-claudecode:executor-high`
4. Run tests locally
5. Commit: `git commit -m "type(scope): description (Task: SP-XXX-YYY)"`
6. Notify completion

**Ultrapiplot Features:**
- File ownership coordination (prevents conflicts)
- Atomic task claiming (5-minute timeout)
- Up to 5 parallel executors
- Automatic retry on failure

### Phase 6: Review & Approve

**When task completes, activate** `oh-my-claudecode:code-reviewer`:

1. **Review task branch** for architectural compliance, code quality, test coverage
2. **Decision via** `AskUserQuestion`:
   - **APPROVE**: Merge to sprint branch
   - **REJECT**: Send back to executor with feedback
   - **NEEDS TESTING**: Send to `oh-my-claudecode:qa-tester`
3. **Documentation:** Create review summary

### Phase 7: Test & Validate

**For tasks requiring validation:**

1. **Execute tests:** Specification compliance, multi-database, performance
2. **Validation report:** Test results, pass/fail, recommendations
3. **Feedback:** Pass → approve, Fail → return to executor

### Phase 8: Sprint Closeout

**When all tasks complete:**

1. **Sprint validation:**
   ```bash
   cd ../sprint-SP-XXX
   python -m pytest tests/
   python tests/run_compliance.py
   ```

2. **Merge to main:**
   ```bash
   cd ../[main-directory]
   git checkout main
   git pull origin main
   git merge sprint-SP-XXX --no-ff
   git push origin main
   ```

3. **Cleanup:**
   ```bash
   git worktree remove ../sprint-SP-XXX
   git worktree prune
   ```

4. **Documentation:** Sprint summary, task archive, retrospective

## Git Workflow Summary

```bash
# Sprint Setup
git worktree add ../sprint-SP-XXX sprint/SP-XXX

# Per-Task (parallel)
git checkout -b SP-XXX-YYY-[task-name]
# ... implement and test ...
git commit -m "feat(scope): description (Task: SP-XXX-YYY)"
git checkout sprint-SP-XXX

# Review (if approved)
git merge SP-XXX-YYY-[task-name] --no-ff

# Sprint Completion
git checkout main
git merge sprint-SP-XXX --no-ff
git push origin main
git worktree remove ../sprint-SP-XXX
git worktree prune
```

## Agent Orchestration

| Phase | Agent | Model | Parallel |
|-------|-------|-------|----------|
| Gap Analysis | architect, explore-high, security-reviewer | opus | ✅ Yes |
| Prioritization | analyst | opus | No |
| Sprint Planning | planner | opus | No |
| Task Creation | planner | opus | ✅ Yes |
| **Execution** | executor, executor-high | sonnet/opus | **✅ ULTRAPILOT** |
| Review | code-reviewer | opus | ✅ Yes |
| Testing | qa-tester | sonnet | ✅ Yes |
| Closeout | architect | opus | No |

## Progress Tracking

**State File:** `.omc/state/autopilot-sprint.json`

## User Interaction Points

1. **Sprint Planning:** Present plan, request approval
2. **Per-Task Review:** Approve/reject/needs-testing decisions
3. **Sprint Completion:** Confirm merge and cleanup

## Cancellation

User says "stop", "cancel", "abort":

**Graceful Shutdown:**
1. Stop spawning new tasks
2. Allow in-progress tasks to complete current work
3. Commit any completed work
4. Document current state
5. Provide resumption instructions

## Deliverables

- Gap/bug analysis report
- Prioritized sprint plan (user approved)
- All task documents
- Completed implementations (all approved)
- Test results showing compliance
- Sprint merged to main
- Worktree cleanup completed
- Sprint retrospective documentation

## Quality Gates

- ✓ Sprint plan approved by user
- ✓ Code review passes before merging
- ✓ Tests pass locally
- ✓ Full test suite passes (100%)
- ✓ Sprint successfully merged

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Deep codebase exploration | `oh-my-claudecode:explore-high` | opus |
| Architecture analysis | `oh-my-claudecode:architect` | opus |
| Security analysis | `oh-my-claudecode:security-reviewer` | opus |
| Prioritization | `oh-my-claudecode:analyst` | opus |
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Plan critique | `oh-my-claudecode:critic` | opus |
| Implementation | `oh-my-claudecode:executor` | sonnet |
| Complex implementation | `oh-my-claudecode:executor-high` | opus |
| Code review | `oh-my-claudecode:code-reviewer` | opus |
| Test validation | `oh-my-claudecode:qa-tester` | sonnet |
| Production QA | `oh-my-claudecode:qa-tester-high` | opus |
| Build fixes | `oh-my-claudecode:build-fixer` | sonnet |
| TDD guidance | `oh-my-claudecode:tdd-guide` | sonnet |
| Git operations | `oh-my-claudecode:git-master` skill | - |
