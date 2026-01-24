"""Unit tests for ASTToSQLTranslator advanced math function translation.

Tests the _translate_math_function() method implementation for advanced math
operations: sqrt(), exp(), ln(), log(), power().

Test Coverage:
- sqrt() for square root
- exp() for exponential (e^x)
- ln() for natural logarithm
- log() for logarithm base 10
- power() for exponentiation
- Multi-database consistency (DuckDB and PostgreSQL)
- Error handling for invalid arguments
- Proper SQL generation through dialect methods

Module: tests.unit.fhirpath.sql.test_translator_advanced_math_functions
Created: 2025-10-03
Task: SP-006-017
"""

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode, LiteralNode, IdentifierNode
)
from fhir4ds.fhirpath.parser import FHIRPathParser


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


@pytest.fixture(scope="module")
def fhirpath_parser():
    """Provide shared FHIRPath parser for expression-based tests."""
    return FHIRPathParser()


class TestSqrtFunction:
    """Test sqrt() function translation"""

    def test_sqrt_with_integer_duckdb(self, duckdb_dialect):
        """Test sqrt() with integer literal on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create sqrt(16) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="16",
            literal_type="integer",
            value=16
        )
        literal_node.children = []

        sqrt_node = FunctionCallNode(
            node_type="functionCall",
            text="sqrt()",
            function_name="sqrt",
            arguments=[literal_node]
        )
        sqrt_node.children = [literal_node]

        fragment = translator._translate_math_function(sqrt_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.startswith("(")
        assert "CASE" in fragment.expression
        assert "sqrt(" in fragment.expression
        assert "CAST(16" in fragment.expression
        assert "isfinite" in fragment.expression
        assert "< 0 THEN NULL" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_sqrt_with_decimal_postgresql(self, postgresql_dialect):
        """Test sqrt() with decimal literal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        # Create sqrt(2.5) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="2.5",
            literal_type="decimal",
            value=2.5
        )
        literal_node.children = []

        sqrt_node = FunctionCallNode(
            node_type="functionCall",
            text="sqrt()",
            function_name="sqrt",
            arguments=[literal_node]
        )
        sqrt_node.children = [literal_node]

        fragment = translator._translate_math_function(sqrt_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.startswith("(")
        assert "CASE" in fragment.expression
        assert "sqrt(" in fragment.expression
        assert "2.5" in fragment.expression
        assert "isfinite" in fragment.expression
        assert fragment.requires_unnest is False


class TestExpFunction:
    """Test exp() function translation"""

    def test_exp_with_integer_duckdb(self, duckdb_dialect):
        """Test exp() with integer on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create exp(2) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        literal_node.children = []

        exp_node = FunctionCallNode(
            node_type="functionCall",
            text="exp()",
            function_name="exp",
            arguments=[literal_node]
        )
        exp_node.children = [literal_node]

        fragment = translator._translate_math_function(exp_node)

        assert isinstance(fragment, SQLFragment)
        assert "exp(" in fragment.expression
        assert "2" in fragment.expression

    def test_exp_with_decimal_postgresql(self, postgresql_dialect):
        """Test exp() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create exp(1.5) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="1.5",
            literal_type="decimal",
            value=1.5
        )
        literal_node.children = []

        exp_node = FunctionCallNode(
            node_type="functionCall",
            text="exp()",
            function_name="exp",
            arguments=[literal_node]
        )
        exp_node.children = [literal_node]

        fragment = translator._translate_math_function(exp_node)

        assert isinstance(fragment, SQLFragment)
        assert "exp(" in fragment.expression
        assert "1.5" in fragment.expression


class TestLnFunction:
    """Test ln() function translation"""

    def test_ln_with_integer_duckdb(self, duckdb_dialect):
        """Test ln() with integer on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create ln(10) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="10",
            literal_type="integer",
            value=10
        )
        literal_node.children = []

        ln_node = FunctionCallNode(
            node_type="functionCall",
            text="ln()",
            function_name="ln",
            arguments=[literal_node]
        )
        ln_node.children = [literal_node]

        fragment = translator._translate_math_function(ln_node)

        assert isinstance(fragment, SQLFragment)
        assert "ln(" in fragment.expression
        assert "10" in fragment.expression

    def test_ln_with_decimal_postgresql(self, postgresql_dialect):
        """Test ln() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create ln(2.718) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="2.718",
            literal_type="decimal",
            value=2.718
        )
        literal_node.children = []

        ln_node = FunctionCallNode(
            node_type="functionCall",
            text="ln()",
            function_name="ln",
            arguments=[literal_node]
        )
        ln_node.children = [literal_node]

        fragment = translator._translate_math_function(ln_node)

        assert isinstance(fragment, SQLFragment)
        assert "ln(" in fragment.expression
        assert "2.718" in fragment.expression


class TestLogFunction:
    """Test log() function translation"""

    def test_log_with_integer_duckdb(self, duckdb_dialect):
        """Test log() with integer on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create log(100) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="100",
            literal_type="integer",
            value=100
        )
        literal_node.children = []

        log_node = FunctionCallNode(
            node_type="functionCall",
            text="log()",
            function_name="log",
            arguments=[literal_node]
        )
        log_node.children = [literal_node]

        fragment = translator._translate_math_function(log_node)

        assert isinstance(fragment, SQLFragment)
        # DuckDB uses log10 for base-10 logarithm
        assert "log" in fragment.expression.lower()
        assert "100" in fragment.expression

    def test_log_with_decimal_postgresql(self, postgresql_dialect):
        """Test log() with decimal on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create log(1000.0) expression
        literal_node = LiteralNode(
            node_type="literal",
            text="1000.0",
            literal_type="decimal",
            value=1000.0
        )
        literal_node.children = []

        log_node = FunctionCallNode(
            node_type="functionCall",
            text="log()",
            function_name="log",
            arguments=[literal_node]
        )
        log_node.children = [literal_node]

        fragment = translator._translate_math_function(log_node)

        assert isinstance(fragment, SQLFragment)
        # PostgreSQL uses log for base-10 logarithm
        assert "log(" in fragment.expression
        assert "1000.0" in fragment.expression

    def test_log_with_base_argument_duckdb(self, duckdb_dialect):
        """log() with explicit base should generate safe ln ratio in DuckDB."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        value_node = LiteralNode(
            node_type="literal",
            text="16",
            literal_type="integer",
            value=16
        )
        value_node.children = []

        base_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        base_node.children = []

        log_node = FunctionCallNode(
            node_type="functionCall",
            text="log()",
            function_name="log",
            arguments=[value_node, base_node]
        )
        log_node.children = [value_node, base_node]

        fragment = translator._translate_math_function(log_node)

        expression = fragment.expression
        assert "CASE" in expression
        assert "isfinite" in expression
        assert "ln(" in expression.lower()
        assert "/ " in expression or "/(" in expression
        assert "CAST(16" in expression
        assert "CAST(2" in expression

    def test_log_with_base_argument_postgresql(self, postgresql_dialect):
        """log() with explicit base should generate safe ln ratio in PostgreSQL."""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        value_node = LiteralNode(
            node_type="literal",
            text="100.0",
            literal_type="decimal",
            value=100.0
        )
        value_node.children = []

        base_node = LiteralNode(
            node_type="literal",
            text="10.0",
            literal_type="decimal",
            value=10.0
        )
        base_node.children = []

        log_node = FunctionCallNode(
            node_type="functionCall",
            text="log()",
            function_name="log",
            arguments=[value_node, base_node]
        )
        log_node.children = [value_node, base_node]

        fragment = translator._translate_math_function(log_node)

        expression = fragment.expression
        assert "CASE" in expression
        assert "isfinite" in expression
        assert "ln(" in expression.lower()
        assert "/ " in expression or "/(" in expression
        assert "CAST(100.0" in expression
        assert "CAST(10.0" in expression

    def test_log_method_invocation_duckdb(self, duckdb_dialect, fhirpath_parser):
        """Translate 16.log(2) via parser to ensure method invocation works."""
        enhanced_ast = fhirpath_parser.parse("16.log(2)").get_ast()
        fhir_ast = enhanced_ast
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        fragments = translator.translate(fhir_ast)
        assert fragments, "Expected at least one SQL fragment"
        expression = fragments[-1].expression
        assert "ln(" in expression.lower()
        assert "/ " in expression or "/(" in expression
        assert "CAST(16" in expression
        assert "CAST(2" in expression

    def test_log_method_invocation_postgresql(self, postgresql_dialect, fhirpath_parser):
        """Translate 100.log(10) via parser to ensure method invocation works."""
        enhanced_ast = fhirpath_parser.parse("100.log(10)").get_ast()
        fhir_ast = enhanced_ast
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        fragments = translator.translate(fhir_ast)
        assert fragments, "Expected at least one SQL fragment"
        expression = fragments[-1].expression
        assert "ln(" in expression.lower()
        assert "/ " in expression or "/(" in expression
        assert "CAST(100" in expression
        assert "CAST(10" in expression


class TestPowerFunction:
    """Test power() function translation"""

    def test_power_with_integers_duckdb(self, duckdb_dialect):
        """Test power() with integer arguments on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create power(2, 3) expression
        base_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.startswith("(")
        assert "CASE" in fragment.expression
        assert "pow(" in fragment.expression
        assert "2" in fragment.expression
        assert "3" in fragment.expression
        assert "= 0 AND" in fragment.expression
        assert "isfinite" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    def test_power_with_decimals_postgresql(self, postgresql_dialect):
        """Test power() with decimal arguments on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")

        # Create power(2.5, 2.0) expression
        base_node = LiteralNode(
            node_type="literal",
            text="2.5",
            literal_type="decimal",
            value=2.5
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="2.0",
            literal_type="decimal",
            value=2.0
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.startswith("(")
        assert "CASE" in fragment.expression
        assert "power(" in fragment.expression
        assert "2.5" in fragment.expression
        assert "2.0" in fragment.expression
        assert "< 0 AND" in fragment.expression
        assert "isfinite" in fragment.expression
        assert fragment.requires_unnest is False


class TestAdvancedMathFunctionWithIdentifier:
    """Test advanced math functions with identifier (path) as target"""

    def test_sqrt_with_identifier_duckdb(self, duckdb_dialect):
        """Test sqrt() with identifier target on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Create sqrt(value.valueDecimal) expression
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueDecimal",
            identifier="valueDecimal"
        )
        identifier_node.children = []

        # Set up context for Observation.value
        translator.context.push_path("value")

        sqrt_node = FunctionCallNode(
            node_type="functionCall",
            text="sqrt()",
            function_name="sqrt",
            arguments=[identifier_node]
        )
        sqrt_node.children = [identifier_node]

        fragment = translator._translate_math_function(sqrt_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.startswith("(")
        assert "CASE" in fragment.expression
        assert "sqrt(" in fragment.expression
        assert "isfinite" in fragment.expression
        assert "< 0 THEN NULL" in fragment.expression
        assert "json_extract" in fragment.expression  # DuckDB JSON extraction
        assert "valueDecimal" in fragment.expression


class TestAdvancedMathFunctionErrorHandling:
    """Test error handling for advanced math functions"""

    def test_power_with_zero_arguments_raises_error(self, duckdb_dialect):
        """Test that power() with zero arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create power() with no arguments
        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[]
        )
        power_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(power_node)

        assert "requires exactly 2 arguments" in str(exc_info.value)

    def test_power_with_one_argument_raises_error(self, duckdb_dialect):
        """Test that power() with one argument raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create power() with one argument
        literal_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        literal_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[literal_node]
        )
        power_node.children = [literal_node]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(power_node)

        assert "requires exactly 2 arguments" in str(exc_info.value)

    def test_power_with_three_arguments_raises_error(self, duckdb_dialect):
        """Test that power() with three arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create power() with three arguments
        literal_node1 = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        literal_node2 = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        literal_node3 = LiteralNode(
            node_type="literal",
            text="4",
            literal_type="integer",
            value=4
        )

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[literal_node1, literal_node2, literal_node3]
        )
        power_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(power_node)

        assert "requires exactly 2 arguments" in str(exc_info.value)

    def test_sqrt_with_too_many_arguments_raises_error(self, duckdb_dialect):
        """Test that sqrt() with too many arguments raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create sqrt() with two arguments
        literal_node1 = LiteralNode(
            node_type="literal",
            text="16",
            literal_type="integer",
            value=16
        )
        literal_node2 = LiteralNode(
            node_type="literal",
            text="4",
            literal_type="integer",
            value=4
        )

        sqrt_node = FunctionCallNode(
            node_type="functionCall",
            text="sqrt()",
            function_name="sqrt",
            arguments=[literal_node1, literal_node2]
        )
        sqrt_node.children = []

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(sqrt_node)

        assert "at most 1 argument" in str(exc_info.value)


class TestMultiDatabaseConsistency:
    """Test that advanced math functions produce consistent results across databases"""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    @pytest.mark.parametrize("function_name,value", [
        ("sqrt", "16"),
        ("exp", "2"),
        ("ln", "10"),
        ("log", "100"),
    ])
    def test_single_arg_math_function_consistency(
        self, request, dialect_fixture, function_name, value
    ):
        """Test single-argument math function consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create literal node
        literal_node = LiteralNode(
            node_type="literal",
            text=value,
            literal_type="integer",
            value=int(value)
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
        assert value in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_power_function_consistency(self, request, dialect_fixture):
        """Test power() function consistency across databases"""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Patient")

        # Create power(2, 3) expression
        base_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        # Both dialects should generate SQL with power/pow function
        assert isinstance(fragment, SQLFragment)
        assert "2" in fragment.expression
        assert "3" in fragment.expression
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False


class TestPowerFunctionGuards:
    """Ensure power() translation enforces domain safety checks."""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_power_zero_to_zero_returns_one_clause(self, request, dialect_fixture):
        """power(0, 0) should emit guard clause that returns 1."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Observation")

        base_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        base_expr = dialect.cast_to_double("0")
        exponent_expr = dialect.cast_to_double("0")
        assert f"WHEN {base_expr} = 0 AND {exponent_expr} = 0 THEN 1" in fragment.expression

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_power_zero_base_negative_exponent_returns_null(self, request, dialect_fixture):
        """power(0, negative) should emit guard clause returning NULL."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Observation")

        base_node = LiteralNode(
            node_type="literal",
            text="0",
            literal_type="integer",
            value=0
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="-1",
            literal_type="integer",
            value=-1
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        base_expr = dialect.cast_to_double("0")
        exponent_expr = dialect.cast_to_double("-1")
        assert f"WHEN {base_expr} = 0 AND {exponent_expr} < 0 THEN NULL" in fragment.expression

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_power_negative_base_fractional_exponent_returns_null(self, request, dialect_fixture):
        """power(negative, fractional) should guard against complex outputs."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Observation")

        base_node = LiteralNode(
            node_type="literal",
            text="-8",
            literal_type="integer",
            value=-8
        )
        base_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="0.5",
            literal_type="decimal",
            value=0.5
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            arguments=[base_node, exponent_node]
        )
        power_node.children = [base_node, exponent_node]

        fragment = translator._translate_math_function(power_node)

        base_expr = dialect.cast_to_double("-8")
        exponent_expr = dialect.cast_to_double("0.5")
        floor_expr = dialect.generate_math_function("floor", exponent_expr)
        guard_clause = f"WHEN {base_expr} < 0 AND {exponent_expr} <> {floor_expr} THEN NULL"
        assert guard_clause in fragment.expression

    def test_power_method_target_uses_single_argument(self, duckdb_dialect):
        """Method-form power() should accept exactly one exponent argument."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        target_node = LiteralNode(
            node_type="literal",
            text="4",
            literal_type="integer",
            value=4
        )
        target_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        exponent_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            target=target_node,
            arguments=[exponent_node]
        )
        power_node.children = [exponent_node]

        fragment = translator._translate_math_function(power_node)

        base_expr = duckdb_dialect.cast_to_double("4")
        exponent_expr = duckdb_dialect.cast_to_double("2")
        assert base_expr in fragment.expression
        assert exponent_expr in fragment.expression

    def test_power_method_with_multiple_arguments_raises_error(self, duckdb_dialect):
        """Method-form power() should reject more than one argument."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        target_node = LiteralNode(
            node_type="literal",
            text="4",
            literal_type="integer",
            value=4
        )
        target_node.children = []

        exponent_node = LiteralNode(
            node_type="literal",
            text="2",
            literal_type="integer",
            value=2
        )
        exponent_node.children = []

        extra_node = LiteralNode(
            node_type="literal",
            text="3",
            literal_type="integer",
            value=3
        )
        extra_node.children = []

        power_node = FunctionCallNode(
            node_type="functionCall",
            text="power()",
            function_name="power",
            target=target_node,
            arguments=[exponent_node, extra_node]
        )
        power_node.children = [exponent_node, extra_node]

        with pytest.raises(ValueError) as exc_info:
            translator._translate_math_function(power_node)

        assert "requires exactly 1 argument" in str(exc_info.value)


class TestMathFunctionContextUsage:
    """Ensure context-only math invocations use current path extraction."""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
    def test_sqrt_without_arguments_uses_context_path(self, request, dialect_fixture):
        """sqrt() with no arguments should operate on current context path."""
        dialect = request.getfixturevalue(dialect_fixture)
        translator = ASTToSQLTranslator(dialect, "Observation")
        translator.context.push_path("valueQuantity")

        sqrt_node = FunctionCallNode(
            node_type="functionCall",
            text="sqrt()",
            function_name="sqrt",
            arguments=[]
        )
        sqrt_node.children = []

        fragment = translator._translate_math_function(sqrt_node)

        path_expr = dialect.extract_json_field("resource", "$.valueQuantity")
        assert path_expr in fragment.expression
