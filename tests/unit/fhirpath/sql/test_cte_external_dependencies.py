"""Unit tests for CTE external table dependency handling (SP-021-006).

Tests that CTEAssembler correctly handles external table dependencies like 'resource'
without raising "Missing CTE dependencies" errors.
"""

import pytest
from fhir4ds.fhirpath.sql.cte import CTE, CTEAssembler
from fhir4ds.dialects.duckdb import DuckDBDialect


class TestCTEExternalDependencies:
    """Test CTE assembly with external table dependencies."""

    @pytest.fixture
    def assembler(self) -> CTEAssembler:
        """Create a CTEAssembler with DuckDB dialect."""
        return CTEAssembler(DuckDBDialect())

    def test_resource_table_recognized_as_external(self, assembler: CTEAssembler):
        """CTE with 'resource' dependency should not raise 'Missing CTE dependencies' error."""
        cte = CTE(
            name="cte_1",
            query="SELECT * FROM resource WHERE resourceType = 'Patient'",
            depends_on=["resource"]
        )

        # Should not raise ValueError about missing dependencies
        sql = assembler.assemble_query([cte])

        assert "WITH" in sql
        assert "cte_1" in sql
        assert "SELECT * FROM resource" in sql

    def test_unknown_dependency_raises_error(self, assembler: CTEAssembler):
        """CTE with unknown dependency (not CTE, not external) should raise error."""
        cte = CTE(
            name="cte_1",
            query="SELECT * FROM unknown_table",
            depends_on=["unknown_table"]
        )

        with pytest.raises(ValueError, match="Missing CTE dependencies: unknown_table"):
            assembler.assemble_query([cte])

    def test_multiple_ctes_with_resource_dependency(self, assembler: CTEAssembler):
        """Multiple CTEs can depend on 'resource' table."""
        ctes = [
            CTE(
                name="cte_1",
                query="SELECT id, name FROM resource WHERE resourceType = 'Patient'",
                depends_on=["resource"]
            ),
            CTE(
                name="cte_2",
                query="SELECT id, active FROM resource WHERE resourceType = 'Practitioner'",
                depends_on=["resource"]
            ),
        ]

        sql = assembler.assemble_query(ctes)

        assert "cte_1" in sql
        assert "cte_2" in sql
        assert sql.count("FROM resource") == 2

    def test_chained_dependencies_with_external_table(self, assembler: CTEAssembler):
        """CTEs can form dependency chains starting from external tables."""
        ctes = [
            CTE(
                name="cte_1",
                query="SELECT id FROM resource",
                depends_on=["resource"]
            ),
            CTE(
                name="cte_2",
                query="SELECT id FROM cte_1 WHERE id > 100",
                depends_on=["cte_1"]
            ),
            CTE(
                name="cte_3",
                query="SELECT COUNT(*) as count FROM cte_2",
                depends_on=["cte_2"]
            ),
        ]

        sql = assembler.assemble_query(ctes)

        # Verify ordering: cte_1 before cte_2 before cte_3
        cte_1_pos = sql.index("cte_1")
        cte_2_pos = sql.index("cte_2")
        cte_3_pos = sql.index("cte_3")

        assert cte_1_pos < cte_2_pos < cte_3_pos

    def test_mixed_dependencies_external_and_cte(self, assembler: CTEAssembler):
        """CTE can depend on both external tables and other CTEs."""
        ctes = [
            CTE(
                name="cte_1",
                query="SELECT id FROM resource",
                depends_on=["resource"]
            ),
            CTE(
                name="cte_2",
                query="SELECT cte_1.id FROM cte_1 JOIN resource ON cte_1.id = resource.id",
                depends_on=["cte_1", "resource"]
            ),
        ]

        sql = assembler.assemble_query(ctes)

        # Verify both CTEs are in the output
        assert "cte_1" in sql
        assert "cte_2" in sql
        # Verify ordering: cte_1 before cte_2
        assert sql.index("cte_1") < sql.index("cte_2")

    def test_external_dependency_does_not_affect_ordering(self, assembler: CTEAssembler):
        """External dependencies don't affect CTE ordering (only CTE-to-CTE deps matter)."""
        ctes = [
            CTE(
                name="cte_1",
                query="SELECT id FROM resource",
                depends_on=["resource"]
            ),
            CTE(
                name="cte_2",
                query="SELECT id FROM resource WHERE active = true",
                depends_on=["resource"]
            ),
        ]

        sql = assembler.assemble_query(ctes)

        # Both CTEs should be present
        assert "cte_1" in sql
        assert "cte_2" in sql

        # Since neither depends on the other, they maintain input order
        assert sql.index("cte_1") < sql.index("cte_2")

    def test_custom_external_tables_parameter(self, assembler: CTEAssembler):
        """CTEAssembler can accept custom external tables beyond 'resource'."""
        # This tests the extensibility of the fix
        cte = CTE(
            name="cte_1",
            query="SELECT * FROM valueset",
            depends_on=["valueset"]
        )

        # Should raise error since 'valueset' is not in default external tables
        with pytest.raises(ValueError, match="Missing CTE dependencies: valueset"):
            assembler.assemble_query([cte])

        # NOTE: Currently external_tables parameter is not exposed through assemble_query()
        # This test documents the desired behavior for future enhancement
        # If external_tables becomes configurable, uncomment below:
        # sql = assembler.assemble_query([cte], external_tables={"resource", "valueset"})
        # assert "valueset" in sql

    def test_no_dependencies_still_works(self, assembler: CTEAssembler):
        """CTEs with no dependencies work as before."""
        cte = CTE(
            name="cte_1",
            query="SELECT 1 as value",
            depends_on=[]
        )

        sql = assembler.assemble_query([cte])
        assert "cte_1" in sql
        assert "SELECT 1 as value" in sql
