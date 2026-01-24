"""Tests covering comment handling edge cases in the FHIRPath parser."""

import pytest

from fhir4ds.fhirpath.exceptions import FHIRPathParseError
from fhir4ds.fhirpath.parser import FHIRPathParser


@pytest.fixture
def parser() -> FHIRPathParser:
    return FHIRPathParser()


def test_multiline_comment_with_special_characters(parser: FHIRPathParser) -> None:
    expression = "Patient.name /* comment with */ stars, slashes /* and newline\ncontent */.first()"
    parsed = parser.parse(expression)
    assert parsed.is_valid()


def test_nested_block_comment_rejected_with_location(parser: FHIRPathParser) -> None:
    expression = "1 /* outer /* inner */ still outer */"
    with pytest.raises(FHIRPathParseError, match=r"Nested block comments.*line 1, column 12"):
        parser.parse(expression)


def test_unexpected_terminator_reports_position(parser: FHIRPathParser) -> None:
    expression = "value */ stray terminator"
    with pytest.raises(FHIRPathParseError, match=r"Unexpected block comment terminator at line 1, column 7"):
        parser.parse(expression)


def test_unterminated_block_comment_reports_start(parser: FHIRPathParser) -> None:
    expression = "Patient.name /* missing end"
    with pytest.raises(FHIRPathParseError, match=r"Unterminated block comment starting at line 1, column 14"):
        parser.parse(expression)
