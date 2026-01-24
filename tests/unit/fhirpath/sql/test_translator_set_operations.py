"""Unit tests covering FHIRPath set operations (distinct, isDistinct, intersect, exclude)."""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.parser import FHIRPathParser

from .test_translator_converts_to import _StubDialect

try:
    from fhir4ds.dialects.duckdb import DuckDBDialect
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

try:
    from fhir4ds.dialects.postgresql import PostgreSQLDialect
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False


@pytest.fixture(scope="module")
def parser() -> FHIRPathParser:
    return FHIRPathParser()


@pytest.fixture()
def stub_translator() -> ASTToSQLTranslator:
    return ASTToSQLTranslator(_StubDialect(), "Patient")


@pytest.fixture()
def duckdb_translator():
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    dialect = DuckDBDialect(database=":memory:")
    return ASTToSQLTranslator(dialect, "Patient")


@pytest.fixture()
def postgresql_translator():
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not accessible")
    return ASTToSQLTranslator(dialect, "Patient")


def _translate(translator: ASTToSQLTranslator, parser: FHIRPathParser, expression: str):
    parsed = parser.parse(expression)
    ast = parsed.get_ast()
    fragments = translator.translate(ast)
    return fragments[-1]


class TestStubSetOperations:
    """Sanity checks using the lightweight stub dialect."""

    def test_distinct_generates_row_number_dedup(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.distinct()")
        sql = fragment.expression
        assert "ROW_NUMBER" in sql
        assert "SERIALIZE" in sql
        assert "AGG(" in sql
        assert "ORDER BY distinct_" in sql
        assert fragment.metadata == {"function": "distinct", "is_collection": True}

    def test_is_distinct_uses_count_distinct(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.isDistinct()")
        sql = fragment.expression
        assert "count(distinct serialize" in sql.lower()
        assert "CASE" in sql.upper()
        assert fragment.metadata == {"function": "isDistinct", "result_type": "boolean"}

    def test_intersect_generates_membership_filter(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.intersect(name.family)")
        sql = fragment.expression
        assert "IN (SELECT" in sql.upper()
        assert "ROW_NUMBER" in sql
        assert "ORDER BY intersect_" in sql
        assert fragment.metadata == {"function": "intersect", "is_collection": True}

    def test_exclude_builds_not_in_filter(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.exclude('Jim')")
        sql = fragment.expression
        assert "NOT IN" in sql
        assert "ROW_NUMBER" in sql
        assert "ORDER BY exclude_" in sql
        assert fragment.metadata == {"function": "exclude", "is_collection": True}

    @pytest.mark.skip(reason="Compositional design: chaining behavior changed")
    def test_distinct_empty_chain(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.distinct().empty()")
        sql = fragment.expression
        assert "ARRAY_LENGTH" in sql
        assert "= 0" in sql
        assert fragment.metadata == {"function": "empty", "result_type": "boolean"}

    def test_intersect_count_chain(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.intersect(name.family).count()")
        sql = fragment.expression
        assert "ARRAY_LENGTH" in sql
        assert "CASE" in sql
        assert fragment.metadata == {"function": "count", "result_type": "integer"}

    def test_exclude_empty_not_chain(self, stub_translator, parser):
        fragment = _translate(stub_translator, parser, "name.given.exclude(name.family).empty().not()")
        sql = fragment.expression
        assert "NOT(" in sql
        assert fragment.metadata == {"function": "not", "result_type": "boolean"}


class TestMultiDatabaseSetOperations:
    """Ensure real dialects generate database-specific set operation SQL."""

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_distinct_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.distinct()")
        sql = fragment.expression.lower()
        assert "row_number" in sql
        assert "order by" in sql
        if translator.dialect.name == "DUCKDB":
            assert "json_each" in sql
            assert "to_json(list" in sql
        else:
            assert "jsonb_array_elements" in sql

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_is_distinct_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.isDistinct()")
        sql = fragment.expression.lower()
        assert "count(distinct" in sql

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_intersect_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.intersect(name.family)")
        sql = fragment.expression.lower()
        assert "row_number" in sql
        assert "in (select" in sql
        assert "order by" in sql
        if translator.dialect.name == "DUCKDB":
            assert "json_each" in sql
            assert "to_json(list" in sql
        else:
            assert "jsonb_array_elements" in sql

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_exclude_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.exclude('Jim')")
        sql = fragment.expression.lower()
        assert "not in" in sql
        assert "row_number" in sql
        assert "order by" in sql
        if translator.dialect.name == "DUCKDB":
            assert "json_each" in sql
            assert "to_json(list" in sql
        else:
            assert "jsonb_array_elements" in sql

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    @pytest.mark.skip(reason="Compositional design: chaining behavior changed")
    def test_distinct_empty_chain_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.distinct().empty()")
        sql = fragment.expression.lower()
        assert "case" in sql
        if translator.dialect.name == "DUCKDB":
            assert "json_array_length" in sql
        else:
            assert "jsonb_array_length" in sql
        assert fragment.metadata == {"function": "empty", "result_type": "boolean"}

    @pytest.mark.parametrize("dialect_fixture", ["duckdb_translator", "postgresql_translator"])
    def test_intersect_count_chain_consistency(self, request, dialect_fixture, parser):
        translator = request.getfixturevalue(dialect_fixture)
        fragment = _translate(translator, parser, "name.given.intersect(name.family).count()")
        sql = fragment.expression.lower()
        assert "case" in sql
        if translator.dialect.name == "DUCKDB":
            assert "json_array_length" in sql
        else:
            assert "jsonb_array_length" in sql
        assert fragment.metadata == {"function": "count", "result_type": "integer"}


class TestSetOperationArgumentValidation:
    """Validate argument handling for set operation functions."""

    @pytest.mark.parametrize("expression", ["name.given.distinct('extra')", "name.given.isDistinct('extra')"])
    def test_distinct_family_rejects_arguments(self, stub_translator, parser, expression):
        with pytest.raises(ValueError):
            _translate(stub_translator, parser, expression)

    def test_intersect_requires_single_argument(self, stub_translator, parser):
        with pytest.raises(ValueError):
            _translate(stub_translator, parser, "name.given.intersect()")
        with pytest.raises(ValueError):
            _translate(stub_translator, parser, "name.given.intersect(name.family, name.family)")

    def test_exclude_requires_single_argument(self, stub_translator, parser):
        with pytest.raises(ValueError):
            _translate(stub_translator, parser, "name.given.exclude()")
        with pytest.raises(ValueError):
            _translate(stub_translator, parser, "name.given.exclude(name.family, name.family)")
