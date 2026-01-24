
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

def get_official_tests_path():
    return Path(__file__).parent / "official_tests.xml"

def parse_fhirpath_tests():
    """Parses the official FHIRPath tests XML file."""
    tree = ET.parse(get_official_tests_path())
    root = tree.getroot()
    tests = []
    for group in root.findall("group"):
        for test in group.findall("test"):
            expression_element = test.find("expression")
            test_data = {
                "name": test.get("name"),
                "expression": expression_element.text if expression_element is not None else "",
                "inputfile": test.get("inputfile"),
                "outputs": [],
                "invalid": expression_element.get("invalid") if expression_element is not None else None,
                "predicate": test.get("predicate"),
            }
            for output in test.findall("output"):
                # Value can be in 'value' attribute OR in text content
                value = output.get("value")
                if value is None and output.text:
                    value = output.text.strip()
                test_data["outputs"].append({
                    "type": output.get("type"),
                    "value": value,
                })
            tests.append(test_data)
    return tests

class TestFHIRPathXMLParser:
    def test_parsing_official_xml(self):
        """Tests that the FHIRPath XML test file can be parsed."""
        tests = parse_fhirpath_tests()
        assert len(tests) > 0, "No tests were parsed from the XML file."
        
        # Check the structure of the first test
        first_test = tests[0]
        assert "name" in first_test
        assert "expression" in first_test
        assert "outputs" in first_test
        assert "invalid" in first_test
        assert "predicate" in first_test
        assert isinstance(first_test["outputs"], list)

    def test_inputfile_extraction(self):
        """Tests that the inputfile attribute is extracted correctly."""
        tests = parse_fhirpath_tests()
        # Find a test that is known to have an inputfile
        test_with_input = next((t for t in tests if t["name"] == "testExtractBirthDate"), None)
        assert test_with_input is not None, "Test 'testExtractBirthDate' not found."
        assert "inputfile" in test_with_input
        assert test_with_input["inputfile"] == "patient-example.xml"
        assert test_with_input["invalid"] is None

    def test_invalid_attribute_extraction(self):
        """Tests that the invalid attribute is extracted correctly."""
        tests = parse_fhirpath_tests()
        semantic_fail = next((t for t in tests if t["name"] == "testSimpleFail"), None)
        assert semantic_fail is not None, "Test 'testSimpleFail' not found."
        assert semantic_fail["invalid"] == "semantic"

    def test_predicate_attribute_extraction(self):
        """Tests that the predicate attribute is extracted correctly."""
        tests = parse_fhirpath_tests()
        predicate_test = next((t for t in tests if t["name"] == "testPatientHasBirthDate"), None)
        assert predicate_test is not None, "Test 'testPatientHasBirthDate' not found."
        assert predicate_test["predicate"] == "true"
