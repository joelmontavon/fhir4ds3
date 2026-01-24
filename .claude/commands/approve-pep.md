# Approve PEP and Create Sprint Artifacts

**Primary Agent**: oh-my-claudecode:planner
**Supporting Agents**: oh-my-claudecode:architect, oh-my-claudecode:critic, oh-my-claudecode:writer
**Situation**: Approving a PEP and creating complete implementation plan
**Usage**: Include PEP number (e.g., "approve PEP-005")

Approve the specified PEP and execute the complete PEP approval workflow:

**PEP Management:**
1. Assign next sequential PEP number (check `project-docs/peps/README.md` for numbering)
2. Move PEP from `project-docs/peps/drafts/` to `project-docs/peps/accepted/`
3. Update PEP status and approval date in the document

**Sprint Planning (use templates in project-docs/plans/templates/):**
1. **Sprint Plan**: Create `project-docs/plans/current-sprint/sprint-XXX-[pep-name].md`
   - Use `sprint-plan-template.md`
   - Include timeline, team assignments, dependencies
   - Define sprint goals and success criteria

2. **Milestone**: Create `project-docs/plans/milestones/milestone-[milestone-id]-[pep-name].md`
   - Use `milestone-template.md`
   - Break PEP into logical implementation phases
   - Include quality gates and deliverables

3. **Individual Tasks**: Create task files in `project-docs/plans/tasks/`
   - Use `task-template.md` for each task
   - Name format: `SP-XXX-YYY-[task-name].md`
   - Include clear acceptance criteria, dependencies, estimates
   - Ensure tasks are properly scoped for implementation

**Developer Orientation:**
1. **Create PEP Orientation Guide**: Use `orientation-guide-template.md` to create comprehensive orientation
   - Copy template from `project-docs/plans/templates/orientation-guide-template.md`
   - Replace all bracketed placeholders with PEP-specific information
   - Save as `project-docs/plans/orientation/[pep-id]-orientation-guide.md`
   - Include all tasks, sprint timeline, and PEP objectives
2. Update `project-docs/plans/orientation/` materials for new PEP context
3. Create PEP-specific developer guidance if needed
4. Update architecture documentation if PEP introduces new patterns

**Cross-References:**
1. Update current sprint summary to reference new PEP
2. Link tasks to milestone and sprint documentation
3. Ensure all documentation follows FHIR4DS standards

**Quality Assurance:**
- Verify all tasks advance toward 100% specification compliance
- Ensure adherence to unified FHIRPath architecture principles
- Confirm population-first design and thin dialect requirements

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Architecture review | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Plan review/critique | `oh-my-claudecode:critic` | opus |
| Codebase exploration | `oh-my-claudecode:explore` | haiku |
| Thorough codebase search | `oh-my-claudecode:explore-medium` | sonnet |
| Deep architectural search | `oh-my-claudecode:explore-high` | opus |
| Documentation creation | `oh-my-claudecode:writer` | haiku |
