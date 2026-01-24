"""
Comprehensive FHIRPath Exception Hierarchy

This module defines a comprehensive exception hierarchy for FHIRPath parsing and evaluation
with healthcare-specific error contexts and security-conscious error reporting.
"""

from typing import Optional, Dict, Any, List, Union
from .error_context import ErrorContext, ErrorLocation, ErrorSeverity


class FHIRPathError(Exception):
    """
    Base exception for all FHIRPath operations

    All FHIRPath exceptions should inherit from this class to provide consistent
    error handling and context preservation across the system.
    """

    def __init__(
        self,
        message: str,
        error_context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_context = error_context
        self.cause = cause
        self.error_code = error_code

    def __str__(self) -> str:
        """String representation with context information"""
        base_msg = self.message
        if self.error_context and self.error_context.location:
            location = self.error_context.location
            if location.line is not None and location.column is not None:
                base_msg = f"{base_msg} at line {location.line}, column {location.column}"
            elif location.expression:
                base_msg = f"{base_msg} in expression: {location.expression}"

        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"

        return base_msg


# =============================================================================
# Parsing Exceptions
# =============================================================================

class FHIRPathParseError(FHIRPathError):
    """Base exception for FHIRPath parsing errors"""
    pass


class FHIRPathSyntaxError(FHIRPathParseError):
    """Exception raised for FHIRPath syntax errors"""

    def __init__(
        self,
        message: str,
        expression: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        expected_tokens: Optional[List[str]] = None,
        error_context: Optional[ErrorContext] = None
    ):
        # Build location context if not provided
        if error_context is None and (line is not None or column is not None or expression):
            location = ErrorLocation(
                expression=expression,
                line=line,
                column=column
            )
            error_context = ErrorContext(
                location=location,
                severity=ErrorSeverity.ERROR,
                category="SYNTAX_ERROR",
                healthcare_context=None
            )

        super().__init__(message, error_context, error_code="FP001")
        self.expression = expression
        self.line = line
        self.column = column
        self.expected_tokens = expected_tokens or []


class FHIRPathGrammarError(FHIRPathParseError):
    """Exception raised for FHIRPath grammar violations"""

    def __init__(self, message: str, rule: str, error_context: Optional[ErrorContext] = None):
        super().__init__(message, error_context, error_code="FP002")
        self.rule = rule


class FHIRPathTokenError(FHIRPathParseError):
    """Exception raised for FHIRPath tokenization errors"""

    def __init__(self, message: str, token: str, position: int, error_context: Optional[ErrorContext] = None):
        super().__init__(message, error_context, error_code="FP003")
        self.token = token
        self.position = position


# =============================================================================
# Evaluation Exceptions
# =============================================================================

class FHIRPathEvaluationError(FHIRPathError):
    """Base exception for FHIRPath evaluation errors"""
    pass


class FHIRPathRuntimeError(FHIRPathEvaluationError):
    """Exception raised during FHIRPath expression evaluation"""

    def __init__(
        self,
        message: str,
        expression: Optional[str] = None,
        evaluation_context: Optional[Dict[str, Any]] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP010")
        self.expression = expression
        self.evaluation_context = evaluation_context or {}


class FHIRPathContextError(FHIRPathEvaluationError):
    """Exception raised for evaluation context errors"""

    def __init__(self, message: str, context_type: str, error_context: Optional[ErrorContext] = None):
        super().__init__(message, error_context, error_code="FP011")
        self.context_type = context_type


class FHIRPathFunctionError(FHIRPathEvaluationError):
    """Exception raised for function call errors"""

    def __init__(
        self,
        message: str,
        function_name: str,
        arguments: Optional[List[Any]] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP012")
        self.function_name = function_name
        self.arguments = arguments or []


class FHIRPathCollectionError(FHIRPathEvaluationError):
    """Exception raised for collection operation errors"""

    def __init__(
        self,
        message: str,
        operation: str,
        collection_type: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP013")
        self.operation = operation
        self.collection_type = collection_type


class FHIRPathPathNavigationError(FHIRPathEvaluationError):
    """Exception raised for path navigation errors"""

    def __init__(
        self,
        message: str,
        path: str,
        resource_type: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP014")
        self.path = path
        self.resource_type = resource_type


# =============================================================================
# Type System Exceptions
# =============================================================================

class FHIRPathTypeError(FHIRPathError):
    """Base exception for FHIRPath type system errors"""
    pass


class FHIRPathTypeValidationError(FHIRPathTypeError):
    """Exception raised for type validation failures"""

    def __init__(
        self,
        message: str,
        expected_type: str,
        actual_type: str,
        value: Optional[Any] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP020")
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.value = value


class FHIRPathTypeConversionError(FHIRPathTypeError):
    """Exception raised for type conversion failures"""

    def __init__(
        self,
        message: str,
        from_type: str,
        to_type: str,
        value: Optional[Any] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP021")
        self.from_type = from_type
        self.to_type = to_type
        self.value = value


class FHIRPathTypeMismatchError(FHIRPathTypeError):
    """Exception raised for type mismatches in operations"""

    def __init__(
        self,
        message: str,
        operation: str,
        left_type: str,
        right_type: str,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP022")
        self.operation = operation
        self.left_type = left_type
        self.right_type = right_type


class FHIRPathValidationError(FHIRPathError):
    """Exception raised for FHIRPath validation failures"""

    def __init__(
        self,
        message: str,
        validation_rule: str,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP030")
        self.validation_rule = validation_rule


# =============================================================================
# Translation Exceptions
# =============================================================================

class FHIRPathTranslationError(FHIRPathError):
    """Exception raised for FHIRPath translation (AST → SQL) errors."""

    def __init__(
        self,
        message: str,
        error_context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, error_context, cause, error_code="FP040")


# =============================================================================
# Healthcare-Specific Exceptions
# =============================================================================

class FHIRPathHealthcareError(FHIRPathError):
    """Base exception for healthcare-specific FHIRPath errors"""

    def __init__(
        self,
        message: str,
        error_context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message, error_context, cause, error_code or "FP040")


class FHIRPathResourceError(FHIRPathHealthcareError):
    """Exception raised for FHIR resource-related errors"""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP040")
        self.resource_type = resource_type
        self.resource_id = resource_id


class FHIRPathTerminologyError(FHIRPathHealthcareError):
    """Exception raised for terminology/coding errors"""

    def __init__(
        self,
        message: str,
        system: Optional[str] = None,
        code: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP041")
        self.system = system
        self.code = code


class FHIRPathComplianceError(FHIRPathHealthcareError):
    """Exception raised for FHIR specification compliance errors"""

    def __init__(
        self,
        message: str,
        specification: str,
        version: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP042")
        self.specification = specification
        self.version = version


# =============================================================================
# Database Exceptions
# =============================================================================

class FHIRPathDatabaseError(FHIRPathError):
    """Exception raised for database-related errors"""

    def __init__(
        self,
        message: str,
        database_type: Optional[str] = None,
        sql_state: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP050")
        self.database_type = database_type
        self.sql_state = sql_state


class FHIRPathDialectError(FHIRPathDatabaseError):
    """Exception raised for database dialect errors"""

    def __init__(
        self,
        message: str,
        dialect: str,
        feature: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP051")
        self.dialect = dialect
        self.feature = feature


# =============================================================================
# Execution Exceptions
# =============================================================================

class FHIRPathExecutionError(FHIRPathError):
    """Exception raised when the end-to-end execution pipeline fails."""

    def __init__(
        self,
        message: str,
        stage: str,
        expression: str,
        original_exception: Optional[Exception] = None,
        error_context: Optional[ErrorContext] = None,
    ):
        super().__init__(message, error_context, error_code="FP070")
        self.stage = stage
        self.expression = expression
        self.original_exception = original_exception

    def __str__(self) -> str:
        base = super().__str__()
        if self.stage:
            return f"[{self.stage}] {base}"
        return base


# =============================================================================
# Security Exceptions
# =============================================================================

class FHIRPathSecurityError(FHIRPathError):
    """Exception raised for security-related errors"""

    def __init__(
        self,
        message: str,
        security_context: Optional[str] = None,
        error_context: Optional[ErrorContext] = None
    ):
        super().__init__(message, error_context, error_code="FP060")
        self.security_context = security_context
