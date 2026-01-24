"""
Unit tests for FHIRPath exception hierarchy
"""

import pytest
from fhir4ds.fhirpath.exceptions import (
    FHIRPathError, FHIRPathSyntaxError, FHIRPathRuntimeError,
    FHIRPathTypeValidationError, FHIRPathHealthcareError,
    ErrorContext, ErrorLocation, ErrorSeverity, build_error_context
)


class TestExceptionHierarchy:
    """Test the exception hierarchy structure and functionality"""

    def test_base_exception_creation(self):
        """Test basic exception creation"""
        error = FHIRPathError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_context is None
        assert error.cause is None
        assert error.error_code is None

    def test_exception_with_context(self):
        """Test exception creation with error context"""
        context = build_error_context(
            expression="Patient.name",
            line=1,
            column=5,
            operation="parsing"
        )
        error = FHIRPathSyntaxError(
            "Invalid syntax",
            "Patient.name",
            line=1,
            column=5,
            error_context=context
        )

        assert "line 1, column 5" in str(error)
        assert error.expression == "Patient.name"
        assert error.line == 1
        assert error.column == 5

    def test_syntax_error_specialization(self):
        """Test syntax error specific functionality"""
        error = FHIRPathSyntaxError(
            "Unexpected token",
            "Patient.invalid$syntax",
            line=1,
            column=15,
            expected_tokens=["identifier", "function"]
        )

        assert error.error_code == "FP001"
        assert error.expression == "Patient.invalid$syntax"
        assert error.expected_tokens == ["identifier", "function"]
        assert "line 1, column 15" in str(error)

    def test_type_validation_error(self):
        """Test type validation error functionality"""
        error = FHIRPathTypeValidationError(
            "Type mismatch",
            expected_type="string",
            actual_type="integer",
            value=42
        )

        assert error.error_code == "FP020"
        assert error.expected_type == "string"
        assert error.actual_type == "integer"
        assert error.value == 42

    def test_healthcare_error_context(self):
        """Test healthcare-specific error context"""
        from fhir4ds.fhirpath.exceptions import HealthcareErrorContext

        healthcare_context = HealthcareErrorContext(
            resource_type="Patient",
            resource_id="patient-123",
            clinical_domain="demographics"
        )

        context = ErrorContext(
            healthcare_context=healthcare_context,
            severity=ErrorSeverity.ERROR,
            category="RESOURCE_ERROR"
        )

        error = FHIRPathHealthcareError(
            "Resource processing failed",
            error_context=context
        )

        assert error.error_code == "FP040"
        assert error.error_context.healthcare_context.resource_type == "Patient"

    def test_error_context_sanitization(self):
        """Test error context sanitization for logging"""
        context = build_error_context(
            expression="Patient.name",
            resource_type="Patient",
            resource_id="sensitive-patient-id-123456789",
            operation="evaluation"
        )

        sanitized = context.get_sanitized_context()

        assert sanitized["healthcare_resource_type"] == "Patient"
        assert "sensitive" not in str(sanitized)  # Should be sanitized
        assert sanitized["severity"] == "error"

    def test_exception_chaining(self):
        """Test exception chaining functionality"""
        original_error = ValueError("Original error")

        # Create error context that can hold the cause
        context = build_error_context(operation="test")

        fhirpath_error = FHIRPathError(
            "Runtime error occurred",
            error_context=context,
            cause=original_error
        )

        assert fhirpath_error.cause is original_error
        assert isinstance(fhirpath_error.cause, ValueError)

    def test_error_severity_levels(self):
        """Test different error severity levels"""
        context_debug = build_error_context(severity=ErrorSeverity.DEBUG)
        context_warning = build_error_context(severity=ErrorSeverity.WARNING)
        context_error = build_error_context(severity=ErrorSeverity.ERROR)
        context_critical = build_error_context(severity=ErrorSeverity.CRITICAL)

        assert context_debug.severity == ErrorSeverity.DEBUG
        assert context_warning.severity == ErrorSeverity.WARNING
        assert context_error.severity == ErrorSeverity.ERROR
        assert context_critical.severity == ErrorSeverity.CRITICAL

    def test_error_location_string_representation(self):
        """Test error location string representation"""
        location = ErrorLocation(
            expression="Patient.name.given.first()",
            line=3,
            column=15
        )

        location_str = str(location)
        assert "line 3, column 15" in location_str
        assert "Patient.name.given.first()" in location_str

    def test_long_expression_truncation(self):
        """Test truncation of long expressions in error messages"""
        long_expression = "Patient.name.given.where(use = 'official').first().family.where(value.length() > 10)"
        location = ErrorLocation(expression=long_expression)

        location_str = str(location)
        assert "..." in location_str  # Should be truncated
        assert len(location_str) < len(long_expression)

    def test_error_context_stack_management(self):
        """Test error context stack frame management"""
        context = ErrorContext()
        assert context.stack_trace == []

        context.add_stack_frame("Frame 1")
        context.add_stack_frame("Frame 2")

        assert len(context.stack_trace) == 2
        assert context.stack_trace[0] == "Frame 1"
        assert context.stack_trace[1] == "Frame 2"