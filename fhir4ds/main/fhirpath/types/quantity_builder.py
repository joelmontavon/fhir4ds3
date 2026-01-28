"""
FHIR Quantity Builder - Business Logic for Quantity JSON Construction

This module contains FHIR-specific business logic for constructing FHIR Quantity
JSON structures. This ensures the SQL translator layer remains "thin" and contains
only syntax translation logic, not FHIR business rules.

Module: fhir4ds.fhirpath.types.quantity_builder
Purpose: Provide centralized FHIR Quantity construction logic per architectural principles
"""

from typing import Dict, Any, Union
from decimal import Decimal
import json


# FHIR-specific constants for Quantity
UCUM_SYSTEM_URL = "http://unitsofmeasure.org"


def build_quantity_json(value: Union[Decimal, int, float, str], unit: str) -> Dict[str, Any]:
    """
    Build a FHIR Quantity JSON structure from value and unit.

    According to FHIR specification, Quantity has:
    - value (required): Numerical value
    - unit (optional): Human-readable unit representation
    - system (optional): URI for the unit code system (e.g., UCUM)
    - code (optional): Coded form of the unit

    For UCUM units, we use the standard system URL and set code to the unit string.

    Args:
        value: Numeric value as Decimal, int, float, or string
        unit: Unit string (e.g., 'mg', 'kg', 'mL')

    Returns:
        Dictionary representing FHIR Quantity JSON structure

    Example:
        >>> build_quantity_json(Decimal('10'), 'mg')
        {'value': 10, 'unit': 'mg', 'system': 'http://unitsofmeasure.org', 'code': 'mg'}

        >>> build_quantity_json(Decimal('10.5'), 'kg')
        {'value': 10.5, 'unit': 'kg', 'system': 'http://unitsofmeasure.org', 'code': 'kg'}
    """
    # Convert value to appropriate numeric type
    # Use int if no decimal point, float otherwise
    value_str = str(value)
    numeric_value = float(value) if '.' in value_str else int(value)

    return {
        'value': numeric_value,
        'unit': unit,
        'system': UCUM_SYSTEM_URL,
        'code': unit
    }


def build_quantity_json_string(value: Union[Decimal, int, float, str], unit: str) -> str:
    """
    Build a FHIR Quantity JSON string for SQL literal embedding.

    This is a convenience function that returns the JSON string representation
    suitable for embedding directly in SQL queries.

    Args:
        value: Numeric value as Decimal, int, float, or string
        unit: Unit string (e.g., 'mg', 'kg', 'mL')

    Returns:
        JSON string representation of FHIR Quantity

    Example:
        >>> build_quantity_json_string(Decimal('10'), 'mg')
        '{"value": 10, "unit": "mg", "system": "http://unitsofmeasure.org", "code": "mg"}'
    """
    quantity_json = build_quantity_json(value, unit)
    return json.dumps(quantity_json)


def validate_quantity_fields(quantity_info: Dict[str, Any]) -> bool:
    """
    Validate that quantity info has required fields.

    Args:
        quantity_info: Dictionary with 'value' and 'unit' fields

    Returns:
        True if valid, False otherwise

    Example:
        >>> validate_quantity_fields({'value': Decimal('10'), 'unit': 'mg'})
        True
        >>> validate_quantity_fields({'value': Decimal('10')})
        False
    """
    return 'value' in quantity_info and 'unit' in quantity_info
