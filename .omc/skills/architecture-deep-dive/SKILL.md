---
name: architecture-deep-dive
description: Comprehensive architectural analysis and validation of FHIR4DS implementation
triggers:
  - architecture deep dive
  - architecture analysis
  - analyze architecture
  - architectural review
  - deep dive
argument-hint: ""
---

# Architecture Deep Dive Skill

**Primary Agent**: `oh-my-claudecode:architect`
**Supporting Agents**: `oh-my-claudecode:explore`, `oh-my-claudecode:analyst`, `oh-my-claudecode:security-reviewer`

## Purpose

Conduct thorough architectural analysis of FHIR4DS implementation, assessing compliance with core principles and identifying strategic improvement opportunities.

## When to Activate

When user says:
- "do an architecture deep dive"
- "analyze the architecture"
- "architectural review"
- "deep dive into architecture"

## Workflow

### Unified FHIRPath Architecture Analysis

1. **Foundation Verification:**
   - Analyze current FHIRPath engine implementation
   - Verify single execution path for all healthcare specifications
   - Assess translation layer effectiveness (SQL-on-FHIR → FHIRPath, CQL → FHIRPath)
   - Review forked parser integration and enterprise accessibility

2. **Execution Flow Analysis:**
   - Trace complete execution path from input to SQL generation
   - Verify CTE-first design implementation
   - Analyze dependency resolution for complex expressions
   - Review monolithic query generation approach

### Population-Scale Analytics Assessment

1. **Design Pattern Validation:**
   - Confirm population-first query generation
   - Verify elimination of row-by-row processing anti-patterns
   - Assess CTE template library effectiveness
   - Review database optimization integration

2. **Performance Architecture:**
   - Analyze query plan optimization strategies
   - Review memory efficiency for large datasets
   - Assess concurrent execution capabilities
   - Validate population-scale benchmarking results

### Database Dialect Architecture

1. **Thin Dialect Compliance:**
   - **Critical Assessment**: Verify dialects contain ONLY syntax differences
   - Confirm complete elimination of business logic from dialects
   - Review method overriding patterns for SQL functions
   - Validate clean separation between syntax and logic

2. **Multi-Database Support:**
   - Analyze feature parity between DuckDB and PostgreSQL
   - Review performance characteristics comparison
   - Assess extensibility for additional database platforms
   - Validate identical result generation across dialects

### Specification Integration Architecture

1. **FHIRPath Foundation:**
   - Review parser implementation and AST handling
   - Analyze function library completeness
   - Assess choice type resolution mechanisms
   - Evaluate compliance progress tracking

2. **SQL-on-FHIR Integration:**
   - Review ViewDefinition processing pipeline
   - Analyze translation accuracy and performance
   - Verify maintained 100% compliance
   - Assess regression prevention mechanisms

3. **CQL Translation Layer:**
   - Analyze CQL → FHIRPath translation effectiveness
   - Review dependency resolution for complex libraries
   - Assess monolithic execution implementation
   - Evaluate compliance improvement trajectory

### Quality and Compliance Architecture

1. **Testing Infrastructure:**
   - Review official test suite integration
   - Analyze compliance tracking mechanisms
   - Assess regression detection capabilities
   - Evaluate multi-database testing strategies

2. **Quality Gates:**
   - Review architectural principle enforcement
   - Analyze code quality metrics integration
   - Assess performance monitoring implementation
   - Evaluate specification compliance automation

### Scalability and Extensibility

1. **System Scalability:**
   - Analyze population-scale performance characteristics
   - Review memory usage patterns and optimization
   - Assess concurrent user support capabilities
   - Evaluate large dataset handling efficiency

2. **Architecture Extensibility:**
   - Review plugin architecture for new specifications
   - Analyze framework extension points
   - Assess configuration management flexibility
   - Evaluate future specification integration readiness

### Risk Assessment

1. **Architectural Risks:**
   - Identify potential violations of core principles
   - Assess technical debt accumulation patterns
   - Review performance regression risks
   - Evaluate specification compliance risks

2. **Mitigation Strategies:**
   - Recommend architectural safeguards
   - Suggest monitoring and alerting improvements
   - Propose quality gate enhancements
   - Identify training and documentation needs

### Future Architecture Vision

1. **Evolution Path:**
   - Assess alignment with 100% compliance goals
   - Review roadmap for new specification support
   - Analyze enterprise feature requirements
   - Evaluate community and ecosystem integration

2. **Strategic Recommendations:**
   - Propose architectural improvements
   - Suggest performance optimization opportunities
   - Recommend specification integration enhancements
   - Identify research and development priorities

## Deliverable

Comprehensive architectural analysis report with strategic recommendations for maintaining and evolving FHIR4DS toward industry-leading healthcare interoperability platform status.

## Agent Delegation

| Task | Agent | Model |
|------|-------|-------|
| Deep architectural analysis | `oh-my-claudecode:architect` | opus |
| Medium-complexity architecture | `oh-my-claudecode:architect-medium` | sonnet |
| Quick architecture lookups | `oh-my-claudecode:architect-low` | haiku |
| Deep codebase exploration | `oh-my-claudecode:explore-high` | opus |
| Thorough codebase search | `oh-my-claudecode:explore-medium` | sonnet |
| Quick file/pattern search | `oh-my-claudecode:explore` | haiku |
| Pre-planning analysis | `oh-my-claudecode:analyst` | opus |
| Security review | `oh-my-claudecode:security-reviewer` | opus |
| Quick security scan | `oh-my-claudecode:security-reviewer-low` | haiku |
