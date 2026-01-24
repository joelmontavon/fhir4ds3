"""
FHIR Type System Module

This module provides FHIR type system support for the FHIRPath evaluation engine,
including type checking, conversion, and FHIR-specific data type handling.
"""

from .fhir_types import (
    FHIRDataType,
    FHIRTypeValidator,
    PrimitiveTypeValidator,
    ComplexTypeValidator,
    ResourceTypeValidator,
    FHIRTypeSystem
)

from .type_registry import (
    TypeRegistry,
    get_type_registry,
    register_global_type,
    is_valid_type,
    convert_to_type
)

from .type_converter import (
    FHIRTypeConverter,
    get_type_converter,
    convert_to_fhirpath_type,
    convert_from_fhirpath_type,
    validate_healthcare_constraints
)

from .element_type_resolver import (
    FHIRElementTypeResolver,
    get_element_type_resolver,
    resolve_element_type
)

from .temporal_parser import (
    FHIRTemporalParser,
    ParsedTemporal,
    TemporalPrecision,
    get_temporal_parser,
    parse_temporal
)

from .type_discriminators import (
    FHIR_TYPE_DISCRIMINATORS,
    get_type_discriminator,
)

__all__ = [
    # Core type system
    'FHIRDataType',
    'FHIRTypeValidator',
    'PrimitiveTypeValidator',
    'ComplexTypeValidator',
    'ResourceTypeValidator',
    'FHIRTypeSystem',

    # Type registry
    'TypeRegistry',
    'get_type_registry',
    'register_global_type',
    'is_valid_type',
    'convert_to_type',

    # Type converter
    'FHIRTypeConverter',
    'get_type_converter',
    'convert_to_fhirpath_type',
    'convert_from_fhirpath_type',
    'validate_healthcare_constraints',

    # Element type resolution
    'FHIRElementTypeResolver',
    'get_element_type_resolver',
    'resolve_element_type',

    # Temporal parsing
    'FHIRTemporalParser',
    'ParsedTemporal',
    'TemporalPrecision',
    'get_temporal_parser',
    'parse_temporal',

    # Structural discriminators
    'FHIR_TYPE_DISCRIMINATORS',
    'get_type_discriminator',
]

__version__ = "0.1.0"
__author__ = "FHIR4DS Development Team"
