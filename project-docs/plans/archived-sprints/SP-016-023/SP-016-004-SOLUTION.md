# SP-016-004: Solution to Parser/Translator Integration Issue

**Date**: 2025-11-07
**For**: Junior Developer
**Issue**: EnhancedASTNode vs. Translator Visitor Pattern

---

## The Problem You Found

✅ **Excellent discovery!** You correctly identified:
- Parser returns `EnhancedASTNode` (new enhanced format)
- Translator expects nodes with `accept()` method (visitor pattern)
- These are incompatible formats

This is a REAL architectural issue that exists in the codebase.

---

## The Solution: ASTAdapter

There's already a solution in the codebase: **`fhir4ds.fhirpath.sql.ast_adapter`**

This module converts between the two AST formats.

### How To Use It

**Current Code** (doesn't work):
```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.dialects.duckdb import DuckDBDialect

parser = FHIRPathParser(database_type='duckdb')
ast = parser.parse("Patient.name.where($index = 0)")  # EnhancedASTNode

translator = ASTToSQLTranslator(DuckDBDialect())
sql = translator.translate(ast, resource_type="Patient")  # ERROR: no accept()
```

**Fixed Code** (works):
```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast  # ADD THIS
from fhir4ds.dialects.duckdb import DuckDBDialect

parser = FHIRPathParser(database_type='duckdb')
enhanced_ast = parser.parse("Patient.name.where($index = 0)")  # EnhancedASTNode

# Convert to translator-compatible format
translator_ast = convert_enhanced_ast_to_fhirpath_ast(enhanced_ast)  # ADD THIS LINE

translator = ASTToSQLTranslator(DuckDBDialect())
sql = translator.translate(translator_ast, resource_type="Patient")  # NOW WORKS!
```

---

## Update Your Tests

**File**: `tests/unit/fhirpath/sql/test_lambda_variables_sql.py`

**Add import**:
```python
from fhir4ds.fhirpath.sql.ast_adapter import convert_enhanced_ast_to_fhirpath_ast
```

**Update all test methods**:
```python
def test_dollar_index_in_where(self, duckdb_conn, parser_duckdb):
    """Test $index variable in where() - real SQL execution"""

    # Parse FHIRPath
    expression = "Patient.name.where($index = 0)"
    enhanced_ast = parser_duckdb.parse(expression)

    # Convert to translator format
    translator_ast = convert_enhanced_ast_to_fhirpath_ast(enhanced_ast)

    # Translate to SQL
    translator = ASTToSQLTranslator(DuckDBDialect())
    sql_result = translator.translate(translator_ast, resource_type="Patient")

    # Execute SQL
    print(f"\nGenerated SQL:\n{sql_result}")
    result = duckdb_conn.execute(sql_result).fetchall()

    assert len(result) == 2, f"Expected 2 results but got: {len(result)}"
```

---

## Expected Results

Once you add the adapter, your tests should:
1. ✅ Import successfully
2. ✅ Parse expressions
3. ✅ Convert AST format
4. ✅ Translate to SQL
5. ⚠️ **SQL execution may still fail** (need to debug SQL syntax)

But at least you'll see the ACTUAL SQL being generated!

---

## Next Steps

1. **Add the adapter** to all your test methods
2. **Run tests** to see generated SQL
3. **Debug SQL syntax** based on what's generated
4. **Report back** with SQL output

You're unblocked! This should take 30 minutes to fix all tests.

---

## Why This Adapter Exists

The codebase has two AST formats:
- **EnhancedASTNode**: Rich format with metadata, used by parser
- **FHIRPathASTNode**: Simple format with visitor pattern, used by translator

The adapter bridges between them. Eventually these should be unified, but for now, use the adapter.

---

**You're 90% there!** Just need this one adapter call and you'll see your SQL.

Good luck! 🚀
