"""
Error Context Preservation and Reporting

This module provides comprehensive error context preservation for FHIRPath errors,
including location information, healthcare context, and security-conscious error reporting.
"""

from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import logging


class ErrorSeverity(Enum):
    """Severity levels for FHIRPath errors"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorLocation:
    """Location information for FHIRPath errors"""
    expression: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    character_position: Optional[int] = None
    context_expression: Optional[str] = None

    def __str__(self) -> str:
        """String representation of error location"""
        parts = []
        if self.line is not None and self.column is not None:
            parts.append(f"line {self.line}, column {self.column}")
        elif self.character_position is not None:
            parts.append(f"position {self.character_position}")

        if self.expression:
            # Truncate long expressions for readability
            expr = self.expression
            if len(expr) > 50:
                expr = expr[:47] + "..."
            parts.append(f"in expression: {expr}")

        return ", ".join(parts) if parts else "unknown location"


@dataclass
class HealthcareErrorContext:
    """Healthcare-specific error context"""
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    patient_context: Optional[bool] = None
    clinical_domain: Optional[str] = None
    measure_context: Optional[str] = None
    terminology_context: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Initialize nested dictionaries"""
        if self.terminology_context is None:
            self.terminology_context = {}


@dataclass
class ErrorContext:
    """Comprehensive error context for FHIRPath operations"""
    location: Optional[ErrorLocation] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: Optional[str] = None
    operation: Optional[str] = None
    evaluation_context: Optional[Dict[str, Any]] = field(default_factory=dict)
    healthcare_context: Optional[HealthcareErrorContext] = None
    stack_trace: Optional[List[str]] = field(default_factory=list)
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None

    def add_stack_frame(self, frame: str) -> None:
        """Add a stack frame to the error context"""
        if self.stack_trace is None:
            self.stack_trace = []
        self.stack_trace.append(frame)

    def get_sanitized_context(self) -> Dict[str, Any]:
        """Get sanitized context for logging (removes sensitive data)"""
        return {
            "location": str(self.location) if self.location else None,
            "severity": self.severity.value,
            "category": self.category,
            "operation": self.operation,
            "healthcare_resource_type": self.healthcare_context.resource_type if self.healthcare_context else None,
            "clinical_domain": self.healthcare_context.clinical_domain if self.healthcare_context else None,
            "stack_depth": len(self.stack_trace) if self.stack_trace else 0,
            "correlation_id": self.correlation_id
        }


def build_error_context(
    expression: Optional[str] = None,
    line: Optional[int] = None,
    column: Optional[int] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: Optional[str] = None,
    operation: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    evaluation_context: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> ErrorContext:
    """
    Build comprehensive error context from available information

    Args:
        expression: The FHIRPath expression being evaluated
        line: Line number where error occurred
        column: Column number where error occurred
        severity: Error severity level
        category: Error category/type
        operation: The operation being performed
        resource_type: FHIR resource type being processed
        resource_id: FHIR resource ID (will be sanitized)
        evaluation_context: Additional evaluation context
        correlation_id: Correlation ID for request tracing

    Returns:
        ErrorContext: Comprehensive error context object
    """
    location = None
    if expression or line is not None or column is not None:
        location = ErrorLocation(
            expression=expression,
            line=line,
            column=column
        )

    healthcare_context = None
    if resource_type or resource_id:
        healthcare_context = HealthcareErrorContext(
            resource_type=resource_type,
            # Sanitize resource ID for security
            resource_id=_sanitize_resource_id(resource_id) if resource_id else None
        )

    return ErrorContext(
        location=location,
        severity=severity,
        category=category,
        operation=operation,
        evaluation_context=evaluation_context or {},
        healthcare_context=healthcare_context,
        correlation_id=correlation_id
    )


def sanitize_error_for_logging(
    error: Exception,
    include_stack_trace: bool = False,
    max_message_length: int = 200
) -> Dict[str, Any]:
    """
    Sanitize error information for secure logging

    Removes sensitive information while preserving debugging context.

    Args:
        error: The exception to sanitize
        include_stack_trace: Whether to include stack trace
        max_message_length: Maximum length for error messages

    Returns:
        Dict containing sanitized error information
    """
    from .fhirpath_exceptions import FHIRPathError

    sanitized = {
        "error_type": type(error).__name__,
        "error_code": None,
        "error_message": _sanitize_error_message(str(error), max_message_length),  # Changed from 'message' to avoid LogRecord conflict
        "severity": "error",
        "category": "unknown"
    }

    # Add FHIRPath-specific context
    if isinstance(error, FHIRPathError):
        sanitized["error_code"] = error.error_code
        if error.error_context:
            sanitized.update(error.error_context.get_sanitized_context())

    # Add stack trace if requested (be careful with sensitive data)
    if include_stack_trace and hasattr(error, '__traceback__'):
        import traceback
        sanitized["stack_trace"] = _sanitize_stack_trace(
            traceback.format_tb(error.__traceback__)
        )

    return sanitized


def _sanitize_resource_id(resource_id: str) -> str:
    """
    Sanitize resource ID for logging

    Preserves enough information for debugging while protecting privacy.
    """
    if not resource_id:
        return ""

    # For UUID-style IDs, show first 8 characters
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', resource_id.lower()):
        return f"{resource_id[:8]}..."

    # For other IDs, show prefix and length
    if len(resource_id) <= 8:
        return "***"
    else:
        return f"{resource_id[:3]}...({len(resource_id)} chars)"


def _sanitize_error_message(message: str, max_length: int) -> str:
    """
    Sanitize error message for logging

    Removes potentially sensitive data while preserving error context.
    """
    if not message:
        return ""

    # Remove potential patient identifiers (basic patterns)
    message = re.sub(r'\b\d{9,}\b', '[ID]', message)  # Long numbers (SSN, etc.)
    message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)  # Email
    message = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', message)  # SSN format

    # Truncate if too long
    if len(message) > max_length:
        message = message[:max_length - 3] + "..."

    return message


def _sanitize_stack_trace(stack_frames: List[str]) -> List[str]:
    """
    Sanitize stack trace for logging

    Removes file paths and other sensitive information while preserving
    debugging context.
    """
    sanitized_frames = []
    for frame in stack_frames:
        # Remove full file paths, keep only filename
        frame = re.sub(r'/[^/]+/[^/]+/', '.../', frame)
        # Remove potential sensitive data from variable values
        frame = re.sub(r"'[^']{50,}'", "'[LONG_VALUE]'", frame)
        sanitized_frames.append(frame)
    return sanitized_frames


# Logging utilities
def log_fhirpath_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[ErrorContext] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log FHIRPath error with proper sanitization

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional error context
        extra_data: Additional data to include
    """
    log_data = sanitize_error_for_logging(error)

    if context:
        log_data.update(context.get_sanitized_context())

    if extra_data:
        # Sanitize extra data
        sanitized_extra = {}
        for key, value in extra_data.items():
            if isinstance(value, str):
                sanitized_extra[key] = _sanitize_error_message(str(value), 100)
            elif isinstance(value, (int, float, bool)):
                sanitized_extra[key] = value
            else:
                sanitized_extra[key] = f"<{type(value).__name__}>"
        log_data.update(sanitized_extra)

    # Log at appropriate level
    severity = log_data.get("severity", "error")
    log_method = getattr(logger, severity, logger.error)
    log_method("FHIRPath error occurred", extra=log_data)