# Task SP-109-005: Comparison Operators - Temporal and Quantity

**Created:** 2026-01-29
**Sprint:** SP-109
**Impact:** 88 tests (74.0% → 100%, +9.4% overall)
**Effort:** 16-20 hours
**Priority:** P0
**Status:** Pending

---

## Objective

Implement datetime timezone handling, DATE/TIME compatibility, Quantity unit conversion, and calendar duration conversion to achieve 100% compliance in comparison operators category.

---

## Current State

**Comparison Operators: 74.0% (250/338 tests passing)**

### Key Issues Identified

1. **DateTime Timezone Handling**
   - `@2017-11-05T01:30:00.0-04:00 > @2017-11-05T01:15:00.0-05:00` fails
   - Timezone normalization not implemented
   - Different timezone representations not compared correctly

2. **DATE vs TIME Literal Comparisons**
   - `Patient.birthDate != @T12:14:15` fails with incompatible types error
   - DATE and TIME should be comparable (result is false, not error)
   - Type compatibility checks too restrictive

3. **Mixed-Type Comparisons**
   - `Observation.value.value < 'test'` fails
   - Quantity vs string comparisons not supported
   - Type coercion for comparisons incomplete

4. **Calendar Duration Comparisons**
   - `7 days = 1 'wk'` fails
   - Unit conversion not implemented
   - Calendar duration arithmetic missing

5. **DateTime vs Date Comparisons**
   - `now() > today()` fails
   - DateTime should be comparable to Date
   - Time component handling inconsistent

---

## Implementation Plan

### Step 1: Implement DateTime Timezone Normalization (4-5 hours)

**Problem:** Different timezones not compared correctly

**Solution:**
1. Parse timezone information from datetime literals
2. Convert all datetimes to UTC for comparison
3. Handle timezone offsets correctly
4. Test with various timezone scenarios

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/temporal_parser.py`
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/dialects/duckdb.py`
- `fhir4ds/dialects/postgresql.py`

**SQL Logic:**
```sql
-- Normalize to UTC before comparison
SELECT ... WHERE
    datetime1 AT TIME ZONE 'UTC' > datetime2 AT TIME ZONE 'UTC'
```

### Step 2: Fix DATE/TIME Type Compatibility (3-4 hours)

**Problem:** DATE and TIME comparisons error instead of returning false

**Solution:**
1. Update type compatibility matrix
2. Allow DATE vs TIME comparisons (always false)
3. Add proper type checking logic
4. Test all temporal type combinations

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/type_registry.py`
- `fhir4ds/main/fhirpath/sql/translator.py`

**Compatibility Matrix:**
| Type  | Date | Time | DateTime |
|-------|------|------|----------|
| Date  | OK   | False| OK       |
| Time  | False| OK   | False    |
| DateTime| OK | False| OK       |

### Step 3: Implement Quantity Unit Conversion (4-5 hours)

**Problem:** Quantity comparisons don't handle unit conversion

**Solution:**
1. Implement unit conversion logic
2. Parse UCUM units
3. Convert to common unit before comparison
4. Handle unitless quantities

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/quantity_builder.py` (or create new)
- `fhir4ds/main/fhirpath/sql/translator.py`

**Considerations:**
- Use UCUM unit conversion logic
- Handle incompatible units (error)
- Handle unitless quantities
- Support common units (days, weeks, etc.)

### Step 4: Implement Calendar Duration Conversion (3-4 hours)

**Problem:** Calendar durations not converted for comparison

**Solution:**
1. Implement calendar duration parsing
2. Convert durations to common unit
3. Support: days, weeks, months, years
4. Test duration comparisons

**Files to Modify:**
- `fhir4ds/main/fhirpath/types/temporal_parser.py`
- `fhir4ds/main/fhirpath/sql/translator.py`

**Duration Conversions:**
- 1 week = 7 days
- 1 month = 30 days (approximate)
- 1 year = 365 days (approximate)

### Step 5: Fix DateTime vs Date Comparisons (2-3 hours)

**Problem:** DateTime vs Date comparisons fail

**Solution:**
1. Implement DateTime to Date truncation
2. Compare Date components only
3. Handle time component correctly
4. Test edge cases (midnight, timezone)

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/dialects/duckdb.py`

**SQL Logic:**
```sql
-- DateTime vs Date comparison
SELECT ... WHERE
    DATE_TRUNC('day', datetime1) > date2
```

---

## Testing Strategy

### Unit Tests
1. Test timezone normalization
2. Test DATE/TIME compatibility
3. Test Quantity unit conversion
4. Test calendar duration conversion
5. Test DateTime vs Date comparisons

### Integration Tests
1. Test comparisons in expressions
2. Test comparisons with CTEs
3. Test comparisons across databases
4. Test timezone edge cases

### Compliance Tests
1. Run full comparison_operators test suite
2. Verify 100% pass rate
3. Check for regressions
4. Generate compliance report

---

## Success Criteria

- [ ] All 338 comparison_operators tests passing
- [ ] No regressions in other categories
- [ ] Code reviewed and approved
- [ ] Both DuckDB and PostgreSQL tests passing
- [ ] Overall compliance improved to 95.6%+

---

## Risk Assessment

**Risk Level:** Medium to High

**Risks:**
- Timezone handling is complex
- Unit conversion may be extensive
- Date/Time compatibility may have edge cases
- Calendar durations are approximate

**Mitigation:**
- Focus on common timezone scenarios first
- Use established UCUM conversion library
- Test edge cases thoroughly
- Document approximate conversions
- Start with simpler comparisons

---

## Dependencies

- SP-109-001 (type system improvements)
- SP-109-003 (function call improvements)

---

## Notes

- This is a high-impact task with many edge cases
- Timezone handling requires careful implementation
- Unit conversion may be a larger project
- Consider using existing libraries for UCUM
- Calendar durations are inherently approximate
- Focus on common cases first, edge cases second
