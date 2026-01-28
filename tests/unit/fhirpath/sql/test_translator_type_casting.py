"""
Unit tests for type casting in comparison operations (SP-022-005).

Validates that VARCHAR values from JSON extraction are correctly cast when
compared against typed literals (decimal, integer, date, datetime, boolean).
"""

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


class _CastingDialect:
    """Minimal dialect implementation with safe casting for translation testing."""

    name = "TEST"

    def generate_datetime_literal(self, datetime_value: str) -> str:
        return f"TIMESTAMP '{datetime_value.replace('T', ' ')}'"

    def generate_date_literal(self, date_value: str) -> str:
        return f"DATE '{date_value}'"

    def generate_time_literal(self, time_value: str) -> str:
        return f"TIME '{time_value}'"

    def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
        return f"({left_expr} {operator} {right_expr})"

    def generate_logical_combine(self, left_condition: str, operator: str, right_condition: str) -> str:
        return f"({left_condition}) {operator} ({right_condition})"

    def extract_json_field(self, column: str, path: str) -> str:
        return f"json_extract_string({column}, '{path}')"

    def extract_primitive_value(self, column: str, path: str) -> str:
        return f"COALESCE(json_extract_string({column}, '{path}.value'), json_extract_string({column}, '{path}'))"

    def safe_cast_to_decimal(self, expression: str) -> str:
        return f"TRY_CAST({expression} AS DECIMAL)"

    def safe_cast_to_integer(self, expression: str) -> str:
        return f"TRY_CAST({expression} AS BIGINT)"

    def safe_cast_to_date(self, expression: str) -> str:
        return f"TRY_CAST({expression} AS DATE)"

    def safe_cast_to_timestamp(self, expression: str) -> str:
        return f"TRY_CAST({expression} AS TIMESTAMP)"

    def safe_cast_to_boolean(self, expression: str) -> str:
        return f"TRY_CAST({expression} AS BOOLEAN)"

    def extract_json_string(self, column: str, path: str) -> str:
        """Extract JSON field as string for string comparisons."""
        return f"json_extract_string({column}, '{path}')"

    def generate_type_cast(self, expression: str, target_type: str) -> str:
        """Generate type casting for arithmetic operations."""
        type_map = {
            "string": "VARCHAR",
            "integer": "INTEGER",
            "decimal": "DECIMAL",
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMP",
            "date": "DATE",
            "time": "TIME",
        }
        normalized_type = target_type.lower() if target_type else ""
        sql_type = type_map.get(normalized_type, "VARCHAR")
        return f"TRY_CAST({expression} AS {sql_type})"


@pytest.fixture
def translator():
    """Create translator with casting-capable stub dialect."""
    dialect = _CastingDialect()
    return ASTToSQLTranslator(dialect, "Observation")


def _translate_expression(translator: ASTToSQLTranslator, expression: str) -> str:
    parser = FHIRPathParser()
    enhanced_ast = parser.parse(expression).get_ast()
    fhirpath_ast = enhanced_ast
    fragments = translator.translate(fhirpath_ast)
    assert fragments, "Translator should produce at least one fragment"
    return fragments[-1].expression


class TestNumericCasting:
    """Tests for numeric type casting in comparisons."""

    def test_json_field_compared_to_decimal_literal_uses_try_cast(self, translator):
        """JSON-extracted value compared to decimal should use TRY_CAST."""
        sql = _translate_expression(translator, "Observation.valueInteger > 180.0")
        assert "TRY_CAST" in sql
        assert "AS DECIMAL" in sql
        assert "180.0" in sql

    def test_json_field_compared_to_integer_literal_uses_try_cast(self, translator):
        """JSON-extracted value compared to integer should use TRY_CAST."""
        sql = _translate_expression(translator, "Observation.valueInteger > 42")
        assert "TRY_CAST" in sql
        # Integer comparison should cast to DECIMAL or BIGINT
        assert "AS DECIMAL" in sql or "AS BIGINT" in sql

    def test_decimal_literal_vs_json_field_casts_json(self, translator):
        """Decimal literal on left, JSON on right - should cast the JSON side."""
        sql = _translate_expression(translator, "180.0 < Observation.valueInteger")
        assert "TRY_CAST" in sql
        assert "AS DECIMAL" in sql


class TestDateTimeCasting:
    """Tests for date/time type casting in comparisons."""

    def test_json_field_compared_to_date_literal_uses_try_cast(self):
        """JSON-extracted date compared to date literal should use TRY_CAST."""
        dialect = _CastingDialect()
        translator = ASTToSQLTranslator(dialect, "Patient")
        sql = _translate_expression(translator, "Patient.birthDate < @2025-01-01")
        assert "TRY_CAST" in sql
        assert "AS DATE" in sql
        assert "DATE '2025-01-01'" in sql

    def test_json_field_compared_to_datetime_literal_uses_try_cast(self):
        """JSON-extracted datetime compared to datetime literal should use TRY_CAST."""
        dialect = _CastingDialect()
        translator = ASTToSQLTranslator(dialect, "Observation")
        sql = _translate_expression(translator, "Observation.issued < @2025-01-01T12:00:00")
        assert "TRY_CAST" in sql
        assert "AS TIMESTAMP" in sql


class TestNoUnnecessaryCasting:
    """Tests to ensure casting is not applied when not needed."""

    def test_string_comparison_no_cast(self, translator):
        """String literals should not trigger casting."""
        sql = _translate_expression(translator, "Observation.status = 'final'")
        assert "TRY_CAST" not in sql

    def test_boolean_literal_uses_cast(self):
        """Boolean comparisons should use casting for JSON-extracted values."""
        dialect = _CastingDialect()
        translator = ASTToSQLTranslator(dialect, "Patient")
        sql = _translate_expression(translator, "Patient.active = true")
        assert "TRY_CAST" in sql
        assert "AS BOOLEAN" in sql


class TestLiteralMetadata:
    """Tests for literal type metadata in SQLFragment."""

    def test_literal_fragment_has_type_metadata(self, translator):
        """Literal nodes should include type metadata."""
        parser = FHIRPathParser()
        enhanced_ast = parser.parse("180.0").get_ast()
        fragments = translator.translate(enhanced_ast)

        literal_fragment = fragments[-1]
        assert literal_fragment.metadata.get("is_literal") is True
        assert literal_fragment.metadata.get("literal_type") == "decimal"

    def test_integer_literal_has_integer_type(self, translator):
        """Integer literals should have integer type in metadata."""
        parser = FHIRPathParser()
        enhanced_ast = parser.parse("42").get_ast()
        fragments = translator.translate(enhanced_ast)

        literal_fragment = fragments[-1]
        assert literal_fragment.metadata.get("is_literal") is True
        assert literal_fragment.metadata.get("literal_type") == "integer"

    def test_date_literal_has_date_type(self):
        """Date literals should have date type in metadata."""
        dialect = _CastingDialect()
        translator = ASTToSQLTranslator(dialect, "Patient")
        parser = FHIRPathParser()
        enhanced_ast = parser.parse("@2025-01-01").get_ast()
        fragments = translator.translate(enhanced_ast)

        literal_fragment = fragments[-1]
        assert literal_fragment.metadata.get("is_literal") is True
        assert literal_fragment.metadata.get("literal_type") == "date"


class TestJsonStringMetadata:
    """Tests for JSON string metadata in SQLFragment."""

    def test_json_extracted_field_has_metadata(self, translator):
        """JSON-extracted fields should have is_json_string metadata."""
        parser = FHIRPathParser()
        enhanced_ast = parser.parse("Observation.valueInteger").get_ast()
        fragments = translator.translate(enhanced_ast)

        # Find the fragment with the JSON extraction (not the resource type reference)
        json_fragment = None
        for f in fragments:
            if "json_extract" in f.expression:
                json_fragment = f
                break

        assert json_fragment is not None
        assert json_fragment.metadata.get("is_json_string") is True
