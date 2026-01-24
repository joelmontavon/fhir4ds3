"""Unit tests for ASTToSQLTranslator aggregation function translation.

Tests the visit_aggregation() method implementation for aggregation function
SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- count() function for arrays and collections
- sum() function for numeric fields
- avg() function for numeric fields
- min() function for comparable values
- max() function for comparable values
- is_aggregate flag correctly set
- Context preservation (no side effects on translation state)
- Dialect-specific SQL syntax generation
- Error handling for invalid aggregation functions
- Population-friendly SQL patterns

Module: tests.unit.fhirpath.sql.test_translator_aggregation
Created: 2025-09-30
Task: SP-005-011
"""

import pytest
from unittest.mock import Mock, patch

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import AggregationNode


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for testing"""
    from fhir4ds.dialects.duckdb import DuckDBDialect
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for testing (if available)"""
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestCountAggregation:
    """Test count() aggregation function translation"""

    def test_count_array_field_duckdb(self, duckdb_dialect):
        """Test count() on array field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.count()
        translator.context.push_path("name")

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert fragment.requires_unnest is False
        assert "json_array_length" in fragment.expression
        assert "$.name" in fragment.expression or "'$.name'" in fragment.expression

    def test_count_array_field_postgresql(self, postgresql_dialect):
        """Test count() on array field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.telecom.count()
        translator.context.push_path("telecom")

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "json_array_length" in fragment.expression or "jsonb_array_length" in fragment.expression

    def test_count_star_no_path(self, duckdb_dialect):
        """Test count() with no path (COUNT(*))"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # No path - should generate COUNT(*)
        # Clear any existing path
        translator.context.parent_path.clear()

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "COUNT(*)" in fragment.expression

    def test_count_nested_field(self, duckdb_dialect):
        """Test count() on nested field"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.name.given.count()
        translator.context.push_path("name")
        translator.context.push_path("given")

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "$.name.given" in fragment.expression or "'$.name.given'" in fragment.expression

    def test_count_handles_null_with_coalesce_duckdb(self, duckdb_dialect):
        """Test count() uses COALESCE to handle null values (returns 0)"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.link.count() (link often null/empty)
        translator.context.push_path("link")

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        # Should use COALESCE to return 0 for null/empty per FHIRPath spec
        assert "COALESCE" in fragment.expression
        assert ", 0)" in fragment.expression

    def test_count_handles_null_with_coalesce_postgresql(self, postgresql_dialect):
        """Test count() uses COALESCE to handle null values (returns 0)"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.link.count() (link often null/empty)
        translator.context.push_path("link")

        # Create count() aggregation node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        # Should use COALESCE to return 0 for null/empty per FHIRPath spec
        assert "COALESCE" in fragment.expression
        assert ", 0)" in fragment.expression

    def test_count_uses_dialect_method_duckdb(self, duckdb_dialect):
        """Test count() uses dialect method not hardcoded json_array_length"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")

        # Create count() node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        # Should use DuckDB's json_array_length via dialect method
        assert "json_array_length" in fragment.expression
        # Should use extract_json_object (which DuckDB uses json_extract for)
        assert "json_extract" in fragment.expression

    def test_count_uses_dialect_method_postgresql(self, postgresql_dialect):
        """Test count() uses dialect method for PostgreSQL syntax"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")

        # Create count() node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        # Should use PostgreSQL's jsonb_array_length via dialect method
        assert "jsonb_array_length" in fragment.expression
        # Should use extract_json_object (which PostgreSQL uses jsonb_extract_path for)
        assert "jsonb_extract_path" in fragment.expression or "jsonb" in fragment.expression


class TestSumAggregation:
    """Test sum() aggregation function translation"""

    def test_sum_numeric_field_duckdb(self, duckdb_dialect):
        """Test sum() on numeric field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up context: Observation.valueQuantity.value.sum()
        translator.context.push_path("valueQuantity")
        translator.context.push_path("value")

        # Create sum() aggregation node
        sum_node = AggregationNode(
            node_type="aggregation",
            text="sum()",
            aggregation_function="sum",
            aggregation_type="sum"
        )
        sum_node.children = []

        fragment = translator.visit_aggregation(sum_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "SUM(" in fragment.expression
        assert "CAST" in fragment.expression
        assert "DECIMAL" in fragment.expression

    def test_sum_numeric_field_postgresql(self, postgresql_dialect):
        """Test sum() on numeric field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        # Set up context: Observation.valueQuantity.value.sum()
        translator.context.push_path("valueQuantity")
        translator.context.push_path("value")

        # Create sum() aggregation node
        sum_node = AggregationNode(
            node_type="aggregation",
            text="sum()",
            aggregation_function="sum",
            aggregation_type="sum"
        )
        sum_node.children = []

        fragment = translator.visit_aggregation(sum_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "sum(" in fragment.expression.lower()
        assert "cast" in fragment.expression.lower() or "::" in fragment.expression


class TestAvgAggregation:
    """Test avg() aggregation function translation"""

    def test_avg_numeric_field_duckdb(self, duckdb_dialect):
        """Test avg() on numeric field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up context: Observation.valueQuantity.value.avg()
        translator.context.push_path("valueQuantity")
        translator.context.push_path("value")

        # Create avg() aggregation node
        avg_node = AggregationNode(
            node_type="aggregation",
            text="avg()",
            aggregation_function="avg",
            aggregation_type="avg"
        )
        avg_node.children = []

        fragment = translator.visit_aggregation(avg_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "AVG(" in fragment.expression
        assert "CAST" in fragment.expression
        assert "DECIMAL" in fragment.expression

    def test_avg_numeric_field_postgresql(self, postgresql_dialect):
        """Test avg() on numeric field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        # Set up context: Observation.valueQuantity.value.avg()
        translator.context.push_path("valueQuantity")
        translator.context.push_path("value")

        # Create avg() aggregation node
        avg_node = AggregationNode(
            node_type="aggregation",
            text="avg()",
            aggregation_function="avg",
            aggregation_type="avg"
        )
        avg_node.children = []

        fragment = translator.visit_aggregation(avg_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "avg(" in fragment.expression.lower()
        assert "cast" in fragment.expression.lower() or "::" in fragment.expression


class TestMinAggregation:
    """Test min() aggregation function translation"""

    def test_min_field_duckdb(self, duckdb_dialect):
        """Test min() on field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.birthDate.min()
        translator.context.push_path("birthDate")

        # Create min() aggregation node
        min_node = AggregationNode(
            node_type="aggregation",
            text="min()",
            aggregation_function="min",
            aggregation_type="min"
        )
        min_node.children = []

        fragment = translator.visit_aggregation(min_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "MIN(" in fragment.expression
        assert "birthDate" in fragment.expression or "'$.birthDate'" in fragment.expression

    def test_min_field_postgresql(self, postgresql_dialect):
        """Test min() on field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.birthDate.min()
        translator.context.push_path("birthDate")

        # Create min() aggregation node
        min_node = AggregationNode(
            node_type="aggregation",
            text="min()",
            aggregation_function="min",
            aggregation_type="min"
        )
        min_node.children = []

        fragment = translator.visit_aggregation(min_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "min(" in fragment.expression.lower()


class TestMaxAggregation:
    """Test max() aggregation function translation"""

    def test_max_field_duckdb(self, duckdb_dialect):
        """Test max() on field with DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context: Patient.birthDate.max()
        translator.context.push_path("birthDate")

        # Create max() aggregation node
        max_node = AggregationNode(
            node_type="aggregation",
            text="max()",
            aggregation_function="max",
            aggregation_type="max"
        )
        max_node.children = []

        fragment = translator.visit_aggregation(max_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "MAX(" in fragment.expression
        assert "birthDate" in fragment.expression or "'$.birthDate'" in fragment.expression

    def test_max_field_postgresql(self, postgresql_dialect):
        """Test max() on field with PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up context: Patient.birthDate.max()
        translator.context.push_path("birthDate")

        # Create max() aggregation node
        max_node = AggregationNode(
            node_type="aggregation",
            text="max()",
            aggregation_function="max",
            aggregation_type="max"
        )
        max_node.children = []

        fragment = translator.visit_aggregation(max_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.is_aggregate is True
        assert "max(" in fragment.expression.lower()


class TestAggregationContextManagement:
    """Test that aggregation functions preserve context correctly"""

    def test_context_preserved_after_count(self, duckdb_dialect):
        """Test context is preserved after count() translation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up initial context
        translator.context.push_path("name")
        initial_table = translator.context.current_table
        initial_path = translator.context.parent_path.copy()

        # Create count() node
        count_node = AggregationNode(
            node_type="aggregation",
            text="count()",
            aggregation_function="count",
            aggregation_type="count"
        )
        count_node.children = []

        fragment = translator.visit_aggregation(count_node)

        # Verify context unchanged
        assert translator.context.current_table == initial_table
        assert translator.context.parent_path == initial_path

    def test_context_preserved_after_sum(self, duckdb_dialect):
        """Test context is preserved after sum() translation"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Set up initial context
        translator.context.push_path("valueQuantity")
        translator.context.push_path("value")
        initial_table = translator.context.current_table
        initial_path = translator.context.parent_path.copy()

        # Create sum() node
        sum_node = AggregationNode(
            node_type="aggregation",
            text="sum()",
            aggregation_function="sum",
            aggregation_type="sum"
        )
        sum_node.children = []

        fragment = translator.visit_aggregation(sum_node)

        # Verify context unchanged
        assert translator.context.current_table == initial_table
        assert translator.context.parent_path == initial_path


class TestAggregationErrorHandling:
    """Test error handling for invalid aggregation functions"""

    def test_invalid_aggregation_function(self, duckdb_dialect):
        """Test that invalid aggregation function raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create node with invalid aggregation function
        invalid_node = AggregationNode(
            node_type="aggregation",
            text="invalid()",
            aggregation_function="invalid",
            aggregation_type="invalid"
        )
        invalid_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator.visit_aggregation(invalid_node)

        assert "Unsupported aggregation function" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestAggregationFlagSet:
    """Test that is_aggregate flag is correctly set"""

    @pytest.mark.parametrize("agg_type", ["count", "sum", "avg", "min", "max"])
    def test_is_aggregate_flag_set(self, duckdb_dialect, agg_type):
        """Test that is_aggregate flag is True for all aggregation functions"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Set up context
        translator.context.push_path("name")

        # Create aggregation node
        agg_node = AggregationNode(
            node_type="aggregation",
            text=f"{agg_type}()",
            aggregation_function=agg_type,
            aggregation_type=agg_type
        )
        agg_node.children = []

        fragment = translator.visit_aggregation(agg_node)

        assert fragment.is_aggregate is True, f"{agg_type}() should set is_aggregate=True"


class TestMultiDatabaseConsistency:
    """Test that aggregation functions produce consistent logic across databases"""

    @pytest.mark.parametrize("agg_type", ["count", "sum", "avg", "min", "max"])
    def test_aggregation_consistency(self, duckdb_dialect, postgresql_dialect, agg_type):
        """Test that aggregation functions produce equivalent logic across dialects"""
        # Create translators for both dialects
        duckdb_translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        pg_translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Set up same context for both
        duckdb_translator.context.push_path("name")
        pg_translator.context.push_path("name")

        # Create aggregation node
        agg_node = AggregationNode(
            node_type="aggregation",
            text=f"{agg_type}()",
            aggregation_function=agg_type,
            aggregation_type=agg_type
        )
        agg_node.children = []

        # Translate with both dialects
        duckdb_fragment = duckdb_translator.visit_aggregation(agg_node)
        pg_fragment = pg_translator.visit_aggregation(agg_node)

        # Both should be aggregates
        assert duckdb_fragment.is_aggregate is True
        assert pg_fragment.is_aggregate is True

        # Both should have the aggregation function (case-insensitive)
        # Note: count() may use json_array_length instead of COUNT keyword
        if agg_type == "count":
            assert "count" in duckdb_fragment.expression.lower() or "length" in duckdb_fragment.expression.lower()
            assert "count" in pg_fragment.expression.lower() or "length" in pg_fragment.expression.lower()
        else:
            assert agg_type in duckdb_fragment.expression.lower()
            assert agg_type in pg_fragment.expression.lower()
