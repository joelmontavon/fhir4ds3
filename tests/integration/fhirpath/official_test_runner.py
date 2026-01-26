"""
Enhanced Official FHIRPath Test Runner

Integrates enhanced FHIRPath components with official test suite execution,
providing automated compliance measurement and detailed reporting.
"""

import time
import json
import os
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import pytest
import xml.etree.ElementTree as ET

import logging

from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.exceptions import FHIRPathParseError
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.cte import CTEBuilder, CTEAssembler
from fhir4ds.fhirpath.types.type_registry import TypeRegistry
from fhir4ds.dialects.duckdb import DuckDBDialect
from fhir4ds.dialects.postgresql import PostgreSQLDialect
from tests.compliance.fhirpath.test_parser import parse_fhirpath_tests

# Set up logger for debugging
logger = logging.getLogger(__name__)

# IMPORTANT: SQL-only execution strategy for official tests
# All tests now use SQL translation (production path) to measure real compliance
# No Python evaluator fallback - we test what we ship


@dataclass
class TestResult:
    """Individual test result with enhanced metadata"""
    name: str
    expression: str
    expected_outputs: List[Dict[str, Any]]
    actual_result: Any
    passed: bool
    execution_time_ms: float
    error_message: Optional[str] = None
    parser_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceReport:
    """Comprehensive compliance measurement report"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    compliance_percentage: float
    execution_time_total_ms: float
    execution_time_average_ms: float
    parser_type: str
    database_type: str
    timestamp: str
    test_categories: Dict[str, Dict[str, int]]
    performance_metrics: Dict[str, float]
    failed_test_analysis: List[Dict[str, Any]]


class EnhancedOfficialTestRunner:
    """
    Enhanced Official Test Runner with Compliance Measurement

    Executes official FHIRPath R4 test cases with enhanced parser integration,
    automated compliance tracking, and comprehensive reporting.

    SQL-Only Execution Strategy (SP-018-001):
    - Uses SQL translation exclusively (production path)
    - Tests measure actual production capabilities
    - No Python evaluator fallback - aligned with population-first architecture

    This SQL-only approach ensures:
    1. Compliance metrics reflect production SQL translator capabilities
    2. Testing aligns with "population-first" architectural principle
    3. Development focuses on the production code path only
    """

    def __init__(self, database_type: str = "duckdb", postgresql_conn_string: Optional[str] = None):
        """Initialize the enhanced test runner"""
        self.database_type = database_type
        self.parser = FHIRPathParser(database_type)
        self.test_results: List[TestResult] = []
        self.compliance_history: List[ComplianceReport] = []
        self._fixtures_root = (
            Path(__file__).resolve().parent.parent.parent / "fixtures" / "sample_fhir_data"
        )
        self._context_cache: Dict[str, Dict[str, Any]] = {}
        self._type_registry = TypeRegistry()  # SP-012-013: For FHIR cardinality
        self._postgresql_conn_string = (
            postgresql_conn_string
            or os.environ.get("FHIR4DS_POSTGRESQL_CONN_STRING")
            or "postgresql://postgres:postgres@localhost:5432/postgres"
        )

    def run_official_tests(self,
                          test_filter: Optional[str] = None,
                          max_tests: Optional[int] = None) -> ComplianceReport:
        """
        Run official FHIRPath tests with enhanced components

        Args:
            test_filter: Optional filter to limit tests (e.g., "arithmetic")
            max_tests: Maximum number of tests to run (for performance testing)

        Returns:
            Comprehensive compliance report
        """
        print(f"Starting enhanced FHIRPath test execution...")
        print(f"Database type: {self.database_type}")
        print(f"Parser type: {type(self.parser).__name__}")

        # Get official test cases
        official_tests = parse_fhirpath_tests()

        # Apply filters
        if test_filter:
            official_tests = [t for t in official_tests if test_filter.lower() in t['name'].lower()]

        if max_tests:
            official_tests = official_tests[:max_tests]

        print(f"Running {len(official_tests)} tests...")

        # Execute tests
        start_time = time.time()
        self.test_results = []

        for i, test_data in enumerate(official_tests):
            if i % 100 == 0:
                print(f"Progress: {i}/{len(official_tests)} tests completed")

            result = self._execute_single_test(test_data)
            self.test_results.append(result)

        total_time = (time.time() - start_time) * 1000

        # Generate compliance report
        report = self._generate_compliance_report(total_time)
        self.compliance_history.append(report)

        return report

    def _execute_single_test(self, test_data: Dict[str, Any]) -> TestResult:
        """Execute a single test case with enhanced metadata collection"""
        start_time = time.time()

        try:
            # Parse and evaluate the expression
            invalid_flag = test_data.get('invalid')
            predicate_flag = test_data.get('predicate')
            context = self._load_test_context(test_data.get('inputfile'))

            # SQL translation only (production path)
            result = self._evaluate_with_translator(
                test_data['expression'],
                context
            )

            # If translator didn't return a result, mark as translator limitation
            if result is None:
                result = {
                    'is_valid': False,
                    'error': 'SQL translator does not yet support this expression',
                    'result': None,
                    'error_type': 'translator_unsupported'
                }

            execution_time = (time.time() - start_time) * 1000

            passed = self._validate_test_result(
                result,
                test_data.get('outputs', []),
                invalid_flag=invalid_flag,
                predicate_flag=predicate_flag,
            )

            error_message = None
            if not passed:
                if invalid_flag:
                    error_message = "Expected semantic failure but expression was accepted."
                elif not test_data.get('outputs', []):
                    error_message = "Expected valid expression with empty result set."
                elif result is None:
                    error_message = "Expression evaluation failed."
                else:
                    error_message = "Unexpected evaluation outcome."

            return TestResult(
                name=test_data['name'],
                expression=test_data['expression'],
                expected_outputs=test_data.get('outputs', []),
                actual_result=result,
                passed=passed,
                execution_time_ms=execution_time,
                error_message=error_message,
                parser_metadata=result.get('parser_metadata') if result else None
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return TestResult(
                name=test_data['name'],
                expression=test_data['expression'],
                expected_outputs=test_data.get('outputs', []),
                actual_result=None,
                passed=False,
                execution_time_ms=execution_time,
                error_message=f"Exception during test execution: {str(e)}"
            )

    def _validate_test_result(
        self,
        actual_result: Any,
        expected_outputs: List[Dict[str, Any]],
        invalid_flag: Optional[str] = None,
        predicate_flag: Optional[str] = None,
    ) -> bool:
        """
        Validate actual test result against expected outputs

        Args:
            actual_result: Result from parser evaluation
            expected_outputs: Expected outputs from official test case
            invalid_flag: Optional invalid indicator from official suite

        Returns:
            True if result matches expected outputs, False otherwise
        """
        # Semantic/invalid expressions must fail to parse/evaluate
        if invalid_flag:
            if actual_result is None:
                return True
            # Check if result is invalid
            if not actual_result.get('is_valid', True):
                # If error_type is specified, it should match the invalid_flag
                error_type = actual_result.get('error_type')
                if error_type:
                    # Map invalid_flag to expected error_type
                    # "syntax" flag expects syntax errors (parse errors are syntax errors)
                    # "semantic" flag expects semantic errors
                    # "execution" flag expects execution errors
                    if error_type == invalid_flag:
                        return True
                    # Treat parser-level errors as acceptable for syntax and semantic expectations
                    if error_type == "parse" and invalid_flag in ("syntax", "semantic"):
                        return True
                    return False
                # No error_type specified - any invalid result is OK
                return True
            return False  # Result is valid but should be invalid

        # Predicate tests evaluate truthiness of the result (non-empty -> True).
        if predicate_flag and predicate_flag.lower() == "true":
            expected_bool = True
            if expected_outputs:
                expected_entry = expected_outputs[0]
                expected_bool = str(expected_entry.get("value")).lower() == "true"

            actual_value = actual_result.get("result") if actual_result else None
            if isinstance(actual_value, list):
                actual_bool = len(actual_value) > 0
            else:
                actual_bool = bool(actual_value)

            return actual_bool == expected_bool

        # Empty expected outputs means the expression should fail to parse/evaluate
        if not expected_outputs:
            if actual_result is None:
                return False
            if not actual_result.get('is_valid', False):
                return False
            result_value = actual_result.get('result')
            if result_value is None:
                return True
            if isinstance(result_value, list):
                return len(result_value) == 0
            return False

        # If parsing completely failed (returned None)
        if actual_result is None:
            # Check if failure was expected
            for expected in expected_outputs:
                if expected.get('error', False) or expected.get('invalid', False):
                    return True  # Failure was expected
            return False  # Unexpected failure

        # If parser returned invalid result
        if not actual_result.get('is_valid', True):
            # Check if failure was expected
            for expected in expected_outputs:
                if expected.get('error', False) or expected.get('invalid', False):
                    return True  # Failure was expected
            return False  # Unexpected failure

        # Parser succeeded - now compare actual vs expected results
        if expected_outputs:
            actual_value = actual_result.get('result')

            # Early collection comparison when result and expectations align
            if isinstance(actual_value, list) and all('value' in item for item in expected_outputs):
                if len(actual_value) == len(expected_outputs):
                    if all(
                        self._values_match(actual_value[idx], expected_outputs[idx].get('value'),
                                           expected_outputs[idx].get('type'))
                        for idx in range(len(expected_outputs))
                    ):
                        return True

            # Compare actual vs expected
            for expected in expected_outputs:
                expected_value = expected.get('value')
                expected_type = expected.get('type')

                # Handle NULL/empty as valid expected outcome (SP-008-008)
                # fhirpathpy returns empty list [] for NULL, we treat it as None
                if actual_value is None or (isinstance(actual_value, list) and len(actual_value) == 0):
                    actual_is_null = True
                else:
                    actual_is_null = False

                # No expected value/type means expecting NULL
                if expected_value is None and expected_type is None:
                    if actual_is_null:
                        return True
                    continue

                # Handle other value comparisons
                if self._values_match(actual_value, expected_value, expected_type):
                    return True

            return False  # No expected output matched

        # Should not reach here, but default to failure for safety
        return False

    def _values_match(self, actual: Any, expected: Any, expected_type: str) -> bool:
        """Compare actual and expected values with type consideration"""
        # Handle NULL
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False

        # fhirpathpy returns results as lists, extract single value if list of 1
        if isinstance(actual, list):
            if len(actual) == 0:
                return expected is None or expected == ""
            elif len(actual) == 1:
                actual = actual[0]
            # else: keep as list for collection comparison

        # Handle booleans
        if expected_type == 'boolean':
            expected_bool = str(expected).lower() == 'true'
            if isinstance(actual, bool):
                return actual == expected_bool
            return str(actual).lower() == str(expected).lower()

        # Handle numbers
        if expected_type in ('integer', 'decimal'):
            try:
                return float(actual) == float(expected)
            except (ValueError, TypeError):
                return False

        # Handle strings
        if expected_type in ('string', 'code', 'date', 'time', 'datetime'):
            actual_str = str(actual)
            expected_str = str(expected)
            if expected_type in ('date', 'time', 'datetime') and expected_str.startswith("@"):
                expected_str = expected_str[1:]
            return actual_str == expected_str

        # Handle collections
        if isinstance(actual, list) and isinstance(expected, str):
            # Expected is a single value, actual is a collection
            # Check if expected is in the collection
            return any(self._values_match(item, expected, expected_type) for item in actual)

        # Default: string comparison
        return str(actual) == str(expected)

    # ------------------------------------------------------------------ #
    # Test input loading helpers
    # ------------------------------------------------------------------ #

    def _load_test_context(self, input_file: Optional[str]) -> Optional[Dict[str, Any]]:
        """Load evaluation context (resource metadata) for a test input file.
        
        SP-024-001: Returns minimal context for context-free expressions (no inputfile)
        to enable evaluation of pure arithmetic expressions like '1 + 1'.
        """
        if not input_file:
            # SP-024-001: Return minimal context for context-free expressions
            # This enables evaluation of pure literals/arithmetic without a resource
            return {"resourceType": "Resource"}

        if input_file in self._context_cache:
            return self._context_cache[input_file]

        file_path = self._fixtures_root / input_file
        if not file_path.exists():
            return None

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            resource_type = self._strip_namespace(root.tag)
            # SP-012-013: Pass resource_type for FHIR cardinality handling
            resource = self._convert_xml_element(root, resource_type=resource_type)
            if isinstance(resource, dict):
                resource.setdefault("resourceType", resource_type)
            self._context_cache[input_file] = resource
            return resource
        except ET.ParseError:
            return None

    def _convert_xml_element(self, element: ET.Element, resource_type: Optional[str] = None) -> Any:
        """Convert FHIR XML element to JSON-compatible structure with FHIR cardinality.

        Args:
            element: XML element to convert
            resource_type: FHIR resource type (e.g., "Patient") for cardinality checking

        Returns:
            JSON-compatible structure (dict, list, or primitive value)
        """
        tag = self._strip_namespace(element.tag)
        children = list(element)

        # Handle primitive attributes (value attribute)
        if not children:
            if "value" in element.attrib:
                return element.attrib["value"]
            if element.text and element.text.strip():
                return element.text.strip()
            return None

        result: Dict[str, Any] = {}

        # Include attributes as regular properties (e.g., url="...")
        for attr_name, attr_value in element.attrib.items():
            if attr_name == "value":
                result["value"] = attr_value
            else:
                result[attr_name] = attr_value

        for child in children:
            child_tag = self._strip_namespace(child.tag)

            # Determine element type for nested cardinality handling
            child_resource_type = resource_type
            if resource_type:
                try:
                    element_type = self._type_registry.get_element_type(resource_type, child_tag)
                    if element_type:
                        child_resource_type = element_type
                except Exception:
                    child_resource_type = resource_type

            child_value = self._convert_xml_element(child, resource_type=child_resource_type)
            if child_value is None:
                continue

            if child_tag in result:
                existing = result[child_tag]
                if not isinstance(existing, list):
                    result[child_tag] = [existing]
                result[child_tag].append(child_value)
            else:
                result[child_tag] = child_value

        # SP-012-013: Apply FHIR cardinality rules to wrap 0..* fields in arrays
        if resource_type and isinstance(result, dict):
            result = self._apply_fhir_cardinality(result, resource_type)

        return result

    def _apply_fhir_cardinality(self, data: Dict[str, Any], resource_type: str) -> Dict[str, Any]:
        """Wrap fields in arrays according to FHIR cardinality (SP-012-013).

        FHIR defines cardinality for each element (0..1, 0..*, 1..1, 1..*).
        Elements with 0..* or 1..* cardinality should always be arrays, even if
        only one element is present.

        Args:
            data: Dictionary of field_name -> value
            resource_type: FHIR resource type (e.g., "Patient")

        Returns:
            Dictionary with array fields properly wrapped
        """
        for field_name, field_value in list(data.items()):  # list() to allow modification
            # Check if this field should be an array according to FHIR spec
            try:
                if self._type_registry.is_array_element(resource_type, field_name):
                    # If value is not already a list, wrap it
                    if not isinstance(field_value, list):
                        data[field_name] = [field_value]
            except Exception:
                # If type registry doesn't have this field, leave as-is
                # (could be a custom extension or unknown resource type)
                pass

        return data

    def _evaluate_with_translator(
        self, expression: str, context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        SQL translation evaluation (production path only).

        This method uses SQL translation exclusively to evaluate FHIRPath expressions.
        No Python fallback - we test what we ship in production.

        Args:
            expression: FHIRPath expression to evaluate
            context: FHIR resource context

        Returns:
            Dictionary with evaluation result or None if translation fails
        """
        if context is None:
            return None

        # SP-012-011/012: Support both DuckDB and PostgreSQL
        database_type_lower = self.database_type.lower()
        if database_type_lower not in ("duckdb", "postgresql"):
            return None

        resource_type = context.get("resourceType")
        if not resource_type:
            return None

        # SQL translation only (production path)
        try:
            parsed_expression = self.parser.parse(expression)
            ast = parsed_expression.get_ast()
            if ast is None:
                # AST conversion failed
                return None

            # Select appropriate dialect based on database_type
            if database_type_lower == "postgresql":
                dialect = PostgreSQLDialect(self._postgresql_conn_string)
            else:
                dialect = DuckDBDialect()

            translator = ASTToSQLTranslator(dialect, resource_type)
            fragments = translator.translate(ast)
            if not fragments:
                # Translation failed
                return None

            # Build CTEs from fragments
            cte_builder = CTEBuilder(dialect)
            ctes = cte_builder.build_cte_chain(fragments)

            # Assemble final SQL query
            cte_assembler = CTEAssembler(dialect)
            query = cte_assembler.assemble_query(ctes)

            rows: List[Any]
            if database_type_lower == "postgresql":
                payload = json.dumps(context)
                dialect.execute_query("CREATE TEMP TABLE resource (id INTEGER, resource JSONB)")
                dialect.execute_query(
                    "INSERT INTO resource VALUES (%s, %s::jsonb)",
                    (1, payload),
                )
                rows = dialect.execute_query(query)
                dialect.execute_query("DROP TABLE resource")
            else:
                conn = dialect.get_connection()
                try:
                    conn.execute("CREATE TEMP TABLE resource (id INTEGER, resource JSON)")
                    conn.execute(
                        "INSERT INTO resource VALUES (1, ?)",
                        (json.dumps(context),)
                    )
                    rows = conn.execute(query).fetchall()
                finally:
                    try:
                        conn.execute("DROP TABLE resource")
                    finally:
                        conn.close()

            # Extract values from result rows
            # CTE queries return all columns, we want the last column (final result)
            # Filter out None values as FHIRPath collections cannot contain nulls
            values = [
                self._normalize_sql_value(row[-1]) 
                for row in rows 
                if row[-1] is not None
            ]
            
            if len(values) == 1 and isinstance(values[0], list):
                values = values[0]

            return {
                "is_valid": True,
                "result": values
            }
        except FHIRPathParseError as exc:
            # Parse errors are real errors
            return {
                "is_valid": False,
                "error": str(exc),
                "result": None,
                "error_type": "parse"
            }
        except Exception as exc:
            # Import here to avoid circular dependency
            from fhir4ds.fhirpath.exceptions import FHIRPathValidationError, FHIRPathEvaluationError

            # Check if this is a validation error (semantic) or evaluation error (execution)
            if isinstance(exc, FHIRPathValidationError):
                return {
                    "is_valid": False,
                    "error": str(exc),
                    "result": None,
                    "error_type": "semantic"
                }
            elif isinstance(exc, FHIRPathEvaluationError):
                return {
                    "is_valid": False,
                    "error": str(exc),
                    "result": None,
                    "error_type": "execution"
                }
            else:
                # SQL translation failed - log details for debugging
                import traceback
                logger.error(f"SQL translation/execution failed for expression: {expression}")
                logger.error(f"Error type: {type(exc).__name__}")
                logger.error(f"Error message: {exc}")
                logger.debug(f"Traceback: {traceback.format_exc()}")

                # Map SQL execution errors to "execution" error type for validation
                # Common SQL error types: BinderException, CatalogException, etc.
                exc_type_name = type(exc).__name__
                sql_execution_errors = {
                    'BinderException', 'CatalogException', 'ConstraintException',
                    'DataException', 'DependencyException', 'IOException',
                    'InterruptedException', 'NumericException', 'OptimizerException',
                    'OutOfWorkMemoryException', 'ParserException', 'PermissionException',
                    'PlannerException', 'SequenceException', 'SerializationException',
                    'StandardException', 'TableNotFoundException', 'TransactionException',
                    'TypeMismatchException', 'VacuumException'
                }

                error_type = "execution" if exc_type_name in sql_execution_errors else exc_type_name

                # Return detailed error information instead of None
                return {
                    'is_valid': False,
                    'error': str(exc),
                    'error_type': error_type,
                    'result': None
                }

    def _is_simple_path_expression(self, expression: str) -> bool:
        """Determine if an expression is a simple identifier path (no functions/operators)."""
        stripped = (expression or "").strip()
        if not stripped:
            return False

        # Reject expressions containing whitespace (beyond separators) or function/operator characters
        disallowed_chars = set(" ()[]{}+-*/%=!<>&|^\",'\"")
        if any(char in disallowed_chars for char in stripped):
            return False

        # Allow letters, digits, '.', '`', and '$' (for variables)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._`$")
        return all(char in allowed_chars for char in stripped)

    @staticmethod
    def _strip_namespace(tag: str) -> str:
        """Remove XML namespace from a tag if present."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    def _normalize_sql_value(self, value: Any) -> Any:
        """Normalize SQL result values by decoding JSON strings where possible."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    return value
        return value

    def _generate_compliance_report(self, total_time_ms: float) -> ComplianceReport:
        """Generate comprehensive compliance measurement report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        compliance_percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        average_time = statistics.mean([r.execution_time_ms for r in self.test_results]) if self.test_results else 0

        # Categorize tests
        test_categories = self._categorize_tests()

        # Performance metrics
        execution_times = [r.execution_time_ms for r in self.test_results]
        performance_metrics = {
            "min_execution_time_ms": min(execution_times) if execution_times else 0,
            "max_execution_time_ms": max(execution_times) if execution_times else 0,
            "median_execution_time_ms": statistics.median(execution_times) if execution_times else 0,
            "std_dev_execution_time_ms": statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        }

        # Failed test analysis
        failed_test_analysis = [
            {
                "name": r.name,
                "expression": r.expression,
                "error": r.error_message,
                "execution_time_ms": r.execution_time_ms,
                "actual_result": r.actual_result
            }
            for r in self.test_results if not r.passed
        ]

        return ComplianceReport(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            compliance_percentage=compliance_percentage,
            execution_time_total_ms=total_time_ms,
            execution_time_average_ms=average_time,
            parser_type=type(self.parser).__name__,
            database_type=self.database_type,
            timestamp=datetime.now().isoformat(),
            test_categories=test_categories,
            performance_metrics=performance_metrics,
            failed_test_analysis=failed_test_analysis[:10]  # Limit to first 10 failures
        )

    def _categorize_tests(self) -> Dict[str, Dict[str, int]]:
        """Categorize tests by FHIRPath specification areas and provide pass/fail counts"""
        categories = {}

        for result in self.test_results:
            # Enhanced categorization based on FHIRPath specification areas
            category = self._categorize_test_by_expression(result.expression, result.name)

            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0}

            categories[category]["total"] += 1
            if result.passed:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1

        return categories

    def _categorize_test_by_expression(self, expression: str, test_name: str) -> str:
        """
        Categorize test by FHIRPath expression content and specification areas

        Args:
            expression: FHIRPath expression string
            test_name: Test name for additional context

        Returns:
            Category string representing FHIRPath specification area
        """
        expr_lower = expression.lower()
        name_lower = test_name.lower()

        # Error/invalid expressions (check test name first)
        if "error" in name_lower or "invalid" in name_lower or "fail" in name_lower:
            return "error_handling"

        # Comments and syntax (high priority)
        if "//" in expression or "/*" in expression:
            return "comments_syntax"

        # Collection functions (check before comparison operators to avoid false positives)
        if any(func in expr_lower for func in ['where', 'select', 'all', 'any', 'exists', 'empty', 'distinct', 'first', 'last', 'tail', 'take', 'skip', 'union', 'intersect', 'exclude']):
            return "collection_functions"

        # String functions
        if any(func in expr_lower for func in ['contains', 'startswith', 'endswith', 'matches', 'replaceall', 'substring', 'indexof', 'split', 'join', 'upper', 'lower', 'length']):
            return "string_functions"

        # Date/Time functions
        if any(func in expr_lower for func in ['today', 'now', 'timeofday']):
            return "datetime_functions"

        # Math functions (check before arithmetic operators)
        if any(func in expr_lower for func in ['abs', 'ceiling', 'exp', 'floor', 'ln', 'log', 'power', 'round', 'sqrt', 'truncate']):
            return "math_functions"

        # Type functions
        if any(func in expr_lower for func in ['is', 'as', 'oftype', 'type', 'instanceof']):
            return "type_functions"

        # Comparison operations (check before arithmetic to catch = signs)
        if any(op in expression for op in ['=', '!=', '<>', '>', '<', '>=', '<=', '~']):
            return "comparison_operators"

        # Arithmetic operations
        if any(op in expression for op in ['+', '-', '*', '/', 'div', 'mod']):
            return "arithmetic_operators"

        # Boolean operations
        if any(op in expr_lower for op in ['and', 'or', 'xor', 'not', 'implies']):
            return "boolean_logic"

        # Functions with parentheses (general functions)
        if '(' in expression and ')' in expression:
            return "function_calls"

        # Path navigation
        if '.' in expression:
            return "path_navigation"

        # Literals and constants
        if any(pattern in expression for pattern in ['@', 'true', 'false', 'null', '{}']):
            return "literals_constants"

        # Default category
        return "basic_expressions"

    def save_compliance_report(self, report: ComplianceReport, output_path: Optional[Path] = None) -> Path:
        """Save compliance report to JSON file"""
        if output_path is None:
            output_path = Path("compliance_report.json")

        with open(output_path, 'w') as f:
            json.dump(asdict(report), f, indent=2)

        return output_path

    def print_compliance_summary(self, report: ComplianceReport) -> None:
        """Print a formatted compliance summary"""
        print("\n" + "="*60)
        print("FHIRPATH COMPLIANCE REPORT")
        print("="*60)
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Compliance: {report.compliance_percentage:.1f}%")
        print(f"Database Type: {report.database_type}")
        print(f"Parser Type: {report.parser_type}")
        print(f"Total Execution Time: {report.execution_time_total_ms:.1f}ms")
        print(f"Average Test Time: {report.execution_time_average_ms:.1f}ms")

        print("\nTest Categories:")
        for category, counts in report.test_categories.items():
            compliance = (counts["passed"] / counts["total"] * 100) if counts["total"] > 0 else 0
            print(f"  {category.title()}: {counts['passed']}/{counts['total']} ({compliance:.1f}%)")

        print("\nPerformance Metrics:")
        print(f"  Min execution time: {report.performance_metrics['min_execution_time_ms']:.1f}ms")
        print(f"  Max execution time: {report.performance_metrics['max_execution_time_ms']:.1f}ms")
        print(f"  Median execution time: {report.performance_metrics['median_execution_time_ms']:.1f}ms")

        if report.failed_test_analysis:
            print(f"\nFirst {len(report.failed_test_analysis)} Failed Tests:")
            for failure in report.failed_test_analysis:
                print(f"  - {failure['name']}: {failure['expression']}")
                if failure['error']:
                    print(f"    Error: {failure['error']}")

    def get_compliance_trend(self) -> Dict[str, Any]:
        """Get compliance trend analysis from history"""
        if len(self.compliance_history) < 2:
            return {"trend": "insufficient_data", "reports": len(self.compliance_history)}

        recent = self.compliance_history[-1]
        previous = self.compliance_history[-2]

        compliance_change = recent.compliance_percentage - previous.compliance_percentage
        performance_change = recent.execution_time_average_ms - previous.execution_time_average_ms

        return {
            "trend": "improving" if compliance_change > 0 else "declining" if compliance_change < 0 else "stable",
            "compliance_change": compliance_change,
            "performance_change_ms": performance_change,
            "current_compliance": recent.compliance_percentage,
            "previous_compliance": previous.compliance_percentage,
            "reports_count": len(self.compliance_history)
        }


def run_compliance_measurement(database_type: str = "duckdb",
                             max_tests: Optional[int] = None) -> ComplianceReport:
    """
    Convenience function to run compliance measurement

    Args:
        database_type: Database type for testing (duckdb or postgresql)
        max_tests: Maximum number of tests to run (None for all)

    Returns:
        Comprehensive compliance report
    """
    runner = EnhancedOfficialTestRunner(database_type)
    report = runner.run_official_tests(max_tests=max_tests)
    runner.print_compliance_summary(report)
    return report


if __name__ == "__main__":
    # Run compliance measurement for demonstration
    print("Running FHIRPath compliance measurement...")

    # Run a limited set for demonstration (first 50 tests)
    report = run_compliance_measurement(database_type="duckdb", max_tests=50)

    # Save report
    runner = EnhancedOfficialTestRunner()
    output_path = runner.save_compliance_report(report)
    print(f"\nCompliance report saved to: {output_path}")
