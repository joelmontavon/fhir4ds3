# Create Sprint

**Primary Agent**: oh-my-claudecode:planner
**Supporting Agents**: oh-my-claudecode:architect, oh-my-claudecode:critic, oh-my-claudecode:analyst, oh-my-claudecode:explore
**Situation**: Creating a new sprint with strategic vision and architectural direction

Create a new sprint following a comprehensive architectural planning process:

---

## 1. Provide Strategic Vision

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

---

## 2. Make Architectural Decisions Collaboratively

**ALWAYS WITH user input and approval:**

**Decision Process:**
1. **Present Options:** Use `AskUserQuestion` tool for architectural choices
2. **Explain Trade-offs:** Clear comparison of approaches with pros/cons
3. **Request Approval:** Never proceed without explicit user confirmation
4. **Document Decisions:** Record all approved architectural decisions

**Common Decision Points:**
- Database feature implementation strategy
- Performance optimization approaches
- Testing infrastructure investments
- Technical debt prioritization
- Specification compliance sequencing

**Example Decision Flow:**
```
1. Analyze codebase to identify architectural options
2. Present options with trade-off analysis
3. Ask user: "Which approach aligns best with your priorities?"
4. Await user selection
5. Validate selection against architectural principles
6. Document decision in sprint plan
```

---

## 3. Identify and Prioritize Architectural Gaps

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

**Gap Analysis Template:**
```markdown
## Architectural Gaps - Sprint SP-XXX

### Critical (P0)
- [ ] Gap description
  - Impact: [description]
  - Solution approach: [description]
  - Estimated effort: [X days]

### High (P1)
- [ ] Gap description
  - Impact: [description]
  - Solution approach: [description]
  - Estimated effort: [X days]
```

---

## 4. Create Sprint Plan

**Generate Complete Sprint Artifacts:**

**A. Sprint Plan Document:**
- File: `project-docs/plans/current-sprint/sprint-XXX-[name].md`
- Use template: `project-docs/plans/templates/sprint-plan-template.md`
- Include:
  - Strategic vision and objectives
  - Architectural decisions (with user approvals)
  - Gap analysis and prioritization
  - Success metrics and acceptance criteria

**B. Milestone Document:**
- File: `project-docs/plans/milestones/milestone-[id]-[name].md`
- Use template: `project-docs/plans/templates/milestone-template.md`
- Break sprint into phases with clear deliverables

**C. Task Documents:**
- Location: `project-docs/plans/tasks/`
- Naming: `SP-XXX-YYY-[task-name].md`
- Use template: `project-docs/plans/templates/task-template.md`
- Each task includes:
  - Clear acceptance criteria
  - Architectural requirements
  - Dependencies and estimates
  - Verification approach

**D. Orientation Guide:**
- File: `project-docs/plans/orientation/SP-XXX-orientation.md`
- Use template: `project-docs/plans/templates/orientation-guide-template.md`
- Includes all tasks, architectural context, and success criteria

---

## 5. Collaborative Review and Approval

**Before Sprint Activation:**
1. **Review with User:**
   - Present complete sprint plan
   - Walk through architectural decisions
   - Explain gap analysis and priorities
   - Confirm task breakdown and estimates

2. **Architecture Validation:**
   - Use `oh-my-claudecode:architect` to validate plan
   - Ensure adherence to all architectural principles
   - Verify no violations of thin dialect requirements
   - Confirm population-first design approach

3. **Critique and Refine:**
   - Use `oh-my-claudecode:critic` to review plan
   - Identify potential risks and oversights
   - Suggest improvements and mitigations
   - Ensure plan is realistic and achievable

4. **Final Approval:**
   - Request explicit user approval
   - Document any modifications requested
   - Confirm sprint is ready to activate

---

## 6. Sprint Activation

**Once Approved:**
1. Create sprint branch: `git checkout -b sprint/SP-XXX`
2. Create sprint worktree: `git worktree add ../sprint-SP-XXX sprint/SP-XXX`
3. Notify team that sprint is ready for implementation
4. Update current sprint summary with activation details

---

## Deliverables

- Complete sprint plan document with strategic vision
- Milestone document with phased deliverables
- All task documents with clear acceptance criteria
- Orientation guide for implementers
- Architectural decision log with user approvals
- Gap analysis with prioritized roadmap
- User approval confirmation

---

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Strategic planning | `oh-my-claudecode:planner` | opus |
| Pre-planning analysis | `oh-my-claudecode:analyst` | opus |
| Architecture validation | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Deep codebase exploration | `oh-my-claudecode:explore-high` | opus |
| Thorough codebase search | `oh-my-claudecode:explore-medium` | sonnet |
| Quick lookups | `oh-my-claudecode:explore` | haiku |
| Plan critique | `oh-my-claudecode:critic` | opus |
| Documentation creation | `oh-my-claudecode:writer` | haiku |
| Git operations | `oh-my-claudecode:git-master` skill | - |

---

## Quality Gates

- Sprint vision aligns with 100% specification compliance goals
- All architectural decisions have explicit user approval
- Gap analysis is comprehensive and prioritized
- Task breakdown is realistic and achievable
- All documents follow FHIR4DS templates and standards
- Architecture validation passes with no critical violations
