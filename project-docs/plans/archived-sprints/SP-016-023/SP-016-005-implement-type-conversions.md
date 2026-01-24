# Task: Implement Type Conversion Functions in FHIRPath Evaluator

**Task ID**: SP-016-005
**Sprint**: 016
**Task Name**: Implement Type Conversion Functions in FHIRPath Evaluator
**Assignee**: Junior Developer
**Created**: 2025-11-06
**Last Updated**: 2025-11-10
**Current Status**: Completed (2025-11-10)

---

## Task Overview

### Description

Implement type conversion and checking functions in the FHIRPath evaluator: `convertsToBoolean()`, `toBoolean()`, `convertsToInteger()`, `toInteger()`, `convertsToDecimal()`, `toDecimal()`, `convertsToQuantity()`, `toQuantity()`, `convertsToString()`, `toString()`, `convertsToDateTime()`, `toDateTime()`.

**Context**: These functions are missing from the evaluator and cause 40+ failures across multiple test categories (Arithmetic Operators, Type Functions). The compliance baseline shows multiple errors like "Unknown or unsupported function: convertsToDecimal".

**Impact**: Implementing type conversion functions should add **+10 to +15 tests**, helping reach the Sprint 016 target of 46.5% compliance.

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [x] Critical (Blocker for sprint goals)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **Conversion Check Functions** (return Boolean):
   - `convertsToBoolean(value)` - Check if convertible to Boolean
   - `convertsToInteger(value)` - Check if convertible to Integer
   - `convertsToDecimal(value)` - Check if convertible to Decimal
   - `convertsToQuantity(value)` - Check if convertible to Quantity
   - `convertsToString(value)` - Check if convertible to String
   - `convertsToDateTime(value)` - Check if convertible to DateTime

2. **Conversion Functions** (return converted value or empty):
   - `toBoolean(value)` - Convert to Boolean or empty
   - `toInteger(value)` - Convert to Integer or empty
   - `toDecimal(value)` - Convert to Decimal or empty
   - `toQuantity(value)` - Convert to Quantity or empty
   - `toString(value)` - Convert to String or empty
   - `toDateTime(value)` - Convert to DateTime or empty

3. **Conversion Rules**:
   - **Boolean**: 'true'/'false' strings, integers 0/1, booleans
   - **Integer**: numeric strings, integers, some decimals
   - **Decimal**: numeric strings, integers, decimals
   - **Quantity**: strings like '10 mg', '5.5 km'
   - **String**: all types can convert to string
   - **DateTime**: ISO 8601 date/time strings

4. **Error Handling**:
   - Invalid conversions → `convertsTo*()` returns `false`
   - Invalid conversions → `to*()` returns empty `{}`
   - Null/empty → returns empty `{}`

### Non-Functional Requirements

- **Performance**: Conversion checks should be fast (<1ms)
- **Compliance**: Target +10 to +15 official tests
- **Database Support**: Evaluator-only (no database changes)
- **Error Handling**: No exceptions, return false/empty per spec

### Acceptance Criteria

**Critical** (Must Have):
- [x] All `convertsTo*()` functions implemented (6 functions) - Already existed
- [x] All `to*()` functions implemented (6 functions) - Already existed
- [x] String → Integer/Decimal/Boolean conversions working
- [x] Integer ↔ Decimal conversions working
- [x] +35 official tests passing (exceeded +10 target!)
- [x] All existing unit tests still passing (no regressions)

**Important** (Should Have):
- [x] Quantity conversions (basic support) - Already implemented
- [x] DateTime conversions (ISO 8601) - Already implemented
- [x] Comprehensive error handling
- [x] Edge case coverage (null, empty, invalid)

**Nice to Have**:
- [ ] Advanced Quantity unit conversions
- [ ] DateTime timezone handling
- [ ] Performance optimization

---

## Technical Specifications

### Affected Components

**Primary Components**:
- **fhir4ds/fhirpath/evaluator/functions.py** - Function implementations
  - Add 12 new functions (6 convertsTo*, 6 to*)
  
- **fhir4ds/fhirpath/evaluator/evaluator.py** - Function registration
  - Register new functions in function registry

**Supporting Components**:
- **fhir4ds/fhirpath/types.py** - Type utilities
  - May need type checking/conversion helpers

### File Modifications

**Production Code**:
- `fhir4ds/fhirpath/evaluator/functions.py` (MODIFY - add ~300 lines):
  ```python
  def convertsToBoolean(value):
      """Check if value can convert to Boolean."""
      if isinstance(value, bool):
          return True
      if isinstance(value, str):
          return value.lower() in ['true', 'false']
      if isinstance(value, int):
          return value in [0, 1]
      return False
  
  def toBoolean(value):
      """Convert value to Boolean or return empty."""
      if isinstance(value, bool):
          return value
      if isinstance(value, str):
          if value.lower() == 'true':
              return True
          if value.lower() == 'false':
              return False
      if isinstance(value, int):
          if value == 1:
              return True
          if value == 0:
              return False
      return None  # Empty result
  
  def convertsToDecimal(value):
      """Check if value can convert to Decimal."""
      if isinstance(value, (int, float)):
          return True
      if isinstance(value, str):
          try:
              float(value)
              return True
          except (ValueError, TypeError):
              return False
      return False
  
  def toDecimal(value):
      """Convert value to Decimal or return empty."""
      if isinstance(value, (int, float)):
          return float(value)
      if isinstance(value, str):
          try:
              return float(value)
          except (ValueError, TypeError):
              return None
      return None
  ```

- `fhir4ds/fhirpath/evaluator/evaluator.py` (MODIFY - register functions):
  ```python
  # In function registry
  self.functions.update({
      'convertsToBoolean': convertsToBoolean,
      'toBoolean': toBoolean,
      'convertsToInteger': convertsToInteger,
      'toInteger': toInteger,
      'convertsToDecimal': convertsToDecimal,
      'toDecimal': toDecimal,
      # ... etc
  })
  ```

**Test Code**:
- `tests/unit/fhirpath/evaluator/test_type_conversions.py` (CREATE - ~400 lines):
  - Test each convertsTo* function
  - Test each to* function
  - Test edge cases
  - ~80-100 test cases

### Database Considerations

- **DuckDB**: No changes (evaluator-only)
- **PostgreSQL**: No changes (evaluator-only)
- **Schema Changes**: None

---

## Dependencies

### Prerequisites

1. **SP-016-002 Completed**: Clean test suite (✅ DONE)
2. **Function Registry**: Understand how functions are registered
3. **FHIRPath Spec**: Read type conversion section (6.5)

### Blocking Tasks

- None (can start immediately)

### Dependent Tasks

- **SP-016-003**: Arithmetic operators (uses toDecimal)
- **SP-016-004**: Lambda variables (may use conversions in tests)

---

## Implementation Approach

### High-Level Strategy

Implement conversion check functions first (`convertsTo*()`), then conversion functions (`to*()`). Start with simplest types (Boolean, Integer, Decimal, String), then add complex types (Quantity, DateTime) if time allows.

### Implementation Steps

#### Step 1: Implement Boolean Conversions (2 hours)

**Key Activities**:
```python
def convertsToBoolean(value):
    """Check if convertible to Boolean."""
    if value is None or value == []:
        return False
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return value.lower() in ['true', 'false', 't', 'f', 'yes', 'no', 'y', 'n']
    if isinstance(value, (int, float)):
        return value in [0, 1, 0.0, 1.0]
    return False

def toBoolean(value):
    """Convert to Boolean."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, bool):
        return [value]
    if isinstance(value, str):
        lower = value.lower()
        if lower in ['true', 't', 'yes', 'y', '1']:
            return [True]
        if lower in ['false', 'f', 'no', 'n', '0']:
            return [False]
    if isinstance(value, int):
        return [value != 0]
    return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_boolean -v
```

#### Step 2: Implement Integer Conversions (2 hours)

**Key Activities**:
```python
def convertsToInteger(value):
    """Check if convertible to Integer."""
    if value is None or value == []:
        return False
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, int) and not isinstance(value, bool):
        return True
    if isinstance(value, float):
        return value == int(value)  # No fractional part
    if isinstance(value, str):
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False
    return False

def toInteger(value):
    """Convert to Integer."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, int) and not isinstance(value, bool):
        return [value]
    if isinstance(value, float):
        if value == int(value):
            return [int(value)]
    if isinstance(value, str):
        try:
            return [int(value)]
        except (ValueError, TypeError):
            pass
    return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_integer -v
```

#### Step 3: Implement Decimal Conversions (2 hours)

**Key Activities**:
```python
def convertsToDecimal(value):
    """Check if convertible to Decimal."""
    if value is None or value == []:
        return False
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    return False

def toDecimal(value):
    """Convert to Decimal."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]
    if isinstance(value, str):
        try:
            return [float(value)]
        except (ValueError, TypeError):
            pass
    return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_decimal -v
```

#### Step 4: Implement String Conversions (2 hours)

**Key Activities**:
```python
def convertsToString(value):
    """Check if convertible to String - almost everything can be."""
    return value is not None and value != []

def toString(value):
    """Convert to String."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        return [value]
    if isinstance(value, bool):
        return ['true' if value else 'false']
    if isinstance(value, (int, float)):
        return [str(value)]
    # Try generic string conversion
    try:
        return [str(value)]
    except:
        return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_string -v
```

#### Step 5: Implement Quantity Conversions (3 hours)

**Key Activities**:
```python
import re

QUANTITY_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$')

def convertsToQuantity(value):
    """Check if convertible to Quantity."""
    if value is None or value == []:
        return False
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    # Quantity format: "value unit" (e.g., "10 mg", "5.5 km")
    if isinstance(value, str):
        return QUANTITY_PATTERN.match(value.strip()) is not None
    # Numbers convert to unitless quantities
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    return False

def toQuantity(value):
    """Convert to Quantity."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        match = QUANTITY_PATTERN.match(value.strip())
        if match:
            # Return as dict with value and unit
            return [{
                'value': float(match.group(1)),
                'unit': match.group(2)
            }]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Unitless quantity
        return [{'value': float(value), 'unit': '1'}]
    return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_quantity -v
```

#### Step 6: Implement DateTime Conversions (3 hours)

**Key Activities**:
```python
from datetime import datetime
import re

# ISO 8601 date/time patterns
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
DATETIME_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

def convertsToDateTime(value):
    """Check if convertible to DateTime."""
    if value is None or value == []:
        return False
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        # Check ISO 8601 format
        if DATE_PATTERN.match(value) or DATETIME_PATTERN.match(value):
            try:
                # Try parsing
                if 'T' in value:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    datetime.fromisoformat(value)
                return True
            except:
                return False
    return False

def toDateTime(value):
    """Convert to DateTime."""
    if value is None or value == []:
        return []
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, str):
        try:
            if 'T' in value:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(value)
            return [dt]
        except:
            return []
    return []
```

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_type_conversions.py::test_datetime -v
```

#### Step 7: Register Functions in Evaluator (2 hours)

**Key Activities**:
1. Find function registry in evaluator
2. Register all 12 functions:
   ```python
   from .functions import (
       convertsToBoolean, toBoolean,
       convertsToInteger, toInteger,
       convertsToDecimal, toDecimal,
       convertsToString, toString,
       convertsToQuantity, toQuantity,
       convertsToDateTime, toDateTime
   )
   
   self.functions = {
       # ... existing functions ...
       'convertsToBoolean': convertsToBoolean,
       'toBoolean': toBoolean,
       'convertsToInteger': convertsToInteger,
       'toInteger': toInteger,
       'convertsToDecimal': convertsToDecimal,
       'toDecimal': toDecimal,
       'convertsToString': toString,
       'toString': toString,
       'convertsToQuantity': convertsToQuantity,
       'toQuantity': toQuantity,
       'convertsToDateTime': convertsToDateTime,
       'toDateTime': toDateTime,
   }
   ```

3. Test that functions are callable

**Validation**:
```bash
pytest tests/unit/fhirpath/evaluator/test_function_registry.py -v
```

#### Step 8: Official Compliance Testing (2 hours)

**Key Activities**:
1. Run official test suite
2. Focus on Type Functions and Arithmetic Operators categories
3. Identify specific failures
4. Fix edge cases

**Validation**:
- Type Functions: 40-45/116 (34-39%) - up from 30/116 (25.9%)
- Overall: 405-410/934 (43.4-43.9%) - up from 395/934 (42.3%)
- Target: +10 to +15 tests

#### Step 9: Documentation (2 hours)

**Key Activities**:
1. Document conversion rules
2. Add examples for each function
3. Document edge cases
4. Self-review code

---

## Testing Strategy

### Unit Testing

**New Tests Required** (~90 tests):
```python
class TestConvertsToFunctions:
    # Boolean (10 tests)
    def test_convertsToBoolean_true_string(self): ...
    def test_convertsToBoolean_integer_0_1(self): ...
    def test_convertsToBoolean_invalid(self): ...
    
    # Integer (12 tests)
    def test_convertsToInteger_valid_string(self): ...
    def test_convertsToInteger_decimal_no_fraction(self): ...
    def test_convertsToInteger_invalid(self): ...
    
    # Decimal (10 tests)
    def test_convertsToDecimal_integer(self): ...
    def test_convertsToDecimal_string(self): ...
    def test_convertsToDecimal_invalid(self): ...
    
    # String (8 tests)
    def test_convertsToString_any_value(self): ...
    
    # Quantity (12 tests)
    def test_convertsToQuantity_valid_format(self): ...
    def test_convertsToQuantity_invalid_format(self): ...
    
    # DateTime (12 tests)
    def test_convertsToDateTime_iso8601(self): ...
    def test_convertsToDateTime_invalid(self): ...

class TestToFunctions:
    # Similar structure for to*() functions (~40 tests)
    ...

class TestEdgeCases:
    # Null, empty, type mismatches (~16 tests)
    ...
```

**Coverage Target**: 95%+ of conversion function code

### Integration Testing

- Official test suite before/after comparison
- Focus on Type Functions category

### Compliance Testing

**Before**: 395/934 (42.3%), Type Functions: 30/116 (25.9%)
**After Target**: 405-410/934 (43.4-43.9%), Type Functions: 40-45/116 (34-39%)
**Improvement**: +10 to +15 tests

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Conversion rule complexity | Medium | Medium | Follow spec strictly, comprehensive tests |
| Quantity format variations | Medium | Low | Support basic format, defer complex |
| DateTime timezone handling | Medium | Low | Use Python datetime, basic support |
| Edge case coverage incomplete | Medium | Medium | Test many edge cases, iterate |

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 2 hours
- **Boolean Conversions**: 2 hours
- **Integer Conversions**: 2 hours
- **Decimal Conversions**: 2 hours
- **String Conversions**: 2 hours
- **Quantity Conversions**: 3 hours
- **DateTime Conversions**: 3 hours
- **Function Registration**: 2 hours
- **Official Testing**: 2 hours
- **Documentation**: 2 hours
- **Total Estimate**: **22 hours** (~2.5-3 days)

### Confidence Level

- [x] High (90%+ confident in estimate)

---

## Success Metrics

### Quantitative Measures

- **Type Functions**: 40-45/116 (34-39%) - up from 30/116 (25.9%)
- **Overall Compliance**: 405-410/934 (43.4-43.9%) - up from 395/934 (42.3%)
- **Minimum Target**: +10 tests
- **Stretch Target**: +15 tests

---

## Progress Tracking

### Status

- [x] Not Started
- [x] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [x] Completed

### Completion Checklist

- [x] All 6 convertsTo*() functions implemented
- [x] All 6 to*() functions implemented
- [x] Functions registered in evaluator
- [x] All existing unit tests passing (274 tests)
- [ ] Official tests improved (awaiting SQL translator integration)
- [x] Code documented and reviewed

### Implementation Notes

**Date**: 2025-11-07

**Functions Implemented**:
1. `convertsToBoolean()` - Test if value can convert to boolean
2. `toBoolean()` - Convert value to boolean or empty
3. `convertsToInteger()` - Test if value can convert to integer
4. `toInteger()` - Convert value to integer or empty (updated)
5. `convertsToDecimal()` - Already existed
6. `toDecimal()` - Already existed
7. `convertsToString()` - Test if value can convert to string
8. `toString()` - Convert value to string or empty (updated)
9. `convertsToQuantity()` - Already existed
10. `toQuantity()` - Already existed
11. `convertsToDateTime()` - Test if value can convert to datetime
12. `toDateTime()` - Convert value to datetime or empty

**Changes Made**:
- Added 6 new type conversion functions to `fhir4ds/fhirpath/evaluator/functions.py`
- Updated `toString()` to follow FHIRPath spec (returns 'true'/'false' for booleans, empty for null)
- Updated `toInteger()` to follow FHIRPath spec (returns empty for floats with fractional parts)
- Updated 2 existing tests to match FHIRPath specification
- All 274 unit tests passing

**Note on Official Tests**:
The official FHIRPath test suite currently uses the SQL translator path (not the Python evaluator),
as indicated by the warning in `engine.py`. Type conversion improvements will be visible in official
tests once the SQL translator is updated to support these functions. This is beyond the scope of
this task which focuses on the Python evaluator.

---

**Task Created**: 2025-11-06 by Senior Solution Architect/Engineer
**Last Updated**: 2025-11-10
**Status**: Completed
**Completed Date**: 2025-11-10
**Merged to Main**: Yes

## Final Implementation (2025-11-10)

### Root Cause Discovery

After fixing the literal evaluation bug (SP-016-003), type conversion functions still weren't working. Investigation revealed:

**The Issue**: In `fhir4ds/fhirpath/evaluator/engine.py`, the `visit_function_call()` method was calling functions with `context.current_resource` instead of evaluating the target expression for member functions.

**Example**: For `1.convertsToInteger()`, the function was receiving the current resource (patient data) instead of the value `1`.

### The Fix

Added target evaluation for member functions in `visit_function_call()`:

```python
# Get the context data (value the function operates on)
# For member functions like value.function(), evaluate the target first
if hasattr(node, 'target') and node.target is not None:
    context_data = self.evaluate(node.target, context)
else:
    context_data = context.current_resource
```

This mirrors the approach already used for aggregate(), ensuring all member functions receive the correct context.

### Results

- **Official Compliance**: 44.4% → 48.2% (+35 tests, +3.8 percentage points)
- **Exceeded Target**: Surpassed Sprint 016 target of 46.5%!
- **All Tests Passing**: 21/21 type conversion tests, 75/75 arithmetic tests
- **No Regressions**: All aggregate and unit tests still passing

### Impact

This fix unblocked not just type conversions, but **all member functions** in the Python evaluator, including:
- Type conversion functions (convertsTo*, to*)
- String functions (startsWith, endsWith, contains, etc.)
- Collection functions with targets
- Any future member functions

---

*This task implements type conversion functions to resolve 40+ errors across multiple test categories, contributing to Sprint 016's 46.5% compliance target. The final fix also resolved a broader architectural issue with member function evaluation.*
