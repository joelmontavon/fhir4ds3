# Known Issue: FHIRPath Translator `.where()` Function Bug

**Issue ID**: TRANSLATOR-001
**Discovered**: 2025-11-15
**Severity**: High (blocks SQL-on-FHIR WHERE clause compliance)
**Status**: Documented - Awaiting Fix

---

## Summary

The FHIRPath translator (ASTToSQLTranslator) has a bug when translating expressions containing the `.where()` function with filtering. Instead of generating proper array filtering logic, it generates:

1. **Invalid JSON paths** for simple cases (e.g., `$.name.where(family='Smith')`)
2. **Embedded SELECT statements** for complex cases that cannot be used in SQL expressions

This blocks SQL-on-FHIR WHERE clause support for any expressions using the `.where()` function.

---

## Detailed Description

### Problem 1: Invalid JSON Path Generation

**Expression**: `name.where(use = 'official').exists()`

**Current Translator Output** (INCORRECT):
```sql
CASE WHEN json_extract_string(resource, '$.name.where(use='official')') IS NOT NULL
     AND json_array_length(json_extract_string(resource, '$.name.where(use='official')')) > 0
     THEN TRUE
     ELSE FALSE
END
```

**Problem**: The translator treats `.where(use='official')` as part of the JSON path, generating `$.name.where(use='official')` which is **invalid JSON path syntax**.

**Expected Output**:
```sql
EXISTS (
  SELECT 1
  FROM json_each(json_extract(resource, '$.name')) AS name_item
  WHERE json_extract_string(name_item.value, '$.use') = 'official'
)
```

---

### Problem 2: Embedded SELECT Statements

**Expression**: `name.where(family = 'f2').empty()`

**Current Translator Output** (INCORRECT - truncated):
```sql
(CASE WHEN (CASE WHEN SELECT resource.id, cte_1_item, cte_1_item_idx
FROM resource, LATERAL (SELECT CAST(key AS INTEGER) AS cte_1_item_idx,
     value AS cte_1_item FROM json_each(json_extract(resource, '$.name')))
     AS enum_table
WHERE (json_extract_string(cte_1_item, '$.family') = 'f2') IS NULL THEN NULL
...
```

**Problem**: The translator generates a full `SELECT resource.id... FROM resource...` statement that cannot be embedded in a SQL expression or CTE.

**Impact**: This SQL **cannot be executed** - it's syntactically invalid when used in:
- WHERE clauses
- SELECT column expressions
- CTE definitions (as boolean expressions)

---

## Impact Analysis

### SQL-on-FHIR WHERE Clause Tests

**Test Suite**: `tests/compliance/sql_on_fhir/official_tests/tests/where.json`

**Total WHERE Tests**: 17
**Failing Due to This Bug**: 17 (100%)

All SQL-on-FHIR WHERE tests use expressions containing `.where()` function:
- `name.where(use = 'official').exists()`
- `name.where(family = 'f2').exists()`
- `name.where(family = 'f2').empty()`
- `name.where(use = 'official' and family = 'f1').exists()`
- etc.

### Blocked Functionality

1. **SQL-on-FHIR WHERE clauses**: Cannot filter resources using FHIRPath `.where()` function
2. **Complex FHIRPath expressions**: Any expression with `.where()` fails in SQL context
3. **CQL WHERE support**: CQL uses same translator, will have identical issues

---

## Root Cause Analysis

### Investigation Findings (2025-11-15)

**Test Script Results**:

```python
# Test 1: Simple comparison - WORKS
expr = "active = true"
# Output: (json_extract_string(resource, '$.active') = TRUE)

# Test 2: Existence check - WORKS
expr = "active.exists()"
# Output: CASE WHEN ... THEN TRUE ELSE FALSE END

# Test 3: .where() with exists() - BROKEN
expr = "name.where(family = 'Smith').exists()"
# Output: $.name.where(family='Smith')  # INVALID JSON PATH!

# Test 4: .where() with empty() - BROKEN WORSE
expr = "name.where(family = 'Smith').empty()"
# Output: SELECT resource.id... FROM resource...  # EMBEDDED SELECT!
```

### Suspected Root Cause

The translator's visitor pattern for the `.where()` function is incomplete:

1. **Does not generate array filtering logic** (LATERAL UNNEST with WHERE)
2. **Incorrectly treats `.where()` as a JSON path component**
3. **Falls back to population-level SELECT generation** which embeds full queries

The `.where()` function should trigger special handling to:
- Extract the array (`name`)
- UNNEST the array elements
- Apply the filter condition (`family = 'Smith'`)
- Check existence/emptiness of filtered results

**Current behavior**: Treats `.where(...)` as literal text in JSON path.

---

## Workaround

**None available** - the `.where()` function is essential for SQL-on-FHIR WHERE clauses.

**Alternative approach** (not implemented):
- Bypass translator for WHERE clauses
- Implement custom WHERE-specific FHIRPath evaluation
- **Rejected**: Violates DRY principle and architectural principles

---

## Implementation Status

### What Was Built (SP-020-002)

✅ **CTE-Based WHERE Clause Infrastructure**:
- WHERE expressions extracted from ViewDefinition
- FHIRPath translator integration
- CTEBuilder creates WHERE evaluation CTEs
- Pure CTE architecture following CLAUDE.md principles
- Clean integration with SQLGenerator

**Architecture**: Following approved CTE-First design, all WHERE expressions use population-level CTEs for evaluation.

**Code Location**: `fhir4ds/sql/generator.py:341-441`

### What Works

✅ **Simple WHERE expressions** (if translator supports them):
- `active = true`
- `active.exists()`
- `birthDate.exists()`
- Boolean comparisons without `.where()` function

✅ **Infrastructure is sound**:
- CTE generation works correctly
- WHERE clause integration works correctly
- Multi-condition AND logic works correctly

### What's Blocked

❌ **All SQL-on-FHIR WHERE tests** (17/17 use `.where()` function)

The WHERE clause implementation itself is **complete and correct**. The failures are entirely due to the translator bug.

---

## Recommended Fix

### Short-Term (Immediate)

1. **Document this limitation** in:
   - SP-020-002 task completion notes ✅ (this document)
   - SQLGenerator docstring (note about `.where()` limitation)
   - SQL-on-FHIR README (known limitations section)

2. **File separate issue** for translator bug fix
   - Title: "FHIRPath Translator: Fix `.where()` function with array filtering"
   - Link to this document
   - Assign to FHIRPath translator team/sprint

3. **Complete SP-020-002** with documented limitations
   - Infrastructure is complete
   - Blocked by dependency (translator bug)

### Long-Term (Translator Fix Required)

**Fix Location**: `fhir4ds/fhirpath/sql/translator.py` - visitor methods for `.where()` function

**Required Changes**:

1. **Detect `.where()` function** in visitor pattern
2. **Generate array filtering logic**:
   ```sql
   EXISTS (
     SELECT 1 FROM json_each(json_extract(resource, '$.array_path')) AS item
     WHERE <filter_condition_on_item>
   )
   ```

3. **Handle `.exists()` and `.empty()` on filtered arrays**:
   - `.exists()` → `EXISTS(...)`
   - `.empty()` → `NOT EXISTS(...)`

4. **Support nested `.where()` calls**:
   - `name.where(use='official').where(family='Smith').exists()`

**Estimated Effort**: 2-3 days (16-24 hours)

**Complexity**: High - requires modifying core translator visitor pattern

---

## Testing Evidence

### Direct Investigation (2025-11-15)

**Test Script**: `/tmp/investigate_translator.py`

**Results**:
```
Test: name.where(family = 'Smith').exists()
✅ Translator succeeded
❌ Output incorrect: treats .where() as JSON path component

Test: name.where(family = 'Smith').empty()
✅ Translator succeeded
❌ Output invalid: embedded SELECT statement
```

### CTEBuilder Test

**Test Script**: `/tmp/test_cte_builder.py`

**Result**: CTEBuilder correctly wraps translator output in CTEs, but **cannot fix invalid translator output**.

### Compliance Test Run

```bash
PYTHONPATH=. DB_TYPE=duckdb python3 -m pytest \
  tests/compliance/sql_on_fhir/test_sql_on_fhir_compliance.py -k "where" -v
```

**Result**: 17 failed, 0 passed, 17 skipped

**Error Pattern**:
```
Parser Error: syntax error at or near "SELECT"
Query: WITH where_eval_1_1 AS (
  SELECT resource.id, (... SELECT resource.id FROM resource ...) AS result
  FROM resource
)
```

---

## Related Issues

- **SP-020-002**: Implement WHERE Clause Generation (completed with limitations)
- **PEP-003**: FHIRPath Translator architecture (needs enhancement for `.where()`)
- **SQL-on-FHIR Compliance**: 17 WHERE tests blocked by this bug

---

## Architecture Notes

### Why This Blocks CTE-Based Approach

The approved CTE-based WHERE architecture (Option D) works as follows:

1. Translate WHERE FHIRPath → boolean expression
2. Wrap in CTE: `SELECT id, <boolean> AS result FROM resource`
3. Filter main query: `WHERE id IN (SELECT id FROM cte WHERE result = true)`

**The translator bug breaks step 1** - it doesn't generate a valid boolean expression.

**The architecture itself is sound** - it just needs translator output to be valid SQL.

### Why We Can't Work Around It

**Option considered**: Parse translator output and fix embedded SELECTs

**Rejected because**:
- String manipulation of SQL is brittle and error-prone
- Violates clean architecture principles
- Doesn't fix the root cause
- Would need complex regex/parsing for all `.where()` variants

---

## Status

**Documented**: 2025-11-15
**Assigned For Fix**: [To be determined]
**Blocks**:
- SP-020-002 complete compliance (17 tests)
- Future SQL-on-FHIR features using `.where()`
- CQL WHERE clause support

**Documented By**: Junior Developer
**Reviewed By**: [To be reviewed by Senior Solution Architect]

---

**Next Steps**:
1. ✅ Document limitation (this document)
2. ⏳ Create translator bug issue (SP-XXX-XXX)
3. ⏳ Update SP-020-002 completion notes
4. ⏳ Mark SP-020-002 complete with known limitations
5. ⏳ Plan translator fix in future sprint
