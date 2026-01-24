# Architecture Documentation

## Overview

This directory contains comprehensive architecture documentation for FHIR4DS, including strategic goals, technical decisions, reference materials, and visual representations of the system design.

## Directory Structure

### Core Documentation
- **[goals.md](goals.md)** - Strategic architecture goals and 100% compliance targets
- **[decisions/](decisions/)** - Architecture Decision Records (ADRs)
- **[diagrams/](diagrams/)** - System architecture diagrams and visual documentation
- **[reference/](reference/)** - Reference materials and external specification links
- **[fhirpath-execution-pipeline.md](fhirpath-execution-pipeline.md)** - End-to-end execution flow for Sprint 011 CTE infrastructure
- **[cte-infrastructure.md](cte-infrastructure.md)** - Detailed design of CTE builder/assembler components
- **[performance-characteristics.md](performance-characteristics.md)** - Sprint 011 performance findings and regression targets

## Architecture Philosophy

### FHIRPath-First Foundation
FHIR4DS is built on the principle that **FHIRPath should be the single execution foundation** for all healthcare expression languages, providing:

- **Unified Execution Path**: Single engine for FHIRPath, SQL-on-FHIR, and CQL
- **Population-Scale Analytics**: Default to population queries with patient filtering when needed
- **CTE-First SQL Generation**: Every operation maps to CTE templates for optimal performance
- **Thin Database Dialects**: Database differences handled through simple syntax translation only

### Core Architectural Principles

#### 1. Population Analytics First
Design for population-scale analytics rather than processing one patient's data at a time:
- CQL execution operates on entire patient populations by default
- 10x+ performance improvements through population-scale optimization
- Natural fit for quality measures and population health analytics

#### 2. Standards Compliance Goals
**Target: 100% compliance** with all major healthcare interoperability specifications:
- **FHIRPath R4**: Complete implementation of FHIRPath specification
- **SQL-on-FHIR**: Full compatibility with SQL-on-FHIR standard
- **CQL Framework**: Complete Clinical Quality Language specification support
- **Quality Measures**: 100% eCQI Framework compliance

#### 3. Multi-Dialect Database Support
Support multiple database platforms with feature parity:
- **DuckDB**: Primary development and embedded analytics platform
- **PostgreSQL**: Production deployment and enterprise integration
- **Extensible**: Clean architecture supports additional dialects

#### 4. Monolithic Query Architecture
Quality measures implemented as monolithic queries for optimal performance:
- Complete CQL library execution in single database query
- All define statements combined into comprehensive CTE structure
- 11.8x average performance improvement validated across measures

## Strategic Goals

### Compliance Targets

| Specification | Target Compliance | Architecture Approach |
|---------------|------------------|----------------------|
| **FHIRPath R4** | 100% | **Foundation execution engine** |
| **SQL-on-FHIR** | 100% | **Translation to FHIRPath patterns** |
| **CQL Framework** | 100% | **Translation to FHIRPath with monolithic execution** |
| **Quality Measures** | 100% | **CQL-based measure calculation** |

### Performance Benchmarks
- **Population Scale**: Support 10M+ patients without performance degradation
- **Query Response**: Population queries complete within 5 seconds
- **Measure Execution**: Quality measures calculate in <30 seconds for 1M patients
- **Memory Efficiency**: Process large datasets using <8GB RAM

### Architecture Components

#### **FHIRPath Engine** (The Heart)
- **Forked Pure Python Parser**: Based on fhirpathpy (MIT licensed) with SQL-optimized extensions
- **Zero Java Dependencies**: Enterprise-accessible pure Python implementation
- **Custom AST Nodes**: Extended AST with SQL metadata for optimal translation
- **Single-Pass SQL Generation**: Direct FHIRPath → SQL translation during parsing
- Population-first design with patient filtering capability

#### **Language Translators** (Input Adapters)
- **ViewDefinition→FHIRPath**: Convert SQL-on-FHIR paths to FHIRPath expressions
- **CQL→FHIRPath**: Convert CQL defines to FHIRPath expressions with dependencies

#### **CTE Generator** (SQL Builder)
- Maps each FHIRPath operation to CTE template
- Generates dependency-ordered CTE chains
- Population-optimized SQL generation

#### **SQL Assembler** (Query Combiner)
- Combines multiple CTE chains into monolithic queries
- Perfect for CQL with multiple define statements
- Database engine optimization friendly

#### **Thin Dialect Layer** (Syntax Only)
- Pure database syntax differences
- No business logic whatsoever
- Simple method overrides for SQL function names

## Architecture Decision Records (ADRs)

Architecture decisions are documented in the `decisions/` directory using the ADR format:

### Current ADRs
- **ADR-001**: [Create your first ADR here]
- **ADR-002**: [Document major architectural decisions]
- **ADR-003**: [Each ADR follows standard template]

### ADR Process
1. **Identify Decision**: Significant architectural choice requiring documentation
2. **Create ADR**: Use standard ADR template in `decisions/` directory
3. **Review**: Senior Solution Architect/Engineer reviews and approves
4. **Implementation**: Decision guides implementation approach
5. **Evolution**: Update ADR status as decisions evolve

## System Architecture Overview

### Unified Execution Path with Forked Parser
```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                              │
├─────────────────┬─────────────────┬─────────────────────────┤
│  SQL-on-FHIR    │      CQL        │      FHIRPath           │
│ ViewDefinition  │   Expression    │     Expression          │
└─────────────────┴─────────────────┴─────────────────────────┘
         │                 │                   │
         ▼                 ▼                   │
┌─────────────────┐┌─────────────────┐        │
│ViewDef→FHIRPath ││  CQL→FHIRPath   │        │
│   Translator    ││   Translator    │        │
└─────────────────┘└─────────────────┘        │
         │                 │                   │
         └─────────────────┼───────────────────┘
                          ▼
              ┌─────────────────────────┐
              │  Forked FHIRPath Parser │
              │ (Pure Python + ANTLR4)  │
              │   - Zero Java deps      │
              │   - SQL-extended AST    │
              │   - Single-pass trans   │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   CTE Generator         │
              │ (Expression → CTEs)     │
              │   - Direct translation  │
              │   - Population CTEs     │
              │   - Metadata inference  │
              └─────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   Thin Dialect Layer    │
              │  (PostgreSQL/DuckDB)    │
              └─────────────────────────┘
```

### Component Responsibilities

#### **Forked FHIRPath Parser** (The Heart)
- **Pure Python Foundation**: Forked from fhirpathpy (MIT license) with zero Java dependencies
- **ANTLR4-Generated Core**: Uses proven ANTLR4-generated parser for specification compliance
- **SQL-Extended AST**: Custom AST nodes with SQL metadata for optimal translation
- **Enterprise Accessible**: Single `pip install` deployment with no external tools
- **Performance Optimized**: Single-pass SQL generation during AST traversal

#### **CTE Generator** (Expression → CTE Engine)
- **Expression → CTE**: Converts FHIRPath expressions into CTE chains
- **Population CTEs**: Produces CTE-optimized SQL for population-scale analytics
- **Dependency Resolution**: Handles complex CQL dependency graphs
- **Template Library**: Reusable CTE patterns for consistent SQL generation

#### **Language Translators** (Input Adapters)
- **ViewDefinition→FHIRPath**: Convert SQL-on-FHIR paths to FHIRPath expressions
- **CQL→FHIRPath**: Convert CQL defines to FHIRPath expressions with dependencies

#### **CTE Generator** (SQL Builder)
- Maps each FHIRPath operation to CTE template
- Generates dependency-ordered CTE chains
- Population-optimized SQL generation

#### **SQL Assembler** (Query Combiner)
- Combines multiple CTE chains into monolithic queries
- Perfect for CQL with multiple define statements
- Database engine optimization friendly

#### **Thin Dialect Layer** (Syntax Only)
- Pure database syntax differences
- No business logic whatsoever
- Simple method overrides for SQL function names

## Component Architecture Documentation

### FHIRPath AST-to-SQL Translator (PEP-003)
Detailed architecture documentation for the translator component:
- **[translator-architecture.md](translator-architecture.md)** - Complete translator architecture guide
  - Visitor pattern implementation
  - SQL fragment structure and design
  - Translation process flow
  - Dialect integration architecture
  - PEP-004 integration contract
  - Performance characteristics
  - Testing architecture

## Reference Materials

### Official Specifications
Comprehensive links to all target specifications are documented in:
- **[specifications.md](reference/specifications.md)** - Complete specification reference with official links

### Key Specifications Include:
- **FHIRPath R4**: [hl7.org/fhirpath/](https://hl7.org/fhirpath/)
- **SQL-on-FHIR v2.0**: [sql-on-fhir-v2.readthedocs.io](https://sql-on-fhir-v2.readthedocs.io/)
- **CQL R1.5**: [cql.hl7.org](https://cql.hl7.org/)
- **eCQI Framework**: [ecqi.healthit.gov](https://ecqi.healthit.gov/)

### Official Testing Resources
- **FHIRPath Test Cases**: [github.com/HL7/FHIRPath/tree/master/tests](https://github.com/HL7/FHIRPath/tree/master/tests)
- **SQL-on-FHIR Tests**: [github.com/sql-on-fhir-v2/sql-on-fhir-v2/tree/main/tests](https://github.com/sql-on-fhir-v2/sql-on-fhir-v2/tree/main/tests)
- **CQL Test Suite**: [github.com/cqframework/cql-tests](https://github.com/cqframework/cql-tests)

## Forked FHIRPath Parser Architecture

### Strategic Decision: Fork fhirpathpy for SQL Optimization

**License**: MIT (Permissive) - Allows modification and redistribution
**Source**: [beda-software/fhirpath-py](https://github.com/beda-software/fhirpath-py)
**Rationale**: Provides proven ANTLR4-generated parser with enterprise accessibility

### Fork Implementation Strategy

#### **Phase 1: Core Parser Fork**
```
fhir4ds/parser/
├── antlr/
│   ├── FHIRPath.g4              # Official ANTLR4 grammar (forked)
│   ├── generated/               # ANTLR4-generated parser files
│   │   ├── FHIRPathLexer.py
│   │   ├── FHIRPathParser.py
│   │   └── FHIRPathListener.py
│   └── build/                   # Build tools for parser generation
├── ast/
│   ├── base_nodes.py           # Core AST nodes (forked)
│   └── sql_nodes.py            # SQL-extended AST nodes (custom)
├── visitors/
│   ├── base_visitor.py         # Base visitor (forked)
│   └── sql_translator.py       # SQL translation visitor (custom)
└── core.py                     # Parser interface (forked + extended)
```

#### **Phase 2: SQL-Extended AST Nodes**
Enhanced AST nodes with SQL metadata for optimal translation:

```python
class SQLAwareIdentifier(Identifier):
    """Extended identifier with SQL hints"""
    def __init__(self, text, sql_column_hint=None, table_alias=None):
        super().__init__(text)
        self.sql_column_hint = sql_column_hint    # JSON path optimization
        self.table_alias = table_alias            # Multi-table support

class PopulationFunction(FunctionCall):
    """Population-specific functions like count(), avg()"""
    def __init__(self, name, args, aggregation_type="population"):
        super().__init__(name, args)
        self.aggregation_type = aggregation_type  # population vs patient-level
```

#### **Phase 3: Single-Pass SQL Translation Visitor**
Custom visitor that generates SQL during AST traversal:

```python
class FHIRPathSQLTranslationVisitor(FHIRPathBaseVisitor):
    """Generates optimized SQL during AST walk"""

    def visitInvocationExpression(self, ctx):
        # Direct SQL generation with population optimization
        return self._generate_population_cte(ctx)

    def visitFunctionCall(self, ctx):
        # Map FHIRPath functions to SQL equivalents
        return self._translate_function_to_sql(ctx)
```

### Architecture Benefits

#### **Performance Advantages**
- **2-3x Faster Parsing**: Single-pass SQL generation vs. parse → extract → translate
- **Memory Efficient**: No intermediate AST storage for SQL generation
- **Population Optimized**: Direct CTE generation during parsing

#### **Enterprise Accessibility**
- **Zero Java Dependencies**: Pure Python implementation
- **Single pip install**: No external tools or complex setup
- **Proven Foundation**: Built on mature, well-tested fhirpathpy parser

#### **Extensibility**
- **Custom Functions**: Add population analytics functions (`Patient.count()`)
- **SQL Optimizations**: Add database-specific optimizations during parsing
- **Metadata Inference**: Enhance AST with SQL hints for better query plans

### Implementation Roadmap

1. **Fork Setup** (SP-001-011): Import fhirpathpy code and establish build process
2. **AST Extensions** (SP-001-012): Add SQL metadata to AST nodes
3. **CTE Generator** (SP-001-013): Implement Expression → CTE translation engine
4. **Population Functions** (SP-001-014): Add custom FHIRPath functions for analytics
5. **Optimization** (SP-001-015): Performance tuning and SQL optimization
6. **Testing** (SP-001-016): Validate against official FHIRPath test suite
7. **Performance** (SP-001-017): Benchmark and optimize for population scale

## Quality Assurance

### Compliance Monitoring
- **Daily Test Execution**: Automated execution of all specification test suites
- **Compliance Dashboard**: Real-time compliance metrics and trend analysis
- **Regression Detection**: Immediate notification of compliance degradation
- **Performance Monitoring**: Continuous performance benchmarking and alerting

### Testing Strategy
- **Official Test Suites**: Execute all official specification test suites
- **Custom Test Development**: FHIR4DS-specific test cases for edge conditions
- **Regression Prevention**: Comprehensive regression testing on every change
- **Performance Validation**: Population-scale performance verification

### Architecture Review Process
1. **Design Review**: All architectural changes reviewed before implementation
2. **Implementation Review**: Code review focuses on architectural alignment
3. **Compliance Verification**: Changes verified against specification requirements
4. **Performance Assessment**: Performance impact assessed and documented

## Getting Started

### For Architects
1. **Review Goals**: Start with [goals.md](goals.md) for strategic objectives
2. **Understand Principles**: Review core architectural principles above
3. **Study Decisions**: Read existing ADRs in [decisions/](decisions/) directory
4. **Plan Changes**: Create new ADRs for significant architectural decisions

### For Developers
1. **Architecture Context**: Understand the FHIRPath-first foundation
2. **Implementation Patterns**: Follow established patterns for database dialects
3. **Testing Requirements**: Ensure all changes maintain specification compliance
4. **Documentation**: Update architecture documentation with structural changes

### For Stakeholders
1. **Strategic Vision**: Review goals and compliance targets
2. **Progress Tracking**: Monitor compliance metrics and architecture evolution
3. **Quality Assurance**: Understand testing and validation approaches
4. **Reference Materials**: Access official specifications and community resources

## Contributing to Architecture Documentation

### Adding New Documentation
- **ADRs**: Create new ADRs for significant architectural decisions
- **Diagrams**: Add visual representations of system components and interactions
- **Reference Updates**: Keep specification links and testing resources current
- **Goal Tracking**: Update progress toward compliance and performance targets

### Documentation Standards
- **Clear Writing**: Use professional, unambiguous language
- **Visual Aids**: Include diagrams and examples where helpful
- **Version Control**: Track all changes with clear rationale
- **Regular Review**: Keep documentation current with system evolution

---

## Conclusion

FHIR4DS architecture is designed to achieve 100% compliance with all major healthcare interoperability specifications while delivering industry-leading performance for population-scale analytics. The FHIRPath-first foundation with CTE-based SQL generation provides a unified, optimizable execution model that scales to production healthcare analytics workloads.

This architecture documentation serves as the authoritative source for understanding system design principles, tracking strategic progress, and guiding implementation decisions.

---

*This architecture documentation is actively maintained to reflect the current state and future direction of FHIR4DS system design.*
