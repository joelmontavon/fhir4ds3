"""
FHIR Type Discriminators

Provides structural discriminator metadata for complex FHIR data types. The
discriminators are used by the SQL translator to validate that a JSON payload
matches the expected FHIR structure before returning values for the `as`
operator. This prevents type casts from succeeding when key structural elements
are absent (for example, casting an Observation.value to Quantity when the JSON
object lacks a `value` element).

Design notes:
- Discriminators focus on core structural fields that uniquely identify the
  complex type. They intentionally avoid optional or profile-specific fields
  so that valid data is not rejected unnecessarily.
- Consumers should always resolve type names to canonical FHIR names prior to
  lookup to ensure aliases (e.g., `System.Quantity`) map correctly.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .type_registry import get_type_registry

# Structural discriminators keyed by canonical FHIR type name. The `required_fields`
# collection lists JSON member names that MUST exist for the type assertion to
# succeed. An empty list indicates that no structural validation is required
# beyond presence of the object itself.
FHIR_TYPE_DISCRIMINATORS: Dict[str, Dict[str, List[str]]] = {
    # Quantities must include a numeric value; unit/system are optional.
    "Quantity": {"required_fields": ["value"]},
    # Periods require at least a start or end; we default to start for minimal validation.
    "Period": {"required_fields": ["start"]},
    # Coding expects a code value to be meaningful.
    "Coding": {"required_fields": ["code"]},
    # CodeableConcepts typically contain a coding collection.
    "CodeableConcept": {"required_fields": ["coding"]},
    # HumanName commonly requires a family element for identification.
    "HumanName": {"required_fields": ["family"]},
    # Address should expose at least one line entry.
    "Address": {"required_fields": ["line"]},
    # Identifier should provide its value.
    "Identifier": {"required_fields": ["value"]},
    # Reference requires a reference string or identifier.
    "Reference": {"required_fields": ["reference"]},
    # Range should expose a low value to represent the lower bound.
    "Range": {"required_fields": ["low"]},
    # Ratio should provide both numerator and denominator structures.
    "Ratio": {"required_fields": ["numerator", "denominator"]},
}


def get_type_discriminator(type_name: str) -> Optional[Dict[str, List[str]]]:
    """
    Retrieve discriminator metadata for a FHIR type.

    Args:
        type_name: Type name that may be an alias or canonical FHIR type.

    Returns:
        Discriminator dictionary if a structural definition is available, otherwise None.
    """
    registry = get_type_registry()
    canonical_name = registry.get_canonical_name(type_name)
    return FHIR_TYPE_DISCRIMINATORS.get(canonical_name)

