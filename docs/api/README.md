# API Reference

This section provides a complete API reference for all public modules, classes, and functions in FHIR4DS.

## FHIRPath AST-to-SQL Translator

**Module**: `fhir4ds.fhirpath.sql`
**PEP**: PEP-003 - FHIRPath AST-to-SQL Translator

The FHIRPath AST-to-SQL Translator provides the core translation layer that converts FHIRPath Abstract Syntax Trees (AST) into database-specific SQL fragments for population-scale healthcare analytics.

### Documentation

- **[API Reference](./translator-api-reference.md)** - Complete API documentation for all classes and methods
  - `ASTToSQLTranslator` - Main translator class
  - `SQLFragment` - SQL fragment data structure
  - `TranslationContext` - Context management during translation
  - ~~`ASTAdapter`~~ - Removed in SP-023-006 (direct translation now supported)

- **[Usage Examples](./translator-usage-examples.md)** - 15 comprehensive examples with real FHIRPath expressions
  - Simple path expressions
  - Array filtering and operations
  - Complex healthcare expressions
  - Multi-database translation
  - Quality measure patterns

- **[Integration Guide](./translator-integration-guide.md)** - Integration with PEP-004 CTE Builder
  - SQLFragment integration contract
  - CTE generation patterns
  - Dependency resolution
  - Monolithic query assembly

- **[Troubleshooting Guide](./translator-troubleshooting.md)** - Common issues and solutions
  - Translation errors
  - Parser integration issues
  - Dialect-specific problems
  - Performance troubleshooting
  - Debugging techniques

### Quick Start

```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect

# Parse FHIRPath expression
parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official')")

# Convert AST
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

# Translate to SQL
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# Process fragments
for fragment in fragments:
    print(f"SQL: {fragment.expression}")
```

### Architecture

The translator is part of FHIR4DS's unified FHIRPath architecture:

```
Parser (PEP-002) → AST-to-SQL Translator (PEP-003) → CTE Builder (PEP-004)
```

**Key Principles**:
- **CTE-First Design**: All operations designed for Common Table Expression wrapping
- **Thin Dialects**: Database-specific syntax only, no business logic in dialects
- **Population-First**: All patterns maintain population-scale analytics capability
- **Database Agnostic**: Same translation logic works with DuckDB and PostgreSQL

---

## Additional Modules

*Additional API documentation coming soon...*
