"""Integration-style translator checks for type casting operations."""

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


parser = FHIRPathParser()


def _translate(expression: str, translator: ASTToSQLTranslator):
    ast = parser.parse(expression.get_ast())
    translator.fragments.clear()
    translator.context.parent_path = []
    fragments = translator.translate(ast)
    return fragments[-1], translator.context.parent_path


@pytest.mark.integration
def test_duckdb_quantity_cast_path_merges_variant():
    translator = ASTToSQLTranslator(DuckDBDialect(database=":memory:"), "Observation")
    fragment, parent_path = _translate("(Observation.value as Quantity).unit", translator)

    assert fragment.expression.endswith("'$.valueQuantity.unit')")
    assert parent_path == ["valueQuantity", "unit"]


@pytest.mark.integration
def test_duckdb_range_cast_applies_discriminator():
    translator = ASTToSQLTranslator(DuckDBDialect(database=":memory:"), "Observation")
    fragment, parent_path = _translate("Observation.value as Range", translator)

    assert fragment.expression.strip().upper().startswith("CASE WHEN")
    assert "$.valueRange" in fragment.expression
    assert fragment.metadata.get("discriminator_fields") == ["low"]
    assert parent_path == ["valueRange"]


@pytest.mark.integration
def test_condition_period_cast_sets_path():
    translator = ASTToSQLTranslator(DuckDBDialect(database=":memory:"), "Condition")
    fragment, parent_path = _translate("Condition.onset as Period", translator)

    assert fragment.expression.strip().upper().startswith("CASE WHEN")
    assert "$.onsetPeriod" in fragment.expression
    assert parent_path == ["onsetPeriod"]


@pytest.mark.integration
def test_postgresql_quantity_cast_case_expression():
    try:
        translator = ASTToSQLTranslator(
            PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres"),
            "Observation",
        )
    except Exception:
        pytest.skip("PostgreSQL not available")

    fragment, parent_path = _translate("Observation.value as Quantity", translator)

    assert fragment.expression.strip().upper().startswith("CASE WHEN")
    assert "valueQuantity" in fragment.expression
    assert parent_path == ["valueQuantity"]
