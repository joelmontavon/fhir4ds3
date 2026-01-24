"""
Tests for FHIRPath AST extensions
"""

import pytest
from fhir4ds.fhirpath.parser_core.ast_extensions import (
    EnhancedASTNode, ASTNodeFactory, ASTAnalyzer
)
from fhir4ds.fhirpath.parser_core.metadata_types import (
    NodeCategory, OptimizationHint, SQLDataType,
    MetadataBuilder, TypeInformation
)


class TestEnhancedASTNode:
    """Test EnhancedASTNode class"""

    def test_node_creation(self):
        """Test basic node creation"""
        node = EnhancedASTNode(
            node_type="pathExpression",
            text="Patient.name"
        )
        assert node.node_type == "pathExpression"
        assert node.text == "Patient.name"
        assert node.children == []
        assert node.parent is None
        assert node.metadata is None

    def test_parent_child_relationships(self):
        """Test parent-child relationship management"""
        parent = EnhancedASTNode("expression", "Patient.name.first()")
        child1 = EnhancedASTNode("pathExpression", "Patient.name")
        child2 = EnhancedASTNode("functionCall", "first()")

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert child1.parent == parent
        assert child2.parent == parent
        assert child1 in parent.children
        assert child2 in parent.children

    def test_remove_child(self):
        """Test child removal"""
        parent = EnhancedASTNode("expression", "test")
        child = EnhancedASTNode("literal", "value")

        parent.add_child(child)
        assert child in parent.children
        assert child.parent == parent

        parent.remove_child(child)
        assert child not in parent.children
        assert child.parent is None

    def test_get_root(self):
        """Test finding root node"""
        root = EnhancedASTNode("expression", "root")
        middle = EnhancedASTNode("pathExpression", "middle")
        leaf = EnhancedASTNode("literal", "leaf")

        root.add_child(middle)
        middle.add_child(leaf)

        assert leaf.get_root() == root
        assert middle.get_root() == root
        assert root.get_root() == root

    def test_get_depth(self):
        """Test depth calculation"""
        root = EnhancedASTNode("expression", "root")
        middle = EnhancedASTNode("pathExpression", "middle")
        leaf = EnhancedASTNode("literal", "leaf")

        root.add_child(middle)
        middle.add_child(leaf)

        assert root.get_depth() == 0
        assert middle.get_depth() == 1
        assert leaf.get_depth() == 2

    def test_find_nodes_by_type(self):
        """Test finding nodes by type"""
        root = EnhancedASTNode("expression", "root")
        path1 = EnhancedASTNode("pathExpression", "Patient")
        path2 = EnhancedASTNode("pathExpression", "name")
        func = EnhancedASTNode("functionCall", "first()")

        root.add_child(path1)
        root.add_child(path2)
        root.add_child(func)

        path_nodes = root.find_nodes_by_type("pathExpression")
        assert len(path_nodes) == 2
        assert path1 in path_nodes
        assert path2 in path_nodes

        func_nodes = root.find_nodes_by_type("functionCall")
        assert len(func_nodes) == 1
        assert func in func_nodes

    def test_find_nodes_by_category(self):
        """Test finding nodes by category"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.PATH_EXPRESSION) \
            .build()

        root = EnhancedASTNode("expression", "root")
        path_node = EnhancedASTNode("pathExpression", "Patient", metadata=metadata)
        root.add_child(path_node)

        path_nodes = root.find_nodes_by_category(NodeCategory.PATH_EXPRESSION)
        assert len(path_nodes) == 1
        assert path_node in path_nodes

    def test_has_optimization_hint(self):
        """Test optimization hint checking"""
        metadata = MetadataBuilder() \
            .with_optimization_hint(OptimizationHint.VECTORIZABLE) \
            .build()

        node = EnhancedASTNode("functionCall", "count()", metadata=metadata)
        assert node.has_optimization_hint(OptimizationHint.VECTORIZABLE)
        assert not node.has_optimization_hint(OptimizationHint.INDEX_FRIENDLY)

    def test_population_optimization_checks(self):
        """Test population optimization helper methods"""
        from fhir4ds.fhirpath.parser_core.metadata_types import PopulationAnalyticsMetadata
        metadata = MetadataBuilder() \
            .with_population_analytics(PopulationAnalyticsMetadata(
                supports_population_query=True,
                requires_patient_context=True
            )) \
            .build()

        node = EnhancedASTNode("pathExpression", "Patient", metadata=metadata)
        assert node.is_population_optimizable()
        assert node.requires_patient_context()

    def test_sql_data_type_retrieval(self):
        """Test SQL data type retrieval"""
        metadata = MetadataBuilder() \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.INTEGER)) \
            .build()

        node = EnhancedASTNode("literal", "42", metadata=metadata)
        assert node.get_sql_data_type() == SQLDataType.INTEGER

        # Test node without metadata
        node_no_metadata = EnhancedASTNode("literal", "test")
        assert node_no_metadata.get_sql_data_type() == SQLDataType.UNKNOWN

    def test_aggregation_node_check(self):
        """Test aggregation node identification"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.AGGREGATION) \
            .build()

        node = EnhancedASTNode("functionCall", "count()", metadata=metadata)
        assert node.is_aggregation_node()

        non_agg_node = EnhancedASTNode("literal", "test")
        assert not non_agg_node.is_aggregation_node()

    def test_to_dict(self):
        """Test dictionary conversion"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.FUNCTION_CALL) \
            .with_optimization_hint(OptimizationHint.VECTORIZABLE) \
            .with_type_info(TypeInformation(sql_data_type=SQLDataType.INTEGER)) \
            .with_source_location("count()", 1, 5) \
            .build()

        node = EnhancedASTNode("functionCall", "count()", metadata=metadata)
        node.sql_fragment = "COUNT(*)"
        node.cte_name = "count_cte"
        node.dependencies = ["patient_table"]

        result = node.to_dict()

        assert result["node_type"] == "functionCall"
        assert result["text"] == "count()"
        assert result["metadata"]["category"] == "function_call"
        assert "vectorizable" in result["metadata"]["optimization_hints"]
        assert result["metadata"]["sql_data_type"] == "integer"
        assert result["metadata"]["source_text"] == "count()"
        assert result["metadata"]["line_number"] == 1
        assert result["metadata"]["column_number"] == 5
        assert result["sql_fragment"] == "COUNT(*)"
        assert result["cte_name"] == "count_cte"
        assert result["dependencies"] == ["patient_table"]

    def test_string_representation(self):
        """Test string representations"""
        node = EnhancedASTNode("pathExpression", "Patient.name")
        assert str(node) == "pathExpression(Patient.name)"
        assert "EnhancedASTNode" in repr(node)
        assert "pathExpression" in repr(node)
        assert "Patient.name" in repr(node)


class TestASTNodeFactory:
    """Test ASTNodeFactory class"""

    def test_create_path_node(self):
        """Test path node creation"""
        node = ASTNodeFactory.create_path_node("Patient.name", "Patient")

        assert node.node_type == "pathExpression"
        assert node.text == "Patient.name"
        assert node.metadata is not None
        assert node.metadata.node_category == NodeCategory.PATH_EXPRESSION
        assert node.metadata.type_info.fhir_type == "Patient"
        assert node.metadata.type_info.sql_data_type == SQLDataType.JSON
        assert OptimizationHint.PROJECTION_SAFE in node.metadata.optimization_hints

    def test_create_function_node_aggregation(self):
        """Test aggregation function node creation"""
        node = ASTNodeFactory.create_function_node("count", "count()")

        assert node.node_type == "functionCall"
        assert node.text == "count()"
        assert node.metadata.node_category == NodeCategory.AGGREGATION
        assert node.metadata.type_info.sql_data_type == SQLDataType.INTEGER
        assert OptimizationHint.AGGREGATION_CANDIDATE in node.metadata.optimization_hints

    def test_create_function_node_conditional(self):
        """Test conditional function node creation"""
        node = ASTNodeFactory.create_function_node("where", "where(active = true)")

        assert node.node_type == "functionCall"
        assert node.text == "where(active = true)"
        assert node.metadata.node_category == NodeCategory.CONDITIONAL
        assert OptimizationHint.POPULATION_FILTER in node.metadata.optimization_hints

    def test_create_function_node_vectorizable(self):
        """Test vectorizable function node creation"""
        node = ASTNodeFactory.create_function_node("first", "first()")

        assert node.node_type == "functionCall"
        assert node.text == "first()"
        assert OptimizationHint.VECTORIZABLE in node.metadata.optimization_hints

    def test_create_literal_node_string(self):
        """Test string literal node creation"""
        node = ASTNodeFactory.create_literal_node("test", "'test'")

        assert node.node_type == "literal"
        assert node.text == "'test'"
        assert node.metadata.node_category == NodeCategory.LITERAL
        assert node.metadata.type_info.sql_data_type == SQLDataType.TEXT
        assert node.metadata.type_info.is_collection is False
        assert node.metadata.type_info.is_nullable is False

    def test_create_literal_node_numeric(self):
        """Test numeric literal node creation"""
        int_node = ASTNodeFactory.create_literal_node(42, "42")
        assert int_node.metadata.type_info.sql_data_type == SQLDataType.INTEGER

        float_node = ASTNodeFactory.create_literal_node(3.14, "3.14")
        assert float_node.metadata.type_info.sql_data_type == SQLDataType.DECIMAL

    def test_create_literal_node_boolean(self):
        """Test boolean literal node creation"""
        node = ASTNodeFactory.create_literal_node(True, "true")
        assert node.metadata.type_info.sql_data_type == SQLDataType.BOOLEAN

    def test_create_operator_node(self):
        """Test operator node creation"""
        node = ASTNodeFactory.create_operator_node("=", "=")

        assert node.node_type == "operator"
        assert node.text == "="
        assert node.metadata.node_category == NodeCategory.OPERATOR
        assert node.metadata.type_info.sql_data_type == SQLDataType.BOOLEAN
        assert OptimizationHint.PROJECTION_SAFE in node.metadata.optimization_hints

    def test_create_from_fhirpath_node(self):
        """Test creation from fhirpath-py node"""
        # Mock fhirpath-py node
        class MockFHIRPathNode:
            def __init__(self, node_type, text, children=None):
                self.type = node_type
                self.text = text
                self.children = children or []

        mock_node = MockFHIRPathNode("functionCall", "count()")
        enhanced_node = ASTNodeFactory.create_from_fhirpath_node(mock_node)

        assert enhanced_node.node_type == "functionCall"
        assert enhanced_node.text == "count()"
        assert enhanced_node.metadata is not None

    def test_create_from_fhirpath_node_with_children(self):
        """Test creation with children"""
        class MockFHIRPathNode:
            def __init__(self, node_type, text, children=None):
                self.type = node_type
                self.text = text
                self.children = children or []

        child_node = MockFHIRPathNode("literal", "42")
        parent_node = MockFHIRPathNode("pathExpression", "Patient.id", [child_node])

        enhanced_node = ASTNodeFactory.create_from_fhirpath_node(parent_node)

        assert enhanced_node.node_type == "pathExpression"
        assert len(enhanced_node.children) == 1
        assert enhanced_node.children[0].text == "42"
        assert enhanced_node.children[0].parent == enhanced_node


class TestASTAnalyzer:
    """Test ASTAnalyzer class"""

    def test_analyze_complexity_simple(self):
        """Test complexity analysis for simple AST"""
        root = EnhancedASTNode("expression", "Patient.name")
        path_node = ASTNodeFactory.create_path_node("Patient.name")
        root.add_child(path_node)

        analysis = ASTAnalyzer.analyze_complexity(root)

        assert analysis["total_nodes"] == 1  # Only the path node has metadata
        assert analysis["max_depth"] == 2
        assert NodeCategory.PATH_EXPRESSION.value in analysis["category_distribution"]
        assert analysis["has_aggregations"] is False
        assert analysis["has_functions"] is False
        assert "complexity_score" in analysis

    def test_analyze_complexity_with_aggregation(self):
        """Test complexity analysis with aggregation"""
        root = EnhancedASTNode("expression", "Patient.count()")
        count_node = ASTNodeFactory.create_function_node("count", "count()")
        root.add_child(count_node)

        analysis = ASTAnalyzer.analyze_complexity(root)

        assert analysis["has_aggregations"] is True
        assert analysis["has_functions"] is True
        assert NodeCategory.AGGREGATION.value in analysis["category_distribution"]

    def test_find_optimization_opportunities(self):
        """Test finding optimization opportunities"""
        root = EnhancedASTNode("expression", "Patient.where(active = true).count()")

        # Add conditional node
        where_node = ASTNodeFactory.create_function_node("where", "where(active = true)")
        where_node.metadata.optimization_hints.add(OptimizationHint.POPULATION_FILTER)
        root.add_child(where_node)

        # Add aggregation node
        count_node = ASTNodeFactory.create_function_node("count", "count()")
        where_node.add_child(count_node)

        # Add CTE reusable node
        reusable_node = ASTNodeFactory.create_function_node("complex", "complex()")
        reusable_node.metadata.optimization_hints.add(OptimizationHint.CTE_REUSABLE)
        root.add_child(reusable_node)

        opportunities = ASTAnalyzer.find_optimization_opportunities(root)

        # Should find CTE extraction, population filter, and aggregation opportunities
        opportunity_types = [opp["type"] for opp in opportunities]
        assert "cte_extraction" in opportunity_types
        assert "population_filter" in opportunity_types
        assert "aggregation_optimization" in opportunity_types

    def test_complexity_score_calculation(self):
        """Test complexity score calculation"""
        # Simple literal should have low complexity
        root = EnhancedASTNode("expression", "42")
        literal_node = ASTNodeFactory.create_literal_node(42, "42")
        root.add_child(literal_node)

        analysis = ASTAnalyzer.analyze_complexity(root)
        simple_score = analysis["complexity_score"]

        # Complex expression should have higher complexity
        complex_root = EnhancedASTNode("expression", "Patient.where(active).count()")
        where_node = ASTNodeFactory.create_function_node("where", "where(active)")
        count_node = ASTNodeFactory.create_function_node("count", "count()")
        complex_root.add_child(where_node)
        where_node.add_child(count_node)

        complex_analysis = ASTAnalyzer.analyze_complexity(complex_root)
        complex_score = complex_analysis["complexity_score"]

        assert complex_score > simple_score