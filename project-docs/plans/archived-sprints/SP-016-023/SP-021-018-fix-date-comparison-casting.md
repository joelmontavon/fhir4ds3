# Task: Fix Date Comparison Type Casting

**Task ID**: SP-021-018-FIX-DATE-COMPARISON-CASTING
**Status**: READY TO START
**Priority**: 🟡 MEDIUM
**Created**: 2025-12-05
**Estimated Effort**: 4-8 hours
**Expected Impact**: +15-25 tests

---

## Objective

Fix date/datetime comparison operations to include proper type casting.

**Current Behavior**: Date comparisons fail with type mismatch errors
```fhirpath
now() > Patient.birthDate  // ✗ Error: Cannot compare TIMESTAMP and VARCHAR
```

**Expected Behavior**: Should automatically cast types for comparison
```fhirpath
now() > Patient.birthDate  // ✓ Should work with implicit casting
```

---

## Problem Statement

### Root Cause

**Error**:
```
BinderException: Binder Error: Cannot compare values of type TIMESTAMP WITH TIME ZONE and type VARCHAR - an explicit cast is required
```

**Explanation**:
- `now()` function returns `TIMESTAMP WITH TIME ZONE`
- `Patient.birthDate` is extracted from JSON as `VARCHAR`
- DuckDB requires explicit type casting for comparison

**Current SQL** (approximate):
```sql
SELECT now() > json_extract_string(resource, '$.birthDate')
-- ✗ Fails: TIMESTAMP > VARCHAR not allowed
```

**What's Needed**:
```sql
SELECT now() > CAST(json_extract_string(resource, '$.birthDate') AS TIMESTAMP)
-- ✓ Works: Both sides are TIMESTAMP
```

---

## Impact Analysis

### Affected Tests

Estimated ~15-25 official compliance tests involve date/datetime comparisons:
- Tests comparing `now()` with date fields
- Tests comparing datetime literals with resource dates
- Tests using `today()` function with dates
- Temporal filter operations

### Current Status

From 2025-12-05 bug fix investigation:
```
Expression: now() > Patient.birthDate
Error: BinderException: Cannot compare TIMESTAMP WITH TIME ZONE and VARCHAR
Status: Failing
```

Similar errors likely affect:
- DateTime comparisons
- Date arithmetic operations
- Temporal filtering

---

## Implementation Plan

### Phase 1: Investigation (1-2 hours)

**Objective**: Understand where comparisons are generated and identify all affected operations.

**Files to Review**:
1. `fhir4ds/fhirpath/sql/translator.py` - How comparisons are translated
2. `fhir4ds/dialects/duckdb.py` - SQL generation for comparisons
3. `fhir4ds/dialects/postgresql.py` - PostgreSQL comparison handling

**Questions to Answer**:
- Where are comparison operations (`>`, `<`, `>=`, `<=`, `=`) generated?
- How are operand types currently detected?
- Is there existing type casting logic?
- What types need casting? (DATE, TIMESTAMP, DATETIME)

**Search Patterns**:
```bash
# Find comparison generation
grep -rn "def.*comparison" fhir4ds/

# Find existing casting logic
grep -rn "CAST.*TIMESTAMP" fhir4ds/

# Find type detection
grep -rn "typeof\|type_of" fhir4ds/
```

**Success Criteria**:
- [ ] Located comparison SQL generation code
- [ ] Identified existing type casting (if any)
- [ ] Documented current comparison handling
- [ ] Listed all temporal comparison operators

---

### Phase 2: Design Solution (1-2 hours)

**Objective**: Design type-aware comparison logic.

**Approach: Smart Type Detection + Automatic Casting**

**Design Pattern**:
```python
def generate_comparison(left_expr, operator, right_expr):
    """Generate comparison with automatic type casting."""

    # Detect operand types
    left_type = detect_operand_type(left_expr)
    right_type = detect_operand_type(right_expr)

    # If types mismatch and involve temporal types, add casts
    if needs_temporal_casting(left_type, right_type):
        left_expr, right_expr = add_temporal_casts(
            left_expr, left_type,
            right_expr, right_type
        )

    return f"{left_expr} {operator} {right_expr}"
```

**Type Detection Logic**:
```python
def detect_operand_type(expr: str) -> str:
    """Detect SQL expression type."""

    # Check for temporal functions
    if 'now()' in expr or 'today()' in expr:
        return 'TIMESTAMP'

    # Check for TIMESTAMP literals
    if 'TIMESTAMP' in expr:
        return 'TIMESTAMP'

    # Check for DATE literals
    if 'DATE' in expr and 'TIMESTAMP' not in expr:
        return 'DATE'

    # Check for JSON extraction (usually VARCHAR)
    if 'json_extract' in expr:
        return 'VARCHAR'  # May need to be cast

    return 'UNKNOWN'
```

**Casting Rules**:
```python
def add_temporal_casts(left_expr, left_type, right_expr, right_type):
    """Add casts to make temporal comparison work."""

    # VARCHAR compared with TIMESTAMP → cast VARCHAR to TIMESTAMP
    if left_type == 'VARCHAR' and right_type == 'TIMESTAMP':
        left_expr = f"CAST({left_expr} AS TIMESTAMP)"

    if right_type == 'VARCHAR' and left_type == 'TIMESTAMP':
        right_expr = f"CAST({right_expr} AS TIMESTAMP)"

    # DATE compared with TIMESTAMP → cast DATE to TIMESTAMP
    if left_type == 'DATE' and right_type == 'TIMESTAMP':
        left_expr = f"CAST({left_expr} AS TIMESTAMP)"

    if right_type == 'DATE' and left_type == 'TIMESTAMP':
        right_expr = f"CAST({right_expr} AS TIMESTAMP)"

    return left_expr, right_expr
```

**Success Criteria**:
- [ ] Type detection algorithm designed
- [ ] Casting rules defined
- [ ] Edge cases identified
- [ ] PostgreSQL compatibility considered

---

### Phase 3: Implementation (2-4 hours)

**Objective**: Implement comparison casting in both dialects.

**Implementation Steps**:

**1. Add Type Detection Helper**:
```python
# fhir4ds/dialects/base_dialect.py

class SQLDialect:
    """Base SQL dialect with common functionality."""

    def detect_expression_type(self, expr: str) -> str:
        """
        Detect SQL expression type.

        Returns: 'TIMESTAMP', 'DATE', 'VARCHAR', 'INTEGER', 'UNKNOWN'
        """
        # Implement type detection logic
        # (see Phase 2 design)
```

**2. Add Casting Helper**:
```python
    def cast_for_comparison(
        self,
        left_expr: str,
        right_expr: str
    ) -> tuple[str, str]:
        """
        Add type casts for comparison operations.

        Automatically detects types and adds casts where needed.
        """
        left_type = self.detect_expression_type(left_expr)
        right_type = self.detect_expression_type(right_expr)

        # Apply casting rules
        # (see Phase 2 design)

        return left_expr, right_expr
```

**3. Update Comparison Generation**:
```python
# fhir4ds/dialects/duckdb.py

class DuckDBDialect(SQLDialect):

    def generate_comparison(
        self,
        left_expr: str,
        operator: str,
        right_expr: str
    ) -> str:
        """Generate comparison with automatic type casting."""

        # Add casts if needed
        left_expr, right_expr = self.cast_for_comparison(
            left_expr, right_expr
        )

        return f"{left_expr} {operator} {right_expr}"
```

**4. Update PostgreSQL Dialect**:
```python
# fhir4ds/dialects/postgresql.py

class PostgreSQLDialect(SQLDialect):
    # Inherit cast_for_comparison from base
    # Override if PostgreSQL has different casting requirements
```

**5. Add Unit Tests**:
```python
def test_timestamp_varchar_comparison():
    """Test now() > Patient.birthDate casts correctly"""
    expr = "now() > Patient.birthDate"
    sql = translator.translate(expr)
    # Should contain CAST(...birthDate... AS TIMESTAMP)
    assert "CAST" in sql
    assert "AS TIMESTAMP" in sql

def test_date_literal_comparison():
    """Test @2015-01-01 > Patient.birthDate"""
    expr = "@2015-01-01 > Patient.birthDate"
    sql = translator.translate(expr)
    result = execute(sql)
    # Should execute without BinderException
```

**Success Criteria**:
- [ ] Type detection implemented
- [ ] Casting logic implemented
- [ ] Both dialects updated
- [ ] Unit tests created (3+ tests)
- [ ] Tests pass

---

### Phase 4: Testing & Validation (1-2 hours)

**Objective**: Verify fix resolves comparison errors.

**Unit Tests**:
```python
class TestDateComparisons:
    def test_now_vs_birthdate(self):
        """now() > Patient.birthDate should work"""

    def test_today_vs_date(self):
        """today() = @2015-01-01 should work"""

    def test_datetime_literal_vs_field(self):
        """@2015-01-01T00:00:00 > Patient.birthDate"""

    def test_symmetric_casting(self):
        """Patient.birthDate < now() should also work"""
```

**Compliance Tests**:
```bash
# Run full suite
PYTHONPATH=. DB_TYPE=duckdb python3 -m pytest tests/compliance/ -v

# Expected improvement
# +15-25 tests from temporal comparison operations
```

**Manual Verification**:
```sql
-- Execute generated SQL directly in DuckDB
-- Verify no BinderException errors
```

**Success Criteria**:
- [ ] All unit tests pass
- [ ] No BinderException errors
- [ ] Compliance improvement +10 tests minimum
- [ ] Both databases tested

---

## Acceptance Criteria

### Functional Requirements
- [ ] `now() > Patient.birthDate` works without error
- [ ] Other temporal comparisons work (`<`, `<=`, `>=`, `=`)
- [ ] Symmetric operations work (field > function and function > field)
- [ ] Both DuckDB and PostgreSQL supported

### Testing Requirements
- [ ] Unit tests cover various comparison operators
- [ ] Compliance tests improve +10 tests minimum
- [ ] No regressions in existing tests
- [ ] Both dialects tested

### Quality Requirements
- [ ] Type detection is maintainable
- [ ] Casting logic is clear and documented
- [ ] No performance degradation
- [ ] Works for both databases

---

## Dependencies

**Prerequisites**: None - can start immediately

**Blocks**:
- ~15-25 compliance tests with temporal comparisons
- Date/datetime filtering operations
- Temporal arithmetic operations (potentially)

---

## Risk Assessment

### Technical Risks

**LOW**: Well-defined problem with clear solution
- **Mitigation**: Type detection is explicit and testable
- **Mitigation**: Casting rules are straightforward

**LOW-MEDIUM**: Different database casting requirements
- **Mitigation**: Test both DuckDB and PostgreSQL
- **Mitigation**: Use base class for shared logic

**LOW**: Over-casting edge cases
- **Mitigation**: Only cast when type mismatch detected
- **Mitigation**: Add tests for already-compatible types

---

## Files to Modify

### Implementation
1. `fhir4ds/dialects/base_dialect.py` - Add type detection helpers
2. `fhir4ds/dialects/duckdb.py` - Update comparison generation
3. `fhir4ds/dialects/postgresql.py` - Update if needed
4. Translator file (if comparisons generated there)

### Testing
1. `tests/unit/fhirpath/test_date_comparisons.py` (create)
2. Compliance tests (verify improvement)

---

## Success Metrics

### Primary Metrics
- [ ] Temporal comparisons work without BinderException
- [ ] +10 tests minimum (+15-25 expected)
- [ ] No regressions

### Secondary Metrics
- [ ] Both databases supported
- [ ] Maintainable solution
- [ ] No performance impact

---

## Notes

### Related Work

This fix complements:
- SP-021-016: Partial timestamp conversion
- SP-021-017: DateTime type check fixes
- REGEXP bug fix from 2025-12-05

### FHIRPath Specification

FHIRPath requires implicit type conversion for comparisons:
> When comparing values of different types, implementations should attempt automatic conversion where semantically appropriate.

### Database-Specific Notes

**DuckDB**:
- Requires explicit CAST for TIMESTAMP vs VARCHAR
- Error message: "an explicit cast is required"

**PostgreSQL**:
- May have similar requirements
- Test carefully for compatibility

---

**Created**: 2025-12-05
**Status**: Ready to start
**Assignee**: TBD
**Reviewer**: Senior Solution Architect
**Estimated Duration**: 4-8 hours
**Expected Impact**: +15-25 tests
