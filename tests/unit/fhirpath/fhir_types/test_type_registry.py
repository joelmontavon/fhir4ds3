"""
Unit tests for FHIR Type Registry

Tests type registration, lookup, and management functionality.
"""

import pytest
from typing import Any

from fhir4ds.fhirpath.types.type_registry import (
    TypeRegistry,
    get_type_registry,
    register_global_type,
    is_valid_type,
    convert_to_type
)
from fhir4ds.fhirpath.types.fhir_types import (
    FHIRTypeValidator,
    PrimitiveTypeValidator,
    FHIRDataType
)


class TestTypeRegistry:
    """Test type registry functionality"""

    @pytest.fixture
    def registry(self):
        """Create a fresh type registry for testing"""
        return TypeRegistry()

    def test_initialization(self, registry):
        """Test registry initializes with standard FHIR types"""
        stats = registry.get_registry_stats()

        assert stats['total_types'] > 0
        assert stats['primitive_types'] > 0
        assert stats['complex_types'] > 0
        assert stats['resource_types'] > 0
        assert stats['aliases'] > 0

    def test_get_primitive_types(self, registry):
        """Test getting primitive type list"""
        primitive_types = registry.get_primitive_types()

        assert isinstance(primitive_types, list)
        assert 'boolean' in primitive_types
        assert 'integer' in primitive_types
        assert 'string' in primitive_types
        assert 'date' in primitive_types
        assert 'dateTime' in primitive_types

    def test_get_complex_types(self, registry):
        """Test getting complex type list"""
        complex_types = registry.get_complex_types()

        assert isinstance(complex_types, list)
        assert 'Quantity' in complex_types
        assert 'Coding' in complex_types
        assert 'CodeableConcept' in complex_types
        assert 'Reference' in complex_types

    def test_get_resource_types(self, registry):
        """Test getting resource type list"""
        resource_types = registry.get_resource_types()

        assert isinstance(resource_types, list)
        assert 'Patient' in resource_types
        assert 'Observation' in resource_types
        assert 'Encounter' in resource_types

    def test_is_registered_type(self, registry):
        """Test checking if types are registered"""
        # Standard FHIR types
        assert registry.is_registered_type('boolean') is True
        assert registry.is_registered_type('Patient') is True
        assert registry.is_registered_type('Quantity') is True

        # Aliases
        assert registry.is_registered_type('bool') is True
        assert registry.is_registered_type('int') is True
        assert registry.is_registered_type('str') is True

        # Unknown type
        assert registry.is_registered_type('UnknownType') is False

    def test_get_canonical_name(self, registry):
        """Test getting canonical names (alias resolution)"""
        assert registry.get_canonical_name('bool') == 'boolean'
        assert registry.get_canonical_name('int') == 'integer'
        assert registry.get_canonical_name('str') == 'string'
        assert registry.get_canonical_name('list') == 'Collection'
        assert registry.get_canonical_name('System.String') == 'string'
        assert registry.get_canonical_name('Duration') == 'Quantity'

        # Non-aliases return themselves
        assert registry.get_canonical_name('Patient') == 'Patient'
        assert registry.get_canonical_name('Quantity') == 'Quantity'

    def test_resolve_to_canonical(self, registry):
        """Test resolving aliases and canonical names."""
        assert registry.resolve_to_canonical('code') == 'string'
        assert registry.resolve_to_canonical('CODE') == 'string'
        assert registry.resolve_to_canonical('url') == 'uri'
        assert registry.resolve_to_canonical('UUID') == 'uri'
        assert registry.resolve_to_canonical('unsignedInt') == 'integer'
        assert registry.resolve_to_canonical('Instant') == 'instant'
        assert registry.resolve_to_canonical('Date') == 'date'
        assert registry.resolve_to_canonical('System.String') == 'string'
        assert registry.resolve_to_canonical('Duration') == 'Quantity'
        assert registry.resolve_to_canonical('string') == 'string'
        assert registry.resolve_to_canonical('Quantity') == 'Quantity'
        assert registry.resolve_to_canonical('unknown-type') is None

    def test_get_validator(self, registry):
        """Test getting type validators"""
        # Primitive type
        validator = registry.get_validator('boolean')
        assert validator is not None
        assert isinstance(validator, FHIRTypeValidator)

        # Complex type
        validator = registry.get_validator('Quantity')
        assert validator is not None

        # Via alias
        validator = registry.get_validator('bool')
        assert validator is not None

        # Unknown type
        validator = registry.get_validator('UnknownType')
        assert validator is None

    def test_get_type_metadata(self, registry):
        """Test getting type metadata"""
        # Primitive type
        metadata = registry.get_type_metadata('boolean')
        assert metadata is not None
        assert metadata['is_primitive'] is True
        assert metadata['is_complex'] is False
        assert metadata['is_resource'] is False
        assert 'description' in metadata

        # Complex type
        metadata = registry.get_type_metadata('Quantity')
        assert metadata is not None
        assert metadata['is_primitive'] is False
        assert metadata['is_complex'] is True
        assert metadata['is_resource'] is False

        # Resource type
        metadata = registry.get_type_metadata('Patient')
        assert metadata is not None
        assert metadata['is_primitive'] is False
        assert metadata['is_complex'] is False
        assert metadata['is_resource'] is True

        # Unknown type
        metadata = registry.get_type_metadata('UnknownType')
        assert metadata is None

    def test_is_compatible_type(self, registry):
        """Test type compatibility checking"""
        # Primitive types
        assert registry.is_compatible_type(True, 'boolean') is True
        assert registry.is_compatible_type(42, 'integer') is True
        assert registry.is_compatible_type('test', 'string') is True

        # Wrong types
        assert registry.is_compatible_type('not a number', 'integer') is False

        # Complex types
        quantity = {'value': 10.5, 'unit': 'mg'}
        assert registry.is_compatible_type(quantity, 'Quantity') is True

        invalid_quantity = {'unit': 'mg'}  # Missing required value
        assert registry.is_compatible_type(invalid_quantity, 'Quantity') is False

    def test_convert_value(self, registry):
        """Test value conversion"""
        # Primitive conversions
        assert registry.convert_value('42', 'integer') == 42
        assert registry.convert_value(42, 'string') == '42'
        assert registry.convert_value('true', 'boolean') is True

        # Complex type conversion (should work for valid data)
        quantity = {'value': 10.5, 'unit': 'mg'}
        converted = registry.convert_value(quantity, 'Quantity')
        assert converted == quantity

    def test_register_custom_type(self, registry):
        """Test registering custom types"""
        # Create a custom validator
        custom_validator = PrimitiveTypeValidator(FHIRDataType.STRING)

        # Register custom type
        registry.register_type(
            'CustomType',
            custom_validator,
            metadata={'description': 'Custom test type'},
            aliases=['custom', 'test-type']
        )

        # Test registration worked
        assert registry.is_registered_type('CustomType') is True
        assert registry.is_registered_type('custom') is True
        assert registry.is_registered_type('test-type') is True

        # Test metadata
        metadata = registry.get_type_metadata('CustomType')
        assert metadata is not None
        assert metadata['custom_type'] is True
        assert 'Custom test type' in metadata['description']

        # Test validator
        validator = registry.get_validator('CustomType')
        assert validator is not None
        assert validator == custom_validator

    def test_type_hierarchy(self, registry):
        """Test type hierarchy support"""
        # Test resource hierarchy
        domain_subtypes = registry.get_type_hierarchy('DomainResource')
        assert 'Patient' in domain_subtypes
        assert 'Observation' in domain_subtypes

        # Test subtype checking
        assert registry.is_subtype_of('Patient', 'DomainResource') is True
        assert registry.is_subtype_of('Observation', 'DomainResource') is True
        assert registry.is_subtype_of('Patient', 'Resource') is False  # Not direct

    def test_get_all_type_names(self, registry):
        """Test getting all registered type names"""
        all_types = registry.get_all_type_names()

        assert isinstance(all_types, list)
        assert len(all_types) > 0
        assert 'boolean' in all_types
        assert 'Patient' in all_types
        assert 'bool' in all_types  # Alias
        assert all_types == sorted(all_types)  # Should be sorted

    def test_validate_type_expression(self, registry):
        """Test type expression validation"""
        # Simple types
        assert registry.validate_type_expression('boolean') is True
        assert registry.validate_type_expression('Patient') is True
        assert registry.validate_type_expression('bool') is True  # Alias

        # Unknown type
        assert registry.validate_type_expression('UnknownType') is False


class TestGlobalRegistry:
    """Test global registry functions"""

    def test_get_global_registry(self):
        """Test getting global registry"""
        registry1 = get_type_registry()
        registry2 = get_type_registry()

        # Should return same instance
        assert registry1 is registry2
        assert isinstance(registry1, TypeRegistry)

    def test_register_global_type(self):
        """Test registering type in global registry"""
        # Create custom validator
        validator = PrimitiveTypeValidator(FHIRDataType.STRING)

        # Register globally
        register_global_type(
            'GlobalTestType',
            validator,
            metadata={'test': True},
            aliases=['global-test']
        )

        # Verify registration in global registry
        registry = get_type_registry()
        assert registry.is_registered_type('GlobalTestType') is True
        assert registry.is_registered_type('global-test') is True

    def test_global_validation(self):
        """Test global validation functions"""
        # Test is_valid_type
        assert is_valid_type(True, 'boolean') is True
        assert is_valid_type(42, 'integer') is True
        assert is_valid_type('not a number', 'integer') is False

        # Test convert_to_type
        assert convert_to_type('42', 'integer') == 42
        assert convert_to_type(42, 'string') == '42'


class TestTypeRegistryEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def registry(self):
        return TypeRegistry()

    def test_none_handling(self, registry):
        """Test handling of None values"""
        assert registry.is_compatible_type(None, 'boolean') is True
        assert registry.convert_value(None, 'boolean') is None

    def test_invalid_operations(self, registry):
        """Test invalid operations"""
        # Getting validator for unregistered type
        assert registry.get_validator('UnknownType') is None

        # Getting metadata for unregistered type
        assert registry.get_type_metadata('UnknownType') is None

        # Type hierarchy for unknown type
        assert registry.get_type_hierarchy('UnknownType') == set()

    def test_complex_type_validation(self, registry):
        """Test complex validation scenarios"""
        # Valid CodeableConcept
        concept = {
            'coding': [
                {'system': 'http://loinc.org', 'code': '12345', 'display': 'Test'}
            ],
            'text': 'Test concept'
        }
        assert registry.is_compatible_type(concept, 'CodeableConcept') is True

        # Invalid CodeableConcept (missing both coding and text)
        invalid_concept = {'id': 'test'}
        assert registry.is_compatible_type(invalid_concept, 'CodeableConcept') is False

        # Valid Reference
        reference = {'reference': 'Patient/123', 'display': 'Test Patient'}
        assert registry.is_compatible_type(reference, 'Reference') is True

        # Invalid Reference (missing reference, identifier, and display)
        invalid_reference = {'id': 'test'}
        assert registry.is_compatible_type(invalid_reference, 'Reference') is False

    def test_quantity_validation_edge_cases(self, registry):
        """Test Quantity validation edge cases"""
        # Valid quantity with common unit (no system required)
        quantity1 = {'value': 100, 'code': 'mg'}
        assert registry.is_compatible_type(quantity1, 'Quantity') is True

        # Valid quantity with system
        quantity2 = {'value': 100, 'code': 'mg', 'system': 'http://unitsofmeasure.org'}
        assert registry.is_compatible_type(quantity2, 'Quantity') is True

        # Invalid quantity (coded without system for uncommon unit)
        quantity3 = {'value': 100, 'code': 'unusual-unit'}
        assert registry.is_compatible_type(quantity3, 'Quantity') is False

        # Invalid quantity (non-numeric value)
        quantity4 = {'value': 'not-a-number', 'unit': 'mg'}
        assert registry.is_compatible_type(quantity4, 'Quantity') is False


if __name__ == "__main__":
    pytest.main([__file__])
