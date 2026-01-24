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

    def test_fhirpath_error_instantiation(self):
        """Test FHIRPath error creation and properties."""
        # Base error
        base_error = FHIRPathError("Base error message")
        assert isinstance(base_error, Exception)
        assert str(base_error) == "Base error message"

        # Parse error
        parse_error = FHIRPathParseError("Parse failed")
        assert isinstance(parse_error, FHIRPathError)
        assert str(parse_error) == "Parse failed"

    def test_sql_error_instantiation(self):
        """Test SQL error creation and properties."""
        # Base SQL error
        base_error = SQLGenerationError("SQL generation failed")
        assert isinstance(base_error, Exception)
        assert str(base_error) == "SQL generation failed"

        # Unsupported dialect error
        dialect_error = UnsupportedDialectError("Unsupported database")
        assert isinstance(dialect_error, SQLGenerationError)
        assert str(dialect_error) == "Unsupported database"

        # Invalid expression error
        expression_error = InvalidExpressionError("Invalid FHIRPath")
        assert isinstance(expression_error, SQLGenerationError)
        assert str(expression_error) == "Invalid FHIRPath"

    def test_exception_raising(self):
        """Test that exceptions can be raised and caught properly."""
        # Test FHIRPath exceptions
        with pytest.raises(FHIRPathError):
            raise FHIRPathError("Test error")

        with pytest.raises(FHIRPathParseError):
            raise FHIRPathParseError("Parse error")

        # Test SQL exceptions
        with pytest.raises(SQLGenerationError):
            raise SQLGenerationError("SQL error")

        with pytest.raises(UnsupportedDialectError):
            raise UnsupportedDialectError("Dialect error")

        with pytest.raises(InvalidExpressionError):
            raise InvalidExpressionError("Expression error")

    def test_exception_inheritance_catching(self):
        """Test that derived exceptions can be caught by base exception types."""
        # FHIRPath parse errors should be catchable as FHIRPath errors
        with pytest.raises(FHIRPathError):
            raise FHIRPathParseError("Parse error caught as base")

        # SQL specific errors should be catchable as SQL generation errors
        with pytest.raises(SQLGenerationError):
            raise UnsupportedDialectError("Dialect error caught as base")

        with pytest.raises(SQLGenerationError):
            raise InvalidExpressionError("Expression error caught as base")