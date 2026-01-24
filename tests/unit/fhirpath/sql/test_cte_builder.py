"""Unit tests for the CTEBuilder class."""

from unittest.mock import Mock

import pytest

from fhir4ds.fhirpath.sql.cte import CTEBuilder
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.dialects.base import DatabaseDialect


def _build_builder() -> tuple[CTEBuilder, Mock]:
    """Create a builder instance with a mocked dialect."""
    dialect = Mock(spec=DatabaseDialect)
    builder = CTEBuilder(dialect=dialect)
    return builder, dialect


def test_cte_builder_initializes_with_dialect() -> None:
    builder, dialect = _build_builder()

    assert builder.cte_counter == 0
    assert builder.dialect is dialect


def test_build_cte_chain_creates_single_cte() -> None:
    builder, _ = _build_builder()
    fragment = SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="resource",
    )

    ctes = builder.build_cte_chain([fragment])

    assert len(ctes) == 1
    cte = ctes[0]
    assert cte.name == "cte_1"
    # Note: The query now includes the 'resource' column to propagate it through CTE chain
    assert cte.query == (
        "SELECT resource.id, resource, json_extract(resource, '$.name') AS result\n"
        "FROM resource"
    )
    assert cte.depends_on == []
    assert cte.requires_unnest is False
    assert cte.source_fragment is fragment


def test_build_cte_chain_chains_dependencies() -> None:
    builder, _ = _build_builder()

    first_fragment = SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="resource",
    )
    second_fragment = SQLFragment(
        expression="json_extract(cte_1, '$.family')",
        source_table="cte_1",
        dependencies=["cte_1"],
    )

    ctes = builder.build_cte_chain([first_fragment, second_fragment])

    assert len(ctes) == 2
    assert ctes[0].depends_on == []
    assert ctes[1].depends_on == ["cte_1"]
    assert ctes[1].name == "cte_2"


def test_wrap_simple_query_respects_existing_select() -> None:
    builder, _ = _build_builder()
    fragment = SQLFragment(
        expression="SELECT id, value FROM resource",
        source_table="resource",
    )

    result = builder._wrap_simple_query(fragment, "resource", [])

    assert result == "SELECT id, value FROM resource"


def test_fragment_metadata_copied_into_cte() -> None:
    builder, _ = _build_builder()
    fragment = SQLFragment(
        expression="json_extract(resource, '$.gender')",
        source_table="resource",
        metadata={"result_alias": "gender"},
    )

    cte = builder.build_cte_chain([fragment])[0]

    # Mutate original fragment metadata to ensure CTE keeps independent copy
    fragment.metadata["result_alias"] = "mutated"
    assert cte.metadata["result_alias"] == "gender"


def test_wrap_unnest_query_requires_array_column_metadata() -> None:
    builder, _ = _build_builder()
    fragment = SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="resource",
        requires_unnest=True,
    )

    with pytest.raises(ValueError, match="array_column"):
        builder._wrap_unnest_query(fragment, "resource", "cte_1", [])


def test_wrap_unnest_query_builds_select_with_dialect() -> None:
    builder, dialect = _build_builder()
    fragment = SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="resource",
        requires_unnest=True,
        metadata={
            "array_column": "json_extract(resource, '$.name')",
            "result_alias": "name_item",
            "id_column": "resource.id",
        },
    )

    dialect.prepare_unnest_source.return_value = "json_extract(resource, '$.name')"
    dialect.generate_lateral_unnest.return_value = (
        "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
    )

    sql, order_col = builder._wrap_unnest_query(fragment, "resource", "cte_1", [])

    # SP-020-DEBUG: Now includes ROW_NUMBER() ordering column with population-first PARTITION BY
    # SP-022-004: Uses PARTITION BY resource.id for population-first semantics
    assert "ROW_NUMBER() OVER (PARTITION BY resource.id)" in sql
    assert "cte_1_order" in sql
    assert order_col == "cte_1_order"
    assert "name_item" in sql  # Result column still present
    assert "FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item" in sql

    dialect.prepare_unnest_source.assert_called_once_with("json_extract(resource, '$.name')")
    dialect.generate_lateral_unnest.assert_called_once_with(
        "resource", "json_extract(resource, '$.name')", "name_item"
    )
