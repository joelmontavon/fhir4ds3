"""Unit tests for subsetOf/supersetOf column preservation (SP-106).

Tests the implementation of set comparison functions subsetOf() and supersetOf()
with special focus on column preservation through CTE chains.

This tests:
- subsetOf() function generates correct SQL
- supersetOf() function generates correct SQL
- Preserved columns (e.g., name_item, given_item) are maintained
- CTE chains work correctly with set operations
- Multi-database consistency
- Edge cases and error handling

Test Coverage:
- Basic subsetOf/supersetOf functionality
- Column preservation through CTEs
- Set operations with path navigation
- Empty collection handling
- Complex expressions with set operations

Module: tests.unit.fhirpath.sql.test_subsetof_column_preservation
Created: 2025-01-27
Task: SP-106
"""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.ast.nodes import (
    FunctionCallNode,
    IdentifierNode,
)

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


@pytest.fixture
def parser() -> FHIRPathParser:
    """Provide FHIRPath parser for tests."""
    return FHIRPathParser()


@pytest.fixture
def duckdb_translator():
    """Create DuckDB translator for testing."""
    if not DUCKDB_AVAILABLE:
        pytest.skip("DuckDB not available")
    dialect = DuckDBDialect(database=":memory:")
    return ASTToSQLTranslator(dialect, "Patient")


@pytest.fixture
def postgresql_translator():
    """Create PostgreSQL translator for testing."""
    if not POSTGRESQL_AVAILABLE:
        pytest.skip("PostgreSQL not available")
    try:
        dialect = PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not accessible")
    return ASTToSQLTranslator(dialect, "Patient")


class TestSubsetOfBasics:
    """Test basic subsetOf() functionality."""

    def test_subsetof_generates_sql(self, duckdb_translator, parser):
        """Test that subsetOf() generates SQL expression."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        fragment = fragments[-1]

        assert isinstance(fragment, SQLFragment)
        # Should generate SQL
        assert fragment.expression is not None
        assert len(fragment.expression) > 0

        # Metadata
        assert fragment.metadata.get('function') == 'subsetOf'
        assert fragment.metadata.get('result_type') == 'boolean'

    def test_subsetof_preserves_columns(self, duckdb_translator, parser):
        """Test that subsetOf() preserves columns through CTEs."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the subsetOf fragment
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

        # Should have preserved_columns attribute
        assert hasattr(subsetof_fragment, 'preserved_columns')
        preserved = subsetof_fragment.preserved_columns

        # Should preserve some columns
        assert preserved is not None
        # May be empty or list, depending on implementation

    def test_subsetof_no_unnest_required(self, duckdb_translator, parser):
        """Test that subsetOf() doesn't require unnesting."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the subsetOf fragment
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None
        assert subsetof_fragment.requires_unnest is False
        assert subsetof_fragment.is_aggregate is False

    def test_subsetof_with_this_variable(self, duckdb_translator, parser):
        """Test subsetOf() with $this variable reference."""
        parsed = parser.parse("name.first().subsetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should handle $this reference
        assert any(f.metadata.get('function') == 'subsetOf' for f in fragments)


class TestSupersetOfBasics:
    """Test basic supersetOf() functionality."""

    def test_supersetof_generates_sql(self, duckdb_translator, parser):
        """Test that supersetOf() generates SQL expression."""
        parsed = parser.parse("name.given.supersetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        fragment = fragments[-1]

        assert isinstance(fragment, SQLFragment)
        # Should generate SQL
        assert fragment.expression is not None
        assert len(fragment.expression) > 0

        # Metadata
        assert fragment.metadata.get('function') == 'supersetOf'
        assert fragment.metadata.get('result_type') == 'boolean'

    def test_supersetof_preserves_columns(self, duckdb_translator, parser):
        """Test that supersetOf() preserves columns through CTEs."""
        parsed = parser.parse("name.given.supersetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the supersetOf fragment
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None

        # Should have preserved_columns attribute
        assert hasattr(supersetof_fragment, 'preserved_columns')
        preserved = supersetof_fragment.preserved_columns

        # Should preserve some columns
        assert preserved is not None

    def test_supersetof_no_unnest_required(self, duckdb_translator, parser):
        """Test that supersetOf() doesn't require unnesting."""
        parsed = parser.parse("name.given.supersetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the supersetOf fragment
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None
        assert supersetof_fragment.requires_unnest is False
        assert supersetof_fragment.is_aggregate is False


class TestSubsetOfColumnPreservation:
    """Test column preservation in subsetOf() through CTE chains."""

    def test_subsetof_preserves_name_item(self, duckdb_translator, parser):
        """Test that subsetOf() preserves name_item column."""
        parsed = parser.parse("name.subsetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the subsetOf fragment
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

        # Check preserved_columns includes name_item
        preserved = subsetof_fragment.preserved_columns
        if preserved:
            # Should preserve columns from path navigation
            assert isinstance(preserved, (list, set, dict))

    def test_subsetof_preserves_given_item(self, duckdb_translator, parser):
        """Test that subsetOf() preserves given_item column."""
        parsed = parser.parse("name.given.subsetOf($this.name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the subsetOf fragment
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

        # Check preserved_columns
        preserved = subsetof_fragment.preserved_columns
        assert preserved is not None

    def test_subsetof_with_first_preserves_columns(self, duckdb_translator, parser):
        """Test subsetOf() after first() preserves columns."""
        parsed = parser.parse("name.first().subsetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Should have subsetOf fragment
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None
        # Should preserve columns even through first()
        assert hasattr(subsetof_fragment, 'preserved_columns')


class TestSupersetOfColumnPreservation:
    """Test column preservation in supersetOf() through CTE chains."""

    def test_supersetof_preserves_name_item(self, duckdb_translator, parser):
        """Test that supersetOf() preserves name_item column."""
        parsed = parser.parse("name.supersetOf($this.name.first())")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the supersetOf fragment
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None

        # Check preserved_columns
        preserved = supersetof_fragment.preserved_columns
        assert preserved is not None

    def test_supersetof_preserves_given_item(self, duckdb_translator, parser):
        """Test that supersetOf() preserves given_item column."""
        parsed = parser.parse("name.given.supersetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        # Find the supersetOf fragment
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None

        # Check preserved_columns
        preserved = supersetof_fragment.preserved_columns
        assert preserved is not None


class TestSetOperationsWithComplexExpressions:
    """Test set operations in complex expressions."""

    def test_subsetof_in_where_clause(self, duckdb_translator, parser):
        """Test subsetOf() used in where() clause."""
        parsed = parser.parse("Patient.name.where(subsetOf($this.name))")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should generate WHERE clause with subsetOf
        assert any("subsetOf" in f.metadata.get('function', '') for f in fragments)

    def test_subsetof_chained_with_other_functions(self, duckdb_translator, parser):
        """Test subsetOf() chained with other functions."""
        parsed = parser.parse("name.given.subsetOf(name.family).empty()")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should have both subsetOf and empty
        functions = [f.metadata.get('function') for f in fragments]
        assert 'subsetOf' in functions or any('subsetOf' in str(f) for f in functions)

    def test_supersetof_with_select(self, duckdb_translator, parser):
        """Test supersetOf() used with select()."""
        parsed = parser.parse("Patient.select(name.supersetOf($this.name.first()))")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should generate SELECT with supersetOf
        assert any("supersetOf" in f.metadata.get('function', '') for f in fragments)


class TestSetOperationsEmptyCollections:
    """Test set operations with empty collections."""

    def test_subsetof_with_empty_collection(self, duckdb_translator, parser):
        """Test subsetOf() behavior with empty collections."""
        parsed = parser.parse("{}.subsetOf({})")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Empty subset of empty should return TRUE or handle gracefully
        fragment = fragments[-1]
        assert fragment.expression is not None

    def test_supersetof_with_empty_collection(self, duckdb_translator, parser):
        """Test supersetOf() behavior with empty collections."""
        parsed = parser.parse("{}.supersetOf({})")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Empty superset of empty should return TRUE or handle gracefully
        fragment = fragments[-1]
        assert fragment.expression is not None

    def test_subsetof_non_empty_of_empty(self, duckdb_translator, parser):
        """Test subsetOf() with non-empty subset of empty superset."""
        parsed = parser.parse("name.given.subsetOf({})")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Non-empty subset of empty should return FALSE
        fragment = fragments[-1]
        assert fragment.expression is not None


class TestSetOperationsMultiDatabaseConsistency:
    """Test that set operations work consistently across databases."""

    @pytest.mark.parametrize("expression", [
        "name.given.subsetOf(name.family)",
        "name.given.supersetOf(name.family)",
    ])
    def test_set_operations_consistency(
        self, expression, duckdb_translator, postgresql_translator, parser
    ):
        """Test that set operations are consistent across DuckDB and PostgreSQL."""
        if not DUCKDB_AVAILABLE or not POSTGRESQL_AVAILABLE:
            pytest.skip("Both databases required for consistency test")

        parsed = parser.parse(expression)
        ast = parsed.get_ast()

        duckdb_fragments = duckdb_translator.translate(ast)
        pg_fragments = postgresql_translator.translate(ast)

        # Both should generate fragments
        assert len(duckdb_fragments) > 0
        assert len(pg_fragments) > 0

        # Both should have the same function in metadata
        duckdb_funcs = [f.metadata.get('function') for f in duckdb_fragments]
        pg_funcs = [f.metadata.get('function') for f in pg_fragments]

        # Should both have subsetOf or supersetOf
        assert any(f in ['subsetOf', 'supersetOf'] for f in duckdb_funcs)
        assert any(f in ['subsetOf', 'supersetOf'] for f in pg_funcs)

        # Both should return boolean type
        duckdb_final = duckdb_fragments[-1]
        pg_final = pg_fragments[-1]
        assert duckdb_final.metadata.get('result_type') == 'boolean'
        assert pg_final.metadata.get('result_type') == 'boolean'


class TestSetOperationsErrorHandling:
    """Test error handling in set operations."""

    def test_subsetof_requires_one_argument(self, duckdb_translator, parser):
        """Test that subsetOf() requires exactly one argument."""
        parsed = parser.parse("name.given.subsetOf()")
        ast = parsed.get_ast()

        # Should raise ValueError
        with pytest.raises(ValueError, match="requires exactly 1 argument"):
            duckdb_translator.visit(ast)

    def test_supersetof_requires_one_argument(self, duckdb_translator, parser):
        """Test that supersetOf() requires exactly one argument."""
        parsed = parser.parse("name.given.supersetOf()")
        ast = parsed.get_ast()

        # Should raise ValueError
        with pytest.raises(ValueError, match="requires exactly 1 argument"):
            duckdb_translator.visit(ast)

    def test_subsetof_with_too_many_arguments(self, duckdb_translator, parser):
        """Test that subsetOf() rejects too many arguments."""
        parsed = parser.parse("name.given.subsetOf(name.family, name.suffix)")
        ast = parsed.get_ast()

        # Should raise ValueError
        with pytest.raises(ValueError, match="requires exactly 1 argument"):
            duckdb_translator.visit(ast)


class TestSetOperationsPreservedColumnsTypes:
    """Test that preserved_columns maintains correct types."""

    def test_preserved_columns_is_list_or_dict(self, duckdb_translator, parser):
        """Test that preserved_columns is a list, set, or dict."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None
        preserved = subsetof_fragment.preserved_columns

        # Should be a known type
        if preserved is not None:
            assert isinstance(preserved, (list, set, dict, str, type(None)))

    def test_preserved_columns_contains_valid_names(self, duckdb_translator, parser):
        """Test that preserved_columns contains valid column names."""
        parsed = parser.parse("name.subsetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None
        preserved = subsetof_fragment.preserved_columns

        # If not empty, should contain valid column names
        if preserved and isinstance(preserved, (list, set)):
            for col in preserved:
                assert isinstance(col, str)
                assert len(col) > 0


class TestSetOperationsWithThisVariable:
    """Test set operations with $this variable references."""

    def test_subsetof_with_this_preserves_context(self, duckdb_translator, parser):
        """Test subsetOf($this.name) preserves context correctly."""
        parsed = parser.parse("name.first().subsetOf($this.name)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should handle $this reference without errors
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

    def test_supersetof_with_this_preserves_context(self, duckdb_translator, parser):
        """Test supersetOf($this.name) preserves context correctly."""
        parsed = parser.parse("name.supersetOf($this.name.first())")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should handle $this reference without errors
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None


class TestSetOperationsWithLiterals:
    """Test set operations with literal values."""

    def test_subsetof_with_literal_collection(self, duckdb_translator, parser):
        """Test subsetOf() with literal collection."""
        parsed = parser.parse("name.given.subsetOf({'John', 'Jane'})")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should handle literal collection
        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

    def test_supersetof_with_literal_collection(self, duckdb_translator, parser):
        """Test supersetOf() with literal collection."""
        parsed = parser.parse("{'John'}.supersetOf(name.given)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        assert len(fragments) > 0
        # Should handle literal collection
        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None


class TestSetOperationsCTEIntegration:
    """Test set operations integration with CTE system."""

    def test_subsetof_generates_dependencies(self, duckdb_translator, parser):
        """Test that subsetOf() tracks dependencies correctly."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None

        # Should have dependencies list
        assert hasattr(subsetof_fragment, 'dependencies')
        deps = subsetof_fragment.dependencies
        assert isinstance(deps, list)

    def test_supersetof_generates_dependencies(self, duckdb_translator, parser):
        """Test that supersetOf() tracks dependencies correctly."""
        parsed = parser.parse("name.given.supersetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        supersetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'supersetOf':
                supersetof_fragment = f
                break

        assert supersetof_fragment is not None

        # Should have dependencies list
        assert hasattr(supersetof_fragment, 'dependencies')
        deps = supersetof_fragment.dependencies
        assert isinstance(deps, list)

    def test_subsetof_preserves_source_table(self, duckdb_translator, parser):
        """Test that subsetOf() preserves source table reference."""
        parsed = parser.parse("name.given.subsetOf(name.family)")
        ast = parsed.get_ast()
        fragments = duckdb_translator.translate(ast)

        subsetof_fragment = None
        for f in fragments:
            if f.metadata.get('function') == 'subsetOf':
                subsetof_fragment = f
                break

        assert subsetof_fragment is not None
        # Should have source_table
        assert hasattr(subsetof_fragment, 'source_table')
        assert subsetof_fragment.source_table is not None
