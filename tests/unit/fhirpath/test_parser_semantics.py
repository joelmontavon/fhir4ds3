"""
Unit tests for semantic validation in FHIRPathParser.
"""

import pytest

from fhir4ds.fhirpath.parser import FHIRPathParser, FHIRPathParseError


@pytest.fixture
def parser():
    return FHIRPathParser()


def test_invalid_choice_alias(parser):
    with pytest.raises(FHIRPathParseError):
        parser.parse("Observation.valueQuantity.unit", context={"resourceType": "Observation"})


def test_invalid_identifier_suffix(parser):
    with pytest.raises(FHIRPathParseError):
        parser.parse("name.given1")


def test_invalid_period_property(parser):
    with pytest.raises(FHIRPathParseError):
        parser.parse("(Observation.value as Period).unit", context={"resourceType": "Observation"})


def test_invalid_root_context(parser):
    with pytest.raises(FHIRPathParseError):
        parser.parse("Encounter.name.given", context={"resourceType": "Patient"})


def test_valid_empty_navigation(parser):
    parser.parse("name.suffix", context={"resourceType": "Patient"})


def test_valid_period_navigation(parser):
    parser.parse("Observation.value.as(Period).start", context={"resourceType": "Observation"})


def test_unknown_function_reports_location(parser):
    with pytest.raises(FHIRPathParseError, match=r"Unknown function 'foobar'.*line 1, column"):
        parser.parse("Patient.name.foobar()")


def test_string_literal_addition_with_plus(parser):
    """Test that + operator supports string concatenation per FHIRPath spec."""
    # String + String should concatenate
    result = parser.parse("'abc' + 'def'")
    assert result.is_valid()

    # String + String with spaces
    result = parser.parse("'hello' + ' ' + 'world'")
    assert result.is_valid()

    # Multiple string concatenation
    result = parser.parse("'a' + 'b' + 'c'")
    assert result.is_valid()


def test_absolute_path_typo_suggests_alternative(parser):
    with pytest.raises(FHIRPathParseError, match=r"Unknown element 'birthDte'.*Patient.*Did you mean: birthDate"):
        parser.parse("Patient.birthDte")


def test_relative_path_typo_in_context(parser):
    with pytest.raises(FHIRPathParseError, match=r"Unknown element 'givn'.*HumanName"):
        parser.parse("name.givn", context={"resourceType": "Patient"})


def test_escaped_identifier_valid_path(parser):
    parser.parse("name.`given`", context={"resourceType": "Patient"})


def test_escaped_identifier_invalid_path(parser):
    with pytest.raises(FHIRPathParseError, match=r"Unknown element 'givn'.*HumanName"):
        parser.parse("name.`givn`", context={"resourceType": "Patient"})


class TestStringFunctionArgumentValidation:
    """SP-110-FIX-014: Test that string functions reject integer arguments"""

    def test_contains_with_integer_argument_rejected(self, parser):
        """contains() should reject integer literal arguments"""
        with pytest.raises(FHIRPathParseError, match=r"Function contains.*requires a string argument, got integer"):
            parser.parse("name.family.contains(10)")

    def test_contains_with_string_argument_accepted(self, parser):
        """contains() should accept string literal arguments"""
        # Should not raise
        parser.parse("name.family.contains('Smith')")

    def test_startswith_with_integer_argument_rejected(self, parser):
        """startsWith() should reject integer literal arguments"""
        with pytest.raises(FHIRPathParseError, match=r"Function startsWith.*requires a string argument, got integer"):
            parser.parse("name.family.startsWith(123)")

    def test_startswith_with_string_argument_accepted(self, parser):
        """startsWith() should accept string literal arguments"""
        # Should not raise
        parser.parse("name.family.startsWith('Mc')")

    def test_endswith_with_integer_argument_rejected(self, parser):
        """endsWith() should reject integer literal arguments"""
        with pytest.raises(FHIRPathParseError, match=r"Function endsWith.*requires a string argument, got integer"):
            parser.parse("name.family.endsWith(456)")

    def test_endswith_with_string_argument_accepted(self, parser):
        """endsWith() should accept string literal arguments"""
        # Should not raise
        parser.parse("name.family.endsWith('son')")
