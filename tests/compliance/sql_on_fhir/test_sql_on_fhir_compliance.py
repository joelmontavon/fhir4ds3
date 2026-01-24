
import glob
import os
import pytest
import json
from fhir4ds.sql import SQLGenerator
from .viewdefinition_parser import load_test_file, ViewDefinitionTest, ViewDefinitionTestFile

# Get the absolute path to the official_tests/tests directory
TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "official_tests", "tests")

# Find all JSON test files
TEST_FILES = glob.glob(os.path.join(TEST_FILES_DIR, "*.json"))

def load_all_test_cases():
    """Loads all test cases from all test files."""
    test_cases = []
    for file_path in TEST_FILES:
        test_file = load_test_file(file_path)
        for test_case in test_file.tests:
            test_cases.append(pytest.param(test_case, test_file, id=f"{test_file.title}-{test_case.title}"))
    return test_cases

def result_to_dict(result, columns):
    """Converts a single query result row to a dictionary."""
    return {col[0]: val for col, val in zip(columns, result)}

def compare_results(actual, expected):
    """Compares two lists of dictionaries, ignoring order."""
    if expected is None:
        return actual is None
    if len(actual) != len(expected):
        return False
    for expected_row in expected:
        if expected_row not in actual:
            return False
    return True

@pytest.mark.parametrize("dialect", ["duckdb", "postgresql"])
@pytest.mark.parametrize("test_case, test_file", load_all_test_cases())
@pytest.mark.usefixtures("duckdb_conn", "postgresql_conn")
def test_sql_on_fhir_compliance(request, test_case: ViewDefinitionTest, test_file: ViewDefinitionTestFile, dialect):
    """Main test function for SQL-on-FHIR compliance."""
    if dialect == "duckdb":
        conn = request.getfixturevalue("duckdb_conn")
        if not conn:
            pytest.skip("DuckDB connection not available")
    elif dialect == "postgresql":
        conn = request.getfixturevalue("postgresql_conn")
        if not conn:
            pytest.skip("PostgreSQL connection not available")

    # 1. Create tables and load data
    for resource_type in set(r["resourceType"] for r in test_file.resources):
        resources = [r for r in test_file.resources if r["resourceType"] == resource_type]
        conn.execute(f"CREATE OR REPLACE TABLE {resource_type} (resource JSON)")
        for resource in resources:
            conn.execute(f"INSERT INTO {resource_type} VALUES ('{json.dumps(resource)}')")

    # 2. Translate test_case.view to SQL
    sql_generator = SQLGenerator(dialect=dialect)
    try:
        sql_query = sql_generator.generate_sql(test_case.view)
    except Exception as e:
        pytest.fail(f"SQL generation failed: {e}")

    # 3. Execute the SQL
    try:
        result_set = conn.execute(sql_query)
        columns = result_set.description
        actual_results = [result_to_dict(row, columns) for row in result_set.fetchall()]
    except Exception as e:
        pytest.fail(f"SQL execution failed: {e}\nQuery: {sql_query}")

    # 4. Compare with test_case.expect
    assert compare_results(actual_results, test_case.expect), \
        f"Results do not match expected output.\nExpected: {test_case.expect}\nActual: {actual_results}"

    # 5. Compare with test_case.expect_columns
    if test_case.expect_columns:
        actual_columns = [col[0] for col in columns]
        assert actual_columns == test_case.expect_columns, \
            f"Column names do not match expected output.\nExpected: {test_case.expect_columns}\nActual: {actual_columns}"
