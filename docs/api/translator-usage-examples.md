# FHIRPath AST-to-SQL Translator Usage Examples

**Version**: 0.1.0
**Module**: `fhir4ds.fhirpath.sql`
**Task**: SP-005-023 - API Documentation and Examples

---

## Overview

This document provides 10+ practical examples demonstrating how to use the FHIRPath AST-to-SQL Translator with real healthcare FHIRPath expressions. Each example includes:

- Complete working code
- Expected output
- Explanation of the translation process
- Common use cases and variations

---

## Setup

All examples assume the following imports:

```python
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import (
    ASTToSQLTranslator,
    SQLFragment,
    TranslationContext,
    # (Removed - SP-023-006)
)
from fhir4ds.dialects import DuckDBDialect, PostgreSQLDialect
```

---

## Example 1: Simple Path Expression - Patient Birth Date

### Use Case
Extract patient birth dates for age calculations in quality measures.

### FHIRPath Expression
```
Patient.birthDate
```

### Code
```python
# Parse expression
parser = FHIRPathParser()
expression = parser.parse("Patient.birthDate")

# Convert AST
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

# Translate to SQL
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# View result
print(f"SQL: {fragments[0].expression}")
print(f"Source: {fragments[0].source_table}")
```

### Output
```
SQL: json_extract(resource, '$.birthDate')
Source: resource
```

### Explanation
- Simple path expressions extract JSON fields using `json_extract()`
- DuckDB syntax: `json_extract(resource, '$.birthDate')`
- PostgreSQL syntax would use: `jsonb_extract_path_text(resource, 'birthDate')`
- Population-scale: Operates on entire resource table, not individual rows

---

## Example 2: Nested Path - Patient Name Components

### Use Case
Extract patient family names for patient matching and de-duplication.

### FHIRPath Expression
```
Patient.name.family
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.name.family")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```
SQL: json_extract(resource, '$.name.family')
```

### Explanation
- Nested paths build JSON paths incrementally: `$.name.family`
- Handles FHIR's nested structure naturally
- Array handling depends on whether array functions are applied

---

## Example 3: Array Filtering - Official Names Only

### Use Case
Filter patient names to find only official names (e.g., for legal documents).

### FHIRPath Expression
```
Patient.name.where(use='official')
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official')")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# where() generates LATERAL UNNEST SQL
sql_fragment = fragments[-1]
print(f"SQL:\n{sql_fragment.expression}")
print(f"\nRequires Unnest: {sql_fragment.requires_unnest}")
```

### Output
```sql
SQL:
SELECT resource.id, cte_1_item
FROM resource,
LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
WHERE json_extract(cte_1_item, '$.use') = 'official'

Requires Unnest: True
```

### Explanation
- `where()` function generates LATERAL UNNEST for array filtering
- Each array item becomes a row with alias `cte_1_item`
- Filter condition applied in WHERE clause
- `requires_unnest=True` flags this for CTE Builder (PEP-004)
- Population-scale: Processes all patients' name arrays in single query

---

## Example 4: Array Indexing - First Name Only

### Use Case
Get the first name from the names array (e.g., primary name display).

### FHIRPath Expression
```
Patient.name.first()
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.name.first()")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[-1].expression}")
```

### Output
```sql
SQL: json_extract(resource, '$.name[0]')
```

### Explanation
- `first()` uses array indexing `[0]` instead of UNNEST
- More efficient than filtering when only first element needed
- Population-first: Operates on all patients simultaneously
- Avoids `LIMIT 1` anti-pattern (which breaks population queries)

---

## Example 5: Boolean Comparison - Active Patients

### Use Case
Filter patients to active status for current patient lists.

### FHIRPath Expression
```
Patient.active = true
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.active = true")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: json_extract(resource, '$.active') = TRUE
```

### Explanation
- Boolean literals translated to SQL `TRUE`/`FALSE`
- Comparison operators (`=`, `!=`, `<`, `>`, etc.) map directly to SQL
- Can be used in WHERE clauses for filtering active patients

---

## Example 6: Observation Values - Numeric Comparison

### Use Case
Find observations with values above a threshold (e.g., high blood pressure).

### FHIRPath Expression
```
Observation.valueQuantity.value > 140
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Observation.valueQuantity.value > 140")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Observation")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: CAST(json_extract(resource, '$.valueQuantity.value') AS DOUBLE) > 140
```

### Explanation
- Numeric comparisons require CAST for type safety
- Nested paths extract deeply nested values
- Useful for quality measures with numeric thresholds
- Resource type changed to `"Observation"`

---

## Example 7: Existence Check - Has Telecom

### Use Case
Check if patient has any contact information for outreach campaigns.

### FHIRPath Expression
```
Patient.telecom.exists()
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.telecom.exists()")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: json_extract(resource, '$.telecom') IS NOT NULL AND json_array_length(json_extract(resource, '$.telecom')) > 0
```

### Explanation
- `exists()` checks both NULL and empty array
- Population-scale: Identifies all patients with/without telecom
- Useful for data quality assessments

---

## Example 8: String Literal Matching - Gender Filter

### Use Case
Filter patients by gender for demographic analysis.

### FHIRPath Expression
```
Patient.gender = 'female'
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.gender = 'female'")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: json_extract(resource, '$.gender') = 'female'
```

### Explanation
- String literals properly escaped in SQL
- Gender values: `'male'`, `'female'`, `'other'`, `'unknown'`
- Case-sensitive string comparison

---

## Example 9: Chained Operations - Official Last Name

### Use Case
Extract family name from official name only (multi-step filtering).

### FHIRPath Expression
```
Patient.name.where(use='official').family
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.name.where(use='official').family")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

# Multiple fragments for chained operations
for i, fragment in enumerate(fragments):
    print(f"Fragment {i+1}:")
    print(f"  SQL: {fragment.expression}")
    print(f"  Source: {fragment.source_table}")
    print()
```

### Output
```
Fragment 1:
  SQL: SELECT resource.id, cte_1_item
       FROM resource,
       LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
       WHERE json_extract(cte_1_item, '$.use') = 'official'
  Source: cte_1

Fragment 2:
  SQL: json_extract(cte_1_item, '$.family')
  Source: cte_1
```

### Explanation
- Chained operations generate multiple fragments
- Each fragment becomes a CTE in final SQL (handled by PEP-004)
- Fragment 1: Filters to official names
- Fragment 2: Extracts family name from filtered results
- Dependencies tracked automatically

---

## Example 10: Condition Filtering - Diabetes Diagnosis

### Use Case
Find all diabetes condition records for quality measure inclusion criteria.

### FHIRPath Expression
```
Condition.code.coding.where(system='http://snomed.info/sct' and code='44054006')
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse(
    "Condition.code.coding.where(system='http://snomed.info/sct' and code='44054006')"
)
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Condition")
fragments = translator.translate(ast)

print(f"SQL:\n{fragments[-1].expression}")
```

### Output
```sql
SQL:
SELECT resource.id, cte_2_item
FROM resource,
LATERAL UNNEST(json_extract(resource, '$.code.coding')) AS cte_2_item
WHERE json_extract(cte_2_item, '$.system') = 'http://snomed.info/sct'
  AND json_extract(cte_2_item, '$.code') = '44054006'
```

### Explanation
- Nested array filtering: `code.coding` is an array
- Compound condition: Multiple WHERE clauses with AND
- SNOMED CT code: 44054006 = Type 2 Diabetes Mellitus
- Real-world quality measure pattern
- Population-scale: Finds all matching conditions across all patients

---

## Example 11: Multi-Database Translation - Cross-Platform Compatibility

### Use Case
Generate SQL for both DuckDB (development) and PostgreSQL (production).

### FHIRPath Expression
```
Patient.name.first().family
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.name.first().family")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

# DuckDB translation
duckdb_translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
duckdb_fragments = duckdb_translator.translate(ast)

print("DuckDB SQL:")
print(duckdb_fragments[-1].expression)
print()

# PostgreSQL translation
pg_connection = "postgresql://postgres:postgres@localhost:5432/postgres"
pg_translator = ASTToSQLTranslator(PostgreSQLDialect(pg_connection), "Patient")
pg_fragments = pg_translator.translate(ast)

print("PostgreSQL SQL:")
print(pg_fragments[-1].expression)
```

### Output
```
DuckDB SQL:
json_extract(json_extract(resource, '$.name[0]'), '$.family')

PostgreSQL SQL:
jsonb_extract_path_text(jsonb_extract_path(resource::jsonb, 'name', '0'), 'family')
```

### Explanation
- Same FHIRPath expression generates different SQL per dialect
- DuckDB: `json_extract()` function
- PostgreSQL: `jsonb_extract_path()` and `jsonb_extract_path_text()` functions
- Thin dialect architecture: Business logic identical, only syntax differs
- Validates identical behavior across databases

---

## Example 12: Aggregation - Count Active Patients

### Use Case
Count active patients for dashboard metrics.

### FHIRPath Expression
```
Patient.active.count()
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Patient.active.count()")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
fragments = translator.translate(ast)

print(f"SQL: {fragments[-1].expression}")
print(f"Is Aggregate: {fragments[-1].is_aggregate}")
```

### Output
```sql
SQL: COUNT(json_extract(resource, '$.active'))
Is Aggregate: True
```

### Explanation
- `count()` generates SQL `COUNT()` aggregation
- `is_aggregate=True` flags this for GROUP BY handling
- Population-scale: Counts across entire patient population
- Other aggregations: `sum()`, `avg()`, `min()`, `max()`

---

## Example 13: Date Comparison - Recent Encounters

### Use Case
Find encounters within the last year for continuity of care measures.

### FHIRPath Expression
```
Encounter.period.start > @2024-01-01
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("Encounter.period.start > @2024-01-01")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Encounter")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: CAST(json_extract(resource, '$.period.start') AS DATE) > DATE '2024-01-01'
```

### Explanation
- Date literals prefixed with `@` in FHIRPath
- SQL CAST ensures proper date comparison
- Useful for measurement period filtering
- Population-scale: Processes all encounters efficiently

---

## Example 14: Medication Request - Active Prescriptions

### Use Case
Find active medication requests for medication reconciliation.

### FHIRPath Expression
```
MedicationRequest.status = 'active' and MedicationRequest.intent = 'order'
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse(
    "MedicationRequest.status = 'active' and MedicationRequest.intent = 'order'"
)
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "MedicationRequest")
fragments = translator.translate(ast)

print(f"SQL: {fragments[0].expression}")
```

### Output
```sql
SQL: json_extract(resource, '$.status') = 'active' AND json_extract(resource, '$.intent') = 'order'
```

### Explanation
- Logical AND combines multiple conditions
- Both conditions evaluated for each medication request
- Useful for active medication lists
- Resource type: `MedicationRequest`

---

## Example 15: Complex Healthcare Expression - Quality Measure Pattern

### Use Case
Complete quality measure logic: Diabetic patients with recent HbA1c > 9%.

### FHIRPath Expression
```
Observation.where(
  code.coding.exists(system='http://loinc.org' and code='4548-4') and
  valueQuantity.value > 9 and
  effectiveDateTime > @2024-01-01
)
```

### Code
```python
parser = FHIRPathParser()
expression = parser.parse("""
Observation.where(
  code.coding.exists(system='http://loinc.org' and code='4548-4') and
  valueQuantity.value > 9 and
  effectiveDateTime > @2024-01-01
)
""")
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation

translator = ASTToSQLTranslator(DuckDBDialect(), "Observation")
fragments = translator.translate(ast)

print(f"SQL:\n{fragments[-1].expression}")
```

### Output
```sql
SQL:
SELECT resource.id, cte_1_item
FROM resource,
LATERAL UNNEST(json_extract(resource, '$.code.coding')) AS cte_1_item
WHERE (
  json_extract(cte_1_item, '$.system') = 'http://loinc.org' AND
  json_extract(cte_1_item, '$.code') = '4548-4'
) AND
CAST(json_extract(resource, '$.valueQuantity.value') AS DOUBLE) > 9 AND
CAST(json_extract(resource, '$.effectiveDateTime') AS DATE) > DATE '2024-01-01'
```

### Explanation
- Complete quality measure inclusion criteria
- LOINC code 4548-4 = Hemoglobin A1c
- Multiple nested conditions with exists(), comparisons, and dates
- Real-world CQL → FHIRPath → SQL pattern
- Population-scale: Identifies all qualifying observations
- Demonstrates translator handling complex healthcare logic

---

## Advanced Usage Patterns

### Pattern 1: Reusing Translator for Multiple Expressions

```python
# Create translator once
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")

# Translate multiple expressions
expressions = [
    "Patient.birthDate",
    "Patient.gender",
    "Patient.active"
]

for expr_text in expressions:
    expression = parser.parse(expr_text)
    enhanced_ast = expression.get_ast()
    ast = enhanced_ast  # SP-023-006: Direct translation
    fragments = translator.translate(ast)
    print(f"{expr_text}: {fragments[0].expression}")
```

### Pattern 2: Processing Fragment Dependencies

```python
# Get fragments with dependencies
fragments = translator.translate(ast)

# Check dependencies for CTE ordering
for fragment in fragments:
    if fragment.dependencies:
        print(f"Fragment depends on: {fragment.dependencies}")
```

### Pattern 3: Adding Custom Metadata

```python
fragments = translator.translate(ast)

# Add performance hints
for fragment in fragments:
    fragment.set_metadata("estimated_rows", 100000)
    fragment.set_metadata("optimization_hint", "use_index_on_resource_type")

# Retrieve metadata later
for fragment in fragments:
    rows = fragment.get_metadata("estimated_rows", 0)
    print(f"Estimated rows: {rows}")
```

---

## Testing Your Translations

### Unit Test Example

```python
import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql import ASTToSQLTranslator, # (Removed - SP-023-006)
from fhir4ds.dialects import DuckDBDialect

def test_patient_birthdate_translation():
    """Test simple path translation"""
    parser = FHIRPathParser()
    expression = parser.parse("Patient.birthDate")
    enhanced_ast = expression.get_ast()
    ast = enhanced_ast  # SP-023-006: Direct translation

    translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
    fragments = translator.translate(ast)

    assert len(fragments) == 1
    assert "birthDate" in fragments[0].expression
    assert fragments[0].source_table == "resource"
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Forgetting to Convert AST

```python
# ❌ Wrong - passing enhanced AST directly to translator
enhanced_ast = expression.get_ast()
fragments = translator.translate(enhanced_ast)  # ERROR!

# ✅ Correct - convert first
enhanced_ast = expression.get_ast()
ast = enhanced_ast  # SP-023-006: Direct translation
fragments = translator.translate(ast)
```

### Pitfall 2: Wrong Resource Type

```python
# ❌ Wrong - translating Observation expression with Patient resource type
translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
expression = parser.parse("Observation.valueQuantity.value")
# Will generate incorrect SQL

# ✅ Correct - match resource type to expression
translator = ASTToSQLTranslator(DuckDBDialect(), "Observation")
expression = parser.parse("Observation.valueQuantity.value")
```

### Pitfall 3: Not Checking Fragment Flags

```python
# ❌ Wrong - ignoring requires_unnest flag
fragments = translator.translate(ast)
sql = fragments[0].expression  # May be incomplete if requires_unnest=True

# ✅ Correct - check flags and handle appropriately
fragments = translator.translate(ast)
for fragment in fragments:
    if fragment.requires_unnest:
        print("This fragment needs special UNNEST handling")
    if fragment.is_aggregate:
        print("This fragment needs GROUP BY clause")
```

---

## Performance Tips

1. **Parse Once, Translate Multiple Times**: Parse FHIRPath once, translate for multiple dialects
2. **Reuse Translator Instances**: Create translator once per dialect, reuse for multiple expressions
3. **Batch Processing**: Process multiple expressions in sequence to amortize initialization costs
4. **Cache Results**: Cache translated SQL for frequently used expressions

---

## Next Steps

- [API Reference](translator-api-reference.md) - Complete API documentation
- [Integration Guide](translator-integration-guide.md) - Integration with PEP-004 CTE Builder
- [Troubleshooting Guide](translator-troubleshooting.md) - Common issues and solutions
- [PEP-003 Specification](../../project-docs/peps/accepted/pep-003-ast-to-sql-translator.md) - Complete technical specification

---

**Last Updated**: 2025-10-02
**Task**: SP-005-023 - API Documentation and Examples
**Examples Count**: 15 comprehensive examples with real healthcare FHIRPath expressions
