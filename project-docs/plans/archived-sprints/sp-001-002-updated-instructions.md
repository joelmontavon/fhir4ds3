# SP-001-002 Updated Instructions - Unit Test Framework with Stub Implementations

**Date**: 27-09-2025
**Status**: ✅ **READY TO PROCEED** - Stub implementations created
**Task**: Implement comprehensive unit tests for FHIRPath parser and SQL generator stubs

---

## Overview

The blocker has been resolved by creating stub implementations of the FHIRPath parser and SQL generator components. You can now proceed with developing comprehensive unit tests using these realistic stub interfaces.

---

## Stub Components Available

### 1. FHIRPath Parser (`fhir4ds/fhirpath/parser.py`)

```python
from fhir4ds.fhirpath import FHIRPathParser

# Initialize parser
parser = FHIRPathParser(database_type="duckdb")

# Parse expressions
result = parser.parse("Patient.name.family")
assert result.is_valid()
assert len(result.get_path_components()) == 3

# Get statistics
stats = parser.get_statistics()
assert stats["parse_count"] > 0
```

**Key Methods to Test**:
- `parse(expression)` - Parse FHIRPath expressions
- `evaluate(expression, context)` - Evaluate against FHIR data
- `get_statistics()` - Usage statistics

### 2. SQL Generator (`fhir4ds/sql/generator.py`)

```python
from fhir4ds.sql import SQLGenerator

# Initialize generator
generator = SQLGenerator(dialect="duckdb")

# Generate SQL
sql = generator.generate_from_fhirpath("Patient.name.family")
assert "json_extract" in sql.lower()

# Test multi-database support
duckdb_gen = SQLGenerator(dialect="duckdb")
postgresql_gen = SQLGenerator(dialect="postgresql")

duckdb_sql = duckdb_gen.generate_from_fhirpath("Patient.name.family")
postgresql_sql = postgresql_gen.generate_from_fhirpath("Patient.name.family")
assert duckdb_sql != postgresql_sql  # Different SQL for different databases
```

**Key Methods to Test**:
- `generate_from_fhirpath(expression)` - Convert FHIRPath to SQL
- `get_dialect_specific_function(name)` - Database-specific functions
- `get_statistics()` - Usage statistics

---

## Unit Test Development Strategy

### 1. Update Existing Test Files

**File**: `tests/unit/test_fhirpath_parser.py`

Replace the placeholder test with comprehensive tests:

```python
import pytest
from fhir4ds.fhirpath import FHIRPathParser
from fhir4ds.fhirpath.exceptions import FHIRPathParseError

@pytest.mark.unit
class TestFHIRPathParser:

    def test_parser_initialization(self):
        """Test parser initialization with different database types."""
        parser = FHIRPathParser(database_type="duckdb")
        assert parser.database_type == "duckdb"

        parser = FHIRPathParser(database_type="postgresql")
        assert parser.database_type == "postgresql"

    def test_valid_expression_parsing(self):
        """Test parsing of valid FHIRPath expressions."""
        parser = FHIRPathParser()

        # Simple path
        result = parser.parse("Patient.name.family")
        assert result.is_valid()
        assert len(result.get_path_components()) == 3

        # Path with function
        result = parser.parse("Patient.name.first()")
        assert result.is_valid()
        assert "first()" in result.get_functions()

    def test_invalid_expression_handling(self):
        """Test error handling for invalid expressions."""
        parser = FHIRPathParser()

        # Empty expression
        with pytest.raises(FHIRPathParseError):
            parser.parse("")

        # Invalid syntax
        with pytest.raises(FHIRPathParseError):
            parser.parse("Patient..name")

    def test_function_detection(self):
        """Test detection of FHIRPath functions."""
        parser = FHIRPathParser()

        # where() function
        result = parser.parse("Patient.name.where(family.exists())")
        functions = result.get_functions()
        assert "where()" in functions
        assert "exists()" in functions

        # first() function
        result = parser.parse("Patient.telecom.first()")
        assert "first()" in result.get_functions()

    def test_statistics_tracking(self):
        """Test usage statistics tracking."""
        parser = FHIRPathParser()

        initial_stats = parser.get_statistics()
        assert initial_stats["parse_count"] == 0

        parser.parse("Patient.name")
        parser.parse("Patient.birthDate")

        final_stats = parser.get_statistics()
        assert final_stats["parse_count"] == 2
```

**File**: `tests/unit/test_sql_generator.py`

Replace the placeholder test:

```python
import pytest
from fhir4ds.sql import SQLGenerator
from fhir4ds.sql.exceptions import SQLGenerationError, UnsupportedDialectError

@pytest.mark.unit
class TestSQLGenerator:

    def test_generator_initialization(self):
        """Test SQL generator initialization."""
        generator = SQLGenerator(dialect="duckdb")
        assert generator.dialect == "duckdb"

        generator = SQLGenerator(dialect="postgresql")
        assert generator.dialect == "postgresql"

    def test_basic_sql_generation(self):
        """Test basic SQL generation from FHIRPath."""
        generator = SQLGenerator(dialect="duckdb")

        sql = generator.generate_from_fhirpath("Patient.name.family")
        assert "json_extract" in sql.lower()
        assert "Patient" in sql
        assert "name" in sql
        assert "family" in sql

    def test_multi_database_support(self):
        """Test SQL generation for different database dialects."""
        duckdb_gen = SQLGenerator(dialect="duckdb")
        postgresql_gen = SQLGenerator(dialect="postgresql")

        expression = "Patient.name.family"

        duckdb_sql = duckdb_gen.generate_from_fhirpath(expression)
        postgresql_sql = postgresql_gen.generate_from_fhirpath(expression)

        # Should generate different SQL for different databases
        assert duckdb_sql != postgresql_sql

        # DuckDB should use json_extract
        assert "json_extract" in duckdb_sql.lower()

        # PostgreSQL should use jsonb_extract_path_text
        assert "jsonb_extract_path_text" in postgresql_sql.lower()

    def test_function_handling(self):
        """Test SQL generation for FHIRPath functions."""
        generator = SQLGenerator(dialect="duckdb")

        # first() function
        sql = generator.generate_from_fhirpath("Patient.name.first()")
        assert "LIMIT 1" in sql.upper()

        # where() function
        sql = generator.generate_from_fhirpath("Patient.name.where(family.exists())")
        assert "WHERE" in sql.upper()

    def test_dialect_specific_functions(self):
        """Test dialect-specific function mapping."""
        duckdb_gen = SQLGenerator(dialect="duckdb")
        postgresql_gen = SQLGenerator(dialect="postgresql")

        # Test json_extract function mapping
        duckdb_func = duckdb_gen.get_dialect_specific_function("json_extract")
        postgresql_func = postgresql_gen.get_dialect_specific_function("json_extract")

        assert duckdb_func == "json_extract"
        assert postgresql_func == "jsonb_extract_path_text"

    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        generator = SQLGenerator(dialect="duckdb")

        # Empty expression
        with pytest.raises(SQLGenerationError):
            generator.generate_from_fhirpath("")

        # Whitespace-only expression
        with pytest.raises(SQLGenerationError):
            generator.generate_from_fhirpath("   ")

    def test_statistics_tracking(self):
        """Test usage statistics tracking."""
        generator = SQLGenerator(dialect="duckdb")

        initial_stats = generator.get_statistics()
        assert initial_stats["generation_count"] == 0
        assert initial_stats["dialect"] == "duckdb"

        generator.generate_from_fhirpath("Patient.name")
        generator.generate_from_fhirpath("Patient.birthDate")

        final_stats = generator.get_statistics()
        assert final_stats["generation_count"] == 2
```

### 2. Create New Exception Test File

**File**: `tests/unit/test_exceptions.py`

```python
import pytest
from fhir4ds.fhirpath.exceptions import FHIRPathError, FHIRPathParseError
from fhir4ds.sql.exceptions import SQLGenerationError, UnsupportedDialectError, InvalidExpressionError

@pytest.mark.unit
class TestExceptionHierarchy:

    def test_fhirpath_exception_hierarchy(self):
        """Test FHIRPath exception inheritance."""
        assert issubclass(FHIRPathParseError, FHIRPathError)
        assert issubclass(FHIRPathError, Exception)

    def test_sql_exception_hierarchy(self):
        """Test SQL exception inheritance."""
        assert issubclass(UnsupportedDialectError, SQLGenerationError)
        assert issubclass(InvalidExpressionError, SQLGenerationError)
        assert issubclass(SQLGenerationError, Exception)

    def test_exception_messages(self):
        """Test exception message handling."""
        # Test custom messages
        error = FHIRPathParseError("Custom parse error")
        assert str(error) == "Custom parse error"

        error = SQLGenerationError("Custom SQL error")
        assert str(error) == "Custom SQL error"
```

### 3. Integration Tests

**File**: `tests/integration/test_parser_generator_integration.py`

```python
import pytest
from fhir4ds.fhirpath import FHIRPathParser
from fhir4ds.sql import SQLGenerator

@pytest.mark.integration
class TestParserGeneratorIntegration:

    def test_fhirpath_to_sql_workflow(self):
        """Test complete workflow from FHIRPath parsing to SQL generation."""
        # Parse FHIRPath expression
        parser = FHIRPathParser(database_type="duckdb")
        parsed = parser.parse("Patient.name.family")

        assert parsed.is_valid()

        # Generate SQL from parsed expression
        generator = SQLGenerator(dialect="duckdb")
        sql = generator.generate_from_fhirpath("Patient.name.family")

        assert sql is not None
        assert len(sql) > 0
        assert "Patient" in sql

    def test_multi_database_consistency(self):
        """Test that both parser and generator work consistently across databases."""
        expression = "Patient.name.family"

        # Test DuckDB path
        duckdb_parser = FHIRPathParser(database_type="duckdb")
        duckdb_generator = SQLGenerator(dialect="duckdb")

        duckdb_parsed = duckdb_parser.parse(expression)
        duckdb_sql = duckdb_generator.generate_from_fhirpath(expression)

        # Test PostgreSQL path
        postgresql_parser = FHIRPathParser(database_type="postgresql")
        postgresql_generator = SQLGenerator(dialect="postgresql")

        postgresql_parsed = postgresql_parser.parse(expression)
        postgresql_sql = postgresql_generator.generate_from_fhirpath(expression)

        # Both should parse successfully
        assert duckdb_parsed.is_valid()
        assert postgresql_parsed.is_valid()

        # Both should generate valid SQL
        assert duckdb_sql is not None
        assert postgresql_sql is not None

        # SQL should be different for different databases
        assert duckdb_sql != postgresql_sql
```

---

## Testing Requirements

### Coverage Target
- **80%+ coverage** on all stub implementations
- **100% coverage** on exception handling
- **Complete coverage** of multi-database functionality

### Test Categories to Implement

1. **Unit Tests**:
   - Parser initialization and configuration
   - Valid expression parsing
   - Invalid expression error handling
   - Function detection and analysis
   - SQL generation with different dialects
   - Statistics tracking

2. **Integration Tests**:
   - Parser + Generator workflow
   - Multi-database consistency validation
   - End-to-end expression processing

3. **Error Testing**:
   - Exception hierarchy validation
   - Error message accuracy
   - Graceful error handling

### Multi-Database Validation

**Critical Requirement**: Every test must validate behavior across both DuckDB and PostgreSQL:

```python
@pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
def test_basic_functionality(dialect):
    """Test basic functionality across all supported databases."""
    generator = SQLGenerator(dialect=dialect)
    sql = generator.generate_from_fhirpath("Patient.name.family")

    # Validate SQL is generated
    assert sql is not None
    assert len(sql) > 0

    # Validate dialect-specific behavior
    if dialect == "duckdb":
        assert "json_extract" in sql.lower()
    elif dialect == "postgresql":
        assert "jsonb_extract_path_text" in sql.lower()
```

---

## Success Criteria

### SP-001-002 Completion Requirements

1. **Test Coverage**: ≥80% coverage on all stub components
2. **Multi-Database**: All tests pass on both DuckDB and PostgreSQL
3. **Error Handling**: Comprehensive exception testing
4. **Integration**: Parser + Generator workflow validated
5. **Documentation**: Updated test documentation with patterns

### Files to Create/Update

- ✅ `tests/unit/test_fhirpath_parser.py` - Comprehensive parser tests
- ✅ `tests/unit/test_sql_generator.py` - Comprehensive generator tests
- ✅ `tests/unit/test_exceptions.py` - Exception hierarchy tests
- ✅ `tests/integration/test_parser_generator_integration.py` - Integration tests

### Quality Standards

- **Realistic Testing**: Tests should validate actual stub behavior
- **Error Coverage**: Test all error conditions and edge cases
- **Multi-Database**: Consistent testing across database platforms
- **Future-Proof**: Tests should support transition to real implementations

---

## Next Steps

1. **Update existing test files** with comprehensive test suites
2. **Create new test files** for exceptions and integration testing
3. **Run test suite** and achieve 80%+ coverage
4. **Validate multi-database support** across DuckDB and PostgreSQL
5. **Document testing patterns** for future development

---

**Status**: ✅ **READY TO PROCEED**
**Estimated Effort**: 8 hours
**Priority**: HIGH - Required for Sprint 001 success

---

**Note**: The stub implementations provide realistic interfaces that simulate actual component behavior. This enables meaningful unit test development while maintaining the incremental development approach outlined in Sprint 001 goals.