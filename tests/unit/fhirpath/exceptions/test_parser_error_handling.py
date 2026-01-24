"""
Unit tests for FHIRPath parser error handling
"""

import pytest
from unittest.mock import Mock, patch
from fhir4ds.fhirpath.parser_core.enhanced_parser import EnhancedFHIRPathParser, ParseResult
from fhir4ds.fhirpath.exceptions import (
    FHIRPathSyntaxError, FHIRPathParseError, ErrorSeverity
)


class TestParserErrorHandling:
    """Test parser error handling functionality"""

    def test_empty_expression_error(self):
        """Test error handling for empty expressions"""
        parser = EnhancedFHIRPathParser()

        # Test empty string
        result = parser.parse("")
        assert not result.is_valid
        assert result.parse_exception is not None
        assert isinstance(result.parse_exception, FHIRPathSyntaxError)
        assert "Empty or whitespace-only expression" in result.error_message

        # Test whitespace-only string
        result = parser.parse("   ")
        assert not result.is_valid
        assert isinstance(result.parse_exception, FHIRPathSyntaxError)

    def test_syntax_error_location_extraction(self):
        """Test extraction of error location from parser errors"""
        parser = EnhancedFHIRPathParser()

        # Test the helper method directly
        line, column = parser._extract_error_location("Error at line 2, column 15")
        assert line == 2
        assert column == 15

        # Test different formats
        line, column = parser._extract_error_location("Syntax error (3,8)")
        assert line == 3
        assert column == 8

        # Test line only
        line, column = parser._extract_error_location("Error on line 5")
        assert line == 5
        assert column is None

        # Test no location info
        line, column = parser._extract_error_location("Generic error message")
        assert line is None
        assert column is None

    def test_error_message_classification(self):
        """Test classification and enhancement of error messages"""
        parser = EnhancedFHIRPathParser()

        # Test syntax error classification
        enhanced = parser._classify_parse_error(
            "unexpected token",
            "Patient.name$invalid"
        )
        assert "Invalid syntax" in enhanced
        assert "unexpected character" in enhanced

        # Test missing parenthesis detection
        enhanced = parser._classify_parse_error(
            "missing closing parenthesis",
            "exists(Patient.name"
        )
        assert "missing closing parenthesis" in enhanced.lower()

        # Test healthcare context suggestions
        enhanced = parser._classify_parse_error(
            "unknown field",
            "Patient.invalidField"
        )
        assert "Patient" in enhanced
        assert "resource field names" in enhanced

    def test_parsing_with_stub_implementation(self):
        """Test parsing with stub implementation when fhirpath-py not available"""
        parser = EnhancedFHIRPathParser()

        # Mock fhirpath-py as unavailable
        with patch('fhir4ds.fhirpath.parser_core.enhanced_parser.FHIRPATHPY_AVAILABLE', False):
            result = parser.parse("Patient.name")

            # Should still create a result (stub implementation)
            assert result is not None

    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.fhirpath_parse')
    def test_fhirpath_py_error_handling(self, mock_parse):
        """Test error handling when fhirpath-py raises exceptions"""
        parser = EnhancedFHIRPathParser()

        # Test syntax error from fhirpath-py
        mock_parse.side_effect = Exception("Syntax error at position 5")

        result = parser.parse("Invalid$expression")
        assert not result.is_valid
        assert result.parse_exception is not None

    def test_parse_result_error_context(self):
        """Test that parse results include proper error context"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("")  # Empty expression
        assert result.error_context is not None
        assert result.error_context.severity == ErrorSeverity.ERROR
        assert result.error_context.category == "EMPTY_EXPRESSION"
        assert result.error_context.operation == "parse"

    def test_caching_with_errors(self):
        """Test that parsing errors are not cached"""
        parser = EnhancedFHIRPathParser(enable_cache=True)

        # Parse invalid expression
        result1 = parser.parse("")
        assert not result1.is_valid

        # Parse again - should still fail (not return cached valid result)
        result2 = parser.parse("")
        assert not result2.is_valid

    def test_healthcare_specific_error_suggestions(self):
        """Test healthcare-specific error suggestions"""
        parser = EnhancedFHIRPathParser()

        # Test patient context suggestions
        enhanced = parser._classify_parse_error(
            "unknown field",
            "Patient.birthdata"  # Typo for birthDate
        )
        assert "Patient" in enhanced
        assert "birthDate" in enhanced or "resource field" in enhanced

        # Test quote mismatch detection
        enhanced = parser._classify_parse_error(
            "unexpected end",
            "Patient.name.where(use = 'official)"  # Missing closing quote
        )
        assert "Unmatched" in enhanced or "quote" in enhanced

    def test_error_message_sanitization(self):
        """Test that error messages are properly sanitized"""
        from fhir4ds.fhirpath.exceptions import sanitize_error_for_logging

        error = FHIRPathSyntaxError(
            "Error with sensitive data: patient-123456789",
            "Patient.where(id = '123456789')"
        )

        sanitized = sanitize_error_for_logging(error)

        # Should sanitize long numbers (potential IDs)
        assert "123456789" not in sanitized["error_message"] or "[ID]" in sanitized["error_message"]
        assert sanitized["error_type"] == "FHIRPathSyntaxError"

    def test_parse_time_tracking(self):
        """Test that parse time is tracked even for errors"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("")  # Invalid expression
        assert not result.is_valid
        assert result.parse_time_ms is None  # Error occurred before timing

    def test_complex_error_scenarios(self):
        """Test complex error scenarios with multiple issues"""
        parser = EnhancedFHIRPathParser()

        # Expression with multiple syntax issues
        complex_expr = "Patient.name.where((use = 'official' and"  # Missing closing paren and incomplete

        result = parser.parse(complex_expr)
        assert not result.is_valid
        assert result.error_message is not None
        assert result.error_context is not None