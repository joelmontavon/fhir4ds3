"""
FHIR4DS FHIRPath Parser Module

Enhanced FHIRPath parser integrating fhirpath-py with FHIR4DS-specific
AST extensions and metadata for CTE generation and population analytics.
"""

from .enhanced_parser import (
    EnhancedFHIRPathParser,
    ParseResult,
    ExpressionValidator,
    create_enhanced_parser
)

from .ast_extensions import (
    EnhancedASTNode,
    ASTNodeFactory,
    ASTAnalyzer
)
from .metadata_types import (
    ASTNodeMetadata,
    NodeCategory,
    OptimizationHint,
    SQLDataType,
    TypeInformation,
    PerformanceMetadata,
    CTEGenerationContext,
    PopulationAnalyticsMetadata,
    MetadataBuilder,
    METADATA_TEMPLATES
)

# Also expose main parser classes (need to avoid circular import)
try:
    # Import after other imports to avoid circular dependency
    import sys
    if 'fhir4ds.fhirpath.parser' not in sys.modules or getattr(sys.modules['fhir4ds.fhirpath.parser'], '_initializing', False):
        # Mark as initializing to prevent circular import
        sys.modules[__name__]._initializing = True

        # Import the main parser classes from the parent parser.py file
        import importlib.util
        import os

        parser_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'parser.py')
        spec = importlib.util.spec_from_file_location("main_parser", parser_file)
        if spec and spec.loader:
            main_parser = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_parser)
            FHIRPathParser = main_parser.FHIRPathParser
            FHIRPathExpression = main_parser.FHIRPathExpression
        else:
            FHIRPathParser = None
            FHIRPathExpression = None

        # Clear initializing flag
        delattr(sys.modules[__name__], '_initializing')
    else:
        FHIRPathParser = None
        FHIRPathExpression = None

except Exception:
    FHIRPathParser = None
    FHIRPathExpression = None

__all__ = [
    # Main parser components
    "EnhancedFHIRPathParser",
    "ParseResult",
    "ExpressionValidator",
    "create_enhanced_parser",

    # AST components
    "EnhancedASTNode",
    "ASTNodeFactory",
    "ASTAnalyzer",

    # Metadata types
    "ASTNodeMetadata",
    "NodeCategory",
    "OptimizationHint",
    "SQLDataType",
    "TypeInformation",
    "PerformanceMetadata",
    "CTEGenerationContext",
    "PopulationAnalyticsMetadata",
    "MetadataBuilder",
    "METADATA_TEMPLATES"
]

# Add main parser classes if available
if FHIRPathParser is not None:
    __all__.extend(["FHIRPathParser", "FHIRPathExpression"])

# Version information
__version__ = "0.1.0"
__author__ = "FHIR4DS Development Team"