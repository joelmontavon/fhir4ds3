"""FHIRPath AST-to-SQL Translation Module.

This module provides the core translation layer that converts FHIRPath Abstract Syntax
Trees (AST) into database-specific SQL fragments. This is a critical component of FHIR4DS's
unified FHIRPath architecture, enabling population-scale healthcare analytics.

The translation follows these core principles:
- **CTE-First Design**: All operations designed for Common Table Expression wrapping
- **Thin Dialects**: Database-specific syntax only, no business logic in dialects
- **Population-First**: All patterns maintain population-scale analytics capability
- **Database Agnostic**: Same translation logic works with DuckDB and PostgreSQL

Key Components:
    - SQLFragment: Data structure representing SQL fragment output from translation
    - TranslationContext: Context manager tracking state during AST traversal
    - ASTToSQLTranslator: Main translator class using visitor pattern
    - FHIRPathExecutor: End-to-end execution pipeline orchestrator

Example Usage:
    >>> from fhir4ds.fhirpath.sql import ASTToSQLTranslator, SQLFragment
    >>> from fhir4ds.fhirpath.parser import FHIRPathParser
    >>> from fhir4ds.dialects.duckdb import DuckDBDialect
    >>>
    >>> # Create translator for DuckDB
    >>> translator = ASTToSQLTranslator(DuckDBDialect(), resource_type="Patient")
    >>>
    >>> # Parse and translate directly (SP-023-004: no adapter needed)
    >>> parser = FHIRPathParser()
    >>> ast = parser.parse("Patient.name.given").get_ast()
    >>> fragments = translator.translate(ast)

Architecture:
    This module is part of the translation pipeline:

    Parser (PEP-002) → AST-to-SQL Translator (PEP-003) → CTE Manager (PEP-004)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
                         This module fills this gap

    SP-023-004/SP-023-006: The translator works directly with the parser's EnhancedASTNode
    output. The EnhancedASTNode.accept() method handles visitor dispatch correctly,
    eliminating the need for any intermediate AST conversion step.

Module: fhir4ds.fhirpath.sql
PEP: PEP-003 - FHIRPath AST-to-SQL Translator
Created: 2025-09-29
Updated: SP-023-004 (2025-12-17) - Direct EnhancedASTNode translation
Author: FHIR4DS Development Team
"""

from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.context import TranslationContext
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor

__all__ = [
    "SQLFragment",
    "TranslationContext",
    "ASTToSQLTranslator",
    "FHIRPathExecutor",
]

__version__ = "0.1.0"
