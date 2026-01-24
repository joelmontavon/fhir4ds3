"""Unit tests for SQLFragment data structure.

This test module provides comprehensive coverage of the SQLFragment dataclass,
including instantiation, validation, methods, and edge cases.

Test Coverage:
- SQLFragment instantiation with all field combinations
- Default field values
- Field validation in __post_init__
- Dependency management methods
- Metadata management methods
- Edge cases (empty strings, None values, etc.)

Module: tests.unit.fhirpath.sql.test_fragments
Related: fhir4ds.fhirpath.sql.fragments
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-29
"""

import pytest
from fhir4ds.fhirpath.sql.fragments import SQLFragment


class TestSQLFragmentInstantiation:
    """Test SQLFragment instantiation and initialization."""

    def test_minimal_instantiation(self):
        """Test SQLFragment with only required fields."""
        fragment = SQLFragment(expression="SELECT * FROM patient")

        assert fragment.expression == "SELECT * FROM patient"
        assert fragment.source_table == "resource"  # Default value
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert fragment.dependencies == []
        assert fragment.metadata == {}

    def test_full_instantiation(self):
        """Test SQLFragment with all fields specified."""
        fragment = SQLFragment(
            expression="SELECT id, name FROM cte_1",
            source_table="cte_1",
            requires_unnest=True,
            is_aggregate=False,
            dependencies=["patient_resources"],
            metadata={"estimated_rows": 1000}
        )

        assert fragment.expression == "SELECT id, name FROM cte_1"
        assert fragment.source_table == "cte_1"
        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is False
        assert fragment.dependencies == ["patient_resources"]
        assert fragment.metadata == {"estimated_rows": 1000}

    def test_aggregate_fragment(self):
        """Test SQLFragment with is_aggregate flag set."""
        fragment = SQLFragment(
            expression="SELECT COUNT(*) FROM patient",
            source_table="patient",
            is_aggregate=True
        )

        assert fragment.is_aggregate is True
        assert fragment.requires_unnest is False

    def test_unnest_fragment(self):
        """Test SQLFragment with requires_unnest flag set."""
        fragment = SQLFragment(
            expression="SELECT * FROM resource, LATERAL UNNEST(names) AS name_item",
            source_table="resource",
            requires_unnest=True
        )

        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is False


class TestSQLFragmentValidation:
    """Test SQLFragment validation in __post_init__."""

    def test_empty_expression_raises_error(self):
        """Test that empty expression raises ValueError."""
        with pytest.raises(ValueError, match="expression must be a non-empty string"):
            SQLFragment(expression="")

    def test_none_expression_raises_error(self):
        """Test that None expression raises ValueError."""
        with pytest.raises(ValueError, match="expression must be a non-empty string"):
            SQLFragment(expression=None)

    def test_empty_source_table_raises_error(self):
        """Test that empty source_table raises ValueError."""
        with pytest.raises(ValueError, match="source_table must be a non-empty string"):
            SQLFragment(expression="SELECT * FROM patient", source_table="")

    def test_none_source_table_raises_error(self):
        """Test that None source_table raises ValueError."""
        with pytest.raises(ValueError, match="source_table must be a non-empty string"):
            SQLFragment(expression="SELECT * FROM patient", source_table=None)

    def test_invalid_dependencies_type_raises_error(self):
        """Test that non-list dependencies raises ValueError."""
        with pytest.raises(ValueError, match="dependencies must be a list"):
            SQLFragment(
                expression="SELECT * FROM patient",
                dependencies="not_a_list"
            )

    def test_invalid_metadata_type_raises_error(self):
        """Test that non-dict metadata raises ValueError."""
        with pytest.raises(ValueError, match="metadata must be a dictionary"):
            SQLFragment(
                expression="SELECT * FROM patient",
                metadata="not_a_dict"
            )


class TestSQLFragmentDependencyManagement:
    """Test SQLFragment dependency management methods."""

    def test_add_dependency(self):
        """Test adding a single dependency."""
        fragment = SQLFragment(expression="SELECT * FROM cte_1")
        fragment.add_dependency("patient_resources")

        assert "patient_resources" in fragment.dependencies
        assert len(fragment.dependencies) == 1

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        fragment = SQLFragment(expression="SELECT * FROM cte_2")
        fragment.add_dependency("cte_1")
        fragment.add_dependency("patient_resources")

        assert "cte_1" in fragment.dependencies
        assert "patient_resources" in fragment.dependencies
        assert len(fragment.dependencies) == 2

    def test_add_duplicate_dependency_ignored(self):
        """Test that adding duplicate dependency is ignored."""
        fragment = SQLFragment(expression="SELECT * FROM cte_1")
        fragment.add_dependency("patient_resources")
        fragment.add_dependency("patient_resources")  # Duplicate

        assert len(fragment.dependencies) == 1
        assert fragment.dependencies == ["patient_resources"]

    def test_dependencies_initialized_with_values(self):
        """Test dependencies can be initialized with values."""
        fragment = SQLFragment(
            expression="SELECT * FROM cte_2",
            dependencies=["cte_1", "patient_resources"]
        )

        assert len(fragment.dependencies) == 2
        assert "cte_1" in fragment.dependencies
        assert "patient_resources" in fragment.dependencies


class TestSQLFragmentMetadataManagement:
    """Test SQLFragment metadata management methods."""

    def test_set_metadata(self):
        """Test setting a single metadata value."""
        fragment = SQLFragment(expression="SELECT * FROM patient")
        fragment.set_metadata("estimated_rows", 1000)

        assert fragment.metadata["estimated_rows"] == 1000

    def test_set_multiple_metadata_values(self):
        """Test setting multiple metadata values."""
        fragment = SQLFragment(expression="SELECT * FROM patient")
        fragment.set_metadata("estimated_rows", 1000)
        fragment.set_metadata("optimization_hint", "use_index")
        fragment.set_metadata("query_cost", 42.5)

        assert fragment.metadata["estimated_rows"] == 1000
        assert fragment.metadata["optimization_hint"] == "use_index"
        assert fragment.metadata["query_cost"] == 42.5
        assert len(fragment.metadata) == 3

    def test_get_metadata_existing_key(self):
        """Test getting metadata for existing key."""
        fragment = SQLFragment(expression="SELECT * FROM patient")
        fragment.set_metadata("rows", 1000)

        value = fragment.get_metadata("rows")
        assert value == 1000

    def test_get_metadata_missing_key_returns_none(self):
        """Test getting metadata for missing key returns None."""
        fragment = SQLFragment(expression="SELECT * FROM patient")

        value = fragment.get_metadata("missing_key")
        assert value is None

    def test_get_metadata_missing_key_with_default(self):
        """Test getting metadata for missing key with default value."""
        fragment = SQLFragment(expression="SELECT * FROM patient")

        value = fragment.get_metadata("missing_key", "default_value")
        assert value == "default_value"

    def test_metadata_initialized_with_values(self):
        """Test metadata can be initialized with values."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient",
            metadata={"rows": 1000, "hint": "use_index"}
        )

        assert fragment.metadata["rows"] == 1000
        assert fragment.metadata["hint"] == "use_index"

    def test_metadata_supports_various_types(self):
        """Test metadata can store various value types."""
        fragment = SQLFragment(expression="SELECT * FROM patient")
        fragment.set_metadata("integer", 42)
        fragment.set_metadata("float", 3.14)
        fragment.set_metadata("string", "test")
        fragment.set_metadata("boolean", True)
        fragment.set_metadata("list", [1, 2, 3])
        fragment.set_metadata("dict", {"nested": "value"})

        assert fragment.metadata["integer"] == 42
        assert fragment.metadata["float"] == 3.14
        assert fragment.metadata["string"] == "test"
        assert fragment.metadata["boolean"] is True
        assert fragment.metadata["list"] == [1, 2, 3]
        assert fragment.metadata["dict"] == {"nested": "value"}


class TestSQLFragmentEdgeCases:
    """Test SQLFragment edge cases and boundary conditions."""

    def test_very_long_expression(self):
        """Test SQLFragment with very long SQL expression."""
        long_expression = "SELECT " + ", ".join([f"col_{i}" for i in range(1000)]) + " FROM patient"
        fragment = SQLFragment(expression=long_expression)

        assert len(fragment.expression) > 5000
        assert fragment.expression.startswith("SELECT col_0")
        assert fragment.expression.endswith("FROM patient")

    def test_expression_with_special_characters(self):
        """Test SQLFragment with special characters in expression."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient WHERE name LIKE '%O\\'Brien%'"
        )

        assert "'Brien" in fragment.expression

    def test_unicode_in_expression(self):
        """Test SQLFragment with Unicode characters in expression."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient WHERE name = 'José García'"
        )

        assert "José García" in fragment.expression

    def test_multiline_expression(self):
        """Test SQLFragment with multiline SQL expression."""
        fragment = SQLFragment(
            expression="""
                SELECT id, name, birthDate
                FROM patient
                WHERE active = TRUE
                ORDER BY name
            """
        )

        assert "SELECT id, name, birthDate" in fragment.expression
        assert "WHERE active = TRUE" in fragment.expression

    def test_empty_dependencies_list(self):
        """Test SQLFragment with explicitly empty dependencies list."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient",
            dependencies=[]
        )

        assert fragment.dependencies == []
        assert len(fragment.dependencies) == 0

    def test_empty_metadata_dict(self):
        """Test SQLFragment with explicitly empty metadata dict."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient",
            metadata={}
        )

        assert fragment.metadata == {}
        assert len(fragment.metadata) == 0

    def test_both_flags_set(self):
        """Test SQLFragment with both requires_unnest and is_aggregate set."""
        fragment = SQLFragment(
            expression="SELECT COUNT(*) FROM resource, LATERAL UNNEST(names) AS name_item",
            requires_unnest=True,
            is_aggregate=True
        )

        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is True


class TestSQLFragmentDataclassFeatures:
    """Test SQLFragment dataclass-specific features."""

    def test_equality_comparison(self):
        """Test SQLFragment equality comparison."""
        fragment1 = SQLFragment(
            expression="SELECT * FROM patient",
            source_table="patient"
        )
        fragment2 = SQLFragment(
            expression="SELECT * FROM patient",
            source_table="patient"
        )

        assert fragment1 == fragment2

    def test_inequality_comparison(self):
        """Test SQLFragment inequality comparison."""
        fragment1 = SQLFragment(expression="SELECT * FROM patient")
        fragment2 = SQLFragment(expression="SELECT * FROM observation")

        assert fragment1 != fragment2

    def test_repr_output(self):
        """Test SQLFragment __repr__ output."""
        fragment = SQLFragment(
            expression="SELECT * FROM patient",
            source_table="patient"
        )

        repr_str = repr(fragment)
        assert "SQLFragment" in repr_str
        assert "SELECT * FROM patient" in repr_str

    def test_fragment_is_mutable(self):
        """Test that SQLFragment fields are mutable."""
        fragment = SQLFragment(expression="SELECT * FROM patient")

        # Modify fields
        fragment.expression = "SELECT * FROM observation"
        fragment.source_table = "observation"
        fragment.requires_unnest = True
        fragment.is_aggregate = True

        assert fragment.expression == "SELECT * FROM observation"
        assert fragment.source_table == "observation"
        assert fragment.requires_unnest is True
        assert fragment.is_aggregate is True
