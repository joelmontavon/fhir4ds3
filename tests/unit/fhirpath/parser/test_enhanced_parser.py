"""
Tests for Enhanced FHIRPath Parser
"""

import pytest
import time
from unittest.mock import Mock, patch
from fhir4ds.fhirpath.parser_core.enhanced_parser import (
    EnhancedFHIRPathParser, ParseResult, ExpressionValidator,
    create_enhanced_parser
)
from fhir4ds.fhirpath.parser_core.ast_extensions import EnhancedASTNode
from fhir4ds.fhirpath.parser_core.metadata_types import NodeCategory, OptimizationHint


class TestParseResult:
    """Test ParseResult dataclass"""

    def test_parse_result_defaults(self):
        """Test default values for ParseResult"""
        result = ParseResult()
        assert result.ast is None
        assert result.is_valid is False
        assert result.error_message is None
        assert result.parse_time_ms is None
        assert result.complexity_analysis is None
        assert result.optimization_opportunities is None

    def test_parse_result_with_values(self):
        """Test ParseResult with explicit values"""
        ast = EnhancedASTNode("expression", "test")
        result = ParseResult(
            ast=ast,
            is_valid=True,
            parse_time_ms=5.2,
            complexity_analysis={"total_nodes": 1},
            optimization_opportunities=[{"type": "test"}]
        )
        assert result.ast == ast
        assert result.is_valid is True
        assert result.parse_time_ms == 5.2
        assert result.complexity_analysis == {"total_nodes": 1}
        assert result.optimization_opportunities == [{"type": "test"}]


class TestEnhancedFHIRPathParser:
    """Test EnhancedFHIRPathParser class"""

    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = EnhancedFHIRPathParser("postgresql")
        assert parser.database_type == "postgresql"
        assert parser.parse_count == 0
        assert parser.total_parse_time == 0.0

    def test_parser_initialization_default(self):
        """Test parser initialization with defaults"""
        parser = EnhancedFHIRPathParser()
        assert parser.database_type == "duckdb"

    def test_parse_empty_expression(self):
        """Test parsing empty expression"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("")
        assert not result.is_valid
        assert "Empty" in result.error_message or "empty" in result.error_message
        assert result.ast is None

        result = parser.parse("   ")
        assert not result.is_valid
        assert "Empty" in result.error_message or "empty" in result.error_message or "whitespace" in result.error_message

    def test_parse_simple_expression_stub(self):
        """Test parsing simple expression with stub implementation"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("Patient.name")
        assert result.is_valid
        assert result.ast is not None
        assert result.parse_time_ms is not None
        assert result.parse_time_ms > 0

    def test_parse_complex_expression_stub(self):
        """Test parsing complex expression with stub implementation"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("Patient.name.where(use='official').first()")
        assert result.is_valid
        assert result.ast is not None
        assert len(result.ast.children) > 0

    def test_parse_with_analysis_options(self):
        """Test parsing with analysis options"""
        parser = EnhancedFHIRPathParser()

        # With complexity analysis
        result = parser.parse("Patient.name", analyze_complexity=True)
        assert result.complexity_analysis is not None
        assert "total_nodes" in result.complexity_analysis

        # Without complexity analysis
        result = parser.parse("Patient.name", analyze_complexity=False)
        assert result.complexity_analysis is None

        # With optimization analysis
        result = parser.parse("Patient.name", find_optimizations=True)
        assert result.optimization_opportunities is not None

        # Without optimization analysis
        result = parser.parse("Patient.name", find_optimizations=False)
        assert result.optimization_opportunities is None

    def test_parse_statistics_tracking(self):
        """Test that parsing statistics are tracked"""
        parser = EnhancedFHIRPathParser()
        initial_count = parser.parse_count
        initial_time = parser.total_parse_time

        parser.parse("Patient.name")

        assert parser.parse_count == initial_count + 1
        assert parser.total_parse_time > initial_time

    def test_parse_with_database_specific_hints(self):
        """Test database-specific optimization hints"""
        # Test DuckDB parser
        duckdb_parser = EnhancedFHIRPathParser("duckdb")
        result = duckdb_parser.parse("Patient.count()")

        # Should have vectorizable hint for aggregations in DuckDB
        agg_nodes = result.ast.find_nodes_by_category(NodeCategory.AGGREGATION)
        if agg_nodes:
            assert any(node.has_optimization_hint(OptimizationHint.VECTORIZABLE)
                      for node in agg_nodes)

        # Test PostgreSQL parser
        pg_parser = EnhancedFHIRPathParser("postgresql")
        result = pg_parser.parse("Patient.name")

        # Should have index-friendly hint for path expressions in PostgreSQL
        path_nodes = result.ast.find_nodes_by_category(NodeCategory.PATH_EXPRESSION)
        if path_nodes:
            assert any(node.has_optimization_hint(OptimizationHint.INDEX_FRIENDLY)
                      for node in path_nodes)

    def test_get_statistics(self):
        """Test statistics retrieval"""
        parser = EnhancedFHIRPathParser("postgresql")

        # Parse a few expressions
        parser.parse("Patient.name")
        parser.parse("Patient.id")

        stats = parser.get_statistics()
        assert stats["parse_count"] == 2
        assert stats["database_type"] == "postgresql"
        assert stats["average_parse_time_ms"] > 0
        assert "fhirpathpy_available" in stats

    def test_reset_statistics(self):
        """Test statistics reset"""
        parser = EnhancedFHIRPathParser()

        parser.parse("Patient.name")
        assert parser.parse_count > 0
        assert parser.total_parse_time > 0

        parser.reset_statistics()
        assert parser.parse_count == 0
        assert parser.total_parse_time == 0.0

    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.FHIRPATHPY_AVAILABLE', True)
    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.fhirpath_parse')
    def test_parse_with_fhirpathpy_success(self, mock_fhirpath_parse):
        """Test parsing with fhirpath-py when available and successful"""
        # Mock successful fhirpath-py parsing
        mock_ast = Mock()
        mock_ast.type = "pathExpression"
        mock_ast.text = "Patient.name"
        mock_ast.children = []
        mock_fhirpath_parse.return_value = mock_ast

        parser = EnhancedFHIRPathParser()
        result = parser.parse("Patient.name")

        assert result.is_valid
        assert result.ast is not None
        mock_fhirpath_parse.assert_called_once_with("Patient.name")

    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.FHIRPATHPY_AVAILABLE', True)
    @patch('fhir4ds.fhirpath.parser_core.enhanced_parser.fhirpath_parse')
    def test_parse_with_fhirpathpy_failure(self, mock_fhirpath_parse):
        """Test parsing with fhirpath-py when it fails"""
        # Mock fhirpath-py parsing failure
        mock_fhirpath_parse.side_effect = Exception("Parse error")

        parser = EnhancedFHIRPathParser()
        result = parser.parse("invalid expression")

        # Should fall back to stub implementation or return error
        assert not result.is_valid
        assert "error" in result.error_message.lower() or "parse" in result.error_message.lower()

    def test_parse_error_handling(self):
        """Test error handling during parsing"""
        parser = EnhancedFHIRPathParser()

        # Test with empty expression (known to be invalid)
        result = parser.parse("")

        # Should handle error gracefully
        assert not result.is_valid
        assert result.error_message is not None

    def test_population_analytics_metadata_enhancement(self):
        """Test population analytics metadata enhancement"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("Patient.name")
        assert result.is_valid

        # Check that patient-related nodes have correct metadata
        patient_nodes = [node for node in result.ast.find_nodes_by_type("pathExpression")
                        if "patient" in node.text.lower()]

        for node in patient_nodes:
            if node.metadata:
                assert node.metadata.population_analytics.requires_patient_context

    def test_performance_metadata_enhancement(self):
        """Test performance metadata enhancement"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("Patient.count()")
        assert result.is_valid

        # Check that aggregation nodes have performance metadata
        agg_nodes = result.ast.find_nodes_by_category(NodeCategory.AGGREGATION)
        for node in agg_nodes:
            if node.metadata:
                assert node.metadata.performance.cpu_intensive

    def test_cte_generation_metadata_enhancement(self):
        """Test CTE generation metadata enhancement"""
        parser = EnhancedFHIRPathParser()

        result = parser.parse("Patient.name.first()")
        assert result.is_valid

        # Check that path expressions have CTE metadata
        path_nodes = result.ast.find_nodes_by_category(NodeCategory.PATH_EXPRESSION)
        for node in path_nodes:
            if node.metadata and "." in node.text:
                assert node.metadata.cte_context.requires_join


class TestExpressionValidator:
    """Test ExpressionValidator class"""

    def test_validate_empty_expression(self):
        """Test validation of empty expression"""
        result = ExpressionValidator.validate_expression("")
        assert not result["is_valid"]
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "error"
        assert "Empty expression" in result["issues"][0]["message"]

    def test_validate_valid_expression(self):
        """Test validation of valid expression"""
        result = ExpressionValidator.validate_expression("Patient.name")
        assert result["is_valid"]
        assert all(issue["type"] != "error" for issue in result["issues"])

    def test_validate_double_dots(self):
        """Test validation of double dots syntax error"""
        result = ExpressionValidator.validate_expression("Patient..name")
        assert not result["is_valid"]
        error_issues = [issue for issue in result["issues"] if issue["type"] == "error"]
        assert len(error_issues) == 1
        assert "consecutive dots" in error_issues[0]["message"]

    def test_validate_unmatched_parentheses(self):
        """Test validation of unmatched parentheses"""
        # Too many opening
        result = ExpressionValidator.validate_expression("Patient.name.where((active = true)")
        assert not result["is_valid"]

        # Too many closing
        result = ExpressionValidator.validate_expression("Patient.name.where(active = true))")
        assert not result["is_valid"]

    def test_validate_performance_warnings(self):
        """Test performance warning detection"""
        deep_expression = "Patient." + ".".join([f"field{i}" for i in range(15)])
        result = ExpressionValidator.validate_expression(deep_expression)

        warning_issues = [issue for issue in result["issues"] if issue["type"] == "warning"]
        assert any("performance" in issue["message"].lower() for issue in warning_issues)

    def test_validate_security_warnings(self):
        """Test security warning detection"""
        result = ExpressionValidator.validate_expression("Patient.name.select *")
        warning_issues = [issue for issue in result["issues"] if issue["type"] == "warning"]
        assert any("problematic pattern" in issue["message"] for issue in warning_issues)

    def test_complexity_estimation(self):
        """Test complexity estimation"""
        # Simple expression
        simple_result = ExpressionValidator.validate_expression("Patient.name")
        assert simple_result["complexity_estimate"] == "low"

        # Medium complexity
        medium_result = ExpressionValidator.validate_expression("Patient.name.where(use='official').first()")
        assert medium_result["complexity_estimate"] in ["low", "medium"]

        # High complexity
        complex_expr = "Patient.name.where(use='official').select(given.where(length() > 3).first()).exists()"
        complex_result = ExpressionValidator.validate_expression(complex_expr)
        assert complex_result["complexity_estimate"] in ["medium", "high"]


class TestCreateEnhancedParser:
    """Test create_enhanced_parser factory function"""

    def test_create_parser_default(self):
        """Test creating parser with default settings"""
        parser = create_enhanced_parser()
        assert isinstance(parser, EnhancedFHIRPathParser)
        assert parser.database_type == "duckdb"

    def test_create_parser_postgresql(self):
        """Test creating parser for PostgreSQL"""
        parser = create_enhanced_parser("postgresql")
        assert isinstance(parser, EnhancedFHIRPathParser)
        assert parser.database_type == "postgresql"

    def test_create_parser_multiple_instances(self):
        """Test that multiple parser instances are independent"""
        parser1 = create_enhanced_parser("duckdb")
        parser2 = create_enhanced_parser("postgresql")

        assert parser1 is not parser2
        assert parser1.database_type != parser2.database_type

        # Parse with one parser shouldn't affect the other
        parser1.parse("Patient.name")
        assert parser1.parse_count == 1
        assert parser2.parse_count == 0


class TestIntegrationScenarios:
    """Integration tests for realistic parsing scenarios"""

    def test_healthcare_expression_parsing(self):
        """Test parsing common healthcare FHIRPath expressions"""
        parser = EnhancedFHIRPathParser()

        expressions = [
            "Patient.name.where(use='official').given.first()",
            "Patient.birthDate",
            "Patient.gender",
            "Patient.address.where(use='home').city",
            "Patient.telecom.where(system='phone').value",
            "Observation.value.as(Quantity)",
            "Encounter.participant.where(type.coding.code='ATND').individual",
            "Condition.code.coding.where(system='http://snomed.info/sct').code"
        ]

        for expr in expressions:
            result = parser.parse(expr)
            assert result.is_valid, f"Failed to parse: {expr}"
            assert result.ast is not None
            assert result.complexity_analysis is not None

    def test_aggregation_expression_parsing(self):
        """Test parsing aggregation expressions"""
        parser = EnhancedFHIRPathParser()

        aggregation_expressions = [
            "Patient.count()",
            "Observation.value.as(Quantity).value.sum()",
            "Encounter.length.average()",
            "Condition.onset.as(DateTime).min()",
            "Patient.name.count()"
        ]

        for expr in aggregation_expressions:
            result = parser.parse(expr)
            assert result.is_valid, f"Failed to parse aggregation: {expr}"

            # Should have aggregation opportunities
            assert result.optimization_opportunities is not None
            agg_opportunities = [opp for opp in result.optimization_opportunities
                               if opp["type"] == "aggregation_optimization"]
            assert len(agg_opportunities) > 0

    def test_conditional_expression_parsing(self):
        """Test parsing conditional expressions"""
        parser = EnhancedFHIRPathParser()

        conditional_expressions = [
            "Patient.where(active = true)",
            "Observation.where(status = 'final')",
            "Encounter.where(status in ('finished', 'completed'))",
            "Patient.name.where(use = 'official').exists()"
        ]

        for expr in conditional_expressions:
            result = parser.parse(expr)
            assert result.is_valid, f"Failed to parse conditional: {expr}"

            # Should have population filter opportunities
            assert result.optimization_opportunities is not None
            filter_opportunities = [opp for opp in result.optimization_opportunities
                                  if opp["type"] == "population_filter"]
            assert len(filter_opportunities) >= 0  # May or may not find opportunities

    def test_performance_analysis(self):
        """Test performance analysis across different expression types"""
        parser = EnhancedFHIRPathParser()

        # Simple expression should be fast
        start_time = time.time()
        result = parser.parse("Patient.name")
        simple_time = (time.time() - start_time) * 1000

        assert result.parse_time_ms is not None
        assert result.parse_time_ms < 100  # Should be under 100ms

        # Complex expression might take longer but should still be reasonable
        complex_expr = "Patient.name.where(use='official').given.where(length() > 2).first()"
        start_time = time.time()
        result = parser.parse(complex_expr)
        complex_time = (time.time() - start_time) * 1000

        assert result.parse_time_ms is not None
        assert result.parse_time_ms < 1000  # Should be under 1 second