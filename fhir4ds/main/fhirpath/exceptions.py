"""
FHIRPath parsing and evaluation exceptions for error handling.
"""


class FHIRPathError(Exception):
    """Base exception for FHIRPath operations."""
    pass


class FHIRPathParseError(FHIRPathError):
    """Exception raised when FHIRPath expression cannot be parsed."""
    pass


class FHIRPathEvaluationError(FHIRPathError):
    """Exception raised when FHIRPath expression evaluation fails."""
    pass


class FHIRPathTypeError(FHIRPathError):
    """Exception raised when FHIRPath type operations fail."""
    pass


class FHIRPathValidationError(FHIRPathError):
    """Exception raised when FHIRPath validation fails."""
    pass


class FHIRPathTranslationError(FHIRPathError):
    """Exception raised when FHIRPath translation fails."""
    pass
