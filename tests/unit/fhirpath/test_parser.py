"""FHIRPath parser regression tests for Phase 3 validation rules."""

from __future__ import annotations

import pytest

from fhir4ds.fhirpath.exceptions import FHIRPathParseError
from fhir4ds.fhirpath.parser import FHIRPathParser


def test_parse_rejects_consecutive_dots():
    """Syntactically invalid expressions with consecutive dots should raise."""
    parser = FHIRPathParser()
    with pytest.raises(FHIRPathParseError, match="consecutive dots not allowed"):
        parser.parse("Patient..name")


def test_parse_enforces_context_resource_root():
    """Semantic validator must reject mismatched resource contexts."""
    parser = FHIRPathParser()
    with pytest.raises(FHIRPathParseError, match="Expression root 'Observation' is invalid"):
        parser.parse("Observation.value", context={"resourceType": "Patient"})


def test_parse_extracts_functions_and_paths():
    """The enhanced parser should expose function names for downstream planning."""
    parser = FHIRPathParser()
    parsed = parser.parse("Patient.name.where(use='official').first()")

    functions = parsed.get_functions()
    assert "where()" in functions
    assert "first()" in functions

    components = parsed.get_path_components()
    assert "Patient" in components
    assert "name" in components


def test_parse_returns_ast_with_metadata():
    """AST nodes should include metadata for downstream translation."""
    parser = FHIRPathParser()
    parsed = parser.parse("Patient.name")
    ast = parsed.get_ast()

    assert ast is not None
    assert getattr(ast, "metadata", None) is not None


def test_parse_rejects_unterminated_block_comment():
    """Block comments must include a closing terminator."""
    parser = FHIRPathParser()
    with pytest.raises(FHIRPathParseError, match="Unterminated block comment"):
        parser.parse("2 + 2 /* unfinished")


def test_parse_allows_comment_markers_inside_strings():
    """Comment delimiters appearing inside strings should not trigger validation."""
    parser = FHIRPathParser()
    expression = "'http://example.org/fhir/ValueSet/*notacomment*/resource'"
    parsed = parser.parse(expression)
    assert parsed.is_valid()


def test_parse_allows_trailing_single_line_comment():
    """Single-line comments at the end of an expression should be ignored."""
    parser = FHIRPathParser()
    parsed = parser.parse("2 + 2 // ignore remainder")
    assert parsed.is_valid()


def test_parse_union_operator_is_recognized():
    """Parser must surface the union operator so downstream translation can succeed."""
    parser = FHIRPathParser()
    parsed = parser.parse("1 | 2")

    ast = parsed.get_ast()
    assert ast is not None
    assert ast.node_type == "UnionExpression"

    fhirpath_ast = ast
    assert fhirpath_ast.operator == "|"
    assert fhirpath_ast.operator_type == "union"
    assert len(fhirpath_ast.children) == 2
