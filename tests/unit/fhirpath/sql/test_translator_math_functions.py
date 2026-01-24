"""Unit tests for ASTToSQLTranslator math function translation.

Tests the _translate_math_function() method implementation for basic math
operations: abs(), ceiling(), floor(), round(), truncate().

Test Coverage:
- abs() for absolute value
- ceiling() for rounding up
- floor() for rounding down
- round() for rounding to nearest
- truncate() for removing decimal
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for missing target
- Proper SQL generation through dialect methods

Module: tests.unit.fhirpath.sql.test_translator_math_functions
Created: 2025-10-03
Task: SP-006-016
"""

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, LiteralNode, IdentifierNode
)


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


class TestAbsFunction:
    """Test abs() function translation"""

    def test_abs_with_integer_duckdb(self, duckdb_dialect):
        """Test abs() with integer literal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create abs(-5) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="-5",
            literal_type="integer",
            value=-5
        )
        literal_node.children = []

        abs_node = FunctionCallNode(
            node_type="functionCall",
            text="abs()",
            function_name="abs",
            arguments=[literal_node]
            
        )
        abs_node.children = [literal_node]

        fragment = translator._translate_math_function(abs_node)

        assert isinstance(fragment, SQLFragment)
        assert "abs(" in fragment.expression
        assert "-5" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_abs_with_decimal_postgresql(self, postgresql_dialect):
        """Test abs() with decimal literal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        # Create abs(-3.14) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="-3.14",
            literal_type="decimal",
            value=-3.14
        )
        literal_node.children = []

        abs_node = FunctionCallNode(
            node_type="functionCall",
            text="abs()",
            function_name="abs",
            arguments=[literal_node]
            
        )
        abs_node.children = [literal_node]

        fragment = translator._translate_math_function(abs_node)

        assert isinstance(fragment, SQLFragment)
        assert "abs(" in fragment.expression
        assert "-3.14" in fragment.expression
        assert fragment.requires_unnest is False


class TestCeilingFunction:
    """Test ceiling() function translation"""

    def test_ceiling_with_decimal_duckdb(self, duckdb_dialect):
        """Test ceiling() with decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create ceiling(3.2) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.2",
            literal_type="decimal",
            value=3.2
        )
        literal_node.children = []

        ceiling_node = FunctionCallNode(
            node_type="functionCall",
            text="ceiling()",
            function_name="ceiling",
            arguments=[literal_node]
            
        )
        ceiling_node.children = [literal_node]

        fragment = translator._translate_math_function(ceiling_node)

        assert isinstance(fragment, SQLFragment)
        assert "ceil(" in fragment.expression  # DuckDB uses ceil
        assert "3.2" in fragment.expression

    def test_ceiling_with_decimal_postgresql(self, postgresql_dialect):
        """Test ceiling() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create ceiling(3.2) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.2",
            literal_type="decimal",
            value=3.2
        )
        literal_node.children = []

        ceiling_node = FunctionCallNode(
            node_type="functionCall",
            text="ceiling()",
            function_name="ceiling",
            arguments=[literal_node]
            
        )
        ceiling_node.children = [literal_node]

        fragment = translator._translate_math_function(ceiling_node)

        assert isinstance(fragment, SQLFragment)
        assert "ceil(" in fragment.expression  # PostgreSQL also uses ceil
        assert "3.2" in fragment.expression


class TestFloorFunction:
    """Test floor() function translation"""

    def test_floor_with_decimal_duckdb(self, duckdb_dialect):
        """Test floor() with decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create floor(3.8) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.8",
            literal_type="decimal",
            value=3.8
        )
        literal_node.children = []

        floor_node = FunctionCallNode(
            node_type="functionCall",
            text="floor()",
            function_name="floor",
            arguments=[literal_node]
            
        )
        floor_node.children = [literal_node]

        fragment = translator._translate_math_function(floor_node)

        assert isinstance(fragment, SQLFragment)
        assert "floor(" in fragment.expression
        assert "3.8" in fragment.expression

    def test_floor_with_decimal_postgresql(self, postgresql_dialect):
        """Test floor() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create floor(3.8) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.8",
            literal_type="decimal",
            value=3.8
        )
        literal_node.children = []

        floor_node = FunctionCallNode(
            node_type="functionCall",
            text="floor()",
            function_name="floor",
            arguments=[literal_node]
            
        )
        floor_node.children = [literal_node]

        fragment = translator._translate_math_function(floor_node)

        assert isinstance(fragment, SQLFragment)
        assert "floor(" in fragment.expression
        assert "3.8" in fragment.expression


class TestRoundFunction:
    """Test round() function translation"""

    def test_round_with_decimal_duckdb(self, duckdb_dialect):
        """Test round() with decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create round(3.5) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.5",
            literal_type="decimal",
            value=3.5
        )
        literal_node.children = []

        round_node = FunctionCallNode(
            node_type="functionCall",
            text="round()",
            function_name="round",
            arguments=[literal_node]
            
        )
        round_node.children = [literal_node]

        fragment = translator._translate_math_function(round_node)

        assert isinstance(fragment, SQLFragment)
        assert "round(" in fragment.expression
        assert "3.5" in fragment.expression

    def test_round_with_decimal_postgresql(self, postgresql_dialect):
        """Test round() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create round(3.5) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.5",
            literal_type="decimal",
            value=3.5
        )
        literal_node.children = []

        round_node = FunctionCallNode(
            node_type="functionCall",
            text="round()",
            function_name="round",
            arguments=[literal_node]
            
        )
        round_node.children = [literal_node]

        fragment = translator._translate_math_function(round_node)

        assert isinstance(fragment, SQLFragment)
        assert "round(" in fragment.expression
        assert "3.5" in fragment.expression


class TestTruncateFunction:
    """Test truncate() function translation"""

    def test_truncate_with_decimal_duckdb(self, duckdb_dialect):
        """Test truncate() with decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create truncate(3.9) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.9",
            literal_type="decimal",
            value=3.9
        )
        literal_node.children = []

        truncate_node = FunctionCallNode(
            node_type="functionCall",
            text="truncate()",
            function_name="truncate",
            arguments=[literal_node]
            
        )
        truncate_node.children = [literal_node]

        fragment = translator._translate_math_function(truncate_node)

        assert isinstance(fragment, SQLFragment)
        assert "trunc(" in fragment.expression  # DuckDB uses trunc
        assert "3.9" in fragment.expression

    def test_truncate_with_decimal_postgresql(self, postgresql_dialect):
        """Test truncate() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create truncate(3.9) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="3.9",
            literal_type="decimal",
            value=3.9
        )
        literal_node.children = []

        truncate_node = FunctionCallNode(
            node_type="functionCall",
            text="truncate()",
            function_name="truncate",
            arguments=[literal_node]
            
        )
        truncate_node.children = [literal_node]

        fragment = translator._translate_math_function(truncate_node)

        assert isinstance(fragment, SQLFragment)
        assert "trunc(" in fragment.expression  # PostgreSQL also uses trunc
        assert "3.9" in fragment.expression


class TestMathFunctionWithIdentifier:
    """Test math functions with identifier (path) as target"""

    def test_abs_with_identifier_duckdb(self, duckdb_dialect):
        """Test abs() with identifier target on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Create abs(value.valueDecimal) expression
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueDecimal",
            identifier="valueDecimal"
        )
        identifier_node.children = []

        # Set up context for Observation.value
        translator.context.push_path("value")

        abs_node = FunctionCallNode(
            node_type="functionCall",
            text="abs()",
            function_name="abs",
            arguments=[identifier_node]
        )
        abs_node.children = [identifier_node]

        fragment = translator._translate_math_function(abs_node)

        assert isinstance(fragment, SQLFragment)
        assert "abs(" in fragment.expression
        assert "json_extract" in fragment.expression  # DuckDB JSON extraction
        assert "valueDecimal" in fragment.expression


class TestMathFunctionErrorHandling:
    """Test error handling for math functions"""

    def test_math_function_with_too_many_arguments_raises_error(self, duckdb_dialect):
        """Test that math function with too many arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create abs() with too many arguments
        literal_node1 = LiteralNode(
            node_type="literal",
            text="5",
            literal_type="integer",
            value=5
        )
        literal_node2 = LiteralNode(
            node_type="literal",
            text="10",
            literal_type="integer",
            value=10
        )

        abs_node = FunctionCallNode(
            node_type="functionCall",
            text="abs()",
            function_name="abs",
            arguments=[literal_node1, literal_node2]
        )
        abs_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(abs_node)

        assert "at most 1 argument" in str(exc_info.value)


class TestMultiDatabaseConsistency:
    """Test that math functions produce consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    @pytest.mark.parametrize("function_name,value,expected_func", [
        ("abs", "-10", "abs"),
        ("ceiling", "3.2", "ceil"),
        ("floor", "3.8", "floor"),
        ("round", "3.5", "round"),
        ("truncate", "3.9", "trunc"),
    ])
    def test_math_function_consistency(
        self, request, dialect_fixture, function_name, value, expected_func
    ):
        """Test math function consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create literal node
        literal_node = LiteralNode(
            node_type="literal",
            text=value,
            literal_type="decimal" if "." in value else "integer",
            value=float(value) if "." in value else int(value)
        )
        literal_node.children = []

        # Create function node
        func_node = FunctionCallNode(
            node_type="functionCall",
            text=f"{function_name}()",
            function_name=function_name,
            arguments=[literal_node]

        )
        func_node.children = [literal_node]

        fragment = translator._translate_math_function(func_node)

        # Both dialects should generate similar SQL with correct function
        assert isinstance(fragment, SQLFragment)
        assert expected_func in fragment.expression
        assert value in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False


class TestNegativeNumberHandling:
    """Test math functions with negative numbers"""

    def test_abs_with_negative_decimal_duckdb(self, duckdb_dialect):
        """Test abs() with negative decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="-123.456",
            literal_type="decimal",
            value=-123.456
        )
        literal_node.children = []

        abs_node = FunctionCallNode(
            node_type="functionCall",
            text="abs()",
            function_name="abs",
            arguments=[literal_node]
        )
        abs_node.children = [literal_node]

        fragment = translator._translate_math_function(abs_node)

        assert isinstance(fragment, SQLFragment)
        assert "abs(" in fragment.expression
        assert "-123.456" in fragment.expression

    def test_ceiling_with_negative_decimal_postgresql(self, postgresql_dialect):
        """Test ceiling() with negative decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="-3.2",
            literal_type="decimal",
            value=-3.2
        )
        literal_node.children = []

        ceiling_node = FunctionCallNode(
            node_type="functionCall",
            text="ceiling()",
            function_name="ceiling",
            arguments=[literal_node]
        )
        ceiling_node.children = [literal_node]

        fragment = translator._translate_math_function(ceiling_node)

        assert isinstance(fragment, SQLFragment)
        assert "ceil(" in fragment.expression
        assert "-3.2" in fragment.expression

    def test_floor_with_negative_decimal_duckdb(self, duckdb_dialect):
        """Test floor() with negative decimal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="-3.8",
            literal_type="decimal",
            value=-3.8
        )
        literal_node.children = []

        floor_node = FunctionCallNode(
            node_type="functionCall",
            text="floor()",
            function_name="floor",
            arguments=[literal_node]
        )
        floor_node.children = [literal_node]

        fragment = translator._translate_math_function(floor_node)

        assert isinstance(fragment, SQLFragment)
        assert "floor(" in fragment.expression
        assert "-3.8" in fragment.expression
