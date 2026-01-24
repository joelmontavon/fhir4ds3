---
name: create-sprint
description: Create sprint with strategic vision, collaborative architectural decisions, and gap analysis
triggers:
  - create sprint
  - new sprint
  - plan sprint
  - sprint planning
argument-hint: "[sprint-name]"
---

# Create Sprint Skill

**Primary Agent**: `oh-my-claudecode:planner`
**Supporting Agents**: `oh-my-claudecode:architect`, `oh-my-claudecode:critic`, `oh-my-claudecode:analyst`, `oh-my-claudecode:explore`

## Purpose

Create a new sprint with comprehensive strategic vision, collaborative architectural decision-making, and architectural gap analysis.

## When to Activate

When user says:
- "create a sprint"
- "plan a new sprint"
- "start sprint planning"
- "setup sprint SP-XXX"

## Workflow

### 1. Provide Strategic Vision

**Define Architectural Direction:**
- Analyze long-term project goals and 100% specification compliance targets
- Align sprint objectives with unified FHIRPath architecture principles
- Ensure population-first design patterns guide all implementation work
- Consider technical debt reduction and architectural evolution

**Vision Components:**
1. **North Star Metrics:**
   - Specification compliance progress (FHIRPath, SQL-on-FHIR, CQL)
   - Population-scale performance targets
   - Test coverage and quality standards

2. **Architectural Principles:**
   - Single execution foundation for all specifications
   - Thin dialects (no business logic in database layers)
   - CTE-first SQL generation approach
   - Population-analytics optimization

3. **Strategic Outcomes:**
   - What capabilities will this sprint unlock?
   - How does this advance the platform vision?
   - What technical debt will be addressed?

### 2. Make Architectural Decisions Collaboratively

**ALWAYS WITH user input and approval:**

**Decision Process:**
1. **Present Options:** Use `AskUserQuestion` tool for architectural choices
2. **Explain Trade-offs:** Clear comparison of approaches with pros/cons
3. **Request Approval:** Never proceed without explicit user confirmation
4. **Document Decisions:** Record all approved architectural decisions

### 3. Identify and Prioritize Architectural Gaps

**Analyze the Codebase:**
1. **Comprehensive Gap Analysis:**
   - Use `oh-my-claudecode:explore-high` for deep codebase investigation
   - Identify deviations from architectural principles
   - Locate performance bottlenecks and scaling limitations
   - Find areas lacking specification compliance

2. **Categorize Gaps by Impact:**
   | Category | Description | Priority |
   |----------|-------------|----------|
   | **Critical** | Violates core architectural principles | P0 |
   | **High** | Blocks specification compliance progress | P1 |
   | **Medium** | Technical debt accumulation | P2 |
   | **Low** | Code quality improvements | P3 |

3. **Create Strategic Roadmap:**
   - Map gaps to sprint capabilities
   - Sequence work for maximum impact
   - Identify dependencies and prerequisites
   - Estimate effort and risk

### 4. Create Sprint Plan

**Generate Complete Sprint Artifacts:**

**A. Sprint Plan Document:**
- File: `project-docs/plans/current-sprint/sprint-XXX-[name].md`
- Use template: `project-docs/plans/templates/sprint-plan-template.md`

**B. Milestone Document:**
- File: `project-docs/plans/milestones/milestone-[id]-[name].md`
- Use template: `project-docs/plans/templates/milestone-template.md`

**C. Task Documents:**
- Location: `project-docs/plans/tasks/`
- Naming: `SP-XXX-YYY-[task-name].md`
- Use template: `project-docs/plans/templates/task-template.md`

**D. Orientation Guide:**
- File: `project-docs/plans/orientation/SP-XXX-orientation.md`
- Use template: `project-docs/plans/templates/orientation-guide-template.md`

### 5. Collaborative Review and Approval

**Before Sprint Activation:**
1. **Review with User:** Present complete sprint plan
2. **Architecture Validation:** Use `oh-my-claudecode:architect` to validate
3. **Critique and Refine:** Use `oh-my-claudecode:critic` to review
4. **Final Approval:** Request explicit user approval

### 6. Sprint Activation

**Once Approved:**
1. Create sprint branch: `git checkout -b sprint/SP-XXX`
2. Create sprint worktree: `git worktree add ../sprint-SP-XXX sprint/SP-XXX`
3. Notify team that sprint is ready for implementation

## Deliverables

- Complete sprint plan document with strategic vision
- Milestone document with phased deliverables
- All task documents with clear acceptance criteria
- Orientation guide for implementers
- Architectural decision log with user approvals
- Gap analysis with prioritized roadmap
- User approval confirmation

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Pre-planning analysis | `oh-my-claudecode:analyst` | opus |
| Architecture validation | `oh-my-claudecode:architect` | opus |
| Deep codebase exploration | `oh-my-claudecode:explore-high` | opus |
| Plan critique | `oh-my-claudecode:critic` | opus |
| Documentation creation | `oh-my-claudecode:writer` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |

## Quality Gates

- Sprint vision aligns with 100% specification compliance goals
- All architectural decisions have explicit user approval
- Gap analysis is comprehensive and prioritized
- Task breakdown is realistic and achievable
- All documents follow FHIR4DS templates and standards
- Architecture validation passes with no critical violations
