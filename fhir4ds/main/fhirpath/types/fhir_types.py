"""
FHIR Type System Integration for FHIRPath Engine

This module provides FHIR type system support for the FHIRPath evaluation engine,
including type checking, conversion, and FHIR-specific data type handling.
"""

from typing import Any, Dict, List, Optional, Union, Type, Set
from enum import Enum
from datetime import datetime, date
import re
from abc import ABC, abstractmethod


class FHIRDataType(Enum):
    """FHIR Data Types enumeration"""
    # Primitive types
    BOOLEAN = "boolean"
    INTEGER = "integer"
    INTEGER64 = "integer64"
    STRING = "string"
    DECIMAL = "decimal"
    URI = "uri"
    URL = "url"
    CANONICAL = "canonical"
    BASE64BINARY = "base64Binary"
    INSTANT = "instant"
    DATE = "date"
    DATETIME = "dateTime"
    TIME = "time"
    CODE = "code"
    OID = "oid"
    ID = "id"
    MARKDOWN = "markdown"
    UNSIGNEDINT = "unsignedInt"
    POSITIVEINT = "positiveInt"
    UUID = "uuid"

    # Complex types
    QUANTITY = "Quantity"
    RATIO = "Ratio"
    RANGE = "Range"
    PERIOD = "Period"
    CODING = "Coding"
    CODEABLECONCEPT = "CodeableConcept"
    IDENTIFIER = "Identifier"
    HUMANNAME = "HumanName"
    ADDRESS = "Address"
    CONTACTPOINT = "ContactPoint"
    REFERENCE = "Reference"
    ATTACHMENT = "Attachment"
    ANNOTATION = "Annotation"

    # Resource types
    RESOURCE = "Resource"
    DOMAINRESOURCE = "DomainResource"
    PATIENT = "Patient"
    OBSERVATION = "Observation"
    ENCOUNTER = "Encounter"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    MEDICATION = "Medication"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"
    DIAGNOSTICREPORT = "DiagnosticReport"
    MEDICATIONREQUEST = "MedicationRequest"

    # Special types
    ANY = "Any"
    COLLECTION = "Collection"


class FHIRTypeValidator(ABC):
    """Abstract base for FHIR type validators"""

    @abstractmethod
    def is_valid(self, value: Any) -> bool:
        """Check if value is valid for this type"""
        pass

    @abstractmethod
    def convert(self, value: Any) -> Any:
        """Convert value to this type"""
        pass


class PrimitiveTypeValidator(FHIRTypeValidator):
    """Validator for FHIR primitive types"""

    def __init__(self, data_type: FHIRDataType):
        self.data_type = data_type

    def is_valid(self, value: Any) -> bool:
        """Check if value is valid for this primitive type"""
        if value is None:
            return True

        try:
            self.convert(value)
            return True
        except (ValueError, TypeError):
            return False

    def convert(self, value: Any) -> Any:
        """Convert value to this primitive type"""
        if value is None:
            return None

        if self.data_type == FHIRDataType.BOOLEAN:
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                if value.lower() in ('true', '1'):
                    return True
                elif value.lower() in ('false', '0'):
                    return False
                else:
                    raise ValueError(f"Cannot convert '{value}' to boolean")
            else:
                return bool(value)

        elif self.data_type in (FHIRDataType.INTEGER, FHIRDataType.INTEGER64):
            if isinstance(value, int):
                return value
            elif isinstance(value, float):
                return int(value)
            elif isinstance(value, str):
                return int(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to integer")

        elif self.data_type == FHIRDataType.DECIMAL:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return float(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to decimal")

        elif self.data_type in (FHIRDataType.STRING, FHIRDataType.CODE, FHIRDataType.ID,
                               FHIRDataType.MARKDOWN, FHIRDataType.URI, FHIRDataType.URL,
                               FHIRDataType.CANONICAL, FHIRDataType.OID, FHIRDataType.UUID):
            return str(value)

        elif self.data_type == FHIRDataType.DATE:
            if isinstance(value, datetime):
                return value.date()
            elif isinstance(value, date):
                return value
            elif isinstance(value, str):
                # Parse FHIR date format (YYYY, YYYY-MM, YYYY-MM-DD)
                return self._parse_fhir_date(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to date")

        elif self.data_type == FHIRDataType.DATETIME:
            if isinstance(value, datetime):
                return value
            elif isinstance(value, str):
                return self._parse_fhir_datetime(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to datetime")

        elif self.data_type == FHIRDataType.INSTANT:
            if isinstance(value, datetime):
                return value
            elif isinstance(value, str):
                return self._parse_fhir_instant(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to instant")

        else:
            # For other types, return as-is
            return value

    def _parse_fhir_date(self, date_str: str) -> date:
        """Parse FHIR date string"""
        # FHIR dates can be YYYY, YYYY-MM, or YYYY-MM-DD
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
        # Simplified parsing - would need more comprehensive implementation
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%S.%f%z'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        raise ValueError(f"Invalid FHIR datetime format: {datetime_str}")

    def _parse_fhir_instant(self, instant_str: str) -> datetime:
        """Parse FHIR instant string"""
        return self._parse_fhir_datetime(instant_str)


class ComplexTypeValidator(FHIRTypeValidator):
    """Validator for FHIR complex types"""

    def __init__(self, data_type: FHIRDataType, required_fields: Optional[Set[str]] = None):
        self.data_type = data_type
        self.required_fields = required_fields or set()

    def is_valid(self, value: Any) -> bool:
        """Check if value is valid for this complex type"""
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Check required fields
        for field in self.required_fields:
            if field not in value:
                return False

        return True

    def convert(self, value: Any) -> Any:
        """Convert value to this complex type"""
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValueError(f"Complex type {self.data_type.value} requires dictionary")

        # Validate required fields
        for field in self.required_fields:
            if field not in value:
                raise ValueError(f"Required field '{field}' missing for type {self.data_type.value}")

        return value


class ResourceTypeValidator(FHIRTypeValidator):
    """Validator for FHIR resource types"""

    def __init__(self, resource_type: FHIRDataType):
        self.resource_type = resource_type

    def is_valid(self, value: Any) -> bool:
        """Check if value is valid for this resource type"""
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Check resourceType field
        resource_type = value.get('resourceType')
        if resource_type != self.resource_type.value:
            return False

        return True

    def convert(self, value: Any) -> Any:
        """Convert value to this resource type"""
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValueError(f"Resource type {self.resource_type.value} requires dictionary")

        resource_type = value.get('resourceType')
        if resource_type != self.resource_type.value:
            raise ValueError(f"Expected resourceType '{self.resource_type.value}', got '{resource_type}'")

        return value


class QuantityValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Quantity type"""

    def __init__(self):
        super().__init__(FHIRDataType.QUANTITY, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have value
        if 'value' not in value:
            return False

        # Value must be numeric
        try:
            float(value['value'])
        except (ValueError, TypeError):
            return False

        # If code is present, system should be present (for coded quantities)
        if 'code' in value and 'system' not in value:
            # Allow code without system for commonly understood units
            if value['code'] not in ['kg', 'g', 'mg', 'L', 'mL', 'cm', 'm', '%']:
                return False

        return True


class CodingValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Coding type"""

    def __init__(self):
        super().__init__(FHIRDataType.CODING, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have either code or display
        if 'code' not in value and 'display' not in value:
            return False

        # If code is present, it should be a string
        if 'code' in value and not isinstance(value['code'], str):
            return False

        # System should be a valid URI if present
        if 'system' in value:
            system = value['system']
            if not isinstance(system, str):
                return False

        return True


class CodeableConceptValidator(ComplexTypeValidator):
    """Specialized validator for FHIR CodeableConcept type"""

    def __init__(self):
        super().__init__(FHIRDataType.CODEABLECONCEPT, set())
        self._coding_validator = CodingValidator()

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have either coding or text
        if 'coding' not in value and 'text' not in value:
            return False

        # Validate coding array if present
        if 'coding' in value:
            coding = value['coding']
            if not isinstance(coding, list):
                return False

            for coding_item in coding:
                if not self._coding_validator.is_valid(coding_item):
                    return False

        return True


class ReferenceValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Reference type"""

    def __init__(self):
        super().__init__(FHIRDataType.REFERENCE, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have reference, identifier, or display
        if not any(key in value for key in ['reference', 'identifier', 'display']):
            return False

        # Reference should be a valid string if present
        if 'reference' in value and not isinstance(value['reference'], str):
            return False

        return True


class IdentifierValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Identifier type"""

    def __init__(self):
        super().__init__(FHIRDataType.IDENTIFIER, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have value
        if 'value' not in value:
            return False

        # Value must be a string
        if not isinstance(value['value'], str):
            return False

        # Use should be valid if present
        if 'use' in value:
            valid_uses = ['usual', 'official', 'temp', 'secondary', 'old']
            if value['use'] not in valid_uses:
                return False

        return True


class PeriodValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Period type"""

    def __init__(self):
        super().__init__(FHIRDataType.PERIOD, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have start or end
        if 'start' not in value and 'end' not in value:
            return False

        # Validate datetime formats
        for field in ['start', 'end']:
            if field in value:
                try:
                    # Simple validation - should be datetime string
                    datetime_str = value[field]
                    if not isinstance(datetime_str, str):
                        return False
                    # Could add more sophisticated datetime validation here
                except Exception:
                    return False

        return True


class RangeValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Range type"""

    def __init__(self):
        super().__init__(FHIRDataType.RANGE, set())
        self._quantity_validator = QuantityValidator()

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have low or high
        if 'low' not in value and 'high' not in value:
            return False

        # Validate quantities
        for field in ['low', 'high']:
            if field in value:
                if not self._quantity_validator.is_valid(value[field]):
                    return False

        return True


class RatioValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Ratio type"""

    def __init__(self):
        super().__init__(FHIRDataType.RATIO, set())
        self._quantity_validator = QuantityValidator()

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have numerator or denominator
        if 'numerator' not in value and 'denominator' not in value:
            return False

        # Validate quantities
        for field in ['numerator', 'denominator']:
            if field in value:
                if not self._quantity_validator.is_valid(value[field]):
                    return False

        return True


class AttachmentValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Attachment type"""

    def __init__(self):
        super().__init__(FHIRDataType.ATTACHMENT, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have data, url, or title
        if not any(key in value for key in ['data', 'url', 'title']):
            return False

        # Validate data is base64 if present
        if 'data' in value:
            data = value['data']
            if not isinstance(data, str):
                return False
            # Could add base64 validation here

        # Validate URL format if present
        if 'url' in value:
            url = value['url']
            if not isinstance(url, str):
                return False

        return True


class AnnotationValidator(ComplexTypeValidator):
    """Specialized validator for FHIR Annotation type"""

    def __init__(self):
        super().__init__(FHIRDataType.ANNOTATION, set())

    def is_valid(self, value: Any) -> bool:
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Must have text
        if 'text' not in value:
            return False

        # Text must be a string
        if not isinstance(value['text'], str):
            return False

        return True


class FHIRTypeSystem:
    """
    FHIR Type System implementation

    Provides type checking, conversion, and validation for FHIR data types
    in the context of FHIRPath evaluation.
    """

    def __init__(self):
        self._validators: Dict[FHIRDataType, FHIRTypeValidator] = {}
        self._initialize_validators()

    def _initialize_validators(self) -> None:
        """Initialize type validators for all FHIR types"""
        # Primitive types
        for primitive_type in [
            FHIRDataType.BOOLEAN, FHIRDataType.INTEGER, FHIRDataType.INTEGER64,
            FHIRDataType.STRING, FHIRDataType.DECIMAL, FHIRDataType.URI,
            FHIRDataType.URL, FHIRDataType.CANONICAL, FHIRDataType.BASE64BINARY,
            FHIRDataType.INSTANT, FHIRDataType.DATE, FHIRDataType.DATETIME,
            FHIRDataType.TIME, FHIRDataType.CODE, FHIRDataType.OID,
            FHIRDataType.ID, FHIRDataType.MARKDOWN, FHIRDataType.UNSIGNEDINT,
            FHIRDataType.POSITIVEINT, FHIRDataType.UUID
        ]:
            self._validators[primitive_type] = PrimitiveTypeValidator(primitive_type)

        # Enhanced complex types with specialized validation
        self._validators[FHIRDataType.QUANTITY] = QuantityValidator()
        self._validators[FHIRDataType.CODING] = CodingValidator()
        self._validators[FHIRDataType.CODEABLECONCEPT] = CodeableConceptValidator()
        self._validators[FHIRDataType.IDENTIFIER] = IdentifierValidator()
        self._validators[FHIRDataType.REFERENCE] = ReferenceValidator()
        self._validators[FHIRDataType.PERIOD] = PeriodValidator()
        self._validators[FHIRDataType.RANGE] = RangeValidator()
        self._validators[FHIRDataType.RATIO] = RatioValidator()
        self._validators[FHIRDataType.ATTACHMENT] = AttachmentValidator()
        self._validators[FHIRDataType.ANNOTATION] = AnnotationValidator()

        # Other complex types with basic validation
        self._validators[FHIRDataType.HUMANNAME] = ComplexTypeValidator(
            FHIRDataType.HUMANNAME, set()
        )
        self._validators[FHIRDataType.ADDRESS] = ComplexTypeValidator(
            FHIRDataType.ADDRESS, set()
        )
        self._validators[FHIRDataType.CONTACTPOINT] = ComplexTypeValidator(
            FHIRDataType.CONTACTPOINT, set()
        )

        # Resource types
        for resource_type in [
            FHIRDataType.PATIENT, FHIRDataType.OBSERVATION, FHIRDataType.ENCOUNTER,
            FHIRDataType.PRACTITIONER, FHIRDataType.ORGANIZATION, FHIRDataType.MEDICATION,
            FHIRDataType.CONDITION, FHIRDataType.PROCEDURE, FHIRDataType.DIAGNOSTICREPORT,
            FHIRDataType.MEDICATIONREQUEST
        ]:
            self._validators[resource_type] = ResourceTypeValidator(resource_type)

    def is_type(self, value: Any, type_name: str) -> bool:
        """
        Check if value is of specified FHIR type

        Args:
            value: Value to check
            type_name: FHIR type name

        Returns:
            True if value is of specified type
        """
        try:
            fhir_type = FHIRDataType(type_name)
        except ValueError:
            # Unknown type
            return False

        if fhir_type == FHIRDataType.ANY:
            return True

        if fhir_type == FHIRDataType.COLLECTION:
            return isinstance(value, list)

        if fhir_type not in self._validators:
            # Default validation for unknown types
            return True

        return self._validators[fhir_type].is_valid(value)

    def convert_to_type(self, value: Any, type_name: str) -> Any:
        """
        Convert value to specified FHIR type

        Args:
            value: Value to convert
            type_name: Target FHIR type name

        Returns:
            Converted value

        Raises:
            ValueError: If conversion is not possible
        """
        try:
            fhir_type = FHIRDataType(type_name)
        except ValueError:
            raise ValueError(f"Unknown FHIR type: {type_name}")

        if fhir_type == FHIRDataType.ANY:
            return value

        if fhir_type == FHIRDataType.COLLECTION:
            if isinstance(value, list):
                return value
            else:
                return [value] if value is not None else []

        if fhir_type not in self._validators:
            # Default conversion for unknown types
            return value

        return self._validators[fhir_type].convert(value)

    def convert_to_fhir_type(self, value: Any, fhir_type: FHIRDataType) -> Any:
        """
        Convert value to specified FHIR type enum

        Args:
            value: Value to convert
            fhir_type: Target FHIR type

        Returns:
            Converted value
        """
        return self.convert_to_type(value, fhir_type.value)

    def get_type_name(self, value: Any) -> str:
        """
        Get the FHIR type name for a value

        Args:
            value: Value to analyze

        Returns:
            FHIR type name
        """
        if value is None:
            return "null"

        if isinstance(value, bool):
            return FHIRDataType.BOOLEAN.value
        elif isinstance(value, int):
            return FHIRDataType.INTEGER.value
        elif isinstance(value, float):
            return FHIRDataType.DECIMAL.value
        elif isinstance(value, str):
            return FHIRDataType.STRING.value
        elif isinstance(value, datetime):
            return FHIRDataType.DATETIME.value
        elif isinstance(value, date):
            return FHIRDataType.DATE.value
        elif isinstance(value, list):
            return FHIRDataType.COLLECTION.value
        elif isinstance(value, dict):
            # Check for FHIR resource
            resource_type = value.get('resourceType')
            if resource_type:
                try:
                    return FHIRDataType(resource_type).value
                except ValueError:
                    return "Resource"
            else:
                # Complex type - would need more sophisticated detection
                return "Complex"
        else:
            return "unknown"

    def is_primitive_type(self, type_name: str) -> bool:
        """Check if type name is a FHIR primitive type"""
        try:
            fhir_type = FHIRDataType(type_name)
            return fhir_type in [
                FHIRDataType.BOOLEAN, FHIRDataType.INTEGER, FHIRDataType.INTEGER64,
                FHIRDataType.STRING, FHIRDataType.DECIMAL, FHIRDataType.URI,
                FHIRDataType.URL, FHIRDataType.CANONICAL, FHIRDataType.BASE64BINARY,
                FHIRDataType.INSTANT, FHIRDataType.DATE, FHIRDataType.DATETIME,
                FHIRDataType.TIME, FHIRDataType.CODE, FHIRDataType.OID,
                FHIRDataType.ID, FHIRDataType.MARKDOWN, FHIRDataType.UNSIGNEDINT,
                FHIRDataType.POSITIVEINT, FHIRDataType.UUID
            ]
        except ValueError:
            return False

    def is_complex_type(self, type_name: str) -> bool:
        """Check if type name is a FHIR complex type"""
        try:
            fhir_type = FHIRDataType(type_name)
            return fhir_type in [
                FHIRDataType.QUANTITY, FHIRDataType.RATIO, FHIRDataType.RANGE,
                FHIRDataType.PERIOD, FHIRDataType.CODING, FHIRDataType.CODEABLECONCEPT,
                FHIRDataType.IDENTIFIER, FHIRDataType.HUMANNAME, FHIRDataType.ADDRESS,
                FHIRDataType.CONTACTPOINT, FHIRDataType.REFERENCE, FHIRDataType.ATTACHMENT,
                FHIRDataType.ANNOTATION
            ]
        except ValueError:
            return False

    def is_resource_type(self, type_name: str) -> bool:
        """Check if type name is a FHIR resource type"""
        try:
            fhir_type = FHIRDataType(type_name)
            return fhir_type in [
                FHIRDataType.RESOURCE, FHIRDataType.DOMAINRESOURCE,
                FHIRDataType.PATIENT, FHIRDataType.OBSERVATION, FHIRDataType.ENCOUNTER,
                FHIRDataType.PRACTITIONER, FHIRDataType.ORGANIZATION, FHIRDataType.MEDICATION,
                FHIRDataType.CONDITION, FHIRDataType.PROCEDURE, FHIRDataType.DIAGNOSTICREPORT,
                FHIRDataType.MEDICATIONREQUEST
            ]
        except ValueError:
            return False

    def get_supported_types(self) -> List[str]:
        """Get list of all supported FHIR type names"""
        return [fhir_type.value for fhir_type in FHIRDataType]

    def validate_value(self, value: Any, type_name: str) -> bool:
        """
        Validate that a value conforms to specified FHIR type

        Args:
            value: Value to validate
            type_name: Expected FHIR type name

        Returns:
            True if value is valid for the type
        """
        return self.is_type(value, type_name)


# Polymorphic Property Mappings for FHIR Resources
# These properties use the [x] suffix pattern where the property can be one of multiple types
POLYMORPHIC_PROPERTIES: Dict[str, List[str]] = {
    # Observation.value[x] - most commonly used polymorphic property
    'value': [
        'valueQuantity', 'valueCodeableConcept', 'valueString',
        'valueBoolean', 'valueInteger', 'valueRange', 'valueRatio',
        'valueSampledData', 'valueTime', 'valueDateTime', 'valuePeriod'
    ],
    # Condition.onset[x]
    'onset': [
        'onsetDateTime', 'onsetAge', 'onsetPeriod', 'onsetRange', 'onsetString'
    ],
    # Condition.abatement[x]
    'abatement': [
        'abatementDateTime', 'abatementAge', 'abatementPeriod', 'abatementRange', 'abatementString', 'abatementBoolean'
    ],
    # Patient.deceased[x]
    'deceased': [
        'deceasedBoolean', 'deceasedDateTime'
    ],
    # Patient.multipleBirth[x]
    'multipleBirth': [
        'multipleBirthBoolean', 'multipleBirthInteger'
    ],
    # Timing.repeat.bounds[x]
    'bounds': [
        'boundsDuration', 'boundsRange', 'boundsPeriod'
    ],
    # Dosage.asNeeded[x]
    'asNeeded': [
        'asNeededBoolean', 'asNeededCodeableConcept'
    ],
    # Dosage.dose[x]
    'dose': [
        'doseRange', 'doseQuantity'
    ],
    # Dosage.rate[x]
    'rate': [
        'rateRatio', 'rateRange', 'rateQuantity'
    ],
    # Extension.value[x]
    'extension_value': [  # Renamed to avoid conflict with Observation.value
        'valueBase64Binary', 'valueBoolean', 'valueCanonical', 'valueCode', 'valueDate',
        'valueDateTime', 'valueDecimal', 'valueId', 'valueInstant', 'valueInteger',
        'valueMarkdown', 'valueOid', 'valuePositiveInt', 'valueString', 'valueTime',
        'valueUnsignedInt', 'valueUri', 'valueUrl', 'valueUuid', 'valueAddress',
        'valueAge', 'valueAnnotation', 'valueAttachment', 'valueCodeableConcept',
        'valueCoding', 'valueContactPoint', 'valueCount', 'valueDistance', 'valueDuration',
        'valueHumanName', 'valueIdentifier', 'valueMoney', 'valuePeriod', 'valueQuantity',
        'valueRange', 'valueRatio', 'valueReference', 'valueSampledData', 'valueSignature',
        'valueTiming', 'valueContactDetail', 'valueContributor', 'valueDataRequirement',
        'valueExpression', 'valueParameterDefinition', 'valueRelatedArtifact',
        'valueTriggerDefinition', 'valueUsageContext', 'valueDosage', 'valueMeta'
    ],
    # Procedure.performed[x]
    'performed': [
        'performedDateTime', 'performedPeriod', 'performedString', 'performedAge', 'performedRange'
    ],
    # MedicationAdministration.effective[x]
    'effective': [
        'effectiveDateTime', 'effectivePeriod'
    ],
    # ServiceRequest.occurrence[x]
    'occurrence': [
        'occurrenceDateTime', 'occurrencePeriod', 'occurrenceTiming'
    ],
    # DiagnosticReport.effective[x] (same as MedicationAdministration but kept for clarity)
    # Already covered by 'effective' key above

    # MedicationRequest.reported[x]
    'reported': [
        'reportedBoolean', 'reportedReference'
    ],
}


def resolve_polymorphic_property(base_property: str, resource_type: Optional[str] = None) -> Optional[List[str]]:
    """
    Resolve a polymorphic property to its possible typed variants.

    Args:
        base_property: The base property name without type suffix (e.g., 'value', 'onset')
        resource_type: Optional resource type for context-specific resolution

    Returns:
        List of possible typed property names, or None if not polymorphic

    Example:
        >>> resolve_polymorphic_property('value')
        ['valueQuantity', 'valueCodeableConcept', 'valueString', ...]

        >>> resolve_polymorphic_property('onset')
        ['onsetDateTime', 'onsetAge', 'onsetPeriod', 'onsetRange', 'onsetString']
    """
    # Direct lookup
    if base_property in POLYMORPHIC_PROPERTIES:
        return POLYMORPHIC_PROPERTIES[base_property]

    # Check if property might be a typed variant already
    # If someone passes 'valueQuantity', return None (not polymorphic, already typed)
    for base, variants in POLYMORPHIC_PROPERTIES.items():
        if base_property in variants:
            return None  # Already a specific typed property

    return None


def is_polymorphic_property(property_name: str) -> bool:
    """
    Check if a property name is a polymorphic property.

    Args:
        property_name: Property name to check

    Returns:
        True if the property is polymorphic

    Example:
        >>> is_polymorphic_property('value')
        True
        >>> is_polymorphic_property('valueQuantity')
        False
        >>> is_polymorphic_property('identifier')
        False
    """
    return property_name in POLYMORPHIC_PROPERTIES


def resolve_polymorphic_field_for_type(base_property: str, target_type: str) -> Optional[str]:
    """
    Resolve polymorphic field name from base property and target type.

    In FHIR, polymorphic fields encode the type in the field name itself.
    For example, Observation.value[x] can be valueString, valueInteger, valueRange, etc.
    This function maps from the base property ("value") and target type ("Integer")
    to the specific polymorphic field name ("valueInteger").

    Args:
        base_property: Base property name (e.g., "value", "deceased", "onset")
        target_type: FHIRPath type name (e.g., "Range", "integer", "string", "Quantity")

    Returns:
        Full polymorphic field name, or None if not a polymorphic property

    Examples:
        >>> resolve_polymorphic_field_for_type("value", "Range")
        "valueRange"
        >>> resolve_polymorphic_field_for_type("value", "integer")
        "valueInteger"
        >>> resolve_polymorphic_field_for_type("value", "string")
        "valueString"
        >>> resolve_polymorphic_field_for_type("deceased", "boolean")
        "deceasedBoolean"
        >>> resolve_polymorphic_field_for_type("identifier", "string")
        None  # 'identifier' is not polymorphic
    """
    # Check if base property is polymorphic
    if not is_polymorphic_property(base_property):
        return None

    # Normalize type name: capitalize first letter
    # FHIR uses PascalCase for types in field names
    type_suffix = target_type[0].upper() + target_type[1:] if target_type else ""

    # Construct the polymorphic field name
    return f"{base_property}{type_suffix}"


def get_polymorphic_base_property(typed_property: str) -> Optional[str]:
    """
    Get the base polymorphic property name from a typed variant.

    Args:
        typed_property: Typed property name (e.g., 'valueQuantity')

    Returns:
        Base property name (e.g., 'value'), or None if not a polymorphic variant

    Example:
        >>> get_polymorphic_base_property('valueQuantity')
        'value'
        >>> get_polymorphic_base_property('onsetDateTime')
        'onset'
        >>> get_polymorphic_base_property('identifier')
        None
    """
    for base, variants in POLYMORPHIC_PROPERTIES.items():
        if typed_property in variants:
            return base
    return None