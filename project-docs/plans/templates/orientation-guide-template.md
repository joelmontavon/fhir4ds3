# [PEP-ID] Implementation Orientation Guide

**PEP**: [PEP-ID] - [PEP-NAME]
**Implementation Duration**: [START-DATE] to [END-DATE] ([DURATION])
**Your Role**: [ROLE-TITLE]
**Lead**: Senior Solution Architect/Engineer

---

## Welcome to [PEP-NAME] Implementation

[BRIEF-DESCRIPTION-OF-PEP-PURPOSE-AND-IMPACT]

You are implementing **[PEP-ID]: [PEP-NAME]** across [NUMBER-OF-SPRINTS] sprint(s).

---

## 1. Initial Review and Context

### Required Reading (in order)
1. **CLAUDE.md** - Development workflow and principles (READ FIRST)
2. **project-docs/peps/accepted/[pep-file].md** - The PEP you're implementing (CRITICAL)
3. **project-docs/plans/current-sprint/[sprint-plan].md** - Current sprint plan
4. **project-docs/plans/milestones/[milestone-file].md** - Overall milestone context
5. **project-docs/process/** - All process documentation
6. **project-docs/architecture/** - Architecture goals and overview

### Key Concepts to Understand
- **[KEY-CONCEPT-1]**: [Description]
- **[KEY-CONCEPT-2]**: [Description]
- **[KEY-CONCEPT-3]**: [Description]
- **[KEY-CONCEPT-4]**: [Description]

---

## 2. Your [PEP-NAME] Implementation Tasks

### Task Sequence (Must be completed in order)
1. **[TASK-ID-1]**: [Task Name] ([HOURS] hours)
2. **[TASK-ID-2]**: [Task Name] ([HOURS] hours)
3. **[TASK-ID-3]**: [Task Name] ([HOURS] hours)
4. **[TASK-ID-4]**: [Task Name] ([HOURS] hours) [Priority Level]
5. **[TASK-ID-5]**: [Task Name] ([HOURS] hours) [Priority Level]

### Task Locations
All detailed task specifications are in: `project-docs/plans/tasks/[TASK-PREFIX]-[XXX]-[task-name].md`

---

## 3. Development Workflow

### Branch Management
- Create a new branch for each task: `[TASK-PREFIX]-[XXX]-[task-name]`
- Example: `[EXAMPLE-BRANCH-NAME]`
- Follow git workflow in `project-docs/process/git-workflow.md`

### Progress Tracking Requirements
**For EVERY task, update these documents as you work:**

#### A. Task Document Updates
Location: `project-docs/plans/tasks/[TASK-PREFIX]-[XXX]-[task-name].md`
- Update "Progress Updates" table daily with status and blockers
- Mark checklist items as completed: `- [x] Item completed`
- Update "Status" section: Not Started → In Analysis → In Development → In Testing → In Review → Completed
- Document any issues, blockers, or deviations

#### B. Sprint Plan Updates
Location: `project-docs/plans/current-sprint/[sprint-plan-file].md`
- Update task status in "Task Breakdown" tables
- Note any timeline changes or blockers
- Update PEP implementation progress

#### C. Daily Progress Format
Add entries like this to task documents:
```
| [DATE] | [STATUS] | [PROGRESS-DESCRIPTION] | [BLOCKERS] | [NEXT-STEPS] |
```

---

## 4. Implementation Guidelines

### Code Quality Standards
- Follow all standards documented in `CLAUDE.md`
- **No hardcoded values** - use configuration
- **Multi-database support** - test against both DuckDB and PostgreSQL
- **Population-first design** - default to population-scale queries
- **Error handling** - comprehensive error handling for all scenarios

### Testing Requirements
- **Unit Tests**: 80%+ coverage for all implemented components
- **Integration Tests**: Multi-database consistency validation
- **Compliance Tests**: Official specification test integration
- **Performance**: Test execution within specified time limits

### Documentation Standards
- Inline comments for complex logic
- Function/method documentation
- Clear error messages
- Update all relevant documentation

---

## 5. [PEP-NAME] Implementation Success Criteria

### Primary Objectives (Must Complete)
- [ ] [PRIMARY-OBJECTIVE-1]
- [ ] [PRIMARY-OBJECTIVE-2]
- [ ] [PRIMARY-OBJECTIVE-3]
- [ ] [PRIMARY-OBJECTIVE-4]

### Quality Gates
- [ ] All code passes lint and format checks
- [ ] All tests pass in both database environments
- [ ] Code review completed and approved
- [ ] Documentation updated for all changes

### Compliance Targets
- **[SPECIFICATION-1]**: [CURRENT%] → [TARGET%] compliance
- **[SPECIFICATION-2]**: [CURRENT%] → [TARGET%] compliance
- **[COMPONENT]**: [CURRENT%] → [TARGET%] operational

---

## 6. Resources and References

### Official Test Suite Locations
- **[SPECIFICATION-1]**: [URL-OR-LOCATION]
- **[SPECIFICATION-2]**: [URL-OR-LOCATION]
- **[SPECIFICATION-3]**: [URL-OR-LOCATION]

### Development Environment
- **Python**: [VERSION] (project standard)
- **Databases**: [PRIMARY-DB] (primary) + [SECONDARY-DB] (validation)
- **Testing**: [TESTING-FRAMEWORK] with coverage reporting
- **Quality**: [QUALITY-TOOLS] for code quality

### [SPRINT-SPECIFIC-RESOURCES]
- **[RESOURCE-TYPE]**: [Description and location]
- **[RESOURCE-TYPE]**: [Description and location]

### Archived Implementation Reference
**⚠️ IMPORTANT**: The `archive/` folder contains previous implementations that provide valuable patterns and insights, but should NOT be copied wholesale due to known architectural issues.

**What to Reference:**
- **[RELEVANT-PATTERN-1]**: `archive/[PATH-TO-FILE]` - [Description of useful patterns]
- **[RELEVANT-PATTERN-2]**: `archive/[PATH-TO-FILE]` - [Description of useful patterns]
- **[RELEVANT-PATTERN-3]**: `archive/[PATH-TO-FILE]` - [Description of useful patterns]
- **[RELEVANT-PATTERN-4]**: `archive/[PATH-TO-FILE]` - [Description of useful patterns]

**What NOT to Do:**
- ❌ Copy code wholesale without understanding current architecture
- ❌ Reintroduce deprecated patterns or technical debt
- ❌ Ignore the reasons these implementations were archived
- ❌ Skip the unified architecture principles for quick wins

**How to Use Archived Code Effectively:**
1. **Understand First**: Read archived code to understand approaches and patterns
2. **Identify Patterns**: Extract useful design patterns, not specific implementations
3. **Adapt to Current Architecture**: Apply lessons within the [CURRENT-ARCHITECTURE-NAME] architecture
4. **Learn from Problems**: Research why these implementations were archived
5. **Test Thoroughly**: Ensure any adapted patterns work with current testing infrastructure

---

## 7. Communication and Support

### Daily Updates
- **Format**: Update task documentation daily
- **Content**: Progress, current focus, any blockers, next steps
- **Timing**: End of day updates

### Weekly Reviews
- **Schedule**: Every Friday at 2:00 PM
- **Participants**: Team member + Senior Solution Architect/Engineer
- **Agenda**: Progress review, technical discussions, planning adjustments

### Getting Help
- **Blockers**: Document in task progress immediately
- **Questions**: Update task with questions and continue where possible
- **Escalation**: If blocked >2 hours, notify Senior Solution Architect/Engineer

---

## 8. Completion Process

### For Each Task
1. **Validate**: Ensure all acceptance criteria met
2. **Test**: Run complete test suite and validation
3. **Document**: Update all progress tracking
4. **Review**: Self-review using task checklist
5. **Commit**: Single-line descriptive commit message
6. **Notify**: Request Senior Solution Architect/Engineer review

### Commit Message Format
- **Format**: "[type]([scope]): [brief description of accomplishment]"
- **Example**: "[EXAMPLE-COMMIT-MESSAGE]"
- **Guidelines**: Single line, describe what was accomplished, no names/agents/companies

### Final PEP Review
- All high-priority tasks completed
- Documentation updated and accurate
- PEP implementation retrospective participation
- Lessons learned documented

---

## 9. Success Tips

### Best Practices
- **Read documentation thoroughly** before starting each task
- **Follow established patterns** from existing codebase
- **Test early and often** - don't wait until the end
- **Document as you go** - don't leave documentation for later
- **Ask questions early** - better to clarify than assume

### Common Pitfalls to Avoid
- Skipping documentation updates
- Not testing multi-database compatibility
- Hardcoding values instead of using configuration
- Implementing without understanding the broader context
- Not following the exact task specifications

### [PEP-SPECIFIC-TIPS]
- [SPECIFIC-TIP-1]
- [SPECIFIC-TIP-2]
- [SPECIFIC-TIP-3]

---

## 10. [PEP-NAME] Impact

Your work implementing this PEP creates the foundation for:
- **[IMPACT-AREA-1]**: [Description of impact]
- **[IMPACT-AREA-2]**: [Description of impact]
- **[IMPACT-AREA-3]**: [Description of impact]
- **[IMPACT-AREA-4]**: [Description of impact]

[BROADER-CONTEXT-AND-IMPORTANCE]

---

**Ready to Begin**: Start with [FIRST-TASK-ID] after completing your document review
**Questions**: Document in task progress and continue where possible
**Success**: Measured by PEP implementation goals achievement and quality standards

---

*This orientation guide ensures you have everything needed to successfully implement [PEP-NAME] and advance FHIR4DS [PROJECT-AREA].*

---

## Template Usage Instructions

### How to Use This Template

1. **Copy this template** to create a new orientation guide
2. **Replace all bracketed placeholders** with PEP-specific information:
   - `[PEP-ID]` → e.g., "PEP-001"
   - `[PEP-NAME]` → e.g., "Testing Infrastructure and Specification Compliance Automation"
   - `[START-DATE]` → e.g., "27-09-2025"
   - `[END-DATE]` → e.g., "08-11-2025"
   - `[DURATION]` → e.g., "6 weeks"
   - `[NUMBER-OF-SPRINTS]` → e.g., "3"
   - And all other bracketed variables

3. **Customize sections** as needed for specific PEP requirements
4. **Review completeness** to ensure all PEP-specific information is included
5. **Save as**: `project-docs/plans/orientation/[pep-id]-implementation-guide.md`

### Required Customizations
- Update task lists with actual PEP implementation tasks
- Replace example URLs with real specification sources
- Customize success criteria for PEP goals
- Add PEP-specific tips and resources
- Update compliance targets and metrics
- Set appropriate role title and experience expectations
- **Customize Archived Implementation Section**: Replace placeholder patterns with actual archived files relevant to the PEP

### Optional Customizations
- Add PEP-specific architecture concepts
- Include additional resources or references
- Modify communication schedule if different
- Add specialized testing requirements
- Include PEP-specific risk areas
- **Expand Archived Code Guidance**: Add more specific archived implementations if particularly relevant to the PEP

This template provides a consistent structure while allowing flexibility for different PEP types, requirements, and team member experience levels.