"""
Database Dialect Abstraction for FHIR4DS

This module provides database-specific implementations for SQL generation
following the thin dialect architecture principle: business logic in the
FHIRPath evaluator, only syntax differences in database dialects.
"""

from .base import DatabaseDialect
from .factory import DialectFactory
from .duckdb import DuckDBDialect
from .postgresql import PostgreSQLDialect

__all__ = [
    'DatabaseDialect',
    'DialectFactory',
    'DuckDBDialect',
    'PostgreSQLDialect'
]