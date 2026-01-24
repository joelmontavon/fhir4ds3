"""
Enhanced AST Serialization for FHIR4DS FHIRPath Engine

This module provides comprehensive serialization capabilities for FHIRPath AST
trees, including metadata serialization for debugging, caching, and analysis.
"""

from typing import Dict, Any, List, Optional, Union, IO
import json
import pickle
from dataclasses import asdict
from datetime import datetime
import gzip
import base64
import logging

from .nodes import (
    FHIRPathASTNode, LiteralNode, IdentifierNode, FunctionCallNode,
    OperatorNode, ConditionalNode, AggregationNode, TypeOperationNode
)
from ..parser_core.metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint, SQLDataType
)


class SerializationFormat:
    """Supported serialization formats"""
    JSON = "json"
    JSON_COMPRESSED = "json_compressed"
    PICKLE = "pickle"
    PICKLE_COMPRESSED = "pickle_compressed"
    XML = "xml"
    YAML = "yaml"


class ASTSerializer:
    """
    Enhanced AST serializer with comprehensive metadata support

    Provides multiple serialization formats optimized for different use cases:
    - JSON: Human-readable debugging and analysis
    - Compressed JSON: Space-efficient storage
    - Pickle: Fast Python-specific serialization
    - XML: Standards-compliant exchange format
    """

    def __init__(self, include_metadata: bool = True, include_stats: bool = True):
        self.include_metadata = include_metadata
        self.include_stats = include_stats
        self.logger = logging.getLogger(__name__)

    def serialize(self, root: FHIRPathASTNode, format_type: str = SerializationFormat.JSON) -> Union[str, bytes]:
        """
        Serialize AST to specified format

        Args:
            root: Root node of AST to serialize
            format_type: Target serialization format

        Returns:
            Serialized representation as string or bytes
        """
        try:
            if format_type == SerializationFormat.JSON:
                return self._serialize_to_json(root)
            elif format_type == SerializationFormat.JSON_COMPRESSED:
                return self._serialize_to_json_compressed(root)
            elif format_type == SerializationFormat.PICKLE:
                return self._serialize_to_pickle(root)
            elif format_type == SerializationFormat.PICKLE_COMPRESSED:
                return self._serialize_to_pickle_compressed(root)
            elif format_type == SerializationFormat.XML:
                return self._serialize_to_xml(root)
            elif format_type == SerializationFormat.YAML:
                return self._serialize_to_yaml(root)
            else:
                raise ValueError(f"Unsupported serialization format: {format_type}")

        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            raise

    def _serialize_to_json(self, root: FHIRPathASTNode) -> str:
        """Serialize AST to JSON format"""
        ast_dict = self._convert_to_dict(root)

        # Add serialization metadata
        serialization_info = {
            "format": SerializationFormat.JSON,
            "timestamp": datetime.now().isoformat(),
            "serializer_version": "1.0.0",
            "include_metadata": self.include_metadata,
            "include_stats": self.include_stats
        }

        if self.include_stats:
            serialization_info["stats"] = self._calculate_ast_stats(root)

        result = {
            "serialization_info": serialization_info,
            "ast": ast_dict
        }

        return json.dumps(result, indent=2, default=self._json_serializer)

    def _serialize_to_json_compressed(self, root: FHIRPathASTNode) -> bytes:
        """Serialize AST to compressed JSON format"""
        json_str = self._serialize_to_json(root)
        return gzip.compress(json_str.encode('utf-8'))

    def _serialize_to_pickle(self, root: FHIRPathASTNode) -> bytes:
        """Serialize AST to pickle format"""
        ast_dict = self._convert_to_dict(root)
        return pickle.dumps(ast_dict)

    def _serialize_to_pickle_compressed(self, root: FHIRPathASTNode) -> bytes:
        """Serialize AST to compressed pickle format"""
        pickle_data = self._serialize_to_pickle(root)
        return gzip.compress(pickle_data)

    def _serialize_to_xml(self, root: FHIRPathASTNode) -> str:
        """Serialize AST to XML format"""
        # Basic XML serialization - could be enhanced with proper XML library
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<fhirpath_ast>')

        # Add serialization info
        xml_lines.append('<serialization_info>')
        xml_lines.append(f'  <format>{SerializationFormat.XML}</format>')
        xml_lines.append(f'  <timestamp>{datetime.now().isoformat()}</timestamp>')
        xml_lines.append(f'  <include_metadata>{self.include_metadata}</include_metadata>')
        xml_lines.append('</serialization_info>')

        # Add AST structure
        xml_lines.append('<ast>')
        self._node_to_xml(root, xml_lines, 1)
        xml_lines.append('</ast>')

        xml_lines.append('</fhirpath_ast>')
        return '\n'.join(xml_lines)

    def _serialize_to_yaml(self, root: FHIRPathASTNode) -> str:
        """Serialize AST to YAML format"""
        try:
            import yaml
            ast_dict = self._convert_to_dict(root)
            return yaml.dump(ast_dict, default_flow_style=False)
        except ImportError:
            raise ImportError("PyYAML is required for YAML serialization")

    def _convert_to_dict(self, node: FHIRPathASTNode) -> Dict[str, Any]:
        """Convert AST node to dictionary representation"""
        result = {
            "node_type": node.node_type,
            "text": node.text,
            "class_name": node.__class__.__name__
        }

        # Add node-specific properties
        if isinstance(node, LiteralNode):
            result.update({
                "value": getattr(node, 'value', None),
                "literal_type": getattr(node, 'literal_type', 'unknown')
            })
        elif isinstance(node, IdentifierNode):
            result.update({
                "identifier": getattr(node, 'identifier', ''),
                "is_qualified": getattr(node, 'is_qualified', False)
            })
        elif isinstance(node, FunctionCallNode):
            result.update({
                "function_name": getattr(node, 'function_name', ''),
                "argument_count": len(getattr(node, 'arguments', []))
            })
        elif isinstance(node, OperatorNode):
            result.update({
                "operator": getattr(node, 'operator', ''),
                "operator_type": getattr(node, 'operator_type', 'unknown')
            })
        elif isinstance(node, ConditionalNode):
            result.update({
                "condition_type": getattr(node, 'condition_type', 'where')
            })
        elif isinstance(node, AggregationNode):
            result.update({
                "aggregation_function": getattr(node, 'aggregation_function', ''),
                "aggregation_type": getattr(node, 'aggregation_type', 'count')
            })
        elif isinstance(node, TypeOperationNode):
            result.update({
                "operation": getattr(node, 'operation', ''),
                "target_type": getattr(node, 'target_type', '')
            })

        # Add validation information
        if hasattr(node, '_validation_errors') and hasattr(node, '_is_validated'):
            result["validation"] = {
                "is_validated": getattr(node, '_is_validated', False),
                "is_valid": node.is_valid() if hasattr(node, 'is_valid') else None,
                "errors": getattr(node, '_validation_errors', [])
            }

        # Add metadata if requested
        if self.include_metadata and node.metadata:
            result["metadata"] = self._serialize_metadata(node.metadata)

        # Add SQL generation context
        if hasattr(node, 'sql_fragment') and node.sql_fragment:
            result["sql_fragment"] = node.sql_fragment
        if hasattr(node, 'cte_name') and node.cte_name:
            result["cte_name"] = node.cte_name
        if hasattr(node, 'dependencies') and node.dependencies:
            result["dependencies"] = list(node.dependencies)

        # Recursively serialize children
        if node.children:
            result["children"] = [self._convert_to_dict(child) for child in node.children]

        return result

    def _serialize_metadata(self, metadata: ASTNodeMetadata) -> Dict[str, Any]:
        """Serialize AST node metadata"""
        result = {
            "node_category": metadata.node_category.value,
            "source_text": metadata.source_text,
            "line_number": metadata.line_number,
            "column_number": metadata.column_number
        }

        # Serialize type information
        if metadata.type_info:
            result["type_info"] = {
                "expected_input_type": metadata.type_info.expected_input_type,
                "expected_output_type": metadata.type_info.expected_output_type,
                "sql_data_type": metadata.type_info.sql_data_type.value,
                "is_collection": metadata.type_info.is_collection,
                "is_nullable": metadata.type_info.is_nullable,
                "fhir_type": metadata.type_info.fhir_type
            }

        # Serialize optimization hints
        result["optimization_hints"] = [hint.value for hint in metadata.optimization_hints]

        # Serialize performance metadata
        if metadata.performance:
            result["performance"] = {
                "estimated_selectivity": metadata.performance.estimated_selectivity,
                "supports_indexing": metadata.performance.supports_indexing,
                "memory_intensive": metadata.performance.memory_intensive,
                "cpu_intensive": metadata.performance.cpu_intensive,
                "io_intensive": metadata.performance.io_intensive
            }

        # Serialize CTE context
        if metadata.cte_context:
            result["cte_context"] = {
                "requires_join": metadata.cte_context.requires_join,
                "join_conditions": list(metadata.cte_context.join_conditions),
                "dependent_tables": list(metadata.cte_context.dependent_tables),
                "can_be_subquery": metadata.cte_context.can_be_subquery,
                "requires_window_function": metadata.cte_context.requires_window_function
            }

        # Serialize population analytics
        if metadata.population_analytics:
            result["population_analytics"] = {
                "supports_population_query": metadata.population_analytics.supports_population_query,
                "requires_patient_context": metadata.population_analytics.requires_patient_context,
                "can_be_population_filtered": metadata.population_analytics.can_be_population_filtered,
                "aggregation_level": metadata.population_analytics.aggregation_level
            }

        # Custom attributes
        if metadata.custom_attributes:
            result["custom_attributes"] = metadata.custom_attributes.copy()

        return result

    def _calculate_ast_stats(self, root: FHIRPathASTNode) -> Dict[str, Any]:
        """Calculate statistics about the AST"""
        stats = {
            "total_nodes": 0,
            "max_depth": 0,
            "node_type_counts": {},
            "metadata_coverage": 0,
            "validation_status": {
                "validated_nodes": 0,
                "valid_nodes": 0,
                "invalid_nodes": 0
            }
        }

        self._collect_stats_recursive(root, stats, 0)

        # Calculate percentages
        if stats["total_nodes"] > 0:
            stats["metadata_coverage"] = (stats["metadata_coverage"] / stats["total_nodes"]) * 100

        return stats

    def _collect_stats_recursive(self, node: FHIRPathASTNode, stats: Dict[str, Any], depth: int) -> None:
        """Recursively collect statistics"""
        stats["total_nodes"] += 1
        stats["max_depth"] = max(stats["max_depth"], depth)

        # Count node types
        node_type = node.__class__.__name__
        stats["node_type_counts"][node_type] = stats["node_type_counts"].get(node_type, 0) + 1

        # Check metadata coverage
        if node.metadata:
            stats["metadata_coverage"] += 1

        # Check validation status
        if hasattr(node, '_is_validated') and getattr(node, '_is_validated', False):
            stats["validation_status"]["validated_nodes"] += 1
            if hasattr(node, 'is_valid') and node.is_valid():
                stats["validation_status"]["valid_nodes"] += 1
            else:
                stats["validation_status"]["invalid_nodes"] += 1

        # Recurse through children
        for child in node.children:
            self._collect_stats_recursive(child, stats, depth + 1)

    def _node_to_xml(self, node: FHIRPathASTNode, xml_lines: List[str], indent_level: int) -> None:
        """Convert node to XML representation"""
        indent = "  " * indent_level
        xml_lines.append(f'{indent}<node type="{node.node_type}" class="{node.__class__.__name__}">')
        xml_lines.append(f'{indent}  <text>{self._escape_xml(node.text)}</text>')

        if self.include_metadata and node.metadata:
            xml_lines.append(f'{indent}  <metadata>')
            xml_lines.append(f'{indent}    <category>{node.metadata.node_category.value}</category>')
            if node.metadata.type_info:
                xml_lines.append(f'{indent}    <sql_type>{node.metadata.type_info.sql_data_type.value}</sql_type>')
            xml_lines.append(f'{indent}  </metadata>')

        if node.children:
            xml_lines.append(f'{indent}  <children>')
            for child in node.children:
                self._node_to_xml(child, xml_lines, indent_level + 2)
            xml_lines.append(f'{indent}  </children>')

        xml_lines.append(f'{indent}</node>')

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))

    def _json_serializer(self, obj) -> Any:
        """Custom JSON serializer for special objects"""
        if hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):  # dataclass or custom objects
            return obj.__dict__
        return str(obj)


class ASTDeserializer:
    """
    AST deserializer for loading serialized AST trees

    Supports all formats provided by ASTSerializer and reconstructs
    fully functional AST nodes with metadata.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def deserialize(self, data: Union[str, bytes], format_type: str = SerializationFormat.JSON) -> Optional[FHIRPathASTNode]:
        """
        Deserialize AST from specified format

        Args:
            data: Serialized AST data
            format_type: Format of the serialized data

        Returns:
            Reconstructed AST root node or None if deserialization fails
        """
        try:
            if format_type == SerializationFormat.JSON:
                return self._deserialize_from_json(data)
            elif format_type == SerializationFormat.JSON_COMPRESSED:
                return self._deserialize_from_json_compressed(data)
            elif format_type == SerializationFormat.PICKLE:
                return self._deserialize_from_pickle(data)
            elif format_type == SerializationFormat.PICKLE_COMPRESSED:
                return self._deserialize_from_pickle_compressed(data)
            elif format_type == SerializationFormat.YAML:
                return self._deserialize_from_yaml(data)
            else:
                raise ValueError(f"Unsupported deserialization format: {format_type}")

        except Exception as e:
            self.logger.error(f"Deserialization failed: {e}")
            return None

    def _deserialize_from_json(self, json_str: str) -> Optional[FHIRPathASTNode]:
        """Deserialize AST from JSON format"""
        data = json.loads(json_str)
        if "ast" in data:
            return self._dict_to_node(data["ast"])
        return self._dict_to_node(data)

    def _deserialize_from_json_compressed(self, compressed_data: bytes) -> Optional[FHIRPathASTNode]:
        """Deserialize AST from compressed JSON format"""
        json_str = gzip.decompress(compressed_data).decode('utf-8')
        return self._deserialize_from_json(json_str)

    def _deserialize_from_pickle(self, pickle_data: bytes) -> Optional[FHIRPathASTNode]:
        """Deserialize AST from pickle format"""
        data = pickle.loads(pickle_data)
        return self._dict_to_node(data)

    def _deserialize_from_pickle_compressed(self, compressed_data: bytes) -> Optional[FHIRPathASTNode]:
        """Deserialize AST from compressed pickle format"""
        pickle_data = gzip.decompress(compressed_data)
        return self._deserialize_from_pickle(pickle_data)

    def _deserialize_from_yaml(self, yaml_str: str) -> Optional[FHIRPathASTNode]:
        """Deserialize AST from YAML format"""
        try:
            import yaml
            data = yaml.safe_load(yaml_str)
            return self._dict_to_node(data)
        except ImportError:
            raise ImportError("PyYAML is required for YAML deserialization")

    def _dict_to_node(self, node_dict: Dict[str, Any]) -> Optional[FHIRPathASTNode]:
        """Convert dictionary representation back to AST node"""
        try:
            # Determine node class
            class_name = node_dict.get("class_name", "FHIRPathASTNode")
            node_type = node_dict.get("node_type", "unknown")
            text = node_dict.get("text", "")

            # Create appropriate node type
            node = self._create_node_by_class_name(class_name, node_type, text)
            if not node:
                return None

            # Restore node-specific properties
            self._restore_node_properties(node, node_dict)

            # Restore metadata if present
            if "metadata" in node_dict:
                node.metadata = self._deserialize_metadata(node_dict["metadata"])

            # Restore SQL context
            if "sql_fragment" in node_dict:
                node.sql_fragment = node_dict["sql_fragment"]
            if "cte_name" in node_dict:
                node.cte_name = node_dict["cte_name"]
            if "dependencies" in node_dict:
                node.dependencies = list(node_dict["dependencies"])

            # Recursively restore children
            if "children" in node_dict:
                for child_dict in node_dict["children"]:
                    child_node = self._dict_to_node(child_dict)
                    if child_node:
                        node.add_child(child_node)

            return node

        except Exception as e:
            self.logger.error(f"Error converting dict to node: {e}")
            return None

    def _create_node_by_class_name(self, class_name: str, node_type: str, text: str) -> Optional[FHIRPathASTNode]:
        """Create node instance by class name"""
        if class_name == "LiteralNode":
            return LiteralNode(node_type, text)
        elif class_name == "IdentifierNode":
            return IdentifierNode(node_type, text)
        elif class_name == "FunctionCallNode":
            return FunctionCallNode(node_type, text)
        elif class_name == "OperatorNode":
            return OperatorNode(node_type, text)
        elif class_name == "ConditionalNode":
            return ConditionalNode(node_type, text)
        elif class_name == "AggregationNode":
            return AggregationNode(node_type, text)
        elif class_name == "TypeOperationNode":
            return TypeOperationNode(node_type, text)
        else:
            # Fallback to base class
            return FHIRPathASTNode.__new__(FHIRPathASTNode)

    def _restore_node_properties(self, node: FHIRPathASTNode, node_dict: Dict[str, Any]) -> None:
        """Restore node-specific properties"""
        if isinstance(node, LiteralNode):
            if "value" in node_dict:
                node.value = node_dict["value"]
            if "literal_type" in node_dict:
                node.literal_type = node_dict["literal_type"]

        elif isinstance(node, IdentifierNode):
            if "identifier" in node_dict:
                node.identifier = node_dict["identifier"]
            if "is_qualified" in node_dict:
                node.is_qualified = node_dict["is_qualified"]

        elif isinstance(node, FunctionCallNode):
            if "function_name" in node_dict:
                node.function_name = node_dict["function_name"]

        elif isinstance(node, OperatorNode):
            if "operator" in node_dict:
                node.operator = node_dict["operator"]
            if "operator_type" in node_dict:
                node.operator_type = node_dict["operator_type"]

        elif isinstance(node, ConditionalNode):
            if "condition_type" in node_dict:
                node.condition_type = node_dict["condition_type"]

        elif isinstance(node, AggregationNode):
            if "aggregation_function" in node_dict:
                node.aggregation_function = node_dict["aggregation_function"]
            if "aggregation_type" in node_dict:
                node.aggregation_type = node_dict["aggregation_type"]

        elif isinstance(node, TypeOperationNode):
            if "operation" in node_dict:
                node.operation = node_dict["operation"]
            if "target_type" in node_dict:
                node.target_type = node_dict["target_type"]

    def _deserialize_metadata(self, metadata_dict: Dict[str, Any]) -> ASTNodeMetadata:
        """Deserialize metadata from dictionary"""
        from ..parser_core.metadata_types import (
            MetadataBuilder, NodeCategory, OptimizationHint, SQLDataType,
            TypeInformation, PerformanceMetadata, CTEGenerationContext,
            PopulationAnalyticsMetadata
        )

        builder = MetadataBuilder()

        # Basic metadata
        if "node_category" in metadata_dict:
            builder.with_category(NodeCategory(metadata_dict["node_category"]))

        if "source_text" in metadata_dict:
            builder.with_source_location(
                metadata_dict["source_text"],
                metadata_dict.get("line_number"),
                metadata_dict.get("column_number")
            )

        # Type information
        if "type_info" in metadata_dict:
            type_info_dict = metadata_dict["type_info"]
            type_info = TypeInformation(
                expected_input_type=type_info_dict.get("expected_input_type"),
                expected_output_type=type_info_dict.get("expected_output_type"),
                sql_data_type=SQLDataType(type_info_dict.get("sql_data_type", "unknown")),
                is_collection=type_info_dict.get("is_collection", False),
                is_nullable=type_info_dict.get("is_nullable", True),
                fhir_type=type_info_dict.get("fhir_type")
            )
            builder.with_type_info(type_info)

        # Optimization hints
        if "optimization_hints" in metadata_dict:
            for hint_value in metadata_dict["optimization_hints"]:
                try:
                    hint = OptimizationHint(hint_value)
                    builder.with_optimization_hint(hint)
                except ValueError:
                    self.logger.warning(f"Unknown optimization hint: {hint_value}")

        # Custom attributes
        if "custom_attributes" in metadata_dict:
            for key, value in metadata_dict["custom_attributes"].items():
                builder.with_custom_attribute(key, value)

        return builder.build()


# Utility functions for common serialization scenarios
def serialize_ast_for_debugging(root: FHIRPathASTNode) -> str:
    """Serialize AST in human-readable format for debugging"""
    serializer = ASTSerializer(include_metadata=True, include_stats=True)
    return serializer.serialize(root, SerializationFormat.JSON)


def serialize_ast_for_caching(root: FHIRPathASTNode) -> bytes:
    """Serialize AST in efficient format for caching"""
    serializer = ASTSerializer(include_metadata=True, include_stats=False)
    return serializer.serialize(root, SerializationFormat.PICKLE_COMPRESSED)


def deserialize_ast_from_cache(cached_data: bytes) -> Optional[FHIRPathASTNode]:
    """Deserialize AST from cached data"""
    deserializer = ASTDeserializer()
    return deserializer.deserialize(cached_data, SerializationFormat.PICKLE_COMPRESSED)