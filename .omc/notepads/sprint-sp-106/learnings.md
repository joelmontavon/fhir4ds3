# SP-106 Learnings

## SP-106-004: Decimal Comparisons

### Issue: Floating-Point Precision Loss in Decimal Operations
**Problem:** DuckDB dialect was mapping FHIRPath `decimal` type to SQL `DOUBLE`, causing floating-point precision errors.

**Root Cause:** Type mapping in `duckdb.py`:
```python
"decimal": "DOUBLE",  # Wrong - causes precision loss
```

**Impact:** 
- `0.1 + 0.2` returned `0.30000000000000004` instead of `0.3`
- Decimal comparisons could fail due to precision issues
- Violated FHIRPath specification requirement for decimal precision

**Solution:**
```python
"decimal": "DECIMAL",  # Correct - maintains precision
```

### Key Takeaways

1. **SQL Type Selection Matters**
   - DECIMAL/NUMERIC: Fixed-point, exact precision (required for FHIRPath)
   - DOUBLE/FLOAT: Floating-point, approximation (causes precision loss)
   - Always use DECIMAL for FHIRPath decimal type

2. **Database Dialect Consistency**
   - PostgreSQL: Already correctly uses `NUMERIC` for decimal
   - DuckDB: Was incorrectly using `DOUBLE`, now fixed to `DECIMAL`
   - Both dialects must maintain decimal precision

3. **Testing Strategy**
   - Test edge cases like `0.1 + 0.2 = 0.3`
   - Verify type mappings in both dialects
   - Check SQL output contains `DECIMAL` not `DOUBLE`

4. **Arithmetic Operations**
   - Addition, subtraction, multiplication now use DECIMAL
   - Division always returns decimal (per FHIRPath spec)
   - Type promotion: integer + decimal = decimal

### Files Changed
- `/mnt/d/fhir4ds3/fhir4ds/main/dialects/duckdb.py` (line 1411)
- `/mnt/d/fhir4ds3/tests/unit/fhirpath/sql/test_translator_type_casting.py` (test fix)

### Verification
All 33 comparison and arithmetic tests pass after fix.

## SP-106-007: TIME vs DATE/TIMESTAMP Comparison Validation

### Problem
Comparing TIME literals (@T12:14:15) with DATE/TIMESTAMP fields caused DuckDB conversion errors:
```
Conversion Error: Unimplemented type for cast (TIME -> TIMESTAMP)
```

### Solution Approach
**Semantic validation at parse time** rather than runtime cast support because:
1. TIME and DATE are fundamentally incompatible types
2. No semantically correct way to cast TIME to TIMESTAMP (what date to use?)
3. Early error detection provides better UX than cryptic database errors

### Implementation Details

**File**: `fhir4ds/main/fhirpath/parser_core/semantic_validator.py`

Added validation method `_validate_temporal_comparison_compatibility()`:
- Detects TIME literals in expressions (pattern: `@T\d{2}(:\d{2})?(:\d{2})?`)
- Checks if expression contains comparison operators (=, !=, <, >, <=, >=)
- Walks AST to find comparison nodes
- Determines temporal types of both operands:
  - For literals: Direct pattern detection (@T... = TIME, @YYYY-MM-DD = DATE, @YYYY-MM-DDTHH:MM:SS = DATETIME)
  - For fields: Type registry lookup (e.g., Patient.birthDate → date type)
- Raises `FHIRPathParseError` if incompatible types detected

**Key Helper Methods**:
- `_get_temporal_type_of_operand(node)`: Returns "time", "date", "datetime", or None
- `_find_temporal_literal_in_subtree(node)`: Recursively searches for temporal literals
- `_get_temporal_literal_type(node)`: Enhanced temporal literal detection

### Example Error Message
```
FHIRPathParseError: Cannot compare TIME literal with DATE field/value. 
TIME and DATE are incompatible types for comparison. TIME represents 
time-of-day without date context, while DATE represents a calendar date 
or timestamp. Use compatible temporal types or extract components explicitly.
```

### Test Cases
**Valid Comparisons** (should pass):
- `Patient.birthDate != @2024-01-01` (DATE vs DATE)
- `@2024-01-01T12:00:00 = @2024-01-01T12:00:00` (DATETIME vs DATETIME)

**Invalid Comparisons** (should fail):
- `Patient.birthDate != @T12:14:15` (DATE vs TIME) ✅
- `Patient.birthDate != @T12:14` (DATE vs TIME) ✅

### Lessons Learned
1. **Type registry integration**: Semantic validation can leverage the existing type registry to determine field types (e.g., `Patient.birthDate` is a `date` field)
2. **AST node type variations**: ANTLR generates nested structures; need to walk entire subtrees, not just check root node types
3. **Literal vs field detection**: Operands can be literals (direct values) or field references (path expressions) - need different detection strategies
4. **Error messaging**: Clear, actionable error messages that explain WHY the comparison is invalid improve developer experience

### Related Files
- Type registry: `fhir4ds/main/fhirpath/types/type_registry.py`
- AST extensions: `fhir4ds/main/fhirpath/parser_core/ast_extensions.py`
- Semantic validator: `fhir4ds/main/fhirpath/parser_core/semantic_validator.py`

### Future Considerations
- Could extend validation to catch other incompatible type comparisons
- Pattern could be applied to other type mismatches (e.g., string vs number in certain contexts)
