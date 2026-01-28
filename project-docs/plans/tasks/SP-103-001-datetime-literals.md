# Task SP-103-001: DateTime Literal Parsing

**Priority:** HIGH (Quick Win)  
**Category:** DateTime Literals  
**Estimated Tests Fixed:** 6  
**Complexity:** LOW  
**Estimated Time:** 2-3 hours

## Problem Statement

The FHIRPath parser does not correctly handle partial date/time literals in the official test suite:

1. **Year-only:** `@2015T.is(DateTime)` - should evaluate to true
2. **Month-only:** `@2015-02T.is(DateTime)` - should evaluate to true
3. **Day-only:** `@2015-02-04T.is(DateTime)` - should evaluate to true
4. **Hour-only:** `@T14.is(Time)` - should evaluate to true
5. **Time with UTC:** `@T14:34:28Z.is(Time)` - should evaluate to true
6. **Time with offset:** `@T14:34:28+10:00.is(Time)` - should evaluate to true

Currently, these expressions are either:
- Not recognized as valid DateTime/Time literals
- Incorrectly parsed, leading to evaluation failures

## Root Cause

The parser's literal handling likely only supports full ISO 8601 formats:
- Full date: `@2015-02-04`
- Full datetime: `@2015-02-04T14:34:28`
- Full time: `@T14:34:28`

But does NOT support partial formats:
- Year-only: `@2015T`
- Month-only: `@2015-02T`
- Hour-only: `@T14`
- Timezone suffix: `Z` or `+10:00`

## Implementation Plan

### Step 1: Locate Parser Code
```bash
# Find literal parsing
fhir4ds/fhirpath/parser.py
# Look for: DATETIME_LITERAL, TIME_LITERAL patterns
```

### Step 2: Update Literal Patterns

Add support for partial date/time formats:

```python
# Current pattern (example)
DATETIME_PATTERN = r'@\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?)?'

# Enhanced pattern
DATETIME_PATTERN = r'@(\d{4})(-\d{2})?(-\d{2})?(T(\d{2}))?(:\d{2})?(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?T?'
```

### Step 3: Update Type Validation

Ensure `is(DateTime)` and `is(Time)` correctly validate partial formats:

```python
# In type checking logic
def is_datetime_type(value):
    # Accept partial date/time formats
    pass
```

### Step 4: Test

```python
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner

runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='DateTime')

# Should see 6/6 tests passing
print(f"DateTime tests: {report.passed_tests}/{report.total_tests}")
```

## Acceptance Criteria

- [ ] All 6 datetime literal tests pass
- [ ] Parser accepts `@2015T`, `@2015-02T`, `@2015-02-04T` formats
- [ ] Parser accepts `@T14`, `@T14:34:28Z`, `@T14:34:28+10:00` formats
- [ ] `is(DateTime)` returns true for partial date formats
- [ ] `is(Time)` returns true for partial time formats
- [ ] No regressions in existing datetime tests
- [ ] DuckDB and PostgreSQL parity maintained

## Testing Commands

```bash
# Quick test
cd /mnt/d/sprint-SP-103
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='DateTime')
for r in runner.test_results:
    print(f'{r.name}: {r.passed} - {r.expression}')
    if not r.passed:
        print(f'  Error: {r.error_message}')
"

# Full validation
PYTHONPATH=. timeout 512 python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=50)
"
```

## Files to Modify

1. **fhir4ds/fhirpath/parser.py**
   - Update literal token patterns
   - Add partial datetime/time formats

2. **fhir4ds/fhirpath/fhir_types/** (if needed)
   - Update datetime type validation

3. **tests/unit/fhirpath/test_parser.py** (add tests)
   - Add unit tests for partial datetime literals

## Success Metrics

- Compliance increase: +0.6% (6 tests)
- No regressions in existing tests
- Code follows unified FHIRPath architecture

## Dependencies

None - this is a standalone fix

## Notes

- Keep changes minimal - only update literal patterns
- Ensure timezone handling (Z, +10:00) is correct
- Verify SQL generation for partial dates works correctly

---

**Task Status:** Ready for implementation  
**Assigned To:** executor  
**Review Status:** Pending
