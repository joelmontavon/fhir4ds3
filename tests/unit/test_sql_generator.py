import pytest
from fhir4ds.sql import SQLGenerator
from fhir4ds.sql.exceptions import SQLGenerationError

@pytest.mark.unit
class TestSQLGenerator:

    def test_generator_initialization(self):
        """Test SQL generator initialization."""
        generator = SQLGenerator(dialect="duckdb")
        assert generator.dialect == "duckdb"

        generator = SQLGenerator(dialect="postgresql")
        assert generator.dialect == "postgresql"

    def test_basic_sql_generation(self):
        """Test basic SQL generation from ViewDefinition."""
        generator = SQLGenerator(dialect="duckdb")

        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"path": "name.family", "name": "family_name"}]}
            ]
        }

        sql = generator.generate_sql(view_def)
        assert "json_extract" in sql.lower()
        assert "family_name" in sql
        assert "name" in sql

    def test_multi_database_support(self):
        """Test SQL generation for different database dialects."""
        duckdb_gen = SQLGenerator(dialect="duckdb")
        postgresql_gen = SQLGenerator(dialect="postgresql")

        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"path": "name.family", "name": "family_name"}]}
            ]
        }

        duckdb_sql = duckdb_gen.generate_sql(view_def)
        postgresql_sql = postgresql_gen.generate_sql(view_def)

        # Should generate different SQL for different databases
        assert duckdb_sql != postgresql_sql

        # DuckDB should use json_extract
        assert "json_extract" in duckdb_sql.lower()

        # PostgreSQL should use different JSON syntax
        assert ("resource->>" in postgresql_sql or "resource->" in postgresql_sql)

    def test_function_handling(self):
        """Test SQL generation for FHIRPath first() function in ViewDefinitions."""
        generator = SQLGenerator(dialect="duckdb")

        # Test first() function - should use array indexing, not LIMIT 1
        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"path": "name.first()", "name": "first_name"}]}
            ]
        }

        sql = generator.generate_sql(view_def)
        # Should use array indexing [0], not LIMIT 1 (population-friendly)
        assert "[0]" in sql
        assert "LIMIT 1" not in sql.upper()  # Architectural compliance check

    def test_type_conversion_support(self):
        """Test type conversion for different column types."""
        generator = SQLGenerator(dialect="duckdb")

        # Test boolean type conversion
        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"path": "active", "name": "is_active", "type": "boolean"}]}
            ]
        }

        sql = generator.generate_sql(view_def)
        assert "BOOLEAN" in sql.upper() or "boolean" in sql.lower()

    def test_error_handling(self):
        """Test error handling for invalid ViewDefinitions."""
        generator = SQLGenerator(dialect="duckdb")

        # Empty ViewDefinition
        with pytest.raises(SQLGenerationError):
            generator.generate_sql({})

        # ViewDefinition with no columns
        with pytest.raises(SQLGenerationError):
            generator.generate_sql({"select": [{"column": []}]})

    def test_statistics_tracking(self):
        """Test usage statistics tracking."""
        generator = SQLGenerator(dialect="duckdb")

        initial_stats = generator.get_statistics()
        assert initial_stats["generation_count"] == 0
        assert initial_stats["dialect"] == "duckdb"

        # Note: statistics were used by removed generate_from_fhirpath method
        # This test validates the statistics interface still works
        stats = generator.get_statistics()
        assert "dialect" in stats
        assert "generation_count" in stats

    @pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
    def test_dialect_consistency(self, dialect):
        """Test basic functionality across all supported databases."""
        generator = SQLGenerator(dialect=dialect)

        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"path": "name.family", "name": "family_name"}]}
            ]
        }

        sql = generator.generate_sql(view_def)

        # Validate SQL is generated
        assert sql is not None
        assert len(sql) > 0
        assert "family_name" in sql

        # Both dialects should work (specific syntax tested in other tests)

    def test_two_columns_basic(self):
        """Test SQL generation with two columns - regression test for SP-019-004."""
        generator = SQLGenerator(dialect="duckdb")

        view_def = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"name": "id", "path": "id", "type": "id"},
                        {"name": "last_name", "path": "name.family.first()", "type": "string"}
                    ]
                }
            ]
        }

        sql = generator.generate_sql(view_def)

        # Both columns should be in the SQL
        assert "id" in sql
        assert "last_name" in sql

        # For DuckDB, should use json_extract_string for both
        assert "json_extract_string" in sql

        # Should have correct JSON paths
        assert "$.id" in sql
        assert "$.name[0].family" in sql

        # Should only have one SELECT statement
        assert sql.count("SELECT") == 1

    def test_two_columns_mixed_types(self):
        """Test two columns with different types."""
        generator = SQLGenerator(dialect="duckdb")

        view_def = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"name": "id", "path": "id", "type": "string"},
                        {"name": "active", "path": "active", "type": "boolean"}
                    ]
                }
            ]
        }

        sql = generator.generate_sql(view_def)

        # Both columns should be present
        assert "id" in sql
        assert "active" in sql

        # String should use json_extract_string
        assert "json_extract_string" in sql

        # Boolean should use BOOLEAN cast
        assert "BOOLEAN" in sql or "boolean" in sql

    def test_path_with_nested_first(self):
        """Test path conversion for name.family.first() pattern."""
        generator = SQLGenerator(dialect="duckdb")

        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"name": "family", "path": "name.family.first()", "type": "string"}]}
            ]
        }

        sql = generator.generate_sql(view_def)

        # Should generate correct JSON path with [0] in the right place
        # name.family.first() should become $.name[0].family (not $.name.family[0])
        assert "$.name[0].family" in sql

    def test_simple_first_function(self):
        """Test simple .first() at the end of path."""
        generator = SQLGenerator(dialect="duckdb")

        view_def = {
            "resource": "Patient",
            "select": [
                {"column": [{"name": "first_name", "path": "name.first()", "type": "string"}]}
            ]
        }

        sql = generator.generate_sql(view_def)

        # Should generate $.name[0]
        assert "$.name[0]" in sql

    def test_needs_fhirpath_translation_logic(self):
        """Test that simple .first() doesn't trigger FHIRPath translator."""
        generator = SQLGenerator(dialect="duckdb")

        # Simple .first() at end should NOT need translation
        assert not generator._needs_fhirpath_translation("name.family.first()")
        assert not generator._needs_fhirpath_translation("name.first()")

        # Complex functions should need translation
        assert generator._needs_fhirpath_translation("name.where(use='official')")
        assert generator._needs_fhirpath_translation("extension.ofType(Extension)")

        # .first() in the middle should need translation
        assert generator._needs_fhirpath_translation("name.first().family")
