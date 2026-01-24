# Development Workflow Guide

## Overview
This document outlines the development workflow and principles for maintaining code quality, documentation, and systematic progress tracking throughout the project lifecycle.

## Core Principles

### 1. Simplicity is Paramount
Your primary goal is to make the simplest possible change. Every modification should be small, targeted, and impact as little code as possible.

### 2. Document As You Go
Maintain clear documentation of your work throughout the process. This ensures anyone can understand the context and pick up where you left off. **For significant changes, create PEPs in project-docs/peps/. For routine work, update relevant project documentation.**

### 3. Keep the Workspace Tidy
  - Remove all dead code and unused imports
  - Delete temporary files (e.g., `work/backup_*.py`, debug scripts)
  - Clean up any exploratory or test files not needed for production
  - Remove commented-out code blocks unless they serve documentation purposes
  - Ensure no hardcoded values or development artifacts remain

### 4. Never Change Tests Without Approval
If you suspect a test is incorrect or flawed, raise your concerns with me first. Do not modify any tests without explicit approval.

### 5. Address Root Causes
Always fix the root cause of any issues; never apply surface-level fixes or band-aid solutions.

### 6. Understand Context Before Starting
Before beginning any work:
- Thoroughly review the **CLAUDE.md** file
- Review any current architecture and/or plan documents related to the project
- Conduct a high-level review of the entire codebase
- Perform a thorough review of code that is relevant or likely to be relevant to the upcoming work
- Understand dependencies and potential impact areas

### 7. Always Test Your Work
Execute all code including:
- Examples in documentation
- All cells from demo notebooks
- Unit tests, integration tests, and end-to-end tests
- Manual testing of critical paths

Ensure code runs without errors and produces expected results. Even handled errors should be evaluated for appropriateness.

## Standard Workflow

### 1. Version Control and Worktree Workflow
* **Project Structure**: Maintain a primary directory (e.g., `main/`) for the long-lived branch and use **Git Worktrees** for active tasks in sibling directories.
* **Branching**: Create a dedicated branch for every new chunk of functionality or project using `git worktree add ../<directory-name> <branch-name>`.
* **Naming Conventions**:
  * Use descriptive branch/directory names (e.g., `feature/cql-enhanced-parsing`, `fix/literal-type-support`).
* **Commits**:
  * Commit frequently with short, descriptive single-line messages.
  * Follow **Conventional Commit** format: `type(scope): brief description`.
  * Use architecture-specific types: `feat`, `fix`, `docs`, `arch`, `compliance`, `dialect`.
* **Cleanup**: Once a task is merged, remove the worktree directory and prune with `git worktree prune`.
* **Anonymity**: Avoid mentioning specific people or agents in commit messages.

---

## Directory Structure

To keep your workspace clean by organizing your project folder like this:

```text
fhir4ds/
├── main/       (The "primary" repo/worktree, usually on 'main' or 'develop')
├── feat/   (Worktree for a specific feature)
└── fix/  (Worktree for a bug fix)

```

### 2. Plan First
Before writing any code, thoroughly analyze the problem, review the codebase for relevant files, and determine if a Project Enhancement Proposal (PEP) is required. For significant changes (>40 hours effort, architectural modifications, breaking changes), create a PEP in **project-docs/peps/** following the established process. This plan must include:

#### Required Plan Components
- **Metadata:**
  - Date the plan was created
  - Date last updated
  - Estimated effort/complexity
- **Architecture Alignment:**
  - Description of how proposed changes align with or extend the overall architecture
  - Impact assessment on existing components
- **Implementation Details:**
  - Detailed breakdown of implementation steps
  - Dependencies and prerequisites
  - Risk assessment and mitigation strategies
- **Testing Strategy:**
  - Explicit testing strategy for planned changes
  - What tests will be run or created
  - Acceptance criteria
- **Deliverables:**
  - Clear checklist of TODO items
  - Definition of done

### 3. Get Plan Approval
**MANDATORY:** Pause and wait for plan review and approval before proceeding with implementation.

### 3a. PEP Process for Significant Changes
**When to Create a PEP**: Changes requiring >40 hours effort, architectural modifications, or breaking changes require a Project Enhancement Proposal following the process in `project-docs/peps/README.md`.

**PEP Workflow**:
- Create PEP draft using template in `project-docs/peps/templates/`
- Submit for Senior Solution Architect/Engineer review
- Wait for approval before proceeding with implementation
- Document outcomes in implementation summary upon completion

### 4. Execute the Plan (Stepwise Approach)

#### Implementation Guidelines
- Work through approved TODO items one by one using a stepwise approach
- Break down work into smaller, manageable tasks (ideally < 2 hours each)
- Focus on one function or piece of functionality at a time
- Provide high-level summaries of changes as you complete each task
- Update PEP progress or relevant project documentation regularly

### 5. Test and Finalize (Thorough Verification)

#### Testing Requirements
After implementing each step or completing related changes:

**Database Testing (Both Environments Required):**
- **DuckDB:** Test all functionality in DuckDB environment
- **PostgreSQL:** Test all functionality in PostgreSQL environment using connection string: `postgresql://postgres:postgres@localhost:5432/postgres`

**Test Categories:**
- **Official Tests:** Execute the main test suite
- **Compliance Tests:** Execute relevant official specification test suites
- **Unit Tests:** Test individual components in isolation
- **Integration Tests:** Test component interactions
- **End-to-End (E2E) Tests:** Test complete user workflows
- **Architecture Validation:** Ensure changes align with unified FHIRPath architecture
- **Dialect Compatibility:** Validate identical behavior across database dialects
- **New Tests:** Create tests for new functionality to prevent regressions

#### Issue Resolution Protocol
1. Do not proceed to the next task until all issues are fully resolved
2. Ensure 100% of the test suite in the **tests/** directory is passing
3. **Backup Management:**
   - If all tests pass: Delete the backup file from **work/**
   - If any tests fail: Revert changes using backup and analyze root cause

### 6. Post-Completion Code Review
After completing all tasks, perform a final comprehensive review:

#### Review Checklist
- [ ] Code passes "sniff test" (no suspicious or poorly implemented sections)
- [ ] No "band-aid" fixes that don't address root causes
- [ ] Code complexity is appropriate for functionality requirements
- [ ] No dead code or unused imports
- [ ] Alignment with unified FHIRPath architecture principles
- [ ] Database dialects contain ONLY syntax differences (no business logic)
- [ ] Consistent coding style and patterns
- [ ] Adequate error handling and logging
- [ ] Performance considerations addressed

### PEP Review Requirements
For changes requiring PEPs:
- [ ] PEP follows established template structure
- [ ] Architectural alignment with unified FHIRPath principles
- [ ] Clear success metrics and acceptance criteria
- [ ] Comprehensive testing strategy included
- [ ] Senior Solution Architect/Engineer approval obtained

Report findings before final handoff.

### 7. Summarize Your Work
Once all tasks are complete, update relevant documentation:
- For PEPs: Create implementation summary in **project-docs/peps/implemented/**
- For routine changes: Update relevant project documentation
- Summary of all changes made
- Key decisions and rationale
- Any architectural changes or implications
- Known limitations or future considerations
- Relevant notes for final review before preparing for commit

### 8. Prepare for Commit
- Stage changes in Git with short, descriptive single-line commit messages
- Ensure no temporary or backup files are staged
- Verify all tests pass one final time
- **Note:** Actual commit will be performed manually

## Post-Compacting Workflow

**IMPORTANT:** Before starting any work after compacting, you must re-familiarize yourself with the current project state and any changes that occurred during compacting.

## Unified FHIRPath Architecture Alignment

All development must align with FHIR4DS's unified FHIRPath architecture:

### Architecture Principles
- **FHIRPath-First**: Single execution foundation for all healthcare expression languages
- **CTE-First Design**: Every operation maps to CTE templates for population-scale performance
- **Thin Dialects**: Database differences handled through syntax translation only - NO business logic
- **Population Analytics**: Default to population queries with patient filtering when needed

### Implementation Requirements
- All business logic belongs in FHIRPath engine and CTE generator
- Database dialects contain ONLY syntax differences
- New features must support both DuckDB and PostgreSQL
- Changes must maintain or improve specification compliance

## Core Architectural Principles

### 1. Population Analytics First
**Principle:** Design for population-scale analytics rather than processing one patient's data at a time.

**Implementation:**
- CQL execution operates on entire patient populations by default
- Individual patient queries are achieved through population filtering, not separate execution paths
- Database queries are optimized for batch processing and population-level insights
- Patient-level results are derived from population queries, maintaining performance benefits

**Benefits:**
- 10x+ performance improvements through population-scale optimization
- Natural fit for quality measures and population health analytics
- Efficient resource utilization across large datasets
- Scalable architecture for healthcare analytics at scale

### 2. CQL Translates to SQL
**Principle:** Clinical Quality Language (CQL) expressions are translated into optimized SQL queries.

**Implementation:**
- CQL parser converts CQL syntax into intermediate representations
- SQL generator produces database-specific SQL from CQL expressions
- Translation maintains CQL semantics while leveraging database optimization
- Direct SQL execution eliminates interpretation overhead

**Benefits:**
- Leverages database engine optimization capabilities
- Enables complex queries with high performance
- Maintains CQL expressiveness while achieving SQL efficiency
- Provides clear execution model for debugging and optimization

### 3. Multi-Dialect Database Support
**Principle:** Support multiple database dialects with DuckDB and PostgreSQL as primary targets.

**Implementation:**
- Dialect-aware SQL generation with database-specific optimizations
- Common abstract interface with dialect-specific implementations
- Feature parity across supported databases where possible
- Graceful handling of dialect-specific limitations

**Dialect Implementation Strategy:**
- **CRITICAL REQUIREMENT:** Database dialects MUST contain only syntax differences. Any business logic in dialects violates the unified architecture and will be rejected in code review.
- **Function Overriding Approach:** Database-specific syntax implemented through method overriding in dialect classes
- **No Regex Post-Processing:** Dialect differences handled at SQL generation time, not through post-processing with regular expressions
- **Clean Separation:** Database-specific syntax belongs in overriding functions within dialect implementations
- **Type Safety:** Compile-time detection of dialect-specific differences rather than runtime string manipulation

**Dialect Architecture:**
```python
# Base dialect interface
class SQLDialect:
    def generate_json_extract(self, json_col: str, path: str) -> str:
        raise NotImplementedError
    
    def generate_date_diff(self, start_date: str, end_date: str, unit: str) -> str:
        raise NotImplementedError

# Database-specific implementations
class DuckDBDialect(SQLDialect):
    def generate_json_extract(self, json_col: str, path: str) -> str:
        return f"json_extract_string({json_col}, '{path}')"

class PostgreSQLDialect(SQLDialect):
    def generate_json_extract(self, json_col: str, path: str) -> str:
        return f"jsonb_extract_path_text({json_col}, '{path}')"
```

**Supported Dialects:**
- **DuckDB:** Primary target for embedded analytics and development
- **PostgreSQL:** Production target for enterprise deployments
- **Extensible:** Architecture supports additional dialects through inheritance

**Benefits:**
- Flexibility in deployment environments
- Optimal performance on each database platform
- Risk mitigation through multi-database support
- Future-proofing for new database technologies
- Clean, maintainable dialect-specific code
- Compile-time validation of database compatibility

### 4. CQL as FHIRPath Superset
**Principle:** CQL implementation builds on FHIRPath implementation, treating CQL as a superset of FHIRPath.

**Implementation:**
- FHIRPath engine handles path expressions and basic operations
- CQL layer adds clinical logic, temporal operations, and library management
- Shared expression evaluation between FHIRPath and CQL components
- Incremental enhancement from FHIRPath to full CQL support

**Architecture Layers:**
```
CQL Layer (Clinical Logic, Libraries, Parameters)
    ↓
FHIRPath Layer (Path Navigation, Expression Evaluation)
    ↓
FHIR Data Layer (Resource Access, Type System)
```

**Benefits:**
- Leverages proven FHIRPath foundation
- Consistent expression semantics across layers
- Efficient code reuse and maintenance
- Natural progression from basic path queries to complex clinical logic

### 5. SQL Leverages CTEs for Efficiency
**Principle:** Use Common Table Expressions (CTEs) whenever possible for query organization and improved efficiency.

**Implementation:**
- CQL defines are converted to named CTEs in SQL output
- Dependency resolution ensures proper CTE ordering
- Monolithic queries combine multiple CTEs for optimal database execution
- CTE structure improves query readability and database optimization opportunities

**CTE Strategy:**
- **Single Query Approach:** N CQL defines → 1 monolithic CTE query
- **Dependency Management:** Automatic topological sorting of CTE dependencies
- **Performance Optimization:** Database engines optimize CTE execution plans
- **Debugging Support:** Named CTEs improve SQL query comprehension

**Benefits:**
- 10x+ performance improvements through reduced database round trips
- Better database query optimization through CTE structure
- Improved code organization and maintainability
- Enhanced debugging and performance monitoring capabilities

### 6. Monolithic Query Architecture for Measures
**Principle:** Quality measures are implemented as monolithic queries for optimal performance.

**Implementation:**
- Complete CQL library execution in single database query
- All define statements combined into comprehensive CTE structure
- Population-level results returned in single result set
- Individual query fallback eliminated in favor of monolithic approach

**Monolithic Query Benefits:**
- **Performance:** 11.8x average improvement validated across measures
- **Efficiency:** 11.0x reduction in database queries and connections
- **Scalability:** Single query scales better than N individual queries
- **Optimization:** Database engines can optimize entire execution plan

### 7. Standards Compliance Goals
**Principle:** Achieve 100% compliance with FHIRPath, SQL on FHIR, and CQL specifications.

**Compliance Targets:**
- **100% FHIRPath:** Complete implementation of FHIRPath specification
- **100% SQL on FHIR:** Full compatibility with SQL on FHIR standard
- **100% CQL:** Complete Clinical Quality Language specification support

**Implementation Strategy:**
- Specification-driven development with compliance testing
- Comprehensive test suites covering all specification features
- Regular validation against official test cases
- Community engagement for specification clarification and enhancement

**Benefits:**
- Interoperability with other FHIR-based systems
- Confidence in clinical quality measure accuracy
- Future-proofing through standards alignment
- Industry credibility and adoption potential

### 8. No Hardcoded Values
**Principle:** Eliminate hardcoded values throughout the system for maximum flexibility and maintainability.

**Implementation:**
- Configuration-driven behavior with external configuration files
- Dynamic value sets and terminology loading
- Parameterized queries and expressions
- Environment-specific configuration without code changes

**Configurable Elements:**
- Database connection parameters and dialect selection
- Value set URLs and terminology service endpoints
- Performance tuning parameters and optimization settings
- Feature flags and behavioral switches
- Error handling and logging configuration

**Benefits:**
- Flexible deployment across different environments
- Easy customization without code modifications
- Maintainable configuration management
- Testing and development environment isolation

## Architectural Patterns

### 1. Layered Architecture
```
┌─────────────────────────────────────┐
│ CQL Workflow Engine (API Layer)    │
├─────────────────────────────────────┤
│ CTE Pipeline (Translation Layer)   │
├─────────────────────────────────────┤
│ SQL Generation (Database Layer)    │
├─────────────────────────────────────┤
│ Dialect Adaptation (Platform Layer)│
├─────────────────────────────────────┤
│ FHIR Data Store (Storage Layer)    │
└─────────────────────────────────────┘
```

### 2. Translation Pipeline
```
CQL Library → Parser → AST → CTE Generator → SQL → Database → Results
```

### 3. Dependency Resolution
```
CQL Defines → Dependency Graph → Topological Sort → Ordered CTEs
```

### 4. Multi-Dialect Support
```
Common Interface → Dialect Factory → Database-Specific Implementation
```

## Performance Architecture

### 1. Population-First Design
- Default to population queries with patient filtering when needed
- Batch processing optimizations throughout the pipeline
- Memory-efficient handling of large result sets

### 2. CTE Optimization Strategy
- Convert N individual queries to 1 monolithic query
- Leverage database CTE optimization capabilities  
- Minimize database connection overhead

### 3. Caching and Reuse
- Query plan caching for repeated CQL library execution
- Result caching for expensive intermediate computations
- Terminology and value set caching

## Quality Assurance Architecture

### 1. Comprehensive Testing Strategy
- Unit tests for individual components
- Integration tests for component interaction
- End-to-end tests for complete workflows
- Performance benchmarking and regression testing

### 2. Standards Compliance Validation
- Automated testing against official specification test suites
- Regular compliance validation and reporting
- Community engagement for specification interpretation

### 3. Multi-Database Validation
- Identical result validation across database dialects
- Performance characteristic comparison
- Feature parity verification

## Extensibility Architecture

### 1. Plugin Architecture
- Extensible dialect support for new databases
- Pluggable terminology services
- Configurable optimization strategies

### 2. API Design
- Stable public interfaces with internal flexibility
- Backward compatibility maintenance
- Clear deprecation and migration paths

### 3. Configuration Management
- External configuration files for all behavioral parameters
- Environment-specific configuration support
- Runtime configuration updates where appropriate

## Security Architecture

### 1. Data Protection
- Secure handling of patient data throughout pipeline
- Encryption support for data at rest and in transit
- Audit logging for data access and processing

### 2. Access Control
- Role-based access control for different user types
- Secure API authentication and authorization
- Resource-level access control where appropriate

## Deployment Architecture

### 1. Environment Support
- Development, testing, staging, and production environments
- Container-based deployment support
- Cloud and on-premises deployment flexibility

### 2. Monitoring and Observability
- Performance monitoring and alerting
- Error tracking and diagnostic information
- Usage analytics and optimization insights

## Architecture Guidelines

### Database Support Strategy
- Follow a dialect approach using method overriding for database-specific functionality
- Support both DuckDB and PostgreSQL environments
- Use Common Table Expressions (CTEs) to optimize SQL code for efficiency and readability
- Maintain backward compatibility where possible

### Code Organization
- Separate concerns appropriately
- Use clear naming conventions
- Implement proper error handling
- Follow established patterns within the codebase

## Technical Environment

### Database Connections
- **PostgreSQL:** `postgresql://postgres:postgres@localhost:5432/postgres`
- **DuckDB:** Local file-based or in-memory as appropriate

### Development Tools
- Git for version control
- Standard Python testing frameworks
- Database-specific testing utilities

## Documentation Standards Integration

### Project Documentation Structure
Follow the established project-docs structure:
- **Architecture changes**: Update `project-docs/architecture/` documentation
- **Process changes**: Update relevant files in `project-docs/process/`
- **Significant features**: Create PEPs in `project-docs/peps/`

### Architecture Decision Records (ADRs)
For significant architectural decisions:
- Create ADR in `project-docs/architecture/decisions/`
- Follow ADR template and review process
- Link ADRs to relevant PEPs when applicable

## Additional Guidelines

- Maintain professional documentation standards
- Use clear, descriptive variable and function names
- Implement appropriate logging for debugging and monitoring
- Consider performance implications of changes
- Follow security best practices
- Ensure accessibility and maintainability of code

---

**Note:** This workflow is designed to ensure high-quality, maintainable code while minimizing risks and maximizing collaboration effectiveness.