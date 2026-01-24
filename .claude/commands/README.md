# FHIR4DS Claude Commands

Agent-based command system for FHIR4DS development workflow, aligned with oh-my-claudecode multi-agent orchestration and git worktree workflow.

## **Git Worktree Workflow**

### **Project Structure**
- Maintain a **primary directory** (e.g., `main/` or `oh-my-claude-code/`) for the long-lived branch
- Use **Git Worktrees** for active tasks in sibling directories
- Each sprint/task gets its own dedicated worktree directory

### **Worktree Commands**
```bash
# Create sprint worktree from main
git worktree add ../sprint-SP-XXX sprint/SP-XXX

# Create task worktree from sprint worktree (optional, for complex tasks)
git worktree add ../task-SP-XXX-YYY SP-XXX-YYY-[task-name]

# List all worktrees
git worktree list

# Remove worktree after merge
git worktree remove ../sprint-SP-XXX

# Prune stale worktree metadata
git worktree prune
```

### **Naming Conventions**
| Type | Worktree Path | Branch Name |
|------|---------------|-------------|
| Sprint | `../sprint-SP-XXX` | `sprint/SP-XXX` |
| Task | `../task-SP-XXX-YYY` | `SP-XXX-YYY-[task-name]` |
| Feature | `../feature-name` | `feature/descriptive-name` |

### **Conventional Commit Format**
```
type(scope): description (Task: SP-XXX-YYY)
```

**Types:** `feat`, `fix`, `docs`, `arch`, `compliance`, `dialect`, `test`, `refactor`

**Examples:**
- `feat(fhirpath): add choice type resolution (Task: SP-025-001)`
- `fix(dialect): correct PostgreSQL NULL handling (Task: SP-025-002)`
- `arch(cte): implement CTE template library (Task: SP-025-003)`

### **Cleanup Workflow**
1. Task completed → commits to sprint branch
2. Task reviewed → approved, no cleanup yet
3. All tasks completed → sprint validated
4. Sprint merged to main
5. **Then** remove worktrees:
   ```bash
   git worktree remove ../sprint-SP-XXX
   git worktree prune
   ```

---

## **Core Workflow Commands**

### **Planning and Sprint Creation**

#### **0. Autopilot Sprint** - `/autopilot-sprint` ⚡ FULLY AUTOMATED
- **Primary Mode**: `oh-my-claudecode:ultrapilot`
- **Primary Agents**: `planner`, `architect`, `executor`, `code-reviewer`, `qa-tester`

**Complete automated sprint workflow from gap analysis to completion:**

**8-Phase Automated Process:**
1. **Gap/Bug Analysis** (Parallel) - `architect`, `explore-high`, `security-reviewer` analyze codebase
2. **Prioritization** - `analyst` prioritizes findings by impact/urgency
3. **Sprint Planning** - `planner` creates sprint plan with user approval
4. **Task Creation** - Generate all task documents from plan
5. **Parallel Execution** (ULTRAPILOT) - Up to 5 `executor` workers complete tasks in parallel
6. **Review & Approve** - `code-reviewer` approves each task (reject/needs-testing options)
7. **Test & Validate** - `qa-tester` validates as needed
8. **Sprint Closeout** - Merge to main, worktree cleanup, documentation

**Git Workflow:** Full automation with worktree management, task branches, merge coordination

**User Interaction:** 3 checkpoints - plan approval, per-task review decisions, final merge confirmation

**Deliverables:** Complete sprint from analysis to merged completion.

---

#### **1. Create Sprint** - `/create-sprint`
- **Primary Agent**: `oh-my-claudecode:planner`
- **Supporting**: `architect`, `critic`, `analyst`, `explore`

Creates a new sprint with strategic vision and architectural direction (interactive, not automated).

**Process:**
1. **Provide Strategic Vision** - Define architectural direction aligned with long-term goals
2. **Make Architectural Decisions Collaboratively** - Always WITH user input and approval
3. **Identify and Prioritize Architectural Gaps** - Analyze codebase, categorize by impact, create roadmaps
4. **Create Sprint Plan Document** - `project-docs/plans/current-sprint/sprint-XXX-[name].md`
5. **Create Milestone Document** - `project-docs/plans/milestones/milestone-[id]-[name].md`
6. **Create Task Documents** - `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
7. **Create Orientation Guide** - `project-docs/plans/orientation/SP-XXX-orientation.md`

**Deliverables:** Complete sprint plan, milestone, all task documents, and orientation guide.

---

#### **2. Create PEP** - `/create-pep`
- **Primary Agent**: `oh-my-claudecode:planner`
- **Supporting**: `analyst`, `architect`, `critic`

Creates a new Project Enhancement Proposal following the established process.

**Deliverable:** Complete PEP draft in `project-docs/peps/drafts/`

---

#### **3. Approve PEP and Create Sprint Artifacts** - `/approve-pep`
- **Primary Agent**: `oh-my-claudecode:planner`
- **Supporting**: `architect`, `critic`, `writer`

Approves a PEP and creates all implementation artifacts (sprint plan, milestone, tasks, orientation).

---

### **Implementation and Review**

#### **4. Complete Task** - `/complete-task`
- **Primary Agent**: `oh-my-claudecode:executor`
- **Supporting**: `executor-low`, `executor-high`, `build-fixer`, `tdd-guide`

Implements and completes an assigned task following the full development workflow.

**Process:**
1. Create/use sprint worktree: `../sprint-SP-XXX`
2. Implement solution following architecture principles
3. Update task documentation
4. Commit to sprint branch

---

#### **5. Review Task and Merge** - `/review-task`
- **Primary Agent**: `oh-my-claudecode:code-reviewer`
- **Supporting**: `architect`, `qa-tester`, `security-reviewer`

Reviews completed work and manages merges.

**For Individual Tasks:**
- Reviews work against standards
- Approves commit to sprint branch
- Creates review documentation

**For Sprints:**
- Validates sprint completion
- Merges sprint to main
- Handles worktree cleanup

---

#### **6. Complete Sprint** - `/complete-sprint`
- **Primary Agent**: `oh-my-claudecode:architect`
- **Supporting**: `qa-tester`, `code-reviewer`, `security-reviewer`, `writer`

Conducts comprehensive sprint completion review and documentation updates.

---

## **Adhoc Utility Commands**

### **Quality Assurance**

#### **7. Run Full Test Suite** - `/run-full-test-suite`
- **Primary Agent**: `oh-my-claudecode:qa-tester`
- **Supporting**: `build-fixer`, `code-reviewer`, `architect`

Executes comprehensive testing across all FHIR4DS components.

---

#### **8. Code Quality Audit** - `/code-quality-audit`
- **Primary Agent**: `oh-my-claudecode:code-reviewer`
- **Supporting**: `architect`, `security-reviewer`, `qa-tester`

Conducts comprehensive code quality assessment across the FHIR4DS codebase.

---

#### **9. Architecture Deep Dive** - `/architecture-deep-dive`
- **Primary Agent**: `oh-my-claudecode:architect`
- **Supporting**: `explore`, `analyst`, `security-reviewer`

Conducts thorough architectural analysis of FHIR4DS implementation.

---

## **Command Usage Examples**

### **Complete Sprint Workflow with Worktrees**
```bash
# === Create sprint with strategic vision ===
/create-sprint

# === Approve PEP and create sprint artifacts ===
/approve-pep PEP-005

# === Implement tasks using worktrees ===
# From main directory, create sprint worktree
git worktree add ../sprint-SP-005 sprint/SP-005
cd ../sprint-SP-005

# Implement tasks
/complete-task SP-005-001
/complete-task SP-005-002

# === Review tasks ===
/review-task SP-005-001
/review-task SP-005-002

# === Complete sprint ===
/complete-sprint SP-005

# === Merge and cleanup ===
/review-task sprint SP-005  # Merges to main
cd ../[main-directory]
git worktree remove ../sprint-SP-005
git worktree prune
```

### **Quality Assurance**
```bash
# Run comprehensive tests
/run-full-test-suite

# Audit code quality
/code-quality-audit

# Deep architecture analysis
/architecture-deep-dive
```

---

## **Agent Reference Table**

| Domain | LOW (Haiku) | MEDIUM (Sonnet) | HIGH (Opus) |
|--------|-------------|-----------------|-------------|
| **Analysis** | `architect-low` | `architect-medium` | `architect` |
| **Execution** | `executor-low` | `executor` | `executor-high` |
| **Search** | `explore` | `explore-medium` | `explore-high` |
| **Research** | `researcher-low` | `researcher` | - |
| **Frontend** | `designer-low` | `designer` | `designer-high` |
| **Docs** | `writer` | - | - |
| **Visual** | - | `vision` | - |
| **Planning** | - | - | `planner` |
| **Critique** | - | - | `critic` |
| **Pre-Planning** | - | - | `analyst` |
| **Testing** | - | `qa-tester` | `qa-tester-high` |
| **Security** | `security-reviewer-low` | - | `security-reviewer` |
| **Build** | `build-fixer-low` | `build-fixer` | - |
| **TDD** | `tdd-guide-low` | `tdd-guide` | - |
| **Code Review** | `code-reviewer-low` | - | `code-reviewer` |

---

## **Command Summary**

| Command | Primary Agent/Mode | Purpose |
|---------|-------------------|---------|
| `/autopilot-sprint` ⚡ | `ultrapilot` mode | **FULLY AUTOMATED**: Gap analysis → prioritization → planning → parallel execution → review → completion |
| `/create-sprint` | `planner` | Create sprint with strategic vision and architectural direction |
| `/create-pep` | `planner` | Create new Project Enhancement Proposal |
| `/approve-pep` | `planner` | Approve PEP and create sprint artifacts |
| `/complete-task` | `executor` | Implement and complete assigned task |
| `/review-task` | `code-reviewer` | Review work and manage merges |
| `/complete-sprint` | `architect` | Complete sprint review and documentation |
| `/run-full-test-suite` | `qa-tester` | Execute comprehensive testing |
| `/code-quality-audit` | `code-reviewer` | Comprehensive code quality assessment |
| `/architecture-deep-dive` | `architect` | Detailed architectural analysis |

---

## **Architectural Compliance**

All commands enforce FHIR4DS core principles:
- ✅ **Unified FHIRPath Architecture** - Single execution foundation
- ✅ **Population-First Design** - Population-scale analytics focus
- ✅ **Thin Dialects** - No business logic in database dialects
- ✅ **CTE-First SQL** - Optimized query generation
- ✅ **100% Compliance** - Progress toward full specification compliance

---

## **Success Metrics Integration**

Commands automatically track and report:
- Specification compliance progress
- Architecture principle adherence
- Code quality metrics
- Performance benchmarks
- Team velocity and delivery

This agent-based command system provides complete workflow automation while maintaining FHIR4DS architectural integrity and quality standards, fully aligned with oh-my-claudecode's multi-agent orchestration capabilities and git worktree workflow.
