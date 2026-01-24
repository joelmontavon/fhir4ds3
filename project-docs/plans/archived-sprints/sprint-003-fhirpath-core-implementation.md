# Sprint 003: FHIRPath Core Implementation

**Sprint**: Sprint 003 - FHIRPath Core Implementation
**Duration**: 28-09-2025 - 12-10-2025 (2 weeks)
**Sprint Lead**: Senior Solution Architect/Engineer
**Developer**: Junior Developer
**PEP Reference**: [PEP-002: FHIRPath Core Implementation](../../../project-docs/peps/accepted/pep-002-fhirpath-core-implementation.md)

---

## Sprint Goals

### Primary Objectives
1. **FHIRPath Parser Foundation**: Fork fhirpath-py and enhance with metadata-rich AST for CTE generation
2. **Core Evaluator Framework**: Complete FHIRPath evaluation engine with FHIR type system support
3. **Database Dialect Foundation**: Thin dialect architecture for DuckDB and PostgreSQL
4. **Testing Infrastructure Integration**: Comprehensive integration with established testing framework
5. **Compliance Validation**: Achieve 30%+ FHIRPath compliance improvement with official test suites

### Success Criteria
- [ ] Enhanced FHIRPath parser with metadata-rich AST parses 95% of common healthcare expressions
- [ ] Core evaluator leverages AST metadata for optimized path navigation and collection operations
- [ ] Database dialect abstraction provides consistent behavior across DuckDB and PostgreSQL
- [ ] Testing infrastructure integration demonstrates 30%+ FHIRPath compliance improvement
- [ ] Complete foundation established for Phase 2 (advanced features) development
- [ ] No regression in existing SQL-on-FHIR (100%) or CQL (59.2%) compliance levels

### Alignment with Architecture Goals
**Unified FHIRPath Architecture Implementation**: This sprint implements the critical foundation component of FHIR4DS's unified architecture, establishing FHIRPath as the single execution foundation for all healthcare expression languages. Success directly advances toward 100% FHIRPath compliance goals and enables future SQL-on-FHIR and CQL implementations.

### Implementation Approach
**Parser Strategy**: Fork and enhance the proven fhirpath-py parser (https://github.com/beda-software/fhirpath-py) rather than building from scratch. This approach:
- **Leverages Proven Foundation**: Uses mature, tested parser with existing FHIRPath compliance
- **Adds FHIR4DS Value**: Extends AST with metadata for SQL/CTE generation and population analytics
- **Reduces Risk**: Eliminates parser development risk while focusing effort on FHIR4DS-specific capabilities
- **Enables Rich CTE Generation**: Enhanced AST provides type hints, optimization flags, and database context

---

## Task Breakdown

### High Priority Tasks
| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| SP-003-001 | FHIRPath Parser Integration (fhirpath-py Fork) | Junior Developer | 20 hours | Testing infrastructure | Enhanced parser with AST metadata for CTE generation |
| SP-003-002 | Enhanced AST Integration and Validation | Junior Developer | 12 hours | SP-003-001 | Validated AST integration with metadata utilities |
| SP-003-003 | Core FHIRPath Evaluator Engine | Junior Developer | 24 hours | SP-003-002 | Basic path navigation and filtering working |
| SP-003-011 | FHIRPath Evaluator Test Fixes and Stabilization | Junior Developer | 8 hours | SP-003-003 | Unit test pass rate 100%, no regressions |
| SP-003-004 | Database Dialect Abstraction | Junior Developer | 16 hours | SP-003-011 | DuckDB and PostgreSQL syntax abstraction |
| SP-003-005 | Testing Infrastructure Integration | Junior Developer | 14 hours | SP-003-004 | Enhanced FHIRPath integration with official test suites |

### Medium Priority Tasks
| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| SP-003-006 | FHIR Type System Integration | Junior Developer | 20 hours | SP-003-005 | Proper FHIR data type handling |
| SP-003-007 | Collection Operations Implementation | Junior Developer | 18 hours | SP-003-006 | where(), select(), exists() operations |
| SP-003-008 | Error Handling and Validation | Junior Developer | 12 hours | SP-003-007 | Comprehensive error reporting |

### Low Priority Tasks (Stretch Goals)
| Task ID | Task Name | Assignee | Estimate | Dependencies | Success Criteria |
|---------|-----------|----------|-----------|--------------|------------------|
| SP-003-009 | Performance Optimization Foundation | Junior Developer | 16 hours | SP-003-008 | Basic performance monitoring |
| SP-003-010 | Documentation and Examples | Junior Developer | 12 hours | SP-003-008 | API documentation and usage examples |

---

## Compliance Focus Areas

### Target Specifications
- **FHIRPath R4**: 0.9% → 30%+ compliance (significant foundation progress)
- **SQL-on-FHIR v2.0**: Maintain 100% (foundation preparation for integration)
- **CQL Framework**: Maintain 59.2% (foundation preparation for enhancement)

### Compliance Activities
1. **Official Test Integration**: Execute FHIRPath R4 official test cases throughout development
2. **Multi-Database Validation**: Ensure identical behavior across DuckDB and PostgreSQL platforms
3. **Architecture Compliance**: Maintain unified FHIRPath architecture principles throughout implementation

### Compliance Metrics
- **Test Suite Execution**: Daily execution of FHIRPath official tests during active development
- **Performance Benchmarks**: <100ms evaluation for typical healthcare FHIRPath expressions
- **Regression Prevention**: Continuous testing prevents degradation of existing SQL-on-FHIR and CQL infrastructure

---

## Technical Focus

### Architecture Components
**Primary Components**: FHIRPath Core Engine Foundation
- **FHIRPath Parser**: ANTLR4-based grammar parser with comprehensive expression support
- **FHIRPath Evaluator**: Core evaluation engine with FHIR type system integration
- **Dialect Abstraction**: Thin dialect layer supporting DuckDB and PostgreSQL
- **Testing Integration**: Seamless integration with established testing infrastructure

### Database Dialects
- **DuckDB**: Core development and testing platform with embedded analytics focus
- **PostgreSQL**: Production deployment target with enterprise database features
- **Consistency Requirement**: 100% identical results across both database platforms

### Integration Points
- **Testing Infrastructure**: Leverage established multi-specification testing framework from PEP-001
- **Future SQL-on-FHIR**: Foundation architecture supports ViewDefinition processing integration
- **Future CQL**: Foundation architecture supports CQL expression evaluation integration

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|-------------------|
| ANTLR4 Grammar Complexity | Medium | High | Start with proven FHIRPath grammar patterns, incremental complexity |
| Type System Integration Complexity | Medium | Medium | Leverage existing FHIR type definitions, incremental implementation |
| Multi-Database Consistency | Low | High | Early testing across both platforms, thin dialect architecture |
| Performance Requirements | Low | Medium | Focus on foundation correctness, performance optimization in later phases |

### Dependencies and Blockers
1. **Testing Infrastructure Dependency**: Requires stable testing infrastructure from PEP-001 (available)
2. **ANTLR4 Runtime Dependency**: Python ANTLR4 runtime required (existing project dependency)
3. **Multi-Database Environment**: Requires access to both DuckDB and PostgreSQL (available)

### Contingency Plans
- **If ANTLR4 Grammar Issues**: Fall back to manual parser implementation with future ANTLR4 migration
- **If Performance Targets Not Met**: Focus on correctness and specification compliance, defer optimization
- **If Multi-Database Issues**: Prioritize DuckDB implementation with PostgreSQL compatibility in later sprint

---

## Testing Strategy

### Unit Testing
- **Coverage Target**: 90%+ for all new FHIRPath core components
- **New Test Requirements**: Comprehensive parser, evaluator, and dialect abstraction testing
- **Test Enhancement**: Integration with existing FHIR4DS testing patterns and quality standards

### Integration Testing
- **Database Testing**: Mandatory validation across both DuckDB and PostgreSQL environments
- **End-to-End Testing**: Complete FHIRPath expression evaluation workflows
- **Performance Testing**: Basic performance validation for foundation components

### Compliance Testing
- **Official Test Suites**: Execute FHIRPath R4 official test cases continuously during development
- **Regression Testing**: Prevent degradation of existing SQL-on-FHIR and CQL testing infrastructure
- **Custom Test Development**: Create FHIRPath-specific tests for FHIR4DS architecture patterns

---

## Definition of Done

### Code Quality Requirements
- [ ] All code passes lint and format checks according to FHIR4DS standards
- [ ] Unit test coverage meets 90%+ target for all new components
- [ ] All tests pass in both DuckDB and PostgreSQL environments
- [ ] Code review completed and approved by Senior Solution Architect/Engineer
- [ ] Documentation updated for all new APIs and architectural components

### Compliance Requirements
- [ ] FHIRPath R4 official test suite shows 30%+ compliance improvement
- [ ] Multi-database testing validates 100% consistent behavior
- [ ] No regression in existing SQL-on-FHIR or CQL testing infrastructure
- [ ] Performance targets met for basic FHIRPath evaluation (<100ms typical expressions)

### Documentation Requirements
- [ ] Code comments added for all complex logic and architectural decisions
- [ ] API documentation created for FHIRPath parser, evaluator, and dialect interfaces
- [ ] Architecture documentation updated to reflect FHIRPath foundation implementation
- [ ] Sprint progress documentation maintained throughout development

---

## Communication Plan

### Daily Updates
- **Format**: Brief status update in project documentation and daily standup
- **Content**: Task progress, blockers, next steps, test results
- **Timing**: End of development day with progress summary

### Weekly Reviews
- **Schedule**: Fridays at 3:00 PM
- **Participants**: Senior Solution Architect/Engineer, Junior Developer
- **Agenda**: Progress review, technical discussions, planning adjustments, compliance tracking

### Sprint Ceremonies
- **Sprint Planning**: 28-09-2025, 2 hours (comprehensive task planning and architecture review)
- **Mid-Sprint Check-in**: 05-10-2025, 1 hour (progress assessment and risk mitigation)
- **Sprint Review**: 12-10-2025, 2 hours (deliverable demonstration and compliance assessment)
- **Sprint Retrospective**: 12-10-2025, 1 hour (process improvement and lessons learned)

---

## Resource Requirements

### Development Environment
- **Database Access**: Local DuckDB and PostgreSQL instances for multi-database testing
- **Testing Infrastructure**: Access to established multi-specification testing framework
- **Development Tools**: Python development environment with ANTLR4 runtime support

### External Dependencies
- **FHIRPath Specification**: Monitor R4 specification for any updates or clarifications
- **ANTLR4 Python Runtime**: Ensure stable runtime version for grammar implementation
- **Official Test Cases**: Access to FHIRPath R4 official test repository for compliance validation

---

## Success Measurement

### Quantitative Metrics
- **Task Completion Rate**: Target 100% for high priority tasks, 75%+ for medium priority
- **Test Coverage**: Target 90%+ coverage for all new FHIRPath components
- **Compliance Improvement**: FHIRPath R4 compliance 0.9% → 30%+
- **Performance**: <100ms evaluation time for typical healthcare FHIRPath expressions

### Qualitative Assessments
- **Code Quality**: Clean, maintainable implementation following FHIR4DS architecture patterns
- **Architecture Alignment**: 100% compliance with unified FHIRPath architecture principles
- **Knowledge Transfer**: Strong foundation understanding for advanced FHIRPath features in future sprints
- **Process Improvement**: Refinement of development workflow for complex architectural implementations

---

## Sprint Retrospective Planning

### Areas for Evaluation
1. **What went well**: FHIRPath foundation implementation effectiveness, testing integration success
2. **What could be improved**: Development workflow efficiency, technical decision making speed
3. **Action items**: Process optimizations for complex architectural component development
4. **Lessons learned**: Architectural implementation patterns and compliance-driven development insights

### Retrospective Format
- **Duration**: 1 hour focused session
- **Facilitation**: Senior Solution Architect/Engineer with structured format
- **Documentation**: Comprehensive retrospective summary with actionable insights
- **Follow-up**: Integration of lessons learned into Sprint 004 planning

---

**Plan Created**: 27-09-2025
**Last Updated**: 27-09-2025
**Next Review**: 05-10-2025 (Mid-Sprint Check-in)

---

*This sprint plan implements PEP-002 Phase 1 objectives, establishing the critical FHIRPath foundation for FHIR4DS's unified architecture while maintaining quality standards and advancing toward 100% specification compliance goals.*