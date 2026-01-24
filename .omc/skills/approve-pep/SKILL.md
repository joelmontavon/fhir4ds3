---
name: approve-pep
description: Approve PEP and create sprint artifacts (plan, milestone, tasks, orientation)
triggers:
  - approve pep
  - approve proposal
  - accept pep
argument-hint: "[PEP-NUMBER]"
---

# Approve PEP Skill

**Primary Agent**: `oh-my-claudecode:planner`
**Supporting Agents**: `oh-my-claudecode:architect`, `oh-my-claudecode:critic`, `oh-my-claudecode:writer`

## Purpose

Approve a Project Enhancement Proposal (PEP) and create all implementation artifacts including sprint plan, milestone, tasks, and orientation guide.

## When to Activate

When user says:
- "approve PEP-005"
- "accept this proposal"
- "create sprint plan from PEP"

## Workflow

### PEP Management
1. Assign next sequential PEP number (check `project-docs/peps/README.md`)
2. Move PEP from `project-docs/peps/drafts/` to `project-docs/peps/accepted/`
3. Update PEP status and approval date

### Sprint Planning

**Use templates in `project-docs/plans/templates/`:**

1. **Sprint Plan**: `project-docs/plans/current-sprint/sprint-XXX-[pep-name].md`
   - Use `sprint-plan-template.md`
   - Include timeline, team assignments, dependencies
   - Define sprint goals and success criteria

2. **Milestone**: `project-docs/plans/milestones/milestone-[milestone-id]-[pep-name].md`
   - Use `milestone-template.md`
   - Break PEP into logical implementation phases
   - Include quality gates and deliverables

3. **Individual Tasks**: `project-docs/plans/tasks/SP-XXX-YYY-[task-name].md`
   - Use `task-template.md` for each task
   - Include clear acceptance criteria, dependencies, estimates
   - Ensure tasks are properly scoped for implementation

### Developer Orientation
1. **Create PEP Orientation Guide**: Use `orientation-guide-template.md`
   - Save as `project-docs/plans/orientation/[pep-id]-orientation-guide.md`
   - Include all tasks, sprint timeline, and PEP objectives
2. Update `project-docs/plans/orientation/` materials
3. Create PEP-specific developer guidance if needed
4. Update architecture documentation if PEP introduces new patterns

### Cross-References
1. Update current sprint summary to reference new PEP
2. Link tasks to milestone and sprint documentation
3. Ensure all documentation follows FHIR4DS standards

### Quality Assurance
- Verify all tasks advance toward 100% specification compliance
- Ensure adherence to unified FHIRPath architecture principles
- Confirm population-first design and thin dialect requirements

## Deliverable

Fully configured sprint with all artifacts: sprint plan, milestone, tasks, and orientation guide.

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Architecture review | `oh-my-claudecode:architect` | opus |
| Plan review/critique | `oh-my-claudecode:critic` | opus |
| Documentation creation | `oh-my-claudecode:writer` | haiku |
| Codebase exploration | `oh-my-claudecode:explore` | haiku |
