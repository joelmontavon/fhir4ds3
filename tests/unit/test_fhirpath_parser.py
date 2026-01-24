
import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser, FHIRPathExpression
from fhir4ds.fhirpath.exceptions import FHIRPathParseError

def test_simple_path_expression():
    """Tests parsing of a simple FHIRPath expression."""
    parser = FHIRPathParser()
    expression = "Patient.name.given"
    result = parser.parse(expression)
    assert isinstance(result, FHIRPathExpression)
    assert result.get_path_components() == ["Patient", "name", "given"]

def test_path_with_function():
    """Tests parsing of a FHIRPath expression with a function."""
    parser = FHIRPathParser()
    expression = "Patient.telecom.first()"
    result = parser.parse(expression)
    assert "first()" in result.get_functions()

def test_path_with_where_clause():
    """Tests parsing of a FHIRPath expression with a where clause."""
    parser = FHIRPathParser()
    expression = "Patient.contact.where(relationship.coding.code = 'EP')"
    result = parser.parse(expression)
    assert "where()" in result.get_functions()

def test_invalid_expression_syntax():
    """Tests that an invalid expression raises a parse error."""
    parser = FHIRPathParser()
    with pytest.raises(FHIRPathParseError):
        parser.parse("Patient..name")

def test_empty_expression():
    """Tests that an empty expression raises a parse error."""
    parser = FHIRPathParser()
    with pytest.raises(FHIRPathParseError):
        parser.parse("")

def test_parser_statistics():
    """Tests that the parser tracks usage statistics."""
    parser = FHIRPathParser()
    parser.parse("Patient.id")
    parser.parse("Observation.value")
    stats = parser.get_statistics()
    assert stats["parse_count"] == 2
