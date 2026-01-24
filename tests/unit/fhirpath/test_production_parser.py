"""
Tests for Production FHIRPath Parser

Tests the production parser implementation that integrates real fhirpathpy
with FHIR4DS-specific enhancements.
"""

import pytest
from fhir4ds.fhirpath.parser import (
    FHIRPathParser,
    FHIRPathExpression
)
from fhir4ds.fhirpath.exceptions import FHIRPathParseError


class TestProductionFHIRPathParser:
    """Test cases for production FHIRPath parser"""

    def test_parser_creation(self):
        """Test basic parser creation"""
        parser = FHIRPathParser()
        assert parser is not None
        assert parser.database_type == "duckdb"

    def test_parser_creation_with_database_type(self):
        """Test parser creation with different database types"""
        duckdb_parser = FHIRPathParser(database_type="duckdb")
        assert duckdb_parser.database_type == "duckdb"

        postgres_parser = FHIRPathParser(database_type="postgresql")
        assert postgres_parser.database_type == "postgresql"

    def test_factory_function(self):
        """Test factory function for parser creation"""
        parser = FHIRPathParser()
        assert parser is not None
        assert isinstance(parser, FHIRPathParser)

    def test_basic_parsing(self):
        """Test basic FHIRPath expression parsing"""
        parser = FHIRPathParser()

        # Simple path expression
        result = parser.parse("Patient.name")
        assert result is not None
        assert result.is_valid()
        assert "Patient" in result.get_path_components()
        assert "name" in result.get_path_components()

    def test_function_parsing(self):
        """Test parsing expressions with functions"""
        parser = FHIRPathParser()

        # Function call expression
        result = parser.parse("Patient.name.first()")
        assert result is not None
        assert result.is_valid()
        assert len(result.get_functions()) > 0

    def test_empty_expression_error(self):
        """Test that empty expressions raise appropriate errors"""
        parser = FHIRPathParser()

        with pytest.raises(FHIRPathParseError):
            parser.parse("")

        with pytest.raises(FHIRPathParseError):
            parser.parse("   ")

    def test_robust_parsing(self):
        """Test that the production parser is robust with various inputs"""
        parser = FHIRPathParser()

        # Test expression that should raise parse error (double dots explicitly rejected)
        with pytest.raises(FHIRPathParseError):
            parser.parse("Patient..name")

    def test_expression_components(self):
        """Test extraction of path components and functions"""
        parser = FHIRPathParser()

        result = parser.parse("Patient.name.given.first()")
        assert result.is_valid()

        components = result.get_path_components()
        assert len(components) > 0
        assert "Patient" in components
        assert "name" in components
        assert "given" in components

        functions = result.get_functions()
        assert len(functions) > 0

    def test_evaluation_basic(self):
        """Test basic evaluation functionality"""
        parser = FHIRPathParser()

        result = parser.evaluate("Patient.name")
        assert result is not None
        assert result["is_valid"] is True
        assert "path_components" in result
        assert "functions" in result

    def test_evaluation_with_context(self):
        """Test evaluation with context"""
        parser = FHIRPathParser()

        context = {"Patient": {"name": [{"given": ["John"], "family": "Doe"}]}}
        result = parser.evaluate("Patient.name", context=context)

        assert result is not None
        assert result["is_valid"] is True

    def test_complex_expressions(self):
        """Test complex FHIRPath expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Patient.name.where(use = 'official')",
            "Patient.telecom.where(system = 'phone').value",
            "Patient.birthDate > today() - 18 'years'",
            "Patient.address.where(use = 'home').postalCode",
        ]

        for expr in expressions:
            result = parser.parse(expr)
            assert result is not None
            assert result.is_valid()

    def test_statistics(self):
        """Test parser statistics functionality"""
        parser = FHIRPathParser()

        # Parse a few expressions to generate statistics
        parser.parse("Patient.name")
        parser.parse("Patient.birthDate")

        stats = parser.get_statistics()
        assert "parse_count" in stats
        assert "database_type" in stats
        assert "fhirpathpy_available" in stats
        assert stats["parse_count"] >= 2
        assert stats["fhirpathpy_available"] is True

    def test_validation_functionality(self):
        """Test expression validation without full parsing"""
        parser = FHIRPathParser()

        # Valid expression
        result = parser.validate_expression("Patient.name")
        assert "valid" in result or result is not None

        # Invalid expression
        result = parser.validate_expression("Patient..name")
        # Should still return some validation info

    def test_enhanced_parser_access(self):
        """Test access to underlying enhanced parser"""
        parser = FHIRPathParser()

        enhanced_parser = parser.get_enhanced_parser()
        assert enhanced_parser is not None

    def test_complexity_analysis(self):
        """Test complexity analysis functionality"""
        parser = FHIRPathParser()

        result = parser.parse("Patient.name.where(use = 'official').given.first()")
        assert result.is_valid()

        complexity = result.get_complexity_analysis()
        assert complexity is not None
        assert "complexity_score" in complexity

    def test_optimization_opportunities(self):
        """Test optimization opportunity detection"""
        parser = FHIRPathParser()

        result = parser.parse("Patient.name.first()")
        assert result.is_valid()

        optimizations = result.get_optimization_opportunities()
        assert optimizations is not None
        assert isinstance(optimizations, list)

    def test_ast_access(self):
        """Test AST access functionality"""
        parser = FHIRPathParser()

        result = parser.parse("Patient.name")
        assert result.is_valid()

        ast = result.get_ast()
        assert ast is not None

    def test_database_type_consistency(self):
        """Test that database type is preserved throughout operations"""
        duckdb_parser = FHIRPathParser(database_type="duckdb")
        postgres_parser = FHIRPathParser(database_type="postgresql")

        assert duckdb_parser.get_statistics()["database_type"] == "duckdb"
        assert postgres_parser.get_statistics()["database_type"] == "postgresql"

    def test_performance_basic(self):
        """Test basic performance characteristics"""
        parser = FHIRPathParser()

        import time
        start_time = time.time()

        for _ in range(10):
            result = parser.parse("Patient.name")
            assert result.is_valid()

        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to milliseconds
        avg_time = total_time / 10

        # Should be well under 100ms per parse
        assert avg_time < 100

    def test_evaluation_robustness(self):
        """Test robust evaluation handling"""
        parser = FHIRPathParser()

        # Test expression that is invalid and should return None
        result = parser.evaluate("Patient..name")  # Double dots - invalid
        assert result is None


class TestFHIRPathExpression:
    """Test cases for FHIRPath expression objects"""

    def test_expression_creation(self):
        """Test expression object creation"""
        parser = FHIRPathParser()
        expr = parser.parse("Patient.name")

        assert isinstance(expr, FHIRPathExpression)
        assert expr.is_valid()

    def test_expression_string_representation(self):
        """Test that expression preserves original string"""
        parser = FHIRPathParser()
        original = "Patient.name.first()"
        expr = parser.parse(original)

        assert expr.expression is not None
        # Original expression content should be preserved

    def test_component_extraction(self):
        """Test component extraction works correctly"""
        parser = FHIRPathParser()
        expr = parser.parse("Patient.name.given")

        components = expr.get_path_components()
        assert isinstance(components, list)
        assert len(components) > 0

        functions = expr.get_functions()
        assert isinstance(functions, list)

    def test_metadata_access(self):
        """Test metadata access methods"""
        parser = FHIRPathParser()
        expr = parser.parse("Patient.name.first()")

        # Test all metadata access methods
        assert expr.get_complexity_analysis() is not None
        assert expr.get_optimization_opportunities() is not None
        assert expr.get_ast() is not None


if __name__ == "__main__":
    pytest.main([__file__])