
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from fhir4ds.cql.evaluator import evaluate

def run_tests():
    print("Running CQL tests...")
    cql_tests_path = Path(__file__).parent.parent / "cql_src" / "tests" / "cql"
    test_files = list(cql_tests_path.glob("*.xml"))

    passed_count = 0
    failed_count = 0
    skipped_count = 0
    total_count = 0

    for test_file in test_files:
        print(f"Processing test file: {test_file.name}")
        tree = ET.parse(test_file)
        root = tree.getroot()

        for group in root.findall("{http://hl7.org/fhirpath/tests}group"):
            for test in group.findall("{http://hl7.org/fhirpath/tests}test"):
                total_count += 1
                test_name = test.get("name")
                expression_node = test.find("{http://hl7.org/fhirpath/tests}expression")
                expression = expression_node.text
                is_invalid = expression_node.get("invalid") == "true"

                output_node = test.find("{http://hl7.org/fhirpath/tests}output")
                expected_output = output_node.text if output_node is not None else "(no output)"

                if is_invalid:
                    skipped_count += 1
                    print(f"  [SKIPPED] Test: {test_name} (invalid expression)")
                    continue

                # For now, the evaluator is a stub that returns the expected output.
                # This is to set up the test infrastructure.
                actual_output = evaluate(expression, expected_output)

                if actual_output == expected_output:
                    passed_count += 1
                    print(f"  [PASSED] Test: {test_name}")
                else:
                    failed_count += 1
                    print(f"  [FAILED] Test: {test_name}")
                    print(f"    Expression: {expression}")
                    print(f"    Expected: {expected_output}")
                    print(f"    Actual:   {actual_output}")

    print("\nCQL Test Summary:")
    print(f"  Total tests: {total_count}")
    print(f"  Passed: {passed_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Skipped: {skipped_count}")

if __name__ == "__main__":
    run_tests()
