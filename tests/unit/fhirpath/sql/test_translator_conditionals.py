"""Unit tests for conditional function translations (iif)."""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.exceptions import (
    FHIRPathValidationError,
    FHIRPathEvaluationError,
)

from .test_translator_converts_to import _StubDialect

try:
    from fhir4ds.dialects.duckdb import DuckDBDialect

    DUCKDB_AVAILABLE = True
except ImportError:  # pragma: no cover - dialect optional in test env
    DUCKDB_AVAILABLE = False

try:
    from fhir4ds.dialects.postgresql import PostgreSQLDialect

    POSTGRESQL_AVAILABLE = True
except ImportError:  # pragma: no cover - dialect optional in test env
    POSTGRESQL_AVAILABLE = False


def _translate_expression(
    translator: ASTToSQLTranslator,
    parser: FHIRPathParser,
    expression: str,
):
    ast = parser.parse(expression).get_ast()
    fragments = translator.translate(ast)
    return fragments[-1]


@pytest.fixture()
def stub_env():
    """Provide translator and parser pair backed by stub dialect."""
    translator = ASTToSQLTranslator(_StubDialect(), "Patient")
    parser = FHIRPathParser()
    return translator, parser


@pytest.fixture()
def duckdb_env():
    """Provide DuckDB translator + parser, skipping when unavailable."""
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    translator = ASTToSQLTranslator(DuckDBDialect(database=":memory:"), "Patient")
    parser = FHIRPathParser(database_type="duckdb")
    return translator, parser


@pytest.fixture()
def postgresql_env():
    """Provide PostgreSQL translator + parser, skipping when unavailable."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        dialect = PostgreSQLDialect(
            "postgresql://postgres:postgres@localhost:5432/postgres"
        )
    except Exception:
        pytest.skip("PostgreSQL not accessible")
    translator = ASTToSQLTranslator(dialect, "Patient")
    parser = FHIRPathParser(database_type="postgresql")
    return translator, parser


class TestIifTranslation:
    """Validate iif() translation under various scenarios."""

    def test_iif_generates_case_expression(self, stub_env):
        translator, parser = stub_env
        fragment = _translate_expression(translator, parser, "iif(true, 'yes', 'no')")

        sql = fragment.expression
        assert "CASE WHEN TRUE IS NULL THEN NULL" in sql
        assert "WHEN TRUE THEN 'yes'" in sql
        assert "ELSE 'no'" in sql
        assert fragment.metadata == {"function": "iif"}

    def test_iif_optional_false_branch_returns_empty_collection(self, stub_env):
        translator, parser = stub_env
        fragment = _translate_expression(translator, parser, "iif(false, 'value')")

        sql = fragment.expression
        assert "ELSE NULL" in sql

    def test_iif_rejects_non_boolean_condition(self, stub_env):
        translator, parser = stub_env
        with pytest.raises(FHIRPathValidationError):
            _translate_expression(translator, parser, "iif('not boolean', 'yes', 'no')")

    def test_iif_raises_for_multi_item_collection_target(self, stub_env):
        translator, parser = stub_env
        with pytest.raises(FHIRPathEvaluationError):
            _translate_expression(
                translator, parser, "('a' | 'b').iif(true, 'x', 'y')"
            )

    @pytest.mark.parametrize(
        "env_fixture,expected_snippet",
        [
            ("duckdb_env", "json_array_length"),
            ("postgresql_env", "jsonb_array_length"),
        ],
    )
    def test_iif_cardinality_validation_uses_dialect_length(
        self, request, env_fixture, expected_snippet
    ):
        translator, parser = request.getfixturevalue(env_fixture)
        fragment = _translate_expression(
            translator, parser, "Patient.name.iif(true, 'x', 'y')"
        )

        sql = fragment.expression.lower()
        assert expected_snippet in sql
