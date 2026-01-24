# Task: Fix DateTime Type Check Logic

**Task ID**: SP-021-017-FIX-DATETIME-TYPE-CHECK
**Status**: READY TO START
**Priority**: 🟡 MEDIUM
**Created**: 2025-12-05
**Estimated Effort**: 8-16 hours
**Expected Impact**: +20-30 tests

---

## Objective

Fix `.is(DateTime)` type check function to return correct results for datetime values.

**Current Behavior**: `.is(DateTime)` returns false for valid datetime values
```fhirpath
@2015-02-04T14:34:28.is(DateTime)  // ✗ Returns: false (WRONG!)
```

**Expected Behavior**: Should return true for datetime values
```fhirpath
@2015-02-04T14:34:28.is(DateTime)  // ✓ Should return: true
```

---

## Problem Statement

### Root Cause

After fixing the REGEXP syntax bug (SP-021-014), datetime type checks now generate valid SQL but return incorrect results.

**Evidence**:
```
Expression: @2015-02-04T14:34:28.is(DateTime)
Expected: true
Actual: false
SQL executes: ✓ (no syntax error)
Result: WRONG
```

This suggests the **type detection logic or regex pattern is incorrect**.

### Current Implementation

From bug fix investigation on 2025-12-05, the DuckDB dialect now uses:

```python
# fhir4ds/dialects/duckdb.py (lines 1163-1168)
if family in regex_patterns:
    pattern = regex_patterns[family].replace("'", "''")
    scalar_value = f"CAST({expression} AS VARCHAR)"
    json_value = f"json_extract_string({expression}, '$')"
    scalar_predicate = f"regexp_matches({scalar_value}, '{pattern}')"
    json_predicate = f"regexp_matches({json_value}, '{pattern}')"
```

**The problem is likely**:
1. Wrong regex pattern for DateTime type
2. Incorrect type detection logic
3. Wrong SQL predicate evaluation

---

## Investigation Plan

### Phase 1: Identify Root Cause (2-4 hours)

**Objective**: Determine why `.is(DateTime)` returns false.

**Step 1: Check Regex Pattern**

Find the regex pattern used for DateTime type checking:

```python
# Look for regex_patterns dictionary
# Expected location: fhir4ds/dialects/base_dialect.py or duckdb.py
regex_patterns = {
    'DateTime': r'^pattern_here$',
    # ...
}
```

**Questions to Answer**:
- What is the current regex pattern for 'DateTime'?
- Does it match `'2015-02-04T14:34:28'` or `'2015-02-04 14:34:28'`?
- Is the pattern correct per FHIRPath datetime format?

**Step 2: Test SQL Directly**

Execute the generated SQL in DuckDB to verify behavior:

```sql
-- What does our current implementation generate?
SELECT regexp_matches(
    CAST(TIMESTAMP '2015-02-04 14:34:28' AS VARCHAR),
    '^PATTERN_HERE$'
);

-- Test pattern manually
SELECT regexp_matches('2015-02-04 14:34:28', '^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}$');
-- Should return: true

-- What format does CAST(TIMESTAMP AS VARCHAR) produce?
SELECT CAST(TIMESTAMP '2015-02-04 14:34:28' AS VARCHAR);
-- Need to know exact format
```

**Step 3: Check Type Detection Logic**

Review how `.is(DateTime)` is translated:

```python
# Expected flow:
# FHIRPath: @2015-02-04T14:34:28.is(DateTime)
# → Parser: creates type check AST node
# → Translator: converts to SQL with regex pattern
# → Dialect: generates regexp_matches() call
```

**Success Criteria**:
- [ ] Located regex pattern for DateTime
- [ ] Tested pattern against actual timestamp formats
- [ ] Identified mismatch between expected and actual format
- [ ] Documented root cause

---

### Phase 2: Design Fix (2-3 hours)

**Objective**: Design correct type detection approach.

**Option A: Fix Regex Pattern**

Update pattern to match DuckDB's TIMESTAMP-to-VARCHAR format:

```python
# Current (possibly wrong):
'DateTime': r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}$'

# Fixed (if DuckDB uses space separator):
'DateTime': r'^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}'

# Or more flexible (matches both):
'DateTime': r'^\\d{4}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}:\\d{2}'
```

**Option B: Use Native Type Checking**

Instead of regex on string, use SQL type checking functions:

```sql
-- Instead of regexp_matches(CAST(value AS VARCHAR), pattern)
-- Use typeof() or similar:
SELECT typeof(TIMESTAMP '2015-02-04 14:34:28') = 'TIMESTAMP'
```

**DuckDB Example**:
```sql
SELECT typeof(TIMESTAMP '2015-02-04 14:34:28');
-- Returns: 'TIMESTAMP'
```

**Option C: Check Column Type Metadata**

Use database metadata to determine type:

```python
# Check if column/value is TIMESTAMP type
# More reliable than regex matching
```

**Recommendation**:
- **Short term**: Fix regex pattern (Option A) - quick win
- **Long term**: Consider native type checking (Option B) - more robust

**Success Criteria**:
- [ ] Approach chosen and documented
- [ ] Regex pattern fix designed (if Option A)
- [ ] Native type checking approach designed (if Option B)
- [ ] PostgreSQL compatibility considered

---

### Phase 3: Implementation (3-6 hours)

**Objective**: Implement the fix in both dialects.

**Implementation Steps** (Option A - Regex Fix):

**1. Locate Regex Patterns**:
```bash
# Find where regex_patterns are defined
grep -r "regex_patterns" fhir4ds/dialects/
```

**2. Test Current Format**:
```python
# Test what format DuckDB actually produces
import duckdb
conn = duckdb.connect()
result = conn.execute("SELECT CAST(TIMESTAMP '2015-02-04 14:34:28' AS VARCHAR)").fetchone()
print(f"DuckDB format: {result[0]}")
# Expected: '2015-02-04 14:34:28' (with space, not 'T')
```

**3. Update Regex Pattern**:
```python
# fhir4ds/dialects/duckdb.py or base_dialect.py

regex_patterns = {
    # OLD (possibly wrong):
    # 'DateTime': r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}',

    # NEW (fixed for DuckDB format):
    'DateTime': r'^\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}',

    # Or flexible (matches both T and space):
    'DateTime': r'^\\d{4}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}:\\d{2}',
}
```

**4. Update PostgreSQL Dialect** (if needed):
```python
# Check PostgreSQL's TIMESTAMP::VARCHAR format
# Update pattern accordingly if different from DuckDB
```

**5. Add Unit Tests**:
```python
def test_datetime_type_check():
    """Test .is(DateTime) returns true for datetime values"""
    expr = "@2015-02-04T14:34:28.is(DateTime)"
    result = execute_expression(expr)
    assert result == True  # Should return true!

def test_datetime_type_check_with_milliseconds():
    """Test .is(DateTime) with milliseconds"""
    expr = "@2015-02-04T14:34:28.123.is(DateTime)"
    result = execute_expression(expr)
    assert result == True

def test_non_datetime_type_check():
    """Test .is(DateTime) returns false for non-datetime"""
    expr = "'not a datetime'.is(DateTime)"
    result = execute_expression(expr)
    assert result == False
```

**Success Criteria**:
- [ ] Regex pattern updated
- [ ] Both dialects updated
- [ ] Unit tests created (3+ tests)
- [ ] Tests pass on both DuckDB and PostgreSQL

---

### Phase 4: Testing & Validation (1-3 hours)

**Objective**: Verify fix improves compliance test results.

**Unit Tests**:
- Type checking with various datetime formats
- Edge cases (with milliseconds, with timezone)
- Non-datetime values (should return false)

**Compliance Tests**:
```bash
# Run full compliance suite
PYTHONPATH=. DB_TYPE=duckdb python3 -m pytest tests/compliance/ -v

# Check improvement
# Expected: +20-30 tests from type checking category
```

**Expected Results**:
- Type_Functions: 37/116 → 55-65/116 (significant improvement)
- Overall: 452/934 → 472-482/934 (+20-30 tests)

**Success Criteria**:
- [ ] All unit tests pass
- [ ] No regressions
- [ ] Compliance improvement +15 tests minimum
- [ ] Both databases tested

---

## Acceptance Criteria

### Functional Requirements
- [ ] `.is(DateTime)` returns true for valid datetime values
- [ ] `.is(DateTime)` returns false for non-datetime values
- [ ] Works with full precision timestamps
- [ ] Works with partial precision (if SP-021-016 implemented)
- [ ] Both DuckDB and PostgreSQL supported

### Testing Requirements
- [ ] Unit tests cover positive and negative cases
- [ ] Compliance tests show +15 test minimum improvement
- [ ] No regressions in existing tests
- [ ] Both dialects tested

### Quality Requirements
- [ ] Pattern is maintainable and documented
- [ ] Solution works for both databases
- [ ] No performance degradation
- [ ] Code follows project standards

---

## Dependencies

**Prerequisites**:
- None required (can start immediately)
- **Recommended**: SP-021-016 (partial timestamps) for full compliance

**Blocks**:
- ~20-30 compliance tests currently failing
- Type checking function tests
- Type conversion tests

---

## Risk Assessment

### Technical Risks

**LOW**: Pattern fix is localized change
- **Mitigation**: Thoroughly test regex pattern first
- **Mitigation**: Add comprehensive unit tests

**MEDIUM**: Different formats between databases
- **Mitigation**: Test both DuckDB and PostgreSQL formats
- **Mitigation**: Use flexible pattern if formats differ

---

## Files to Modify

### Investigation
1. `fhir4ds/dialects/base_dialect.py` - Check regex_patterns
2. `fhir4ds/dialects/duckdb.py` - Type check implementation
3. `fhir4ds/dialects/postgresql.py` - PostgreSQL comparison

### Implementation
1. Regex pattern definition file (likely base_dialect.py)
2. Both dialect files if patterns differ

### Testing
1. `tests/unit/fhirpath/test_type_checks.py` (create if needed)
2. Compliance tests (verify improvement)

---

## Success Metrics

### Primary Metrics
- [ ] `.is(DateTime)` returns correct result
- [ ] +15 tests minimum (+20-30 expected)
- [ ] Type_Functions: 37/116 → 55-65/116

### Secondary Metrics
- [ ] No performance degradation
- [ ] Both dialects supported
- [ ] Maintainable solution

---

## Notes

### Related Issues

This fix builds on:
- REGEXP syntax fix from 2025-12-05 bug fix session
- Error visibility improvements

May interact with:
- SP-021-016: Partial timestamp conversion
- Future timezone handling improvements

### Investigation Commands

```bash
# Test DuckDB timestamp format
duckdb -c "SELECT CAST(TIMESTAMP '2015-02-04 14:34:28' AS VARCHAR)"

# Test PostgreSQL timestamp format
psql -c "SELECT TIMESTAMP '2015-02-04 14:34:28'::VARCHAR"

# Find regex patterns
grep -rn "regex_patterns" fhir4ds/dialects/

# Run type function tests only
pytest tests/unit/fhirpath/ -k "type" -v
```

---

**Created**: 2025-12-05
**Status**: Ready to start
**Assignee**: TBD
**Reviewer**: Senior Solution Architect
**Estimated Duration**: 8-16 hours
**Expected Impact**: +20-30 tests
