"""High-level comparison operator regression tests for Phase 3 fixes.

These tests validate the precision-aware temporal comparison logic introduced in
SP-008-008. They ensure identical SQL is produced for DuckDB and PostgreSQL
dialects, covering the true/false branches for all four comparison operators,
plus boundary behaviour such as full-precision fallbacks and time literals.
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


@pytest.fixture(scope="module")
def _parser() -> FHIRPathParser:
    """Shared parser instance so tests avoid reinitialisation overhead."""
    return FHIRPathParser()


def _translate(expression: str, dialect, parser: FHIRPathParser) -> str:
    """Translate an expression to its final SQL fragment for the given dialect."""
    ast = parser.parse(expression.get_ast())
    translator = ASTToSQLTranslator(dialect, "Patient")
    fragments = translator.translate(ast)
    assert fragments, "translation should yield at least one SQL fragment"
    return fragments[-1].expression


@pytest.mark.parametrize(
    ("expression", "expected_true_clause", "expected_false_clause"),
    [
        (
            "@2018-03 < @2018-03-01",
            "TIMESTAMP '2018-04-01 00:00:00' <= TIMESTAMP '2018-03-01 00:00:00'",
            "TIMESTAMP '2018-03-01 00:00:00' >= TIMESTAMP '2018-03-02 00:00:00'",
        ),
        (
            "@2018-03 <= @2018-03-01",
            "TIMESTAMP '2018-04-01 00:00:00' <= TIMESTAMP '2018-03-01 00:00:00'",
            "TIMESTAMP '2018-03-01 00:00:00' > TIMESTAMP '2018-03-02 00:00:00'",
        ),
        (
            "@2018-03 > @2018-03-01",
            "TIMESTAMP '2018-03-01 00:00:00' >= TIMESTAMP '2018-03-02 00:00:00'",
            "TIMESTAMP '2018-04-01 00:00:00' <= TIMESTAMP '2018-03-01 00:00:00'",
        ),
        (
            "@2018-03 >= @2018-03-01",
            "TIMESTAMP '2018-03-01 00:00:00' >= TIMESTAMP '2018-03-02 00:00:00'",
            "TIMESTAMP '2018-04-01 00:00:00' < TIMESTAMP '2018-03-01 00:00:00'",
        ),
    ],
)
@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_partial_temporal_comparisons_generate_case(
    expression: str,
    expected_true_clause: str,
    expected_false_clause: str,
    dialect_fixture: str,
    request: pytest.FixtureRequest,
    _parser: FHIRPathParser,
) -> None:
    """Partial temporal literals should emit CASE statements with NULL fallback."""
    dialect = request.getfixturevalue(dialect_fixture)
    sql = _translate(expression, dialect, _parser)

    assert sql.startswith("CASE"), "temporal comparison should produce CASE expression"
    assert "THEN TRUE" in sql and "THEN FALSE" in sql and "ELSE NULL" in sql
    assert expected_true_clause in sql
    assert expected_false_clause in sql


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_time_literal_precisions_align(dialect_fixture: str, request: pytest.FixtureRequest, _parser: FHIRPathParser) -> None:
    """Reduced-precision time literals should expand to inclusive ranges."""
    dialect = request.getfixturevalue(dialect_fixture)
    sql = _translate("@T10:30 > @T10:30:00", dialect, _parser)

    assert "TIME '10:30:00'" in sql  # range start
    assert "TIME '10:31:00'" in sql  # range end computed from minutes precision
    assert sql.count("TIME '10:30:00'") == 2  # start appears in true+false branches
    assert sql.startswith("CASE") and sql.endswith("END")


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_full_precision_temporal_uses_direct_comparison(
    dialect_fixture: str,
    request: pytest.FixtureRequest,
    _parser: FHIRPathParser,
) -> None:
    """When both operands are full precision the translator should fall back to direct comparison."""
    dialect = request.getfixturevalue(dialect_fixture)
    sql = _translate("@2018-03-01 < @2018-03-02", dialect, _parser)

    assert sql == "(DATE '2018-03-01' < DATE '2018-03-02')"


@pytest.mark.parametrize("dialect_fixture", ["duckdb_dialect", "postgresql_dialect"])
def test_mixed_precision_datetime_range_bounds(
    dialect_fixture: str,
    request: pytest.FixtureRequest,
    _parser: FHIRPathParser,
) -> None:
    """Mixed precision dateTime literals should convert to matching inclusive ranges."""
    dialect = request.getfixturevalue(dialect_fixture)
    sql = _translate("@2018-03-01T10:30 < @2018-03-01T10:30:00", dialect, _parser)

    # sanity-check both range endpoints appear for each operand
    assert "TIMESTAMP '2018-03-01 10:30:00'" in sql
    assert "TIMESTAMP '2018-03-01 10:31:00'" in sql
    assert sql.startswith("CASE")
