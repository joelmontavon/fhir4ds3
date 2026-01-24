"""
FHIRPath Exception Handling

This module provides comprehensive exception handling for FHIRPath parsing and evaluation,
including healthcare-specific error contexts and security-conscious error reporting.
"""

from .fhirpath_exceptions import (
    # Base exceptions
    FHIRPathError,
    FHIRPathParseError,
    FHIRPathEvaluationError,
    FHIRPathTypeError,
    FHIRPathValidationError,

    # Parsing exceptions
    FHIRPathSyntaxError,
    FHIRPathGrammarError,
    FHIRPathTokenError,

    # Evaluation exceptions
    FHIRPathRuntimeError,
    FHIRPathContextError,
    FHIRPathFunctionError,
    FHIRPathCollectionError,
    FHIRPathPathNavigationError,

    # Type system exceptions
    FHIRPathTypeValidationError,
    FHIRPathTypeConversionError,
    FHIRPathTypeMismatchError,
    FHIRPathTranslationError,

    # Healthcare-specific exceptions
    FHIRPathHealthcareError,
    FHIRPathResourceError,
    FHIRPathTerminologyError,
    FHIRPathComplianceError,

    # Database exceptions
    FHIRPathDatabaseError,
    FHIRPathDialectError,

    # Execution exceptions
    FHIRPathExecutionError,

    # Security exceptions
    FHIRPathSecurityError,
)

from .error_context import (
    ErrorContext,
    ErrorLocation,
    ErrorSeverity,
    HealthcareErrorContext,
    build_error_context,
    sanitize_error_for_logging,
    log_fhirpath_error,
)

__all__ = [
    # Base exceptions
    'FHIRPathError',
    'FHIRPathParseError',
    'FHIRPathEvaluationError',
    'FHIRPathTypeError',
    'FHIRPathValidationError',

    # Parsing exceptions
    'FHIRPathSyntaxError',
    'FHIRPathGrammarError',
    'FHIRPathTokenError',

    # Evaluation exceptions
    'FHIRPathRuntimeError',
    'FHIRPathContextError',
    'FHIRPathFunctionError',
    'FHIRPathCollectionError',
    'FHIRPathPathNavigationError',

    # Type system exceptions
    'FHIRPathTypeValidationError',
    'FHIRPathTypeConversionError',
    'FHIRPathTypeMismatchError',
    'FHIRPathTranslationError',

    # Healthcare-specific exceptions
    'FHIRPathHealthcareError',
    'FHIRPathResourceError',
    'FHIRPathTerminologyError',
    'FHIRPathComplianceError',

    # Database exceptions
    'FHIRPathDatabaseError',
    'FHIRPathDialectError',

    # Execution exceptions
    'FHIRPathExecutionError',

    # Security exceptions
    'FHIRPathSecurityError',

    # Error context
    'ErrorContext',
    'ErrorLocation',
    'ErrorSeverity',
    'HealthcareErrorContext',
    'build_error_context',
    'sanitize_error_for_logging',
    'log_fhirpath_error',
]
