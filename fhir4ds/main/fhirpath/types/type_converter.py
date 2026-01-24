"""
FHIR Type Conversion Utilities

This module provides utilities for converting between FHIR types and FHIRPath
evaluation types, with special handling for healthcare-specific type semantics.
"""

from typing import Any, Dict, List, Optional, Union, Type, cast
from datetime import datetime, date, time
from decimal import Decimal
import logging
import re

from .fhir_types import FHIRDataType, FHIRTypeSystem
from .type_registry import get_type_registry
from ..exceptions import (
    FHIRPathTypeValidationError, FHIRPathTypeConversionError,
    FHIRPathTypeMismatchError, ErrorContext, ErrorSeverity,
    build_error_context
)


class FHIRTypeConverter:
    """
    FHIR Type Converter for healthcare-specific type handling

    Provides specialized conversion utilities for FHIR types with healthcare
    domain knowledge and validation rules.
    """

    def __init__(self, type_system: Optional[FHIRTypeSystem] = None):
        self.type_system = type_system or FHIRTypeSystem()
        self.type_registry = get_type_registry()
        self.logger = logging.getLogger(__name__)

        # Healthcare-specific validation patterns
        self._validation_patterns = {
            'oid': re.compile(r'^urn:oid:[0-2](\.[1-9]\d*)*$'),
            'uuid': re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
            'uri': re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:'),
            'url': re.compile(r'^https?://[^\s]+'),  # Must have content after protocol
            'id': re.compile(r'^[A-Za-z0-9\-\.]{1,64}$'),
            'code': re.compile(r'^[^\s]+(\s[^\s]+)*$')
        }

    def convert_to_fhir_path_type(self, value: Any, source_type: str) -> Any:
        """
        Convert FHIR value to FHIRPath evaluation type

        Args:
            value: FHIR value to convert
            source_type: Source FHIR type name

        Returns:
            Value converted for FHIRPath evaluation
        """
        if value is None:
            return None

        try:
            # Handle collections
            if isinstance(value, list):
                return [self.convert_to_fhir_path_type(item, source_type) for item in value]

            # Get canonical type name
            canonical_type = self.type_registry.get_canonical_name(source_type)

            # Primitive type conversions
            # NOTE: Pass ORIGINAL source_type, not canonical_type, to preserve
            # constrained type semantics (e.g., 'date' stays 'date', not 'dateTime')
            if self.type_system.is_primitive_type(canonical_type):
                return self._convert_primitive_to_fhirpath(value, source_type)

            # Complex type conversions
            elif self.type_system.is_complex_type(canonical_type):
                return self._convert_complex_to_fhirpath(value, canonical_type)

            # Resource type conversions
            elif self.type_system.is_resource_type(canonical_type):
                return self._convert_resource_to_fhirpath(value, canonical_type)

            # Default - return as-is
            return value

        except Exception as e:
            self.logger.warning(f"Failed to convert {source_type} to FHIRPath type: {e}")
            return value

    def convert_from_fhir_path_type(self, value: Any, target_type: str) -> Any:
        """
        Convert FHIRPath evaluation result to FHIR type

        Args:
            value: FHIRPath evaluation result
            target_type: Target FHIR type name

        Returns:
            Value converted to FHIR type
        """
        if value is None:
            return None

        try:
            # Handle collections
            if isinstance(value, list):
                return [self.convert_from_fhir_path_type(item, target_type) for item in value]

            # Get canonical type name
            canonical_type = self.type_registry.get_canonical_name(target_type)

            # Use type system for conversion
            return self.type_system.convert_to_type(value, canonical_type)

        except Exception as e:
            self.logger.warning(f"Failed to convert from FHIRPath type to {target_type}: {e}")
            return value

    def _convert_primitive_to_fhirpath(self, value: Any, fhir_type: str) -> Any:
        """Convert FHIR primitive to FHIRPath type"""
        # Normalize for case-insensitive comparison
        fhir_type_lower = fhir_type.lower()

        if fhir_type_lower == 'boolean':
            return self._ensure_boolean(value)
        elif fhir_type_lower in ('integer', 'integer64', 'unsignedint', 'positiveint'):
            return self._ensure_integer(value)
        elif fhir_type_lower == 'decimal':
            return self._ensure_decimal(value)
        elif fhir_type_lower in ('string', 'code', 'id', 'markdown', 'uri', 'url', 'canonical', 'oid', 'uuid'):
            return self._ensure_string(value)
        elif fhir_type_lower == 'date':
            return self._ensure_date(value)
        elif fhir_type_lower in ('datetime', 'instant'):
            return self._ensure_datetime(value)
        elif fhir_type_lower == 'time':
            return self._ensure_time(value)
        else:
            return value

    def _convert_complex_to_fhirpath(self, value: Any, fhir_type: str) -> Any:
        """Convert FHIR complex type to FHIRPath type"""
        if not isinstance(value, dict):
            return value

        if fhir_type == 'Quantity':
            return self._convert_quantity_to_fhirpath(value)
        elif fhir_type == 'Coding':
            return self._convert_coding_to_fhirpath(value)
        elif fhir_type == 'CodeableConcept':
            return self._convert_codeable_concept_to_fhirpath(value)
        elif fhir_type == 'Reference':
            return self._convert_reference_to_fhirpath(value)
        elif fhir_type == 'Identifier':
            return self._convert_identifier_to_fhirpath(value)
        elif fhir_type == 'Period':
            return self._convert_period_to_fhirpath(value)
        elif fhir_type == 'Range':
            return self._convert_range_to_fhirpath(value)
        else:
            return value

    def _convert_resource_to_fhirpath(self, value: Any, fhir_type: str) -> Any:
        """Convert FHIR resource to FHIRPath type"""
        # Resources are typically handled as-is in FHIRPath
        return value

    def _ensure_boolean(self, value: Any) -> bool:
        """Ensure value is a boolean"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return bool(value)

    def _ensure_integer(self, value: Any) -> int:
        """Ensure value is an integer"""
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return int(value)
        elif isinstance(value, str):
            return int(value)
        else:
            return int(value)

    def _ensure_decimal(self, value: Any) -> Union[float, Decimal]:
        """Ensure value is a decimal"""
        if isinstance(value, (float, Decimal)):
            return value
        elif isinstance(value, int):
            return float(value)
        elif isinstance(value, str):
            return Decimal(value)
        else:
            return float(value)

    def _ensure_string(self, value: Any) -> str:
        """Ensure value is a string"""
        if isinstance(value, str):
            return value
        else:
            return str(value)

    def _ensure_date(self, value: Any) -> date:
        """Ensure value is a date"""
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, str):
            return self._parse_fhir_date(value)
        else:
            raise ValueError(f"Cannot convert {type(value)} to date")

    def _ensure_datetime(self, value: Any) -> datetime:
        """Ensure value is a datetime"""
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            return self._parse_fhir_datetime(value)
        else:
            raise ValueError(f"Cannot convert {type(value)} to datetime")

    def _ensure_time(self, value: Any) -> time:
        """Ensure value is a time"""
        if isinstance(value, time):
            return value
        elif isinstance(value, str):
            return self._parse_fhir_time(value)
        else:
            raise ValueError(f"Cannot convert {type(value)} to time")

    def _parse_fhir_date(self, date_str: str) -> date:
        """Parse FHIR date string"""
        if re.match(r'^\d{4}$', date_str):
            return date(int(date_str), 1, 1)
        elif re.match(r'^\d{4}-\d{2}$', date_str):
            year, month = map(int, date_str.split('-'))
            return date(year, month, 1)
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            raise ValueError(f"Invalid FHIR date format: {date_str}")

    def _parse_fhir_datetime(self, datetime_str: str) -> datetime:
        """Parse FHIR datetime string"""
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid FHIR datetime format: {datetime_str}")

    def _parse_fhir_time(self, time_str: str) -> time:
        """Parse FHIR time string"""
        formats = [
            '%H:%M:%S',
            '%H:%M:%S.%f'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt).time()
            except ValueError:
                continue

        raise ValueError(f"Invalid FHIR time format: {time_str}")

    def _convert_quantity_to_fhirpath(self, quantity: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Quantity to FHIRPath representation"""
        result = {}

        # Extract and convert value
        if 'value' in quantity:
            result['value'] = self._ensure_decimal(quantity['value'])

        # Extract unit information
        if 'unit' in quantity:
            result['unit'] = self._ensure_string(quantity['unit'])

        if 'system' in quantity:
            result['system'] = self._ensure_string(quantity['system'])

        if 'code' in quantity:
            result['code'] = self._ensure_string(quantity['code'])

        return result

    def _convert_coding_to_fhirpath(self, coding: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Coding to FHIRPath representation"""
        result = {}

        if 'system' in coding:
            result['system'] = self._ensure_string(coding['system'])

        if 'version' in coding:
            result['version'] = self._ensure_string(coding['version'])

        if 'code' in coding:
            result['code'] = self._ensure_string(coding['code'])

        if 'display' in coding:
            result['display'] = self._ensure_string(coding['display'])

        if 'userSelected' in coding:
            result['userSelected'] = self._ensure_boolean(coding['userSelected'])

        return result

    def _convert_codeable_concept_to_fhirpath(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CodeableConcept to FHIRPath representation"""
        result = {}

        if 'coding' in concept:
            result['coding'] = [
                self._convert_coding_to_fhirpath(coding)
                for coding in concept['coding']
                if isinstance(coding, dict)
            ]

        if 'text' in concept:
            result['text'] = self._ensure_string(concept['text'])

        return result

    def _convert_reference_to_fhirpath(self, reference: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Reference to FHIRPath representation"""
        result = {}

        if 'reference' in reference:
            result['reference'] = self._ensure_string(reference['reference'])

        if 'type' in reference:
            result['type'] = self._ensure_string(reference['type'])

        if 'identifier' in reference:
            result['identifier'] = self._convert_identifier_to_fhirpath(reference['identifier'])

        if 'display' in reference:
            result['display'] = self._ensure_string(reference['display'])

        return result

    def _convert_identifier_to_fhirpath(self, identifier: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Identifier to FHIRPath representation"""
        result = {}

        if 'use' in identifier:
            result['use'] = self._ensure_string(identifier['use'])

        if 'type' in identifier:
            result['type'] = self._convert_codeable_concept_to_fhirpath(identifier['type'])

        if 'system' in identifier:
            result['system'] = self._ensure_string(identifier['system'])

        if 'value' in identifier:
            result['value'] = self._ensure_string(identifier['value'])

        if 'period' in identifier:
            result['period'] = self._convert_period_to_fhirpath(identifier['period'])

        if 'assigner' in identifier:
            result['assigner'] = self._convert_reference_to_fhirpath(identifier['assigner'])

        return result

    def _convert_period_to_fhirpath(self, period: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Period to FHIRPath representation"""
        result = {}

        if 'start' in period:
            result['start'] = self._ensure_datetime(period['start'])

        if 'end' in period:
            result['end'] = self._ensure_datetime(period['end'])

        return result

    def _convert_range_to_fhirpath(self, range_val: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Range to FHIRPath representation"""
        result = {}

        if 'low' in range_val:
            result['low'] = self._convert_quantity_to_fhirpath(range_val['low'])

        if 'high' in range_val:
            result['high'] = self._convert_quantity_to_fhirpath(range_val['high'])

        return result

    def validate_healthcare_constraints(self, value: Any, fhir_type: str,
                                         raise_on_error: bool = False) -> bool:
        """
        Validate healthcare-specific constraints for FHIR types

        Args:
            value: Value to validate
            fhir_type: FHIR type name
            raise_on_error: Whether to raise exceptions on validation failure

        Returns:
            True if value meets healthcare constraints

        Raises:
            FHIRPathTypeValidationError: If validation fails and raise_on_error is True
        """
        if value is None:
            return True

        try:
            # Normalize type name for comparison (case-insensitive)
            fhir_type_lower = fhir_type.lower()

            # Apply healthcare-specific validation
            # NOTE: Check ORIGINAL type name (not canonical) for constrained types
            # because uuid, oid, url, etc. are constrained versions of uri/string
            validation_result = None
            error_details = None

            if fhir_type_lower == 'oid':
                validation_result = self._validate_oid(value)
                error_details = "OID must follow pattern 'urn:oid:' followed by numeric identifiers"
            elif fhir_type_lower == 'uuid':
                validation_result = self._validate_uuid(value)
                error_details = "UUID must be in format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            elif fhir_type_lower == 'url':
                validation_result = self._validate_url(value)
                error_details = "URL must be valid HTTP or HTTPS URL"
            elif fhir_type_lower == 'uri':
                validation_result = self._validate_uri(value)
                error_details = "URI must have valid scheme (e.g., http:, fhir:, urn:)"
            elif fhir_type_lower == 'id':
                validation_result = self._validate_id(value)
                error_details = "ID must contain only alphanumeric characters, hyphens, and periods (max 64 chars)"
            elif fhir_type_lower == 'code':
                validation_result = self._validate_code(value)
                error_details = "Code must not contain leading/trailing whitespace or multiple consecutive spaces"
            elif fhir_type_lower == 'positiveint':
                validation_result = self._validate_positive_int(value)
                error_details = "Value must be a positive integer (greater than 0)"
            elif fhir_type_lower == 'unsignedint':
                validation_result = self._validate_unsigned_int(value)
                error_details = "Value must be an unsigned integer (0 or greater)"
            else:
                # No specific validation for this type
                validation_result = True

            # Handle validation failure
            if validation_result is False and raise_on_error:
                error_context = build_error_context(
                    severity=ErrorSeverity.ERROR,
                    category="TYPE_VALIDATION",
                    operation="healthcare_constraint_validation"
                )
                raise FHIRPathTypeValidationError(
                    f"Healthcare constraint validation failed for {fhir_type}: {error_details}. Value: {value}",
                    expected_type=fhir_type,
                    actual_type=type(value).__name__,
                    value=value,
                    error_context=error_context
                )

            return validation_result if validation_result is not None else True

        except FHIRPathTypeValidationError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            error_context = build_error_context(
                severity=ErrorSeverity.ERROR,
                category="TYPE_VALIDATION_ERROR",
                operation="healthcare_constraint_validation"
            )

            if raise_on_error:
                raise FHIRPathTypeValidationError(
                    f"Unexpected error during healthcare constraint validation for {fhir_type}: {e}",
                    expected_type=fhir_type,
                    actual_type=type(value).__name__,
                    value=value,
                    error_context=error_context
                ) from e
            else:
                self.logger.warning(f"Healthcare constraint validation failed for {fhir_type}: {e}")
                return False

    def _validate_oid(self, value: str) -> bool:
        """Validate OID format"""
        return isinstance(value, str) and bool(self._validation_patterns['oid'].match(value))

    def _validate_uuid(self, value: str) -> bool:
        """Validate UUID format"""
        return isinstance(value, str) and bool(self._validation_patterns['uuid'].match(value))

    def _validate_uri(self, value: str) -> bool:
        """Validate URI format"""
        return isinstance(value, str) and bool(self._validation_patterns['uri'].match(value))

    def _validate_url(self, value: str) -> bool:
        """Validate URL format"""
        return isinstance(value, str) and bool(self._validation_patterns['url'].match(value))

    def _validate_id(self, value: str) -> bool:
        """Validate FHIR id format"""
        return isinstance(value, str) and bool(self._validation_patterns['id'].match(value))

    def _validate_code(self, value: str) -> bool:
        """Validate FHIR code format"""
        return isinstance(value, str) and bool(self._validation_patterns['code'].match(value))

    def _validate_positive_int(self, value: int) -> bool:
        """Validate positive integer"""
        # Accept string representations that can be converted to positive int
        if isinstance(value, str):
            try:
                int_val = int(value)
                return int_val > 0
            except (ValueError, TypeError):
                return False
        return isinstance(value, int) and value > 0

    def _validate_unsigned_int(self, value: int) -> bool:
        """Validate unsigned integer"""
        return isinstance(value, int) and value >= 0

    def get_conversion_info(self, source_type: str, target_type: str) -> Dict[str, Any]:
        """
        Get information about type conversion

        Args:
            source_type: Source type name
            target_type: Target type name

        Returns:
            Conversion information
        """
        return {
            'source_type': source_type,
            'target_type': target_type,
            'source_canonical': self.type_registry.get_canonical_name(source_type),
            'target_canonical': self.type_registry.get_canonical_name(target_type),
            'conversion_possible': True,  # Could implement more sophisticated checking
            'requires_validation': target_type in ['oid', 'uuid', 'uri', 'url', 'id', 'code'],
            'lossy_conversion': self._is_lossy_conversion(source_type, target_type)
        }

    def _is_lossy_conversion(self, source_type: str, target_type: str) -> bool:
        """Check if conversion might be lossy"""
        # Examples of potentially lossy conversions
        lossy_pairs = [
            ('decimal', 'integer'),
            ('dateTime', 'date'),
            ('integer64', 'integer'),
        ]

        source_canonical = self.type_registry.get_canonical_name(source_type)
        target_canonical = self.type_registry.get_canonical_name(target_type)

        return (source_canonical, target_canonical) in lossy_pairs


# Global converter instance
_global_converter: Optional[FHIRTypeConverter] = None


def get_type_converter() -> FHIRTypeConverter:
    """
    Get the global type converter instance

    Returns:
        Global FHIRTypeConverter instance
    """
    global _global_converter
    if _global_converter is None:
        _global_converter = FHIRTypeConverter()
    return _global_converter


def convert_to_fhirpath_type(value: Any, source_type: str) -> Any:
    """
    Convert FHIR value to FHIRPath type using global converter

    Args:
        value: FHIR value to convert
        source_type: Source FHIR type name

    Returns:
        Value converted for FHIRPath evaluation
    """
    converter = get_type_converter()
    return converter.convert_to_fhir_path_type(value, source_type)


def convert_from_fhirpath_type(value: Any, target_type: str) -> Any:
    """
    Convert FHIRPath result to FHIR type using global converter

    Args:
        value: FHIRPath evaluation result
        target_type: Target FHIR type name

    Returns:
        Value converted to FHIR type
    """
    converter = get_type_converter()
    return converter.convert_from_fhir_path_type(value, target_type)


def validate_healthcare_constraints(value: Any, fhir_type: str) -> bool:
    """
    Validate healthcare constraints using global converter

    Args:
        value: Value to validate
        fhir_type: FHIR type name

    Returns:
        True if value meets healthcare constraints
    """
    converter = get_type_converter()
    return converter.validate_healthcare_constraints(value, fhir_type)