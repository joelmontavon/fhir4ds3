"""
Unit tests for FHIRPath type validation error handling
"""

import pytest
from fhir4ds.fhirpath.types.type_converter import FHIRTypeConverter
from fhir4ds.fhirpath.exceptions import (
    FHIRPathTypeValidationError, FHIRPathTypeConversionError
)


class TestTypeValidationErrors:
    """Test type validation error handling"""

    def test_healthcare_constraint_validation_success(self):
        """Test successful healthcare constraint validation"""
        converter = FHIRTypeConverter()

        # Test valid values
        assert converter.validate_healthcare_constraints("123-45-6789", "id") is True
        assert converter.validate_healthcare_constraints("http://example.com", "url") is True
        assert converter.validate_healthcare_constraints("urn:oid:1.2.3.4", "oid") is True

    def test_healthcare_constraint_validation_failure(self):
        """Test healthcare constraint validation failures"""
        converter = FHIRTypeConverter()

        # Test invalid values without raising errors
        assert converter.validate_healthcare_constraints("invalid$id", "id") is False
        assert converter.validate_healthcare_constraints("not-a-url", "url") is False
        assert converter.validate_healthcare_constraints("invalid-oid", "oid") is False

    def test_healthcare_constraint_validation_with_errors(self):
        """Test healthcare constraint validation with error raising"""
        converter = FHIRTypeConverter()

        # Test that errors are raised when requested
        with pytest.raises(FHIRPathTypeValidationError) as exc_info:
            converter.validate_healthcare_constraints(
                "invalid$id",
                "id",
                raise_on_error=True
            )

        error = exc_info.value
        assert error.expected_type == "id"
        assert error.actual_type == "str"
        assert error.value == "invalid$id"
        assert "ID must contain only alphanumeric" in str(error)

    def test_oid_validation_specifics(self):
        """Test OID validation specific patterns"""
        converter = FHIRTypeConverter()

        # Valid OIDs
        valid_oids = [
            "urn:oid:1.2.3.4",
            "urn:oid:2.16.840.1.113883.4.1",
            "urn:oid:0.1.2.3.4.5"
        ]

        for oid in valid_oids:
            assert converter.validate_healthcare_constraints(oid, "oid") is True

        # Invalid OIDs
        invalid_oids = [
            "1.2.3.4",  # Missing urn:oid prefix
            "urn:oid:",  # No identifier
            "urn:oid:3.2.1",  # Starts with 3 (invalid)
            "urn:oid:1.0.2.3"  # Contains 0 as second node
        ]

        for oid in invalid_oids:
            assert converter.validate_healthcare_constraints(oid, "oid") is False

    def test_uuid_validation_specifics(self):
        """Test UUID validation specific patterns"""
        converter = FHIRTypeConverter()

        # Valid UUIDs
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "123e4567-e89b-12d3-a456-426614174000"
        ]

        for uuid in valid_uuids:
            assert converter.validate_healthcare_constraints(uuid, "uuid") is True

        # Invalid UUIDs
        invalid_uuids = [
            "550e8400-e29b-41d4-a716-44665544000",  # Wrong length
            "550e8400-e29b-41d4-a716-44665544000g",  # Invalid character
            "550e8400e29b41d4a716446655440000",  # Missing hyphens
            "550e8400-e29b-41d4-a716"  # Incomplete
        ]

        for uuid in invalid_uuids:
            assert converter.validate_healthcare_constraints(uuid, "uuid") is False

    def test_id_validation_specifics(self):
        """Test FHIR ID validation specific patterns"""
        converter = FHIRTypeConverter()

        # Valid IDs
        valid_ids = [
            "example",
            "patient-123",
            "Patient.123.name",
            "a1b2c3d4e5f6",
            "test-id-123.456"
        ]

        for id_val in valid_ids:
            assert converter.validate_healthcare_constraints(id_val, "id") is True

        # Invalid IDs
        invalid_ids = [
            "invalid$id",  # Invalid character $
            "patient 123",  # Space not allowed
            "very-long-id-that-exceeds-the-maximum-allowed-length-of-64-characters-for-fhir-ids",  # Too long
            "",  # Empty
            "patient@example.com"  # @ not allowed
        ]

        for id_val in invalid_ids:
            assert converter.validate_healthcare_constraints(id_val, "id") is False

    def test_positive_int_validation(self):
        """Test positive integer validation"""
        converter = FHIRTypeConverter()

        # Valid positive integers
        assert converter.validate_healthcare_constraints(1, "positiveInt") is True
        assert converter.validate_healthcare_constraints(100, "positiveInt") is True
        assert converter.validate_healthcare_constraints("5", "positiveInt") is True  # String representation

        # Invalid positive integers
        assert converter.validate_healthcare_constraints(0, "positiveInt") is False
        assert converter.validate_healthcare_constraints(-1, "positiveInt") is False
        assert converter.validate_healthcare_constraints(3.14, "positiveInt") is False

    def test_unsigned_int_validation(self):
        """Test unsigned integer validation"""
        converter = FHIRTypeConverter()

        # Valid unsigned integers
        assert converter.validate_healthcare_constraints(0, "unsignedInt") is True
        assert converter.validate_healthcare_constraints(100, "unsignedInt") is True

        # Invalid unsigned integers
        assert converter.validate_healthcare_constraints(-1, "unsignedInt") is False
        assert converter.validate_healthcare_constraints(-100, "unsignedInt") is False

    def test_url_validation_specifics(self):
        """Test URL validation patterns"""
        converter = FHIRTypeConverter()

        # Valid URLs
        valid_urls = [
            "http://example.com",
            "https://www.example.com/path",
            "http://localhost:8080/api",
            "https://api.example.com/v1/resource?param=value"
        ]

        for url in valid_urls:
            assert converter.validate_healthcare_constraints(url, "url") is True

        # Invalid URLs
        invalid_urls = [
            "ftp://example.com",  # Wrong protocol
            "example.com",  # Missing protocol
            "http://",  # Incomplete
            "not-a-url-at-all"
        ]

        for url in invalid_urls:
            assert converter.validate_healthcare_constraints(url, "url") is False

    def test_error_context_in_validation_errors(self):
        """Test that validation errors include proper context"""
        converter = FHIRTypeConverter()

        with pytest.raises(FHIRPathTypeValidationError) as exc_info:
            converter.validate_healthcare_constraints(
                "invalid$id",
                "id",
                raise_on_error=True
            )

        error = exc_info.value
        assert error.error_context is not None
        assert error.error_context.category == "TYPE_VALIDATION"
        assert error.error_context.operation == "healthcare_constraint_validation"

    def test_unexpected_validation_errors(self):
        """Test handling of unexpected errors during validation"""
        converter = FHIRTypeConverter()

        # Mock a method to raise an unexpected error
        original_method = converter._validate_id
        def failing_method(value):
            raise RuntimeError("Unexpected error")

        converter._validate_id = failing_method

        try:
            # Should handle unexpected error gracefully
            result = converter.validate_healthcare_constraints("test", "id", raise_on_error=False)
            assert result is False

            # Should raise wrapped error when requested
            with pytest.raises(FHIRPathTypeValidationError):
                converter.validate_healthcare_constraints("test", "id", raise_on_error=True)

        finally:
            # Restore original method
            converter._validate_id = original_method

    def test_null_value_handling(self):
        """Test handling of null/None values"""
        converter = FHIRTypeConverter()

        # Null values should always pass validation
        assert converter.validate_healthcare_constraints(None, "id") is True
        assert converter.validate_healthcare_constraints(None, "url") is True
        assert converter.validate_healthcare_constraints(None, "uuid") is True

    def test_unknown_type_handling(self):
        """Test handling of unknown FHIR types"""
        converter = FHIRTypeConverter()

        # Unknown types should pass validation (no specific constraints)
        assert converter.validate_healthcare_constraints("any value", "unknownType") is True
        assert converter.validate_healthcare_constraints(123, "customType") is True