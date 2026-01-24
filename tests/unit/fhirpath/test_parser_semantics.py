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


def test_string_literal_addition_is_rejected(parser):
    with pytest.raises(FHIRPathParseError, match=r"Operator '\+' does not support string literals"):
        parser.parse("'abc' + 5")


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
