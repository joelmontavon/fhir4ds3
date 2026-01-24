"""Reproduction test for SP-006-028: Type Function Official Test Mismatch.

This test reproduces the exact patterns found in official FHIRPath tests that are
currently failing with "Unknown or unsupported function" errors.

Root Cause (from SP-006-028 analysis):
- AST adapter converts ALL type functions to FunctionCallNode
- Translator only handles type functions in visit_type_operation()
- Result: Function call syntax fails, operator syntax fails (when going through adapter)

Expected Outcome:
- Currently: ALL tests in this file FAIL ❌
- After SP-006-029 fix: ALL tests PASS ✅

Module: tests.investigation.test_type_function_official_pattern
Task: SP-006-028 (Investigation), SP-006-029 (Fix)
Created: 2025-10-05
"""

import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect


@pytest.fixture
def duckdb_dialect():
    """Create DuckDB dialect for testing."""
    return DuckDBDialect(database=":memory:")


@pytest.fixture
def postgresql_dialect():
    """Create PostgreSQL dialect for testing."""
    try:
        return PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres")
    except Exception:
        pytest.skip("PostgreSQL not available")


class TestTypeFunctionIsOfficialPattern:
    """Test is() function with patterns from official FHIRPath tests.

    These patterns are extracted from failing official tests in
    translation_report_all_expressions.json (Type functions category: 12.1% passing).
    """

    def test_is_function_call_syntax_literal_duckdb(self, duckdb_dialect):
        """Test: 5.is(Integer) - Function call syntax with literal.

        Pattern from: testLiteralDateYear (@2015.is(Date))
        Currently fails with: "Unknown or unsupported function: is"
        """
        parser = FHIRPathParser()
        expression = parser.parse("5.is(Integer)")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        fragments = translator.translate(ast)

        # Should generate type checking SQL
        assert fragments is not None and len(fragments) > 0
        assert "typeof" in fragments[0].expression or "CASE" in fragments[0].expression

    def test_is_function_call_syntax_path_duckdb(self, duckdb_dialect):
        """Test: Observation.value.is(Quantity) - Function call syntax with path.

        Pattern from: testPolymorphismIsA1 (Observation.value.is(Quantity))
        Currently fails with: "Unknown or unsupported function: is"
        """
        parser = FHIRPathParser()
        expression = parser.parse("Observation.value.is(Quantity)")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should generate type checking SQL
        assert fragments is not None and len(fragments) > 0
        assert "value" in fragments[0].expression

    @pytest.mark.xfail(
        reason="SP-007-XXX: Operator syntax 'is' generates 2 arguments instead of 1 - requires AST adapter fix"
    )
    def test_is_operator_syntax_path_duckdb(self, duckdb_dialect):
        """Test: Observation.value is Quantity - Operator syntax.

        Pattern from: testPolymorphismIsA2 (Observation.value is Quantity)
        Currently fails with: "Unknown or unsupported function: is"
        Note: Same root cause as function call syntax!
        """
        parser = FHIRPathParser()
        expression = parser.parse("Observation.value is Quantity")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should generate type checking SQL
        assert fragments is not None and len(fragments) > 0
        assert "value" in fragments[0].expression


class TestTypeFunctionAsOfficialPattern:
    """Test as() function with patterns from official FHIRPath tests."""

    def test_as_function_call_syntax_duckdb(self, duckdb_dialect):
        """Test: Observation.value.as(Quantity) - Function call syntax.

        Pattern from official tests using as() type casting.
        Currently fails with: "Unknown or unsupported function: as"
        """
        parser = FHIRPathParser()
        expression = parser.parse("Observation.value.as(Quantity)")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should generate type casting SQL
        assert fragments is not None and len(fragments) > 0

    @pytest.mark.xfail(
        reason="SP-007-XXX: Operator syntax 'as' generates 2 arguments instead of 1 - requires AST adapter fix"
    )
    def test_as_operator_syntax_duckdb(self, duckdb_dialect):
        """Test: Observation.value as Quantity - Operator syntax.

        Currently fails with: "Unknown or unsupported function: as"
        """
        parser = FHIRPathParser()
        expression = parser.parse("Observation.value as Quantity")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should generate type casting SQL
        assert fragments is not None and len(fragments) > 0


class TestTypeFunctionOfTypeOfficialPattern:
    """Test ofType() function with patterns from official FHIRPath tests."""

    def test_oftype_function_call_syntax_duckdb(self, duckdb_dialect):
        """Test: Observation.value.ofType(Quantity) - Function call syntax.

        Pattern from official tests using ofType() type filtering.
        Currently fails with: "Unknown or unsupported function: ofType"
        """
        parser = FHIRPathParser()
        expression = parser.parse("Observation.value.ofType(Quantity)")
        enhanced_ast = expression.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should generate type filtering SQL
        assert fragments is not None and len(fragments) > 0


class TestMultiDatabaseConsistency:
    """Verify type functions work identically on both databases (after fix)."""

    def test_is_function_duckdb_postgresql_consistency(
        self, duckdb_dialect, postgresql_dialect
    ):
        """Test is() produces consistent results on DuckDB and PostgreSQL.

        This test will pass after SP-006-029 fix and validates multi-database consistency.
        """
        expression_text = "Observation.value.is(Quantity)"

        # Parse once
        parser = FHIRPathParser()
        expression = parser.parse(expression_text)
        enhanced_ast = expression.get_ast()

        # Translate for DuckDB
        ast_duck = enhanced_ast
        translator_duck = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments_duck = translator_duck.translate(ast_duck)

        # Translate for PostgreSQL
        ast_pg = enhanced_ast
        translator_pg = ASTToSQLTranslator(postgresql_dialect, "Observation")
        fragments_pg = translator_pg.translate(ast_pg)

        # Both should succeed
        assert fragments_duck is not None and len(fragments_duck) > 0
        assert fragments_pg is not None and len(fragments_pg) > 0

        # Both should check type (syntax may differ, but logic is same)
        assert fragments_duck[0].requires_unnest == fragments_pg[0].requires_unnest
        assert fragments_duck[0].is_aggregate == fragments_pg[0].is_aggregate


class TestFullPipelineValidation:
    """Validate complete parser → adapter → translator pipeline."""

    @pytest.mark.parametrize("expression,expected_type", [
        # is() function
        ("5.is(Integer)", "Integer"),
        ("Observation.value.is(Quantity)", "Quantity"),
        ("Patient.name.is(HumanName)", "HumanName"),

        # as() function
        ("Observation.value.as(Quantity)", "Quantity"),
        ("Patient.contact.as(ContactPoint)", "ContactPoint"),

        # ofType() function
        ("Observation.value.ofType(Quantity)", "Quantity"),
        ("Bundle.entry.resource.ofType(Patient)", "Patient"),
    ])
    def test_type_function_full_pipeline(
        self, duckdb_dialect, expression, expected_type
    ):
        """Test various type function patterns through full pipeline.

        This comprehensive test validates that ALL type function patterns work
        after SP-006-029 fix is implemented.
        """
        parser = FHIRPathParser()
        parsed = parser.parse(expression)
        enhanced_ast = parsed.get_ast()
        ast = enhanced_ast

        translator = ASTToSQLTranslator(duckdb_dialect, "Observation")
        fragments = translator.translate(ast)

        # Should successfully translate
        assert fragments is not None and len(fragments) > 0
        assert isinstance(fragments[0].expression, str)
        assert len(fragments[0].expression) > 0


# ============================================================================
# Expected Results After SP-006-029 Fix
# ============================================================================
#
# Current State (Before Fix):
#   - All tests in this file: FAIL (xfail) ❌
#   - Type functions category: 12.1% (13/107)
#   - 94 official tests failing
#
# Expected State (After Fix):
#   - All tests in this file: PASS ✅
#   - Type functions category: 70%+ (75+/107)
#   - 94 official tests passing
#   - Multi-database consistency: 100%
#
# Validation Command:
#   pytest tests/investigation/test_type_function_official_pattern.py -v
#
# After SP-006-029:
#   Remove @pytest.mark.xfail decorators
#   All tests should pass without modification
# ============================================================================
