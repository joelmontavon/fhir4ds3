"""Unit tests for ASTToSQLTranslator type operation translation.

Tests the visit_type_operation() and _translate_is_operation() method implementations
for type checking SQL generation. Validates correctness across both DuckDB and PostgreSQL dialects.

Test Coverage:
- is() operation with all supported FHIRPath types (String, Integer, Decimal, Boolean, DateTime, Date, Time)
- is() with literal values
- is() with identifier expressions
- is() with complex expressions
- Dialect-specific SQL syntax generation (DuckDB vs PostgreSQL)
- Error handling for invalid operations
- Multi-database consistency verification
- Unknown type handling

Module: tests.unit.fhirpath.sql.test_translator_type_operations
Created: 2025-10-02
Task: SP-006-005
"""

import pytest
from unittest.mock import Mock

from fhir4ds.fhirpath.exceptions import FHIRPathTranslationError
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.ast.nodes import (
    TypeOperationNode, LiteralNode, IdentifierNode, FunctionCallNode
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


class TestIsOperationBasicTypes:
    """Test is() operation with basic FHIRPath types"""

    def test_is_integer_type_duckdb(self, duckdb_dialect):
        """Test is() with Integer type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: 5 is Integer
        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 is Integer",
            operation="is",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE" in fragment.expression
        assert "typeof" in fragment.expression
        assert "INTEGER" in fragment.expression
        assert "5" in fragment.expression

    def test_is_string_type_duckdb(self, duckdb_dialect):
        """Test is() with String type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: 'hello' is String
        literal_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            value="hello",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'hello' is String",
            operation="is",
            target_type="String"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "VARCHAR" in fragment.expression
        assert "'hello'" in fragment.expression

    def test_is_boolean_type_duckdb(self, duckdb_dialect):
        """Test is() with Boolean type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: true is Boolean
        literal_node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="true is Boolean",
            operation="is",
            target_type="Boolean"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "BOOLEAN" in fragment.expression

    def test_is_decimal_type_duckdb(self, duckdb_dialect):
        """Test is() with Decimal type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: 3.14 is Decimal
        literal_node = LiteralNode(
            node_type="literal",
            text="3.14",
            value=3.14,
            literal_type="decimal"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="3.14 is Decimal",
            operation="is",
            target_type="Decimal"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "DOUBLE" in fragment.expression

    def test_is_code_alias_canonicalizes_to_string(self, duckdb_dialect):
        """Test is() resolves code alias to string canonical name."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="'male'",
            value="male",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'male' is code",
            operation="is",
            target_type="code"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "VARCHAR" in fragment.expression


class TestIsOperationPostgreSQL:
    """Test is() operation with PostgreSQL dialect"""

    def test_is_integer_type_postgresql(self, postgresql_dialect):
        """Test is() with Integer type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: 5 is Integer
        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 is Integer",
            operation="is",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE" in fragment.expression
        assert "pg_typeof" in fragment.expression
        assert "integer" in fragment.expression or "bigint" in fragment.expression
        assert "5" in fragment.expression

    def test_is_string_type_postgresql(self, postgresql_dialect):
        """Test is() with String type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: 'hello' is String
        literal_node = LiteralNode(
            node_type="literal",
            text="'hello'",
            value="hello",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'hello' is String",
            operation="is",
            target_type="String"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "text" in fragment.expression
        assert "'hello'" in fragment.expression


class TestIsOperationWithIdentifiers:
    """Test is() operation with identifiers (FHIR paths)"""

    def test_is_with_identifier_duckdb(self, duckdb_dialect):
        """Test is() with identifier expression on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: Patient.birthDate is Date
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="birthDate",
            identifier="birthDate"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="birthDate is Date",
            operation="is",
            target_type="Date"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_matches" in fragment.expression
        assert "$.birthDate" in fragment.expression or "$.birthDate" in fragment.expression.replace('"', '')
        assert "birthDate" in fragment.expression or "$.birthDate" in fragment.expression


class TestIsOperationDateTimeTypes:
    """Test is() operation with date/time types"""

    def test_is_date_type_duckdb(self, duckdb_dialect):
        """Test is() with Date type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create a mock literal for date
        literal_node = LiteralNode(
            node_type="literal",
            text="@2024-01-01",
            value="2024-01-01",
            literal_type="date"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="@2024-01-01 is Date",
            operation="is",
            target_type="Date"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "regexp_matches" in fragment.expression
        assert r"\d{4}" in fragment.expression

    def test_is_datetime_type_duckdb(self, duckdb_dialect):
        """Test is() with DateTime type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create a mock literal for datetime
        literal_node = LiteralNode(
            node_type="literal",
            text="@2024-01-01T12:00:00",
            value="2024-01-01T12:00:00",
            literal_type="datetime"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="@2024-01-01T12:00:00 is DateTime",
            operation="is",
            target_type="DateTime"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TIMESTAMP" in fragment.expression

    def test_is_time_type_duckdb(self, duckdb_dialect):
        """Test is() with Time type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create a mock literal for time
        literal_node = LiteralNode(
            node_type="literal",
            text="@T12:00:00",
            value="12:00:00",
            literal_type="time"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="@T12:00:00 is Time",
            operation="is",
            target_type="Time"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TIME" in fragment.expression


class TestIsOperationErrorHandling:
    """Test is() operation error handling"""

    def test_is_operation_without_children_raises_error(self, duckdb_dialect):
        """Test that is() operation without children raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create is() node without children
        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="is Integer",
            operation="is",
            target_type="Integer"
        )
        type_op_node.children = []

        with pytest.raises(ValueError, match="is\\(\\) operation requires an expression to check"):
            translator.visit_type_operation(type_op_node)

    def test_type_operation_without_operation_raises_error(self, duckdb_dialect):
        """Test that type operation without operation type raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create node without operation
        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 Integer",
            operation="",  # No operation
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        with pytest.raises(ValueError, match="Type operation must specify an operation"):
            translator.visit_type_operation(type_op_node)

    def test_type_operation_without_target_type_raises_error(self, duckdb_dialect):
        """Test that type operation without target type raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create node without target type
        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 is",
            operation="is",
            target_type=""  # No target type
        )
        type_op_node.children = [literal_node]

        with pytest.raises(ValueError, match="Type operation must specify a target type"):
            translator.visit_type_operation(type_op_node)

    def test_unknown_type_raises_translation_error(self, duckdb_dialect):
        """Test that unknown types raise FHIRPathTranslationError."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 is Foo",
            operation="is",
            target_type="Foo"
        )
        type_op_node.children = [literal_node]

        with pytest.raises(FHIRPathTranslationError, match="Unknown FHIR type 'Foo'"):
            translator.visit_type_operation(type_op_node)

    def test_unknown_type_operation_raises_error(self, duckdb_dialect):
        """Test that unknown type operations raise ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create unknown operation
        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 unknownOp Integer",
            operation="unknownOp",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        with pytest.raises(ValueError, match="Unknown type operation: unknownOp"):
            translator.visit_type_operation(type_op_node)


class TestAsOperationBasicTypes:
    """Test as() operation with basic FHIRPath types"""

    def test_as_integer_type_duckdb(self, duckdb_dialect):
        """Test as() with Integer type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: '123' as Integer
        literal_node = LiteralNode(
            node_type="literal",
            text="'123'",
            value="123",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'123' as Integer",
            operation="as",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "TRY_CAST" in fragment.expression
        assert "INTEGER" in fragment.expression
        assert "'123'" in fragment.expression

    def test_as_string_type_duckdb(self, duckdb_dialect):
        """Test as() with String type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: 123 as String
        literal_node = LiteralNode(
            node_type="literal",
            text="123",
            value=123,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="123 as String",
            operation="as",
            target_type="String"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression
        assert "VARCHAR" in fragment.expression
        assert "123" in fragment.expression

    def test_as_datetime_type_duckdb(self, duckdb_dialect):
        """Test as() with DateTime type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: '2024-01-01' as DateTime
        literal_node = LiteralNode(
            node_type="literal",
            text="'2024-01-01'",
            value="2024-01-01",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'2024-01-01' as DateTime",
            operation="as",
            target_type="DateTime"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression
        assert "TIMESTAMP" in fragment.expression
        assert "'2024-01-01'" in fragment.expression

    def test_as_boolean_type_duckdb(self, duckdb_dialect):
        """Test as() with Boolean type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: 'true' as Boolean
        literal_node = LiteralNode(
            node_type="literal",
            text="'true'",
            value="true",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'true' as Boolean",
            operation="as",
            target_type="Boolean"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression
        assert "BOOLEAN" in fragment.expression
        assert "'true'" in fragment.expression


class TestAsOperationPostgreSQL:
    """Test as() operation with PostgreSQL dialect"""

    def test_as_integer_type_postgresql(self, postgresql_dialect):
        """Test as() with Integer type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: '123' as Integer
        literal_node = LiteralNode(
            node_type="literal",
            text="'123'",
            value="123",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'123' as Integer",
            operation="as",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "CASE" in fragment.expression
        assert "INTEGER" in fragment.expression
        assert "'123'" in fragment.expression

    def test_as_string_type_postgresql(self, postgresql_dialect):
        """Test as() with String type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: 123 as String
        literal_node = LiteralNode(
            node_type="literal",
            text="123",
            value=123,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="123 as String",
            operation="as",
            target_type="String"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE" in fragment.expression
        assert "TEXT" in fragment.expression
        assert "123" in fragment.expression

    @pytest.mark.parametrize(
        "resource_type, expression, expected_path, expected_variant, expected_fields",
        [
            (
                "Observation",
                "Observation.value as Quantity",
                ["valueQuantity"],
                "valueQuantity",
                ["value"],
            ),
            (
                "Observation",
                "Observation.value.as(Quantity)",
                ["valueQuantity"],
                "valueQuantity",
                ["value"],
            ),
            (
                "Observation",
                "Observation.value as CodeableConcept",
                ["valueCodeableConcept"],
                "valueCodeableConcept",
                ["coding"],
            ),
            (
                "Observation",
                "Observation.value as Range",
                ["valueRange"],
                "valueRange",
                ["low"],
            ),
            (
                "Observation",
                "Observation.value as Ratio",
                ["valueRatio"],
                "valueRatio",
                ["numerator", "denominator"],
            ),
            (
                "Procedure",
                "Procedure.performed as Period",
                ["performedPeriod"],
                "performedPeriod",
                ["start"],
            ),
            (
                "Procedure",
                "Procedure.performed as Range",
                ["performedRange"],
                "performedRange",
                ["low"],
            ),
            (
                "Procedure",
                "Procedure.performed.as(Period)",
                ["performedPeriod"],
                "performedPeriod",
                ["start"],
            ),
            (
                "Condition",
                "Condition.onset as Period",
                ["onsetPeriod"],
                "onsetPeriod",
                ["start"],
            ),
        ],
    )
    def test_complex_type_casts_postgresql(
        self,
        postgresql_dialect,
        resource_type,
        expression,
        expected_path,
        expected_variant,
        expected_fields,
    ):
        """Complex polymorphic casts should translate for PostgreSQL as jsonb_extract_path."""
        translator = ASTToSQLTranslator(postgresql_dialect, resource_type)
        parser = FHIRPathParser()
        ast = parser.parse(expression)

        fragments = translator.translate(ast)
        result_fragment = fragments[-1]

        assert result_fragment.expression.strip().upper().startswith("CASE WHEN")
        assert result_fragment.metadata.get("mode") == "complex"
        assert result_fragment.metadata.get("variant_property") == expected_variant
        assert result_fragment.metadata.get("discriminator_fields") == expected_fields
        for field in expected_fields:
            assert field in result_fragment.expression
        assert translator.context.parent_path == expected_path

    def test_complex_type_cast_with_nested_collection_postgresql(self, postgresql_dialect):
        """Ensure component Quantity casts work on PostgreSQL as well."""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        parser = FHIRPathParser()
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("Observation.component.value as Quantity").get_ast()
        )

        fragments = translator.translate(ast)
        assert len(fragments) >= 3
        quantity_fragment = fragments[-1]

        assert quantity_fragment.expression.strip().upper().startswith("CASE WHEN")
        assert "valueQuantity" in quantity_fragment.expression
        assert quantity_fragment.metadata.get("variant_property") == "valueQuantity"
        assert quantity_fragment.metadata.get("discriminator_fields") == ["value"]
        assert translator.context.parent_path == ["component", "valueQuantity"]


class TestAsOperationWithIdentifiers:
    """Test as() operation with identifiers (FHIR paths)"""

    def test_as_with_identifier_duckdb(self, duckdb_dialect):
        """Test as() with identifier expression on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: Procedure.performed as DateTime (healthcare use case)
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="performed",
            identifier="performed"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="performed as DateTime",
            operation="as",
            target_type="DateTime"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression
        assert "TIMESTAMP" in fragment.expression
        assert "performed" in fragment.expression or "$.performed" in fragment.expression


class TestAsOperationErrorHandling:
    """Test as() operation error handling"""

    def test_as_operation_without_children_raises_error(self, duckdb_dialect):
        """Test that as() operation without children raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create as() node without children
        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="as Integer",
            operation="as",
            target_type="Integer"
        )
        type_op_node.children = []

        with pytest.raises(ValueError, match="as\\(\\) operation requires an expression to cast"):
            translator.visit_type_operation(type_op_node)

    def test_as_unknown_type_returns_null_duckdb(self, duckdb_dialect):
        """Test as() with unknown type returns NULL (DuckDB)"""
        sql = duckdb_dialect.generate_type_cast("'value'", "UnknownType")
        assert sql == "NULL"

    def test_as_unknown_type_returns_null_postgresql(self, postgresql_dialect):
        """Test as() with unknown type returns NULL (PostgreSQL)"""
        sql = postgresql_dialect.generate_type_cast("'value'", "UnknownType")
        assert sql == "NULL"

    def test_as_resource_type_returns_null_fragment(self, duckdb_dialect):
        """Translator should return NULL fragments when casting to resource types."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        parser = FHIRPathParser()
        ast = parser.parse("Observation.value as Patient")

        fragments = translator.translate(ast)
        result_fragment = fragments[-1]

        assert result_fragment.expression == "NULL"
        assert result_fragment.metadata.get("mode") == "null"
        assert translator.context.parent_path == []


class TestDialectTypeCastMethod:
    """Test dialect generate_type_cast() method directly"""

    def test_duckdb_generate_type_cast_integer(self, duckdb_dialect):
        """Test DuckDB generate_type_cast for Integer type"""
        sql = duckdb_dialect.generate_type_cast("'123'", "integer")

        assert "TRY_CAST" in sql
        assert "'123'" in sql
        assert "INTEGER" in sql

    def test_duckdb_generate_type_cast_string(self, duckdb_dialect):
        """Test DuckDB generate_type_cast for String type"""
        sql = duckdb_dialect.generate_type_cast("123", "string")

        assert "TRY_CAST" in sql
        assert "123" in sql
        assert "VARCHAR" in sql

    def test_duckdb_generate_type_cast_datetime(self, duckdb_dialect):
        """Test DuckDB generate_type_cast for DateTime type"""
        sql = duckdb_dialect.generate_type_cast("'2024-01-01'", "dateTime")

        assert "TRY_CAST" in sql
        assert "'2024-01-01'" in sql
        assert "TIMESTAMP" in sql

    def test_postgresql_generate_type_cast_integer(self, postgresql_dialect):
        """Test PostgreSQL generate_type_cast for Integer type"""
        sql = postgresql_dialect.generate_type_cast("'123'", "integer")

        assert "CASE" in sql
        assert "'123'" in sql
        assert "INTEGER" in sql

    def test_postgresql_generate_type_cast_string(self, postgresql_dialect):
        """Test PostgreSQL generate_type_cast for String type"""
        sql = postgresql_dialect.generate_type_cast("123", "string")

        assert "CASE" in sql
        assert "123" in sql
        assert "TEXT" in sql

    def test_postgresql_generate_type_cast_datetime(self, postgresql_dialect):
        """Test PostgreSQL generate_type_cast for DateTime type"""
        sql = postgresql_dialect.generate_type_cast("'2024-01-01'", "dateTime")

        assert "CASE" in sql
        assert "'2024-01-01'" in sql
        assert "TIMESTAMP" in sql


class TestAsOperationMultiDatabaseConsistency:
    """Test as() operation consistency across DuckDB and PostgreSQL"""

    @pytest.mark.parametrize("source_value,source_type,target_type", [
        ("'123'", "string", "Integer"),
        ("123", "integer", "String"),
        ("'true'", "string", "Boolean"),
        ("'3.14'", "string", "Decimal"),
        ("'2024-01-01'", "string", "DateTime"),
        ("'2024-01-01'", "string", "Date"),
        ("'12:30:00'", "string", "Time"),
    ])
    def test_as_operation_consistency(self, duckdb_dialect, source_value, source_type, target_type):
        """Test that as() generates SQL for both dialects (structure validation)"""
        # Test DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text=str(source_value),
            value=source_value,
            literal_type=source_type
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"{source_value} as {target_type}",
            operation="as",
            target_type=target_type
        )
        type_op_node.children = [literal_node]

        fragment_duck = translator_duck.visit_type_operation(type_op_node)

        # Validate DuckDB fragment structure
        assert isinstance(fragment_duck, SQLFragment)
        assert fragment_duck.requires_unnest is False
        assert fragment_duck.is_aggregate is False
        assert "TRY_CAST" in fragment_duck.expression
        assert str(source_value) in fragment_duck.expression

        # Note: PostgreSQL test would require actual database connection
        # Multi-database E2E testing happens in integration tests


class TestIsOperationMultiDatabaseConsistency:
    """Test is() operation consistency across DuckDB and PostgreSQL"""

    @pytest.mark.parametrize("fhirpath_type,literal_value,literal_type", [
        ("Integer", 5, "integer"),
        ("String", "hello", "string"),
        ("Boolean", True, "boolean"),
        ("Decimal", 3.14, "decimal"),
    ])
    def test_is_operation_consistency(self, duckdb_dialect, fhirpath_type, literal_value, literal_type):
        """Test that is() generates SQL for both dialects (structure validation)"""
        # Test DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text=str(literal_value),
            value=literal_value,
            literal_type=literal_type
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"{literal_value} is {fhirpath_type}",
            operation="is",
            target_type=fhirpath_type
        )
        type_op_node.children = [literal_node]

        fragment_duck = translator_duck.visit_type_operation(type_op_node)

        # Validate DuckDB fragment structure
        assert isinstance(fragment_duck, SQLFragment)
        assert fragment_duck.requires_unnest is False
        assert fragment_duck.is_aggregate is False
        assert "CASE" in fragment_duck.expression
        # Boolean values are uppercased in SQL (TRUE/FALSE)
        expected_value = str(literal_value).upper() if isinstance(literal_value, bool) else str(literal_value)
        assert expected_value in fragment_duck.expression

        # Note: PostgreSQL test would require actual database connection
        # Multi-database E2E testing happens in integration tests


class TestDialectTypeCheckMethod:
    """Test dialect generate_type_check() method directly"""

    def test_duckdb_generate_type_check_integer(self, duckdb_dialect):
        """Test DuckDB generate_type_check for Integer type"""
        sql = duckdb_dialect.generate_type_check("5", "integer")

        assert "CASE" in sql
        assert "5" in sql
        assert "typeof" in sql
        assert "INTEGER" in sql
        assert "IS NULL THEN false" in sql

    def test_duckdb_generate_type_check_string(self, duckdb_dialect):
        """Test DuckDB generate_type_check for String type"""
        sql = duckdb_dialect.generate_type_check("'hello'", "string")

        assert "CASE" in sql
        assert "'hello'" in sql
        assert "typeof" in sql
        assert "VARCHAR" in sql

    def test_duckdb_generate_type_check_unknown_type(self, duckdb_dialect):
        """Test DuckDB generate_type_check with unknown type returns false"""
        sql = duckdb_dialect.generate_type_check("value", "UnknownType")

        assert sql == "false"

    def test_postgresql_generate_type_check_integer(self, postgresql_dialect):
        """Test PostgreSQL generate_type_check for Integer type"""
        sql = postgresql_dialect.generate_type_check("5", "integer")

        assert "CASE" in sql
        assert "5" in sql
        assert "pg_typeof" in sql
        assert "integer" in sql or "bigint" in sql
        assert "IS NULL THEN false" in sql

    def test_postgresql_generate_type_check_string(self, postgresql_dialect):
        """Test PostgreSQL generate_type_check for String type"""
        sql = postgresql_dialect.generate_type_check("'hello'", "string")

        assert "CASE" in sql
        assert "'hello'" in sql
        assert "pg_typeof" in sql
        assert "text" in sql

    def test_postgresql_generate_type_check_unknown_type(self, postgresql_dialect):
        """Test PostgreSQL generate_type_check with unknown type returns false"""
        sql = postgresql_dialect.generate_type_check("value", "UnknownType")

        assert sql == "false"


class TestIsOperationNullHandling:
    """Test is() operation with NULL values"""

    def test_is_with_null_returns_false_duckdb(self, duckdb_dialect):
        """Test that NULL values return false in type checking (DuckDB)"""
        sql = duckdb_dialect.generate_type_check("NULL", "integer")

        # Should contain explicit NULL check returning false
        assert "IS NULL THEN false" in sql

    def test_is_with_null_returns_false_postgresql(self, postgresql_dialect):
        """Test that NULL values return false in type checking (PostgreSQL)"""
        sql = postgresql_dialect.generate_type_check("NULL", "string")

        # Should contain explicit NULL check returning false
        assert "IS NULL THEN false" in sql


class TestOfTypeOperationBasicTypes:
    """Test ofType() operation with basic FHIRPath types"""

    def test_oftype_integer_type_duckdb(self, duckdb_dialect):
        """Test ofType() with Integer type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: identifier ofType Integer
        # In practice, this would come from a field containing a mixed-type array
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="mixedArray",
            identifier="mixedArray"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="mixedArray ofType Integer",
            operation="ofType",
            target_type="Integer"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "json_each" in fragment.expression
        assert "json_group_array" in fragment.expression
        assert "'UBIGINT'" in fragment.expression or "'INTEGER'" in fragment.expression

    def test_oftype_string_type_duckdb(self, duckdb_dialect):
        """Test ofType() with String type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: collection ofType String
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="mixedArray",
            identifier="mixedArray"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="mixedArray ofType String",
            operation="ofType",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "json_each" in fragment.expression
        assert "json_group_array" in fragment.expression
        assert "VARCHAR" in fragment.expression

    def test_oftype_decimal_type_duckdb(self, duckdb_dialect):
        """Test ofType() with Decimal type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create: collection ofType Decimal
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="numericArray",
            identifier="numericArray"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="numericArray ofType Decimal",
            operation="ofType",
            target_type="Decimal"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "json_each" in fragment.expression
        assert "json_group_array" in fragment.expression
        assert "DOUBLE" in fragment.expression or "DECIMAL" in fragment.expression


class TestOfTypeOperationPostgreSQL:
    """Test ofType() operation with PostgreSQL dialect"""

    def test_oftype_integer_type_postgresql(self, postgresql_dialect):
        """Test ofType() with Integer type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: collection ofType Integer
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="mixedArray",
            identifier="mixedArray"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="mixedArray ofType Integer",
            operation="ofType",
            target_type="Integer"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.requires_unnest is False
        assert fragment.is_aggregate is False
        assert "jsonb_array_elements" in fragment.expression
        assert "jsonb_agg" in fragment.expression
        assert "jsonb_typeof" in fragment.expression
        assert "elem::text ~ '^-?[0-9]+$'" in fragment.expression

    def test_oftype_string_type_postgresql(self, postgresql_dialect):
        """Test ofType() with String type on PostgreSQL"""
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")

        # Create: collection ofType String
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="stringArray",
            identifier="stringArray"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="stringArray ofType String",
            operation="ofType",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "jsonb_array_elements" in fragment.expression
        assert "jsonb_agg" in fragment.expression
        assert "jsonb_typeof" in fragment.expression
        assert "string" in fragment.expression


class TestOfTypeOperationWithIdentifiers:
    """Test ofType() operation with identifiers (FHIR paths)"""

    def test_oftype_with_identifier_duckdb(self, duckdb_dialect):
        """Test ofType() with identifier expression on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Create: Observation.valueString ofType String
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueString",
            identifier="valueString"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="valueString ofType String",
            operation="ofType",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "json_each" in fragment.expression
        assert "json_group_array" in fragment.expression
        assert "valueString" in fragment.expression or "$.valueString" in fragment.expression


class TestOfTypeOperationErrorHandling:
    """Test ofType() operation error handling"""

    def test_oftype_operation_without_children_raises_error(self, duckdb_dialect):
        """Test that ofType() operation without children raises ValueError"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Create ofType() node without children
        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="ofType Integer",
            operation="ofType",
            target_type="Integer"
        )
        type_op_node.children = []

        with pytest.raises(ValueError, match="ofType\\(\\) operation requires an expression to filter"):
            translator.visit_type_operation(type_op_node)

    def test_oftype_unknown_type_returns_empty_array_duckdb(self, duckdb_dialect):
        """Test ofType() with unknown type returns empty array (DuckDB)"""
        sql = duckdb_dialect.generate_collection_type_filter("[1, 2, 3]", "UnknownType")
        assert sql == "[]"

    def test_oftype_unknown_type_returns_empty_array_postgresql(self, postgresql_dialect):
        """Test ofType() with unknown type returns empty array (PostgreSQL)"""
        sql = postgresql_dialect.generate_collection_type_filter("ARRAY[1, 2, 3]", "UnknownType")
        assert sql == "'[]'::jsonb"


class TestDialectCollectionTypeFilterMethod:
    """Test dialect generate_collection_type_filter() method directly"""

    def test_duckdb_generate_collection_type_filter_integer(self, duckdb_dialect):
        """Test DuckDB generate_collection_type_filter for Integer type"""
        sql = duckdb_dialect.generate_collection_type_filter("[1, 'hello', 2]", "integer")

        assert "json_each" in sql
        assert "json_group_array" in sql
        assert "'UBIGINT'" in sql or "'INTEGER'" in sql

    def test_duckdb_generate_collection_type_filter_string(self, duckdb_dialect):
        """Test DuckDB generate_collection_type_filter for String type"""
        sql = duckdb_dialect.generate_collection_type_filter("['hello', 1, 'world']", "string")

        assert "json_each" in sql
        assert "json_group_array" in sql
        assert "VARCHAR" in sql

    def test_postgresql_generate_collection_type_filter_integer(self, postgresql_dialect):
        """Test PostgreSQL generate_collection_type_filter for Integer type"""
        sql = postgresql_dialect.generate_collection_type_filter("ARRAY[1, 2, 3]", "integer")

        assert "jsonb_array_elements" in sql
        assert "jsonb_agg" in sql
        assert "jsonb_typeof" in sql
        assert "elem::text ~ '^-?[0-9]+$'" in sql

    def test_postgresql_generate_collection_type_filter_string(self, postgresql_dialect):
        """Test PostgreSQL generate_collection_type_filter for String type"""
        sql = postgresql_dialect.generate_collection_type_filter("ARRAY['hello', 'world']", "string")

        assert "jsonb_array_elements" in sql
        assert "jsonb_agg" in sql
        assert "jsonb_typeof" in sql
        assert "string" in sql


class TestOfTypeOperationMultiDatabaseConsistency:
    """Test ofType() operation consistency across DuckDB and PostgreSQL"""

    @pytest.mark.parametrize("target_type", [
        "Integer",
        "String",
        "Boolean",
        "Decimal",
        "DateTime",
        "Date",
        "Time",
    ])
    def test_oftype_operation_consistency(self, duckdb_dialect, target_type):
        """Test that ofType() generates SQL for both dialects (structure validation)"""
        # Test DuckDB
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Patient")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="collection",
            identifier="collection"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"collection ofType {target_type}",
            operation="ofType",
            target_type=target_type
        )
        type_op_node.children = [identifier_node]

        fragment_duck = translator_duck.visit_type_operation(type_op_node)

        # Validate DuckDB fragment structure
        assert isinstance(fragment_duck, SQLFragment)
        assert fragment_duck.requires_unnest is False
        assert fragment_duck.is_aggregate is False
        assert "json_each" in fragment_duck.expression
        assert "json_group_array" in fragment_duck.expression

        # Note: PostgreSQL test would require actual database connection
        # Multi-database E2E testing happens in integration tests


class TestTypeOperationPerformance:
    """Test performance of type operations (<10ms requirement)"""

    def test_is_operation_performance_duckdb(self, duckdb_dialect, benchmark):
        """Benchmark is() operation performance on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="5",
            value=5,
            literal_type="integer"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="5 is Integer",
            operation="is",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        # Benchmark the operation
        result = benchmark(translator.visit_type_operation, type_op_node)

        assert isinstance(result, SQLFragment)
        # Performance requirement: <10ms per operation
        # pytest-benchmark measures this automatically

    def test_as_operation_performance_duckdb(self, duckdb_dialect, benchmark):
        """Benchmark as() operation performance on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="'123'",
            value="123",
            literal_type="string"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="'123' as Integer",
            operation="as",
            target_type="Integer"
        )
        type_op_node.children = [literal_node]

        # Benchmark the operation
        result = benchmark(translator.visit_type_operation, type_op_node)

        assert isinstance(result, SQLFragment)

    def test_oftype_operation_performance_duckdb(self, duckdb_dialect, benchmark):
        """Benchmark ofType() operation performance on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="collection",
            identifier="collection"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="collection ofType Integer",
            operation="ofType",
            target_type="Integer"
        )
        type_op_node.children = [identifier_node]

        # Benchmark the operation
        result = benchmark(translator.visit_type_operation, type_op_node)

        assert isinstance(result, SQLFragment)


class TestTypeOperationComplexExpressions:
    """Test type operations with complex expression chains"""

    def test_is_with_function_call_result_duckdb(self, duckdb_dialect):
        """Test is() with result from function call"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Simulate: Patient.name.first().family is String
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="family",
            identifier="family"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="family is String",
            operation="is",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "typeof" in fragment.expression
        assert "VARCHAR" in fragment.expression

    def test_as_chained_with_where_duckdb(self, duckdb_dialect):
        """Test as() in context of where() filtering"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        # Simulate: value as Decimal (for subsequent filtering)
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="value",
            identifier="value"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="value as Decimal",
            operation="as",
            target_type="Decimal"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression
        assert "DOUBLE" in fragment.expression

    def test_oftype_with_nested_arrays_duckdb(self, duckdb_dialect):
        """Test ofType() with nested array structures"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Simulate: Patient.contact.name.given ofType String
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="given",
            identifier="given"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="given ofType String",
            operation="ofType",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "json_each" in fragment.expression
        assert "json_group_array" in fragment.expression


class TestTypeOperationAdditionalTypes:
    """Test type operations with additional type scenarios"""

    def test_is_quantity_type_duckdb(self, duckdb_dialect):
        """Test is() with Quantity type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueQuantity",
            identifier="valueQuantity"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="valueQuantity is Quantity",
            operation="is",
            target_type="Quantity"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        # Quantity is treated as a structured type
        assert "CASE" in fragment.expression

    def test_is_age_profile_resolves_to_quantity_duckdb(self, duckdb_dialect):
        """Age profile should resolve to Quantity canonical type."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueQuantity",
            identifier="valueQuantity"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="valueQuantity is Age",
            operation="is",
            target_type="Age"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE" in fragment.expression

    def test_is_duration_profile_resolves_to_quantity_duckdb(self, duckdb_dialect):
        """Duration profile should resolve to Quantity canonical type."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="valueQuantity",
            identifier="valueQuantity"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="valueQuantity is Duration",
            operation="is",
            target_type="Duration"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.strip().upper().startswith("CASE")
        assert "$" in fragment.expression

    def test_is_system_boolean_alias_duckdb(self, duckdb_dialect):
        """System.Boolean should canonicalize to boolean primitive."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text="true",
            value=True,
            literal_type="boolean"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="true is System.Boolean",
            operation="is",
            target_type="System.Boolean"
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "BOOLEAN" in fragment.expression or "boolean" in fragment.expression.lower()

    def test_as_quantity_type_duckdb(self, duckdb_dialect):
        """Test as() with Quantity type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        parser = FHIRPathParser()
        type_op_node = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("Observation.value as Quantity").get_ast()
        )

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert fragment.expression.strip().upper().startswith("CASE WHEN")
        assert "$.valueQuantity" in fragment.expression
        assert "$.value" in fragment.expression
        assert fragment.metadata.get("mode") == "complex"
        assert fragment.metadata.get("discriminator_fields") == ["value"]

    @pytest.mark.parametrize(
        "resource_type, expression, expected_path, expected_variant, expected_fields",
        [
            (
                "Observation",
                "Observation.value as Quantity",
                ["valueQuantity"],
                "valueQuantity",
                ["value"],
            ),
            (
                "Observation",
                "Observation.value.as(Quantity)",
                ["valueQuantity"],
                "valueQuantity",
                ["value"],
            ),
            (
                "Observation",
                "Observation.value as CodeableConcept",
                ["valueCodeableConcept"],
                "valueCodeableConcept",
                ["coding"],
            ),
            (
                "Observation",
                "Observation.value as Range",
                ["valueRange"],
                "valueRange",
                ["low"],
            ),
            (
                "Observation",
                "Observation.value as Ratio",
                ["valueRatio"],
                "valueRatio",
                ["numerator", "denominator"],
            ),
            (
                "Procedure",
                "Procedure.performed as Period",
                ["performedPeriod"],
                "performedPeriod",
                ["start"],
            ),
            (
                "Procedure",
                "Procedure.performed as Range",
                ["performedRange"],
                "performedRange",
                ["low"],
            ),
            (
                "Procedure",
                "Procedure.performed.as(Period)",
                ["performedPeriod"],
                "performedPeriod",
                ["start"],
            ),
            (
                "Condition",
                "Condition.onset as Period",
                ["onsetPeriod"],
                "onsetPeriod",
                ["start"],
            ),
        ],
    )
    def test_complex_type_casts_duckdb(
        self,
        duckdb_dialect,
        resource_type,
        expression,
        expected_path,
        expected_variant,
        expected_fields,
    ):
        """Ensure complex polymorphic casts hydrate the correct JSON structure."""
        translator = ASTToSQLTranslator(duckdb_dialect, resource_type)
        parser = FHIRPathParser()
        ast = parser.parse(expression.get_ast())

        fragments = translator.translate(ast)
        result_fragment = fragments[-1]

        assert result_fragment.expression.strip().upper().startswith("CASE WHEN")
        assert result_fragment.metadata.get("mode") == "complex"
        assert result_fragment.metadata.get("variant_property") == expected_variant
        assert result_fragment.metadata.get("discriminator_fields") == expected_fields
        for field in expected_fields:
            assert f"$.{field}" in result_fragment.expression
        assert translator.context.parent_path == expected_path

    def test_complex_type_cast_with_nested_collection_duckdb(self, duckdb_dialect):
        """Observation.component.value should cast Quantity elements inside arrays."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        parser = FHIRPathParser()
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("Observation.component.value as Quantity").get_ast()
        )

        fragments = translator.translate(ast)
        assert len(fragments) >= 3
        quantity_fragment = fragments[-1]

        assert quantity_fragment.expression.strip().upper().startswith("CASE WHEN")
        assert "$.valueQuantity" in quantity_fragment.expression
        assert "$.value" in quantity_fragment.expression
        assert quantity_fragment.metadata.get("variant_property") == "valueQuantity"
        assert quantity_fragment.metadata.get("discriminator_fields") == ["value"]
        assert translator.context.parent_path == ["component", "valueQuantity"]

    def test_oftype_quantity_type_duckdb(self, duckdb_dialect):
        """Test ofType() with Quantity type on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="values",
            identifier="values"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="values ofType Quantity",
            operation="ofType",
            target_type="Quantity"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        # Quantity ofType currently normalises to empty set (complex filtering pending)
        assert fragment.expression.strip() == "[]"


class TestExtensionFunctionTranslation:
    """Tests for extension() function translation including type operations."""

    def test_extension_value_is_quantity_typecheck_duckdb(self, duckdb_dialect):
        """extension().value should translate for type checks on DuckDB."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        parser = FHIRPathParser()
        expr = (
            "Observation.extension('http://example.com/fhir/StructureDefinition/patient-age')"
            ".value is Quantity"
        )
        ast = parser.parse(expr.get_ast())

        fragments = translator.translate(ast)
        assert fragments, "Translator should return at least one fragment"
        sql_expr = fragments[-1].expression
        assert "list_filter" in sql_expr
        assert "patient-age" in sql_expr
        assert "valueQuantity" in sql_expr

    def test_extension_value_is_quantity_typecheck_postgresql(self, postgresql_dialect):
        """extension().value should translate for type checks on PostgreSQL."""
        translator = ASTToSQLTranslator(postgresql_dialect, "Observation")
        parser = FHIRPathParser()
        expr = (
            "Observation.extension('http://example.com/fhir/StructureDefinition/patient-age')"
            ".value is Quantity"
        )
        ast = parser.parse(expr.get_ast())

        fragments = translator.translate(ast)
        assert fragments, "Translator should return at least one fragment"
        sql_expr = fragments[-1].expression
        assert "jsonb_array_elements" in sql_expr
        assert "patient-age" in sql_expr
        assert "valueQuantity" in sql_expr

    def test_extension_requires_argument(self, duckdb_dialect):
        """extension() must receive a URL argument."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        node = FunctionCallNode(
            node_type="functionCall",
            text="Observation.extension()",
            function_name="extension",
            arguments=[]
        )
        with pytest.raises(ValueError):
            translator.visit_function_call(node)

    def test_extension_value_oftype_quantity_duckdb(self, duckdb_dialect):
        """extension().value.ofType(Quantity) should emit filtering SQL."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        parser = FHIRPathParser()
        expr = (
            "Observation.extension('http://example.com/fhir/StructureDefinition/patient-age')"
            ".value.ofType(Quantity)"
        )
        ast = parser.parse(expr.get_ast())

        fragments = translator.translate(ast)
        sql_expr = fragments[-1].expression.strip()
        assert sql_expr == "[]"

    def test_extension_value_oftype_duration_duckdb_returns_empty(self, duckdb_dialect):
        """extension().value.ofType(Duration) should be empty array when alias missing."""
        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        parser = FHIRPathParser()
        expr = (
            "Observation.extension('http://example.com/fhir/StructureDefinition/patient-age')"
            ".value.ofType(Duration)"
        )
        ast = parser.parse(expr.get_ast())

        fragments = translator.translate(ast)
        sql_expr = fragments[-1].expression.strip()
        assert sql_expr == "[]"


class TestTypeOperationEmptyAndNullCollections:
    """Test type operations with empty and null collections"""

    def test_is_with_empty_collection_duckdb(self, duckdb_dialect):
        """Test is() with identifier that might be empty"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        # Test with identifier that could be empty collection
        identifier_node = IdentifierNode(
            node_type="identifier",
            text="emptyField",
            identifier="emptyField"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text="emptyField is String",
            operation="is",
            target_type="String"
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        # Should generate type check SQL
        assert "CASE" in fragment.expression
        assert "typeof" in fragment.expression

    def test_as_with_null_value_duckdb(self, duckdb_dialect):
        """Test as() with null value returns null"""
        sql = duckdb_dialect.generate_type_cast("NULL", "integer")

        # TRY_CAST(NULL AS INTEGER) returns NULL
        assert "TRY_CAST" in sql
        assert "NULL" in sql
        assert "INTEGER" in sql

    def test_as_with_null_value_postgresql(self, postgresql_dialect):
        """Test as() with null value returns null (PostgreSQL)"""
        sql = postgresql_dialect.generate_type_cast("NULL", "integer")

        # PostgreSQL CASE statement with NULL handling
        assert "CASE" in sql
        assert "NULL" in sql
        assert "INTEGER" in sql

    def test_oftype_with_empty_collection_duckdb(self, duckdb_dialect):
        """Test ofType() with empty collection returns empty"""
        sql = duckdb_dialect.generate_collection_type_filter("[]", "integer")

        # Empty collection filtered should return empty collection
        assert "json_each" in sql
        assert "json_group_array" in sql
        assert "'[]'" in sql

    def test_oftype_with_empty_collection_postgresql(self, postgresql_dialect):
        """Test ofType() with empty collection returns empty (PostgreSQL)"""
        sql = postgresql_dialect.generate_collection_type_filter("ARRAY[]", "string")

        # PostgreSQL empty array handling
        assert "jsonb_array_elements" in sql
        assert "jsonb_agg" in sql
        assert "'[]'::jsonb" in sql


class TestTypeOperationAllTypeCoverage:
    """Comprehensive test ensuring all FHIRPath types are covered"""

    @pytest.mark.parametrize("fhirpath_type,literal_value,literal_type", [
        ("String", "test", "string"),
        ("Integer", 42, "integer"),
        ("Decimal", 3.14159, "decimal"),
        ("Boolean", False, "boolean"),
        ("DateTime", "2024-01-01T00:00:00Z", "string"),
        ("Date", "2024-01-01", "string"),
        ("Time", "12:30:45", "string"),
    ])
    def test_is_all_types_duckdb(self, duckdb_dialect, fhirpath_type, literal_value, literal_type):
        """Test is() with all supported FHIRPath types on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text=str(literal_value),
            value=literal_value,
            literal_type=literal_type
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"{literal_value} is {fhirpath_type}",
            operation="is",
            target_type=fhirpath_type
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "CASE" in fragment.expression
        assert "typeof" in fragment.expression

    @pytest.mark.parametrize("fhirpath_type,literal_value,literal_type", [
        ("String", "test", "string"),
        ("Integer", 42, "integer"),
        ("Decimal", 3.14159, "decimal"),
        ("Boolean", False, "boolean"),
        ("DateTime", "2024-01-01T00:00:00Z", "string"),
        ("Date", "2024-01-01", "string"),
        ("Time", "12:30:45", "string"),
    ])
    def test_as_all_types_duckdb(self, duckdb_dialect, fhirpath_type, literal_value, literal_type):
        """Test as() with all supported FHIRPath types on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        literal_node = LiteralNode(
            node_type="literal",
            text=str(literal_value),
            value=literal_value,
            literal_type=literal_type
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"{literal_value} as {fhirpath_type}",
            operation="as",
            target_type=fhirpath_type
        )
        type_op_node.children = [literal_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        assert "TRY_CAST" in fragment.expression

    @pytest.mark.parametrize("fhirpath_type", [
        "String",
        "Integer",
        "Decimal",
        "Boolean",
        "DateTime",
        "Date",
        "Time",
    ])
    def test_oftype_all_types_duckdb(self, duckdb_dialect, fhirpath_type):
        """Test ofType() with all supported FHIRPath types on DuckDB"""
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")

        identifier_node = IdentifierNode(
            node_type="identifier",
            text="collection",
            identifier="collection"
        )

        type_op_node = TypeOperationNode(
            node_type="typeOperation",
            text=f"collection ofType {fhirpath_type}",
            operation="ofType",
            target_type=fhirpath_type
        )
        type_op_node.children = [identifier_node]

        fragment = translator.visit_type_operation(type_op_node)

        assert isinstance(fragment, SQLFragment)
        primitive_targets = {"Integer", "String", "Boolean", "Decimal", "DateTime", "Date", "Time"}
        if fhirpath_type in primitive_targets:
            assert "json_each" in fragment.expression
            assert "json_group_array" in fragment.expression
        else:
            assert fragment.expression.strip() == "[]"


class TestConformsToFunction:
    """Tests for conformsTo() function translation."""

    def test_conformsto_duckdb(self, duckdb_dialect):
        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        parser = FHIRPathParser()
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("Patient.conformsTo('http://example.com/Profile')").get_ast()
        )

        fragments = translator.translate(ast)
        fragment = fragments[-1]

        assert "profile" in fragment.expression
        assert "json_each" in fragment.expression
        assert "http://example.com/Profile" in fragment.expression
        assert fragment.metadata.get("function") == "conformsTo"
        assert fragment.metadata.get("profile_url") == "http://example.com/Profile"

    def test_conformsto_postgresql(self, postgresql_dialect):
        translator = ASTToSQLTranslator(postgresql_dialect, "Patient")
        parser = FHIRPathParser()
        ast = convert_enhanced_ast_to_fhirpath_ast(
            parser.parse("Patient.conformsTo('http://example.com/Profile')").get_ast()
        )

        fragments = translator.translate(ast)
        fragment = fragments[-1]

        assert "profile" in fragment.expression
        assert "jsonb_array_elements" in fragment.expression
        assert "http://example.com/Profile" in fragment.expression
        assert fragment.metadata.get("function") == "conformsTo"


class TestTypeExpressionParsing:
    """Test TypeExpression AST parsing for is/as operations (SP-022-006).

    These tests verify that TypeExpression nodes are correctly routed to
    visit_type_operation() instead of being treated as wrapper nodes or
    function calls. This addresses the bug where TypeSpecifier child nodes
    were being visited independently before the parent TypeExpression was
    properly handled.
    """

    def test_is_quantity_does_not_raise_unknown_type(self, duckdb_dialect):
        """Test that 'Observation.value is Quantity' does not raise Unknown type error.

        SP-022-006: Previously this raised '[FP040] Unknown FHIR type Unknown'
        because the TypeSpecifier child was visited before the parent TypeExpression.
        """
        parser = FHIRPathParser()
        ast = parser.parse('Observation.value is Quantity').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Observation')
        # This should not raise FHIRPathTranslationError
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        assert len(fragments) > 0
        # The result should contain a type check expression
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)

    def test_is_instant_does_not_raise_unknown_type(self, duckdb_dialect):
        """Test that 'Observation.issued is instant' does not raise Unknown type error."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.issued is instant').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Observation')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)

    def test_as_quantity_with_field_access(self, duckdb_dialect):
        """Test that 'Observation.value.as(Quantity).unit' works without error."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.value.as(Quantity).unit').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Observation')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"

    def test_as_quantity_parenthesized(self, duckdb_dialect):
        """Test that '(Observation.value as Quantity).unit' works without error."""
        parser = FHIRPathParser()
        ast = parser.parse('(Observation.value as Quantity).unit').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Observation')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"

    def test_is_boolean_literal(self, duckdb_dialect):
        """Test that 'true is Boolean' works correctly."""
        parser = FHIRPathParser()
        ast = parser.parse('true is Boolean').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Patient')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)

    def test_is_string_literal(self, duckdb_dialect):
        """Test that \"'hello' is String\" works correctly."""
        parser = FHIRPathParser()
        ast = parser.parse("'hello' is String").get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Patient')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)

    def test_is_integer_literal(self, duckdb_dialect):
        """Test that '5 is Integer' works correctly."""
        parser = FHIRPathParser()
        ast = parser.parse('5 is Integer').get_ast()

        translator = ASTToSQLTranslator(duckdb_dialect, 'Patient')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)

    def test_type_expression_postgresql(self, postgresql_dialect):
        """Test TypeExpression parsing on PostgreSQL dialect."""
        parser = FHIRPathParser()
        ast = parser.parse('Observation.value is Quantity').get_ast()

        translator = ASTToSQLTranslator(postgresql_dialect, 'Observation')
        fragments = translator.translate(ast)

        assert fragments, "Should produce fragments"
        last_fragment = fragments[-1]
        assert isinstance(last_fragment, SQLFragment)
