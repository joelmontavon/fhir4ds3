# FHIRPath Translator Troubleshooting Guide

**Version**: 0.1.0
**Module**: `fhir4ds.fhirpath.sql`
**Task**: SP-005-023 - API Documentation and Examples

---

## Overview

This guide provides solutions to common issues encountered when using the FHIRPath AST-to-SQL Translator. Each issue includes symptoms, root causes, and step-by-step solutions with code examples.

---

## Table of Contents

1. [Translation Errors](#translation-errors)
2. [Parser Integration Issues](#parser-integration-issues)
3. [Dialect-Specific Problems](#dialect-specific-problems)
4. [Performance Issues](#performance-issues)
5. [SQL Generation Issues](#sql-generation-issues)
6. [Fragment Handling Issues](#fragment-handling-issues)
7. [Debugging Techniques](#debugging-techniques)
8. [Common Pitfalls](#common-pitfalls)

---

## Translation Errors

### Error: `NotImplementedError: Visitor method not implemented for node type`

**Symptoms**:
```
NotImplementedError: Visitor method not implemented for node type: SomeNode
```

**Root Cause**:
The translator encountered an AST node type that doesn't have a corresponding `visit_*()` method implemented yet.

**Solution**:

1. **Check which node type is unsupported**:
   ```python
   try:
       fragments = translator.translate(ast_root)
   except NotImplementedError as e:
       print(f"Unsupported node type: {e}")
   ```

2. **Verify FHIRPath expression**:
   - Some advanced FHIRPath features may not be implemented yet
   - Check if your expression uses unsupported operations

3. **Workaround options**:
   ```python
   # Option 1: Simplify expression
   # Instead of: Patient.name.select(given + ' ' + family)
   # Use: Patient.name.given (simpler path)

   # Option 2: Check implementation status
   # Review PEP-003 for list of implemented operations

   # Option 3: File feature request
   # Document the unsupported operation needed
   ```

**Prevention**:
- Review [supported operations](translator-api-reference.md#supported-operations) before translation
- Test expressions incrementally

---

### Error: `ValueError: expression must be a non-empty string`

**Symptoms**:
```
ValueError: expression must be a non-empty string
```

**Root Cause**:
Attempting to create a `SQLFragment` with an empty or invalid expression.

**Solution**:

1. **Check AST structure**:
   ```python
   # Verify AST is valid before translation
   if ast_root is None:
       raise ValueError("AST is None - check parser output")

   # Check AST has content
   if not hasattr(ast_root, 'node_type'):
       raise ValueError("Invalid AST structure")
   ```

2. **Verify parser output**:
   ```python
   parser = FHIRPathParser()
   expression = parser.parse("Patient.name")

   # Validate parser succeeded
   if not expression.is_valid():
       print("Parser failed - check expression syntax")
   ```

**Prevention**:
- Always validate parser output before translation
- Check for empty expressions

---

## Parser Integration Issues

### Issue: `AttributeError: 'EnhancedASTNode' object has no attribute 'visit'`

**Symptoms**:
```
AttributeError: 'EnhancedASTNode' object has no attribute 'visit'
```

**Root Cause**:
Passing `EnhancedASTNode` directly to translator without conversion.

**Solution**:

```python
# ❌ Wrong - passing Enhanced AST directly
parser = FHIRPathParser()
expression = parser.parse("Patient.name")
enhanced_ast = expression.get_ast()
fragments = translator.translate(enhanced_ast)  # ERROR!

# ✅ Correct - convert AST first

enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation
fragments = translator.translate(ast)  # SUCCESS!
```

**Prevention**:
- Always use `# (Removed - SP-023-006)()` after parsing
- Follow the standard workflow pattern

---

### Issue: Incorrect SQL Generated for Function Calls

**Symptoms**:
Function calls (e.g., `where()`, `first()`) generate incorrect SQL or missing operations.

**Root Cause**:
AST conversion may not properly identify function calls vs. path expressions.

**Solution**:

1. **Verify function call detection**:
   ```python
   # Debug AST structure

   adapter = ASTAdapter()
   print(f"Node type: {enhanced_node.node_type}")
   print(f"Is function: {adapter._is_function_call(enhanced_node)}")
   print(f"Is path: {adapter._is_path_expression(enhanced_node)}")
   ```

2. **Check parser AST structure**:
   ```python
   # Inspect parser output
   parser = FHIRPathParser()
   expression = parser.parse("Patient.name.where(use='official')")
   enhanced_ast = expression.get_ast()

   # Print AST structure
   def print_ast(node, indent=0):
       print("  " * indent + f"{node.node_type}: {node.text}")
       if hasattr(node, 'children'):
           for child in node.children:
               print_ast(child, indent+1)

   print_ast(enhanced_ast)
   ```

**Prevention**:
- Test function calls with integration tests
- Validate SQL output matches expected pattern

---

## Dialect-Specific Problems

### Issue: DuckDB SQL Works, PostgreSQL Fails

**Symptoms**:
Generated SQL works in DuckDB but fails in PostgreSQL (or vice versa).

**Root Cause**:
Database-specific syntax differences not properly handled by dialect.

**Solution**:

1. **Verify dialect is correct**:
   ```python
   # ❌ Wrong - using wrong dialect
   translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
   # ... generate SQL ...
   # Execute on PostgreSQL - FAILS!

   # ✅ Correct - match dialect to database
   pg_connection = "postgresql://user:pass@localhost:5432/db"
   translator = ASTToSQLTranslator(PostgreSQLDialect(pg_connection), "Patient")
   ```

2. **Compare SQL output**:
   ```python
   # Generate SQL for both dialects
   duckdb_translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
   pg_translator = ASTToSQLTranslator(PostgreSQLDialect(pg_conn), "Patient")

   duckdb_fragments = duckdb_translator.translate(ast_root)
   pg_fragments = pg_translator.translate(ast_root)

   print("DuckDB SQL:")
   print(duckdb_fragments[0].expression)
   print("\nPostgreSQL SQL:")
   print(pg_fragments[0].expression)
   ```

3. **Check syntax differences**:
   ```python
   # Common differences:
   # DuckDB: json_extract(resource, '$.name')
   # PostgreSQL: jsonb_extract_path_text(resource::jsonb, 'name')

   # DuckDB: json_array_length(json_extract(...))
   # PostgreSQL: jsonb_array_length(jsonb_extract_path(...))
   ```

**Prevention**:
- Always test both dialects
- Use parametrized tests with both dialects

---

### Issue: PostgreSQL Connection Error

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server
```

**Root Cause**:
PostgreSQL connection string is incorrect or database is not running.

**Solution**:

1. **Verify PostgreSQL is running**:
   ```bash
   # Check PostgreSQL status
   pg_isready -h localhost -p 5432
   ```

2. **Test connection string**:
   ```python
   import psycopg2

   # Test connection
   conn_string = "postgresql://postgres:postgres@localhost:5432/postgres"
   try:
       conn = psycopg2.connect(conn_string)
       print("Connection successful!")
       conn.close()
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

3. **Use environment variable**:
   ```python
   import os

   # Get connection from environment
   pg_connection = os.getenv(
       "FHIR4DS_PG_CONNECTION",
       "postgresql://postgres:postgres@localhost:5432/postgres"
   )
   ```

**Prevention**:
- Use configuration files for connection strings
- Test connection before creating translator

---

## Performance Issues

### Issue: Translation Takes Too Long

**Symptoms**:
Translation of complex expressions takes >100ms (expected <10ms).

**Root Cause**:
- Complex nested expressions
- Inefficient AST traversal
- Memory allocation overhead

**Solution**:

1. **Profile translation**:
   ```python
   import time

   start = time.time()
   fragments = translator.translate(ast_root)
   duration = time.time() - start

   print(f"Translation took: {duration*1000:.2f}ms")

   # If > 10ms, investigate further
   ```

2. **Simplify expression**:
   ```python
   # ❌ Complex nested expression
   expr = "Patient.name.where(use='official').first().given.where(exists()).first()"

   # ✅ Simpler alternative
   expr = "Patient.name.where(use='official').first().given"
   ```

3. **Reuse translator instance**:
   ```python
   # ❌ Creating new translator for each expression
   for expr in expressions:
       translator = ASTToSQLTranslator(dialect, "Patient")  # Slow!
       fragments = translator.translate(expr)

   # ✅ Reuse translator
   translator = ASTToSQLTranslator(dialect, "Patient")
   for expr in expressions:
       fragments = translator.translate(expr)  # Fast!
   ```

**Prevention**:
- Cache translator instances
- Profile performance regularly
- Set performance budgets (<10ms per translation)

---

### Issue: Memory Usage Growing

**Symptoms**:
Memory usage increases with each translation, eventually causing OOM errors.

**Root Cause**:
- Fragment accumulation
- Context not being reset
- Cached ASTs not released

**Solution**:

1. **Reset context between translations**:
   ```python
   translator = ASTToSQLTranslator(dialect, "Patient")

   for expression in expressions:
       fragments = translator.translate(ast_root)
       # Process fragments...

       # Reset for next translation
       translator.context.reset()
       translator.fragments.clear()
   ```

2. **Limit fragment lifetime**:
   ```python
   # Process fragments immediately, don't accumulate
   fragments = translator.translate(ast_root)
   sql = process_fragments(fragments)  # Convert to SQL
   fragments = None  # Release fragments
   ```

**Prevention**:
- Monitor memory usage in production
- Set memory limits and alerts

---

## SQL Generation Issues

### Issue: Generated SQL is Incorrect

**Symptoms**:
SQL runs but returns wrong results or causes errors.

**Root Cause**:
- Incorrect JSON path generation
- Wrong table references
- Missing quotes or escaping

**Solution**:

1. **Validate generated SQL**:
   ```python
   # Print generated SQL for inspection
   fragments = translator.translate(ast_root)
   for i, fragment in enumerate(fragments):
       print(f"Fragment {i+1}:")
       print(fragment.expression)
       print()

   # Test SQL in database CLI
   # Copy/paste to verify manually
   ```

2. **Check JSON path construction**:
   ```python
   # Verify path building
   context = TranslationContext()
   context.push_path("name")
   context.push_path("family")
   path = context.get_json_path()
   print(f"JSON path: {path}")  # Should be: $.name.family
   ```

3. **Validate escaping**:
   ```python
   # Check string escaping
   expr = "Patient.name.where(use='official')"
   # Generated SQL should have: '$.use' = 'official'
   # NOT: $.use = official (missing quotes)
   ```

**Prevention**:
- Add SQL validation tests
- Use EXPLAIN to verify query plans
- Test with actual data

---

### Issue: UNNEST SQL Missing or Incorrect

**Symptoms**:
Array filtering doesn't work, or UNNEST syntax is wrong.

**Root Cause**:
- `where()` function not generating LATERAL UNNEST
- Dialect doesn't support UNNEST properly

**Solution**:

1. **Verify UNNEST generation**:
   ```python
   expr = "Patient.name.where(use='official')"
   fragments = translator.translate(ast_root)

   # Check for UNNEST
   sql = fragments[-1].expression
   assert "UNNEST" in sql.upper() or "LATERAL" in sql

   # Check requires_unnest flag
   assert fragments[-1].requires_unnest == True
   ```

2. **Test UNNEST SQL manually**:
   ```sql
   -- Test in database
   SELECT resource.id, name_item
   FROM patient_resources,
   LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item
   WHERE json_extract(name_item, '$.use') = 'official';
   ```

**Prevention**:
- Test array operations explicitly
- Validate UNNEST syntax for each dialect

---

## Fragment Handling Issues

### Issue: Missing Fragment Dependencies

**Symptoms**:
CTE generation fails because dependencies are not tracked.

**Root Cause**:
Fragments don't declare their dependencies correctly.

**Solution**:

1. **Verify dependencies**:
   ```python
   fragments = translator.translate(ast_root)

   for i, fragment in enumerate(fragments):
       print(f"Fragment {i+1}:")
       print(f"  Source: {fragment.source_table}")
       print(f"  Dependencies: {fragment.dependencies}")
   ```

2. **Manually add dependencies if needed**:
   ```python
   # If fragment is missing dependency
   fragment.add_dependency("cte_1")
   ```

3. **Validate dependency chain**:
   ```python
   def validate_dependencies(fragments):
       available = {'resource'}
       for fragment in fragments:
           # Check all dependencies are available
           for dep in fragment.dependencies:
               if dep not in available:
                   raise ValueError(f"Missing dependency: {dep}")
           # Add this fragment's table to available
           available.add(fragment.source_table)
   ```

**Prevention**:
- Test dependency tracking for complex expressions
- Validate before CTE generation

---

### Issue: Fragment Flags Not Set Correctly

**Symptoms**:
`requires_unnest` or `is_aggregate` flags don't match actual SQL.

**Root Cause**:
Translator doesn't set flags correctly during generation.

**Solution**:

1. **Check flags match SQL**:
   ```python
   fragments = translator.translate(ast_root)

   for fragment in fragments:
       # If SQL has UNNEST, flag should be True
       if "UNNEST" in fragment.expression.upper():
           assert fragment.requires_unnest, "Missing requires_unnest flag"

       # If SQL has aggregation, flag should be True
       if any(agg in fragment.expression.upper() for agg in ["COUNT", "SUM", "AVG", "MIN", "MAX"]):
           assert fragment.is_aggregate, "Missing is_aggregate flag"
   ```

2. **Manually set flags if needed**:
   ```python
   # Override flag if incorrect
   fragment.requires_unnest = True
   ```

**Prevention**:
- Add flag validation tests
- Review flag setting in translator code

---

## Debugging Techniques

### Technique 1: Enable Debug Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('fhir4ds.fhirpath.sql')
logger.setLevel(logging.DEBUG)

# Translation will now log debug info
fragments = translator.translate(ast_root)
```

### Technique 2: Inspect AST Structure

```python
def print_ast(node, indent=0):
    """Pretty-print AST structure"""
    print("  " * indent + f"{node.node_type}: {getattr(node, 'text', '')}")
    if hasattr(node, 'children'):
        for child in (node.children or []):
            print_ast(child, indent+1)

# Print before conversion
print("Enhanced AST:")
print_ast(enhanced_ast)

# Print after conversion
print("\nFHIRPath AST:")
print_ast(fhirpath_ast)
```

### Technique 3: Step Through Translation

```python
# Translate step-by-step
translator = ASTToSQLTranslator(dialect, "Patient")

# Set breakpoint or add prints in visitor methods
# Override visit method for debugging
original_visit = translator.visit

def debug_visit(node):
    print(f"Visiting: {node.node_type}")
    result = original_visit(node)
    print(f"Generated: {result.expression if result else 'None'}")
    return result

translator.visit = debug_visit

# Now translate
fragments = translator.translate(ast_root)
```

### Technique 4: Compare Expected vs. Actual SQL

```python
def compare_sql(expected: str, actual: str):
    """Compare expected and actual SQL, highlighting differences"""
    import difflib

    diff = difflib.unified_diff(
        expected.splitlines(),
        actual.splitlines(),
        lineterm='',
        fromfile='expected',
        tofile='actual'
    )

    print('\n'.join(diff))

# Usage
expected_sql = "SELECT json_extract(resource, '$.name') FROM patient"
actual_sql = fragments[0].expression
compare_sql(expected_sql, actual_sql)
```

### Technique 5: Validate SQL Syntax

```python
def validate_sql_syntax(sql: str, dialect: str = "duckdb"):
    """Validate SQL syntax using database"""
    if dialect == "duckdb":
        import duckdb
        try:
            conn = duckdb.connect(':memory:')
            conn.execute(f"EXPLAIN {sql}")
            return True
        except Exception as e:
            print(f"SQL syntax error: {e}")
            return False
    # Similar for PostgreSQL...
```

---

## Common Pitfalls

### Pitfall 1: Mixing Dialects

```python
# ❌ Wrong - DuckDB SQL on PostgreSQL
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
sql = translator.translate(ast_root)[0].expression
execute_on_postgresql(sql)  # FAILS!

# ✅ Correct - Match dialect to database
translator = ASTToSQLTranslator(PostgreSQLDialect(pg_conn), "Patient")
sql = translator.translate(ast_root)[0].expression
execute_on_postgresql(sql)  # SUCCESS!
```

### Pitfall 2: Not Converting AST

```python
# ❌ Wrong - Direct enhanced AST
fragments = translator.translate(enhanced_ast)  # ERROR!

# ✅ Correct - Convert first
ast = enhanced_ast  # SP-023-006: Direct translation
fragments = translator.translate(ast)
```

### Pitfall 3: Ignoring Fragment Metadata

```python
# ❌ Wrong - Assuming all fragments are simple
for fragment in fragments:
    sql = f"WITH cte AS ({fragment.expression}) SELECT * FROM cte"
    # May fail if requires_unnest=True

# ✅ Correct - Check flags
for fragment in fragments:
    if fragment.requires_unnest:
        # Handle UNNEST specially
        pass
    elif fragment.is_aggregate:
        # Handle aggregation specially
        pass
```

### Pitfall 4: Wrong Resource Type

```python
# ❌ Wrong - Observation expression with Patient type
translator = ASTToSQLTranslator(dialect, "Patient")
expr = "Observation.valueQuantity.value"
# Generates incorrect SQL

# ✅ Correct - Match resource type
translator = ASTToSQLTranslator(dialect, "Observation")
expr = "Observation.valueQuantity.value"
```

### Pitfall 5: Not Resetting Context

```python
# ❌ Wrong - Context pollution between translations
translator = ASTToSQLTranslator(dialect, "Patient")
fragments1 = translator.translate(ast1)
fragments2 = translator.translate(ast2)  # May have stale context!

# ✅ Correct - Reset between translations
translator = ASTToSQLTranslator(dialect, "Patient")
fragments1 = translator.translate(ast1)
translator.context.reset()  # Clean state
fragments2 = translator.translate(ast2)
```

---

## Getting Help

### Check Documentation

1. [API Reference](translator-api-reference.md) - Complete API documentation
2. [Usage Examples](translator-usage-examples.md) - Working code examples
3. [Integration Guide](translator-integration-guide.md) - PEP-004 integration

### Enable Verbose Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### File an Issue

When filing an issue, include:
1. FHIRPath expression that fails
2. Complete error message and stack trace
3. Database dialect used
4. Generated SQL (if any)
5. Expected behavior
6. Actual behavior
7. Code snippet to reproduce

### Run Tests

```bash
# Run translator tests
python tests/run_tests.py --module sql

# Run integration tests
python tests/run_tests.py --integration

# Run with verbose output
python tests/run_tests.py --verbose
```

---

## Quick Reference

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `NotImplementedError` | Unsupported AST node type | Check PEP-003 for supported operations |
| `ValueError: expression must be non-empty` | Invalid SQL fragment | Validate AST before translation |
| `AttributeError: 'EnhancedASTNode'...` | Wrong AST type | Use `# (Removed - SP-023-006)()` |
| `psycopg2.OperationalError` | PostgreSQL connection failed | Check connection string and database |

### Validation Checklist

Before deploying translator code:

- [ ] Parser integration tested
- [ ] Both dialects tested (DuckDB and PostgreSQL)
- [ ] Complex expressions tested
- [ ] Error handling implemented
- [ ] SQL syntax validated
- [ ] Performance benchmarked (<10ms)
- [ ] Logging configured
- [ ] Tests passing

---

## Appendix: Diagnostic Script

```python
"""
Comprehensive diagnostic script for translator issues.
Run this to get detailed information about a failing translation.
"""

import logging
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def diagnose_translation(expression_text: str, resource_type: str = "Patient"):
    """Run comprehensive diagnostics on a FHIRPath expression"""
    print(f"Diagnosing: {expression_text}")
    print(f"Resource Type: {resource_type}")
    print("=" * 80)

    # Step 1: Parse
    print("\n1. PARSING")
    try:
        parser = FHIRPathParser()
        expression = parser.parse(expression_text)
        print(f"✓ Parse successful")
        print(f"  Valid: {expression.is_valid()}")
    except Exception as e:
        print(f"✗ Parse failed: {e}")
        return

    # Step 2: Get Enhanced AST
    print("\n2. ENHANCED AST")
    try:
        enhanced_ast = expression.get_ast()
        print(f"✓ Enhanced AST retrieved")
        print(f"  Node type: {enhanced_ast.node_type}")
        print(f"  Text: {enhanced_ast.text}")
    except Exception as e:
        print(f"✗ Enhanced AST failed: {e}")
        return

    # Step 3: Convert AST
    print("\n3. AST CONVERSION")
    try:
        ast = enhanced_ast  # SP-023-006: Direct translation
        print(f"✓ AST conversion successful")
        print(f"  Node type: {fhirpath_ast.node_type}")
    except Exception as e:
        print(f"✗ AST conversion failed: {e}")
        return

    # Step 4: Translate (DuckDB)
    print("\n4. TRANSLATION (DuckDB)")
    try:
        duckdb_translator = ASTToSQLTranslator(DuckDBDialect(), resource_type)
        duckdb_fragments = duckdb_translator.translate(ast)
        print(f"✓ DuckDB translation successful")
        print(f"  Fragments: {len(duckdb_fragments)}")
        for i, frag in enumerate(duckdb_fragments):
            print(f"  Fragment {i+1}:")
            print(f"    SQL: {frag.expression[:100]}...")
            print(f"    Source: {frag.source_table}")
            print(f"    Requires UNNEST: {frag.requires_unnest}")
            print(f"    Is Aggregate: {frag.is_aggregate}")
    except Exception as e:
        print(f"✗ DuckDB translation failed: {e}")

    # Step 5: Translate (PostgreSQL)
    print("\n5. TRANSLATION (PostgreSQL)")
    try:
        pg_conn = "postgresql://postgres:postgres@localhost:5432/postgres"
        pg_translator = ASTToSQLTranslator(PostgreSQLDialect(pg_conn), resource_type)
        pg_fragments = pg_translator.translate(ast)
        print(f"✓ PostgreSQL translation successful")
        print(f"  Fragments: {len(pg_fragments)}")
        for i, frag in enumerate(pg_fragments):
            print(f"  Fragment {i+1}:")
            print(f"    SQL: {frag.expression[:100]}...")
    except Exception as e:
        print(f"✗ PostgreSQL translation failed: {e}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")

# Example usage
if __name__ == "__main__":
    diagnose_translation("Patient.name.where(use='official').first()")
```

---

**Last Updated**: 2025-10-02
**Task**: SP-005-023 - API Documentation and Examples
