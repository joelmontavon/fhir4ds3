# Git Workflow

**Document Version**: 2.0
**Date**: 2026-01-22
**Status**: Development Process

---

## Overview

This document defines the Git workflow and version control practices for FHIR4DS development. The workflow is designed to support **sprint-based parallel development** while maintaining code quality and architectural consistency.

## Branching Strategy

### Main Branch

#### `main` Branch
- **Purpose**: Production-ready code
- **Protection**: No direct commits allowed
- **Merge Source**: Sprint branches merge to main after sprint completion
- **Quality Gates**: All tests must pass, compliance maintained
- **Release Source**: All releases are tagged from main branch

### Sprint Branches (Primary Development Pattern)

#### Naming Convention
```
sprint/SP-XXX
```

#### Examples
```
sprint/SP-025
sprint/SP-026
```

#### Lifecycle
1. **Create** at sprint start from main
2. **Develop** - Multiple tasks commit to the same sprint branch
3. **Test** sprint integration regularly (all tasks together)
4. **Sprint End Review** - Comprehensive review before merge
5. **Merge** to main after architect approval
6. **Delete** sprint branch after successful merge

#### Task Commits Within Sprint Branch
- Each task completion results in a commit to the sprint branch
- Commits follow conventional commit format with task ID: `type(task): description`
- Sequential or parallel tasks all commit to same branch
- Task order matters: dependent tasks must complete in sequence

**Example Sprint Timeline:**
```
Day 1:  git checkout -b sprint/SP-025
        [Architect creates sprint plan and tasks]

Day 2:  [Task SP-025-001 completed]
        git commit -m "feat(fhirpath): implement ofType function (SP-025-001)"

Day 3:  [Task SP-025-002 completed]
        git commit -m "fix(dialects): correct JSON extraction (SP-025-002)"

Day 5:  [Task SP-025-003 completed]
        git commit -m "arch(engine): add CTE infrastructure (SP-025-003)"

Day 10: [All sprint tasks complete]
        [Architect conducts sprint completion review]
        git checkout main
        git merge sprint/SP-025
        git branch -d sprint/SP-025
```

### Feature Branches (For Large PEPs or Independent Work)

#### Naming Convention
```
feature/PEP-XXX-brief-description
feature/issue-XXX-brief-description
```

#### When to Use
- Very large PEPs that span multiple sprints
- Experimental features that shouldn't block sprint completion
- Independent work outside sprint scope

#### Lifecycle
1. **Create** from main
2. **Develop** with regular commits
3. **Test** thoroughly in both database environments
4. **Merge** back to main (or merge to sprint branch if part of sprint)
5. **Delete** feature branch after successful merge

### Bug Fix / Hotfix Branches

#### Naming Convention
```
hotfix/urgent-description
fix/SP-XXX-YYY-brief-description
```

#### Lifecycle
- Can merge directly to main for urgent production fixes
- Or merge into current sprint branch if sprint is active
- Follow same review process as sprint work

---

## Commit Standards

### Conventional Commits Format with Task Context

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification with task identification:

```
<type>[optional scope]: <description> (Task: SP-XXX-YYY)

[optional body]

[optional footer(s)]
```

### Commit Types

#### Primary Types
- **feat**: New feature or enhancement
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic changes)
- **refactor**: Code refactoring without adding features or fixing bugs
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Maintenance tasks, dependency updates

#### FHIR4DS-Specific Types
- **compliance**: Changes to improve specification compliance
- **dialect**: Database dialect-specific changes
- **arch**: Architectural changes or improvements

### Commit Message Examples

#### Sprint-Based Task Commits
```
feat(fhirpath): implement ofType function for type filtering (Task: SP-025-001)

- Adds ofType() function to FHIRPath engine
- Filters collections based on type system
- Supports both simple and complex type checks

Ref: Task SP-025-001, PEP-003
```

```
fix(dialects): correct JSON path extraction for nested arrays (Task: SP-025-002)

Previous implementation failed for deeply nested JSON structures.
Updated both DuckDB and PostgreSQL dialects.

Fixes issue where nested path extraction returned null.
```

```
compliance(sql-on-fhir): achieve 100% ViewDefinition test suite compliance (Task: SP-025-010)

All 47 ViewDefinition tests now passing.
No regressions in other specification areas.

Compliance improvement: 87.3% → 92.1%
```

### Atomic Commits

Each commit should represent **one logical change** (one task completion):

#### Good Atomic Commits
- Complete one task from sprint plan
- Fix one specific bug
- Update documentation for one feature
- Refactor one component

#### Bad Non-Atomic Commits
- Mix multiple task completions in one commit
- Update multiple unrelated components
- Combine code changes with documentation updates
- Include formatting changes with logic changes

---

## Sprint Workflow

### Sprint Start

1. **Architect** creates sprint plan and tasks
2. **Create sprint branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b sprint/SP-XXX
   ```

### During Sprint

**Sequential Task Execution:**
1. Coder implements task on sprint branch
2. Code tester runs comprehensive tests
3. Code reviewer reviews architecture and code quality
4. If approved: commit to sprint branch
5. If needs revision: coder fixes, re-test, re-review
6. Move to next task

**Parallel Task Execution (coordinated by orchestrator):**
1. Multiple coders work on different tasks (same sprint branch)
2. Each task goes through coder → code tester → code reviewer
3. Approved tasks commit to sprint branch as they complete
4. Orchestrator resolves any merge conflicts
5. Sprint branch accumulates all completed task commits

**Commit Pattern:**
```bash
# After task completion and review approval
git add .
git commit -m "type(scope): description (Task: SP-XXX-YYY)"
```

### Sprint Integration Testing

**Regular Integration Checks** (recommended after each task or daily):
```bash
# Run full test suite on sprint branch
python -m pytest tests/
python tests/run_compliance.py

# Verify both databases
python tests/run_tests.py --dialect duckdb
python tests/run_tests.py --dialect postgresql
```

### Sprint End

1. **All tasks complete** - All sprint tasks committed to sprint branch
2. **Sprint completion review** - Architect conducts documentation review
3. **Sprint validation** - Code reviewer validates sprint quality on sprint branch
4. **Orchestrator merge**:
   - Orchestrator validates all tasks complete
   - Orchestrator runs final test validation
   - Orchestrator merges sprint branch to main
   - Orchestrator cleans up sprint branch
5. **Architect final review** - Architect conducts strategic sprint completion review

---

## Pull Request Process

### Sprint-Level Reviews

For sprint-based development, code review happens **per task** during the sprint, but there is also a **sprint-level review** before merge.

### Per-Task Review (During Sprint)

**Conducted by:** code reviewer agent

**Process:**
1. Task completes on sprint branch
2. Code reviewer reviews the diff for that task
3. Approval → task can be committed
4. Revision needed → coder fixes and resubmits

**No formal PR required** for individual tasks within sprint. Review happens via direct commit to sprint branch.

### Sprint-End Review (Before Merge)

**Conducted by:** orchestrator (with validation from architect and code reviewer)

**Process:**
1. All sprint tasks complete
2. Architect provides sprint documentation
3. Code reviewer validates sprint quality and test results
4. Orchestrator reviews all validation outputs
5. Approval → orchestrator merges sprint to main
6. Revision needed → address issues and re-review

### Sprint Merge Checklist

Before merging sprint branch to main:

**Code Quality:**
- [ ] All tasks properly committed with conventional commit messages
- [ ] No merge conflicts or conflicts resolved
- [ ] No temporary/debug code remains
- [ ] All dead code and unused imports removed

**Testing:**
- [ ] Full test suite passes (100% pass rate)
- [ ] Both DuckDB and PostgreSQL tested
- [ ] Official specification tests pass
- [ ] No regressions from previous sprint

**Architecture:**
- [ ] No thin dialect violations
- [ ] Population-first design maintained
- [ ] CTE-first SQL generation preserved
- [ ] No hardcoded values introduced

**Documentation:**
- [ ] All task statuses updated to "completed"
- [ ] Sprint summary documentation created
- [ ] Architectural decisions documented
- [ ] Milestone progress updated

---

## Merge Strategies

### Sprint Branch Merges

**Squash and Merge (Preferred for Sprint Merges)**
- **Use Case**: Merging entire sprint branch to main
- **Benefit**: Clean main branch history with atomic sprint delivery
- **Process**: All task commits become one merge commit on main

**Example:**
```bash
git checkout main
git merge --squash --no-edit sprint/SP-025
# Creates single merge commit with aggregated message
```

**Or Fast-Forward Merge (If Linear)**
- **Use Case**: When main has no new commits since sprint branch created
- **Benefit**: Preserves complete history
- **Process**: Simple fast-forward merge

---

## Release Management

### Version Numbering
Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes or major architectural updates
- **MINOR**: New features, specification compliance improvements
- **PATCH**: Bug fixes, performance improvements

### Release Process

#### Pre-Release Checklist
1. **Compliance Validation**
   - [ ] All official test suites passing
   - [ ] Compliance metrics meet or exceed targets
   - [ ] No critical test failures

2. **Quality Assurance**
   - [ ] All tests passing in both database environments
   - [ ] Performance benchmarks met
   - [ ] Security scan completed
   - [ ] Documentation complete and current

3. **Release Preparation**
   - [ ] CHANGELOG updated with all changes
   - [ ] Version numbers updated in all relevant files
   - [ ] Migration scripts prepared (if needed)
   - [ ] Release notes drafted

#### Release Workflow
1. **Tag Release**: Create annotated tag on main branch
2. **GitHub Release**: Create GitHub release from tag
3. **Deploy**: Follow deployment procedures
4. **Announce**: Communicate release to stakeholders

---

## Collaboration Guidelines

### Multi-Agent Sprint Collaboration

**Sprint Branch Coordination:**

When multiple agents work on the same sprint branch:

1. **Task Order Awareness**: Check git status before starting work
2. **Pull Before Starting**: `git pull origin sprint/SP-XXX`
3. **Sequential Commits**: Don't push while another agent is pushing
4. **Merge Conflicts**: Resolve conflicts and re-test

**Example Parallel Workflow:**
```
[Orchestrator launches 3 tracks in parallel]

Track 1 (coder A): Task SP-025-001
├── Implement on sprint/SP-025
├── Code tester validates
├── Code reviewer approves
└── git commit -m "feat(...): task 001 complete"

Track 2 (coder B): Task SP-025-002 (depends on 001)
├── Wait for task 001 commit
├── git pull
├── Implement on sprint/SP-025
├── Code tester validates
├── Code reviewer approves
└── git commit -m "fix(...): task 002 complete"

Track 3 (coder C): Task SP-025-003 (independent)
├── Implement in parallel (on separate files ideally)
├── Code tester validates
├── Code reviewer approves
├── git pull (merge task 001 if needed)
└── git commit -m "arch(...): task 003 complete"
```

### Communication Protocol

**Task Completion States:**
1. **"Task implemented, testing started"** - Coder done, code tester running
2. **"Task tested, review in progress"** - Code tester done, code reviewer reviewing
3. **"Task reviewed, commit pending"** - Code reviewer approved, ready to commit
4. **"Task committed to sprint/SP-XXX"** - Changes committed to sprint branch

**Sprint Completion:**
- **"Sprint tasks all complete"** - All tasks committed, ready for sprint review
- **"Sprint review in progress"** - Architect conducting review
- **"Sprint approved, merge pending"** - Ready to merge to main
- **"Sprint merged to main"** - Sprint complete, branch deleted

---

## Git Configuration

### Required Git Configuration
```bash
# User identification
git config user.name "Your Full Name"
git config user.email "your.email@domain.com"

# Default branch
git config init.defaultBranch main

# Push settings
git config push.default simple
git config push.followTags true

# Merge settings
git config merge.ff only
```

---

## Troubleshooting

### Common Issues

#### "Multiple agents committing to same branch"
```bash
# Pull before starting work
git pull origin sprint/SP-XXX

# If conflicts occur
git pull --rebase origin sprint/SP-XXX
# Resolve conflicts
# Continue rebase
```

#### "Sprint branch has merge conflicts with main"
```bash
git checkout sprint/SP-XXX
git fetch origin main
git rebase origin/main
# Resolve conflicts
# Complete rebase
git checkout main
git merge sprint/SP-XXX
```

#### "One task in sprint broke the build"
```bash
# Identify the problematic commit
git log --oneline sprint/SP-XXX

# Revert that specific commit
git revert <commit-hash>

# Or if before merge to main:
git reset --hard HEAD~1
# Fix the issue
# Re-commit
```

---

## Best Practices Summary

### Do's ✅
- **Create sprint branches** at sprint start, delete after merge
- **Commit tasks atomically** with task ID in commit message
- **Pull before starting** work on sprint branch
- **Test sprint integration** regularly throughout sprint
- **Review each task** before committing to sprint branch
- **Conventional commits** with task context

### Don'ts ❌
- **Never commit directly** to main branch
- **Don't skip task review** even within sprint
- **Don't let broken builds persist** in sprint branch
- **Don't mix unrelated changes** in single commits
- **Don't force push** sprint branch if main has moved ahead
- **Don't merge incomplete sprint** to main

---

## Conclusion

This sprint-based Git workflow supports parallel development while maintaining code quality and architectural consistency. By committing completed tasks to sprint branches and merging at sprint completion, teams can work collaboratively with proper quality gates and architectural oversight.

The workflow balances development velocity with systematic quality assurance, ensuring FHIR4DS progresses systematically toward 100% specification compliance.

---

*This workflow supports the PEP-inspired sprint development process while maintaining the architectural principles and quality standards essential to FHIR4DS success.*
