"""
Tests for FHIRPath AST metadata types
"""

import pytest
from fhir4ds.fhirpath.parser_core.metadata_types import (
    OptimizationHint, NodeCategory, SQLDataType,
    TypeInformation, PerformanceMetadata, CTEGenerationContext,
    PopulationAnalyticsMetadata, ASTNodeMetadata, MetadataBuilder,
    METADATA_TEMPLATES
)


class TestOptimizationHint:
    """Test OptimizationHint enum"""

    def test_optimization_hint_values(self):
        """Test that optimization hints have expected values"""
        assert OptimizationHint.POPULATION_FILTER.value == "population_filter"
        assert OptimizationHint.PROJECTION_SAFE.value == "projection_safe"
        assert OptimizationHint.AGGREGATION_CANDIDATE.value == "aggregation_candidate"
        assert OptimizationHint.INDEX_FRIENDLY.value == "index_friendly"
        assert OptimizationHint.CTE_REUSABLE.value == "cte_reusable"
        assert OptimizationHint.VECTORIZABLE.value == "vectorizable"


class TestNodeCategory:
    """Test NodeCategory enum"""

    def test_node_category_values(self):
        """Test that node categories have expected values"""
        assert NodeCategory.PATH_EXPRESSION.value == "path_expression"
        assert NodeCategory.FUNCTION_CALL.value == "function_call"
        assert NodeCategory.LITERAL.value == "literal"
        assert NodeCategory.OPERATOR.value == "operator"
        assert NodeCategory.CONDITIONAL.value == "conditional"
        assert NodeCategory.AGGREGATION.value == "aggregation"
        assert NodeCategory.TYPE_OPERATION.value == "type_operation"


class TestSQLDataType:
    """Test SQLDataType enum"""

    def test_sql_data_type_values(self):
        """Test that SQL data types have expected values"""
        assert SQLDataType.TEXT.value == "text"
        assert SQLDataType.INTEGER.value == "integer"
        assert SQLDataType.DECIMAL.value == "decimal"
        assert SQLDataType.BOOLEAN.value == "boolean"
        assert SQLDataType.DATE.value == "date"
        assert SQLDataType.TIMESTAMP.value == "timestamp"
        assert SQLDataType.JSON.value == "json"
        assert SQLDataType.ARRAY.value == "array"
        assert SQLDataType.UNKNOWN.value == "unknown"


class TestTypeInformation:
    """Test TypeInformation dataclass"""

    def test_type_information_defaults(self):
        """Test default values for TypeInformation"""
        type_info = TypeInformation()
        assert type_info.expected_input_type is None
        assert type_info.expected_output_type is None
        assert type_info.sql_data_type == SQLDataType.UNKNOWN
        assert type_info.is_collection is False
        assert type_info.is_nullable is True
        assert type_info.fhir_type is None

    def test_type_information_with_values(self):
        """Test TypeInformation with explicit values"""
        type_info = TypeInformation(
            expected_input_type="Patient",
            expected_output_type="string",
            sql_data_type=SQLDataType.TEXT,
            is_collection=True,
            is_nullable=False,
            fhir_type="Patient"
        )
        assert type_info.expected_input_type == "Patient"
        assert type_info.expected_output_type == "string"
        assert type_info.sql_data_type == SQLDataType.TEXT
        assert type_info.is_collection is True
        assert type_info.is_nullable is False
        assert type_info.fhir_type == "Patient"


class TestPerformanceMetadata:
    """Test PerformanceMetadata dataclass"""

    def test_performance_metadata_defaults(self):
        """Test default values for PerformanceMetadata"""
        perf = PerformanceMetadata()
        assert perf.estimated_selectivity is None
        assert perf.supports_indexing is False
        assert perf.memory_intensive is False
        assert perf.cpu_intensive is False
        assert perf.io_intensive is False

    def test_performance_metadata_with_values(self):
        """Test PerformanceMetadata with explicit values"""
        perf = PerformanceMetadata(
            estimated_selectivity=0.1,
            supports_indexing=True,
            memory_intensive=True,
            cpu_intensive=True,
            io_intensive=False
        )
        assert perf.estimated_selectivity == 0.1
        assert perf.supports_indexing is True
        assert perf.memory_intensive is True
        assert perf.cpu_intensive is True
        assert perf.io_intensive is False


class TestCTEGenerationContext:
    """Test CTEGenerationContext dataclass"""

    def test_cte_context_defaults(self):
        """Test default values for CTEGenerationContext"""
        context = CTEGenerationContext()
        assert context.requires_join is False
        assert context.join_conditions == []
        assert context.dependent_tables == set()
        assert context.can_be_subquery is True
        assert context.requires_window_function is False

    def test_cte_context_post_init(self):
        """Test __post_init__ method"""
        context = CTEGenerationContext()
        assert isinstance(context.join_conditions, list)
        assert isinstance(context.dependent_tables, set)

    def test_cte_context_with_values(self):
        """Test CTEGenerationContext with explicit values"""
        context = CTEGenerationContext(
            requires_join=True,
            join_conditions=["p.id = e.patient_id"],
            dependent_tables={"patient", "encounter"},
            can_be_subquery=False,
            requires_window_function=True
        )
        assert context.requires_join is True
        assert context.join_conditions == ["p.id = e.patient_id"]
        assert context.dependent_tables == {"patient", "encounter"}
        assert context.can_be_subquery is False
        assert context.requires_window_function is True


class TestPopulationAnalyticsMetadata:
    """Test PopulationAnalyticsMetadata dataclass"""

    def test_population_analytics_defaults(self):
        """Test default values for PopulationAnalyticsMetadata"""
        pop_analytics = PopulationAnalyticsMetadata()
        assert pop_analytics.supports_population_query is True
        assert pop_analytics.requires_patient_context is False
        assert pop_analytics.can_be_population_filtered is False
        assert pop_analytics.aggregation_level is None

    def test_population_analytics_with_values(self):
        """Test PopulationAnalyticsMetadata with explicit values"""
        pop_analytics = PopulationAnalyticsMetadata(
            supports_population_query=False,
            requires_patient_context=True,
            can_be_population_filtered=True,
            aggregation_level="patient"
        )
        assert pop_analytics.supports_population_query is False
        assert pop_analytics.requires_patient_context is True
        assert pop_analytics.can_be_population_filtered is True
        assert pop_analytics.aggregation_level == "patient"


class TestASTNodeMetadata:
    """Test ASTNodeMetadata dataclass"""

    def test_ast_node_metadata_creation(self):
        """Test creating ASTNodeMetadata with all components"""
        type_info = TypeInformation(sql_data_type=SQLDataType.TEXT)
        perf = PerformanceMetadata(cpu_intensive=True)
        cte_context = CTEGenerationContext(requires_join=True)
        pop_analytics = PopulationAnalyticsMetadata(aggregation_level="population")

        metadata = ASTNodeMetadata(
            node_category=NodeCategory.FUNCTION_CALL,
            type_info=type_info,
            optimization_hints={OptimizationHint.VECTORIZABLE},
            performance=perf,
            cte_context=cte_context,
            population_analytics=pop_analytics,
            source_text="count()",
            line_number=1,
            column_number=5
        )

        assert metadata.node_category == NodeCategory.FUNCTION_CALL
        assert metadata.type_info.sql_data_type == SQLDataType.TEXT
        assert OptimizationHint.VECTORIZABLE in metadata.optimization_hints
        assert metadata.performance.cpu_intensive is True
        assert metadata.cte_context.requires_join is True
        assert metadata.population_analytics.aggregation_level == "population"
        assert metadata.source_text == "count()"
        assert metadata.line_number == 1
        assert metadata.column_number == 5

    def test_ast_node_metadata_post_init(self):
        """Test __post_init__ method"""
        metadata = ASTNodeMetadata(
            node_category=NodeCategory.LITERAL,
            type_info=TypeInformation(),
            optimization_hints=set(),
            performance=PerformanceMetadata(),
            cte_context=CTEGenerationContext(),
            population_analytics=PopulationAnalyticsMetadata()
        )
        assert isinstance(metadata.custom_attributes, dict)
        assert metadata.custom_attributes == {}


class TestMetadataBuilder:
    """Test MetadataBuilder class"""

    def test_builder_reset(self):
        """Test builder reset functionality"""
        builder = MetadataBuilder()
        builder.with_category(NodeCategory.AGGREGATION)

        # Reset and verify defaults
        builder.reset()
        metadata = builder.build()
        assert metadata.node_category == NodeCategory.PATH_EXPRESSION  # default

    def test_builder_fluent_interface(self):
        """Test fluent interface pattern"""
        metadata = MetadataBuilder() \
            .with_category(NodeCategory.FUNCTION_CALL) \
            .with_optimization_hint(OptimizationHint.VECTORIZABLE) \
            .with_optimization_hint(OptimizationHint.CTE_REUSABLE) \
            .with_source_location("count()", 1, 5) \
            .with_custom_attribute("test_key", "test_value") \
            .build()

        assert metadata.node_category == NodeCategory.FUNCTION_CALL
        assert OptimizationHint.VECTORIZABLE in metadata.optimization_hints
        assert OptimizationHint.CTE_REUSABLE in metadata.optimization_hints
        assert metadata.source_text == "count()"
        assert metadata.line_number == 1
        assert metadata.column_number == 5
        assert metadata.custom_attributes["test_key"] == "test_value"

    def test_builder_with_type_info(self):
        """Test builder with type information"""
        type_info = TypeInformation(sql_data_type=SQLDataType.INTEGER)
        metadata = MetadataBuilder().with_type_info(type_info).build()
        assert metadata.type_info.sql_data_type == SQLDataType.INTEGER

    def test_builder_with_performance(self):
        """Test builder with performance metadata"""
        perf = PerformanceMetadata(memory_intensive=True)
        metadata = MetadataBuilder().with_performance(perf).build()
        assert metadata.performance.memory_intensive is True

    def test_builder_with_cte_context(self):
        """Test builder with CTE context"""
        cte_context = CTEGenerationContext(requires_join=True)
        metadata = MetadataBuilder().with_cte_context(cte_context).build()
        assert metadata.cte_context.requires_join is True

    def test_builder_with_population_analytics(self):
        """Test builder with population analytics"""
        pop_analytics = PopulationAnalyticsMetadata(aggregation_level="patient")
        metadata = MetadataBuilder().with_population_analytics(pop_analytics).build()
        assert metadata.population_analytics.aggregation_level == "patient"


class TestMetadataTemplates:
    """Test predefined metadata templates"""

    def test_patient_path_template(self):
        """Test patient path metadata template"""
        template = METADATA_TEMPLATES["patient_path"]()
        assert template.node_category == NodeCategory.PATH_EXPRESSION
        assert template.type_info.fhir_type == "Patient"
        assert template.type_info.sql_data_type == SQLDataType.JSON
        assert OptimizationHint.POPULATION_FILTER in template.optimization_hints
        assert template.population_analytics.requires_patient_context is True
        assert template.population_analytics.aggregation_level == "patient"

    def test_count_function_template(self):
        """Test count function metadata template"""
        template = METADATA_TEMPLATES["count_function"]()
        assert template.node_category == NodeCategory.AGGREGATION
        assert template.type_info.sql_data_type == SQLDataType.INTEGER
        assert template.type_info.is_collection is False
        assert OptimizationHint.AGGREGATION_CANDIDATE in template.optimization_hints
        assert OptimizationHint.VECTORIZABLE in template.optimization_hints
        assert template.population_analytics.aggregation_level == "population"

    def test_string_literal_template(self):
        """Test string literal metadata template"""
        template = METADATA_TEMPLATES["string_literal"]()
        assert template.node_category == NodeCategory.LITERAL
        assert template.type_info.sql_data_type == SQLDataType.TEXT
        assert template.type_info.is_collection is False
        assert template.type_info.is_nullable is False
        assert OptimizationHint.PROJECTION_SAFE in template.optimization_hints

    def test_template_immutability(self):
        """Test that templates are independent instances"""
        template1 = METADATA_TEMPLATES["patient_path"]()
        template2 = METADATA_TEMPLATES["patient_path"]()

        # Should be equal but not the same instance
        assert template1.node_category == template2.node_category
        # Modifying one shouldn't affect the other
        template1.optimization_hints.add(OptimizationHint.VECTORIZABLE)
        assert len(template1.optimization_hints) != len(template2.optimization_hints)