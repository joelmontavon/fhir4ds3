"""
Unit Tests for Testing Infrastructure Integration

Comprehensive unit tests for the enhanced FHIRPath testing infrastructure
components including compliance measurement, multi-database validation,
regression prevention, and performance benchmarking.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from tests.integration.fhirpath.official_test_runner import (
    EnhancedOfficialTestRunner, ComplianceReport, TestResult
)
from tests.integration.fhirpath.compliance_tracker import (
    ComplianceTracker, ComplianceDatabase, ComplianceMetrics
)
from tests.integration.cross_database.multi_database_validator import (
    MultiDatabaseValidator, ConsistencyCheck, DatabaseResult
)
from tests.regression.fhirpath_regression_prevention import (
    FHIRPathRegressionPrevention, RegressionBaseline
)
from tests.performance.fhirpath.performance_benchmarking import (
    FHIRPathPerformanceTester, PerformanceBenchmark
)


class TestEnhancedOfficialTestRunner:
    """Test suite for EnhancedOfficialTestRunner"""

    @pytest.fixture
    def test_runner(self):
        """Create test runner instance"""
        return EnhancedOfficialTestRunner(database_type="duckdb")

    def test_runner_initialization(self, test_runner):
        """Test runner initializes correctly"""
        assert test_runner.database_type == "duckdb"
        assert test_runner.parser is not None
        assert isinstance(test_runner.test_results, list)
        assert isinstance(test_runner.compliance_history, list)

    def test_execute_single_test_success(self, test_runner):
        """Test successful single test execution"""
        test_data = {
            'name': 'test_simple',
            'expression': 'true',
            'outputs': [{'type': 'boolean', 'value': 'true'}]
        }

        result = test_runner._execute_single_test(test_data)

        assert isinstance(result, TestResult)
        assert result.name == 'test_simple'
        assert result.expression == 'true'
        assert result.passed is True
        assert result.execution_time_ms > 0

    def test_execute_single_test_failure(self, test_runner):
        """Test single test execution with invalid expression"""
        test_data = {
            'name': 'test_invalid_parsing',
            'expression': '(((',  # Invalid syntax - parser correctly rejects this
            'outputs': []
        }

        result = test_runner._execute_single_test(test_data)

        assert isinstance(result, TestResult)
        assert result.name == 'test_invalid_parsing'
        # Parser correctly fails on invalid syntax
        assert result.passed is False
        assert result.error_message is not None

    @patch('tests.integration.fhirpath.official_test_runner.parse_fhirpath_tests')
    def test_run_official_tests(self, mock_parse_tests, test_runner):
        """Test running official test suite"""
        # Mock test data
        mock_parse_tests.return_value = [
            {'name': 'test1', 'expression': 'true', 'outputs': []},
            {'name': 'test2', 'expression': 'false', 'outputs': []},
        ]

        report = test_runner.run_official_tests(max_tests=2)

        assert isinstance(report, ComplianceReport)
        assert report.total_tests == 2
        assert report.passed_tests >= 0
        assert report.compliance_percentage >= 0
        assert len(test_runner.test_results) == 2

    def test_categorize_tests(self, test_runner):
        """Test test categorization"""
        test_runner.test_results = [
            TestResult('arithmetic_test', '1 + 1', [], None, True, 10.0),
            TestResult('string_test', "'hello'", [], None, True, 5.0),
            TestResult('path_test', 'Patient.name', [], None, True, 8.0),
        ]

        categories = test_runner._categorize_tests()

        # Categorization groups tests - check that we have categories
        assert len(categories) > 0
        # Check that all tests are accounted for
        total_tests = sum(cat['total'] for cat in categories.values())
        assert total_tests == 3
        total_passed = sum(cat['passed'] for cat in categories.values())
        assert total_passed == 3

    def test_compliance_report_generation(self, test_runner):
        """Test compliance report generation"""
        test_runner.test_results = [
            TestResult('test1', 'general', 'true', [], True, 10.0),
            TestResult('test2', 'general', 'false', [], True, 15.0),
            TestResult('test3', 'general', 'invalid', [], False, 5.0, error_message="Parse error"),
        ]

        report = test_runner._generate_compliance_report(100.0)

        assert report.total_tests == 3
        assert report.passed_tests == 2
        assert report.failed_tests == 1
        assert report.compliance_percentage == pytest.approx(66.67, rel=0.01)
        assert report.execution_time_total_ms == 100.0


class TestComplianceTracker:
    """Test suite for ComplianceTracker"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def compliance_tracker(self, temp_db):
        """Create compliance tracker with temporary database"""
        return ComplianceTracker(db_path=temp_db)

    def test_compliance_database_initialization(self, temp_db):
        """Test compliance database initialization"""
        db = ComplianceDatabase(temp_db)
        assert Path(temp_db).exists()

    def test_store_and_retrieve_report(self, compliance_tracker):
        """Test storing and retrieving compliance reports"""
        # Create sample report
        report = ComplianceReport(
            total_tests=100,
            passed_tests=80,
            failed_tests=20,
            compliance_percentage=80.0,
            execution_time_total_ms=1000.0,
            execution_time_average_ms=10.0,
            parser_type="FHIRPathParser",
            database_type="duckdb",
            timestamp="2024-01-01T00:00:00",
            test_categories={},
            performance_metrics={},
            failed_test_analysis=[]
        )

        # Store report
        report_id = compliance_tracker.database.store_report(report)
        assert report_id > 0

        # Retrieve reports
        reports = compliance_tracker.database.get_reports(database_type="duckdb", limit=1)
        assert len(reports) == 1
        assert reports[0].total_tests == 100
        assert reports[0].compliance_percentage == 80.0

    def test_compliance_metrics_calculation(self, compliance_tracker):
        """Test compliance metrics calculation"""
        # Store some sample reports
        for i in range(3):
            report = ComplianceReport(
                total_tests=100,
                passed_tests=70 + i * 5,  # Improving compliance
                failed_tests=30 - i * 5,
                compliance_percentage=70.0 + i * 5,
                execution_time_total_ms=1000.0,
                execution_time_average_ms=10.0 - i,
                parser_type="FHIRPathParser",
                database_type="duckdb",
                timestamp=f"2024-01-0{i+1}T00:00:00",
                test_categories={},
                performance_metrics={},
                failed_test_analysis=[]
            )
            compliance_tracker.database.store_report(report)

        metrics = compliance_tracker.get_compliance_metrics("duckdb")

        assert isinstance(metrics, ComplianceMetrics)
        assert metrics.current_compliance == 80.0  # Latest report
        assert metrics.improvement_rate > 0  # Should detect improvement


class TestMultiDatabaseValidator:
    """Test suite for MultiDatabaseValidator"""

    @pytest.fixture
    def validator(self):
        """Create multi-database validator"""
        return MultiDatabaseValidator(database_types=["duckdb"])

    def test_validator_initialization(self, validator):
        """Test validator initializes correctly"""
        assert "duckdb" in validator.database_types
        assert "duckdb" in validator.parsers

    def test_validate_single_expression(self, validator):
        """Test validating a single expression"""
        check = validator.validate_expression("true")

        assert isinstance(check, ConsistencyCheck)
        assert check.expression == "true"
        assert len(check.results) == 1
        assert check.results[0].database_type == "duckdb"

    def test_consistency_check_success(self, validator):
        """Test consistency check with successful execution"""
        # Create mock results that are consistent
        results = [
            DatabaseResult("duckdb", "true", {"result": True}, 10.0, True, result_hash="abc123")
        ]

        consistent, issues = validator._check_consistency(results)
        assert consistent is True
        assert len(issues) == 0

    def test_consistency_check_failure(self, validator):
        """Test consistency check with failed execution"""
        results = [
            DatabaseResult("duckdb", "invalid", None, 0.0, False, error_message="Parse error")
        ]

        consistent, issues = validator._check_consistency(results)
        assert consistent is False
        assert len(issues) > 0

    def test_hash_result_consistency(self, validator):
        """Test result hashing for consistency comparison"""
        result1 = {"expression": "true", "is_valid": True}
        result2 = {"is_valid": True, "expression": "true"}  # Same data, different order

        hash1 = validator._hash_result(result1)
        hash2 = validator._hash_result(result2)

        assert hash1 == hash2  # Should be same due to sorted keys

    @patch('tests.integration.cross_database.multi_database_validator.parse_fhirpath_tests')
    def test_validate_official_tests(self, mock_parse_tests, validator):
        """Test validating official test suite"""
        mock_parse_tests.return_value = [
            {'expression': 'true'},
            {'expression': 'false'},
        ]

        report = validator.validate_official_tests(max_tests=2)

        assert report.total_expressions == 2
        assert report.databases_tested == ["duckdb"]
        assert len(report.consistency_checks) == 2


class TestRegressionPrevention:
    """Test suite for FHIRPathRegressionPrevention"""

    @pytest.fixture
    def temp_baseline(self):
        """Create temporary baseline file"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            baseline_path = f.name
        yield baseline_path
        Path(baseline_path).unlink(missing_ok=True)

    @pytest.fixture
    def regression_prevention(self, temp_baseline):
        """Create regression prevention instance"""
        prevention = FHIRPathRegressionPrevention(database_type="duckdb")
        prevention.baseline.baseline_file = Path(temp_baseline)
        return prevention

    def test_baseline_management(self, temp_baseline):
        """Test baseline save and load operations"""
        baseline = RegressionBaseline(temp_baseline)

        # Set baseline
        baseline.set_baseline("test1", "fhirpath", {"result": "success"})
        baseline.save_baselines()

        # Create new instance and check baseline exists
        new_baseline = RegressionBaseline(temp_baseline)
        assert new_baseline.has_baseline("test1", "fhirpath")
        result = new_baseline.get_baseline("test1", "fhirpath")
        assert result == {"result": "success"}

    def test_regression_test_execution(self, regression_prevention):
        """Test individual regression test execution"""
        result = regression_prevention._run_regression_test("test_simple", "fhirpath", "true")

        assert result.test_name == "test_simple"
        assert result.test_category == "fhirpath"
        assert result.expression == "true"
        assert result.passed is True

    def test_regression_detection(self, regression_prevention):
        """Test regression detection logic"""
        # Set baseline
        regression_prevention.baseline.set_baseline(
            "test1", "fhirpath", {"result": "baseline_value"}
        )

        # Run test with different result
        with patch.object(regression_prevention.parser, 'evaluate') as mock_evaluate:
            mock_evaluate.return_value = {"result": "different_value"}

            result = regression_prevention._run_regression_test("test1", "fhirpath", "true")

            assert result.regression_detected is True

    def test_comprehensive_regression_tests(self, regression_prevention):
        """Test comprehensive regression test execution"""
        report = regression_prevention.run_comprehensive_regression_tests(max_fhirpath_tests=5)

        assert report.total_tests > 0
        assert "fhirpath" in report.categories_tested
        assert "sql_on_fhir" in report.categories_tested
        assert "cql" in report.categories_tested
        assert report.overall_success_rate >= 0


class TestPerformanceTester:
    """Test suite for FHIRPathPerformanceTester"""

    @pytest.fixture
    def performance_tester(self):
        """Create performance tester instance"""
        return FHIRPathPerformanceTester(database_type="duckdb", target_time_ms=100.0)

    def test_performance_tester_initialization(self, performance_tester):
        """Test performance tester initializes correctly"""
        assert performance_tester.database_type == "duckdb"
        assert performance_tester.target_time_ms == 100.0
        assert performance_tester.parser is not None

    def test_benchmark_single_expression(self, performance_tester):
        """Test benchmarking a single expression"""
        benchmark = performance_tester.benchmark_expression("true", "literal", iterations=3)

        assert isinstance(benchmark, PerformanceBenchmark)
        assert benchmark.expression == "true"
        assert benchmark.category == "literal"
        assert benchmark.iterations == 3
        assert benchmark.average_time_ms > 0
        assert benchmark.total_time_ms > 0

    def test_expression_categorization(self, performance_tester):
        """Test expression categorization for performance analysis"""
        assert performance_tester._categorize_expression("1 + 2") == "arithmetic"
        assert performance_tester._categorize_expression("Patient.name") == "path"
        assert performance_tester._categorize_expression("substring('hello', 1)") == "string"
        assert performance_tester._categorize_expression("where(x = y)") == "collection"
        assert performance_tester._categorize_expression("now()") == "datetime"
        assert performance_tester._categorize_expression("length('test')") == "string"  # length is a string function
        assert performance_tester._categorize_expression("someFunction()") == "function"  # generic function
        assert performance_tester._categorize_expression("true") == "literal"

    def test_population_scale_performance(self, performance_tester):
        """Test population-scale performance testing"""
        # Use small scale factors for testing
        scale_performance = performance_tester.test_population_scale_performance([10, 100])

        assert "scale_10" in scale_performance
        assert "scale_100" in scale_performance
        assert all(time_ms >= 0 for time_ms in scale_performance.values())

    @patch('tests.performance.fhirpath.performance_benchmarking.parse_fhirpath_tests')
    def test_benchmark_official_tests(self, mock_parse_tests, performance_tester):
        """Test benchmarking official test expressions"""
        mock_parse_tests.return_value = [
            {'expression': 'true'},
            {'expression': '1 + 1'},
            {'expression': 'Patient.name'},
        ]

        benchmarks = performance_tester.benchmark_official_tests(max_tests=3, iterations=2)

        assert len(benchmarks) == 3
        assert all(isinstance(b, PerformanceBenchmark) for b in benchmarks)
        assert all(b.iterations == 2 for b in benchmarks)

    def test_performance_report_generation(self, performance_tester):
        """Test performance report generation"""
        # Create sample benchmarks
        benchmarks = [
            PerformanceBenchmark("true", "literal", 5, 50.0, 10.0, 8.0, 12.0, 10.0, 1.5, True, 100.0),
            PerformanceBenchmark("1+1", "arithmetic", 5, 250.0, 50.0, 45.0, 55.0, 50.0, 3.0, True, 100.0),
            PerformanceBenchmark("complex", "function", 5, 750.0, 150.0, 140.0, 160.0, 150.0, 8.0, False, 100.0),
        ]

        population_performance = {"scale_100": 25.0, "scale_1000": 45.0}

        report = performance_tester.generate_performance_report(benchmarks, population_performance)

        assert report.total_expressions == 3
        assert report.expressions_meeting_target == 2
        assert report.expressions_exceeding_target == 1
        assert report.target_compliance_percentage == pytest.approx(66.67, rel=0.01)
        assert len(report.performance_categories) > 0
        assert report.population_scale_performance == population_performance


class TestIntegrationWorkflows:
    """Test suite for integration workflows and end-to-end scenarios"""

    def test_compliance_to_regression_workflow(self):
        """Test workflow from compliance measurement to regression prevention"""
        # This would test the integration between different components
        # For now, just verify components can be instantiated together
        test_runner = EnhancedOfficialTestRunner()
        compliance_tracker = ComplianceTracker()
        regression_prevention = FHIRPathRegressionPrevention()

        assert test_runner is not None
        assert compliance_tracker is not None
        assert regression_prevention is not None

    def test_multi_database_performance_workflow(self):
        """Test workflow combining multi-database validation with performance testing"""
        validator = MultiDatabaseValidator(["duckdb"])
        performance_tester = FHIRPathPerformanceTester()

        # Verify they can work with the same expressions
        test_expression = "true"

        consistency_check = validator.validate_expression(test_expression)
        performance_benchmark = performance_tester.benchmark_expression(test_expression, "test")

        assert consistency_check.expression == test_expression
        assert performance_benchmark.expression == test_expression

    def test_reporting_integration(self):
        """Test that all components can generate and save reports"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test each component can save reports
            test_runner = EnhancedOfficialTestRunner()
            sample_report = ComplianceReport(
                total_tests=10, passed_tests=8, failed_tests=2, compliance_percentage=80.0,
                execution_time_total_ms=100.0, execution_time_average_ms=10.0,
                parser_type="test", database_type="test", timestamp="2024-01-01T00:00:00",
                test_categories={}, performance_metrics={}, failed_test_analysis=[]
            )

            # Verify report can be saved and loaded
            report_path = test_runner.save_compliance_report(sample_report, temp_path / "compliance.json")
            assert report_path.exists()

            with open(report_path) as f:
                loaded_data = json.load(f)
                assert loaded_data["total_tests"] == 10
                assert loaded_data["compliance_percentage"] == 80.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])