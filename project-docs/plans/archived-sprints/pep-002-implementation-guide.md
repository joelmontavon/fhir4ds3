# PEP-002 Implementation Orientation Guide

**PEP**: PEP-002 - FHIRPath Core Implementation - Unified Foundation Engine
**Implementation Duration**: 28-09-2025 to 03-12-2025 (10 weeks)
**Your Role**: Junior Developer
**Lead**: Senior Solution Architect/Engineer

---

## Welcome to FHIRPath Core Implementation

This PEP establishes the complete FHIRPath core engine as the unified foundation for all healthcare expression languages in FHIR4DS. The implementation includes a comprehensive FHIRPath parser, evaluator, and CTE-first SQL generation system that enables population-scale healthcare analytics while achieving 60%+ FHIRPath specification compliance.

You are implementing **PEP-002: FHIRPath Core Implementation** across 3 sprint(s).

---

## 1. Initial Review and Context

### Required Reading (in order)
1. **CLAUDE.md** - Development workflow and principles (READ FIRST)
2. **project-docs/peps/active/pep-002-fhirpath-core-implementation.md** - The PEP you're implementing (CRITICAL)
3. **project-docs/plans/current-sprint/sprint-003-fhirpath-core-implementation.md** - Current sprint plan
4. **project-docs/plans/milestones/milestone-m003-fhirpath-foundation-engine.md** - Overall milestone context
5. **project-docs/process/** - All process documentation
6. **project-docs/architecture/** - Architecture goals and overview

### Key Concepts to Understand
- **Unified FHIRPath Architecture**: Single execution foundation for all healthcare expression languages (FHIRPath, SQL-on-FHIR, CQL)
- **Population-First Design**: CTE-first SQL generation optimized for population-scale analytics (1M+ patients)
- **Metadata-Rich AST**: Enhanced Abstract Syntax Tree with type hints, optimization flags, and database context for CTE generation
- **Thin Dialect Architecture**: Business logic in FHIRPath engine, only syntax differences in database dialects

---

## 2. Your FHIRPath Core Implementation Tasks

### Task Sequence (Must be completed in order)
1. **SP-003-001**: FHIRPath Parser Integration (fhirpath-py Fork) (20 hours)
2. **SP-003-002**: Enhanced AST Integration and Validation (12 hours)
3. **SP-003-003**: Core FHIRPath Evaluator Engine (24 hours) ✅ COMPLETED
4. **SP-003-011**: FHIRPath Evaluator Test Fixes and Stabilization (8 hours) [Critical]
5. **SP-003-004**: Database Dialect Abstraction (16 hours) [Critical]
6. **SP-003-005**: Testing Infrastructure Integration (14 hours) [High]

### Task Locations
All detailed task specifications are in: `project-docs/plans/tasks/SP-003-[XXX]-[task-name].md`

---

## 3. Development Workflow

### Branch Management
- Create a new branch for each task: `feature/SP-003-[XXX]-[task-name]`
- Example: `feature/SP-003-011-evaluator-test-fixes`
- Follow git workflow in `project-docs/process/git-workflow.md`

### Progress Tracking Requirements
**For EVERY task, update these documents as you work:**

#### A. Task Document Updates
Location: `project-docs/plans/tasks/SP-003-[XXX]-[task-name].md`
- Update "Progress Updates" table daily with status and blockers
- Mark checklist items as completed: `- [x] Item completed`
- Update "Status" section: Not Started → In Analysis → In Development → In Testing → In Review → Completed
- Document any issues, blockers, or deviations

#### B. Sprint Plan Updates
Location: `project-docs/plans/current-sprint/sprint-003-fhirpath-core-implementation.md`
- Update task status in "Task Breakdown" tables
- Note any timeline changes or blockers
- Update PEP implementation progress

#### C. Daily Progress Format
Add entries like this to task documents:
```
| 2025-09-28 | In Development | Implementing evaluator test fixes | None | Complete operator type detection fix |
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
- **Unit Tests**: 90%+ coverage for all implemented components
- **Integration Tests**: Multi-database consistency validation
- **Compliance Tests**: Official FHIRPath specification test integration
- **Performance**: Test execution within specified time limits (<100ms for typical expressions)

### Documentation Standards
- Inline comments for complex logic
- Function/method documentation
- Clear error messages
- Update all relevant documentation

---

## 5. FHIRPath Core Implementation Success Criteria

### Primary Objectives (Must Complete)
- [ ] Enhanced FHIRPath parser with metadata-rich AST parses 95% of common healthcare expressions
- [ ] Core evaluator leverages AST metadata for optimized path navigation and collection operations
- [ ] Database dialect abstraction provides consistent behavior across DuckDB and PostgreSQL
- [ ] Testing infrastructure integration demonstrates 30%+ FHIRPath compliance improvement

### Quality Gates
- [ ] All code passes lint and format checks
- [ ] All tests pass in both database environments
- [ ] Code review completed and approved
- [ ] Documentation updated for all changes

### Compliance Targets
- **FHIRPath R4**: 0.9% → 60%+ compliance
- **Official Test Suite**: 30%+ improvement in pass rate
- **Population Analytics**: Successfully process 1M+ patient datasets

---

## 6. Resources and References

### Official Test Suite Locations
- **FHIRPath R4 Tests**: https://github.com/HL7/FHIRPath/tree/master/tests
- **Compliance Integration**: `tests/compliance/fhirpath/`
- **Performance Benchmarks**: Population-scale testing with large healthcare datasets

### Development Environment
- **Python**: 3.10+ (project standard)
- **Databases**: DuckDB (primary) + PostgreSQL (validation)
- **Testing**: pytest with coverage reporting
- **Quality**: ruff, black for code quality

### FHIRPath-Specific Resources
- **fhirpath-py Fork**: Base parser implementation to extend
- **ANTLR4 Grammar**: Proven FHIRPath grammar foundation
- **FHIR Type System**: Integration with FHIR R4 type definitions
- **CTE Templates**: SQL generation patterns for population analytics

### Archived Implementation Reference
**⚠️ IMPORTANT**: The `archive/` folder contains previous implementations that provide valuable patterns and insights, but should NOT be copied wholesale due to known architectural issues.

**What to Reference:**
- **Evaluation Patterns**: `archive/fhir4ds/fhirpath/fhirpath.py` - Interface design and evaluation flows
- **Parser Architecture**: `archive/fhir4ds/fhirpath/parser/parser.py` - AST node structures and parsing patterns
- **Context Management**: `archive/fhir4ds/cql/core/engine.py` - Expression context and variable scoping
- **CTE Optimization**: `archive/fhir4ds/cte_pipeline/core/cte_pipeline_engine.py` - Monolithic query strategies
- **Testing Approaches**: `archive/tests/official/fhirpath/fhirpath_r4_test_runner.py` - Compliance test integration

**What NOT to Do:**
- ❌ Copy code wholesale without understanding current architecture
- ❌ Reintroduce deprecated patterns or technical debt
- ❌ Ignore the reasons these implementations were archived
- ❌ Skip the unified architecture principles for quick wins

**How to Use Archived Code Effectively:**
1. **Understand First**: Read archived code to understand approaches and patterns
2. **Identify Patterns**: Extract useful design patterns, not specific implementations
3. **Adapt to Current Architecture**: Apply lessons within the unified FHIRPath architecture
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
- **Example**: "feat(fhirpath): implement evaluator test fixes with operator type detection and type validation"
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

### FHIRPath-Specific Tips
- **Parser Extension Strategy**: Fork fhirpath-py rather than building from scratch - focus on FHIR4DS-specific metadata enhancements
- **AST Metadata Priority**: Type hints and optimization flags are critical for CTE generation - ensure comprehensive metadata population
- **Population-Scale Thinking**: Design collection operations for 1M+ patient datasets from the start, not single-patient scenarios
- **Specification Compliance Focus**: Prioritize FHIRPath R4 compliance over custom optimizations - use official test suite extensively

---

## 10. FHIRPath Core Implementation Impact

Your work implementing this PEP creates the foundation for:
- **Healthcare Analytics at Scale**: Population-scale healthcare analytics with CTE-optimized SQL for 1M+ patient datasets
- **Standards Compliance**: Path to 100% FHIRPath, SQL-on-FHIR, and CQL specification compliance
- **Enterprise Accessibility**: Pure Python implementation eliminates Java dependencies for healthcare organizations
- **Unified Architecture**: Single execution foundation for all healthcare expression languages in FHIR4DS

This implementation establishes the critical foundation component that enables specification-compliant expression evaluation with population-scale optimization capabilities, advancing FHIR4DS toward its goal of becoming the definitive healthcare analytics platform.

---

**Ready to Begin**: Start with SP-003-011 after completing your document review
**Questions**: Document in task progress and continue where possible
**Success**: Measured by PEP implementation goals achievement and quality standards

---

*This orientation guide ensures you have everything needed to successfully implement FHIRPath Core Implementation and advance FHIR4DS healthcare expression evaluation capabilities.*