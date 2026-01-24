"""
Integration Test for Parser-Translator Compatibility

Ensures that the direct workflow is used when integrating parser and translator:
Parser → Translator (direct EnhancedASTNode translation)

SP-023-006 enhanced EnhancedASTNode.accept() to fully support the visitor pattern,
eliminating the need for an intermediate AST adapter conversion step.

Task: SP-007-021 (original), SP-023-006 (enhanced)
Created: 2025-10-09
Updated: 2025-12-22 (SP-023-006 Phase 4 - Direct translation)
"""

import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect


class TestParserTranslatorWorkflow:
    """Test that parser-translator workflow works directly with EnhancedASTNode"""

    def test_direct_translation_works(self):
        """Test the direct workflow: Parser → Translator (no adapter needed)"""
        # Initialize components
        parser = FHIRPathParser()
        translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

        # Test expressions
        test_expressions = [
            "Patient.name",
            "Patient.name.where(use = 'official')",
            "true",
            "42",
            "'hello'",
            "Patient.name.family",
        ]

        for expression in test_expressions:
            # Parse expression
            parsed = parser.parse(expression)
            enhanced_ast = parsed.get_ast()

            # Translate directly (SP-023-006: EnhancedASTNode.accept() handles dispatch)
            fragments = translator.translate(enhanced_ast)

            # Verify we got results
            assert len(fragments) > 0, f"Expected SQL fragments for expression: {expression}"

    def test_direct_translation_with_duckdb(self):
        """Test direct translation with DuckDB dialect"""
        parser = FHIRPathParser()
        translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

        expressions = [
            "Patient.name.first()",
            "Patient.active = true",
            "Patient.telecom.where(system = 'phone')",
        ]

        for expression in expressions:
            parsed = parser.parse(expression)
            enhanced_ast = parsed.get_ast()
            fragments = translator.translate(enhanced_ast)
            assert len(fragments) > 0

    def test_direct_translation_with_postgresql(self):
        """Test direct translation with PostgreSQL dialect"""
        parser = FHIRPathParser()
        translator = ASTToSQLTranslator(
            PostgreSQLDialect("postgresql://postgres:postgres@localhost:5432/postgres"),
            "Patient"
        )

        expressions = [
            "Patient.name.first()",
            "Patient.active = true",
            "Patient.telecom.where(system = 'phone')",
        ]

        for expression in expressions:
            parsed = parser.parse(expression)
            enhanced_ast = parsed.get_ast()
            fragments = translator.translate(enhanced_ast)
            assert len(fragments) > 0

    def test_multiple_expression_types_direct(self):
        """Test direct translation handles all major expression types"""
        parser = FHIRPathParser()
        translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

        expressions = {
            "literal": ["true", "false", "42", "'test'"],
            "path": ["Patient.name", "Patient.name.family", "Patient.contact.telecom.system"],
            "function": ["Patient.name.exists()", "Patient.name.count()", "Patient.name.first()"],
            "operator": [
                "Patient.active = true",
                "Patient.name.family = 'Smith'",
                "1 | 2"
            ],
            "filter": ["Patient.name.where(use = 'official')"],
        }

        for expr_type, expr_list in expressions.items():
            for expression in expr_list:
                # Parse
                parsed = parser.parse(expression)
                enhanced_ast = parsed.get_ast()

                # Translate directly (no adapter needed with SP-023-006)
                fragments = translator.translate(enhanced_ast)

                # Verify
                assert len(fragments) > 0, f"Failed for {expr_type} expression: {expression}"
