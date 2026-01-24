
import json
from typing import Any, Dict, List

class ViewDefinitionTest:
    """A single test case from a SQL-on-FHIR test file."""

    def __init__(self, test_data: Dict[str, Any]):
        self.title: str = test_data["title"]
        self.tags: List[str] = test_data.get("tags", [])
        self.view: Dict[str, Any] = test_data["view"]
        self.expect: List[Dict[str, Any]] = test_data.get("expect")
        self.expect_columns: List[str] | None = test_data.get("expectColumns")


class ViewDefinitionTestFile:
    """Represents a single SQL-on-FHIR test file."""

    def __init__(self, file_path: str):
        with open(file_path, "r") as f:
            test_file_data = json.load(f)

        self.title: str = test_file_data["title"]
        self.description: str = test_file_data.get("description")
        self.fhir_version: List[str] = test_file_data.get("fhirVersion", [])
        self.resources: List[Dict[str, Any]] = test_file_data["resources"]
        self.tests: List[ViewDefinitionTest] = [
            ViewDefinitionTest(test) for test in test_file_data["tests"]
        ]

def load_test_file(file_path: str) -> ViewDefinitionTestFile:
    """Loads a SQL-on-FHIR test file."""
    return ViewDefinitionTestFile(file_path)
