"""
FHIR Type Constants - Centralized Type Definitions

This module contains centralized FHIR type definitions that should not be duplicated
across the codebase. Dialects should import from here rather than hardcoding business logic.

Module: fhir4ds.fhirpath.types.fhir_type_constants
Purpose: Ensure thin dialect principle - dialects contain only syntax, not business logic
"""

# Complex FHIR types that should be checked as JSON objects (not primitives)
# These are FHIR complex types / resources that have structured JSON representations
COMPLEX_FHIR_TYPES = {
    "quantity", "period", "patient", "humanname", "observation",
    "encounter", "condition", "procedure", "medication", "organization",
    "practitioner", "range", "ratio", "codeableconcept", "coding",
    "identifier", "reference", "attachment", "annotation", "address",
    "contactpoint", "age", "duration", "distance", "count",
    "simplequantity", "moneyquantity", "diagnosticreport",
    "medicationrequest"
}

def is_complex_fhir_type(type_name: str) -> bool:
    """
    Determine if a FHIR type is complex (structured JSON object) vs primitive (scalar).

    Args:
        type_name: FHIR type name (case-insensitive)

    Returns:
        True if type is a complex FHIR type, False if primitive

    Example:
        >>> is_complex_fhir_type("HumanName")
        True
        >>> is_complex_fhir_type("string")
        False
    """
    return type_name.lower() in COMPLEX_FHIR_TYPES
