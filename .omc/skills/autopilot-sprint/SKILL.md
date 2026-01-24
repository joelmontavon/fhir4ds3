---
name: autopilot-sprint
description: Full automated sprint workflow: gap analysis → prioritization → planning → parallel execution → review → completion
triggers:
  - autopilot sprint
  - auto sprint
  - ultrapilot sprint
  - automated sprint
  - full sprint automation
argument-hint: "[sprint-name] [focus-area: gaps/bugs/features]"
---

# Autopilot Sprint Skill

**Primary Mode**: `oh-my-claudecode:ultrapilot`
**Primary Agents**: `planner`, `architect`, `executor`, `code-reviewer`, `qa-tester`
**Supporting**: `analyst`, `critic`, `explore`, `security-reviewer`, `tdd-guide`, `build-fixer`

## Purpose

Fully automated sprint workflow that identifies architectural gaps or bugs, prioritizes work, creates sprint plan and tasks, executes work in parallel, reviews/approves, and closes out the sprint with proper git workflow.

## When to Activate

When user says:
- "autopilot sprint for bug fixes"
- "automated sprint to fix architectural gaps"
- "ultrapilot sprint SP-025"
- "auto sprint focused on CQL compliance"
- "run full automated sprint"

## Overview

This skill orchestrates the complete sprint lifecycle:

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

## Workflow

### Phase 1: Gap/Bug Analysis

**Execute in parallel:**

1. **Deep Codebase Exploration** (`oh-my-claudecode:explore-high`):
   - Search for architectural violations
   - Find deviations from core principles
   - Locate performance bottlenecks
   - Identify specification compliance gaps
   - Find bugs and error patterns

2. **Architecture Analysis** (`oh-my-claudecode:architect`):
   - Verify unified FHIRPath architecture compliance
   - Check thin dialect implementation
   - Validate population-first design patterns
   - Assess CTE-first SQL generation
   - Review multi-database parity

3. **Security Analysis** (`oh-my-claudecode:security-reviewer`):
   - Scan for security vulnerabilities
   - Check input validation patterns
   - Review SQL injection prevention
   - Assess access control implementation

**Output:** Comprehensive gap/bug list categorized by:
- **Critical (P0)**: Architectural violations, security issues
- **High (P1)**: Specification compliance blockers
- **Medium (P2)**: Technical debt, performance issues
- **Low (P3)**: Code quality improvements

### Phase 2: Prioritization

**Use** `oh-my-claudecode:analyst` **to:**

1. **Analyze Impact:**
   - Business impact of each gap/bug
   - Technical complexity to fix
   - Dependencies between items
   - Risk assessment

2. **Apply Prioritization Framework:**
   ```
   Priority = (Impact × Urgency) / Effort
   ```
   - Impact: Business/user impact (1-10)
   - Urgency: Time sensitivity (1-10)
   - Effort: Implementation effort (1-10)

3. **Select Top Items:**
   - Choose items that fit sprint capacity
   - Ensure mix of quick wins and strategic items
   - Balance risk and reward
   - Consider team velocity

**Output:** Prioritized list of top items for sprint (typically 5-15 items)

### Phase 3: Create Sprint Plan

**Use** `oh-my-claudecode:planner` **to:**

1. **Strategic Vision:**
   - Define sprint objectives
   - Align with 100% compliance goals
   - Set success metrics

2. **Sprint Plan Document:**
   - File: `project-docs/plans/current-sprint/sprint-XXX-[name].md`
   - Use template: `project-docs/plans/templates/sprint-plan-template.md`

3. **Get User Approval:**
   - Present sprint plan
   - Explain trade-offs
   - Request explicit approval via `AskUserQuestion`

### Phase 4: Create Tasks

**For each prioritized item, create task:**

1. **Task Document:**
   - File: `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
   - Use template: `project-docs/plans/templates/task-template.md`
   - Include:
     - Clear acceptance criteria
     - Architectural requirements
     - Dependencies and estimates
     - Verification approach

2. **Task Assignment:**
   - Tasks are ready for parallel execution
   - No explicit assignment needed (ultrapilot handles)

3. **Orientation Guide:**
   - File: `project-docs/plans/orientation/SP-XXX-orientation.md`
   - Includes all tasks and context

### Phase 5: Parallel Execution (ULTRAPILOT)

**Activate** `oh-my-claudecode:ultrapilot` **mode:**

```bash
# Create sprint worktree
git worktree add ../sprint-SP-XXX sprint/SP-XXX

# Ultrapiplot spawns up to 5 parallel executor workers
# Each worker claims and completes tasks independently
```

**Per-Task Execution:**

1. **Worker claims task** from shared task pool
2. **Navigate to worktree**: `cd ../sprint-SP-XXX`
3. **Create task branch**: `git checkout -b SP-XXX-YYY-[task-name]`
4. **Implement solution** using `oh-my-claudecode:executor` or `oh-my-claudecode:executor-high`
5. **Run tests** locally
6. **Commit to task branch**: Conventional commit format
7. **Notify completion**

**Ultrapiplot Features:**
- **File ownership coordination** - Prevents conflicting edits
- **Atomic task claiming** - 5-minute timeout with auto-release
- **Parallel workers** - Up to 5 executors working simultaneously
- **Automatic retry** - Failed tasks are retried

### Phase 6: Review & Approve

**When task completes, activate** `oh-my-claudecode:code-reviewer`:

1. **Navigate to worktree**: `cd ../sprint-SP-XXX`
2. **Review task branch**:
   - Check architectural compliance
   - Verify code quality standards
   - Assess test coverage
   - Validate specification compliance

3. **Decision via** `AskUserQuestion`:
   - **APPROVE**: Merge to sprint branch
     ```bash
     git checkout sprint-SP-XXX
     git merge SP-XXX-YYY-[task-name] --no-ff
     git branch -d SP-XXX-YYY-[task-name]
     ```
   - **REJECT**: Send back to executor
     - Provide specific feedback
     - Task returns to pool for retry
   - **NEEDS TESTING**: Send to QA tester
     - Create verification tasks
     - Tester validates before final approval

4. **Documentation:**
   - Create review summary: `project-docs/plans/reviews/SP-XXX-YYY-review.md`
   - Update task status

### Phase 7: Test & Validate

**For tasks requiring validation, use** `oh-my-claudecode:qa-tester`:

1. **Test Execution:**
   - Run specification compliance tests
   - Multi-database validation (DuckDB + PostgreSQL)
   - Performance testing
   - Regression testing

2. **Validation Report:**
   - Test results summary
   - Pass/fail determination
   - Recommendations

3. **Feedback Loop:**
   - **PASS**: Task approved, merge to sprint
   - **FAIL**: Task returned to executor with fix requirements

### Phase 8: Sprint Closeout

**When all tasks complete:**

1. **Sprint Validation** (`oh-my-claudecode:architect`):
   ```bash
   cd ../sprint-SP-XXX
   git pull origin sprint-SP-XXX
   python -m pytest tests/
   python tests/run_compliance.py
   ```

2. **Merge to Main:**
   ```bash
   cd ../[main-directory]
   git checkout main
   git pull origin main
   git merge sprint-SP-XXX --no-ff -m "Merge sprint-SP-XXX: [description]"
   git push origin main
   ```

3. **Worktree Cleanup:**
   ```bash
   git worktree remove ../sprint-SP-XXX
   git worktree prune
   ```

4. **Documentation:**
   - Update sprint summary
   - Archive completed tasks
   - Create sprint retrospective

## Git Workflow Summary

```bash
# Sprint Setup
git worktree add ../sprint-SP-XXX sprint/SP-XXX
cd ../sprint-SP-XXX

# Per-Task (parallel)
git checkout -b SP-XXX-YYY-[task-name]
# ... implement and test ...
git commit -m "feat(scope): description (Task: SP-XXX-YYY)"
git checkout sprint-SP-XXX

# Review (if approved)
git merge SP-XXX-YYY-[task-name] --no-ff
git branch -d SP-XXX-YYY-[task-name]

# Sprint Completion (from main)
git checkout main
git merge sprint-SP-XXX --no-ff
git push origin main
git worktree remove ../sprint-SP-XXX
git worktree prune
```

## Agent Orchestration

| Phase | Agent | Model | Parallel |
|-------|-------|-------|----------|
| Gap Analysis | `architect`, `explore-high`, `security-reviewer` | opus | ✅ Yes |
| Prioritization | `analyst` | opus | No |
| Sprint Planning | `planner` | opus | No |
| Task Creation | `planner` | opus | ✅ Yes |
| **Execution** | `executor`, `executor-high` | sonnet/opus | **✅ ULTRAPILOT** |
| Review | `code-reviewer` | opus | ✅ Yes (per task) |
| Testing | `qa-tester` | sonnet | ✅ Yes |
| Closeout | `architect` | opus | No |

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
      "worker": "executor-2"
    }
  ]
}
```

## Deliverables

1. **Comprehensive gap/bug analysis report**
2. **Prioritized sprint plan** with user approval
3. **All task documents** with acceptance criteria
4. **Completed implementations** (all tasks approved)
5. **Test results** showing compliance
6. **Sprint merged to main**
7. **Worktree cleanup completed**
8. **Sprint retrospective documentation**

## Quality Gates

- **Before Execution:** Sprint plan approved by user
- **Per-Task:** Code review passes before merging to sprint branch
- **Per-Task:** Tests pass locally before submission
- **Before Sprint Merge:** All tasks complete and approved
- **Before Merge:** Full test suite passes (100%)
- **Before Cleanup:** Sprint successfully merged to main

## User Interaction Points

1. **Sprint Planning:** Present plan, request approval
2. **Per-Task Review:** Approve/reject/needs-testing decisions
3. **Sprint Completion:** Confirm merge and cleanup

## Error Handling

- **Task Failure:** Automatic retry with different worker (max 3 attempts)
- **Persistent Failure:** Escalate to user for guidance
- **Build Failures:** Invoke `oh-my-claudecode:build-fixer` automatically
- **Test Failures:** Invoke `oh-my-claudecode:qa-tester` for diagnosis
- **Merge Conflicts:** Invoke `oh-my-claudecode:git-master` for resolution

## Cancellation

**User says:** "stop", "cancel", "abort"

**Graceful Shutdown:**
1. Stop spawning new tasks
2. Allow in-progress tasks to complete current work
3. Commit any completed work
4. Document current state
5. Provide resumption instructions

## Example Usage

```
User: "autopilot sprint focused on architectural gaps"

System:
1. Analyzing codebase for architectural gaps...
   - explore-high: Found 23 deviations
   - architect: Identified 7 critical violations
   - security-reviewer: Found 3 vulnerabilities

2. Prioritizing...
   - Top 12 items selected for sprint

3. Creating sprint plan...
   - Sprint SP-026: "Architectural Compliance Sprint"
   - Please review and approve:

   [Sprint plan presented]

User: "Approve"

4. Creating tasks...
   - Created 12 task documents

5. Starting ULTRAPILOT execution...
   - Spawned 5 parallel executors
   - Workers: executor-1, executor-2, executor-3, executor-4, executor-5

   [Real-time progress]
   ✓ Task SP-026-001 complete (executor-2)
   ✓ Task SP-026-003 complete (executor-5)
   ⏳ Task SP-026-002 in progress (executor-1)

   Review SP-026-001: [APPROVE] ✓ merged to sprint
   Review SP-026-003: [NEEDS TESTING] → qa-tester
   Review SP-026-003: [APPROVE] ✓ merged to sprint

   [... all tasks complete ...]

6. Sprint validation...
   ✓ All tests pass
   ✓ Architecture validated

7. Merging to main...
   ✓ Sprint merged

8. Cleanup...
   ✓ Worktree removed
   ✓ Sprint complete!
```

## Success Metrics

- **Velocity:** Tasks completed per day (target: 3-5 tasks/day with ultrapilot)
- **Quality:** First-approval rate (target: 80%+ approved on first review)
- **Coverage:** Test pass rate (target: 100%)
- **Efficiency:** Parallelization speedup (target: 3-5x faster than sequential)
