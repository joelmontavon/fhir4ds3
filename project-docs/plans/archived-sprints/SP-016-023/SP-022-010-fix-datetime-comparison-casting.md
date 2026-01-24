# Task: Fix Date/Time Type Casting in Comparisons

**Task ID**: SP-022-010
**Sprint**: 022
**Task Name**: Fix Date/Time Type Casting in Comparisons
**Assignee**: Junior Developer
**Created**: 2025-12-30
**Last Updated**: 2025-12-30

---

## Task Overview

### Description
When comparing FHIR date/time fields with date/time functions like `today()` or `now()`, the translator generates SQL that fails due to type mismatches. The extracted FHIR values are VARCHAR (JSON strings), but the comparison functions return native DATE or TIMESTAMP types.

**Current Behavior (WRONG):**
```sql
-- Expression: Patient.birthDate < today()
-- Generated SQL (fails):
SELECT (COALESCE(json_extract_string(resource, '$.birthDate.value'),
        json_extract_string(resource, '$.birthDate')) < current_date) AS result

-- Error: Cannot compare values of type VARCHAR and type DATE
```

**Expected Behavior:**
```sql
-- Should cast the extracted value to DATE before comparison:
SELECT (TRY_CAST(COALESCE(json_extract_string(resource, '$.birthDate.value'),
        json_extract_string(resource, '$.birthDate')) AS DATE) < current_date) AS result
```

The `datetime_functions` category has 0% passing (0/4 tests), and `comparison_operators` has many failures related to temporal comparisons.

### Category
- [x] Bug Fix

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Field < today()**: `Patient.birthDate < today()` must work without SQL errors
2. **Field > now()**: `Observation.effectiveDateTime > now()` must work
3. **today() > Field**: Reverse order comparisons must also work
4. **Mixed precision**: Comparing dates with datetimes should work (with appropriate semantics)

### Non-Functional Requirements
- **Performance**: Use efficient casting (TRY_CAST preferred over CAST)
- **Compliance**: Match FHIRPath specification for date/time comparison semantics
- **Database Support**: Work identically on DuckDB and PostgreSQL
- **Error Handling**: Invalid date strings should not cause SQL errors (return NULL/false)

### Acceptance Criteria
- [ ] `Patient.birthDate < today()` executes without error and returns correct results
- [ ] `now() > Patient.birthDate` executes without error
- [ ] `today() > Patient.birthDate` executes without error
- [ ] `Patient.birthDate != @1974-12-25T12:34:00Z` executes without error
- [ ] `Patient.birthDate != @T12:14:15` handles time vs date comparison gracefully
- [ ] Works with both DuckDB and PostgreSQL
- [ ] All existing passing tests continue to pass

---

## Technical Specifications

### Affected Components
- **ASTToSQLTranslator**: Binary operator handling for comparisons
- **Dialect Classes**: Type detection and casting helpers

### File Modifications

1. **`fhir4ds/fhirpath/sql/translator.py`**:
   - Modify `_translate_binary_operator()` (around line 2350-2535)
   - Add logic to detect date/time function results (today(), now(), timeOfDay())
   - Add casting logic when comparing VARCHAR with DATE/TIMESTAMP

### Root Cause Analysis

The current comparison logic (lines 2460-2477) handles JSON vs literal casting:
```python
# Cast left JSON string to match right literal type
if left_is_json and right_is_literal and right_literal_type:
    left_expr = self._apply_safe_cast_for_type(left_expr, right_literal_type)
```

However, it doesn't handle the case where:
- Right side is a **function result** (like `today()`) that returns a DATE type
- Left side is extracted JSON that returns VARCHAR

**The fix**: Detect when either operand is a date/time function result, and cast the other operand appropriately.

### Key Functions to Understand

Before modifying, read these functions in `translator.py`:

1. **`_translate_binary_operator()`** (line ~2350): Main comparison handling
2. **`_apply_safe_cast_for_type()`** (line ~2630): Applies TRY_CAST for a target type
3. **`_translate_today()`** (line ~9660): Returns DATE type SQL
4. **`_translate_now()`** (line ~9700): Returns TIMESTAMP type SQL

### Database Considerations
- **DuckDB**:
  - `TRY_CAST(varchar_col AS DATE)` returns NULL on invalid input
  - `current_date` returns DATE type
  - `now()` returns TIMESTAMP WITH TIME ZONE
- **PostgreSQL**:
  - Use `CAST(... AS DATE)` with error handling or regex validation
  - `CURRENT_DATE` returns DATE type
  - `now()` returns TIMESTAMP WITH TIME ZONE

---

## Dependencies

### Prerequisites
- Understanding of SQL type casting in DuckDB and PostgreSQL
- Familiarity with how `_translate_binary_operator()` works

### Blocking Tasks
- None

### Dependent Tasks
- SP-022-009 (conversion functions) uses similar casting patterns

---

## Implementation Approach

### High-Level Strategy
1. Detect when a comparison operand is a date/time function result
2. Determine the expected type of that function result (DATE, TIMESTAMP, TIME)
3. Cast the other operand to match before generating the comparison SQL

### Implementation Steps

1. **Add function result type detection**
   - Key Activities:
     - Create helper method `_get_datetime_function_type(fragment)` that returns:
       - `"date"` if fragment came from `today()`
       - `"timestamp"` if fragment came from `now()`
       - `"time"` if fragment came from `timeOfDay()`
       - `None` otherwise
     - Check fragment metadata for function name markers
   - Validation: Method correctly identifies today() fragments

2. **Modify `_translate_binary_operator()` to detect datetime comparisons**
   - Key Activities:
     - After translating left and right operands, check if either is a datetime function
     - If left is datetime function and right is JSON extraction, cast right to match
     - If right is datetime function and left is JSON extraction, cast left to match
   - Location: Around line 2460, add before existing JSON vs literal logic:
     ```python
     # Handle datetime function comparisons
     left_datetime_type = self._get_datetime_function_type(left_fragment)
     right_datetime_type = self._get_datetime_function_type(right_fragment)

     if left_datetime_type and self._is_json_extraction(right_fragment):
         right_expr = self._apply_safe_cast_for_type(right_expr, left_datetime_type)
     elif right_datetime_type and self._is_json_extraction(left_fragment):
         left_expr = self._apply_safe_cast_for_type(left_expr, right_datetime_type)
     ```
   - Validation: `Patient.birthDate < today()` generates correct SQL

3. **Add metadata markers to datetime functions**
   - Key Activities:
     - Modify `_translate_today()` to add `metadata={"datetime_function": "date"}`
     - Modify `_translate_now()` to add `metadata={"datetime_function": "timestamp"}`
     - Modify `_translate_time_of_day()` to add `metadata={"datetime_function": "time"}`
   - Validation: Fragments have correct metadata

4. **Add `_is_json_extraction()` helper**
   - Key Activities:
     - Create method to detect if a fragment is a JSON extraction (VARCHAR result)
     - Check for patterns like `json_extract_string`, `COALESCE(...json_extract...)`
   - Validation: Correctly identifies JSON extractions

5. **Test with both databases**
   - Key Activities:
     - Test `Patient.birthDate < today()` on DuckDB
     - Test `Patient.birthDate < today()` on PostgreSQL
     - Verify identical behavior
   - Validation: Both databases pass the same tests

---

## Testing Strategy

### Unit Testing
Test these expressions in isolation:
```python
# In Python REPL with test data
executor.execute("Patient.birthDate < today()")
executor.execute("now() > Patient.birthDate")
executor.execute("Patient.birthDate != @1974-12-25T12:34:00Z")
```

### Compliance Testing
```bash
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
# Filter for datetime-related tests
report = runner.run_official_tests(test_filter='today')
runner.print_compliance_summary(report)
"
```

### Manual Testing
Create test resource and verify:
```python
# Test data with known birthDate
resource = {"resourceType": "Patient", "birthDate": "1974-12-25"}

# These should all execute without SQL errors:
# 1. Patient.birthDate < today()  -> true (if today > 1974-12-25)
# 2. today() > Patient.birthDate  -> true
# 3. Patient.birthDate = today()  -> false
```

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking non-datetime comparisons | Medium | High | Test all comparison types after changes |
| Performance impact from casting | Low | Low | TRY_CAST is efficient |
| Edge cases with invalid dates | Medium | Medium | Use TRY_CAST to return NULL safely |

### Implementation Challenges
1. **Detecting JSON extractions**: Need reliable way to identify when a fragment contains JSON extraction
2. **Mixed precision comparisons**: Date vs DateTime needs careful handling per FHIRPath spec

---

## Success Metrics

### Quantitative Measures
- **Target**: `datetime_functions` category from 0% to 75%+
- **Target**: 10-15 additional `comparison_operators` tests passing

### Compliance Impact
- **Before**: `datetime_functions` at 0% (0/4), many comparison failures
- **After**: Target 75%+ datetime_functions, 50%+ comparison_operators

---

## Code Examples

### Example: Detecting Datetime Function Type
```python
def _get_datetime_function_type(self, fragment: SQLFragment) -> Optional[str]:
    """Detect if fragment is from a datetime function and return its type."""
    if fragment.metadata and isinstance(fragment.metadata, dict):
        return fragment.metadata.get("datetime_function")

    # Fallback: check expression patterns
    expr_lower = fragment.expression.lower()
    if "current_date" in expr_lower:
        return "date"
    elif "now()" in expr_lower:
        return "timestamp"
    elif "current_time" in expr_lower:
        return "time"

    return None
```

### Example: Adding Metadata to today()
```python
def _translate_today(self, node: FunctionCallNode) -> SQLFragment:
    # ... existing code ...

    return SQLFragment(
        expression=date_sql,
        source_table=self.context.current_table,
        requires_unnest=False,
        is_aggregate=False,
        metadata={"datetime_function": "date"}  # ADD THIS
    )
```

---

## Progress Tracking

### Status
- [x] Completed - Merged to Main

### Completion Checklist
- [x] `_get_datetime_function_type()` helper implemented
- [x] `_is_json_extraction()` helper implemented
- [x] `_translate_today()` adds datetime metadata (already had `fhir_type: Date`)
- [x] `_translate_now()` adds datetime metadata (already had `fhir_type: DateTime`)
- [x] `_translate_binary_operator()` handles datetime comparisons
- [x] `Patient.birthDate < today()` works on DuckDB
- [x] `Patient.birthDate < today()` works on PostgreSQL
- [x] Reverse comparisons work (`today() > Patient.birthDate`)
- [x] No regressions in existing tests

### Implementation Summary

**Changes made to `fhir4ds/fhirpath/sql/translator.py`:**

1. Added `_get_datetime_function_type()` helper method (lines 2856-2883):
   - Detects if a SQLFragment is from a datetime function (today, now, timeOfDay)
   - Returns the target type for casting ("date", "datetime", or "time")
   - Uses existing `fhir_type` metadata from datetime function translations

2. Added `_is_json_extraction()` helper method (lines 2885-2921):
   - Detects if a SQLFragment represents a JSON extraction (VARCHAR result)
   - Checks metadata for `is_json_string` marker
   - Falls back to expression pattern matching for JSON functions

3. Modified `_translate_binary_operator()` (lines 2506-2521):
   - Added datetime function comparison handling after existing literal type casting
   - When right operand is a datetime function and left is JSON extraction, casts left
   - When left operand is a datetime function and right is JSON extraction, casts right

**Test Results:**
- DuckDB: All datetime comparison tests pass
- PostgreSQL: All datetime comparison tests pass
- No regressions introduced (all pre-existing failures confirmed on main branch)

---

**Task Created**: 2025-12-30
**Task Completed**: 2025-12-31
**Merged to Main**: 2025-12-31
**Status**: Completed and Merged
