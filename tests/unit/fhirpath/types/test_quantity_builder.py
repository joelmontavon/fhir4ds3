"""
Tests for FHIR Quantity Builder Module

This test suite verifies the FHIR-specific business logic for Quantity JSON construction
has been properly separated from the SQL translator layer, maintaining the "thin dialect"
architectural principle.
"""

import pytest
from decimal import Decimal
from fhir4ds.main.fhirpath.types.quantity_builder import (
    build_quantity_json,
    build_quantity_json_string,
    validate_quantity_fields,
    UCUM_SYSTEM_URL
)


class TestBuildQuantityJson:
    """Test build_quantity_json function"""

    def test_integer_quantity(self):
        """Test building quantity with integer value"""
        result = build_quantity_json(Decimal('10'), 'mg')
        assert result == {
            'value': 10,
            'unit': 'mg',
            'system': UCUM_SYSTEM_URL,
            'code': 'mg'
        }

    def test_decimal_quantity(self):
        """Test building quantity with decimal value"""
        result = build_quantity_json(Decimal('10.5'), 'kg')
        assert result == {
            'value': 10.5,
            'unit': 'kg',
            'system': UCUM_SYSTEM_URL,
            'code': 'kg'
        }

    def test_integer_from_string(self):
        """Test building quantity from string value"""
        result = build_quantity_json('100', 'mL')
        assert result == {
            'value': 100,
            'unit': 'mL',
            'system': UCUM_SYSTEM_URL,
            'code': 'mL'
        }

    def test_decimal_from_string(self):
        """Test building quantity from decimal string value"""
        result = build_quantity_json('0.001', 'g')
        assert result == {
            'value': 0.001,
            'unit': 'g',
            'system': UCUM_SYSTEM_URL,
            'code': 'g'
        }

    def test_float_value(self):
        """Test building quantity with float value"""
        result = build_quantity_json(5.5, 'cm')
        assert result == {
            'value': 5.5,
            'unit': 'cm',
            'system': UCUM_SYSTEM_URL,
            'code': 'cm'
        }

    def test_int_value(self):
        """Test building quantity with int value"""
        result = build_quantity_json(42, 'mm')
        assert result == {
            'value': 42,
            'unit': 'mm',
            'system': UCUM_SYSTEM_URL,
            'code': 'mm'
        }

    def test_ucum_system_constant(self):
        """Verify UCUM system URL is correct"""
        assert UCUM_SYSTEM_URL == "http://unitsofmeasure.org"


class TestBuildQuantityJsonString:
    """Test build_quantity_json_string function"""

    def test_returns_valid_json(self):
        """Test that function returns valid JSON string"""
        result = build_quantity_json_string(Decimal('10'), 'mg')
        assert isinstance(result, str)
        assert result.startswith('{')
        assert result.endswith('}')

    def test_contains_value(self):
        """Test JSON string contains value"""
        result = build_quantity_json_string(Decimal('100'), 'mL')
        assert '"value": 100' in result

    def test_contains_unit(self):
        """Test JSON string contains unit"""
        result = build_quantity_json_string(Decimal('10'), 'mg')
        assert '"unit": "mg"' in result

    def test_contains_system(self):
        """Test JSON string contains UCUM system"""
        result = build_quantity_json_string(Decimal('5'), 'kg')
        assert '"system": "http://unitsofmeasure.org"' in result

    def test_contains_code(self):
        """Test JSON string contains code"""
        result = build_quantity_json_string(Decimal('10.5'), 'cm')
        assert '"code": "cm"' in result

    def test_integer_value_no_decimal_point(self):
        """Test integer values don't have decimal points in JSON"""
        result = build_quantity_json_string(Decimal('10'), 'mg')
        assert '"value": 10' in result
        assert '"value": 10.0' not in result

    def test_decimal_value_has_decimal_point(self):
        """Test decimal values have decimal points in JSON"""
        result = build_quantity_json_string(Decimal('10.5'), 'kg')
        assert '"value": 10.5' in result


class TestValidateQuantityFields:
    """Test validate_quantity_fields function"""

    def test_valid_quantity_info(self):
        """Test validation passes with valid quantity info"""
        result = validate_quantity_fields({
            'value': Decimal('10'),
            'unit': 'mg'
        })
        assert result is True

    def test_missing_value(self):
        """Test validation fails without value"""
        result = validate_quantity_fields({'unit': 'mg'})
        assert result is False

    def test_missing_unit(self):
        """Test validation fails without unit"""
        result = validate_quantity_fields({
            'value': Decimal('10')
        })
        assert result is False

    def test_empty_dict(self):
        """Test validation fails with empty dict"""
        result = validate_quantity_fields({})
        assert result is False

    def test_extra_fields_ok(self):
        """Test validation passes with extra fields"""
        result = validate_quantity_fields({
            'value': Decimal('10'),
            'unit': 'mg',
            'extra': 'field'
        })
        assert result is True


class TestArchitecturalCompliance:
    """Test that the module maintains architectural principles"""

    def test_no_fhir_spec_constants_in_code(self):
        """Verify FHIR spec constants are centralized, not scattered"""
        # The UCUM system URL should be a constant, not hardcoded in functions
        assert UCUM_SYSTEM_URL in build_quantity_json_string(Decimal('1'), 'g')

    def test_business_logic_separated_from_translator(self):
        """Verify business logic is in this module, not in translator"""
        # This test verifies the architectural separation exists
        # The actual verification is that the translator imports and uses this module
        from fhir4ds.main.fhirpath.sql import translator
        # The translator should have imported from quantity_builder
        assert hasattr(translator, 'build_quantity_json_string') or \
               'quantity_builder' in str(translator.__dict__)
