---
name: code-quality-audit
description: Comprehensive code quality assessment across FHIR4DS codebase
triggers:
  - code quality audit
  - quality audit
  - audit code
  - code review
  - check code quality
argument-hint: ""
---

# Code Quality Audit Skill

**Primary Agent**: `oh-my-claudecode:code-reviewer`
**Supporting Agents**: `oh-my-claudecode:architect`, `oh-my-claudecode:security-reviewer`, `oh-my-claudecode:qa-tester`

## Purpose

Conduct thorough code quality audit across the FHIR4DS codebase, assessing architecture compliance, technical debt, and best practices.

## When to Activate

When user says:
- "run a code quality audit"
- "audit the code"
- "check code quality"
- "code review"

## Workflow

### Architecture Compliance Review

1. **Unified FHIRPath Architecture:**
   - Verify single execution foundation implementation
   - Confirm all specifications route through FHIRPath engine
   - Validate translation layer effectiveness

2. **Thin Dialect Implementation:**
   - **Critical Check**: Ensure dialects contain ONLY syntax differences
   - Verify no business logic in database dialect classes
   - Confirm clean method overriding for SQL function names

3. **Population-First Design:**
   - Confirm population-scale query generation
   - Validate CTE-first SQL generation approach
   - Check for row-by-row anti-patterns

### Code Standards Compliance

1. **Coding Standards Adherence:**
   - Review against `project-docs/process/coding-standards.md`
   - Check function and class design patterns
   - Validate naming conventions and documentation

2. **Test Coverage Analysis:**
   - Measure current test coverage (target: 90%+)
   - Identify untested or under-tested components
   - Assess test quality and effectiveness

3. **Documentation Quality:**
   - Verify API documentation completeness
   - Check inline code documentation
   - Validate architectural decision documentation

### Technical Debt Assessment

1. **Code Complexity:**
   - Identify functions with high cyclomatic complexity
   - Assess maintainability metrics
   - Locate areas needing refactoring

2. **Configuration Management:**
   - Check for hardcoded values throughout codebase
   - Verify external configuration implementation
   - Validate environment-specific settings

3. **Error Handling:**
   - Review exception handling patterns
   - Assess logging implementation quality
   - Validate error recovery mechanisms

### Performance and Optimization

1. **Query Optimization:**
   - Review SQL generation efficiency
   - Assess CTE template effectiveness
   - Identify performance bottlenecks

2. **Memory Management:**
   - Check for memory leaks or inefficient patterns
   - Validate resource cleanup implementation
   - Assess large dataset handling

### Security and Best Practices

1. **Security Implementation:**
   - Review input validation patterns
   - Check for SQL injection prevention
   - Validate access control implementation

2. **Dependency Management:**
   - Review external dependency usage
   - Check for outdated or vulnerable packages
   - Validate dependency injection patterns

### Specification Alignment

1. **FHIRPath Implementation:**
   - Verify specification compliance progress
   - Identify gaps requiring attention
   - Assess parser and evaluation accuracy

2. **SQL-on-FHIR Compatibility:**
   - Validate ViewDefinition processing
   - Check for regression risks
   - Ensure continued 100% compliance

3. **CQL Translation Quality:**
   - Review translation layer implementation
   - Assess accuracy and completeness
   - Identify areas for compliance improvement

### Reporting and Recommendations

1. **Priority Issues:**
   - Critical architectural violations
   - Security concerns requiring immediate attention
   - Performance bottlenecks affecting user experience

2. **Technical Debt Items:**
   - Refactoring opportunities
   - Documentation gaps
   - Test coverage improvements

3. **Optimization Opportunities:**
   - Performance enhancement possibilities
   - Code simplification areas
   - Architecture refinement suggestions

## Deliverable

Comprehensive quality report with prioritized action items, focusing on maintaining FHIR4DS architectural integrity while advancing toward 100% specification compliance.

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Comprehensive code review | `oh-my-claudecode:code-reviewer` | opus |
| Quick code checks | `oh-my-claudecode:code-reviewer-low` | haiku |
| Architecture verification | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Quick security scan | `oh-my-claudecode:security-reviewer-low` | haiku |
| Test validation | `oh-my-claudecode:qa-tester` | sonnet |
| Comprehensive QA | `oh-my-claudecode:qa-tester-high` | opus |
