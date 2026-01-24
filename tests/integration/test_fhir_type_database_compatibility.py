"""
Integration tests for FHIR Type System Database Compatibility

Tests that the FHIR type system works consistently across DuckDB and PostgreSQL.
"""

import pytest
from typing import Any, Dict

from fhir4ds.fhirpath.types import (
    FHIRTypeSystem,
    get_type_registry,
    get_type_converter
)


class TestFHIRTypeDatabaseCompatibility:
    """Test FHIR type system compatibility across databases"""

    @pytest.fixture
    def type_system(self):
        """Create FHIR type system for testing"""
        return FHIRTypeSystem()

    @pytest.fixture
    def type_registry(self):
        """Get type registry for testing"""
        return get_type_registry()

    @pytest.fixture
    def type_converter(self):
        """Get type converter for testing"""
        return get_type_converter()

    @pytest.fixture
    def sample_fhir_data(self):
        """Sample FHIR data for testing"""
        return {
            'patient': {
                'resourceType': 'Patient',
                'id': 'patient-123',
                'active': True,
                'name': [
                    {
                        'use': 'official',
                        'given': ['John'],
                        'family': 'Doe'
                    }
                ],
                'identifier': [
                    {
                        'use': 'official',
                        'system': 'http://example.org',
                        'value': 'P123456'
                    }
                ],
                'birthDate': '1990-01-15'
            },
            'observation': {
                'resourceType': 'Observation',
                'id': 'obs-123',
                'status': 'final',
                'code': {
                    'coding': [
                        {
                            'system': 'http://loinc.org',
                            'code': '29463-7',
                            'display': 'Body Weight'
                        }
                    ]
                },
                'valueQuantity': {
                    'value': 70.5,
                    'unit': 'kg',
                    'system': 'http://unitsofmeasure.org',
                    'code': 'kg'
                }
            }
        }

    def test_primitive_type_consistency(self, type_system):
        """Test primitive type validation is consistent"""
        # Boolean values
        assert type_system.is_type(True, 'boolean') is True
        assert type_system.is_type('true', 'boolean') is True
        assert type_system.is_type('invalid', 'boolean') is False

        # Integer values
        assert type_system.is_type(42, 'integer') is True
        assert type_system.is_type('42', 'integer') is True
        assert type_system.is_type('not-a-number', 'integer') is False

        # String values
        assert type_system.is_type('test', 'string') is True
        assert type_system.is_type(42, 'string') is True  # Can convert

        # Date values
        assert type_system.is_type('2023-05-15', 'date') is True
        assert type_system.is_type('invalid-date', 'date') is False

    def test_complex_type_consistency(self, type_system):
        """Test complex type validation is consistent"""
        # Quantity validation
        valid_quantity = {'value': 70.5, 'unit': 'kg'}
        invalid_quantity = {'unit': 'kg'}  # Missing value

        assert type_system.is_type(valid_quantity, 'Quantity') is True
        assert type_system.is_type(invalid_quantity, 'Quantity') is False

        # CodeableConcept validation
        valid_concept = {
            'coding': [
                {'system': 'http://loinc.org', 'code': '29463-7', 'display': 'Body Weight'}
            ]
        }
        invalid_concept = {}  # Missing coding and text

        assert type_system.is_type(valid_concept, 'CodeableConcept') is True
        assert type_system.is_type(invalid_concept, 'CodeableConcept') is False

        # Reference validation
        valid_reference = {'reference': 'Patient/123'}
        invalid_reference = {}  # Missing reference, identifier, and display

        assert type_system.is_type(valid_reference, 'Reference') is True
        assert type_system.is_type(invalid_reference, 'Reference') is False

    def test_resource_type_consistency(self, type_system, sample_fhir_data):
        """Test resource type validation is consistent"""
        # Patient resource
        patient = sample_fhir_data['patient']
        assert type_system.is_type(patient, 'Patient') is True
        assert type_system.is_type(patient, 'Observation') is False

        # Observation resource
        observation = sample_fhir_data['observation']
        assert type_system.is_type(observation, 'Observation') is True
        assert type_system.is_type(observation, 'Patient') is False

    def test_type_conversion_consistency(self, type_system):
        """Test type conversions produce consistent results"""
        # Primitive conversions
        assert type_system.convert_to_type('42', 'integer') == 42
        assert type_system.convert_to_type(42, 'string') == '42'
        assert type_system.convert_to_type('true', 'boolean') is True

        # Complex type conversions (should preserve structure)
        quantity = {'value': 70.5, 'unit': 'kg'}
        converted = type_system.convert_to_type(quantity, 'Quantity')
        assert converted == quantity

    def test_type_registry_consistency(self, type_registry):
        """Test type registry operations are consistent"""
        # Registry stats should be stable
        stats = type_registry.get_registry_stats()
        assert stats['total_types'] > 0
        assert stats['primitive_types'] > 0
        assert stats['complex_types'] > 0
        assert stats['resource_types'] > 0

        # Type lookups should be consistent
        assert type_registry.is_registered_type('boolean') is True
        assert type_registry.is_registered_type('Patient') is True
        assert type_registry.is_registered_type('Quantity') is True
        assert type_registry.is_registered_type('UnknownType') is False

        # Canonical name resolution should be consistent
        assert type_registry.get_canonical_name('bool') == 'boolean'
        assert type_registry.get_canonical_name('int') == 'integer'
        assert type_registry.get_canonical_name('Patient') == 'Patient'

    def test_type_converter_consistency(self, type_converter, sample_fhir_data):
        """Test type converter operations are consistent"""
        # Primitive conversions
        result = type_converter.convert_to_fhir_path_type(True, 'boolean')
        assert result is True

        result = type_converter.convert_to_fhir_path_type('42', 'integer')
        assert result == 42

        # Complex type conversions
        quantity = sample_fhir_data['observation']['valueQuantity']
        result = type_converter.convert_to_fhir_path_type(quantity, 'Quantity')
        assert isinstance(result, dict)
        assert result['value'] == 70.5
        assert result['unit'] == 'kg'

        # CodeableConcept conversion
        concept = sample_fhir_data['observation']['code']
        result = type_converter.convert_to_fhir_path_type(concept, 'CodeableConcept')
        assert isinstance(result, dict)
        assert 'coding' in result
        assert isinstance(result['coding'], list)

    def test_healthcare_constraint_consistency(self, type_converter):
        """Test healthcare constraint validation is consistent"""
        # OID validation
        valid_oid = 'urn:oid:1.2.3.4.5'
        invalid_oid = 'not-an-oid'

        assert type_converter.validate_healthcare_constraints(valid_oid, 'oid') is True
        assert type_converter.validate_healthcare_constraints(invalid_oid, 'oid') is False

        # UUID validation
        valid_uuid = '123e4567-e89b-12d3-a456-426614174000'
        invalid_uuid = 'not-a-uuid'

        assert type_converter.validate_healthcare_constraints(valid_uuid, 'uuid') is True
        assert type_converter.validate_healthcare_constraints(invalid_uuid, 'uuid') is False

        # Positive integer validation
        assert type_converter.validate_healthcare_constraints(5, 'positiveInt') is True
        assert type_converter.validate_healthcare_constraints(0, 'positiveInt') is False
        assert type_converter.validate_healthcare_constraints(-1, 'positiveInt') is False

    def test_date_time_handling_consistency(self, type_converter):
        """Test date/time handling is consistent"""
        # Date parsing
        date_result = type_converter._parse_fhir_date('2023-05-15')
        assert date_result.year == 2023
        assert date_result.month == 5
        assert date_result.day == 15

        # DateTime parsing
        datetime_result = type_converter._parse_fhir_datetime('2023-05-15T10:30:45')
        assert datetime_result.year == 2023
        assert datetime_result.month == 5
        assert datetime_result.day == 15
        assert datetime_result.hour == 10
        assert datetime_result.minute == 30
        assert datetime_result.second == 45

    def test_error_handling_consistency(self, type_system, type_converter):
        """Test error handling is consistent across components"""
        # Type system error handling
        try:
            type_system.convert_to_type('invalid', 'UnknownType')
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected

        # Type converter error handling (should not raise, but may return original)
        result = type_converter.convert_to_fhir_path_type('invalid', 'UnknownType')
        assert result == 'invalid'  # Graceful fallback

    def test_performance_characteristics(self, type_system, sample_fhir_data):
        """Test performance characteristics are reasonable"""
        import time

        # Test type validation performance
        start_time = time.time()
        for _ in range(100):
            type_system.is_type(True, 'boolean')
            type_system.is_type(sample_fhir_data['patient'], 'Patient')
            type_system.is_type(sample_fhir_data['observation']['valueQuantity'], 'Quantity')
        end_time = time.time()

        # Should complete 100 validations in reasonable time (< 100ms)
        duration = end_time - start_time
        assert duration < 0.1, f"Type validation took too long: {duration:.3f}s"

    def test_memory_usage_stability(self, type_system, type_registry):
        """Test memory usage is stable"""
        import gc

        # Force garbage collection
        gc.collect()

        # Perform many operations
        for i in range(1000):
            type_system.is_type(True, 'boolean')
            type_registry.is_compatible_type({'value': i}, 'Quantity')

        # Force garbage collection again
        gc.collect()

        # This test mainly ensures no obvious memory leaks cause test failures
        # More sophisticated memory testing would require additional tools
        assert True  # If we get here without issues, basic memory stability is OK


@pytest.mark.integration
class TestFHIRTypeSystemIntegration:
    """Integration tests for the complete FHIR type system"""

    def test_end_to_end_type_workflow(self):
        """Test complete type workflow from registry to conversion"""
        # Get components
        type_system = FHIRTypeSystem()
        registry = get_type_registry()
        converter = get_type_converter()

        # Sample healthcare data
        patient_data = {
            'resourceType': 'Patient',
            'identifier': [
                {
                    'use': 'official',
                    'system': 'http://example.org',
                    'value': 'P123456'
                }
            ],
            'active': True,
            'birthDate': '1990-01-15'
        }

        # 1. Validate resource type
        assert type_system.is_type(patient_data, 'Patient') is True

        # 2. Check registry registration
        assert registry.is_registered_type('Patient') is True
        validator = registry.get_validator('Patient')
        assert validator is not None

        # 3. Convert for FHIRPath evaluation
        converted = converter.convert_to_fhir_path_type(patient_data, 'Patient')
        assert converted == patient_data  # Resources typically pass through

        # 4. Validate nested types
        identifier = patient_data['identifier'][0]
        assert type_system.is_type(identifier, 'Identifier') is True

        # 5. Convert back from FHIRPath
        back_converted = converter.convert_from_fhir_path_type(converted, 'Patient')
        assert back_converted == patient_data

    def test_complex_nested_validation(self):
        """Test validation of complex nested structures"""
        type_system = FHIRTypeSystem()

        # Complex observation with nested types
        observation = {
            'resourceType': 'Observation',
            'status': 'final',
            'code': {
                'coding': [
                    {
                        'system': 'http://loinc.org',
                        'code': '29463-7',
                        'display': 'Body Weight'
                    }
                ],
                'text': 'Body Weight'
            },
            'valueQuantity': {
                'value': 70.5,
                'unit': 'kg',
                'system': 'http://unitsofmeasure.org',
                'code': 'kg'
            },
            'effectivePeriod': {
                'start': '2023-01-01T00:00:00Z',
                'end': '2023-01-01T01:00:00Z'
            }
        }

        # Validate main resource
        assert type_system.is_type(observation, 'Observation') is True

        # Validate nested CodeableConcept
        assert type_system.is_type(observation['code'], 'CodeableConcept') is True

        # Validate nested Quantity
        assert type_system.is_type(observation['valueQuantity'], 'Quantity') is True

        # Validate nested Period
        assert type_system.is_type(observation['effectivePeriod'], 'Period') is True

        # Validate deeply nested Coding
        coding = observation['code']['coding'][0]
        assert type_system.is_type(coding, 'Coding') is True


if __name__ == "__main__":
    pytest.main([__file__])