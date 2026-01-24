# Create PEP

**Primary Agent**: oh-my-claudecode:planner
**Supporting Agents**: oh-my-claudecode:analyst, oh-my-claudecode:architect, oh-my-claudecode:critic
**Situation**: Creating a new Project Enhancement Proposal

Create a new PEP following the established process:

**Analysis Phase:**
1. Review current project state in project-docs/ to understand context
2. Analyze architectural needs and strategic priorities
3. Consider team capacity, dependencies, and technical risks
4. Evaluate alignment with unified FHIRPath architecture goals

**PEP Creation:**
1. Use template: `project-docs/peps/templates/pep-template.md`
2. Create new PEP file: `project-docs/peps/drafts/pep-draft-XXX-brief-description.md`
3. Include all required sections: Abstract, Motivation, Detailed Design, Implementation Plan, Testing Strategy, Success Metrics
4. Address: scope boundaries, prerequisites, implementation risks, and clear success criteria

**Documentation Requirements:**
- Follow PEP numbering guidelines in `project-docs/peps/README.md`
- Ensure alignment with architectural principles in `project-docs/architecture/`
- Reference relevant specifications in `project-docs/architecture/reference/specifications.md`
- Consider compliance targets: 100% FHIRPath, SQL-on-FHIR, CQL, Quality Measures

**Deliverable:**
Complete PEP draft ready for review and discussion, properly placed in drafts folder with all sections completed according to template requirements.

---

**Agent Delegation:**
| Task | Agent | Model |
|------|-------|-------|
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Pre-planning analysis | `oh-my-claudecode:analyst` | opus |
| Architecture review | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Codebase exploration | `oh-my-claudecode:explore` | haiku |
| Thorough codebase search | `oh-my-claudecode:explore-medium` | sonnet |
| Deep architectural search | `oh-my-claudecode:explore-high` | opus |
| Plan review/critique | `oh-my-claudecode:critic` | opus |
| Documentation creation | `oh-my-claudecode:writer` | haiku |
