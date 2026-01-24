"""
Dialect factory for runtime database dialect selection.

This module provides the factory pattern for creating database dialect instances
based on runtime configuration, supporting the unified FHIRPath architecture.
"""

import logging
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from .base import DatabaseDialect
from .duckdb import DuckDBDialect
from .postgresql import PostgreSQLDialect

logger = logging.getLogger(__name__)


class DialectFactory:
    """
    Factory for creating database dialect instances.

    Supports runtime dialect selection based on connection strings or
    explicit database type specification, enabling the unified FHIRPath
    architecture to work across multiple database platforms.
    """

    # Registry of available dialects
    _dialects: Dict[str, type] = {
        'duckdb': DuckDBDialect,
        'postgresql': PostgreSQLDialect,
        'postgres': PostgreSQLDialect,  # Alias
    }

    @classmethod
    def create_dialect(cls, database_type: str = None, connection_string: str = None,
                      **kwargs) -> DatabaseDialect:
        """
        Create a database dialect instance.

        Args:
            database_type: Explicit database type ('duckdb', 'postgresql')
            connection_string: Database connection string (for auto-detection)
            **kwargs: Additional arguments passed to dialect constructor

        Returns:
            DatabaseDialect instance

        Raises:
            ValueError: If database type cannot be determined or is unsupported
            ImportError: If required database driver is not available
        """
        # Auto-detect database type from connection string if not specified
        if database_type is None and connection_string is not None:
            database_type = cls._detect_database_type(connection_string)

        if database_type is None:
            raise ValueError("Database type must be specified or detectable from connection string")

        database_type = database_type.lower()

        if database_type not in cls._dialects:
            available = ', '.join(cls._dialects.keys())
            raise ValueError(f"Unsupported database type '{database_type}'. Available: {available}")

        dialect_class = cls._dialects[database_type]

        try:
            # Create dialect instance with appropriate arguments
            if database_type == 'duckdb':
                return cls._create_duckdb_dialect(dialect_class, connection_string, **kwargs)
            elif database_type in ('postgresql', 'postgres'):
                return cls._create_postgresql_dialect(dialect_class, connection_string, **kwargs)
            else:
                # Generic dialect creation
                return dialect_class(connection_string, **kwargs)

        except Exception as e:
            logger.error(f"Failed to create {database_type} dialect: {e}")
            raise

    @classmethod
    def _detect_database_type(cls, connection_string: str) -> Optional[str]:
        """
        Detect database type from connection string.

        Args:
            connection_string: Database connection string

        Returns:
            Database type or None if not detectable
        """
        if not connection_string:
            return None

        # Handle file paths and memory databases for DuckDB
        if (connection_string == ':memory:' or
            connection_string.endswith('.db') or
            connection_string.endswith('.duckdb')):
            return 'duckdb'

        # Handle relative/absolute file paths for DuckDB (but not URLs)
        if ('/' in connection_string and
            not connection_string.startswith(('postgres', 'postgresql', 'http', 'ftp', 'file')) and
            '://' not in connection_string):
            return 'duckdb'

        # Parse as URL
        try:
            parsed = urlparse(connection_string)
            scheme = parsed.scheme.lower()

            if scheme in ('postgresql', 'postgres'):
                return 'postgresql'
            elif scheme in ('duckdb', 'duck'):
                return 'duckdb'

        except Exception:
            pass

        # Default fallback
        logger.warning(f"Could not detect database type from connection string: {connection_string}")
        return None

    @classmethod
    def _create_duckdb_dialect(cls, dialect_class: type, connection_string: str = None,
                              **kwargs) -> DuckDBDialect:
        """Create DuckDB dialect with appropriate arguments."""
        # DuckDB specific arguments
        database = kwargs.pop('database', connection_string or ':memory:')
        connection = kwargs.pop('connection', None)

        return dialect_class(connection=connection, database=database, **kwargs)

    @classmethod
    def _create_postgresql_dialect(cls, dialect_class: type, connection_string: str,
                                  **kwargs) -> PostgreSQLDialect:
        """Create PostgreSQL dialect with appropriate arguments."""
        if not connection_string:
            raise ValueError("PostgreSQL dialect requires a connection string")

        return dialect_class(connection_string=connection_string, **kwargs)

    @classmethod
    def register_dialect(cls, name: str, dialect_class: type) -> None:
        """
        Register a new dialect class.

        Args:
            name: Dialect name for factory lookup
            dialect_class: Dialect class inheriting from DatabaseDialect
        """
        if not issubclass(dialect_class, DatabaseDialect):
            raise ValueError(f"Dialect class must inherit from DatabaseDialect")

        cls._dialects[name.lower()] = dialect_class
        logger.info(f"Registered dialect: {name}")

    @classmethod
    def get_available_dialects(cls) -> Dict[str, type]:
        """
        Get available dialect classes.

        Returns:
            Dictionary of dialect name to class mappings
        """
        return cls._dialects.copy()

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> DatabaseDialect:
        """
        Create dialect from configuration dictionary.

        Args:
            config: Configuration containing 'type' and connection parameters

        Returns:
            DatabaseDialect instance

        Example:
            config = {
                'type': 'postgresql',
                'connection_string': 'postgresql://user:pass@localhost/db'
            }
        """
        database_type = config.get('type')
        connection_string = config.get('connection_string')

        # Remove factory-specific keys from kwargs
        kwargs = {k: v for k, v in config.items() if k not in ('type', 'connection_string')}

        return cls.create_dialect(
            database_type=database_type,
            connection_string=connection_string,
            **kwargs
        )


# Convenience functions for common use cases

def create_duckdb_dialect(database: str = ':memory:', connection: Any = None) -> DuckDBDialect:
    """
    Create DuckDB dialect instance.

    Args:
        database: Database file path or ':memory:'
        connection: Existing DuckDB connection (optional)

    Returns:
        DuckDBDialect instance
    """
    return DialectFactory.create_dialect('duckdb', database=database, connection=connection)


def create_postgresql_dialect(connection_string: str) -> PostgreSQLDialect:
    """
    Create PostgreSQL dialect instance.

    Args:
        connection_string: PostgreSQL connection string

    Returns:
        PostgreSQLDialect instance
    """
    return DialectFactory.create_dialect('postgresql', connection_string=connection_string)


def detect_and_create_dialect(connection_string: str, **kwargs) -> DatabaseDialect:
    """
    Auto-detect database type and create dialect.

    Args:
        connection_string: Database connection string
        **kwargs: Additional arguments for dialect

    Returns:
        DatabaseDialect instance
    """
    return DialectFactory.create_dialect(connection_string=connection_string, **kwargs)