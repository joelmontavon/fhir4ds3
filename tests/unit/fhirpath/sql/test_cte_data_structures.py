"""Comprehensive unit tests for CTE data structures (task SP-011-004)."""

from __future__ import annotations

import json
import textwrap
from typing import Any, Callable, Dict, List, Sequence, Set, Tuple
from unittest.mock import Mock

import pytest

from fhir4ds.fhirpath.sql.cte import CTE, CTEAssembler, CTEBuilder
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.dialects.base import DatabaseDialect


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def extract_cte_definition_order(sql: str) -> List[str]:
    """Return the ordered list of CTE names based on WITH clause definitions."""
    names: List[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.endswith("AS (") and " AS (" in stripped:
            names.append(stripped.split(" AS ")[0])
    return names


def normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison by trimming trailing whitespace per line."""
    return "\n".join(line.rstrip() for line in sql.strip().splitlines())


def make_birthdate_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.birthDate extraction."""
    return [
        SQLFragment(
            expression="birth_date",
            source_table=table_name,
            metadata={"result_alias": "birth_date"},
        ),
    ]


def make_gender_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.gender extraction."""
    return [
        SQLFragment(
            expression="gender",
            source_table=table_name,
            metadata={"result_alias": "gender"},
        ),
    ]


def make_name_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.name array navigation."""
    return [
        SQLFragment(
            expression="name_arrays",
            source_table=table_name,
            metadata={"result_alias": "name_collection"},
        ),
        SQLFragment(
            expression="name_arrays",
            source_table=table_name,
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.name_collection",
                "result_alias": "name_entry",
                "id_column": "cte_1.id",
            },
        ),
    ]


def make_name_given_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.name.given navigation."""
    fragments = make_name_fragments(table_name)
    fragments.append(
        SQLFragment(
            expression="name_entry",
            source_table=table_name,
            requires_unnest=True,
            metadata={
                "array_column": "name_entry.unnest",
                "result_alias": "given_component",
                "id_column": "cte_2.id",
                "projection_expression": "given_component.unnest",
            },
        )
    )
    return fragments


def make_telecom_filtered_fragment() -> SQLFragment:
    """Fragment selecting telecom entries filtered by phone system."""
    return SQLFragment(
        expression=textwrap.dedent(
            """\
            SELECT cte_2.id,
                   telecom_entry.unnest
            FROM cte_2
            WHERE json_extract_string(telecom_entry.unnest, '$.system') = 'phone'
            """
        ),
        source_table="cte_2",
        dependencies=["cte_2"],
    )


def make_address_line_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.address.line navigation."""
    return [
        SQLFragment(
            expression="address_lines",
            source_table=table_name,
            metadata={"result_alias": "address_collection"},
        ),
        SQLFragment(
            expression="address_lines",
            source_table=table_name,
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.address_collection",
                "result_alias": "address_entry",
                "id_column": "cte_1.id",
            },
        ),
        SQLFragment(
            expression="address_entry",
            source_table=table_name,
            requires_unnest=True,
            metadata={
                "array_column": "address_entry.unnest",
                "result_alias": "address_line",
                "id_column": "cte_2.id",
                "projection_expression": "address_line.unnest",
            },
        ),
    ]


def make_telecom_fragments(table_name: str) -> List[SQLFragment]:
    """Create fragments emulating Patient.telecom navigation."""
    return [
        SQLFragment(
            expression="telecom_entries",
            source_table=table_name,
            metadata={"result_alias": "telecom_collection"},
        ),
        SQLFragment(
            expression="telecom_entries",
            source_table=table_name,
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.telecom_collection",
                "result_alias": "telecom_entry",
                "id_column": "cte_1.id",
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_dialect() -> Mock:
    """Provide a mock dialect implementing the DatabaseDialect interface."""
    return Mock(spec=DatabaseDialect)


@pytest.fixture
def builder(mock_dialect: Mock) -> CTEBuilder:
    """Create a CTEBuilder using the mock dialect for unit testing."""
    return CTEBuilder(dialect=mock_dialect)


@pytest.fixture
def simple_fragment() -> SQLFragment:
    """Return a simple SQLFragment used by multiple tests."""
    return SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="resource",
        metadata={"result_alias": "name_value"},
    )


@pytest.fixture
def unnest_fragment() -> SQLFragment:
    """Provide a SQLFragment configured for UNNEST testing."""
    return SQLFragment(
        expression="json_extract(resource, '$.name')",
        source_table="patient_resources",
        requires_unnest=True,
        metadata={
            "array_column": "json_extract(resource, '$.name')",
            "result_alias": "name_item",
            "id_column": "patient_resources.id",
        },
    )


@pytest.fixture(scope="session")
def duckdb_dialect() -> Any:
    """Create a DuckDB dialect backed by an in-memory database for execution tests."""
    pytest.importorskip("duckdb")
    from fhir4ds.dialects.duckdb import DuckDBDialect
    try:
        dialect = DuckDBDialect()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"DuckDBDialect unavailable in test environment: {exc}")
    yield dialect
    connection = dialect.get_connection()
    connection.close()


@pytest.fixture
def duckdb_builder(duckdb_dialect: Any) -> CTEBuilder:
    """Create a CTEBuilder backed by the real DuckDB dialect."""
    return CTEBuilder(dialect=duckdb_dialect)


@pytest.fixture
def postgresql_dialect(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, List[str]]:
    """Create a PostgreSQL dialect with a fake connection capturing executed SQL."""
    pytest.importorskip("psycopg2")
    from fhir4ds.dialects import postgresql as postgres_module

    executed_sql: List[str] = []

    class FakeCursor:
        def __init__(self, store: List[str]) -> None:
            self._store = store
            self.description = None  # Standard DB-API 2.0 cursor attribute

        def execute(self, sql: str) -> None:
            self._store.append(sql)

        def fetchall(self) -> List[Any]:
            return []

        def close(self) -> None:
            return None

    class FakeConnection:
        def __init__(self) -> None:
            self.autocommit = False

        def cursor(self) -> FakeCursor:
            return FakeCursor(executed_sql)

    def fake_connect(connection_string: str) -> FakeConnection:  # noqa: ARG001
        return FakeConnection()

    monkeypatch.setattr(postgres_module.psycopg2, "connect", fake_connect)
    dialect = postgres_module.PostgreSQLDialect(
        "dbname=test user=test password=test host=localhost"
    )
    return dialect, executed_sql


@pytest.fixture
def postgresql_builder(postgresql_dialect: tuple[Any, List[str]]) -> tuple[CTEBuilder, List[str]]:
    """Create a CTEBuilder backed by the PostgreSQL dialect and capture SQL executions."""
    dialect, executed_sql = postgresql_dialect
    return CTEBuilder(dialect=dialect), executed_sql


@pytest.fixture
def duckdb_assembler(duckdb_dialect: Any) -> CTEAssembler:
    """Provide a CTEAssembler backed by the DuckDB dialect."""
    return CTEAssembler(dialect=duckdb_dialect)


@pytest.fixture
def postgresql_assembler(
    postgresql_dialect: tuple[Any, List[str]],
) -> Tuple[CTEAssembler, List[str]]:
    """Provide a PostgreSQL assembler and capture buffer for executed SQL."""
    dialect, executed_sql = postgresql_dialect
    return CTEAssembler(dialect=dialect), executed_sql


@pytest.fixture
def duckdb_patient_resources(duckdb_dialect: Any) -> str:
    """Populate an in-memory DuckDB table with Patient resources for integration tests."""
    connection = duckdb_dialect.get_connection()
    table_name = "patient_resources_phase3"
    connection.execute(f"DROP TABLE IF EXISTS {table_name}")
    connection.execute(
        f"""
        CREATE TABLE {table_name} (
            id INTEGER,
            resource JSON,
            birth_date VARCHAR,
            gender VARCHAR,
            name_arrays VARCHAR[][],
            address_lines VARCHAR[][],
            telecom_entries STRUCT(system VARCHAR, value VARCHAR)[]
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO {table_name} VALUES
            (
                1,
                json '{{
                    "resourceType": "Patient",
                    "id": "1",
                    "birthDate": "1980-01-01",
                    "name": [
                        {{"use": "official", "given": ["Alice", "Ann"], "family": "Doe"}},
                        {{"use": "nickname", "given": ["Allie"], "family": "Doe"}}
                    ],
                    "telecom": [
                        {{"system": "phone", "value": "555-1000"}},
                        {{"system": "email", "value": "alice@example.com"}}
                    ],
                    "address": [
                        {{
                            "line": ["123 Main St", "Apt 1"],
                            "city": "Metropolis"
                        }}
                    ],
                    "gender": "female"
                }}',
                '1980-01-01',
                'female',
                [['Alice', 'Ann'], ['Allie']],
                [['123 Main St', 'Apt 1']],
                [
                    STRUCT_PACK(system := 'phone', value := '555-1000'),
                    STRUCT_PACK(system := 'email', value := 'alice@example.com')
                ]
            ),
            (
                2,
                json '{{
                    "resourceType": "Patient",
                    "id": "2",
                    "birthDate": "1975-05-20",
                    "name": [
                        {{"use": "official", "given": ["Bob"], "family": "Smith"}}
                    ],
                    "telecom": [
                        {{"system": "email", "value": "bob@example.com"}}
                    ],
                    "address": [
                        {{
                            "line": ["500 Elm St"],
                            "city": "Gotham"
                        }}
                    ],
                    "gender": "male"
                }}',
                '1975-05-20',
                'male',
                [['Bob']],
                [['500 Elm St']],
                [
                    STRUCT_PACK(system := 'email', value := 'bob@example.com')
                ]
            ),
            (
                3,
                json '{{
                    "resourceType": "Patient",
                    "id": "3",
                    "birthDate": "1990-07-15",
                    "name": [
                        {{"use": "official", "given": ["Cara"], "family": "Jones"}},
                        {{"use": "nickname", "given": ["CJ"], "family": "Jones"}}
                    ],
                    "telecom": [
                        {{"system": "phone", "value": "555-2000"}}
                    ],
                    "address": [
                        {{
                            "line": ["742 Evergreen Terrace"],
                            "city": "Springfield"
                        }}
                    ],
                    "gender": "female"
                }}',
                '1990-07-15',
                'female',
                [['Cara'], ['CJ']],
                [['742 Evergreen Terrace']],
                [
                    STRUCT_PACK(system := 'phone', value := '555-2000')
                ]
            )
        """
    )
    yield table_name
    connection.execute(f"DROP TABLE IF EXISTS {table_name}")


@pytest.fixture
def complex_cte_chain() -> List[CTE]:
    """Return a representative dependency chain of CTEs for integration testing."""
    return [
        CTE(name="cte_seed", query="SELECT 1 AS id"),
        CTE(
            name="cte_filter",
            query="SELECT id FROM cte_seed WHERE id > 0",
            depends_on=["cte_seed"],
        ),
        CTE(
            name="cte_projection",
            query="SELECT id FROM cte_filter",
            depends_on=["cte_filter"],
        ),
    ]


@pytest.fixture
def branching_cte_chain() -> List[CTE]:
    """Return a branching dependency graph for ordering validations."""
    return [
        CTE(name="cte_root_a", query="SELECT 1 AS id"),
        CTE(name="cte_root_b", query="SELECT 2 AS id"),
        CTE(
            name="cte_join",
            query="SELECT cte_root_a.id + cte_root_b.id AS total FROM cte_root_a JOIN cte_root_b",
            depends_on=["cte_root_a", "cte_root_b"],
        ),
        CTE(
            name="cte_final",
            query="SELECT total FROM cte_join",
            depends_on=["cte_join"],
        ),
    ]



# ---------------------------------------------------------------------------
# CTE Dataclass Tests
# ---------------------------------------------------------------------------


class TestCTEDataclass:
    """Validate behavior and edge cases for the CTE dataclass."""

    def test_basic_creation_populates_defaults(self) -> None:
        """CTE stores provided name and query with empty defaults."""
        cte = CTE(name="cte_1", query="SELECT 1")
        assert cte.name == "cte_1"
        assert cte.query == "SELECT 1"
        assert cte.depends_on == []
        assert cte.requires_unnest is False
        assert cte.metadata == {}

    def test_all_fields_preserved(self, simple_fragment: SQLFragment) -> None:
        """CTE preserves optional fields when provided."""
        cte = CTE(
            name="cte_alpha",
            query="SELECT * FROM resource",
            depends_on=["cte_base"],
            requires_unnest=True,
            source_fragment=simple_fragment,
            metadata={"rows": 5},
        )
        assert cte.depends_on == ["cte_base"]
        assert cte.requires_unnest is True
        assert cte.source_fragment is simple_fragment
        assert cte.metadata["rows"] == 5

    def test_depends_on_default_isolated_between_instances(self) -> None:
        """Default depends_on lists remain isolated per instance."""
        first = CTE(name="cte_1", query="SELECT 1")
        second = CTE(name="cte_2", query="SELECT 1")
        first.depends_on.append("cte_0")
        assert second.depends_on == []

    def test_metadata_default_isolated_between_instances(self) -> None:
        """Default metadata dictionaries should not be shared."""
        first = CTE(name="cte_1", query="SELECT 1")
        second = CTE(name="cte_2", query="SELECT 1")
        first.metadata["note"] = "first"
        assert "note" not in second.metadata

    def test_add_dependency_appends_new_value(self) -> None:
        """add_dependency appends unseen dependency names."""
        cte = CTE(name="cte_1", query="SELECT 1")
        cte.add_dependency("cte_parent")
        assert cte.depends_on == ["cte_parent"]

    def test_add_dependency_ignores_duplicates(self) -> None:
        """add_dependency avoids inserting duplicates."""
        cte = CTE(name="cte_1", query="SELECT 1", depends_on=["cte_parent"])
        cte.add_dependency("cte_parent")
        assert cte.depends_on == ["cte_parent"]

    def test_set_metadata_stores_value(self) -> None:
        """set_metadata inserts key-value pairs."""
        cte = CTE(name="cte_1", query="SELECT 1")
        cte.set_metadata("rows", 100)
        assert cte.metadata["rows"] == 100

    def test_get_metadata_returns_default_when_missing(self) -> None:
        """get_metadata returns fallback when key absent."""
        cte = CTE(name="cte_1", query="SELECT 1")
        assert cte.get_metadata("missing", "fallback") == "fallback"

    def test_requires_unnest_default_false(self) -> None:
        """requires_unnest defaults to False."""
        cte = CTE(name="cte_1", query="SELECT 1")
        assert cte.requires_unnest is False

    def test_requires_unnest_true_when_set(self) -> None:
        """requires_unnest stores provided boolean."""
        cte = CTE(name="cte_1", query="SELECT 1", requires_unnest=True)
        assert cte.requires_unnest is True

    def test_source_fragment_optional(self, simple_fragment: SQLFragment) -> None:
        """source_fragment retains reference for debugging."""
        cte = CTE(name="cte_1", query="SELECT 1", source_fragment=simple_fragment)
        assert cte.source_fragment is simple_fragment

    def test_depends_on_preserves_order(self) -> None:
        """Dependencies maintain insertion order."""
        cte = CTE(name="cte_1", query="SELECT 1", depends_on=["a"])
        cte.add_dependency("b")
        assert cte.depends_on == ["a", "b"]

    @pytest.mark.parametrize("value", [42, "text", None, 3.14, {"nested": True}])
    def test_metadata_accepts_various_types(self, value: Any) -> None:
        """Metadata accepts a range of Python values."""
        cte = CTE(name="cte_1", query="SELECT 1")
        cte.set_metadata("value", value)
        assert cte.get_metadata("value") is value

    @pytest.mark.parametrize("invalid_name", ["", "invalid-name", "123*abc"])
    def test_invalid_name_raises_value_error(self, invalid_name: str) -> None:
        """Invalid CTE names raise ValueError."""
        with pytest.raises(ValueError):
            CTE(name=invalid_name, query="SELECT 1")

    def test_empty_query_raises_value_error(self) -> None:
        """Empty query strings are rejected."""
        with pytest.raises(ValueError):
            CTE(name="cte_1", query="")

    def test_depends_on_must_be_list(self) -> None:
        """Non-list depends_on raises ValueError."""
        with pytest.raises(ValueError):
            CTE(name="cte_1", query="SELECT 1", depends_on="cte_parent")  # type: ignore[arg-type]

    def test_metadata_must_be_dict(self) -> None:
        """Non-dict metadata raises ValueError."""
        with pytest.raises(ValueError):
            CTE(name="cte_1", query="SELECT 1", metadata=["not", "dict"])  # type: ignore[arg-type]

    def test_name_must_be_string(self) -> None:
        """Non-string name triggers validation error."""
        with pytest.raises(ValueError):
            CTE(name=123, query="SELECT 1")  # type: ignore[arg-type]

    def test_query_must_be_string(self) -> None:
        """Non-string query triggers validation error."""
        with pytest.raises(ValueError):
            CTE(name="cte_1", query=123)  # type: ignore[arg-type]

    def test_repr_contains_name_and_query(self) -> None:
        """repr includes both name and query snippet."""
        cte = CTE(name="cte_1", query="SELECT 1")
        representation = repr(cte)
        assert "cte_1" in representation
        assert "SELECT 1" in representation

    def test_metadata_can_be_updated(self) -> None:
        """Metadata updates reflect latest values."""
        cte = CTE(name="cte_1", query="SELECT 1")
        cte.set_metadata("rows", 10)
        cte.set_metadata("rows", 20)
        assert cte.get_metadata("rows") == 20

    def test_depends_on_allows_empty_append(self) -> None:
        """Adding empty dependency is ignored downstream but stored."""
        cte = CTE(name="cte_1", query="SELECT 1")
        cte.add_dependency("")
        assert cte.depends_on == [""]


# ---------------------------------------------------------------------------
# CTEBuilder Tests
# ---------------------------------------------------------------------------


class TestCTEBuilder:
    """Exercise CTEBuilder behaviors and edge cases."""

    def test_initializes_with_dialect(self, mock_dialect: Mock) -> None:
        """Builder stores dialect and initializes counter to zero."""
        builder = CTEBuilder(dialect=mock_dialect)
        assert builder.dialect is mock_dialect
        assert builder.cte_counter == 0

    def test_requires_dialect_instance(self) -> None:
        """Passing None for dialect raises ValueError."""
        with pytest.raises(ValueError):
            CTEBuilder(dialect=None)  # type: ignore[arg-type]

    def test_build_cte_chain_empty_list_returns_empty(self, builder: CTEBuilder) -> None:
        """Empty fragment list produces no CTEs."""
        assert builder.build_cte_chain([]) == []

    def test_build_cte_chain_single_fragment(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """Single fragment generates a CTE with expected query."""
        ctes = builder.build_cte_chain([simple_fragment])
        assert len(ctes) == 1
        cte = ctes[0]
        assert cte.name == "cte_1"
        assert "json_extract(resource, '$.name')" in cte.query
        assert "AS name_value" in cte.query
        assert cte.depends_on == []
        assert cte.source_fragment is simple_fragment

    def test_build_cte_chain_increments_counter(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """CTE counter increments for each generated CTE."""
        fragments = [simple_fragment]*3
        ctes = builder.build_cte_chain(fragments)
        assert [cte.name for cte in ctes] == ["cte_1", "cte_2", "cte_3"]
        assert builder.cte_counter == 3

    def test_generate_cte_name_is_unique(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """Generated CTE names are sequentially unique."""
        names = {builder._generate_cte_name(simple_fragment) for _ in range(4)}
        assert names == {"cte_1", "cte_2", "cte_3", "cte_4"}

    def test_wrap_simple_query_returns_existing_select(self, builder: CTEBuilder) -> None:
        """Existing SELECT statements are passed through unchanged."""
        fragment = SQLFragment(
            expression="SELECT id, value FROM resource",
            source_table="resource",
        )
        assert builder._wrap_simple_query(fragment, "resource", []) == "SELECT id, value FROM resource"

    def test_wrap_simple_query_uses_metadata_alias(self, builder: CTEBuilder) -> None:
        """Metadata result_alias controls projected column alias."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.gender')",
            source_table="resource",
            metadata={"result_alias": "gender"},
        )
        sql = builder._wrap_simple_query(fragment, "resource", [])
        assert "AS gender" in sql

    def test_wrap_simple_query_uses_custom_id_column(self, builder: CTEBuilder) -> None:
        """Metadata id_column overrides id projection."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.birthDate')",
            source_table="resource",
            metadata={"id_column": "resource.resource_id"},
        )
        sql = builder._wrap_simple_query(fragment, "resource", [])
        assert "resource.resource_id" in sql and "ROW_NUMBER()" in sql

    def test_wrap_simple_query_raises_on_blank_expression(self, builder: CTEBuilder) -> None:
        """Blank fragment expressions are rejected."""
        fragment = SQLFragment(expression="   ", source_table="resource")
        with pytest.raises(ValueError):
            builder._wrap_simple_query(fragment, "resource", [])

    def test_fragment_to_cte_requires_source_table_or_previous_cte(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """Missing source table with no previous CTE raises ValueError."""
        simple_fragment.source_table = ""
        with pytest.raises(ValueError):
            builder._fragment_to_cte(simple_fragment, previous_cte=None)

    def test_fragment_to_cte_uses_previous_cte_as_source(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """Previous CTE name becomes source table when provided."""
        simple_fragment.metadata["result_alias"] = "alias"
        cte = builder._fragment_to_cte(simple_fragment, previous_cte="cte_prev")
        assert "FROM cte_prev" in cte.query
        assert cte.depends_on == ["cte_prev"]

    def test_fragment_to_cte_combines_dependencies_without_duplicates(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """Dependencies merge previous CTE and fragment dependencies without duplication."""
        simple_fragment.dependencies = ["cte_prev", "cte_other"]
        cte = builder._fragment_to_cte(simple_fragment, previous_cte="cte_prev")
        assert cte.depends_on == ["cte_prev", "cte_other"]

    def test_fragment_to_cte_copies_metadata(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """CTE metadata is a shallow copy to avoid mutation from fragments."""
        simple_fragment.metadata["result_alias"] = "alias"
        cte = builder._fragment_to_cte(simple_fragment, previous_cte=None)
        simple_fragment.metadata["result_alias"] = "changed"
        assert cte.metadata["result_alias"] == "alias"

    def test_fragment_to_cte_preserves_source_fragment(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """CTE retains reference to originating SQLFragment."""
        cte = builder._fragment_to_cte(simple_fragment, previous_cte=None)
        assert cte.source_fragment is simple_fragment

    def test_fragment_to_cte_sets_requires_unnest_flag(self, builder: CTEBuilder, unnest_fragment: SQLFragment) -> None:
        """requires_unnest flag passes through from fragment and generates UNNEST query."""
        builder.dialect.prepare_unnest_source.return_value = "json_extract(resource, '$.name')"
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
        )
        cte = builder._fragment_to_cte(unnest_fragment, previous_cte=None)
        builder.dialect.prepare_unnest_source.assert_called_once_with("json_extract(resource, '$.name')")
        builder.dialect.generate_lateral_unnest.assert_called_once_with(
            "patient_resources", "json_extract(resource, '$.name')", "name_item"
        )
        assert cte.requires_unnest is True
        assert "LATERAL UNNEST" in cte.query
        assert "patient_resources.id" in cte.query

    def test_build_cte_chain_preserves_dependency_order(self, builder: CTEBuilder) -> None:
        """Dependency ordering remains stable in generated CTEs."""
        fragments = [
            SQLFragment(
                expression="json_extract(resource, '$.name')",
                source_table="resource",
            ),
            SQLFragment(
                expression="json_extract(cte_1, '$.given')",
                source_table="cte_1",
                dependencies=["cte_external", "cte_1"],
            ),
        ]
        ctes = builder.build_cte_chain(fragments)
        assert ctes[1].depends_on == ["cte_1", "cte_external"]

    def test_build_cte_chain_returns_requires_unnest_flag(self, builder: CTEBuilder, unnest_fragment: SQLFragment) -> None:
        """CTE requires_unnest flag mirrors fragment property and produces populated query."""
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
        )
        ctes = builder.build_cte_chain([unnest_fragment])
        assert len(ctes) == 1
        assert ctes[0].requires_unnest is True
        assert "LATERAL UNNEST" in ctes[0].query

    def test_build_cte_chain_keeps_newline_formatting(self, builder: CTEBuilder) -> None:
        """Multiline expressions are formatted inside generated query."""
        fragment = SQLFragment(
            expression="\n    json_extract(resource, '$.name')\n",
            source_table="resource",
        )
        sql = builder._wrap_simple_query(fragment, "resource", [])
        assert sql.startswith("SELECT")
        assert "json_extract" in sql

    def test_wrap_simple_query_strips_expression_whitespace(self, builder: CTEBuilder) -> None:
        """Leading/trailing whitespace is removed from expressions before wrapping."""
        fragment = SQLFragment(
            expression="  json_extract(resource, '$.active')  ",
            source_table="resource",
        )
        sql = builder._wrap_simple_query(fragment, "resource", [])
        assert "json_extract(resource, '$.active')" in sql

    def test_build_cte_chain_metadata_independence(self, builder: CTEBuilder, simple_fragment: SQLFragment) -> None:
        """CTE metadata remains unchanged if fragment metadata mutates post-build."""
        ctes = builder.build_cte_chain([simple_fragment])
        simple_fragment.metadata["result_alias"] = "mutated"
        assert ctes[0].metadata["result_alias"] == "name_value"

    def test_build_cte_chain_previous_cte_overrides_fragment_source(self, builder: CTEBuilder) -> None:
        """Previous CTE name takes precedence over fragment source table."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.birthDate')",
            source_table="resource",
        )
        cte = builder._fragment_to_cte(fragment, previous_cte="cte_parent")
        assert "FROM cte_parent" in cte.query

    def test_wrap_unnest_query_requires_metadata(self, builder: CTEBuilder) -> None:
        """UNNEST wrapping enforces presence of array metadata."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="resource",
            requires_unnest=True,
        )
        with pytest.raises(ValueError, match="array_column"):
            builder._wrap_unnest_query(fragment, "resource", "cte_1", [])


# ---------------------------------------------------------------------------
# CTEBuilder UNNEST Tests (Phase 2)
# ---------------------------------------------------------------------------


class TestCTEBuilderUnnest:
    """Dedicated UNNEST coverage for CTEBuilder Phase 2 functionality."""

    def test_wrap_unnest_query_basic(self, builder: CTEBuilder, unnest_fragment: SQLFragment) -> None:
        """Basic UNNEST wrapping preserves id column and adds LATERAL clause."""
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
        )
        sql, order_col = builder._wrap_unnest_query(unnest_fragment, "patient_resources", "cte_1", [])
        assert "SELECT patient_resources.id" in sql and "name_item" in sql and "ROW_NUMBER() OVER ()" in sql
        assert "FROM patient_resources, LATERAL UNNEST" in sql

    def test_wrap_unnest_query_uses_custom_result_alias(self, builder: CTEBuilder) -> None:
        """Custom result_alias flows into SELECT projection and dialect call."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_entry",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_entry"
        )
        sql, order_col = builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])
        builder.dialect.generate_lateral_unnest.assert_called_once()
        assert "name_entry" in sql.splitlines()[0]

    @pytest.mark.parametrize(
        ("metadata", "expected_alias"),
        [
            ({"array_column": "json_extract(resource, '$.name')"}, "item"),
            ({"array_column": "json_extract(resource, '$.name')", "result_alias": None}, "item"),
            ({"array_column": "json_extract(resource, '$.name')", "result_alias": ""}, "item"),
        ],
    )
    def test_wrap_unnest_query_default_alias(
        self,
        builder: CTEBuilder,
        metadata: dict[str, Any],
        expected_alias: str,
    ) -> None:
        """Default alias falls back to 'item' when not provided."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata=metadata,
        )

        def _side_effect(source: str, array_col: str, alias: str) -> str:
            return f"LATERAL UNNEST({array_col}) AS {alias}"

        builder.dialect.generate_lateral_unnest.side_effect = _side_effect
        sql, order_col = builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])
        assert builder.dialect.generate_lateral_unnest.call_args[0][2] == expected_alias
        assert f" AS {expected_alias}" in sql

    @pytest.mark.parametrize("source_table", ["patient_resources", "cte_42"])
    def test_wrap_unnest_query_default_id_column(self, builder: CTEBuilder, source_table: str) -> None:
        """Default id column uses the provided source table identifier."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table=source_table,
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            f"LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
        )
        sql, order_col = builder._wrap_unnest_query(fragment, source_table, "cte_1", [])
        assert f"SELECT {source_table}.id, name_item" in sql

    def test_wrap_unnest_query_custom_id_column(self, builder: CTEBuilder) -> None:
        """Custom id_column metadata overrides default identifier selection."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="cte_base",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_row",
                "id_column": "cte_base.patient_identifier",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_row"
        )
        sql, order_col = builder._wrap_unnest_query(fragment, "cte_base", "cte_1", [])
        assert "SELECT cte_base.patient_identifier, name_row" in sql

    def test_wrap_unnest_query_projection_expression(self, builder: CTEBuilder) -> None:
        """projection_expression metadata replaces default projection column."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
                "projection_expression": "json_extract_scalar(name_item, '$.given[0]')",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item"
        )
        sql, order_col = builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])
        assert "json_extract_scalar(name_item, '$.given[0]')" in sql

    def test_wrap_unnest_query_trimmed_metadata(self, builder: CTEBuilder) -> None:
        """Whitespace in metadata is trimmed before SQL generation."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "  json_extract(resource, '$.name')  ",
                "result_alias": "  names  ",
                "id_column": "  patient_resources.identifier  ",
                "projection_expression": "  json_extract_scalar(names, '$.family')  ",
            },
        )

        def _side_effect(source: str, array_col: str, alias: str) -> str:
            return f"LATERAL UNNEST({array_col}) AS {alias}"

        builder.dialect.prepare_unnest_source.side_effect = lambda expr: expr.strip()
        builder.dialect.generate_lateral_unnest.side_effect = _side_effect
        sql, order_col = builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])
        call_args = builder.dialect.generate_lateral_unnest.call_args[0]
        assert call_args == (
            "patient_resources",
            "json_extract(resource, '$.name')",
            "names",
        )
        assert "SELECT patient_resources.identifier, json_extract_scalar(names, '$.family')" in sql

    def test_wrap_unnest_query_blank_alias_raises(self, builder: CTEBuilder) -> None:
        """Empty result_alias values trigger validation errors."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "   ",
            },
        )
        with pytest.raises(ValueError, match="result_alias"):
            builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])

    def test_wrap_unnest_query_blank_id_column_raises(self, builder: CTEBuilder) -> None:
        """Empty id_column metadata raises ValueError for clarity."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
                "id_column": "   ",
            },
        )
        with pytest.raises(ValueError, match="id_column"):
            builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])

    def test_wrap_unnest_query_missing_dialect_method_raises(
        self,
        builder: CTEBuilder,
        unnest_fragment: SQLFragment,
    ) -> None:
        """Missing dialect.generate_lateral_unnest raises AttributeError."""
        builder.dialect.generate_lateral_unnest = None  # type: ignore[assignment]
        with pytest.raises(AttributeError, match="generate_lateral_unnest"):
            builder._wrap_unnest_query(unnest_fragment, "patient_resources", "cte_1", [])

    def test_wrap_unnest_query_returns_expression_when_full_select(self, builder: CTEBuilder) -> None:
        """Existing SELECT expressions bypass UNNEST wrapping."""
        fragment = SQLFragment(
            expression="SELECT id, array_item FROM patient_view",
            source_table="patient_view",
            requires_unnest=True,
        )
        sql, order_col = builder._wrap_unnest_query(fragment, "patient_view", "cte_1", [])
        assert sql == "SELECT id, array_item FROM patient_view"
        builder.dialect.generate_lateral_unnest.assert_not_called()

    def test_wrap_unnest_query_rejects_blank_source_table(
        self,
        builder: CTEBuilder,
        unnest_fragment: SQLFragment,
    ) -> None:
        """Blank source tables are rejected early."""
        with pytest.raises(ValueError, match="source_table must be"):
            builder._wrap_unnest_query(unnest_fragment, "   ", "cte_1", [])

    def test_fragment_to_cte_with_previous_dependency(self, builder: CTEBuilder) -> None:
        """Previous CTE names flow into dependency list for UNNEST fragments."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.telecom')",
            source_table="cte_parent",
            requires_unnest=True,
            dependencies=["cte_aux"],
            metadata={
                "array_column": "json_extract(resource, '$.telecom')",
                "result_alias": "telecom_item",
                "id_column": "cte_parent.id",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.telecom')) AS telecom_item"
        )
        cte = builder._fragment_to_cte(fragment, previous_cte="cte_prev")
        assert cte.depends_on == ["cte_prev", "cte_aux"]

    def test_fragment_to_cte_unnest_merges_dependencies(self, builder: CTEBuilder) -> None:
        """Duplicate dependencies are removed while preserving order."""
        fragment = SQLFragment(
            expression="json_extract(resource, '$.telecom')",
            source_table="cte_parent",
            requires_unnest=True,
            dependencies=["cte_prev", "cte_other"],
            metadata={
                "array_column": "json_extract(resource, '$.telecom')",
                "result_alias": "telecom_item",
                "id_column": "cte_parent.id",
            },
        )
        builder.dialect.generate_lateral_unnest.return_value = (
            "LATERAL UNNEST(json_extract(resource, '$.telecom')) AS telecom_item"
        )
        cte = builder._fragment_to_cte(fragment, previous_cte="cte_prev")
        assert cte.depends_on == ["cte_prev", "cte_other"]

    def test_build_cte_chain_mixed_simple_and_unnest(self, builder: CTEBuilder) -> None:
        """Mixed fragment chains produce sequential CTEs with proper dependencies."""
        simple = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            metadata={"result_alias": "name_value"},
        )
        unnest_fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.name_value",
                "result_alias": "name_item",
                "id_column": "cte_1.id",
            },
        )

        def _side_effect(source: str, array_col: str, alias: str) -> str:
            return f"LATERAL UNNEST({array_col}) AS {alias}"

        builder.dialect.prepare_unnest_source.side_effect = lambda expr: expr
        builder.dialect.generate_lateral_unnest.side_effect = _side_effect
        ctes = builder.build_cte_chain([simple, unnest_fragment])
        assert [cte.name for cte in ctes] == ["cte_1", "cte_2"]
        assert ctes[1].depends_on == ["cte_1"]
        assert "FROM cte_1, LATERAL UNNEST(cte_1.name_value)" in ctes[1].query
        assert builder.dialect.generate_lateral_unnest.call_args[0][0] == "cte_1"


# ---------------------------------------------------------------------------
# CTEAssembler Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblerOrdering:
    """Focused tests for dependency ordering logic."""

    def test_returns_copy(self, mock_dialect: Mock) -> None:
        """Ordering creates a new list without mutating input."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [CTE(name="cte_seed", query="SELECT 1")]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert ordered == ctes
        assert ordered is not ctes

    def test_topologically_sorts_out_of_order_input(self, mock_dialect: Mock) -> None:
        """Out-of-order dependency chain is sorted correctly."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_3", query="SELECT * FROM cte_2", depends_on=["cte_2"]),
            CTE(name="cte_1", query="SELECT 1"),
            CTE(name="cte_2", query="SELECT * FROM cte_1", depends_on=["cte_1"]),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == ["cte_1", "cte_2", "cte_3"]

    def test_branching_dependencies_preserve_input_order(self, mock_dialect: Mock) -> None:
        """Independent roots maintain their relative order."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_secondary", query="SELECT 2"),
            CTE(name="cte_seed", query="SELECT 1"),
            CTE(
                name="cte_join",
                query="SELECT * FROM cte_seed JOIN cte_secondary",
                depends_on=["cte_seed", "cte_secondary"],
            ),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == [
            "cte_secondary",
            "cte_seed",
            "cte_join",
        ]

    def test_preserves_input_order_for_independent_ctes(self, mock_dialect: Mock) -> None:
        """Multiple independent CTEs stay in the same order."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a", query="SELECT 1"),
            CTE(name="cte_b", query="SELECT 2"),
            CTE(name="cte_c", query="SELECT 3"),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == ["cte_a", "cte_b", "cte_c"]

    def test_preserves_order_when_multiple_dependents_ready(self, mock_dialect: Mock) -> None:
        """Dependents released simultaneously respect original ordering."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_seed", query="SELECT 1"),
            CTE(name="cte_dep_beta", query="SELECT * FROM cte_seed", depends_on=["cte_seed"]),
            CTE(name="cte_dep_alpha", query="SELECT * FROM cte_seed", depends_on=["cte_seed"]),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == [
            "cte_seed",
            "cte_dep_beta",
            "cte_dep_alpha",
        ]

    def test_detects_missing_dependency(self, mock_dialect: Mock) -> None:
        """Missing dependency raises descriptive error."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_valid", query="SELECT 1"),
            CTE(name="cte_missing", query="SELECT * FROM missing_cte", depends_on=["missing_cte"]),
        ]
        with pytest.raises(ValueError, match=r"Missing CTE dependencies: missing_cte"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_detects_multiple_missing_dependencies(self, mock_dialect: Mock) -> None:
        """Multiple missing dependencies listed in order encountered."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_first", query="SELECT * FROM missing_a", depends_on=["missing_a"]),
            CTE(name="cte_second", query="SELECT * FROM missing_b", depends_on=["missing_b"]),
        ]
        with pytest.raises(ValueError, match=r"Missing CTE dependencies: missing_a, missing_b"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_detects_cycle_between_two_ctes(self, mock_dialect: Mock) -> None:
        """Two-node cycle is detected with clear path."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a", query="SELECT * FROM cte_b", depends_on=["cte_b"]),
            CTE(name="cte_b", query="SELECT * FROM cte_a", depends_on=["cte_a"]),
        ]
        with pytest.raises(ValueError, match=r"cte_a -> cte_b -> cte_a"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_detects_cycle_with_three_ctes_reports_path(self, mock_dialect: Mock) -> None:
        """Multi-node cycles provide the dependency path."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_alpha", query="SELECT * FROM cte_gamma", depends_on=["cte_gamma"]),
            CTE(name="cte_beta", query="SELECT * FROM cte_alpha", depends_on=["cte_alpha"]),
            CTE(name="cte_gamma", query="SELECT * FROM cte_beta", depends_on=["cte_beta"]),
        ]
        with pytest.raises(ValueError, match=r"cte_alpha -> cte_gamma -> cte_beta -> cte_alpha"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_detects_self_dependency_cycle(self, mock_dialect: Mock) -> None:
        """Self-referential dependency triggers cycle detection."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_self", query="SELECT * FROM cte_self", depends_on=["cte_self"]),
        ]
        with pytest.raises(ValueError, match=r"cte_self -> cte_self"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_handles_duplicate_dependencies_without_double_counting(self, mock_dialect: Mock) -> None:
        """Duplicate dependency entries are ignored for ordering."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_seed", query="SELECT 1"),
            CTE(
                name="cte_duplicate",
                query="SELECT * FROM cte_seed",
                depends_on=["cte_seed", "cte_seed"],
            ),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == ["cte_seed", "cte_duplicate"]

    def test_detects_duplicate_cte_names(self, mock_dialect: Mock) -> None:
        """Duplicate CTE names are rejected immediately."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_dup", query="SELECT 1"),
            CTE(name="cte_dup", query="SELECT 2"),
        ]
        with pytest.raises(ValueError, match=r"Duplicate CTE name detected: cte_dup"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_handles_long_dependency_chain(self, mock_dialect: Mock) -> None:
        """Long chains are topologically ordered."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_5", query="SELECT * FROM cte_4", depends_on=["cte_4"]),
            CTE(name="cte_1", query="SELECT 1"),
            CTE(name="cte_3", query="SELECT * FROM cte_2", depends_on=["cte_2"]),
            CTE(name="cte_4", query="SELECT * FROM cte_3", depends_on=["cte_3"]),
            CTE(name="cte_2", query="SELECT * FROM cte_1", depends_on=["cte_1"]),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == [
            "cte_1",
            "cte_2",
            "cte_3",
            "cte_4",
            "cte_5",
        ]

    def test_handles_disconnected_components(self, mock_dialect: Mock) -> None:
        """Disjoint dependency subgraphs each retain internal ordering."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a_root", query="SELECT 1"),
            CTE(name="cte_b_root", query="SELECT 1"),
            CTE(name="cte_a_leaf", query="SELECT * FROM cte_a_root", depends_on=["cte_a_root"]),
            CTE(name="cte_b_leaf", query="SELECT * FROM cte_b_root", depends_on=["cte_b_root"]),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == [
            "cte_a_root",
            "cte_b_root",
            "cte_a_leaf",
            "cte_b_leaf",
        ]

    def test_missing_dependency_reported_once_for_duplicates(self, mock_dialect: Mock) -> None:
        """Missing dependency mentioned once even if repeated."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(
                name="cte_missing",
                query="SELECT * FROM missing_cte",
                depends_on=["missing_cte", "missing_cte"],
            ),
        ]
        with pytest.raises(ValueError, match=r"Missing CTE dependencies: missing_cte$"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_orders_complex_graph_deterministically(self, mock_dialect: Mock) -> None:
        """Complex dependency graph results in deterministic ordering."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_base_a", query="SELECT 1"),
            CTE(name="cte_base_b", query="SELECT 1"),
            CTE(name="cte_mid_b", query="SELECT * FROM cte_base_b", depends_on=["cte_base_b"]),
            CTE(
                name="cte_merge",
                query="SELECT * FROM cte_mid_b JOIN cte_base_a",
                depends_on=["cte_mid_b", "cte_base_a"],
            ),
            CTE(name="cte_result", query="SELECT * FROM cte_merge", depends_on=["cte_merge"]),
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [cte.name for cte in ordered] == [
            "cte_base_a",
            "cte_base_b",
            "cte_mid_b",
            "cte_merge",
            "cte_result",
        ]


class TestCTEAssembler:
    """Validate assembly of CTE chains into SQL statements."""

    def test_requires_dialect_instance(self) -> None:
        """Assembler enforces presence of dialect argument."""
        with pytest.raises(ValueError):
            CTEAssembler(dialect=None)  # type: ignore[arg-type]

    def test_validate_cte_collection_raises_on_empty(self, mock_dialect: Mock) -> None:
        """Empty CTE list triggers validation error."""
        assembler = CTEAssembler(dialect=mock_dialect)
        with pytest.raises(ValueError):
            assembler._validate_cte_collection([])

    def test_validate_cte_collection_raises_on_invalid_item(self, mock_dialect: Mock) -> None:
        """Non-CTE entries cause validation failure."""
        assembler = CTEAssembler(dialect=mock_dialect)
        with pytest.raises(ValueError):
            assembler._validate_cte_collection([object()])  # type: ignore[list-item]

    def test_generate_with_clause_single_cte_exact_format(self, mock_dialect: Mock) -> None:
        """WITH clause renders single CTE on separate indented lines."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_1", query="SELECT 1")
        with_clause = assembler._generate_with_clause([cte])
        expected = textwrap.dedent(
            """\
            WITH
              cte_1 AS (
                SELECT 1
              )"""
        )
        assert with_clause == expected

    def test_generate_with_clause_multiple_ctes_comma_placement(self, mock_dialect: Mock) -> None:
        """Multiple CTEs include trailing commas on all but final definition."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_1", query="SELECT 1"),
            CTE(name="cte_2", query="SELECT * FROM cte_1", depends_on=["cte_1"]),
        ]
        with_clause = assembler._generate_with_clause(ctes)
        expected = textwrap.dedent(
            """\
            WITH
              cte_1 AS (
                SELECT 1
              ),
              cte_2 AS (
                SELECT * FROM cte_1
              )"""
        )
        assert with_clause == expected

    def test_generate_with_clause_multiline_query_indentation(self, mock_dialect: Mock) -> None:
        """Multiline queries are indented four spaces per line."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(
            name="cte_1",
            query="SELECT 1\nFROM dual\nWHERE 1 = 1",
        )
        with_clause = assembler._generate_with_clause([cte])
        assert "    SELECT 1" in with_clause
        assert "    FROM dual" in with_clause
        assert "    WHERE 1 = 1" in with_clause

    def test_generate_with_clause_returns_empty_for_no_ctes(self, mock_dialect: Mock) -> None:
        """With clause function returns empty string for empty input."""
        assembler = CTEAssembler(dialect=mock_dialect)
        assert assembler._generate_with_clause([]) == ""

    def test_generate_with_clause_trims_surrounding_whitespace(self, mock_dialect: Mock) -> None:
        """Leading and trailing whitespace is removed from query bodies."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_trim", query="\n\n   SELECT 42   \n")
        with_clause = assembler._generate_with_clause([cte])
        lines = with_clause.splitlines()
        assert lines[2] == "    SELECT 42"
        assert lines[-1] == "  )"

    def test_generate_with_clause_preserves_internal_blank_lines(self, mock_dialect: Mock) -> None:
        """Blank lines inside query bodies are preserved."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(
            name="cte_blank",
            query="SELECT id\n\nFROM patient_resources",
        )
        with_clause = assembler._generate_with_clause([cte])
        lines = with_clause.splitlines()
        blank_index = lines.index("  cte_blank AS (") + 2
        assert lines[blank_index] == ""

    def test_generate_with_clause_dedents_triple_quoted_query(self, mock_dialect: Mock) -> None:
        """Triple quoted queries are dedented before indentation is applied."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(
            name="cte_dedent",
            query="""
                SELECT id,
                       resource
                FROM patient_resources
            """,
        )
        with_clause = assembler._generate_with_clause([cte])
        assert "    SELECT id," in with_clause
        assert "    FROM patient_resources" in with_clause

    def test_generate_with_clause_final_cte_has_no_trailing_comma(self, mock_dialect: Mock) -> None:
        """The final CTE definition omits a trailing comma."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_first", query="SELECT 1"),
            CTE(name="cte_last", query="SELECT * FROM cte_first", depends_on=["cte_first"]),
        ]
        with_clause = assembler._generate_with_clause(ctes)
        assert with_clause.splitlines()[-1] == "  )"

    def test_generate_with_clause_lines_have_no_trailing_whitespace(self, mock_dialect: Mock) -> None:
        """No trailing whitespace is emitted on any WITH clause line."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a", query="SELECT 1"),
            CTE(name="cte_b", query="SELECT * FROM cte_a", depends_on=["cte_a"]),
        ]
        with_clause = assembler._generate_with_clause(ctes)
        assert all(line == line.rstrip() for line in with_clause.splitlines())

    def test_generate_with_clause_preserves_tokens_when_tabs_present(self, mock_dialect: Mock) -> None:
        """Tab characters inside queries retain token ordering after formatting."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_tabs", query="SELECT\t1\nFROM\tdual")
        with_clause = assembler._generate_with_clause([cte])
        lines = with_clause.splitlines()
        assert lines[2].startswith("    SELECT")
        assert lines[2].endswith("1")
        assert lines[3].startswith("    FROM")
        assert lines[3].endswith("dual")

    def test_generate_final_select_appends_semicolon(self, mock_dialect: Mock) -> None:
        """Final SELECT references last CTE with semicolon."""
        assembler = CTEAssembler(dialect=mock_dialect)
        final_select = assembler._generate_final_select(CTE(name="cte_final", query="SELECT 1"))
        assert final_select == "SELECT * FROM cte_final;"

    def test_generate_final_select_uses_select_star(self, mock_dialect: Mock) -> None:
        """Final SELECT exposes all columns via wildcard projection."""
        assembler = CTEAssembler(dialect=mock_dialect)
        final_select = assembler._generate_final_select(CTE(name="cte_results", query="SELECT * FROM base"))
        assert final_select.startswith("SELECT * FROM ")

    def test_generate_final_select_respects_cte_name_case(self, mock_dialect: Mock) -> None:
        """CTE names preserve their original casing in the final SELECT."""
        assembler = CTEAssembler(dialect=mock_dialect)
        final_select = assembler._generate_final_select(CTE(name="CTE_MixedCase", query="SELECT 1"))
        assert final_select == "SELECT * FROM CTE_MixedCase;"

    def test_generate_final_select_supports_long_names(self, mock_dialect: Mock) -> None:
        """Longer CTE identifiers render without truncation."""
        assembler = CTEAssembler(dialect=mock_dialect)
        name = "cte_patient_measurement_results"
        final_select = assembler._generate_final_select(CTE(name=name, query="SELECT 1"))
        assert final_select.endswith(f"{name};")

    def test_generate_final_select_does_not_mutate_cte(self, mock_dialect: Mock) -> None:
        """Method leaves the original CTE object unchanged."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_source", query="SELECT 2", metadata={"sample": True})
        assembler._generate_final_select(cte)
        assert cte.query == "SELECT 2"
        assert cte.metadata["sample"] is True

    def test_generate_final_select_contains_no_newlines(self, mock_dialect: Mock) -> None:
        """Final SELECT remains a single line for predictable formatting."""
        assembler = CTEAssembler(dialect=mock_dialect)
        final_select = assembler._generate_final_select(CTE(name="cte_single_line", query="SELECT 1"))
        assert "\n" not in final_select
        assert final_select == final_select.strip()

    def test_assemble_query_single_cte(self, mock_dialect: Mock) -> None:
        """Single CTE assembly produces WITH + SELECT output."""
        assembler = CTEAssembler(dialect=mock_dialect)
        sql = assembler.assemble_query([CTE(name="cte_1", query="SELECT 1")])
        assert sql.startswith("WITH\n  cte_1 AS (")
        assert sql.endswith("SELECT * FROM cte_1;")

    def test_assemble_query_multiple_ctes(self, mock_dialect: Mock) -> None:
        """Multiple CTEs assemble into sequential WITH clause."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_1", query="SELECT 1"),
            CTE(name="cte_2", query="SELECT * FROM cte_1", depends_on=["cte_1"]),
        ]
        sql = assembler.assemble_query(ctes)
        assert sql.splitlines()[0] == "WITH"
        assert "  cte_1 AS (" in sql
        assert "  cte_2 AS (" in sql
        assert sql.endswith("SELECT * FROM cte_2;")

    def test_assemble_query_includes_newline_between_sections(self, mock_dialect: Mock) -> None:
        """WITH clause and final SELECT separated by newline."""
        assembler = CTEAssembler(dialect=mock_dialect)
        sql = assembler.assemble_query([CTE(name="cte_1", query="SELECT 1")])
        assert "\nSELECT * FROM cte_1;" in sql

    def test_assemble_query_with_clause_starts_with_keyword(self, mock_dialect: Mock) -> None:
        """Assembly output begins with WITH keyword."""
        assembler = CTEAssembler(dialect=mock_dialect)
        sql = assembler.assemble_query([CTE(name="cte_1", query="SELECT 1")])
        assert sql.startswith("WITH\n")

    def test_assemble_query_duckdb_executes(self, duckdb_dialect: Any) -> None:
        """Assembled SQL executes successfully using DuckDB dialect."""
        assembler = CTEAssembler(dialect=duckdb_dialect)
        ctes = [
            CTE(name="cte_seed", query="SELECT 1 AS id"),
            CTE(
                name="cte_result",
                query="SELECT id FROM cte_seed",
                depends_on=["cte_seed"],
            ),
        ]
        sql = assembler.assemble_query(ctes)
        result = duckdb_dialect.execute_query(sql)
        assert result == [(1,)]

    def test_assemble_query_postgresql_executes(self, postgresql_dialect: tuple[Any, List[str]]) -> None:
        """Assembled SQL triggers execute_query on PostgreSQL dialect."""
        dialect, executed_sql = postgresql_dialect
        assembler = CTEAssembler(dialect=dialect)
        ctes = [
            CTE(name="cte_seed", query="SELECT 1 AS id"),
            CTE(name="cte_result", query="SELECT id FROM cte_seed", depends_on=["cte_seed"]),
        ]
        sql = assembler.assemble_query(ctes)
        assert sql.endswith("SELECT * FROM cte_result;")
        result = dialect.execute_query(sql)
        assert result == []
        assert executed_sql[-1] == sql

    def test_assemble_query_final_select_references_last_cte(self, mock_dialect: Mock) -> None:
        """Final SELECT references the last CTE in ordered list."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_1", query="SELECT 1"),
            CTE(name="cte_2", query="SELECT * FROM cte_1", depends_on=["cte_1"]),
            CTE(name="cte_3", query="SELECT * FROM cte_2", depends_on=["cte_2"]),
        ]
        sql = assembler.assemble_query(ctes)
        assert sql.endswith("SELECT * FROM cte_3;")

    def test_assemble_query_preserves_cte_order(self, mock_dialect: Mock) -> None:
        """Assembly retains provided CTE order."""
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a", query="SELECT 1"),
            CTE(name="cte_b", query="SELECT * FROM cte_a", depends_on=["cte_a"]),
        ]
        sql = assembler.assemble_query(ctes)
        assert sql.index("cte_a AS") < sql.index("cte_b AS")


# ---------------------------------------------------------------------------
# DuckDB Dialect UNNEST Tests
# ---------------------------------------------------------------------------


class TestDuckDBDialectUnnest:
    """Validate DuckDB-specific LATERAL UNNEST generation."""

    @pytest.mark.parametrize(
        "array_column",
        [
            "json_extract(resource, '$.name')",
            "json_extract(resource, '$.telecom')",
            "json_extract(resource, '$.address[*].line')",
        ],
    )
    def test_generate_lateral_unnest_formats_expression(
        self,
        duckdb_dialect: Any,
        array_column: str,
    ) -> None:
        """DuckDB generates expected LATERAL UNNEST syntax for various expressions."""
        sql = duckdb_dialect.generate_lateral_unnest("patient_resources", array_column, "alias_item")
        assert sql == f"LATERAL UNNEST({array_column}) AS alias_item"

    @pytest.mark.parametrize("alias", ["name_item", "telecom_entry", "value"])
    def test_generate_lateral_unnest_alias_variations(
        self,
        duckdb_dialect: Any,
        alias: str,
    ) -> None:
        """Alias parameter is preserved verbatim in DuckDB output."""
        array_column = "json_extract(resource, '$.name')"
        sql = duckdb_dialect.generate_lateral_unnest("patient_resources", array_column, alias)
        assert sql.endswith(f"AS {alias}")

    def test_generate_lateral_unnest_ignores_source_table(self, duckdb_dialect: Any) -> None:
        """Source table parameter is not interpolated directly into DuckDB syntax."""
        sql = duckdb_dialect.generate_lateral_unnest("ignored_table", "array_expr", "alias")
        assert "ignored_table" not in sql

    def test_generate_lateral_unnest_multiple_calls_independent(self, duckdb_dialect: Any) -> None:
        """Multiple invocations do not share mutable state."""
        results = [
            duckdb_dialect.generate_lateral_unnest(
                "patient_resources",
                f"json_extract(resource, '$.{path}')",
                alias,
            )
            for path, alias in [("name", "name_item"), ("telecom", "telecom_item"), ("identifier", "id_item")]
        ]
        expected = [
            "LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item",
            "LATERAL UNNEST(json_extract(resource, '$.telecom')) AS telecom_item",
            "LATERAL UNNEST(json_extract(resource, '$.identifier')) AS id_item",
        ]
        assert results == expected

    def test_generate_lateral_unnest_embedded_in_select_executes(self, duckdb_dialect: Any) -> None:
        """Generated clause executes successfully when embedded in a SELECT."""
        connection = duckdb_dialect.get_connection()
        connection.execute("DROP TABLE IF EXISTS duckdb_unnest_test")
        connection.execute("CREATE TABLE duckdb_unnest_test (id INTEGER, names VARCHAR[])")
        connection.execute(
            """
            INSERT INTO duckdb_unnest_test VALUES
                (1, ['Alice', 'Bob']),
                (2, ['Cara'])
            """
        )
        clause = duckdb_dialect.generate_lateral_unnest(
            "duckdb_unnest_test", "t.names", "name_item"
        )
        sql = f"SELECT t.id, name_item.unnest FROM duckdb_unnest_test AS t, {clause}"
        result = duckdb_dialect.execute_query(sql)
        assert sorted(result) == [(1, "Alice"), (1, "Bob"), (2, "Cara")]
        connection.execute("DROP TABLE duckdb_unnest_test")

    def test_generate_lateral_unnest_preserves_whitespace(self, duckdb_dialect: Any) -> None:
        """Whitespace inside array expression is preserved by DuckDB implementation."""
        sql = duckdb_dialect.generate_lateral_unnest(
            "patient_resources",
            "  json_extract(resource, '$.name')  ",
            "alias_item",
        )
        assert sql == "LATERAL UNNEST(  json_extract(resource, '$.name')  ) AS alias_item"


# ---------------------------------------------------------------------------
# PostgreSQL Dialect UNNEST Tests
# ---------------------------------------------------------------------------


class TestPostgreSQLDialectUnnest:
    """Validate PostgreSQL-specific jsonb_array_elements LATERAL generation."""

    @pytest.mark.parametrize(
        "array_column",
        [
            "json_extract(resource, '$.name')",
            "json_extract(resource, '$.telecom')",
            "json_extract(resource, '$.identifier')",
        ],
    )
    def test_generate_lateral_unnest_formats_expression(
        self,
        postgresql_dialect: tuple[Any, List[str]],
        array_column: str,
    ) -> None:
        """PostgreSQL generates LATERAL jsonb_array_elements for arrays."""
        dialect, _ = postgresql_dialect
        sql = dialect.generate_lateral_unnest("patient_resources", array_column, "alias_item")
        assert sql == f"LATERAL jsonb_array_elements({array_column}) AS alias_item(unnest)"

    @pytest.mark.parametrize("alias", ["name_item", "telecom_entry", "identifier_entry"])
    def test_generate_lateral_unnest_alias_variations(
        self,
        postgresql_dialect: tuple[Any, List[str]],
        alias: str,
    ) -> None:
        """Alias parameter is appended to PostgreSQL clause."""
        dialect, _ = postgresql_dialect
        sql = dialect.generate_lateral_unnest("patient_resources", "json_extract(resource, '$.name')", alias)
        assert sql.endswith(f"AS {alias}(unnest)")

    def test_generate_lateral_unnest_ignores_source_table(self, postgresql_dialect: tuple[Any, List[str]]) -> None:
        """Source table parameter is unused in PostgreSQL syntax."""
        dialect, _ = postgresql_dialect
        sql = dialect.generate_lateral_unnest("ignored_table", "array_expr", "alias")
        assert "ignored_table" not in sql

    def test_generate_lateral_unnest_multiple_calls_independent(self, postgresql_dialect: tuple[Any, List[str]]) -> None:
        """Multiple invocations return independent SQL fragments."""
        dialect, _ = postgresql_dialect
        results = [
            dialect.generate_lateral_unnest(
                "patient_resources",
                f"json_extract(resource, '$.{path}')",
                alias,
            )
            for path, alias in [("name", "name_item"), ("telecom", "telecom_item"), ("identifier", "id_item")]
        ]
        expected = [
            "LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item(unnest)",
            "LATERAL jsonb_array_elements(json_extract(resource, '$.telecom')) AS telecom_item(unnest)",
            "LATERAL jsonb_array_elements(json_extract(resource, '$.identifier')) AS id_item(unnest)",
        ]
        assert results == expected

    def test_generate_lateral_unnest_embedded_query_records_sql(
        self,
        postgresql_dialect: tuple[Any, List[str]],
    ) -> None:
        """Generated clause can be embedded in SELECT and captured via execute_query."""
        dialect, executed_sql = postgresql_dialect
        clause = dialect.generate_lateral_unnest(
            "patient_resources", "json_extract(resource, '$.name')", "name_item"
        )
        sql = f"SELECT id FROM patient_resources, {clause}"
        result = dialect.execute_query(sql)
        assert result == []
        assert executed_sql[-1] == sql

    def test_generate_lateral_unnest_preserves_whitespace(
        self,
        postgresql_dialect: tuple[Any, List[str]],
    ) -> None:
        """Whitespace in array expression is preserved."""
        dialect, _ = postgresql_dialect
        sql = dialect.generate_lateral_unnest(
            "patient_resources",
            "  json_extract(resource, '$.name')  ",
            "alias_item",
        )
        assert sql == "LATERAL jsonb_array_elements(  json_extract(resource, '$.name')  ) AS alias_item(unnest)"


# ---------------------------------------------------------------------------
# Multi-Database Parity Tests
# ---------------------------------------------------------------------------


class TestMultiDatabaseParity:
    """Ensure dialect-specific differences retain consistent business logic."""

    def _make_fragment(self) -> SQLFragment:
        return SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
                "id_column": "patient_resources.id",
            },
        )

    def test_projection_line_matches_across_dialects(
        self,
        duckdb_builder: CTEBuilder,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """The projection SELECT line matches across dialects."""
        pg_builder, _ = postgresql_builder
        duckdb_sql = duckdb_builder._wrap_unnest_query(self._make_fragment(), "patient_resources", "cte_1", [])
        pg_sql = pg_builder._wrap_unnest_query(self._make_fragment(), "patient_resources", "cte_1", [])
        assert duckdb_sql.splitlines()[0] == pg_sql.splitlines()[0]

    def test_lateral_clause_differs_only_by_dialect(
        self,
        duckdb_builder: CTEBuilder,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """Dialect clauses differ in syntax but represent the same logic."""
        pg_builder, _ = postgresql_builder
        duckdb_sql = duckdb_builder._wrap_unnest_query(self._make_fragment(), "patient_resources", "cte_1", [])
        pg_sql = pg_builder._wrap_unnest_query(self._make_fragment(), "patient_resources", "cte_1", [])
        assert "LATERAL UNNEST" in duckdb_sql
        assert "jsonb_array_elements" in pg_sql

    def test_cte_chain_dependencies_identical(
        self,
        duckdb_builder: CTEBuilder,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """CTE dependencies remain identical across databases."""
        pg_builder, _ = postgresql_builder
        simple_fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            metadata={"result_alias": "name_array"},
        )
        unnest_fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.name_array",
                "result_alias": "name_item",
                "id_column": "cte_1.id",
            },
        )
        duckdb_ctes = duckdb_builder.build_cte_chain([simple_fragment, unnest_fragment])
        simple_pg_fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            metadata={"result_alias": "name_array"},
        )
        unnest_pg_fragment = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "cte_1.name_array",
                "result_alias": "name_item",
                "id_column": "cte_1.id",
            },
        )
        pg_ctes = pg_builder.build_cte_chain([simple_pg_fragment, unnest_pg_fragment])

        assert duckdb_ctes[1].depends_on == ["cte_1"]
        assert pg_ctes[1].depends_on == ["cte_1"]

    def test_projection_expression_consistency(
        self,
        duckdb_builder: CTEBuilder,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """projection_expression metadata yields matching SELECT content."""
        pg_builder, _ = postgresql_builder
        fragment_duckdb = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
                "projection_expression": "json_extract_scalar(name_item, '$.given[0]')",
            },
        )
        fragment_pg = SQLFragment(
            expression="json_extract(resource, '$.name')",
            source_table="patient_resources",
            requires_unnest=True,
            metadata={
                "array_column": "json_extract(resource, '$.name')",
                "result_alias": "name_item",
                "projection_expression": "json_extract_scalar(name_item, '$.given[0]')",
            },
        )
        duckdb_sql = duckdb_builder._wrap_unnest_query(fragment_duckdb, "patient_resources", "cte_1", [])
        pg_sql = pg_builder._wrap_unnest_query(fragment_pg, "patient_resources", "cte_1", [])
        assert "json_extract_scalar(name_item, '$.given[0]')" in duckdb_sql
        assert "json_extract_scalar(name_item, '$.given[0]')" in pg_sql

    def test_metadata_preserved_between_dialects(
        self,
        duckdb_builder: CTEBuilder,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """CTE metadata is preserved regardless of dialect."""
        pg_builder, _ = postgresql_builder
        duckdb_cte = duckdb_builder._fragment_to_cte(self._make_fragment(), previous_cte=None)
        pg_cte = pg_builder._fragment_to_cte(self._make_fragment(), previous_cte=None)
        assert duckdb_cte.metadata == pg_cte.metadata


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestUnnestIntegration:
    """Integration coverage for CTEBuilder + CTEAssembler with UNNEST behavior."""

    def test_duckdb_integration_single_level_unnest(self, duckdb_builder: CTEBuilder) -> None:
        """DuckDB executes single-level UNNEST chain end-to-end."""
        dialect = duckdb_builder.dialect
        connection = dialect.get_connection()
        table_name = "patient_resources_phase2"
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")
        connection.execute(f"CREATE TABLE {table_name} (id INTEGER, name_collection VARCHAR[])")
        connection.execute(
            f"""
            INSERT INTO {table_name} VALUES
                (1, ['Alice', 'Allie']),
                (2, ['Bob', 'Bobby'])
            """
        )

        fragments = [
            SQLFragment(
                expression="name_collection",
                source_table=table_name,
                metadata={"result_alias": "name_collection"},
            ),
            SQLFragment(
                expression="name_collection",
                source_table=table_name,
                requires_unnest=True,
                metadata={
                    "array_column": "cte_1.name_collection",
                    "result_alias": "name_item",
                    "id_column": "cte_1.id",
                    "projection_expression": "name_item.unnest",
                },
            ),
        ]
        ctes = duckdb_builder.build_cte_chain(fragments)
        assembler = CTEAssembler(dialect=dialect)
        sql = assembler.assemble_query(ctes)
        result = dialect.execute_query(sql)
        values = [
            row[1].strip('"') if isinstance(row[1], str) else row[1]
            for row in result
        ]
        assert "Alice" in values
        assert "Bob" in values
        connection.execute(f"DROP TABLE {table_name}")

    def test_duckdb_integration_nested_unnest(self, duckdb_builder: CTEBuilder) -> None:
        """DuckDB handles nested array UNNEST operations."""
        dialect = duckdb_builder.dialect
        connection = dialect.get_connection()
        table_name = "patient_resources_phase2_nested"
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")
        connection.execute(f"CREATE TABLE {table_name} (id INTEGER, name_collection VARCHAR[][])")
        connection.execute(
            f"""
            INSERT INTO {table_name} VALUES
                (1, [['Alice', 'Alicia'], ['Allie']]),
                (2, [['Bob']])
            """
        )

        fragments = [
            SQLFragment(
                expression="name_collection",
                source_table=table_name,
                metadata={"result_alias": "name_collection"},
            ),
            SQLFragment(
                expression="name_collection",
                source_table=table_name,
                requires_unnest=True,
                metadata={
                    "array_column": "cte_1.name_collection",
                    "result_alias": "name_item",
                    "id_column": "cte_1.id",
                },
            ),
            SQLFragment(
                expression="name_item",
                source_table=table_name,
                requires_unnest=True,
                metadata={
                    "array_column": "name_item.unnest",
                    "result_alias": "given_item",
                    "id_column": "cte_2.id",
                    "projection_expression": "given_item.unnest",
                },
            ),
        ]
        ctes = duckdb_builder.build_cte_chain(fragments)
        assembler = CTEAssembler(dialect=dialect)
        sql = assembler.assemble_query(ctes)
        result = dialect.execute_query(sql)
        flattened = [
            row[1].strip('"') if isinstance(row[1], str) else row[1]
            for row in result
        ]
        assert "Alice" in flattened
        assert "Alicia" in flattened
        assert "Allie" in flattened
        assert "Bob" in flattened
        connection.execute(f"DROP TABLE {table_name}")

    def test_postgresql_integration_sql_generation(
        self,
        postgresql_builder: tuple[CTEBuilder, List[str]],
    ) -> None:
        """PostgreSQL builder + assembler produce executable SQL string."""
        builder, executed_sql = postgresql_builder
        fragments = [
            SQLFragment(
                expression="json_extract(resource, '$.name')",
                source_table="patient_resources",
                metadata={"result_alias": "name_collection"},
            ),
            SQLFragment(
                expression="json_extract(resource, '$.name')",
                source_table="patient_resources",
                requires_unnest=True,
                metadata={
                    "array_column": "cte_1.name_collection",
                    "result_alias": "name_item",
                    "id_column": "cte_1.id",
                },
            ),
        ]
        ctes = builder.build_cte_chain(fragments)
        assembler = CTEAssembler(dialect=builder.dialect)
        sql = assembler.assemble_query(ctes)
        assert "LATERAL jsonb_array_elements" in sql
        result = builder.dialect.execute_query(sql)
        assert result == []
        assert executed_sql[-1] == sql


# ---------------------------------------------------------------------------
# Phase 3 Assembly Integration Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblerIntegrationPhase3:
    """Phase 3 coverage for assembler dependency ordering and builder integration."""

    @pytest.mark.parametrize(
        "ctes, expected_order",
        [
            (
                [
                    CTE(name="cte_gamma", query="SELECT * FROM cte_beta", depends_on=["cte_beta"]),
                    CTE(name="cte_alpha", query="SELECT 1"),
                    CTE(name="cte_beta", query="SELECT * FROM cte_alpha", depends_on=["cte_alpha"]),
                ],
                ["cte_alpha", "cte_beta", "cte_gamma"],
            ),
            (
                [
                    CTE(name="cte_join", query="SELECT * FROM cte_a JOIN cte_b", depends_on=["cte_a", "cte_b"]),
                    CTE(name="cte_b", query="SELECT 2"),
                    CTE(name="cte_a", query="SELECT 1"),
                ],
                ["cte_b", "cte_a", "cte_join"],
            ),
            (
                [
                    CTE(name="cte_child", query="SELECT * FROM cte_parent", depends_on=["cte_parent"]),
                    CTE(name="cte_orphan", query="SELECT 99"),
                    CTE(name="cte_parent", query="SELECT * FROM cte_orphan", depends_on=["cte_orphan"]),
                ],
                ["cte_orphan", "cte_parent", "cte_child"],
            ),
            (
                [
                    CTE(name="cte_tail", query="SELECT * FROM cte_mid", depends_on=["cte_mid"]),
                    CTE(name="cte_mid", query="SELECT * FROM cte_head", depends_on=["cte_head"]),
                    CTE(name="cte_head", query="SELECT 1"),
                    CTE(name="cte_branch", query="SELECT 2"),
                ],
                ["cte_head", "cte_mid", "cte_tail", "cte_branch"],
            ),
        ],
    )
    def test_dependency_ordering_via_assemble_query(
        self,
        mock_dialect: Mock,
        ctes: List[CTE],
        expected_order: Sequence[str],
    ) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        sql = assembler.assemble_query(ctes)
        assert extract_cte_definition_order(sql) == list(expected_order)
        assert sql.endswith(f"SELECT * FROM {expected_order[-1]};")

    @pytest.mark.parametrize(
        "fixture_name",
        ["complex_cte_chain", "branching_cte_chain", "custom_linear_chain"],
    )
    def test_with_clause_formatting_consistency(
        self,
        request: pytest.FixtureRequest,
        mock_dialect: Mock,
        fixture_name: str,
    ) -> None:
        if fixture_name == "custom_linear_chain":
            ctes = [
                CTE(name="cte_noise", query="SELECT 10"),
                CTE(name="cte_final", query="SELECT * FROM cte_noise", depends_on=["cte_noise"]),
            ]
        else:
            ctes = request.getfixturevalue(fixture_name)
        assembler = CTEAssembler(dialect=mock_dialect)
        sql = assembler.assemble_query(ctes)
        lines = sql.splitlines()
        assert lines[0] == "WITH"
        assert all(line == line.rstrip() for line in lines)
        assert sql.count(" AS (") == len(ctes)

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_birthdate_fragments, id="birthDate"),
            pytest.param(make_gender_fragments, id="gender"),
            pytest.param(make_name_fragments, id="name"),
        ],
    )
    def test_builder_pipeline_generates_expected_sql(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        assert extract_cte_definition_order(sql) == [cte.name for cte in ctes]
        assert sql.endswith(f"SELECT * FROM {ctes[-1].name};")

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_name_fragments, id="single_unnest"),
            pytest.param(make_name_given_fragments, id="nested_unnest"),
        ],
    )
    def test_builder_pipeline_contains_lateral_clause(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        assert "LATERAL" in sql
        assert sql.endswith(f"SELECT * FROM {ctes[-1].name};")

    def test_assembler_reorders_builder_output(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_name_given_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(list(reversed(ctes)))
        assert extract_cte_definition_order(sql) == [cte.name for cte in ctes]
        assert sql.endswith(f"SELECT * FROM {ctes[-1].name};")

    def test_assembler_does_not_mutate_cte_metadata(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_name_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        metadata_snapshot = [cte.metadata.copy() for cte in ctes]
        duckdb_assembler.assemble_query(ctes)
        assert [cte.metadata for cte in ctes] == metadata_snapshot

    def test_builder_pipeline_handles_manual_select_fragment(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_telecom_fragments(duckdb_patient_resources)
        fragments.append(make_telecom_filtered_fragment())
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        assert "json_extract_string(telecom_entry.unnest, '$.system') = 'phone'" in sql
        assert sql.endswith(f"SELECT * FROM {ctes[-1].name};")


# ---------------------------------------------------------------------------
# CTE Assembler Edge Cases
# ---------------------------------------------------------------------------


class TestCTEAssemblerEdgeCases:
    """Exercise branch coverage for edge conditions in the assembler."""

    def test_wrap_unnest_query_requires_flag(self, builder: CTEBuilder) -> None:
        """_wrap_unnest_query rejects fragments without requires_unnest."""
        fragment = SQLFragment(expression="json_extract(resource, '$.name')", source_table="patient_resources")
        with pytest.raises(ValueError, match="expects fragment.requires_unnest"):
            builder._wrap_unnest_query(fragment, "patient_resources", "cte_1", [])

    def test_assemble_query_returns_final_select_when_with_clause_empty(
        self,
        mock_dialect: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """assemble_query returns only final SELECT when WITH clause suppressed."""
        assembler = CTEAssembler(dialect=mock_dialect)
        monkeypatch.setattr(assembler, "_generate_with_clause", lambda ctes: "")
        sql = assembler.assemble_query([CTE(name="cte_single", query="SELECT 1")])
        assert sql == "SELECT * FROM cte_single;"

    def test_order_ctes_by_dependencies_empty_input(self, mock_dialect: Mock) -> None:
        """Empty list ordering returns empty list."""
        assembler = CTEAssembler(dialect=mock_dialect)
        assert assembler._order_ctes_by_dependencies([]) == []

    def test_order_ctes_generic_cycle_error(
        self,
        mock_dialect: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Cycle detection fallback raises generic message when path unavailable."""
        assembler = CTEAssembler(dialect=mock_dialect)

        def _no_cycle_path(
            dependencies: Dict[str, List[str]],
            candidates: Set[str],
            order_index: Dict[str, int],
        ) -> List[str]:
            return []

        monkeypatch.setattr(assembler, "_find_dependency_cycle", _no_cycle_path)
        ctes = [
            CTE(name="cte_a", query="SELECT * FROM cte_b", depends_on=["cte_b"]),
            CTE(name="cte_b", query="SELECT * FROM cte_a", depends_on=["cte_a"]),
        ]
        with pytest.raises(ValueError, match=r"CTE dependency cycle detected$"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_find_dependency_cycle_skips_non_candidates(self, mock_dialect: Mock) -> None:
        """_find_dependency_cycle ignores dependencies not in candidate set."""
        assembler = CTEAssembler(dialect=mock_dialect)
        result = assembler._find_dependency_cycle(
            dependencies={"cte_a": ["external"], "cte_b": []},
            candidates={"cte_a"},
            order_index={"cte_a": 0},
        )
        assert result == []

    def test_find_dependency_cycle_skips_already_processed_candidates(self, mock_dialect: Mock) -> None:
        """Visited candidates are skipped on subsequent iterations."""
        assembler = CTEAssembler(dialect=mock_dialect)
        result = assembler._find_dependency_cycle(
            dependencies={"cte_a": ["cte_b"], "cte_b": []},
            candidates={"cte_a", "cte_b"},
            order_index={"cte_a": 0, "cte_b": 1},
        )
        assert result == []

    def test_find_dependency_cycle_detects_cycle_and_skips_visited(self, mock_dialect: Mock) -> None:
        """_find_dependency_cycle returns cycle path and skips already visited nodes."""
        assembler = CTEAssembler(dialect=mock_dialect)
        result = assembler._find_dependency_cycle(
            dependencies={"cte_a": ["cte_b"], "cte_b": ["cte_a"]},
            candidates={"cte_a", "cte_b"},
            order_index={"cte_a": 0, "cte_b": 1},
        )
        assert result == ["cte_a", "cte_b", "cte_a"]

    def test_format_cte_definition_handles_empty_query(self, mock_dialect: Mock) -> None:
        """_format_cte_definition emits minimal block for empty query bodies."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_empty", query="   ")
        formatted = assembler._format_cte_definition(cte, is_last=True)
        assert formatted == "  cte_empty AS (\n  )"

    def test_format_cte_definition_handles_empty_query_non_last(self, mock_dialect: Mock) -> None:
        """Formatting empty block with trailing comma behaves as expected."""
        assembler = CTEAssembler(dialect=mock_dialect)
        cte = CTE(name="cte_mid", query="   ")
        formatted = assembler._format_cte_definition(cte, is_last=False)
        assert formatted == "  cte_mid AS (\n  ),"

    def test_normalize_and_indent_empty_query(self) -> None:
        """_normalize_query_body and _indent_query_body handle empty strings."""
        assert CTEAssembler._normalize_query_body("") == ""
        assert CTEAssembler._indent_query_body("") == ""


# ---------------------------------------------------------------------------
# Phase 3 End-to-End Execution Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblyEndToEnd:
    """End-to-end DuckDB execution tests for assembled SQL."""

    @pytest.mark.parametrize(
        ("fragment_factory", "expected"),
        [
            pytest.param(
                make_birthdate_fragments,
                {1: "1980-01-01", 2: "1975-05-20", 3: "1990-07-15"},
                id="birthDate",
            ),
            pytest.param(
                make_gender_fragments,
                {1: "female", 2: "male", 3: "female"},
                id="gender",
            ),
        ],
    )
    def test_end_to_end_scalar_paths(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        expected: Dict[int, str],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        result_map = {row[0]: row[1] for row in result}
        assert result_map == expected

    @pytest.mark.parametrize(
        ("fragment_factory", "expected_count"),
        [
            pytest.param(make_name_fragments, 5, id="name"),
            pytest.param(make_name_given_fragments, 6, id="name_given"),
        ],
    )
    def test_end_to_end_population_counts(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        expected_count: int,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        assert len(result) == expected_count
        assert sql.endswith(f"SELECT * FROM {ctes[-1].name};")

    def test_end_to_end_name_given_flattening(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_name_given_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        values_by_patient: Dict[int, List[str]] = {}
        for patient_id, given_name in result:
            values_by_patient.setdefault(patient_id, []).append(given_name)
        for pid, names in values_by_patient.items():
            values_by_patient[pid] = [
                name.strip('"') if isinstance(name, str) else name
                for name in names
            ]
        assert set(values_by_patient[1]) == {"Alice", "Ann", "Allie"}
        assert set(values_by_patient[2]) == {"Bob"}
        assert set(values_by_patient[3]) == {"Cara", "CJ"}

    def test_end_to_end_address_line_flattening(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_address_line_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        values_by_patient: Dict[int, List[str]] = {}
        for patient_id, line_value in result:
            values_by_patient.setdefault(patient_id, []).append(line_value)
        for pid, lines in values_by_patient.items():
            values_by_patient[pid] = [
                line.strip('"') if isinstance(line, str) else line
                for line in lines
            ]
        assert set(values_by_patient[1]) == {"123 Main St", "Apt 1"}
        assert set(values_by_patient[2]) == {"500 Elm St"}
        assert set(values_by_patient[3]) == {"742 Evergreen Terrace"}

    def test_end_to_end_telecom_filter_returns_expected_ids(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_telecom_fragments(duckdb_patient_resources)
        fragments.append(make_telecom_filtered_fragment())
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        phone_values: Dict[int, str] = {}
        for patient_id, telecom_json in result:
            value = telecom_json
            if isinstance(telecom_json, str):
                try:
                    parsed = json.loads(telecom_json)
                except json.JSONDecodeError:
                    parsed = {"value": telecom_json.strip('"')}
                value = parsed.get("value") if isinstance(parsed, dict) else telecom_json
            elif isinstance(telecom_json, dict):
                value = telecom_json.get("value")
            phone_values[patient_id] = value
        assert phone_values == {1: "555-1000", 3: "555-2000"}

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_birthdate_fragments, id="birthDate"),
            pytest.param(make_name_fragments, id="name"),
            pytest.param(make_address_line_fragments, id="address"),
        ],
    )
    def test_end_to_end_sql_validity_and_formatting(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        assert sql.startswith("WITH")
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Phase 3 Multi-Database Parity Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblyMultiDatabase:
    """Validate DuckDB and PostgreSQL parity for assembled SQL."""

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_birthdate_fragments, id="birthDate"),
            pytest.param(make_name_fragments, id="name"),
            pytest.param(make_name_given_fragments, id="name_given"),
        ],
    )
    def test_definition_order_matches_between_dialects(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
        duckdb_patient_resources: str,
    ) -> None:
        pg_builder, _ = postgresql_builder
        pg_assembler, _ = postgresql_assembler
        duckdb_ctes = duckdb_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        duckdb_sql = duckdb_assembler.assemble_query(duckdb_ctes)
        pg_ctes = pg_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        pg_sql = pg_assembler.assemble_query(pg_ctes)
        assert extract_cte_definition_order(pg_sql) == extract_cte_definition_order(duckdb_sql)

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_birthdate_fragments, id="birthDate"),
            pytest.param(make_name_fragments, id="name"),
        ],
    )
    def test_final_select_identical_between_dialects(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
        duckdb_patient_resources: str,
    ) -> None:
        pg_builder, _ = postgresql_builder
        pg_assembler, _ = postgresql_assembler
        duckdb_ctes = duckdb_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        pg_ctes = pg_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        duckdb_sql = duckdb_assembler.assemble_query(duckdb_ctes)
        pg_sql = pg_assembler.assemble_query(pg_ctes)
        assert duckdb_sql.splitlines()[-1] == pg_sql.splitlines()[-1]

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_name_fragments, id="name"),
            pytest.param(make_name_given_fragments, id="name_given"),
        ],
    )
    def test_lateral_clause_variations(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
        duckdb_patient_resources: str,
    ) -> None:
        pg_builder, _ = postgresql_builder
        pg_assembler, _ = postgresql_assembler
        duckdb_sql = duckdb_assembler.assemble_query(
            duckdb_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        )
        pg_sql = pg_assembler.assemble_query(
            pg_builder.build_cte_chain(fragment_factory(duckdb_patient_resources))
        )
        assert "LATERAL UNNEST" in duckdb_sql
        assert "jsonb_array_elements" in pg_sql

    def test_sql_formatting_consistency(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
        duckdb_patient_resources: str,
    ) -> None:
        pg_builder, _ = postgresql_builder
        pg_assembler, _ = postgresql_assembler
        fragments = make_address_line_fragments(duckdb_patient_resources)
        duckdb_sql = duckdb_assembler.assemble_query(duckdb_builder.build_cte_chain(fragments))
        pg_sql = pg_assembler.assemble_query(pg_builder.build_cte_chain(fragments))
        assert duckdb_sql.count("WITH") == pg_sql.count("WITH")
        assert len(duckdb_sql.splitlines()) == len(pg_sql.splitlines())


# ---------------------------------------------------------------------------
# Phase 3 Execution Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblyExecution:
    """Validate execution behavior for assembled SQL across dialects."""

    @pytest.mark.parametrize(
        ("fragment_factory", "expected_count"),
        [
            pytest.param(make_birthdate_fragments, 3, id="birthDate"),
            pytest.param(make_name_fragments, 5, id="name"),
            pytest.param(make_address_line_fragments, 4, id="address"),
        ],
    )
    def test_duckdb_execution_row_counts(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        expected_count: int,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        assert len(result) == expected_count

    def test_duckdb_execution_result_values(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_name_given_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        flattened = sorted(
            value.strip('"') if isinstance(value, str) else value
            for _, value in result
        )
        assert flattened == ["Alice", "Allie", "Ann", "Bob", "CJ", "Cara"]

    def test_duckdb_execution_empty_results(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_telecom_fragments(duckdb_patient_resources)
        fragments.append(
            SQLFragment(
                expression=textwrap.dedent(
                    """\
                    SELECT cte_2.id,
                           telecom_entry.unnest
                    FROM cte_2
                    WHERE json_extract_string(telecom_entry.unnest, '$.system') = 'fax'
                    """
                ),
                source_table="cte_2",
                dependencies=["cte_2"],
            )
        )
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = duckdb_assembler.dialect.execute_query(sql)
        assert result == []

    def test_duckdb_execution_handles_null_fields(self, duckdb_assembler: CTEAssembler) -> None:
        dialect = duckdb_assembler.dialect
        connection = dialect.get_connection()
        connection.execute("DROP TABLE IF EXISTS patient_nulls")
        connection.execute("CREATE TABLE patient_nulls (id INTEGER, values_list VARCHAR[])")
        connection.execute("INSERT INTO patient_nulls VALUES (1, ['a', 'b']), (2, NULL)")
        builder = CTEBuilder(dialect)
        fragments = [
            SQLFragment(
                expression="values_list",
                source_table="patient_nulls",
                metadata={"result_alias": "values_list"},
            ),
            SQLFragment(
                expression="values_list",
                source_table="patient_nulls",
                requires_unnest=True,
                metadata={
                    "array_column": "cte_1.values_list",
                    "result_alias": "value_entry",
                    "id_column": "cte_1.id",
                    "projection_expression": "value_entry.unnest",
                },
            ),
        ]
        ctes = builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        result = dialect.execute_query(sql)
        normalized = [
            (row[0], row[1].strip('"') if isinstance(row[1], str) else row[1])
            for row in result
        ]
        assert normalized == [(1, "a"), (1, "b")]
        connection.execute("DROP TABLE patient_nulls")

    @pytest.mark.parametrize(
        "fragment_factory",
        [
            pytest.param(make_birthdate_fragments, id="birthDate"),
            pytest.param(make_name_fragments, id="name"),
            pytest.param(make_address_line_fragments, id="address"),
        ],
    )
    def test_postgresql_execution_captures_sql(
        self,
        fragment_factory: Callable[[str], List[SQLFragment]],
        duckdb_patient_resources: str,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
    ) -> None:
        builder, executed_sql = postgresql_builder
        assembler, captured_sql = postgresql_assembler
        fragments = fragment_factory(duckdb_patient_resources)
        ctes = builder.build_cte_chain(fragments)
        sql = assembler.assemble_query(ctes)
        result = assembler.dialect.execute_query(sql)
        assert result == []
        assert executed_sql[-1] == sql
        assert captured_sql[-1] == sql

    def test_postgresql_execution_records_multiple_statements(
        self,
        duckdb_patient_resources: str,
        postgresql_builder: tuple[CTEBuilder, List[str]],
        postgresql_assembler: Tuple[CTEAssembler, List[str]],
    ) -> None:
        builder, executed_sql = postgresql_builder
        assembler, captured_sql = postgresql_assembler
        birth_sql = assembler.assemble_query(
            builder.build_cte_chain(make_birthdate_fragments(duckdb_patient_resources))
        )
        assembler.dialect.execute_query(birth_sql)
        gender_sql = assembler.assemble_query(
            builder.build_cte_chain(make_gender_fragments(duckdb_patient_resources))
        )
        assembler.dialect.execute_query(gender_sql)
        filtered_builder_sql = [sql for sql in executed_sql if not sql.startswith("SET statement_timeout")]
        filtered_assembler_sql = [sql for sql in captured_sql if not sql.startswith("SET statement_timeout")]
        assert filtered_builder_sql[-2:] == [birth_sql, gender_sql]
        assert filtered_assembler_sql[-2:] == [birth_sql, gender_sql]

    def test_execution_invalid_sql_raises_error(
        self,
        duckdb_assembler: CTEAssembler,
    ) -> None:
        ctes = [
            CTE(name="cte_invalid", query="SELECT invalid_column FROM missing_table"),
        ]
        sql = duckdb_assembler.assemble_query(ctes)
        with pytest.raises(Exception):
            duckdb_assembler.dialect.execute_query(sql)

    def test_duckdb_execution_repeatable_runs_identical(
        self,
        duckdb_builder: CTEBuilder,
        duckdb_assembler: CTEAssembler,
        duckdb_patient_resources: str,
    ) -> None:
        fragments = make_birthdate_fragments(duckdb_patient_resources)
        ctes = duckdb_builder.build_cte_chain(fragments)
        sql = duckdb_assembler.assemble_query(ctes)
        first = duckdb_assembler.dialect.execute_query(sql)
        second = duckdb_assembler.dialect.execute_query(sql)
        assert first == second


# ---------------------------------------------------------------------------
# Phase 3 Error Handling Tests
# ---------------------------------------------------------------------------


class TestCTEAssemblyErrorHandling:
    """Validate public API error handling for CTE assembly."""

    def test_assemble_query_empty_collection_error(self, mock_dialect: Mock) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        with pytest.raises(ValueError, match="requires at least one CTE"):
            assembler.assemble_query([])

    def test_assemble_query_rejects_non_cte_entries(self, mock_dialect: Mock) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        with pytest.raises(ValueError, match="is not a CTE instance"):
            assembler.assemble_query([object()])  # type: ignore[list-item]

    def test_assemble_query_missing_dependency(self, mock_dialect: Mock) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_valid", query="SELECT 1"),
            CTE(name="cte_missing", query="SELECT * FROM missing_cte", depends_on=["missing_cte"]),
        ]
        with pytest.raises(ValueError, match="Missing CTE dependencies: missing_cte"):
            assembler.assemble_query(ctes)

    def test_assemble_query_cycle_detection(self, mock_dialect: Mock) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_a", query="SELECT * FROM cte_b", depends_on=["cte_b"]),
            CTE(name="cte_b", query="SELECT * FROM cte_a", depends_on=["cte_a"]),
        ]
        with pytest.raises(ValueError, match="cte_a -> cte_b -> cte_a"):
            assembler.assemble_query(ctes)

    def test_assemble_query_duplicate_name_detection(self, mock_dialect: Mock) -> None:
        assembler = CTEAssembler(dialect=mock_dialect)
        ctes = [
            CTE(name="cte_dup", query="SELECT 1"),
            CTE(name="cte_dup", query="SELECT 2"),
        ]
        with pytest.raises(ValueError, match="Duplicate CTE name detected: cte_dup"):
            assembler.assemble_query(ctes)
