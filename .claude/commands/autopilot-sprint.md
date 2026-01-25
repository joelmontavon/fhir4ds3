# Autopilot Sprint

## ORCHESTRATION INSTRUCTION (For Main Thread)

**DO NOT execute this workflow directly in the main conversation.**

When this command is invoked, immediately delegate to a background general-purpose agent:

```
Task(
  subagent_type="general-purpose",
  prompt="Execute the autopilot-sprint workflow with the following user request: <USER_REQUEST>",
  run_in_background=true
)
```

Replace `<USER_REQUEST>` with the actual user input (e.g., "SP-026 architectural gaps").

The orchestrator will:
1. Run the full 8-phase workflow autonomously
2. Report progress at key checkpoints
3. Request user approval at interaction points
4. Continue until completion or cancellation

---

## Workflow Definition

**Orchestrator**: general-purpose agent (background execution)
**Primary Mode**: oh-my-claudecode:ultrapilot
**Primary Agents**: planner, architect, executor, code-reviewer, qa-tester
**Supporting**: analyst, critic, explore, security-reviewer, tdd-guide, build-fixer
**Situation**: Full automated sprint workflow from gap analysis to completion
**Usage**: Include sprint name and focus area (e.g., "autopilot sprint SP-026 architectural gaps")

**IMPORTANT**: This workflow runs in a background agent to avoid blocking the main conversation. The orchestrator agent will manage all phases and report progress.

Fully automated ultra fast sprint workflow that identifies architectural gaps or bugs, prioritizes work, creates sprint plan and tasks, executes work in parallel using ultrapilot, reviews/approves, and closes out the sprint with proper git workflow.

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
│ 6. REVIEW & APPROVE     │ 7. TEST & VALIDATE  │ 8. VALIDATE   │
│    code-reviewer        │    qa-tester       │  architect     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. MERGE WORKTREE      │ 10. CLEANUP       │ 11. DOCUMENT    │
│    git-master           │    git-master     │  writer         │
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

**CRITICAL: RALPH LOOP - PERSISTENCE UNTIL APPROVAL**

**When task completes, activate** `oh-my-claudecode:code-reviewer`:

1. **Review task branch** for architectural compliance, code quality, test coverage
2. **Decision via** `AskUserQuestion`:
   - **APPROVE**: Merge to sprint branch, proceed to next task
   - **REJECT**: **SEND BACK TO CODER** - This is NOT the end
   - **NEEDS TESTING**: Send to `oh-my-claudecode:qa-tester`
3. **Documentation:** Create review summary

**REJECTION LOOP (MANDATORY):**

```
┌─────────────────────────────────────────────────────────────┐
│  CODE → REVIEW → (REJECTED?) → CODE AGAIN → REVIEW AGAIN →  │
│                    ↑                                        │
│                    └──────── REPEAT UNTIL APPROVED ─────────┘
│                                                             │
│  THIS LOOP DOES NOT STOP UNTIL:                            │
│  ✓ Code is APPROVED by reviewer                            │
│  ✓ OR User explicitly cancels the entire sprint            │
└─────────────────────────────────────────────────────────────┘
```

**Rejection Handling:**

| Step | Action | Agent |
|------|--------|-------|
| 1 | Reviewer provides specific feedback | `code-reviewer` |
| 2 | Task returns to pool, marked "needs revision" | orchestrator |
| 3 | Coder addresses ALL feedback points | `executor` / `executor-high` |
| 4 | Coder re-submits for review | `executor` |
| 5 | Reviewer reviews AGAIN | `code-reviewer` |
| 6 | **If still rejected → LOOP BACK TO STEP 2** | - |
| 7 | **If approved → Merge to sprint branch** | orchestrator |

**MAXIMUM RETRIES:** 3 attempts per task before escalation to user

**DO NOT:**
- Skip re-review after fixes
- Merge rejected code
- Mark rejected tasks as "complete"
- Move to next task without approval

**DO:**
- Loop until approved
- Track attempt count in state file
- Provide clear feedback for each rejection
- Escalate after 3 failed attempts

### Phase 7: Test & Validate

**For tasks requiring validation:**

1. **Execute tests:** Specification compliance, multi-database, performance
2. **Validation report:** Test results, pass/fail, recommendations
3. **Feedback:** Pass → approve, Fail → return to executor

### Phase 8: Sprint Validation

**When all tasks complete and are approved:**

1. **Navigate to sprint worktree:**
   ```bash
   cd ../sprint-SP-XXX
   ```

2. **Run full test suite:**
   ```bash
   python -m pytest tests/
   python tests/run_compliance.py
   ```

3. **Verify all quality gates:**
   - All tasks approved by code-reviewer
   - All tests passing (100%)
   - No merge conflicts in sprint branch

4. **Report validation results:**
   ```
   ✅ Sprint Validation Complete
   ✅ 15/15 tasks approved
   ✅ 1,247 tests passing
   ✅ Ready to merge to main
   ```

**If validation fails:**
- Report failures to user
- Create tasks for fixes
- Return to Phase 5 (Execution) for remediation

### Phase 9: Merge Worktree

**CRITICAL:** Only proceed after Phase 8 validation passes

**Use** `oh-my-claudecode:git-master` **skill for all merge operations**

1. **Switch to main directory:**
   ```bash
   cd ../[main-directory]
   ```

2. **Checkout and update main branch:**
   ```bash
   git checkout main
   git pull origin main
   ```

3. **Merge sprint branch:**
   ```bash
   git merge sprint-SP-XXX --no-ff -m "Merge sprint-SP-XXX: [sprint name]"
   ```

4. **Resolve any conflicts** (if they arise):
   - Use `git-master` for conflict resolution
   - Test after resolution
   - Commit the merge

5. **Push to remote:**
   ```bash
   git push origin main
   ```

6. **Verify merge:**
   ```bash
   git log --oneline -5
   ```

**Report merge completion:**
```
✅ Sprint SP-XXX merged to main
✅ Commit: abc1234
✅ Pushed to origin/main
```

### Phase 10: Worktree Cleanup

**After successful merge:**

1. **Remove sprint worktree:**
   ```bash
   git worktree remove ../sprint-SP-XXX
   ```

2. **Prune worktree list:**
   ```bash
   git worktree prune
   ```

3. **Verify cleanup:**
   ```bash
   git worktree list
   ```

4. **Delete sprint branch** (optional, after confirmation):
   ```bash
   git branch -d sprint-SP-XXX
   ```

### Phase 11: Documentation

**Final sprint documentation:**

1. **Sprint summary:** `project-docs/plans/archived-sprints/SP-XXX-summary.md`
2. **Task archive:** Move task documents to archived-sprints/
3. **Retrospective:** Lessons learned, metrics, improvements

## Git Workflow Summary

```bash
# ──────────────────────────────────────────────────────────────
# SPRINT SETUP (Phase 5)
# ──────────────────────────────────────────────────────────────
git worktree add ../sprint-SP-XXX sprint/SP-XXX
cd ../sprint-SP-XXX

# ──────────────────────────────────────────────────────────────
# PER-TASK WORKFLOW (Phase 5-6, Parallel)
# ──────────────────────────────────────────────────────────────
git checkout -b SP-XXX-YYY-[task-name]
# ... implement and test ...
git commit -m "feat(scope): description (Task: SP-XXX-YYY)"
git checkout sprint-SP-XXX

# Review (if approved)
git merge SP-XXX-YYY-[task-name] --no-ff
git branch -d SP-XXX-YYY-[task-name]

# ──────────────────────────────────────────────────────────────
# SPRINT VALIDATION (Phase 8)
# ──────────────────────────────────────────────────────────────
cd ../sprint-SP-XXX
python -m pytest tests/
python tests/run_compliance.py

# ──────────────────────────────────────────────────────────────
# MERGE WORKTREE TO MAIN (Phase 9) ⭐ KEY STEP
# ──────────────────────────────────────────────────────────────
cd ../[main-directory]
git checkout main
git pull origin main
git merge sprint-SP-XXX --no-ff -m "Merge sprint-SP-XXX: [description]"
git push origin main

# ──────────────────────────────────────────────────────────────
# WORKTREE CLEANUP (Phase 10)
# ──────────────────────────────────────────────────────────────
git worktree remove ../sprint-SP-XXX
git worktree prune
git branch -d sprint-SP-XXX  # optional
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
| Sprint Validation | architect | opus | No |
| **Merge Worktree** | git-master | - | No |
| Cleanup | git-master | - | No |
| Documentation | writer | haiku | No |

## Progress Tracking

**State File:** `.omc/state/autopilot-sprint.json`

```json
{
  "sprint": "SP-XXX",
  "status": "executing",
  "phases": {
    "analysis": "complete",
    "prioritization": "complete",
    "planning": "complete",
    "execution": {
      "total": 15,
      "pending": 5,
      "in_progress": 2,
      "completed": 8,
      "approved": 6,
      "rejected": 2
    }
  },
  "tasks": [
    {
      "id": "SP-XXX-001",
      "title": "Fix CQL translation bug",
      "status": "approved",
      "worker": "executor-2",
      "reviewAttempts": 1,
      "rejectionCount": 0
    },
    {
      "id": "SP-XXX-007",
      "title": "Add FHIRPath function",
      "status": "needs_revision",
      "worker": "executor-3",
      "reviewAttempts": 2,
      "rejectionCount": 1,
      "lastRejectionReason": "Missing test coverage for edge cases",
      "feedback": ["Add tests for null input handling", "Add tests for empty collections"]
    }
  ]
}
```

**State Tracking for Rejection Loop:**
- `reviewAttempts`: Number of times this task has been reviewed
- `rejectionCount`: Number of times rejected
- `lastRejectionReason`: Most recent rejection feedback
- `feedback`: Array of specific issues to address
- **Task cannot be marked "completed" until `status === "approved"`**

### Background Progress Reporting

**IMPORTANT:** Since this workflow runs in a background agent, you MUST provide regular progress updates to keep the user informed.

**Progress Checkpoints:**

1. **Phase Start:** Report each phase as it begins
   ```
   🏃 Starting Phase 1: Gap/Bug Analysis...
   ```

2. **Phase Complete:** Report when each phase completes
   ```
   ✅ Phase 1 Complete: Found 23 gaps (7 critical, 8 high, 5 medium, 3 low)
   ```

3. **User Interaction Required:** Pause and wait for response
   - Present sprint plan for approval
   - Present code review decisions
   - Request sprint completion confirmation

4. **Task Progress:** During ultrapilot execution, report every 2-3 tasks
   ```
   ⏳ Execution Progress: 8/15 tasks (5 approved, 2 in review, 1 rejected)
   ```

5. **Rejection Loop Progress:** When a task is rejected and returns for re-coding
   ```
   🔄 Task SP-XXX-007 REJECTED (attempt 1/3)
      Reason: Missing test coverage for edge cases
      → Sending back to executor-3 for fixes...
   ```

6. **Rejection Resolution:** When a previously rejected task is approved
   ```
   ✅ Task SP-XXX-007 APPROVED (after 2 attempts)
      → Merging to sprint branch
   ```

7. **Blockers:** Immediately report any issues requiring user input
   ```
   ⚠️ BLOCKER: Task SP-XXX-007 has merge conflicts. Awaiting guidance.
   ```

8. **Merge Phase Progress:** Report during worktree merge (Phase 9)
   ```
   🔀 Phase 9: Merging worktree to main...
      → Switched to main branch
      → Merging sprint-SP-XXX...
      → Merge complete: abc1234
      → Pushed to origin/main
   ```

9. **Completion:** Final summary with deliverables
   ```
   🎉 Sprint SP-XXX Complete!
   ✅ 15/15 tasks approved
   ✅ All tests passing
   ✅ Merged to main
   ```

**Output File:** Background agent output can be checked via the task ID.

## User Interaction Points

1. **Sprint Planning:** Present plan, request approval
2. **Per-Task Review:** Approve/reject/needs-testing decisions
3. **Sprint Validation Confirm:** Confirm all tests passed before merge
4. **Merge Confirmation:** Explicit approval before merging worktree to main
5. **Cleanup Confirm:** Confirm worktree removal after successful merge

## Cancellation

User says "stop", "cancel", "abort":

**Graceful Shutdown:**
1. Stop spawning new tasks
2. Allow in-progress tasks to complete current work
3. Commit any completed work
4. Document current state
5. Provide resumption instructions

## Error Handling

- **Code Rejection:** NOT AN ERROR - This is the normal review loop
  - Return task to executor with feedback
  - Increment `reviewAttempts` counter
  - Executor MUST address ALL feedback points
  - Re-review is MANDATORY after fixes
  - **Loop continues until approved**

- **Maximum Review Attempts (3):** After 3 rejections
  - Escalate to user for guidance
  - Ask: "Continue retrying, take different approach, or skip this task?"
  - If user says continue, reset counter and try again
  - If user says skip, mark task as "deferred" and move on

- **Task Failure (Exception/Timeout):** Automatic retry with different worker (max 3 attempts)
- **Persistent Failure:** Escalate to user for guidance
- **Build Failures:** Invoke `oh-my-claudecode:build-fixer` automatically
- **Test Failures:** Invoke `oh-my-claudecode:qa-tester` for diagnosis
- **Merge Conflicts:** Invoke `oh-my-claudecode:git-master` for resolution

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
- ✓ **Code review APPROVED before merging** (not just reviewed - must be approved)
- ✓ **Rejection loop continues until approval** - no exceptions
- ✓ Tests pass locally
- ✓ Full test suite passes (100%)
- ✓ Sprint successfully merged

**NON-NEGOTIABLE:**
- A task is NOT "complete" until it is APPROVED by code-reviewer
- Rejected code MUST be re-coded and re-reviewed
- The process does NOT stop until approval is obtained
- The only alternative is explicit user cancellation of the entire sprint

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
| **Worktree merge to main** | `git-master` skill | - |
| **Worktree cleanup** | `git-master` skill | - |
| Documentation | `writer` | haiku |
