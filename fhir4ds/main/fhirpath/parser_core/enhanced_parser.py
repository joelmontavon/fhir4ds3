"""
Enhanced FHIRPath Parser for FHIR4DS

This module provides an enhanced FHIRPath parser that integrates fhirpath-py
with FHIR4DS-specific AST extensions and metadata for CTE generation.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import hashlib
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass

from .ast_extensions import EnhancedASTNode, ASTNodeFactory, ASTAnalyzer
from .metadata_types import (
    ASTNodeMetadata, NodeCategory, OptimizationHint,
    MetadataBuilder, TypeInformation, SQLDataType,
    PerformanceMetadata, CTEGenerationContext, PopulationAnalyticsMetadata
)
from ..exceptions import (
    FHIRPathSyntaxError, FHIRPathGrammarError, FHIRPathTokenError,
    FHIRPathParseError, ErrorContext, ErrorLocation, ErrorSeverity,
    build_error_context, log_fhirpath_error
)

# Import forked fhirpath-py components
try:
    from .fhirpath_py import parse as fhirpath_parse
    FHIRPATHPY_AVAILABLE = True
except ImportError:
    FHIRPATHPY_AVAILABLE = False
    logging.warning("fhirpath-py fork not available - using stub implementation")


@dataclass
class ParseResult:
    """Result of parsing a FHIRPath expression"""
    ast: Optional[EnhancedASTNode] = None
    is_valid: bool = False
    error_message: Optional[str] = None
    error_context: Optional[ErrorContext] = None
    parse_exception: Optional[Exception] = None
    parse_time_ms: Optional[float] = None
    complexity_analysis: Optional[Dict[str, Any]] = None
    optimization_opportunities: Optional[List[Dict[str, Any]]] = None


@dataclass
class CacheEntry:
    """Cache entry for parsed expressions"""
    parse_result: ParseResult
    created_time: float
    last_accessed: float
    access_count: int = 0

    def mark_accessed(self) -> None:
        """Mark this entry as accessed"""
        self.last_accessed = time.time()
        self.access_count += 1


class ExpressionCache:
    """
    Smart cache for parsed FHIRPath expressions

    Features:
    - LRU eviction with time-based cleanup
    - Thread-safe operations
    - Memory usage monitoring
    - Cache hit/miss statistics
    """

    def __init__(self, max_size: int = 1000, max_age_seconds: float = 3600):
        """
        Initialize expression cache

        Args:
            max_size: Maximum number of cached entries
            max_age_seconds: Maximum age for cache entries (1 hour default)
        """
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.cleanups = 0

    def _generate_key(self, expression: str, analyze_complexity: bool, find_optimizations: bool) -> str:
        """Generate cache key for expression and options"""
        key_data = f"{expression}:{analyze_complexity}:{find_optimizations}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, expression: str, analyze_complexity: bool = True,
            find_optimizations: bool = True) -> Optional[ParseResult]:
        """Get cached parse result if available"""
        key = self._generate_key(expression, analyze_complexity, find_optimizations)

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self.misses += 1
                return None

            # Check if entry is expired
            if time.time() - entry.created_time > self.max_age_seconds:
                del self._cache[key]
                self.misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.mark_accessed()
            self.hits += 1

            # Return a copy to avoid mutation
            return ParseResult(
                ast=entry.parse_result.ast,  # AST nodes can be reused safely
                is_valid=entry.parse_result.is_valid,
                error_message=entry.parse_result.error_message,
                parse_time_ms=entry.parse_result.parse_time_ms,
                complexity_analysis=entry.parse_result.complexity_analysis,
                optimization_opportunities=entry.parse_result.optimization_opportunities
            )

    def put(self, expression: str, parse_result: ParseResult,
            analyze_complexity: bool = True, find_optimizations: bool = True) -> None:
        """Store parse result in cache"""
        key = self._generate_key(expression, analyze_complexity, find_optimizations)

        with self._lock:
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self.evictions += 1

            # Create cache entry
            current_time = time.time()
            entry = CacheEntry(
                parse_result=parse_result,
                created_time=current_time,
                last_accessed=current_time
            )

            self._cache[key] = entry

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count cleaned up"""
        current_time = time.time()
        expired_keys = []

        with self._lock:
            for key, entry in self._cache.items():
                if current_time - entry.created_time > self.max_age_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                self.cleanups += 1

            return len(expired_keys)

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "cleanups": self.cleanups,
                "max_age_seconds": self.max_age_seconds
            }

    def clear(self) -> None:
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.cleanups = 0


class EnhancedFHIRPathParser:
    """
    Enhanced FHIRPath parser with FHIR4DS-specific AST extensions

    Integrates fhirpath-py parser with enhanced AST nodes containing
    metadata for CTE generation and population-scale analytics.
    """

    def __init__(self, database_type: str = "duckdb", enable_cache: bool = True,
                 cache_size: int = 1000, cache_ttl_seconds: float = 3600):
        """
        Initialize the enhanced parser

        Args:
            database_type: Target database type for optimization hints
            enable_cache: Whether to enable expression caching
            cache_size: Maximum number of cached expressions
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.database_type = database_type
        self.parse_count = 0
        self.total_parse_time = 0.0
        self.logger = logging.getLogger(__name__)

        # Initialize cache if enabled
        self.enable_cache = enable_cache
        self.cache = ExpressionCache(cache_size, cache_ttl_seconds) if enable_cache else None

        if not FHIRPATHPY_AVAILABLE:
            self.logger.warning("fhirpathpy not available - limited functionality")

    def parse(self, expression: str, analyze_complexity: bool = True,
              find_optimizations: bool = True) -> ParseResult:
        """
        Parse a FHIRPath expression into an enhanced AST

        Args:
            expression: FHIRPath expression to parse
            analyze_complexity: Whether to perform complexity analysis
            find_optimizations: Whether to find optimization opportunities

        Returns:
            ParseResult containing enhanced AST and analysis
        """
        start_time = time.time()

        try:
            # Check cache first
            if self.enable_cache and self.cache:
                cached_result = self.cache.get(expression, analyze_complexity, find_optimizations)
                if cached_result is not None:
                    # Still count as parse for statistics, but with minimal time
                    self.parse_count += 1
                    self.total_parse_time += 0.01  # Minimal cache lookup time
                    return cached_result

            self.parse_count += 1

            if not expression or expression.strip() == "":
                error_context = build_error_context(
                    expression=expression,
                    severity=ErrorSeverity.ERROR,
                    category="EMPTY_EXPRESSION",
                    operation="parse"
                )
                error = FHIRPathSyntaxError(
                    "Empty or whitespace-only expression provided",
                    expression or "",
                    error_context=error_context
                )
                return ParseResult(
                    is_valid=False,
                    error_message=str(error),
                    error_context=error_context,
                    parse_exception=error
                )

            # Use fhirpath-py if available, otherwise use stub implementation
            if FHIRPATHPY_AVAILABLE:
                enhanced_ast = self._parse_with_fhirpathpy(expression)
            else:
                enhanced_ast = self._parse_with_stub(expression)

            if enhanced_ast is None:
                return ParseResult(
                    is_valid=False,
                    error_message="Failed to parse expression"
                )

            # Lazy evaluation: defer expensive metadata generation
            # Only add basic metadata, defer expensive operations
            self._add_basic_metadata(enhanced_ast, expression)

            # Calculate parse time
            parse_time = (time.time() - start_time) * 1000
            self.total_parse_time += parse_time

            # Create base result
            result = ParseResult(
                ast=enhanced_ast,
                is_valid=True,
                parse_time_ms=parse_time
            )

            # Lazy analysis: only perform if requested and not cached
            if analyze_complexity:
                result.complexity_analysis = self._get_complexity_analysis(enhanced_ast)

            if find_optimizations:
                result.optimization_opportunities = self._get_optimization_opportunities(enhanced_ast)

            # Cache the result
            if self.enable_cache and self.cache:
                self.cache.put(expression, result, analyze_complexity, find_optimizations)

            return result

        except Exception as e:
            # Create comprehensive error context
            error_context = build_error_context(
                expression=expression,
                severity=ErrorSeverity.ERROR,
                category="PARSE_ERROR",
                operation="parse"
            )

            # Convert to appropriate FHIRPath exception if needed
            if not isinstance(e, FHIRPathParseError):
                parse_error = FHIRPathParseError(
                    f"Failed to parse expression: {str(e)}",
                    error_context=error_context,
                    cause=e
                )
            else:
                parse_error = e
                if parse_error.error_context is None:
                    parse_error.error_context = error_context

            # Log the error with proper sanitization
            log_fhirpath_error(self.logger, parse_error, error_context)

            return ParseResult(
                is_valid=False,
                error_message=str(parse_error),
                error_context=error_context,
                parse_exception=parse_error
            )

    def _parse_with_fhirpathpy(self, expression: str) -> Optional[EnhancedASTNode]:
        """Parse using fhirpath-py library"""
        try:
            # Parse with fhirpath-py
            fhirpath_ast = fhirpath_parse(expression)

            # Convert to enhanced AST
            if fhirpath_ast:
                enhanced_ast = ASTNodeFactory.create_from_fhirpath_node(fhirpath_ast)

                # Check if error recovery was used for missing closing delimiters AT THE END
                # This indicates incomplete expressions, not fhirpathpy parsing quirks
                ast_text = str(enhanced_ast.text)
                if enhanced_ast and (ast_text.endswith("<missing ')'>") or
                                     ast_text.endswith("<missing '}'>") or
                                     ast_text.endswith("<missing ']'>")):
                    raise FHIRPathSyntaxError(
                        "Parser recovered from syntax error - expression is incomplete or invalid",
                        expression
                    )

                return enhanced_ast
            else:
                # Create specific error for null result
                raise FHIRPathSyntaxError(
                    "Parser returned null result - expression may be syntactically invalid",
                    expression
                )

        except Exception as e:
            # Try to extract location information from fhirpath-py errors
            line, column = self._extract_error_location(str(e))

            if isinstance(e, FHIRPathParseError):
                # Re-raise FHIRPath errors as-is
                raise e
            else:
                # Convert other exceptions to appropriate FHIRPath exceptions
                error_message = self._classify_parse_error(str(e), expression)

                if "syntax" in str(e).lower() or "token" in str(e).lower():
                    raise FHIRPathSyntaxError(
                        error_message,
                        expression,
                        line=line,
                        column=column
                    ) from e
                elif "grammar" in str(e).lower() or "rule" in str(e).lower():
                    raise FHIRPathGrammarError(
                        error_message,
                        rule="unknown",
                        error_context=build_error_context(
                            expression=expression,
                            line=line,
                            column=column
                        )
                    ) from e
                else:
                    raise FHIRPathParseError(
                        error_message,
                        error_context=build_error_context(
                            expression=expression,
                            line=line,
                            column=column
                        )
                    ) from e

    def _parse_with_stub(self, expression: str) -> Optional[EnhancedASTNode]:
        """Parse using stub implementation for testing"""
        try:
            # Check for syntax errors first
            if ".." in expression:
                raise ValueError("Invalid syntax: consecutive dots")
            if expression.count("(") != expression.count(")"):
                raise ValueError("Unmatched parentheses")

            # Simple stub parsing for basic expressions
            root = EnhancedASTNode(
                node_type="expression",
                text=expression
            )

            # Basic tokenization
            if "." in expression:
                parts = expression.split(".")
                current_node = root

                for i, part in enumerate(parts):
                    if not part.strip():  # Empty part indicates syntax error
                        raise ValueError("Invalid path expression")

                    if "(" in part and ")" in part:
                        # Function call
                        func_name = part.split("(")[0]
                        func_node = ASTNodeFactory.create_function_node(func_name, part)
                        current_node.add_child(func_node)
                        current_node = func_node
                    else:
                        # Path component
                        path_node = ASTNodeFactory.create_path_node(part)
                        current_node.add_child(path_node)
                        current_node = path_node
            else:
                # Single component
                if "(" in expression and ")" in expression:
                    func_name = expression.split("(")[0]
                    func_node = ASTNodeFactory.create_function_node(func_name, expression)
                    root.add_child(func_node)
                else:
                    path_node = ASTNodeFactory.create_path_node(expression)
                    root.add_child(path_node)

            return root

        except Exception as e:
            self.logger.error(f"Stub parsing failed: {str(e)}")
            return None

    def _add_basic_metadata(self, ast: EnhancedASTNode, original_expression: str) -> None:
        """Add only essential metadata for basic functionality"""
        try:
            # Add minimal metadata required for basic operation
            self._add_essential_metadata(ast)

        except Exception as e:
            self.logger.error(f"Error adding basic metadata: {str(e)}")

    def _add_essential_metadata(self, node: EnhancedASTNode) -> None:
        """Add only essential metadata required for basic functionality"""
        if not node.metadata:
            from .metadata_types import MetadataBuilder
            node.metadata = MetadataBuilder.create_node_metadata(node.node_type, node.text)

        # Recursively process children
        for child in node.children:
            self._add_essential_metadata(child)

    def _get_complexity_analysis(self, ast: EnhancedASTNode) -> Optional[Dict[str, Any]]:
        """Lazy complexity analysis - only compute when needed"""
        try:
            # Ensure full metadata is available before analysis
            self._ensure_full_metadata(ast)
            return ASTAnalyzer.analyze_complexity(ast)
        except Exception as e:
            self.logger.error(f"Error in complexity analysis: {str(e)}")
            return None

    def _get_optimization_opportunities(self, ast: EnhancedASTNode) -> Optional[List[Dict[str, Any]]]:
        """Lazy optimization analysis - only compute when needed"""
        try:
            # Ensure full metadata is available before analysis
            self._ensure_full_metadata(ast)
            return ASTAnalyzer.find_optimization_opportunities(ast)
        except Exception as e:
            self.logger.error(f"Error in optimization analysis: {str(e)}")
            return None

    def _ensure_full_metadata(self, ast: EnhancedASTNode) -> None:
        """Ensure full metadata is available (lazy loading)"""
        # Check if full metadata already exists
        if hasattr(ast, '_full_metadata_loaded') and ast._full_metadata_loaded:
            return

        # Add complete metadata
        self._add_database_specific_hints(ast)
        self._add_population_analytics_metadata(ast)
        self._add_performance_metadata(ast)
        self._add_cte_generation_metadata(ast)

        # Mark as fully loaded
        ast._full_metadata_loaded = True

    def _enhance_ast_metadata(self, ast: EnhancedASTNode, original_expression: str) -> None:
        """Enhance AST nodes with FHIR4DS-specific metadata (legacy method)"""
        self._ensure_full_metadata(ast)

    def _add_database_specific_hints(self, node: EnhancedASTNode) -> None:
        """Add database-specific optimization hints"""
        if not node.metadata:
            return

        # Add database-specific hints based on node type and database
        if self.database_type == "duckdb":
            if node.metadata.node_category == NodeCategory.AGGREGATION:
                node.metadata.optimization_hints.add(OptimizationHint.VECTORIZABLE)
        elif self.database_type == "postgresql":
            if node.metadata.node_category == NodeCategory.PATH_EXPRESSION:
                node.metadata.optimization_hints.add(OptimizationHint.INDEX_FRIENDLY)

        # Recursively process children
        for child in node.children:
            self._add_database_specific_hints(child)

    def _add_population_analytics_metadata(self, node: EnhancedASTNode) -> None:
        """Add population analytics metadata"""
        if not node.metadata:
            return

        # Determine if node supports population queries
        if node.metadata.node_category in [NodeCategory.AGGREGATION, NodeCategory.CONDITIONAL]:
            node.metadata.population_analytics.supports_population_query = True
            node.metadata.population_analytics.can_be_population_filtered = True

        # Check if node requires patient context
        if "patient" in node.text.lower() or "Patient" in node.text:
            node.metadata.population_analytics.requires_patient_context = True
            node.metadata.population_analytics.aggregation_level = "patient"

        # Recursively process children
        for child in node.children:
            self._add_population_analytics_metadata(child)

    def _add_performance_metadata(self, node: EnhancedASTNode) -> None:
        """Add performance-related metadata"""
        if not node.metadata:
            return

        # Estimate selectivity for conditional nodes
        if node.metadata.node_category == NodeCategory.CONDITIONAL:
            # Simple heuristic - actual implementation would be more sophisticated
            if "exists" in node.text.lower():
                node.metadata.performance.estimated_selectivity = 0.5
            elif "=" in node.text:
                node.metadata.performance.estimated_selectivity = 0.1
            else:
                node.metadata.performance.estimated_selectivity = 0.3

        # Mark CPU-intensive operations
        if node.metadata.node_category == NodeCategory.AGGREGATION:
            node.metadata.performance.cpu_intensive = True

        # Mark memory-intensive operations
        if "count" in node.text.lower() and node.metadata.node_category == NodeCategory.AGGREGATION:
            node.metadata.performance.memory_intensive = False  # COUNT is usually memory-efficient
        elif node.metadata.node_category == NodeCategory.AGGREGATION:
            node.metadata.performance.memory_intensive = True

        # Recursively process children
        for child in node.children:
            self._add_performance_metadata(child)

    def _add_cte_generation_metadata(self, node: EnhancedASTNode) -> None:
        """Add CTE generation metadata"""
        if not node.metadata:
            return

        # Determine if node requires joins
        if node.metadata.node_category == NodeCategory.PATH_EXPRESSION:
            if "." in node.text:
                node.metadata.cte_context.requires_join = True
                # Add dependent tables based on path structure
                parts = node.text.split(".")
                if len(parts) > 1:
                    node.metadata.cte_context.dependent_tables.add(parts[0].lower())

        # Check if node can be a subquery
        if node.metadata.node_category in [NodeCategory.AGGREGATION, NodeCategory.CONDITIONAL]:
            node.metadata.cte_context.can_be_subquery = True

        # Check if window functions are needed
        if node.metadata.node_category == NodeCategory.FUNCTION_CALL:
            if any(func in node.text.lower() for func in ["first", "last", "tail"]):
                node.metadata.cte_context.requires_window_function = True

        # Recursively process children
        for child in node.children:
            self._add_cte_generation_metadata(child)

    def get_statistics(self) -> Dict[str, Any]:
        """Get parser usage statistics"""
        avg_parse_time = self.total_parse_time / max(self.parse_count, 1)

        stats = {
            "parse_count": self.parse_count,
            "total_parse_time_ms": self.total_parse_time,
            "average_parse_time_ms": avg_parse_time,
            "database_type": self.database_type,
            "fhirpathpy_available": FHIRPATHPY_AVAILABLE,
            "cache_enabled": self.enable_cache
        }

        # Add cache statistics if available
        if self.enable_cache and self.cache:
            stats["cache_statistics"] = self.cache.get_statistics()

        return stats

    def reset_statistics(self) -> None:
        """Reset parser statistics"""
        self.parse_count = 0
        self.total_parse_time = 0.0

        # Reset cache statistics if available
        if self.enable_cache and self.cache:
            self.cache.clear()

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries and return count cleaned up"""
        if self.enable_cache and self.cache:
            return self.cache.cleanup_expired()
        return 0

    def configure_cache(self, max_size: int = None, max_age_seconds: float = None) -> None:
        """Reconfigure cache parameters"""
        if self.enable_cache and self.cache:
            if max_size is not None:
                self.cache.max_size = max_size
            if max_age_seconds is not None:
                self.cache.max_age_seconds = max_age_seconds

    def get_memory_usage_estimate(self) -> Dict[str, Any]:
        """Get estimated memory usage"""
        import sys

        memory_stats = {
            "parser_instance_bytes": sys.getsizeof(self),
            "cache_enabled": self.enable_cache
        }

        if self.enable_cache and self.cache:
            cache_stats = self.cache.get_statistics()
            # Rough estimate of cache memory usage
            estimated_cache_bytes = cache_stats["size"] * 1024  # Rough estimate per entry
            memory_stats.update({
                "cache_entries": cache_stats["size"],
                "estimated_cache_bytes": estimated_cache_bytes,
                "cache_hit_rate": cache_stats["hit_rate"]
            })

        return memory_stats

    def _extract_error_location(self, error_message: str) -> tuple[Optional[int], Optional[int]]:
        """
        Extract line and column information from error messages

        Args:
            error_message: Error message from parser

        Returns:
            Tuple of (line, column) if found, otherwise (None, None)
        """
        import re

        # Common patterns for error location
        patterns = [
            r"line\s+(\d+),?\s*column\s+(\d+)",
            r"at\s+line\s+(\d+),?\s*column\s+(\d+)",
            r"position\s+(\d+):(\d+)",
            r"\((\d+),(\d+)\)",
            r"line\s+(\d+)",  # Line only
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    try:
                        return int(groups[0]), int(groups[1])
                    except ValueError:
                        pass
                elif len(groups) == 1:
                    try:
                        return int(groups[0]), None
                    except ValueError:
                        pass

        return None, None

    def _classify_parse_error(self, error_message: str, expression: str) -> str:
        """
        Classify and enhance parse error messages for healthcare users

        Args:
            error_message: Original error message
            expression: FHIRPath expression that failed

        Returns:
            Enhanced error message with healthcare context
        """
        # Common FHIRPath errors and their user-friendly messages
        error_patterns = {
            "unexpected token": "Invalid syntax - unexpected character or operator",
            "missing": "Missing required element in expression",
            "expected": "Invalid syntax - check parentheses, quotes, and operators",
            "no viable alternative": "Invalid expression structure - check function names and operators",
            "mismatched input": "Syntax error - check brackets, parentheses, and quotes",
            "extraneous input": "Extra characters found - remove unexpected elements",
            "token recognition error": "Invalid characters or symbols in expression",
        }

        # Convert to lowercase for pattern matching
        lower_message = error_message.lower()

        # Find matching pattern and provide healthcare-friendly message
        for pattern, friendly_msg in error_patterns.items():
            if pattern in lower_message:
                return f"{friendly_msg}. Original error: {error_message}"

        # Provide context-aware suggestions based on expression content
        suggestions = []

        if "patient" in expression.lower():
            suggestions.append("Check FHIR resource field names (e.g., Patient.name, Patient.birthDate)")

        if "(" in expression and ")" not in expression:
            suggestions.append("Missing closing parenthesis")
        elif ")" in expression and "(" not in expression:
            suggestions.append("Missing opening parenthesis")

        if "'" in expression and expression.count("'") % 2 != 0:
            suggestions.append("Unmatched single quote")

        if '"' in expression and expression.count('"') % 2 != 0:
            suggestions.append("Unmatched double quote")

        base_message = f"Parse error: {error_message}"
        if suggestions:
            base_message += f". Suggestions: {'; '.join(suggestions)}"

        return base_message


class ExpressionValidator:
    """Validator for FHIRPath expressions"""

    @staticmethod
    def validate_expression(expression: str) -> Dict[str, Any]:
        """
        Validate a FHIRPath expression

        Args:
            expression: Expression to validate

        Returns:
            Validation result with details
        """
        issues = []

        # Basic validation
        if not expression or expression.strip() == "":
            issues.append({
                "type": "error",
                "message": "Empty expression"
            })
            return {"is_valid": False, "issues": issues}

        # Check for common syntax issues
        if ".." in expression:
            issues.append({
                "type": "error",
                "message": "Invalid syntax: consecutive dots",
                "suggestion": "Use single dots for path navigation"
            })

        # Check for unmatched parentheses
        paren_count = expression.count("(") - expression.count(")")
        if paren_count != 0:
            issues.append({
                "type": "error",
                "message": f"Unmatched parentheses: {abs(paren_count)} {'opening' if paren_count > 0 else 'closing'} parentheses",
                "suggestion": "Check function call syntax"
            })

        # Check for potential performance issues
        if expression.count(".") > 10:
            issues.append({
                "type": "warning",
                "message": "Deep path expression may impact performance",
                "suggestion": "Consider breaking into smaller expressions"
            })

        # Check for reserved words or patterns
        reserved_patterns = ["select *", "delete", "drop", "truncate"]
        for pattern in reserved_patterns:
            if pattern in expression.lower():
                issues.append({
                    "type": "warning",
                    "message": f"Expression contains potentially problematic pattern: {pattern}",
                    "suggestion": "Review expression for SQL injection risks"
                })

        is_valid = not any(issue["type"] == "error" for issue in issues)

        return {
            "is_valid": is_valid,
            "issues": issues,
            "complexity_estimate": ExpressionValidator._estimate_complexity(expression)
        }

    @staticmethod
    def _estimate_complexity(expression: str) -> str:
        """Estimate expression complexity"""
        score = 0
        score += expression.count(".") * 1  # Path depth
        score += expression.count("(") * 2  # Function calls
        score += len([w for w in ["where", "select", "exists"] if w in expression.lower()]) * 3  # Conditionals

        if score <= 5:
            return "low"
        elif score <= 15:
            return "medium"
        else:
            return "high"


# Factory function for creating parser instances
def create_enhanced_parser(database_type: str = "duckdb",
                          enable_cache: bool = True,
                          cache_size: int = 1000,
                          cache_ttl_seconds: float = 3600) -> EnhancedFHIRPathParser:
    """
    Create an enhanced FHIRPath parser instance with optimization features

    Args:
        database_type: Target database type for optimization
        enable_cache: Whether to enable expression caching
        cache_size: Maximum number of cached expressions
        cache_ttl_seconds: Cache time-to-live in seconds

    Returns:
        Configured enhanced parser instance with optimizations
    """
    return EnhancedFHIRPathParser(
        database_type=database_type,
        enable_cache=enable_cache,
        cache_size=cache_size,
        cache_ttl_seconds=cache_ttl_seconds
    )