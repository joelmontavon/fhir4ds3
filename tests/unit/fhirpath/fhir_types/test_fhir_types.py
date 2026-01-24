"""
Unit tests for FHIR Type System

Tests FHIR type checking, conversion, and validation functionality.
"""

import pytest
from datetime import datetime, date
from typing import Any

from fhir4ds.fhirpath.types.fhir_types import (
    FHIRDataType,
    FHIRTypeValidator,
    PrimitiveTypeValidator,
    ComplexTypeValidator,
    ResourceTypeValidator,
    FHIRTypeSystem
)


class TestFHIRDataType:
    """Test FHIR data type enumeration"""

    def test_primitive_types(self):
        """Test primitive type definitions"""
        assert FHIRDataType.BOOLEAN.value == "boolean"
        assert FHIRDataType.INTEGER.value == "integer"
        assert FHIRDataType.STRING.value == "string"
        assert FHIRDataType.DATE.value == "date"
        assert FHIRDataType.DATETIME.value == "dateTime"

    def test_complex_types(self):
        """Test complex type definitions"""
        assert FHIRDataType.QUANTITY.value == "Quantity"
        assert FHIRDataType.CODING.value == "Coding"
        assert FHIRDataType.CODEABLECONCEPT.value == "CodeableConcept"

    def test_resource_types(self):
        """Test resource type definitions"""
        assert FHIRDataType.PATIENT.value == "Patient"
        assert FHIRDataType.OBSERVATION.value == "Observation"
        assert FHIRDataType.ENCOUNTER.value == "Encounter"


class TestPrimitiveTypeValidator:
    """Test primitive type validator"""

    def test_boolean_validator(self):
        """Test boolean type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.BOOLEAN)

        # Valid boolean values
        assert validator.is_valid(True) is True
        assert validator.is_valid(False) is True
        assert validator.is_valid("true") is True
        assert validator.is_valid("false") is True
        assert validator.is_valid("1") is True
        assert validator.is_valid("0") is True
        assert validator.is_valid(None) is True

        # Invalid boolean values
        assert validator.is_valid("maybe") is False

        # Test conversion
        assert validator.convert(True) is True
        assert validator.convert(False) is False
        assert validator.convert("true") is True
        assert validator.convert("false") is False
        assert validator.convert("1") is True
        assert validator.convert("0") is False
        assert validator.convert(None) is None

        with pytest.raises(ValueError):
            validator.convert("invalid")

    def test_integer_validator(self):
        """Test integer type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.INTEGER)

        # Valid integer values
        assert validator.is_valid(42) is True
        assert validator.is_valid(-10) is True
        assert validator.is_valid(0) is True
        assert validator.is_valid("42") is True
        assert validator.is_valid(3.14) is True  # Can convert float to int
        assert validator.is_valid(None) is True

        # Invalid integer values
        assert validator.is_valid("not a number") is False

        # Test conversion
        assert validator.convert(42) == 42
        assert validator.convert(3.14) == 3
        assert validator.convert("42") == 42
        assert validator.convert(None) is None

        with pytest.raises(ValueError):
            validator.convert("not a number")

    def test_decimal_validator(self):
        """Test decimal type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.DECIMAL)

        # Valid decimal values
        assert validator.is_valid(3.14) is True
        assert validator.is_valid(42) is True
        assert validator.is_valid("3.14") is True
        assert validator.is_valid("42") is True
        assert validator.is_valid(None) is True

        # Invalid decimal values
        assert validator.is_valid("not a number") is False

        # Test conversion
        assert validator.convert(3.14) == 3.14
        assert validator.convert(42) == 42.0
        assert validator.convert("3.14") == 3.14
        assert validator.convert(None) is None

        with pytest.raises(ValueError):
            validator.convert("not a number")

    def test_string_validator(self):
        """Test string type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.STRING)

        # All values can be converted to string
        assert validator.is_valid("test") is True
        assert validator.is_valid(42) is True
        assert validator.is_valid(True) is True
        assert validator.is_valid(None) is True

        # Test conversion
        assert validator.convert("test") == "test"
        assert validator.convert(42) == "42"
        assert validator.convert(True) == "True"
        assert validator.convert(None) is None

    def test_date_validator(self):
        """Test date type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.DATE)

        test_date = date(2023, 5, 15)
        test_datetime = datetime(2023, 5, 15, 10, 30)

        # Valid date values
        assert validator.is_valid(test_date) is True
        assert validator.is_valid(test_datetime) is True
        assert validator.is_valid("2023-05-15") is True
        assert validator.is_valid("2023-05") is True
        assert validator.is_valid("2023") is True
        assert validator.is_valid(None) is True

        # Invalid date values
        assert validator.is_valid("not a date") is False
        assert validator.is_valid("2023-13-01") is False  # Invalid month

        # Test conversion
        converted_date = validator.convert(test_date)
        assert converted_date == test_date

        converted_from_datetime = validator.convert(test_datetime)
        assert converted_from_datetime == test_date

        converted_from_string = validator.convert("2023-05-15")
        assert converted_from_string == date(2023, 5, 15)

        assert validator.convert(None) is None

    def test_datetime_validator(self):
        """Test datetime type validation"""
        validator = PrimitiveTypeValidator(FHIRDataType.DATETIME)

        test_datetime = datetime(2023, 5, 15, 10, 30, 45)

        # Valid datetime values
        assert validator.is_valid(test_datetime) is True
        assert validator.is_valid("2023-05-15T10:30:45") is True
        assert validator.is_valid(None) is True

        # Invalid datetime values
        assert validator.is_valid("not a datetime") is False

        # Test conversion
        converted = validator.convert(test_datetime)
        assert converted == test_datetime
        assert validator.convert(None) is None


class TestComplexTypeValidator:
    """Test complex type validator"""

    def test_complex_type_basic(self):
        """Test basic complex type validation"""
        validator = ComplexTypeValidator(FHIRDataType.QUANTITY)

        # Valid complex type (dictionary)
        quantity = {"value": 10.5, "unit": "mg"}
        assert validator.is_valid(quantity) is True
        assert validator.convert(quantity) == quantity

        # Invalid complex type (not dictionary)
        assert validator.is_valid("not a dict") is False
        assert validator.is_valid(None) is True

        with pytest.raises(ValueError):
            validator.convert("not a dict")

    def test_complex_type_with_required_fields(self):
        """Test complex type validation with required fields"""
        validator = ComplexTypeValidator(
            FHIRDataType.QUANTITY,
            required_fields={"value"}
        )

        # Valid with required field
        quantity_with_value = {"value": 10.5}
        assert validator.is_valid(quantity_with_value) is True

        # Invalid without required field
        quantity_without_value = {"unit": "mg"}
        assert validator.is_valid(quantity_without_value) is False

        with pytest.raises(ValueError):
            validator.convert(quantity_without_value)


class TestResourceTypeValidator:
    """Test resource type validator"""

    def test_resource_type_validation(self):
        """Test resource type validation"""
        validator = ResourceTypeValidator(FHIRDataType.PATIENT)

        # Valid patient resource
        patient = {
            "resourceType": "Patient",
            "id": "patient-1",
            "active": True
        }
        assert validator.is_valid(patient) is True
        assert validator.convert(patient) == patient

        # Invalid resource type
        observation = {
            "resourceType": "Observation",
            "id": "obs-1"
        }
        assert validator.is_valid(observation) is False

        # Missing resourceType
        invalid_resource = {"id": "patient-1"}
        assert validator.is_valid(invalid_resource) is False

        # Not a dictionary
        assert validator.is_valid("not a resource") is False

        # None value
        assert validator.is_valid(None) is True
        assert validator.convert(None) is None

        with pytest.raises(ValueError):
            validator.convert(observation)


class TestFHIRTypeSystem:
    """Test FHIR type system"""

    @pytest.fixture
    def type_system(self):
        """Create FHIR type system for testing"""
        return FHIRTypeSystem()

    def test_type_system_initialization(self, type_system):
        """Test type system initializes correctly"""
        assert type_system is not None
        assert len(type_system._validators) > 0

    def test_is_type_primitive(self, type_system):
        """Test type checking for primitive types"""
        assert type_system.is_type(True, "boolean") is True
        assert type_system.is_type(42, "integer") is True
        assert type_system.is_type("test", "string") is True
        assert type_system.is_type(3.14, "decimal") is True

        # Cross-type checks
        assert type_system.is_type(42, "string") is True  # Can convert
        assert type_system.is_type("not a number", "integer") is False

    def test_is_type_complex(self, type_system):
        """Test type checking for complex types"""
        quantity = {"value": 10.5, "unit": "mg"}
        assert type_system.is_type(quantity, "Quantity") is True

        coding = {"system": "http://loinc.org", "code": "12345"}
        assert type_system.is_type(coding, "Coding") is True

        # Wrong type
        assert type_system.is_type("not a complex type", "Quantity") is False

    def test_is_type_resource(self, type_system):
        """Test type checking for resource types"""
        patient = {"resourceType": "Patient", "id": "patient-1"}
        assert type_system.is_type(patient, "Patient") is True

        observation = {"resourceType": "Observation", "id": "obs-1"}
        assert type_system.is_type(observation, "Observation") is True

        # Wrong resource type
        assert type_system.is_type(patient, "Observation") is False

    def test_is_type_special(self, type_system):
        """Test type checking for special types"""
        # Any type
        assert type_system.is_type("anything", "Any") is True
        assert type_system.is_type(42, "Any") is True
        assert type_system.is_type(None, "Any") is True

        # Collection type
        assert type_system.is_type([1, 2, 3], "Collection") is True
        assert type_system.is_type("not a collection", "Collection") is False

    def test_is_type_unknown(self, type_system):
        """Test type checking for unknown types"""
        assert type_system.is_type("anything", "UnknownType") is False

    def test_convert_to_type_primitive(self, type_system):
        """Test type conversion for primitive types"""
        assert type_system.convert_to_type("42", "integer") == 42
        assert type_system.convert_to_type(42, "string") == "42"
        assert type_system.convert_to_type("true", "boolean") is True

    def test_convert_to_type_special(self, type_system):
        """Test type conversion for special types"""
        # Any type
        original_value = {"test": "value"}
        assert type_system.convert_to_type(original_value, "Any") == original_value

        # Collection type
        assert type_system.convert_to_type([1, 2, 3], "Collection") == [1, 2, 3]
        assert type_system.convert_to_type("single", "Collection") == ["single"]
        assert type_system.convert_to_type(None, "Collection") == []

    def test_convert_to_type_unknown(self, type_system):
        """Test type conversion for unknown types"""
        with pytest.raises(ValueError):
            type_system.convert_to_type("value", "UnknownType")

    def test_convert_to_fhir_type(self, type_system):
        """Test conversion using FHIR type enum"""
        result = type_system.convert_to_fhir_type("42", FHIRDataType.INTEGER)
        assert result == 42

        result = type_system.convert_to_fhir_type(42, FHIRDataType.STRING)
        assert result == "42"

    def test_get_type_name(self, type_system):
        """Test getting type name for values"""
        assert type_system.get_type_name(True) == "boolean"
        assert type_system.get_type_name(42) == "integer"
        assert type_system.get_type_name(3.14) == "decimal"
        assert type_system.get_type_name("test") == "string"
        assert type_system.get_type_name([1, 2, 3]) == "Collection"
        assert type_system.get_type_name(None) == "null"

        # Date/datetime
        assert type_system.get_type_name(date.today()) == "date"
        assert type_system.get_type_name(datetime.now()) == "dateTime"

        # Resource
        patient = {"resourceType": "Patient", "id": "test"}
        assert type_system.get_type_name(patient) == "Patient"

        # Complex type (generic)
        complex_obj = {"field": "value"}
        assert type_system.get_type_name(complex_obj) == "Complex"

        # Unknown type
        class CustomObject:
            pass
        assert type_system.get_type_name(CustomObject()) == "unknown"

    def test_type_classification(self, type_system):
        """Test type classification methods"""
        # Primitive types
        assert type_system.is_primitive_type("boolean") is True
        assert type_system.is_primitive_type("integer") is True
        assert type_system.is_primitive_type("string") is True
        assert type_system.is_primitive_type("Patient") is False

        # Complex types
        assert type_system.is_complex_type("Quantity") is True
        assert type_system.is_complex_type("Coding") is True
        assert type_system.is_complex_type("boolean") is False

        # Resource types
        assert type_system.is_resource_type("Patient") is True
        assert type_system.is_resource_type("Observation") is True
        assert type_system.is_resource_type("boolean") is False

        # Unknown types
        assert type_system.is_primitive_type("UnknownType") is False
        assert type_system.is_complex_type("UnknownType") is False
        assert type_system.is_resource_type("UnknownType") is False

    def test_get_supported_types(self, type_system):
        """Test getting supported types"""
        supported_types = type_system.get_supported_types()
        assert isinstance(supported_types, list)
        assert len(supported_types) > 0
        assert "boolean" in supported_types
        assert "Patient" in supported_types
        assert "Quantity" in supported_types

    def test_validate_value(self, type_system):
        """Test value validation"""
        assert type_system.validate_value(True, "boolean") is True
        assert type_system.validate_value(42, "integer") is True
        assert type_system.validate_value("not a number", "integer") is False

        patient = {"resourceType": "Patient", "id": "test"}
        assert type_system.validate_value(patient, "Patient") is True
        assert type_system.validate_value(patient, "Observation") is False


class TestDateTimeParsing:
    """Test FHIR date/time parsing functionality"""

    def test_fhir_date_parsing(self):
        """Test FHIR date format parsing"""
        validator = PrimitiveTypeValidator(FHIRDataType.DATE)

        # Full date
        result = validator.convert("2023-05-15")
        assert result == date(2023, 5, 15)

        # Year-month only
        result = validator.convert("2023-05")
        assert result == date(2023, 5, 1)

        # Year only
        result = validator.convert("2023")
        assert result == date(2023, 1, 1)

        # Invalid formats
        with pytest.raises(ValueError):
            validator.convert("2023-13-01")  # Invalid month

        with pytest.raises(ValueError):
            validator.convert("invalid-date")

    def test_fhir_datetime_parsing(self):
        """Test FHIR datetime format parsing"""
        validator = PrimitiveTypeValidator(FHIRDataType.DATETIME)

        # Basic datetime
        result = validator.convert("2023-05-15T10:30:45")
        assert result.year == 2023
        assert result.month == 5
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45

        # With microseconds
        result = validator.convert("2023-05-15T10:30:45.123456")
        assert result.microsecond == 123456

        # Invalid format
        with pytest.raises(ValueError):
            validator.convert("invalid-datetime")


class TestTypeSystemEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def type_system(self):
        return FHIRTypeSystem()

    def test_none_handling(self, type_system):
        """Test handling of None values"""
        assert type_system.is_type(None, "boolean") is True
        assert type_system.convert_to_type(None, "boolean") is None
        assert type_system.get_type_name(None) == "null"

    def test_empty_collections(self, type_system):
        """Test handling of empty collections"""
        assert type_system.is_type([], "Collection") is True
        assert type_system.convert_to_type([], "Collection") == []

    def test_nested_complex_types(self, type_system):
        """Test handling of nested complex structures"""
        nested_resource = {
            "resourceType": "Patient",
            "name": [
                {
                    "given": ["John"],
                    "family": "Doe"
                }
            ],
            "contact": [
                {
                    "telecom": [
                        {
                            "system": "phone",
                            "value": "123-456-7890"
                        }
                    ]
                }
            ]
        }

        assert type_system.is_type(nested_resource, "Patient") is True
        assert type_system.get_type_name(nested_resource) == "Patient"


if __name__ == "__main__":
    pytest.main([__file__])