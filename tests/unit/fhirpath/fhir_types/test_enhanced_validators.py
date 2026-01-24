"""
Unit tests for Enhanced FHIR Complex Type Validators

Tests the specialized validators for FHIR complex types.
"""

import pytest
from typing import Any

from fhir4ds.fhirpath.types.fhir_types import (
    QuantityValidator,
    CodingValidator,
    CodeableConceptValidator,
    ReferenceValidator,
    IdentifierValidator,
    PeriodValidator,
    RangeValidator,
    RatioValidator,
    AttachmentValidator,
    AnnotationValidator
)


class TestQuantityValidator:
    """Test Quantity validator"""

    @pytest.fixture
    def validator(self):
        return QuantityValidator()

    def test_valid_quantities(self, validator):
        """Test valid Quantity structures"""
        # Basic quantity
        quantity1 = {'value': 10.5, 'unit': 'mg'}
        assert validator.is_valid(quantity1) is True

        # Quantity with system and code
        quantity2 = {'value': 100, 'system': 'http://unitsofmeasure.org', 'code': 'mg'}
        assert validator.is_valid(quantity2) is True

        # Quantity with common unit (no system required)
        quantity3 = {'value': 75, 'code': 'kg'}
        assert validator.is_valid(quantity3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_quantities(self, validator):
        """Test invalid Quantity structures"""
        # Missing value
        quantity1 = {'unit': 'mg'}
        assert validator.is_valid(quantity1) is False

        # Non-numeric value
        quantity2 = {'value': 'not-a-number', 'unit': 'mg'}
        assert validator.is_valid(quantity2) is False

        # Code without system for uncommon unit
        quantity3 = {'value': 100, 'code': 'unusual-unit'}
        assert validator.is_valid(quantity3) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False

    def test_conversion(self, validator):
        """Test Quantity conversion"""
        quantity = {'value': 10.5, 'unit': 'mg'}
        result = validator.convert(quantity)
        assert result == quantity

        assert validator.convert(None) is None

        with pytest.raises(ValueError):
            validator.convert('not-a-dict')


class TestCodingValidator:
    """Test Coding validator"""

    @pytest.fixture
    def validator(self):
        return CodingValidator()

    def test_valid_codings(self, validator):
        """Test valid Coding structures"""
        # Coding with code and display
        coding1 = {'code': '12345', 'display': 'Test Code'}
        assert validator.is_valid(coding1) is True

        # Coding with system, code, and display
        coding2 = {
            'system': 'http://loinc.org',
            'code': '12345',
            'display': 'Test Code'
        }
        assert validator.is_valid(coding2) is True

        # Coding with only display
        coding3 = {'display': 'Display only'}
        assert validator.is_valid(coding3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_codings(self, validator):
        """Test invalid Coding structures"""
        # Missing both code and display
        coding1 = {'system': 'http://loinc.org'}
        assert validator.is_valid(coding1) is False

        # Non-string code
        coding2 = {'code': 12345, 'display': 'Test'}
        assert validator.is_valid(coding2) is False

        # Non-string system
        coding3 = {'system': 123, 'code': 'test'}
        assert validator.is_valid(coding3) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestCodeableConceptValidator:
    """Test CodeableConcept validator"""

    @pytest.fixture
    def validator(self):
        return CodeableConceptValidator()

    def test_valid_concepts(self, validator):
        """Test valid CodeableConcept structures"""
        # Concept with coding array
        concept1 = {
            'coding': [
                {'system': 'http://loinc.org', 'code': '12345', 'display': 'Test'}
            ]
        }
        assert validator.is_valid(concept1) is True

        # Concept with text only
        concept2 = {'text': 'Text description'}
        assert validator.is_valid(concept2) is True

        # Concept with both coding and text
        concept3 = {
            'coding': [
                {'code': '12345', 'display': 'Test'}
            ],
            'text': 'Text description'
        }
        assert validator.is_valid(concept3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_concepts(self, validator):
        """Test invalid CodeableConcept structures"""
        # Missing both coding and text
        concept1 = {'id': 'test-id'}
        assert validator.is_valid(concept1) is False

        # Invalid coding array (not a list)
        concept2 = {'coding': 'not-a-list'}
        assert validator.is_valid(concept2) is False

        # Invalid coding in array
        concept3 = {
            'coding': [
                {'system': 'http://loinc.org'}  # Missing code and display
            ]
        }
        assert validator.is_valid(concept3) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestReferenceValidator:
    """Test Reference validator"""

    @pytest.fixture
    def validator(self):
        return ReferenceValidator()

    def test_valid_references(self, validator):
        """Test valid Reference structures"""
        # Reference with reference string
        ref1 = {'reference': 'Patient/123'}
        assert validator.is_valid(ref1) is True

        # Reference with identifier
        ref2 = {
            'identifier': {
                'system': 'http://example.org',
                'value': 'P123'
            }
        }
        assert validator.is_valid(ref2) is True

        # Reference with display only
        ref3 = {'display': 'Test Patient'}
        assert validator.is_valid(ref3) is True

        # Complete reference
        ref4 = {
            'reference': 'Patient/123',
            'type': 'Patient',
            'display': 'Test Patient'
        }
        assert validator.is_valid(ref4) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_references(self, validator):
        """Test invalid Reference structures"""
        # Missing reference, identifier, and display
        ref1 = {'id': 'test-id'}
        assert validator.is_valid(ref1) is False

        # Non-string reference
        ref2 = {'reference': 123}
        assert validator.is_valid(ref2) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestIdentifierValidator:
    """Test Identifier validator"""

    @pytest.fixture
    def validator(self):
        return IdentifierValidator()

    def test_valid_identifiers(self, validator):
        """Test valid Identifier structures"""
        # Basic identifier
        id1 = {'value': 'P123456'}
        assert validator.is_valid(id1) is True

        # Identifier with use
        id2 = {'use': 'official', 'value': 'P123456'}
        assert validator.is_valid(id2) is True

        # Complete identifier
        id3 = {
            'use': 'official',
            'system': 'http://example.org',
            'value': 'P123456',
            'type': {
                'coding': [
                    {'code': 'MR', 'display': 'Medical record number'}
                ]
            }
        }
        assert validator.is_valid(id3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_identifiers(self, validator):
        """Test invalid Identifier structures"""
        # Missing value
        id1 = {'system': 'http://example.org'}
        assert validator.is_valid(id1) is False

        # Non-string value
        id2 = {'value': 123456}
        assert validator.is_valid(id2) is False

        # Invalid use
        id3 = {'use': 'invalid-use', 'value': 'P123'}
        assert validator.is_valid(id3) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestPeriodValidator:
    """Test Period validator"""

    @pytest.fixture
    def validator(self):
        return PeriodValidator()

    def test_valid_periods(self, validator):
        """Test valid Period structures"""
        # Period with start and end
        period1 = {
            'start': '2023-01-01T00:00:00',
            'end': '2023-12-31T23:59:59'
        }
        assert validator.is_valid(period1) is True

        # Period with start only
        period2 = {'start': '2023-01-01T00:00:00'}
        assert validator.is_valid(period2) is True

        # Period with end only
        period3 = {'end': '2023-12-31T23:59:59'}
        assert validator.is_valid(period3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_periods(self, validator):
        """Test invalid Period structures"""
        # Missing both start and end
        period1 = {'id': 'test-id'}
        assert validator.is_valid(period1) is False

        # Non-string datetime
        period2 = {'start': 123456}
        assert validator.is_valid(period2) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestRangeValidator:
    """Test Range validator"""

    @pytest.fixture
    def validator(self):
        return RangeValidator()

    def test_valid_ranges(self, validator):
        """Test valid Range structures"""
        # Range with low and high
        range1 = {
            'low': {'value': 10, 'unit': 'mg'},
            'high': {'value': 20, 'unit': 'mg'}
        }
        assert validator.is_valid(range1) is True

        # Range with low only
        range2 = {'low': {'value': 10, 'unit': 'mg'}}
        assert validator.is_valid(range2) is True

        # Range with high only
        range3 = {'high': {'value': 20, 'unit': 'mg'}}
        assert validator.is_valid(range3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_ranges(self, validator):
        """Test invalid Range structures"""
        # Missing both low and high
        range1 = {'id': 'test-id'}
        assert validator.is_valid(range1) is False

        # Invalid quantity in low
        range2 = {'low': {'unit': 'mg'}}  # Missing value
        assert validator.is_valid(range2) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestRatioValidator:
    """Test Ratio validator"""

    @pytest.fixture
    def validator(self):
        return RatioValidator()

    def test_valid_ratios(self, validator):
        """Test valid Ratio structures"""
        # Ratio with numerator and denominator
        ratio1 = {
            'numerator': {'value': 1, 'unit': 'tablet'},
            'denominator': {'value': 1, 'unit': 'day'}
        }
        assert validator.is_valid(ratio1) is True

        # Ratio with numerator only
        ratio2 = {'numerator': {'value': 5, 'unit': 'mg'}}
        assert validator.is_valid(ratio2) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_ratios(self, validator):
        """Test invalid Ratio structures"""
        # Missing both numerator and denominator
        ratio1 = {'id': 'test-id'}
        assert validator.is_valid(ratio1) is False

        # Invalid quantity in numerator
        ratio2 = {'numerator': {'unit': 'mg'}}  # Missing value
        assert validator.is_valid(ratio2) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestAttachmentValidator:
    """Test Attachment validator"""

    @pytest.fixture
    def validator(self):
        return AttachmentValidator()

    def test_valid_attachments(self, validator):
        """Test valid Attachment structures"""
        # Attachment with data
        attachment1 = {
            'contentType': 'text/plain',
            'data': 'SGVsbG8gV29ybGQ='  # Base64 encoded
        }
        assert validator.is_valid(attachment1) is True

        # Attachment with URL
        attachment2 = {
            'contentType': 'image/png',
            'url': 'https://example.org/image.png'
        }
        assert validator.is_valid(attachment2) is True

        # Attachment with title
        attachment3 = {'title': 'Document Title'}
        assert validator.is_valid(attachment3) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_attachments(self, validator):
        """Test invalid Attachment structures"""
        # Missing data, url, and title
        attachment1 = {'contentType': 'text/plain'}
        assert validator.is_valid(attachment1) is False

        # Non-string data
        attachment2 = {'data': 123456}
        assert validator.is_valid(attachment2) is False

        # Non-string url
        attachment3 = {'url': 123456}
        assert validator.is_valid(attachment3) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestAnnotationValidator:
    """Test Annotation validator"""

    @pytest.fixture
    def validator(self):
        return AnnotationValidator()

    def test_valid_annotations(self, validator):
        """Test valid Annotation structures"""
        # Basic annotation
        annotation1 = {'text': 'This is an annotation'}
        assert validator.is_valid(annotation1) is True

        # Annotation with author and time
        annotation2 = {
            'authorString': 'Dr. Smith',
            'time': '2023-05-15T10:30:00Z',
            'text': 'Patient shows improvement'
        }
        assert validator.is_valid(annotation2) is True

        # None value
        assert validator.is_valid(None) is True

    def test_invalid_annotations(self, validator):
        """Test invalid Annotation structures"""
        # Missing text
        annotation1 = {'authorString': 'Dr. Smith'}
        assert validator.is_valid(annotation1) is False

        # Non-string text
        annotation2 = {'text': 123456}
        assert validator.is_valid(annotation2) is False

        # Not a dictionary
        assert validator.is_valid('not-a-dict') is False


class TestValidatorIntegration:
    """Test validator integration with type system"""

    def test_integration_with_type_system(self):
        """Test that validators work with the FHIR type system"""
        from fhir4ds.fhirpath.types.fhir_types import FHIRTypeSystem

        type_system = FHIRTypeSystem()

        # Test Quantity validation through type system
        valid_quantity = {'value': 10.5, 'unit': 'mg'}
        assert type_system.is_type(valid_quantity, 'Quantity') is True

        invalid_quantity = {'unit': 'mg'}
        assert type_system.is_type(invalid_quantity, 'Quantity') is False

        # Test CodeableConcept validation through type system
        valid_concept = {
            'coding': [{'code': '12345', 'display': 'Test'}],
            'text': 'Test concept'
        }
        assert type_system.is_type(valid_concept, 'CodeableConcept') is True

        invalid_concept = {}
        assert type_system.is_type(invalid_concept, 'CodeableConcept') is False

    def test_conversion_through_type_system(self):
        """Test conversion through the type system"""
        from fhir4ds.fhirpath.types.fhir_types import FHIRTypeSystem

        type_system = FHIRTypeSystem()

        # Test quantity conversion
        quantity = {'value': 10.5, 'unit': 'mg'}
        result = type_system.convert_to_type(quantity, 'Quantity')
        assert result == quantity

        # Test reference conversion
        reference = {'reference': 'Patient/123'}
        result = type_system.convert_to_type(reference, 'Reference')
        assert result == reference


if __name__ == "__main__":
    pytest.main([__file__])