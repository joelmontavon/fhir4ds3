"""
FHIR Element Type Resolver

Resolves FHIR resource element paths to their canonical types.
This enables functions like highBoundary() to determine whether an element
is a Date, DateTime, Decimal, Quantity, etc.

Examples:
    Patient.birthDate → Date
    Observation.valueQuantity → Quantity
    Observation.effectiveDateTime → DateTime
    RiskAssessment.prediction.probabilityDecimal → Decimal
"""

from typing import Dict, Optional, Set
import logging

logger = logging.getLogger(__name__)


class FHIRElementTypeResolver:
    """
    Resolves FHIR resource element paths to their canonical FHIR types.

    This resolver uses a hardcoded mapping of common FHIR resource elements
    to their types. For a production implementation, this would load from
    FHIR StructureDefinition resources, but for SP-009-016 we use a
    curated subset covering the official test suite requirements.

    Architecture Note:
        This is business logic that belongs in the FHIRPath engine layer,
        not in database dialects. The translator uses this to determine
        which boundary calculation algorithm to apply.
    """

    def __init__(self):
        """Initialize element type resolver with common FHIR element types."""
        self._element_types: Dict[str, str] = {}
        self._initialize_element_types()

    def _initialize_element_types(self) -> None:
        """Initialize mapping of FHIR element paths to types."""

        # Patient resource elements
        self._element_types.update({
            'Patient.birthDate': 'date',
            'Patient.deceasedDateTime': 'dateTime',
            'Patient.deceasedBoolean': 'boolean',
            'Patient.multipleBirthBoolean': 'boolean',
            'Patient.multipleBirthInteger': 'integer',
            'Patient.active': 'boolean',
            'Patient.gender': 'code',
            'Patient.name': 'HumanName',
            'Patient.telecom': 'ContactPoint',
            'Patient.address': 'Address',
            'Patient.maritalStatus': 'CodeableConcept',
            'Patient.contact': 'BackboneElement',
            'Patient.communication': 'BackboneElement',
            'Patient.generalPractitioner': 'Reference',
            'Patient.managingOrganization': 'Reference',
            'Patient.link': 'BackboneElement',
            'Patient.identifier': 'Identifier',
            'Patient.photo': 'Attachment',
        })

        # Observation resource elements
        self._element_types.update({
            'Observation.valueQuantity': 'Quantity',
            'Observation.valueCodeableConcept': 'CodeableConcept',
            'Observation.valueString': 'string',
            'Observation.valueBoolean': 'boolean',
            'Observation.valueInteger': 'integer',
            'Observation.valueRange': 'Range',
            'Observation.valueRatio': 'Ratio',
            'Observation.valueSampledData': 'SampledData',
            'Observation.valueTime': 'time',
            'Observation.valueDateTime': 'dateTime',
            'Observation.valuePeriod': 'Period',
            'Observation.effectiveDateTime': 'dateTime',
            'Observation.effectivePeriod': 'Period',
            'Observation.effectiveTiming': 'Timing',
            'Observation.effectiveInstant': 'instant',
            'Observation.issued': 'instant',
            'Observation.status': 'code',
            'Observation.category': 'CodeableConcept',
            'Observation.code': 'CodeableConcept',
            'Observation.subject': 'Reference',
            'Observation.encounter': 'Reference',
            'Observation.performer': 'Reference',
            'Observation.interpretation': 'CodeableConcept',
            'Observation.note': 'Annotation',
            'Observation.bodySite': 'CodeableConcept',
            'Observation.method': 'CodeableConcept',
            'Observation.referenceRange': 'BackboneElement',
            'Observation.component': 'BackboneElement',
        })

        # Encounter resource elements
        self._element_types.update({
            'Encounter.status': 'code',
            'Encounter.class': 'Coding',
            'Encounter.type': 'CodeableConcept',
            'Encounter.priority': 'CodeableConcept',
            'Encounter.subject': 'Reference',
            'Encounter.period': 'Period',
            'Encounter.length': 'Duration',
            'Encounter.reasonCode': 'CodeableConcept',
            'Encounter.diagnosis': 'BackboneElement',
            'Encounter.hospitalization': 'BackboneElement',
            'Encounter.location': 'BackboneElement',
        })

        # Condition resource elements
        self._element_types.update({
            'Condition.clinicalStatus': 'CodeableConcept',
            'Condition.verificationStatus': 'CodeableConcept',
            'Condition.category': 'CodeableConcept',
            'Condition.severity': 'CodeableConcept',
            'Condition.code': 'CodeableConcept',
            'Condition.bodySite': 'CodeableConcept',
            'Condition.subject': 'Reference',
            'Condition.encounter': 'Reference',
            'Condition.onsetDateTime': 'dateTime',
            'Condition.onsetAge': 'Age',
            'Condition.onsetPeriod': 'Period',
            'Condition.onsetRange': 'Range',
            'Condition.onsetString': 'string',
            'Condition.abatementDateTime': 'dateTime',
            'Condition.abatementAge': 'Age',
            'Condition.abatementPeriod': 'Period',
            'Condition.abatementRange': 'Range',
            'Condition.abatementString': 'string',
            'Condition.recordedDate': 'dateTime',
        })

        # Procedure resource elements
        self._element_types.update({
            'Procedure.status': 'code',
            'Procedure.code': 'CodeableConcept',
            'Procedure.subject': 'Reference',
            'Procedure.encounter': 'Reference',
            'Procedure.performedDateTime': 'dateTime',
            'Procedure.performedPeriod': 'Period',
            'Procedure.performedString': 'string',
            'Procedure.performedAge': 'Age',
            'Procedure.performedRange': 'Range',
            'Procedure.recorder': 'Reference',
            'Procedure.asserter': 'Reference',
            'Procedure.performer': 'BackboneElement',
            'Procedure.location': 'Reference',
            'Procedure.reasonCode': 'CodeableConcept',
            'Procedure.bodySite': 'CodeableConcept',
            'Procedure.outcome': 'CodeableConcept',
            'Procedure.complication': 'CodeableConcept',
        })

        # MedicationRequest resource elements
        self._element_types.update({
            'MedicationRequest.status': 'code',
            'MedicationRequest.intent': 'code',
            'MedicationRequest.medicationCodeableConcept': 'CodeableConcept',
            'MedicationRequest.medicationReference': 'Reference',
            'MedicationRequest.subject': 'Reference',
            'MedicationRequest.encounter': 'Reference',
            'MedicationRequest.authoredOn': 'dateTime',
            'MedicationRequest.requester': 'Reference',
            'MedicationRequest.performer': 'Reference',
            'MedicationRequest.reasonCode': 'CodeableConcept',
            'MedicationRequest.dosageInstruction': 'Dosage',
            'MedicationRequest.dispenseRequest': 'BackboneElement',
        })

        # Common element patterns across all resources
        common_elements = {
            '.id': 'id',
            '.meta': 'Meta',
            '.implicitRules': 'uri',
            '.language': 'code',
            '.text': 'Narrative',
            '.contained': 'Resource',
            '.extension': 'Extension',
            '.modifierExtension': 'Extension',
        }

        # Add common elements for each resource type
        resource_types = ['Patient', 'Observation', 'Encounter', 'Condition',
                         'Procedure', 'MedicationRequest', 'Medication',
                         'Organization', 'Practitioner', 'Location']

        for resource in resource_types:
            for suffix, element_type in common_elements.items():
                self._element_types[f'{resource}{suffix}'] = element_type

        logger.info(f"Initialized FHIRElementTypeResolver with {len(self._element_types)} element mappings")

    def resolve_element_type(self, resource_type: str, element_path: str) -> Optional[str]:
        """
        Resolve an element path to its FHIR type.

        Args:
            resource_type: FHIR resource type (e.g., "Patient", "Observation")
            element_path: Element path relative to resource (e.g., "birthDate", "name.given")

        Returns:
            FHIR type name (e.g., "date", "dateTime", "Quantity") or None if not found

        Examples:
            >>> resolver = FHIRElementTypeResolver()
            >>> resolver.resolve_element_type("Patient", "birthDate")
            'date'
            >>> resolver.resolve_element_type("Observation", "valueQuantity")
            'Quantity'
            >>> resolver.resolve_element_type("Observation", "effectiveDateTime")
            'dateTime'
        """
        # Try full path first
        full_path = f"{resource_type}.{element_path}"
        element_type = self._element_types.get(full_path)

        if element_type:
            logger.debug(f"Resolved {full_path} → {element_type}")
            return element_type

        # Try first component only (for nested paths like "name.given")
        # The first component determines the base type
        first_component = element_path.split('.')[0] if '.' in element_path else element_path
        first_path = f"{resource_type}.{first_component}"
        element_type = self._element_types.get(first_path)

        if element_type:
            logger.debug(f"Resolved {full_path} → {element_type} (via {first_path})")
            return element_type

        logger.debug(f"Could not resolve type for {full_path}")
        return None

    def resolve_full_path(self, full_path: str) -> Optional[str]:
        """
        Resolve a full path like "Patient.birthDate" to its type.

        Args:
            full_path: Full path including resource type (e.g., "Patient.birthDate")

        Returns:
            FHIR type name or None if not found

        Examples:
            >>> resolver = FHIRElementTypeResolver()
            >>> resolver.resolve_full_path("Patient.birthDate")
            'date'
        """
        if '.' not in full_path:
            return None

        parts = full_path.split('.', 1)
        if len(parts) != 2:
            return None

        resource_type, element_path = parts
        return self.resolve_element_type(resource_type, element_path)

    def get_all_date_time_elements(self, resource_type: str) -> Set[str]:
        """
        Get all date/time elements for a resource type.

        Args:
            resource_type: FHIR resource type

        Returns:
            Set of element paths that are date/time types
        """
        date_time_types = {'date', 'dateTime', 'instant', 'time'}
        result = set()

        prefix = f"{resource_type}."
        for full_path, element_type in self._element_types.items():
            if full_path.startswith(prefix) and element_type in date_time_types:
                # Extract just the element path (without resource type prefix)
                element_path = full_path[len(prefix):]
                result.add(element_path)

        return result

    def get_all_numeric_elements(self, resource_type: str) -> Set[str]:
        """
        Get all numeric elements for a resource type.

        Args:
            resource_type: FHIR resource type

        Returns:
            Set of element paths that are numeric types (integer, decimal, Quantity)
        """
        numeric_types = {'integer', 'decimal', 'Quantity', 'Age', 'Duration', 'Count', 'Distance'}
        result = set()

        prefix = f"{resource_type}."
        for full_path, element_type in self._element_types.items():
            if full_path.startswith(prefix) and element_type in numeric_types:
                element_path = full_path[len(prefix):]
                result.add(element_path)

        return result


# Global resolver instance
_global_resolver: Optional[FHIRElementTypeResolver] = None


def get_element_type_resolver() -> FHIRElementTypeResolver:
    """
    Get the global element type resolver instance.

    Returns:
        Global FHIRElementTypeResolver instance
    """
    global _global_resolver
    if _global_resolver is None:
        _global_resolver = FHIRElementTypeResolver()
    return _global_resolver


def resolve_element_type(resource_type: str, element_path: str) -> Optional[str]:
    """
    Convenience function to resolve element type using global resolver.

    Args:
        resource_type: FHIR resource type
        element_path: Element path

    Returns:
        FHIR type name or None
    """
    resolver = get_element_type_resolver()
    return resolver.resolve_element_type(resource_type, element_path)
