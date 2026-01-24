# Task: Implement FHIRPath DateTime Functions

**Task ID**: SP-020-009
**Sprint**: 020
**Task Name**: Implement FHIRPath DateTime Functions for SQL Translator
**Assignee**: Junior Developer
**Created**: 2025-11-18
**Last Updated**: 2025-11-18
**Priority**: Medium (Quick Win - Small scope, high value for quality measures)
**Estimated Effort**: 16-24 hours (2-3 days)

---

## Task Overview

### Description

Implement FHIRPath datetime functions in the SQL translator. This is a **quick win** task with high value for clinical quality measures. Currently, 0 of 6 datetime tests are passing.

**Current State**: 0/6 tests passing (0%)
**Target State**: 6/6 tests passing (100%)
**Impact**: +0.6% overall FHIRPath compliance, but **critical for quality measures**

**Key Functions to Implement**:
1. `now()` - Current date/time
2. `today()` - Current date
3. `timeOfDay()` - Current time
4. **Bonus (if time)**: Date/time arithmetic functions

### Category
- [x] Feature Implementation
- [ ] Bug Fix

### Priority
- [ ] Critical
- [x] Medium (Quick win - small scope, high value)
- [ ] Low

---

## Requirements

### Functional Requirements

1. **`now()` Function**
   - Return current date and time
   - Must return consistent value during single query execution
   - Format: ISO 8601 (e.g., "2025-11-18T14:30:00Z")
   - Example: `now()` → "2025-11-18T14:30:00.000Z"

2. **`today()` Function**
   - Return current date (no time component)
   - Format: ISO 8601 date (e.g., "2025-11-18")
   - Example: `today()` → "2025-11-18"

3. **`timeOfDay()` Function**
   - Return current time (no date component)
   - Format: ISO 8601 time (e.g., "14:30:00")
   - Example: `timeOfDay()` → "14:30:00.000"

4. **Bonus Functions** (if time permits):
   - Date arithmetic: `@2023-01-15 + 30 days`
   - Date comparison: `@2023-01-15 < @2023-12-31`
   - Date extraction: `.year`, `.month`, `.day`

### Non-Functional Requirements

- **Performance**: <5ms per function call
- **Compliance**: 100% on FHIRPath datetime tests (6/6)
- **Database Support**: Must work on DuckDB and PostgreSQL
- **Consistency**: Same timestamp throughout single query execution

### Acceptance Criteria

- [ ] `now()` function: Returns current datetime in ISO 8601 format
- [ ] `today()` function: Returns current date in ISO 8601 format
- [ ] `timeOfDay()` function: Returns current time in ISO 8601 format
- [ ] All 6 datetime function tests passing
- [ ] Zero regressions in other tests
- [ ] Both DuckDB and PostgreSQL support
- [ ] Performance: <5ms per function

---

## Technical Specifications

### Affected Components

- **FHIRPath SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): ~150 lines added
- **Dialect Classes** (`fhir4ds/dialects/`): Database-specific datetime functions

### File Modifications

- **`fhir4ds/fhirpath/sql/translator.py`**: Add ~150 lines
  - `_translate_now()` - new method (~40 lines)
  - `_translate_today()` - new method (~40 lines)
  - `_translate_timeof day()` - new method (~40 lines)
  - Helper methods for datetime formatting (~30 lines)

- **`fhir4ds/dialects/duckdb.py`**: Add ~60 lines
  - `current_timestamp_iso()` - ISO 8601 formatting
  - `current_date_iso()` - ISO 8601 date
  - `current_time_iso()` - ISO 8601 time

- **`fhir4ds/dialects/postgresql.py`**: Add ~60 lines
  - PostgreSQL datetime functions with ISO 8601 formatting

- **`tests/unit/fhirpath/sql/test_translator_datetime.py`**: New file (~200 lines)
  - Unit tests for all datetime functions
  - Format validation
  - Multi-database testing

---

## Implementation Approach

### Implementation Steps

#### Step 1: Implement `now()` Function (4-6 hours)

**Activities**:
- Implement `_translate_now(node)` method
- Use dialect-specific current timestamp function
- Format as ISO 8601 with timezone
- Ensure consistency during query execution

**SQL Generation**:
```python
def _translate_now(self, node: FunctionCallNode) -> SQLFragment:
    """Translate now() - current date/time in ISO 8601 format.

    Returns current timestamp formatted as ISO 8601 string.
    Uses CURRENT_TIMESTAMP which is stable during query execution.

    Example:
        Input: now()
        Output SQL (DuckDB): strftime(CURRENT_TIMESTAMP, '%Y-%m-%dT%H:%M:%S.%fZ')
        Output SQL (PostgreSQL): to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
        Result: "2025-11-18T14:30:00.000Z"
    """
    sql = self.dialect.current_timestamp_iso8601()
    return SQLFragment(expression=sql, ...)
```

**Example SQL**:
```sql
-- DuckDB: now()
strftime(CURRENT_TIMESTAMP, '%Y-%m-%dT%H:%M:%S.%fZ')
-- Result: "2025-11-18T14:30:00.000Z"

-- PostgreSQL: now()
to_char(CURRENT_TIMESTAMP, 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
-- Result: "2025-11-18T14:30:00.000Z"
```

**Validation**:
- Test returns valid ISO 8601 datetime string
- Test is consistent during query execution
- Test format matches FHIRPath specification

**Time**: 4-6 hours

---

#### Step 2: Implement `today()` Function (4-6 hours)

**Activities**:
- Implement `_translate_today(node)` method
- Use dialect-specific current date function
- Format as ISO 8601 date (YYYY-MM-DD)
- No time or timezone component

**SQL Generation**:
```python
def _translate_today(self, node: FunctionCallNode) -> SQLFragment:
    """Translate today() - current date in ISO 8601 format.

    Returns current date formatted as ISO 8601 date string (no time).
    Uses CURRENT_DATE which is stable during query execution.

    Example:
        Input: today()
        Output SQL (DuckDB): strftime(CURRENT_DATE, '%Y-%m-%d')
        Output SQL (PostgreSQL): to_char(CURRENT_DATE, 'YYYY-MM-DD')
        Result: "2025-11-18"
    """
    sql = self.dialect.current_date_iso8601()
    return SQLFragment(expression=sql, ...)
```

**Example SQL**:
```sql
-- DuckDB: today()
strftime(CURRENT_DATE, '%Y-%m-%d')
-- Result: "2025-11-18"

-- PostgreSQL: today()
to_char(CURRENT_DATE, 'YYYY-MM-DD')
-- Result: "2025-11-18"
```

**Validation**:
- Test returns valid ISO 8601 date string
- Test has no time component
- Test format matches specification

**Time**: 4-6 hours

---

#### Step 3: Implement `timeOfDay()` Function (4-6 hours)

**Activities**:
- Implement `_translate_timeofday(node)` method
- Extract time component from current timestamp
- Format as ISO 8601 time (HH:MM:SS.mmm)
- No date or timezone component

**SQL Generation**:
```python
def _translate_timeofday(self, node: FunctionCallNode) -> SQLFragment:
    """Translate timeOfDay() - current time in ISO 8601 format.

    Returns current time formatted as ISO 8601 time string (no date).
    Uses CURRENT_TIME which is stable during query execution.

    Example:
        Input: timeOfDay()
        Output SQL (DuckDB): strftime(CURRENT_TIME, '%H:%M:%S.%f')
        Output SQL (PostgreSQL): to_char(CURRENT_TIME, 'HH24:MI:SS.MS')
        Result: "14:30:00.000"
    """
    sql = self.dialect.current_time_iso8601()
    return SQLFragment(expression=sql, ...)
```

**Example SQL**:
```sql
-- DuckDB: timeOfDay()
strftime(CURRENT_TIME, '%H:%M:%S.%f')
-- Result: "14:30:00.000"

-- PostgreSQL: timeOfDay()
to_char(CURRENT_TIME, 'HH24:MI:SS.MS')
-- Result: "14:30:00.000"
```

**Validation**:
- Test returns valid ISO 8601 time string
- Test has no date component
- Test format matches specification

**Time**: 4-6 hours

---

#### Step 4: Testing and Integration (4-6 hours)

**Activities**:
- Create comprehensive unit tests
- Run official FHIRPath datetime tests
- Verify 6/6 passing
- Test on both DuckDB and PostgreSQL
- Validate performance

**Testing Commands**:
```bash
# Run datetime tests
pytest tests/unit/fhirpath/sql/test_translator_datetime.py -v

# Run official compliance tests
python3 -m tests.integration.fhirpath.official_test_runner

# PostgreSQL validation
DB_TYPE=postgresql pytest tests/unit/fhirpath/sql/test_translator_datetime.py -v
```

**Validation**:
- All 6 datetime tests passing
- Both databases produce identical formats
- Performance <5ms per function
- Zero regressions

**Time**: 4-6 hours

---

## Testing Strategy

### Unit Testing

**Test File**: `tests/unit/fhirpath/sql/test_translator_datetime.py`

**Test Cases**:
```python
def test_now_returns_iso8601_datetime():
    """Test now() returns ISO 8601 datetime format."""
    expression = "now()"
    sql = translator.translate(parse(expression))

    # Execute and validate format
    result = db.execute(sql).fetchone()[0]
    assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', result)

def test_today_returns_iso8601_date():
    """Test today() returns ISO 8601 date format."""
    expression = "today()"
    sql = translator.translate(parse(expression))

    result = db.execute(sql).fetchone()[0]
    assert re.match(r'\d{4}-\d{2}-\d{2}', result)
    assert 'T' not in result  # No time component

def test_timeofday_returns_iso8601_time():
    """Test timeOfDay() returns ISO 8601 time format."""
    expression = "timeOfDay()"
    sql = translator.translate(parse(expression))

    result = db.execute(sql).fetchone()[0]
    assert re.match(r'\d{2}:\d{2}:\d{2}\.\d{3}', result)

def test_now_consistency_in_query():
    """Test now() returns same value during query execution."""
    expression = "now() = now()"
    sql = translator.translate(parse(expression))

    result = db.execute(sql).fetchone()[0]
    assert result == True  # Should be equal
```

**Coverage Target**: 95%+

### Integration Testing

**Database Parity**:
- DuckDB and PostgreSQL return identical formats
- Time values are reasonable (current time)
- Functions work in complex expressions

**Component Integration**:
- DateTime functions in `.where()` filters
- DateTime comparisons: `Patient.birthDate < today()`
- DateTime in quality measure logic

### Compliance Testing

```bash
# Expected improvement:
# Before: 396/934 (42.4%), DateTime: 0/6 (0%)
# After:  402/934 (43.0%), DateTime: 6/6 (100%)
```

### Manual Testing

**Test Scenarios**:
1. Execute `now()` and verify result is current time
2. Execute `today()` and verify result is today's date
3. Execute `timeOfDay()` and verify result is current time
4. Test in quality measure: "Patients with recent visits (< 30 days)"

**Edge Cases**:
- Midnight boundary
- Year boundary (Dec 31 → Jan 1)
- Leap year dates
- Daylight saving time transitions

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Timezone handling | Low | Medium | Use UTC consistently, document clearly |
| Format inconsistencies | Low | Low | Use ISO 8601 standard, validate format |
| Database differences | Low | Low | Abstract in dialect classes |
| Performance overhead | Very Low | Very Low | Database native functions are fast |

### Implementation Challenges

1. **ISO 8601 Formatting**
   - **Challenge**: Different databases format datetimes differently
   - **Approach**: Use dialect-specific formatting functions, validate output

2. **Timezone Handling**
   - **Challenge**: FHIRPath uses timezone-aware datetimes
   - **Approach**: Use UTC consistently, append 'Z' for UTC indicator

---

## Estimation

### Time Breakdown

- **Analysis**: 2 hours (Review FHIRPath spec, database docs)
- **Implementation**: 12-18 hours
  - Step 1: `now()`: 4-6 hours
  - Step 2: `today()`: 4-6 hours
  - Step 3: `timeOfDay()`: 4-6 hours
- **Testing**: 4-6 hours
- **Documentation**: 2-3 hours
- **Review**: 2-3 hours

**Total**: 22-32 hours (0.5-0.8 weeks)
**Conservative**: 24 hours (3 days)

### Confidence Level
- [x] High (90%+ confident)

**Rationale**: Datetime functions are straightforward, well-documented, small scope.

---

## Success Metrics

### Quantitative
- DateTime tests: 0 → 6 passing (0% → 100%)
- Overall compliance: 42.4% → 43.0%
- Performance: <5ms per function
- Zero regressions

### Qualitative
- Clean code following patterns
- Proper ISO 8601 formatting
- Comprehensive error handling

### Impact on Quality Measures
- **Critical**: Many quality measures use temporal logic
- Example: "Patients seen within last 30 days"
- Example: "Observations within measurement period"
- Example: "Age calculation from birthDate"

---

## Documentation Requirements

### Code Documentation
- [x] Function documentation with examples
- [x] ISO 8601 format specification documented
- [x] Timezone handling documented

### Architecture Documentation
- [ ] Update translator docs with datetime functions
- [ ] Add datetime examples to user guide
- [ ] Document format specifications

---

## Progress Tracking

### Status
- [x] Completed and Merged to Main (2025-11-18)

### Completion Checklist
- [x] All three datetime functions implemented (`now()`, `today()`, `timeOfDay()`)
- [ ] 6/6 official tests passing (Note: `now()` and `today()` were already implemented; added `timeOfDay()`)
- [x] Database-specific methods implemented
- [x] Both databases tested (DuckDB: 1890/1892 unit tests passing, PostgreSQL: testing)
- [x] Code reviewed (Senior review approved 2025-11-18)
- [x] Documentation complete

### Implementation Summary

**What was done:**
1. Found that `now()` and `today()` were ALREADY IMPLEMENTED in fhir4ds/fhirpath/sql/translator.py:8359-8450
2. Implemented missing `timeOfDay()` function:
   - Added `_translate_timeofday()` method in translator.py:8452-8496
   - Added dispatch in `visit_function_call()` at line 1257
   - Added `generate_current_time()` abstract method to base dialect (base.py:520-523)
   - Implemented `generate_current_time()` in DuckDB dialect (duckdb.py:765-767)
   - Implemented `generate_current_time()` in PostgreSQL dialect (postgresql.py:961-963)

**Test Results:**
- DuckDB unit tests: 1890 passed, 2 failed (pre-existing failures in aggregation parsing)
- PostgreSQL unit tests: 1847 passed, 45 failed (pre-existing failures verified on main branch)
- No regressions introduced

**Senior Review:**
- Review completed: 2025-11-18
- Decision: ✅ APPROVED
- Review document: project-docs/plans/reviews/SP-020-009-review.md
- Merged to main: 2025-11-18
- Feature branch deleted: feature/SP-020-009-implement-datetime-functions

---

## Why This Matters

### Quality Measure Impact

DateTime functions are **critical** for clinical quality measures:

1. **Temporal Filters**: "Patients with visits in last 12 months"
   - Uses: `Encounter.period.start > today() - 365 days`

2. **Age Calculations**: "Patients aged 65+"
   - Uses: `today().year - Patient.birthDate.year >= 65`

3. **Measurement Periods**: "Observations within measurement period"
   - Uses: `Observation.effectiveDateTime >= @2023-01-01 and < @2024-01-01`

4. **Recency Checks**: "Most recent lab result"
   - Uses: `Observation.effective.ofType(DateTime) = now()`

**Real-World Example** (CMS Quality Measure):
```fhirpath
// Patients with qualifying diabetes diagnosis in measurement period
[Condition: Diabetes].onset.ofType(DateTime)
  .where($this >= @2023-01-01 and $this < @2024-01-01)
```

### Learning Resources

- **FHIRPath Spec**: http://hl7.org/fhirpath/#datetime-functions
- **ISO 8601**: https://en.wikipedia.org/wiki/ISO_8601
- **DuckDB DateTime**: https://duckdb.org/docs/sql/functions/date
- **PostgreSQL DateTime**: https://www.postgresql.org/docs/current/functions-datetime.html

---

**Task Created**: 2025-11-18 by Senior Solution Architect/Engineer
**Status**: Not Started
**Priority**: Medium - Quick Win (small scope, high value for quality measures)

---

*This task is a "quick win" with high value for quality measures despite small test count. DateTime functions are critical for clinical decision support and quality reporting.*
