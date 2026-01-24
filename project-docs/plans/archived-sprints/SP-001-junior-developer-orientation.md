# SP-001 Junior Developer Orientation Guide

**Sprint**: 001 - Testing Infrastructure Foundation
**Duration**: 27-09-2025 to 11-10-2025 (2 weeks)
**Your Role**: Junior Developer
**Sprint Lead**: Senior Solution Architect/Engineer

---

## Welcome to Sprint 001

You are working on the foundational testing infrastructure for FHIR4DS - a critical sprint that enables 100% specification compliance validation. This sprint implements **PEP-001: Testing Infrastructure and Specification Compliance Automation**.

---

## 1. Initial Review and Context

### Required Reading (in order)
1. **CLAUDE.md** - Development workflow and principles (READ FIRST)
2. **project-docs/peps/accepted/pep-001-testing-infrastructure.md** - Approved PEP you're implementing
3. **project-docs/plans/current-sprint/sprint-001-testing-infrastructure.md** - Current sprint plan
4. **project-docs/plans/milestones/milestone-m001-testing-foundation.md** - Overall milestone context
5. **project-docs/process/** - All process documentation
6. **project-docs/architecture/** - Architecture goals and overview

### Key Concepts to Understand
- **FHIRPath-First Architecture**: Single execution foundation for healthcare standards
- **100% Specification Compliance Goal**: Target for FHIRPath, SQL-on-FHIR, and CQL
- **Multi-Database Support**: DuckDB (development) + PostgreSQL (production)
- **Population-Scale Analytics**: Default to population queries, not row-by-row processing

---

## 2. Your Sprint 001 Tasks

### Task Sequence (Must be completed in order)
1. **SP-001-001**: Create test directory structure and pytest configuration (8 hours)
2. **SP-001-002**: Implement unit test framework for FHIRPath parsing (16 hours)
3. **SP-001-003**: Download and integrate FHIRPath official test suite (12 hours)
4. **SP-001-005**: Implement SQL generator unit tests (12 hours) [Medium Priority]
5. **SP-001-006**: Create multi-database integration tests (10 hours) [Medium Priority]

### Task Locations
All detailed task specifications are in: `project-docs/plans/tasks/SP-001-[XXX]-[task-name].md`

---

## 3. Development Workflow

### Branch Management
- Create a new branch for each task: `SP-001-[XXX]-[task-name]`
- Example: `SP-001-001-test-structure-setup`
- Follow git workflow in `project-docs/process/git-workflow.md`

### Progress Tracking Requirements
**For EVERY task, update these documents as you work:**

#### A. Task Document Updates
Location: `project-docs/plans/tasks/SP-001-[XXX]-[task-name].md`
- Update "Progress Updates" table daily with status and blockers
- Mark checklist items as completed: `- [x] Item completed`
- Update "Status" section: Not Started → In Analysis → In Development → In Testing → In Review → Completed
- Document any issues, blockers, or deviations

#### B. Sprint Plan Updates
Location: `project-docs/plans/current-sprint/sprint-001-testing-infrastructure.md`
- Update task status in "Task Breakdown" tables
- Note any timeline changes or blockers
- Update sprint goals progress

#### C. Daily Progress Format
Add entries like this to task documents:
```
| 28-09-2025 | In Development | Created directory structure, working on conftest.py | None | Complete pytest configuration |
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

## 5. Sprint 001 Success Criteria

### Primary Objectives (Must Complete)
- [ ] Complete test directory structure operational
- [ ] Unit test framework with 80%+ coverage
- [ ] FHIRPath official test suite integrated and executing
- [ ] Multi-database testing validated (DuckDB + PostgreSQL)

### Quality Gates
- [ ] All code passes lint and format checks
- [ ] All tests pass in both database environments
- [ ] Code review completed and approved
- [ ] Documentation updated for all changes

### Compliance Targets
- **FHIRPath R4**: 0% → 25% compliance
- **Test Framework**: 100% operational for future development

---

## 6. Resources and References

### Official Test Suite Locations
- **FHIRPath**: https://raw.githubusercontent.com/FHIR/fhir-test-cases/refs/heads/master/r4/fhirpath/tests-fhir-r4.xml
- **SQL-on-FHIR**: https://github.com/FHIR/sql-on-fhir-v2/tree/master/tests
- **CQL**: https://github.com/cqframework/cql-tests/tree/main/tests/cql

### Development Environment
- **Python**: 3.11 (project standard)
- **Databases**: DuckDB (primary) + PostgreSQL (validation)
- **Testing**: pytest framework with coverage reporting
- **Quality**: black, flake8, mypy for code quality

---

## 7. Communication and Support

### Daily Updates
- **Format**: Update task documentation daily
- **Content**: Progress, current focus, any blockers, next steps
- **Timing**: End of day updates

### Weekly Reviews
- **Schedule**: Every Friday at 2:00 PM
- **Participants**: You + Senior Solution Architect/Engineer
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
- **Format**: "Implement [brief description of accomplishment]"
- **Example**: "Implement test directory structure and pytest configuration"
- **Guidelines**: Single line, describe what was accomplished, no names/agents/companies

### Final Sprint Review
- All high-priority tasks completed
- Documentation updated and accurate
- Sprint retrospective participation
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

---

## 10. Sprint 001 Impact

Your work in this sprint creates the foundation for:
- **Continuous Specification Compliance**: Automated validation against official test suites
- **Quality Assurance**: Preventing regressions in healthcare analytics functionality
- **Multi-Database Architecture**: Ensuring consistent behavior across platforms
- **Future Development**: Enabling confident implementation of advanced features

This testing infrastructure is critical for FHIR4DS achieving its goal of 100% specification compliance and becoming a trusted platform for healthcare analytics.

---

**Ready to Begin**: Start with SP-001-001 after completing your document review
**Questions**: Document in task progress and continue where possible
**Success**: Measured by sprint goals achievement and quality standards

---

*This orientation guide ensures you have everything needed to successfully contribute to Sprint 001 and the FHIR4DS testing foundation.*