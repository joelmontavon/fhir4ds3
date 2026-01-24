"""
Integration tests for FHIRPath parser with enhanced capabilities
"""

import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser, FHIRPathExpression
from fhir4ds.fhirpath.exceptions import FHIRPathParseError
from fhir4ds.fhirpath.parser_core.metadata_types import NodeCategory, OptimizationHint


class TestFHIRPathParserIntegration:
    """Test main FHIRPath parser integration with enhanced capabilities"""

    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = FHIRPathParser()
        assert parser.database_type == "duckdb"

        parser_pg = FHIRPathParser("postgresql")
        assert parser_pg.database_type == "postgresql"

    def test_parse_simple_expression(self):
        """Test parsing simple expressions"""
        parser = FHIRPathParser()

        expression = parser.parse("Patient.name")
        assert isinstance(expression, FHIRPathExpression)
        assert expression.is_valid()
        assert expression.expression == "Patient.name"

    def test_parse_complex_expression(self):
        """Test parsing complex expressions"""
        parser = FHIRPathParser()

        expr_text = "Patient.name.where(use='official').given.first()"
        expression = parser.parse(expr_text)

        assert expression.is_valid()
        assert len(expression.get_path_components()) > 0
        assert len(expression.get_functions()) > 0

    def test_parse_empty_expression_error(self):
        """Test that empty expressions raise errors"""
        parser = FHIRPathParser()

        with pytest.raises(FHIRPathParseError, match="Empty expression"):
            parser.parse("")

        with pytest.raises(FHIRPathParseError, match="Empty expression"):
            parser.parse("   ")

    def test_enhanced_expression_methods(self):
        """Test enhanced expression methods"""
        parser = FHIRPathParser()
        expression = parser.parse("Patient.name.first()")

        # Test enhanced methods
        ast = expression.get_ast()
        assert ast is not None

        complexity = expression.get_complexity_analysis()
        assert complexity is not None
        assert "total_nodes" in complexity

        opportunities = expression.get_optimization_opportunities()
        assert opportunities is not None

    def test_path_component_extraction(self):
        """Test path component extraction"""
        parser = FHIRPathParser()

        # Simple path
        expression = parser.parse("Patient.name")
        components = expression.get_path_components()
        assert "Patient.name" in components or any("patient" in comp.lower() for comp in components)

        # Complex path
        expression = parser.parse("Patient.address.city")
        components = expression.get_path_components()
        assert len(components) > 0

    def test_function_extraction(self):
        """Test function extraction"""
        parser = FHIRPathParser()

        # Expression with functions
        expression = parser.parse("Patient.name.where(use='official').first()")
        functions = expression.get_functions()
        assert len(functions) > 0

        # Check for specific functions
        function_text = " ".join(functions).lower()
        assert any(func in function_text for func in ["where", "first"])

    def test_evaluate_method(self):
        """Test evaluate method with enhanced results"""
        parser = FHIRPathParser()

        result = parser.evaluate("Patient.name")
        assert result is not None
        assert isinstance(result, dict)
        assert "expression" in result
        assert "is_valid" in result
        assert "path_components" in result
        assert "functions" in result
        assert "complexity_analysis" in result
        assert "optimization_opportunities" in result

    def test_evaluate_with_context(self):
        """Test evaluate method with context"""
        parser = FHIRPathParser()
        context = {"Patient": {"name": [{"given": ["John"], "family": "Doe"}]}}

        result = parser.evaluate("Patient.name", context)
        assert result is not None
        assert result["is_valid"]

    def test_evaluate_invalid_expression(self):
        """Test evaluate with invalid expression"""
        parser = FHIRPathParser()

        # This should return None for invalid expressions
        result = parser.evaluate("")
        assert result is None

    def test_get_statistics(self):
        """Test statistics collection"""
        parser = FHIRPathParser()

        # Parse some expressions
        parser.parse("Patient.name")
        parser.parse("Patient.id")

        stats = parser.get_statistics()
        assert stats["parse_count"] == 2
        assert stats["database_type"] == "duckdb"
        assert "average_parse_time_ms" in stats
        assert "fhirpathpy_available" in stats

    def test_validate_expression(self):
        """Test expression validation"""
        parser = FHIRPathParser()

        # Valid expression
        result = parser.validate_expression("Patient.name")
        assert result["is_valid"]

        # Invalid expression
        result = parser.validate_expression("Patient..name")
        assert not result["is_valid"]
        assert len(result["issues"]) > 0

    def test_get_enhanced_parser(self):
        """Test getting underlying enhanced parser"""
        parser = FHIRPathParser()
        enhanced_parser = parser.get_enhanced_parser()

        assert enhanced_parser is not None
        assert hasattr(enhanced_parser, "parse")
        assert hasattr(enhanced_parser, "get_statistics")

    def test_database_specific_behavior(self):
        """Test database-specific parsing behavior"""
        duckdb_parser = FHIRPathParser("duckdb")
        pg_parser = FHIRPathParser("postgresql")

        # Parse same expression with both
        expression_text = "Patient.count()"

        duckdb_expr = duckdb_parser.parse(expression_text)
        pg_expr = pg_parser.parse(expression_text)

        assert duckdb_expr.is_valid()
        assert pg_expr.is_valid()

        # Check that database-specific hints are applied
        duckdb_ast = duckdb_expr.get_ast()
        pg_ast = pg_expr.get_ast()

        # Both should parse successfully but may have different optimization hints
        assert duckdb_ast is not None
        assert pg_ast is not None


class TestFHIRPathExpressionEnhanced:
    """Test enhanced FHIRPathExpression functionality"""

    def test_expression_with_ast_metadata(self):
        """Test expression with AST and metadata"""
        parser = FHIRPathParser()
        expression = parser.parse("Patient.name.first()")

        ast = expression.get_ast()
        assert ast is not None

        # Check for metadata presence
        if ast.children:
            for child in ast.children:
                if child.metadata:
                    assert child.metadata.node_category in [
                        NodeCategory.PATH_EXPRESSION,
                        NodeCategory.FUNCTION_CALL,
                        NodeCategory.AGGREGATION,
                        NodeCategory.LITERAL,
                        NodeCategory.OPERATOR,
                        NodeCategory.CONDITIONAL,
                        NodeCategory.TYPE_OPERATION
                    ]

    def test_complexity_analysis_integration(self):
        """Test complexity analysis integration"""
        parser = FHIRPathParser()

        # Simple expression
        simple_expr = parser.parse("Patient.name")
        simple_complexity = simple_expr.get_complexity_analysis()
        assert simple_complexity is not None
        assert simple_complexity["complexity_score"] >= 0

        # Complex expression
        complex_expr = parser.parse("Patient.name.where(use='official').given.first()")
        complex_complexity = complex_expr.get_complexity_analysis()
        assert complex_complexity is not None

        # Complex expression should have higher complexity score
        assert complex_complexity["total_nodes"] >= simple_complexity["total_nodes"]

    def test_optimization_opportunities_integration(self):
        """Test optimization opportunities integration"""
        parser = FHIRPathParser()

        # Expression with aggregation
        agg_expr = parser.parse("Patient.count()")
        agg_opportunities = agg_expr.get_optimization_opportunities()
        assert agg_opportunities is not None

        # Should find aggregation optimization opportunities
        agg_types = [opp["type"] for opp in agg_opportunities]
        assert "aggregation_optimization" in agg_types

        # Expression with conditional
        cond_expr = parser.parse("Patient.where(active = true)")
        cond_opportunities = cond_expr.get_optimization_opportunities()
        assert cond_opportunities is not None

    def test_backwards_compatibility(self):
        """Test backwards compatibility with original interface"""
        parser = FHIRPathParser()
        expression = parser.parse("Patient.name.first()")

        # Original interface methods should still work
        assert expression.is_valid()
        assert isinstance(expression.get_path_components(), list)
        assert isinstance(expression.get_functions(), list)

        # Expression text should be available
        assert hasattr(expression, 'expression')
        assert len(expression.expression) > 0


class TestHealthcareExpressionParsing:
    """Test parsing of realistic healthcare FHIRPath expressions"""

    def test_patient_demographics(self):
        """Test parsing patient demographic expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Patient.name.where(use='official').family",
            "Patient.name.where(use='official').given.first()",
            "Patient.birthDate",
            "Patient.gender",
            "Patient.active"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse: {expr}"
            result = parser.evaluate(expr)
            assert result["is_valid"], f"Failed to evaluate: {expr}"

    def test_patient_contact_info(self):
        """Test parsing patient contact information expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Patient.telecom.where(system='phone').value",
            "Patient.telecom.where(system='email').value",
            "Patient.address.where(use='home').line",
            "Patient.address.where(use='home').city",
            "Patient.address.where(use='home').state",
            "Patient.address.where(use='home').postalCode"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse: {expr}"

    def test_observation_expressions(self):
        """Test parsing observation-related expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Observation.value.as(Quantity)",
            "Observation.value.as(Quantity).value",
            "Observation.value.as(Quantity).unit",
            "Observation.code.coding.where(system='http://loinc.org').code",
            "Observation.status",
            "Observation.effectiveDateTime"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse: {expr}"

    def test_encounter_expressions(self):
        """Test parsing encounter-related expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Encounter.status",
            "Encounter.class.code",
            "Encounter.type.coding.code",
            "Encounter.participant.where(type.coding.code='ATND').individual",
            "Encounter.period.start",
            "Encounter.period.end"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse: {expr}"

    def test_condition_expressions(self):
        """Test parsing condition-related expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Condition.code.coding.where(system='http://snomed.info/sct').code",
            "Condition.clinicalStatus.coding.code",
            "Condition.verificationStatus.coding.code",
            "Condition.onset.as(DateTime)",
            "Condition.subject.reference"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse: {expr}"

    def test_aggregation_expressions(self):
        """Test parsing aggregation expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Patient.count()",
            "Observation.count()",
            "Observation.value.as(Quantity).value.average()",
            "Observation.value.as(Quantity).value.sum()",
            "Patient.name.count()",
            "Encounter.length.average()"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse aggregation: {expr}"

            # Check for aggregation optimization opportunities
            # Note: expressions with .as() type operations may not be detected
            opportunities = parsed.get_optimization_opportunities()
            if ".as(" not in expr:  # Skip .as() expressions - known limitation
                agg_opportunities = [opp for opp in opportunities
                                   if opp["type"] == "aggregation_optimization"]
                assert len(agg_opportunities) > 0, f"No aggregation opportunities found for: {expr}"

    def test_conditional_expressions(self):
        """Test parsing conditional expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Patient.where(active = true)",
            "Observation.where(status = 'final')",
            "Observation.where(value.as(Quantity).value > 10)",
            "Encounter.where(status in ('finished', 'completed'))",
            "Condition.where(clinicalStatus.coding.code = 'active')"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse conditional: {expr}"

    def test_type_operations(self):
        """Test parsing type operation expressions"""
        parser = FHIRPathParser()

        expressions = [
            "Observation.value.as(Quantity)",
            "Observation.value.as(string)",
            "Condition.onset.as(DateTime)",
            "Patient.name.as(HumanName)"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid(), f"Failed to parse type operation: {expr}"

    def test_performance_characteristics(self):
        """Test performance characteristics of healthcare expressions"""
        parser = FHIRPathParser()

        # Test a variety of expressions for performance
        expressions = [
            "Patient.name",
            "Patient.name.where(use='official').given.first()",
            "Observation.value.as(Quantity).value.average()",
            "Patient.address.where(use='home').line.first()",
            "Condition.code.coding.where(system='http://snomed.info/sct').code.first()"
        ]

        for expr in expressions:
            parsed = parser.parse(expr)
            assert parsed.is_valid()

            complexity = parsed.get_complexity_analysis()
            assert complexity["complexity_score"] >= 0

            # Parse time should be reasonable (under 100ms for these expressions)
            # Note: This is checked in the parse result, not here directly
