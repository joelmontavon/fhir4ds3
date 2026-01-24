"""
SQL generation exceptions for error handling.
"""


class SQLGenerationError(Exception):
    """Base exception for SQL generation operations."""
    pass


class UnsupportedDialectError(SQLGenerationError):
    """Exception raised when unsupported database dialect is used."""
    pass


class InvalidExpressionError(SQLGenerationError):
    """Exception raised when FHIRPath expression cannot be converted to SQL."""
    pass


class UndefinedConstantError(SQLGenerationError):
    """Exception raised when FHIRPath expression references undefined constant."""
    pass