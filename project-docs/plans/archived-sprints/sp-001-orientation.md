# SP-001 Junior Developer Orientation Guide

**Date**: 27-09-2025
**Sprint**: SP-001 Testing Infrastructure
**Purpose**: Comprehensive orientation for testing infrastructure implementation

---

## Overview

Welcome to Sprint 001! This sprint focuses on building a robust testing infrastructure for FHIR4DS, targeting comprehensive FHIRPath specification compliance and multi-database support.

**Sprint Duration**: 2 weeks (27-09-2025 to 11-10-2025)
**Total Effort**: 42 hours across 4 critical tasks

---

## Core Architecture Understanding

### Unified FHIRPath Architecture
FHIR4DS uses a unified architecture where:
- **FHIRPath** is the foundation for all healthcare expression evaluation
- **Multi-database support** with DuckDB and PostgreSQL as primary targets
- **Population-scale analytics** through optimized SQL generation
- **CTE-first design** for performance optimization

### Testing Strategy
Our testing approach follows these principles:
- **Specification compliance** - targeting 100% FHIRPath R4 compliance
- **Multi-database validation** - ensuring identical behavior across DuckDB and PostgreSQL
- **Stub-driven development** - using realistic stub implementations for infrastructure development
- **Comprehensive coverage** - 80%+ test coverage across all components

---

## Sprint 001 Tasks

### SP-001-001: Test Directory Structure ✅ COMPLETED
**Status**: ✅ **COMPLETED** and **MERGED**
**Branch**: `feature/SP-001-001` (merged to main)

### SP-001-002: Unit Test Framework ⚠️ IN PROGRESS
**Status**: ⚠️ **READY TO PROCEED** - Stub implementations available
**Effort**: 8 hours
**Priority**: HIGH

**What You Need to Know**:
- Stub implementations have been created for FHIRPath parser and SQL generator
- Comprehensive unit tests need to be developed using these stubs
- Target: 80%+ test coverage on stub implementations
- Multi-database testing is required (DuckDB + PostgreSQL)

**See**: `sp-001-002-updated-instructions.md` for detailed implementation guidance

### SP-001-003: Official Test Integration
**Status**: ⏳ **PENDING** SP-001-002 completion
**Effort**: 16 hours
**Priority**: HIGH

**Overview**: Integrate official FHIRPath specification test suites into our testing framework

### SP-001-004: CI/CD Automation
**Status**: ⏳ **PENDING** SP-001-003 completion
**Effort**: 18 hours
**Priority**: MEDIUM

**Overview**: Set up GitHub Actions workflows for automated testing

---

## Development Environment Setup

### Prerequisites
- Python 3.10+
- Git for version control
- Access to both DuckDB and PostgreSQL

### Database Configuration
- **DuckDB**: Local file-based or in-memory
- **PostgreSQL**: `postgresql://postgres:postgres@localhost:5432/postgres`

### Python Environment
```bash
# Set Python path for testing
export PYTHONPATH=.

# Run tests
python3 -m pytest tests/unit/ -v

# Run specific test with marker
python3 -m pytest -m unit tests/unit/test_fhirpath_parser.py -v
```

---

## Stub Implementation Overview

### FHIRPath Parser Stub (`fhir4ds/fhirpath/parser.py`)

**Purpose**: Provides realistic FHIRPath parsing interface for testing
**Key Features**:
- Expression parsing with validation
- Path component extraction
- Function detection (first(), where(), exists())
- Error handling with custom exceptions
- Statistics tracking for test validation

**Basic Usage**:
```python
from fhir4ds.fhirpath import FHIRPathParser

parser = FHIRPathParser(database_type="duckdb")
result = parser.parse("Patient.name.family")
assert result.is_valid()
assert len(result.get_path_components()) == 3
```

### SQL Generator Stub (`fhir4ds/sql/generator.py`)

**Purpose**: Simulates SQL generation from FHIRPath expressions
**Key Features**:
- Multi-database dialect support (DuckDB/PostgreSQL)
- Different SQL output for different databases
- Function handling (first() → LIMIT, where() → WHERE)
- Dialect-specific function mapping
- Error handling and statistics

**Basic Usage**:
```python
from fhir4ds.sql import SQLGenerator

generator = SQLGenerator(dialect="duckdb")
sql = generator.generate_from_fhirpath("Patient.name.family")
assert "json_extract" in sql.lower()

# Test multi-database differences
postgresql_gen = SQLGenerator(dialect="postgresql")
postgresql_sql = postgresql_gen.generate_from_fhirpath("Patient.name.family")
assert "jsonb_extract_path_text" in postgresql_sql.lower()
```

---

## Testing Patterns and Standards

### Test Organization
```
tests/
├── unit/                 # Unit tests for individual components
│   ├── test_fhirpath_parser.py
│   ├── test_sql_generator.py
│   └── test_exceptions.py
├── integration/          # Integration tests for component interaction
│   └── test_parser_generator_integration.py
├── conftest.py           # Shared test configuration
└── markers.ini           # Test markers configuration
```

### Test Markers
Use pytest markers to categorize tests:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.compliance` - Specification compliance tests

### Multi-Database Testing Pattern
Always test across both databases:
```python
@pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
def test_functionality(dialect):
    generator = SQLGenerator(dialect=dialect)
    # Test implementation
    assert generator.dialect == dialect
```

### Error Testing Pattern
Comprehensive exception testing:
```python
def test_error_handling():
    parser = FHIRPathParser()

    with pytest.raises(FHIRPathParseError):
        parser.parse("")  # Empty expression

    with pytest.raises(FHIRPathParseError):
        parser.parse("Patient..name")  # Invalid syntax
```

---

## Quality Standards

### Code Coverage
- **Target**: 80%+ coverage on all stub implementations
- **Required**: 100% coverage on exception handling
- **Validation**: Multi-database consistency testing

### Test Quality
- **Realistic Testing**: Tests should validate actual stub behavior
- **Edge Cases**: Test boundary conditions and error scenarios
- **Integration Ready**: Tests should support transition to real implementations
- **Documentation**: Clear test descriptions and purpose

### Multi-Database Requirements
Every test must validate behavior across both DuckDB and PostgreSQL:
- Consistent parsing behavior
- Appropriate SQL generation differences
- Error handling consistency
- Feature parity where applicable

---

## Common Issues and Solutions

### Import Issues
If you encounter module import errors:
```bash
# Ensure Python path is set
export PYTHONPATH=.

# Verify stub imports work
python3 -c "from fhir4ds.fhirpath import FHIRPathParser; print('Success')"
```

### Test Discovery Issues
If tests aren't discovered:
- Ensure test files start with `test_`
- Verify proper class and method naming (`TestClassName`, `test_method_name`)
- Check pytest markers are properly applied

### Database Configuration Issues
For PostgreSQL testing:
- Ensure PostgreSQL is running and accessible
- Verify connection string: `postgresql://postgres:postgres@localhost:5432/postgres`
- DuckDB should work without additional configuration

---

## Success Criteria

### SP-001-002 Completion Requirements
- [ ] **Test Coverage**: ≥80% coverage on all stub components
- [ ] **Multi-Database**: All tests pass on both DuckDB and PostgreSQL
- [ ] **Error Handling**: Comprehensive exception testing implemented
- [ ] **Integration**: Parser + Generator workflow validated
- [ ] **Documentation**: Test patterns documented for future development

### Code Quality Standards
- [ ] **Clean Code**: Proper naming, organization, and documentation
- [ ] **Error Safety**: All error conditions tested and handled
- [ ] **Performance**: Tests execute quickly and efficiently
- [ ] **Maintainability**: Tests are clear, well-structured, and extensible

---

## Next Steps After SP-001-002

1. **SP-001-003**: Official test integration
2. **SP-001-004**: GitHub Actions automation
3. **Future Sprints**: Real implementation development using testing foundation

---

## Getting Help

### Resources
- **PEP-001**: `project-docs/peps/accepted/pep-001-testing-infrastructure.md`
- **Sprint Plan**: `project-docs/plans/current-sprint/sprint-001-testing-infrastructure.md`
- **Detailed Instructions**: `project-docs/plans/orientation/sp-001-002-updated-instructions.md`

### Questions and Support
- Review documentation thoroughly before asking questions
- Check existing stub implementations for patterns and examples
- Ensure environment setup is correct before reporting issues

---

**Remember**: The goal is to build a solid testing foundation that will support all future development. Focus on creating comprehensive, reliable tests that will guide the transition from stubs to real implementations.

---

**Status**: ✅ **READY FOR DEVELOPMENT**
**Next Action**: Begin SP-001-002 implementation using updated instructions