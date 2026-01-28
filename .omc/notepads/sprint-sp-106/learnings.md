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
