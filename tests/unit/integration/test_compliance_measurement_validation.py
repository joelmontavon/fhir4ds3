"""
Unit tests for compliance measurement validation functionality

Tests the enhanced compliance measurement system to ensure accurate
real-world compliance reporting with proper test result validation.
"""

import pytest
import unittest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from tests.integration.fhirpath.official_test_runner import (
    EnhancedOfficialTestRunner, TestResult, ComplianceReport
)


class TestComplianceMeasurementValidation(unittest.TestCase):
    """Test compliance measurement validation functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_runner = EnhancedOfficialTestRunner()

    def test_validate_test_result_empty_outputs_expect_success(self):
        """Valid expressions with empty outputs should be treated as success"""
        empty_outputs = []

        # Parser returns success - should be marked as passed test
        success_result = {"is_valid": True, "expression": "test"}
        self.assertTrue(
            self.test_runner._validate_test_result(success_result, empty_outputs)
        )

        # Parser returns failure - should be marked as failed test
        failure_result = {"is_valid": False, "expression": "test"}
        self.assertFalse(
            self.test_runner._validate_test_result(failure_result, empty_outputs)
        )

        # Parser returns None - should be marked as failed test
        none_result = None
        self.assertFalse(
            self.test_runner._validate_test_result(none_result, empty_outputs)
        )

    def test_validate_test_result_with_expected_outputs(self):
        """Test validation with non-empty expected outputs"""
        # Non-empty outputs means expression should succeed
        expected_outputs = [{"type": "integer", "value": None}]

        # Parser returns success - should be marked as passed test
        success_result = {"is_valid": True, "expression": "test"}
        self.assertTrue(
            self.test_runner._validate_test_result(success_result, expected_outputs)
        )

        # Parser returns failure - should be marked as failed test
        failure_result = {"is_valid": False, "expression": "test"}
        self.assertFalse(
            self.test_runner._validate_test_result(failure_result, expected_outputs)
        )

        # Parser returns None - should be marked as failed test
        none_result = None
        self.assertFalse(
            self.test_runner._validate_test_result(none_result, expected_outputs)
        )

    def test_validate_test_result_with_invalid_flag(self):
        """Semantic-invalid expressions must fail parsing"""
        expected_outputs = []
        invalid_flag = "semantic"

        # Parser returns failure (None) - should be marked as pass because failure was expected
        none_result = None
        self.assertTrue(
            self.test_runner._validate_test_result(none_result, expected_outputs, invalid_flag)
        )

        # Parser incorrectly returns success - should be flagged as failure
        success_result = {"is_valid": True}
        self.assertFalse(
            self.test_runner._validate_test_result(success_result, expected_outputs, invalid_flag)
        )

    def test_categorize_test_by_expression_comments_syntax(self):
        """Test categorization of comment and syntax expressions"""
        # Single line comment
        category = self.test_runner._categorize_test_by_expression(
            "2 + 2 // This is a comment", "testComment"
        )
        self.assertEqual(category, "comments_syntax")

        # Multi-line comment
        category = self.test_runner._categorize_test_by_expression(
            "/* Multi-line comment */ 2 + 2", "testComment"
        )
        self.assertEqual(category, "comments_syntax")

    def test_categorize_test_by_expression_arithmetic(self):
        """Test categorization of arithmetic expressions"""
        arithmetic_expressions = [
            "2 + 2",
            "5 - 3",
            "4 * 6",
            "8 / 2",
            "10 div 3",
            "15 mod 4"
        ]

        for expr in arithmetic_expressions:
            category = self.test_runner._categorize_test_by_expression(expr, "test")
            self.assertEqual(category, "arithmetic_operators")

    def test_categorize_test_by_expression_collection_functions(self):
        """Test categorization of collection function expressions"""
        collection_expressions = [
            "Patient.name.where(use = 'official')",
            "Observation.select(value)",
            "Patient.exists()",
            "data.all(value > 0)",
            "items.first()",
            "list.distinct()"
        ]

        for expr in collection_expressions:
            category = self.test_runner._categorize_test_by_expression(expr, "test")
            self.assertEqual(category, "collection_functions")

    def test_categorize_test_by_expression_error_handling(self):
        """Test categorization of error/invalid expressions"""
        # Test name indicates error/invalid
        category = self.test_runner._categorize_test_by_expression(
            "some expression", "testInvalidExpression"
        )
        self.assertEqual(category, "error_handling")

        category = self.test_runner._categorize_test_by_expression(
            "another expression", "testErrorCase"
        )
        self.assertEqual(category, "error_handling")

    def test_compliance_report_generation(self):
        """Test compliance report generation with mixed results"""
        # Mock test results with mixed pass/fail
        mock_results = [
            TestResult(
                name="test1", expression="2 + 2", expected_outputs=[],
                actual_result={"is_valid": True}, passed=False, execution_time_ms=1.0
            ),
            TestResult(
                name="test2", expression="invalid syntax", expected_outputs=[],
                actual_result={"is_valid": False}, passed=True, execution_time_ms=2.0
            ),
            TestResult(
                name="test3", expression="Patient.name", expected_outputs=[{"type": "string"}],
                actual_result={"is_valid": True}, passed=True, execution_time_ms=1.5
            )
        ]

        self.test_runner.test_results = mock_results

        # Generate compliance report
        report = self.test_runner._generate_compliance_report(total_time_ms=4.5)

        # Validate report structure
        self.assertIsInstance(report, ComplianceReport)
        self.assertEqual(report.total_tests, 3)
        self.assertEqual(report.passed_tests, 2)
        self.assertEqual(report.failed_tests, 1)
        self.assertAlmostEqual(report.compliance_percentage, 66.67, places=1)
        self.assertEqual(report.execution_time_total_ms, 4.5)
        self.assertAlmostEqual(report.execution_time_average_ms, 1.5, places=1)

    def test_real_compliance_measurement_accuracy(self):
        """Test that compliance measurement provides realistic results"""
        # Test validation logic directly instead of mocking the test parser

        # Test case 1: Expression that should pass (non-empty outputs)
        result1 = {"is_valid": True}
        expected1 = [{"type": "string"}]
        self.assertTrue(self.test_runner._validate_test_result(result1, expected1))

        # Test case 2: Expression that should return empty result but parser reports failure
        result2 = {"is_valid": False}
        expected2 = []  # Empty outputs = should succeed with empty collection
        self.assertFalse(self.test_runner._validate_test_result(result2, expected2))

        # Test case 3: Expression marked invalid but parser accepts it (should be failure)
        result3 = {"is_valid": True}
        expected3 = []
        self.assertFalse(
            self.test_runner._validate_test_result(result3, expected3, invalid_flag="semantic")
        )

        # This validates that our validation logic can produce non-100% compliance

    def test_failure_analysis_categorization(self):
        """Test that failure analysis properly categorizes failed tests"""
        # Mock test results with failures in different categories
        mock_results = [
            TestResult(
                name="arithmetic_test", expression="2 + 2 /", expected_outputs=[],
                actual_result={"is_valid": True}, passed=False, execution_time_ms=1.0
            ),
            TestResult(
                name="collection_test", expression="Patient.where(value > 0)", expected_outputs=[{"type": "collection"}],
                actual_result={"is_valid": False}, passed=False, execution_time_ms=2.0
            )
        ]

        self.test_runner.test_results = mock_results

        # Generate categorization
        categories = self.test_runner._categorize_tests()

        # Should have categories for arithmetic and collection functions
        self.assertIn("arithmetic_operators", categories)
        self.assertIn("collection_functions", categories)

        # Verify failure counts
        self.assertEqual(categories["arithmetic_operators"]["failed"], 1)
        self.assertEqual(categories["collection_functions"]["failed"], 1)

    def test_performance_metrics_validation(self):
        """Test that performance metrics are correctly calculated"""
        # Mock test results with varying execution times
        mock_results = [
            TestResult(
                name="fast", expression="simple", expected_outputs=[],
                actual_result={"is_valid": True}, passed=True, execution_time_ms=0.5
            ),
            TestResult(
                name="slow", expression="complex", expected_outputs=[],
                actual_result={"is_valid": True}, passed=True, execution_time_ms=5.0
            ),
            TestResult(
                name="medium", expression="normal", expected_outputs=[],
                actual_result={"is_valid": True}, passed=True, execution_time_ms=2.0
            )
        ]

        self.test_runner.test_results = mock_results

        # Generate compliance report
        report = self.test_runner._generate_compliance_report(total_time_ms=7.5)

        # Validate performance metrics
        self.assertAlmostEqual(report.execution_time_average_ms, 2.5, places=1)
        self.assertIn("min_execution_time_ms", report.performance_metrics)
        self.assertIn("max_execution_time_ms", report.performance_metrics)
        self.assertEqual(report.performance_metrics["min_execution_time_ms"], 0.5)
        self.assertEqual(report.performance_metrics["max_execution_time_ms"], 5.0)


if __name__ == "__main__":
    unittest.main()
