"""
This file contains shared fixtures and configuration for the pytest framework.

Fixtures defined here are accessible to all tests in the suite.

Markers:
- unit: Mark a test as a unit test.
- integration: Mark a test as an integration test.
- compliance: Mark a test as a compliance test.
- slow: Mark a test as slow to run.
- postgresql: Mark a test as requiring a PostgreSQL database.
- duckdb: Mark a test as requiring a DuckDB database.
"""
import pytest
from unittest.mock import MagicMock

def pytest_configure(config):
    """
    Dynamically configure pytest markers.
    """
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "compliance: marks tests as compliance tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "postgresql: marks tests requiring PostgreSQL")
    config.addinivalue_line("markers", "duckdb: marks tests requiring DuckDB")

@pytest.fixture(scope="session")
def duckdb_conn():
    """
    Fixture for creating and cleaning up a DuckDB database connection.
    """
    import duckdb
    print("Setting up DuckDB connection")
    conn = duckdb.connect(':memory:')
    yield conn
    print("Tearing down DuckDB connection")
    conn.close()

@pytest.fixture(scope="session")
def postgresql_conn():
    """
    Fixture for creating and cleaning up a PostgreSQL database connection.
    """
    # Placeholder for PostgreSQL connection setup
    print("Setting up PostgreSQL connection")
    conn = None  # Replace with actual PostgreSQL connection
    yield conn
    print("Tearing down PostgreSQL connection")
    # Add cleanup logic here if needed


@pytest.fixture
def duckdb_dialect():
    """
    Provide an in-memory DuckDB dialect for SQL translation tests.
    """
    from fhir4ds.dialects.duckdb import DuckDBDialect

    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect(monkeypatch):
    """
    Provide a PostgreSQL dialect with a stubbed psycopg2 connection.

    The translator only needs dialect SQL generation methods, so we replace the
    database connection with a lightweight stub to keep tests fast and isolated.
    """
    psycopg2 = pytest.importorskip("psycopg2")

    # Create lightweight stub cursor/connection objects
    stub_cursor = MagicMock()
    stub_cursor.fetchall.return_value = []
    stub_cursor.__enter__.return_value = stub_cursor
    stub_cursor.__exit__.return_value = False

    stub_connection = MagicMock()
    stub_connection.cursor.return_value = stub_cursor

    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: stub_connection)

    from fhir4ds.dialects.postgresql import PostgreSQLDialect

    return PostgreSQLDialect("postgresql://stub:stub@localhost:5432/postgres")
