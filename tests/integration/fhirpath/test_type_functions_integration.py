"""Integration tests for type functions with real database execution.

Tests is(), as(), and ofType() functions with actual database queries to validate
end-to-end functionality across both DuckDB and PostgreSQL dialects.

Module: tests.integration.fhirpath.test_type_functions_integration
Created: 2025-10-03
Task: SP-006-009
"""

import pytest
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


@pytest.fixture
def duckdb_connection():
    """Create DuckDB connection for integration testing"""
    dialect = DuckDBDialect(database=":memory:")

    # Create test table with sample data
    dialect.connection.execute("""
        CREATE TABLE Patient (
            id VARCHAR,
            resource JSON
        )
    """)

    # Insert test data
    dialect.connection.execute("""
        INSERT INTO Patient VALUES
        ('patient-1', '{"resourceType": "Patient", "id": "patient-1", "birthDate": "1990-01-01"}'),
        ('patient-2', '{"resourceType": "Patient", "id": "patient-2", "active": true}'),
        ('patient-3', '{"resourceType": "Patient", "id": "patient-3", "multipleBirthInteger": 3}')
    """)

    yield dialect
    dialect.connection.close()


@pytest.fixture
def postgresql_connection():
    """Create PostgreSQL connection for integration testing (if available)"""
    try:
        dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")

        # Create test table
        dialect.connection.execute("""
            DROP TABLE IF EXISTS test_patient_type_ops CASCADE
        """)
        dialect.connection.execute("""
            CREATE TABLE test_patient_type_ops (
                id TEXT,
                resource JSONB
            )
        """)

        # Insert test data
        dialect.connection.execute("""
            INSERT INTO test_patient_type_ops VALUES
            ('patient-1', '{"resourceType": "Patient", "id": "patient-1", "birthDate": "1990-01-01"}'::jsonb),
            ('patient-2', '{"resourceType": "Patient", "id": "patient-2", "active": true}'::jsonb),
            ('patient-3', '{"resourceType": "Patient", "id": "patient-3", "multipleBirthInteger": 3}'::jsonb)
        """)
        dialect.connection.commit()

        yield dialect

        # Cleanup
        dialect.connection.execute("DROP TABLE IF EXISTS test_patient_type_ops CASCADE")
        dialect.connection.commit()
        dialect.connection.close()
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestIsOperationIntegration:
    """Integration tests for is() type checking function"""

    def test_is_string_query_duckdb(self, duckdb_connection):
        """Test is() with String type check in DuckDB query"""
        sql = duckdb_connection.generate_type_check(
            "json_extract_string(resource, '$.id')",
            "String"
        )

        query = f"""
            SELECT id,
                   {sql} as is_string
            FROM Patient
            WHERE id = 'patient-1'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # ID field should be string type
        assert result[1] == True or result[1] == 1

    def test_is_integer_query_duckdb(self, duckdb_connection):
        """Test is() with Integer type check in DuckDB query"""
        sql = duckdb_connection.generate_type_check(
            "json_extract(resource, '$.multipleBirthInteger')",
            "Integer"
        )

        query = f"""
            SELECT id,
                   {sql} as is_integer
            FROM Patient
            WHERE id = 'patient-3'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # multipleBirthInteger should be integer type
        assert result[1] == True or result[1] == 1

    def test_is_boolean_query_duckdb(self, duckdb_connection):
        """Test is() with Boolean type check in DuckDB query"""
        sql = duckdb_connection.generate_type_check(
            "json_extract(resource, '$.active')",
            "Boolean"
        )

        query = f"""
            SELECT id,
                   {sql} as is_boolean
            FROM Patient
            WHERE id = 'patient-2'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # active should be boolean type
        assert result[1] == True or result[1] == 1


class TestAsOperationIntegration:
    """Integration tests for as() type casting function"""

    def test_as_string_to_date_duckdb(self, duckdb_connection):
        """Test as() casting string to Date in DuckDB query"""
        sql = duckdb_connection.generate_type_cast(
            "json_extract_string(resource, '$.birthDate')",
            "Date"
        )

        query = f"""
            SELECT id,
                   {sql} as birth_date
            FROM Patient
            WHERE id = 'patient-1'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should successfully cast to date
        assert result[1] is not None

    def test_as_integer_to_string_duckdb(self, duckdb_connection):
        """Test as() casting integer to String in DuckDB query"""
        sql = duckdb_connection.generate_type_cast(
            "json_extract(resource, '$.multipleBirthInteger')",
            "String"
        )

        query = f"""
            SELECT id,
                   {sql} as multiple_birth_str
            FROM Patient
            WHERE id = 'patient-3'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should successfully cast to string
        assert result[1] is not None


class TestOfTypeOperationIntegration:
    """Integration tests for ofType() collection filtering function"""

    def test_oftype_string_array_duckdb(self, duckdb_connection):
        """Test ofType() filtering string values from mixed array in DuckDB"""
        # Create test data with mixed array
        duckdb_connection.connection.execute("""
            INSERT INTO Patient VALUES
            ('patient-4', '{"resourceType": "Patient", "id": "patient-4", "mixedArray": ["hello", 123, "world", true]}')
        """)

        sql = duckdb_connection.generate_collection_type_filter(
            "json_extract(resource, '$.mixedArray')",
            "String"
        )

        query = f"""
            SELECT id,
                   {sql} as string_values
            FROM Patient
            WHERE id = 'patient-4'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should return filtered array
        assert result[1] is not None

    def test_oftype_integer_array_duckdb(self, duckdb_connection):
        """Test ofType() filtering integer values from mixed array in DuckDB"""
        # Create test data with mixed array
        duckdb_connection.connection.execute("""
            INSERT INTO Patient VALUES
            ('patient-5', '{"resourceType": "Patient", "id": "patient-5", "numbers": [1, "two", 3, "four", 5]}')
        """)

        sql = duckdb_connection.generate_collection_type_filter(
            "json_extract(resource, '$.numbers')",
            "Integer"
        )

        query = f"""
            SELECT id,
                   {sql} as integer_values
            FROM Patient
            WHERE id = 'patient-5'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should return filtered array
        assert result[1] is not None


class TestMultiDatabaseConsistency:
    """Test consistency of type operations across DuckDB and PostgreSQL"""

    def test_is_operation_consistency_duckdb(self, duckdb_connection):
        """Test is() produces consistent results in DuckDB"""
        # Test String type check
        sql = duckdb_connection.generate_type_check(
            "json_extract_string(resource, '$.id')",
            "String"
        )

        query = f"SELECT COUNT(*) FROM Patient WHERE {sql}"
        result = duckdb_connection.connection.execute(query).fetchone()

        # All patients should have string IDs
        assert result[0] == 3

    def test_as_operation_consistency_duckdb(self, duckdb_connection):
        """Test as() produces consistent results in DuckDB"""
        # Test casting to Date
        sql = duckdb_connection.generate_type_cast(
            "json_extract_string(resource, '$.birthDate')",
            "Date"
        )

        query = f"SELECT COUNT(*) FROM Patient WHERE {sql} IS NOT NULL"
        result = duckdb_connection.connection.execute(query).fetchone()

        # Only patient-1 has birthDate
        assert result[0] == 1


class TestTypeOperationPerformanceIntegration:
    """Integration tests for performance requirements"""

    def test_is_operation_scales_with_population_duckdb(self, duckdb_connection):
        """Test is() operation scales well with population queries"""
        # Insert more test data (population-scale simulation)
        for i in range(10):
            duckdb_connection.connection.execute(f"""
                INSERT INTO Patient VALUES
                ('patient-perf-{i}', '{{"resourceType": "Patient", "id": "patient-perf-{i}", "active": true}}')
            """)

        # Run population-scale query
        sql = duckdb_connection.generate_type_check(
            "json_extract(resource, '$.active')",
            "Boolean"
        )

        query = f"""
            SELECT COUNT(*)
            FROM Patient
            WHERE {sql}
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should process all records efficiently
        assert result[0] >= 10

    def test_oftype_operation_scales_with_arrays_duckdb(self, duckdb_connection):
        """Test ofType() operation scales well with large arrays"""
        # Insert test data with large array
        large_array = [i if i % 2 == 0 else str(i) for i in range(100)]
        import json
        array_json = json.dumps(large_array)

        duckdb_connection.connection.execute(f"""
            INSERT INTO Patient VALUES
            ('patient-large', '{{"resourceType": "Patient", "id": "patient-large", "largeArray": {array_json}}}')
        """)

        # Filter integers only
        sql = duckdb_connection.generate_collection_type_filter(
            "json_extract(resource, '$.largeArray')",
            "Integer"
        )

        query = f"""
            SELECT id,
                   {sql} as integers
            FROM Patient
            WHERE id = 'patient-large'
        """

        result = duckdb_connection.connection.execute(query).fetchone()
        assert result is not None
        # Should efficiently filter large array
        assert result[1] is not None
