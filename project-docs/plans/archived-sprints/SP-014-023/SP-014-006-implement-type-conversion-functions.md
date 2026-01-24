# Task: SP-014-006 - Implement Type Conversion Functions

**Task ID**: SP-014-006
**Sprint**: Sprint 014 - Regression Analysis and Recovery
**Task Name**: Implement FHIRPath Type Conversion Functions (toDecimal, convertsToDecimal, toQuantity, convertsToQuantity)
**Assignee**: Junior Developer
**Created**: 2025-10-28
**Last Updated**: 2025-10-28

---

## Task Overview

### Description

Implement four critical FHIRPath type conversion functions that are currently missing: `toDecimal()`, `convertsToDecimal()`, `toQuantity()`, and `convertsToQuantity()`. These functions are essential for type casting and validation in FHIRPath expressions, particularly for numeric conversions and quantity parsing in healthcare data.

**Context from SP-014-002**: Type conversion functions are identified as a high-impact fix, affecting 31 tests across the official FHIRPath R4 test suite. The functions `toDecimal()` and `convertsToDecimal()` account for 17 and 14 failures respectively. While `toQuantity()` and `convertsToQuantity()` have fewer direct test failures, they are critical for complete FHIRPath specification compliance and healthcare-specific quantity handling (e.g., "5.5 'mg'").

**Example Failing Expressions**:
```fhirpath
'123.45'.toDecimal()                    // Should return 123.45 (decimal)
'invalid'.toDecimal()                   // Should return empty collection {}
'123.45'.convertsToDecimal()            // Should return true
'invalid'.convertsToDecimal()           // Should return false
'5.5 \'mg\''.toQuantity()               // Should return Quantity{value: 5.5, unit: 'mg'}
'5.5 \'mg\''.convertsToQuantity()       // Should return true
```

**Impact**: Implementing these functions will improve compliance from 46% (after union operator) to approximately 49-50%, a gain of +31 tests. This represents the third-highest impact fix from SP-014-002 analysis.

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [ ] Critical (Blocker for sprint goals)
- [x] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Third-highest impact fix from SP-014-002 analysis (+31 tests). Essential for numeric type handling and healthcare quantity parsing. Relatively straightforward implementation compared to other high-impact fixes.

---

## Requirements

### Functional Requirements

1. **Implement toDecimal() Function**: Convert values to decimal (floating-point) representation
   - Handle integer inputs: `42.toDecimal()` → `42.0`
   - Handle string inputs: `'123.45'.toDecimal()` → `123.45`
   - Handle boolean inputs: `true.toDecimal()` → `{}` (empty collection per spec)
   - Handle invalid inputs: `'not-a-number'.toDecimal()` → `{}` (empty collection)
   - Handle empty collections: `{}.toDecimal()` → `{}`
   - Handle NULL: `NULL.toDecimal()` → `{}`

2. **Implement convertsToDecimal() Function**: Test if value can be converted to decimal
   - Return boolean indicating conversion validity
   - Same input type handling as toDecimal() but returns true/false
   - `'123.45'.convertsToDecimal()` → `true`
   - `'invalid'.convertsToDecimal()` → `false`
   - `true.convertsToDecimal()` → `false` (booleans don't convert per spec)

3. **Implement toQuantity() Function**: Parse FHIR Quantity from string
   - Parse FHIR Quantity format: `value 'unit'`
   - Handle decimal values: `'5.5 \'mg\''` → `Quantity{value: 5.5, unit: 'mg'}`
   - Handle integer values: `'100 \'mg\''` → `Quantity{value: 100, unit: 'mg'}`
   - Handle unitless quantities: `'42'` → `Quantity{value: 42, unit: ''}`
   - Handle invalid formats: `'not-a-quantity'` → `{}` (empty collection)
   - Support UCUM unit syntax (healthcare standard)

4. **Implement convertsToQuantity() Function**: Test if value can be converted to Quantity
   - Return boolean indicating Quantity conversion validity
   - Validate FHIR Quantity format without performing conversion
   - `'5.5 \'mg\''.convertsToQuantity()` → `true`
   - `'invalid'.convertsToQuantity()` → `false`

### Non-Functional Requirements

- **Performance**: Conversion functions should execute in O(1) time for scalar values
- **Compliance**: Must pass all 31 type conversion tests from official FHIRPath R4 test suite
- **Database Support**: Must work identically in both DuckDB and PostgreSQL environments
- **Error Handling**: Graceful handling of invalid inputs, returning empty collections (not exceptions)
- **Precision**: Decimal conversions must maintain precision per FHIRPath specification
- **Standards Alignment**: Quantity parsing must follow FHIR Quantity format and UCUM standards

### Acceptance Criteria

- [ ] toDecimal() function implemented and registered in function library
- [ ] convertsToDecimal() function implemented and registered
- [ ] toQuantity() function implemented with FHIR Quantity parsing
- [ ] convertsToQuantity() function implemented with format validation
- [ ] All four functions handle integer, string, boolean, and null inputs correctly
- [ ] Invalid inputs return empty collections (toDecimal/toQuantity) or false (convertsTo*)
- [ ] Decimal precision preserved in conversions
- [ ] Quantity format parsing supports FHIR/UCUM syntax
- [ ] At least 28 of 31 type conversion tests passing (90% target)
- [ ] No regressions in other test categories
- [ ] Both DuckDB and PostgreSQL implementations working
- [ ] Unit tests written with >90% coverage
- [ ] Integration tests with official test suite passing

---

## Technical Specifications

### Affected Components

- **FHIRPath Function Library** (`fhir4ds/fhirpath/evaluator/functions.py`): Add function implementations
- **Type System** (`fhir4ds/fhirpath/types/`): May need Quantity type support
- **SQL Translator** (if needed): SQL generation for type conversions
- **Database Dialects** (if needed): Database-specific decimal/quantity handling

### File Modifications

**PRIMARY MODIFICATIONS**:
- **MODIFY**: `/mnt/d/fhir4ds2/fhir4ds/fhirpath/evaluator/functions.py`
  - Add `fn_to_decimal` method (already exists - needs enhancement)
  - Add `fn_converts_to_decimal` method (NEW)
  - Add `fn_to_quantity` method (NEW)
  - Add `fn_converts_to_quantity` method (NEW)
  - Register new functions in `_register_functions` method
  - Add helper methods: `_try_to_decimal`, `_parse_quantity`, `_validate_quantity_format`

**SECONDARY MODIFICATIONS** (if needed):
- **MODIFY**: `/mnt/d/fhir4ds2/fhir4ds/fhirpath/types/fhir_types.py` (if Quantity type class needed)
- **CREATE**: `/mnt/d/fhir4ds2/tests/unit/fhirpath/evaluator/test_type_conversion_functions.py` (unit tests)

**DOCUMENTATION**:
- **UPDATE**: Function documentation in code
- **UPDATE**: FHIRPath compliance tracking

### Database Considerations

**DuckDB**:
- Decimal conversion: Use `CAST(value AS DECIMAL)` or `TRY_CAST` for safe conversion
- Type checking: Use `TRY_CAST` to test convertibility without errors
- String parsing: Use DuckDB string functions for Quantity parsing

**PostgreSQL**:
- Decimal conversion: Use `CAST(value AS NUMERIC)` or PostgreSQL's safe casting
- Type checking: Use `value::numeric` in exception handler or regexp validation
- String parsing: Use PostgreSQL regexp functions for Quantity format validation

**Quantity Representation**:
- Option 1: Return Python dict: `{'value': 5.5, 'unit': 'mg'}`
- Option 2: Create Quantity class (more complex, better type safety)
- Option 3: Return tuple: `(5.5, 'mg')`
- **Recommended**: Start with dict for simplicity, refactor to class if needed

**Type Handling**: Both databases must:
- Handle NULL inputs gracefully (return empty collection)
- Preserve decimal precision (not round prematurely)
- Validate format before conversion
- Return consistent types across dialects

---

## Dependencies

### Prerequisites

1. **SP-014-004 Complete**: Union operator implemented (expected 46% compliance baseline)
2. **SP-014-005 Complete**: List bounds checking fixed (stability prerequisite)
3. **FHIRPath Specification**: Section on type conversion functions (toDecimal, toQuantity semantics)
4. **FHIR Quantity Specification**: Understanding of FHIR Quantity format and UCUM units
5. **Python Decimal Module**: Understanding of `decimal.Decimal` for precision

### Blocking Tasks

- **SP-014-004**: Union operator (recommended completion first for baseline)
- **SP-014-005**: List bounds checking (optional but recommended for stability)

### Dependent Tasks

- **SP-014-007**: String comparison fix (may benefit from convertsTo* validation functions)
- **Future tasks**: Any FHIRPath expressions using type conversion functions

---

## Implementation Approach

### High-Level Strategy

**Approach**: Implement type conversion functions directly in the FHIRPath function library (`functions.py`), following the established pattern of existing conversion functions like `toInteger()` and `toString()`. Use Python's native type system and `decimal.Decimal` for precision. Parse Quantity format using regular expressions for FHIR compliance.

**Key Decisions**:
1. **Enhancement vs. New**: `toDecimal()` already exists but may need enhancement; `convertsToDecimal()`, `toQuantity()`, and `convertsToQuantity()` are entirely new
2. **Decimal Precision**: Use Python `decimal.Decimal` for arbitrary precision (FHIRPath requirement)
3. **Quantity Format**: Parse FHIR format `value 'unit'` using regex, support UCUM units
4. **Error Handling**: Return empty collections for invalid conversions (FHIRPath idiom), not exceptions
5. **SQL Generation**: May not need SQL generation if evaluation happens in Python (depends on architecture)

**Rationale**: Function library approach is simplest and aligns with existing toInteger/toString implementations. Using Python's decimal module ensures precision. Regex parsing is sufficient for Quantity format validation.

### Implementation Steps

#### Step 1: Analyze Existing toDecimal() Implementation (30 minutes)

**Objective**: Understand current toDecimal() implementation and identify what needs enhancement.

**Key Activities**:
1. Read existing `fn_to_decimal` method in `functions.py` (line ~308-311)
2. Examine helper method `_to_decimal` (should be later in file)
3. Review test failures to understand what's currently broken
4. Identify gaps: Does it handle all input types? Does it return empty on invalid input?
5. Determine if enhancement or rewrite is needed

**Validation**:
- Document current behavior vs. specification requirements
- List specific enhancements needed
- Identify test cases that should pass after fix

**Expected Output**: Clear understanding of toDecimal() current state and required changes

---

#### Step 2: Implement/Enhance toDecimal() Function (1.5 hours)

**Objective**: Implement robust toDecimal() conversion handling all input types per FHIRPath spec.

**Key Activities**:
1. Review FHIRPath specification for toDecimal() semantics
   - Valid inputs: integer, decimal (identity), string (parse)
   - Invalid inputs: boolean, complex types → return empty collection

2. Implement enhanced `fn_to_decimal` method:
   ```python
   @fhirpath_function('toDecimal', min_args=0, max_args=0)
   def fn_to_decimal(self, context_data: Any, args: List[Any], context: 'EvaluationContext') -> Union[Decimal, List]:
       """
       Convert value to decimal (arbitrary precision floating-point)

       Per FHIRPath spec:
       - Integer → Decimal (convert directly)
       - String → Decimal (parse, return {} if invalid)
       - Boolean → {} (empty collection)
       - Null → {} (empty collection)
       - Already Decimal → identity

       Returns:
           Decimal value or empty list for invalid conversion
       """
       if context_data is None:
           return []

       # Handle collections: toDecimal() operates on single values
       if isinstance(context_data, list):
           if len(context_data) == 0:
               return []
           if len(context_data) == 1:
               return self.fn_to_decimal(context_data[0], args, context)
           # Multiple items - per spec, return empty
           return []

       # Boolean explicitly not convertible to decimal
       if isinstance(context_data, bool):
           return []

       # Integer converts directly
       if isinstance(context_data, int):
           return Decimal(str(context_data))

       # Float/Decimal already numeric
       if isinstance(context_data, (float, Decimal)):
           return Decimal(str(context_data))

       # String - attempt parse
       if isinstance(context_data, str):
           return self._try_parse_decimal(context_data.strip())

       # Other types not convertible
       return []
   ```

3. Implement helper method `_try_parse_decimal`:
   ```python
   def _try_parse_decimal(self, value_str: str) -> Union[Decimal, List]:
       """
       Attempt to parse string to Decimal

       Args:
           value_str: String to parse

       Returns:
           Decimal if valid, empty list otherwise
       """
       if not value_str:
           return []

       try:
           # Use Python's Decimal for arbitrary precision
           result = Decimal(value_str)

           # Check for special values (NaN, Infinity)
           if result.is_nan() or result.is_infinite():
               return []

           return result
       except (ValueError, decimal.InvalidOperation):
           # Invalid decimal format
           return []
   ```

4. Import `Decimal` at top of file:
   ```python
   from decimal import Decimal, InvalidOperation
   ```

5. Test with manual examples:
   - `42` → `Decimal('42')`
   - `'123.45'` → `Decimal('123.45')`
   - `'invalid'` → `[]`
   - `true` → `[]`
   - `{}` → `[]`

**Validation**:
- toDecimal() handles all input types correctly
- Invalid inputs return empty collection (not exceptions)
- Decimal precision preserved
- Test with official test cases manually

**Expected Output**: Working toDecimal() implementation

---

#### Step 3: Implement convertsToDecimal() Function (1 hour)

**Objective**: Implement boolean validator that tests if value can convert to decimal.

**Key Activities**:
1. Implement `fn_converts_to_decimal` method:
   ```python
   @fhirpath_function('convertsToDecimal', min_args=0, max_args=0)
   def fn_converts_to_decimal(self, context_data: Any, args: List[Any], context: 'EvaluationContext') -> bool:
       """
       Test if value can be converted to decimal

       Returns true if toDecimal() would succeed, false otherwise.
       Does not actually perform conversion.

       Returns:
           Boolean indicating convertibility
       """
       if context_data is None:
           return False

       # Handle collections
       if isinstance(context_data, list):
           if len(context_data) == 0:
               return False
           if len(context_data) == 1:
               return self.fn_converts_to_decimal(context_data[0], args, context)
           # Multiple items - not convertible
           return False

       # Boolean not convertible
       if isinstance(context_data, bool):
           return False

       # Numeric types always convertible
       if isinstance(context_data, (int, float, Decimal)):
           return True

       # String - test parse without converting
       if isinstance(context_data, str):
           result = self._try_parse_decimal(context_data.strip())
           return not isinstance(result, list)  # True if Decimal, False if []

       # Other types not convertible
       return False
   ```

2. Register function in `_register_functions`:
   ```python
   self._functions['convertsToDecimal'] = self.fn_converts_to_decimal
   ```

3. Test with examples:
   - `'123.45'.convertsToDecimal()` → `true`
   - `'invalid'.convertsToDecimal()` → `false`
   - `42.convertsToDecimal()` → `true`
   - `true.convertsToDecimal()` → `false`

**Validation**:
- convertsToDecimal() returns boolean
- Matches toDecimal() behavior (if toDecimal succeeds, convertsToDecimal is true)
- No exceptions thrown

**Expected Output**: Working convertsToDecimal() implementation

---

#### Step 4: Implement toQuantity() Function (2 hours)

**Objective**: Parse FHIR Quantity format from strings and create Quantity objects.

**Key Activities**:
1. Understand FHIR Quantity format:
   - Format: `value 'unit'` (e.g., `5.5 'mg'`)
   - Value: decimal or integer
   - Unit: UCUM unit code in single quotes
   - Unitless: just number (e.g., `42`)
   - Spaces: flexible whitespace between value and unit

2. Create Quantity representation (start simple with dict):
   ```python
   # Type hint for Quantity
   QuantityType = Dict[str, Union[Decimal, str]]
   ```

3. Implement `fn_to_quantity` method:
   ```python
   @fhirpath_function('toQuantity', min_args=0, max_args=0)
   def fn_to_quantity(self, context_data: Any, args: List[Any], context: 'EvaluationContext') -> Union[QuantityType, List]:
       """
       Convert string to FHIR Quantity

       Parses FHIR Quantity format: value 'unit'
       Examples:
       - "5.5 'mg'" → {value: 5.5, unit: 'mg'}
       - "100 'kg'" → {value: 100, unit: 'kg'}
       - "42" → {value: 42, unit: ''}
       - "invalid" → []

       Returns:
           Quantity dict or empty list for invalid format
       """
       if context_data is None:
           return []

       # Handle collections
       if isinstance(context_data, list):
           if len(context_data) == 0:
               return []
           if len(context_data) == 1:
               return self.fn_to_quantity(context_data[0], args, context)
           return []

       # Only strings can be parsed to Quantity
       if not isinstance(context_data, str):
           return []

       return self._parse_quantity(context_data.strip())
   ```

4. Implement `_parse_quantity` helper:
   ```python
   def _parse_quantity(self, quantity_str: str) -> Union[Dict[str, Any], List]:
       """
       Parse FHIR Quantity format string

       Format: value 'unit' or value
       Examples: "5.5 'mg'", "100 'kg'", "42"

       Args:
           quantity_str: String to parse

       Returns:
           Quantity dict {value, unit} or empty list if invalid
       """
       if not quantity_str:
           return []

       # Regex pattern for FHIR Quantity format
       # Matches: optional_whitespace number whitespace 'unit' optional_whitespace
       # Also matches: just a number (unitless)
       import re

       # Pattern 1: value with unit (e.g., "5.5 'mg'")
       pattern_with_unit = r"^\s*([+-]?(?:\d+\.?\d*|\d*\.\d+))\s+'([^']+)'\s*$"

       # Pattern 2: just value (unitless, e.g., "42")
       pattern_unitless = r"^\s*([+-]?(?:\d+\.?\d*|\d*\.\d+))\s*$"

       # Try with unit first
       match = re.match(pattern_with_unit, quantity_str)
       if match:
           value_str = match.group(1)
           unit_str = match.group(2)

           # Parse value as decimal
           try:
               value = Decimal(value_str)
               return {'value': value, 'unit': unit_str}
           except (ValueError, InvalidOperation):
               return []

       # Try unitless
       match = re.match(pattern_unitless, quantity_str)
       if match:
           value_str = match.group(1)
           try:
               value = Decimal(value_str)
               return {'value': value, 'unit': ''}
           except (ValueError, InvalidOperation):
               return []

       # No match - invalid format
       return []
   ```

5. Test with examples:
   - `"5.5 'mg'".toQuantity()` → `{value: 5.5, unit: 'mg'}`
   - `"100 'kg'".toQuantity()` → `{value: 100, unit: 'kg'}`
   - `"42".toQuantity()` → `{value: 42, unit: ''}`
   - `"invalid".toQuantity()` → `[]`
   - `"5.5 mg".toQuantity()` → `[]` (missing quotes)

**Validation**:
- Quantity parsing handles standard FHIR format
- Unitless quantities supported
- Invalid formats return empty collection
- Value precision preserved

**Expected Output**: Working toQuantity() implementation

---

#### Step 5: Implement convertsToQuantity() Function (45 minutes)

**Objective**: Validate Quantity format without performing full conversion.

**Key Activities**:
1. Implement `fn_converts_to_quantity` method:
   ```python
   @fhirpath_function('convertsToQuantity', min_args=0, max_args=0)
   def fn_converts_to_quantity(self, context_data: Any, args: List[Any], context: 'EvaluationContext') -> bool:
       """
       Test if value can be converted to Quantity

       Returns true if toQuantity() would succeed, false otherwise.

       Returns:
           Boolean indicating Quantity convertibility
       """
       if context_data is None:
           return False

       # Handle collections
       if isinstance(context_data, list):
           if len(context_data) == 0:
               return False
           if len(context_data) == 1:
               return self.fn_converts_to_quantity(context_data[0], args, context)
           return False

       # Only strings can convert to Quantity
       if not isinstance(context_data, str):
           return False

       # Test parse
       result = self._parse_quantity(context_data.strip())
       return not isinstance(result, list)  # True if dict, False if []
   ```

2. Register function in `_register_functions`:
   ```python
   self._functions['convertsToQuantity'] = self.fn_converts_to_quantity
   ```

3. Test with examples:
   - `"5.5 'mg'".convertsToQuantity()` → `true`
   - `"invalid".convertsToQuantity()` → `false`
   - `42.convertsToQuantity()` → `false` (not a string)

**Validation**:
- convertsToQuantity() returns boolean
- Matches toQuantity() behavior
- No exceptions thrown

**Expected Output**: Working convertsToQuantity() implementation

---

#### Step 6: Register All Functions (15 minutes)

**Objective**: Ensure all new functions are registered in function library.

**Key Activities**:
1. Update `_register_functions` method in `FunctionLibrary` class:
   ```python
   def _register_functions(self) -> None:
       """Register all function implementations"""
       # ... existing registrations ...

       # Type conversion functions (string/math section)
       self._functions['toString'] = self.fn_to_string
       self._functions['toInteger'] = self.fn_to_integer
       self._functions['toDecimal'] = self.fn_to_decimal  # Enhanced
       self._functions['convertsToDecimal'] = self.fn_converts_to_decimal  # NEW
       self._functions['toQuantity'] = self.fn_to_quantity  # NEW
       self._functions['convertsToQuantity'] = self.fn_converts_to_quantity  # NEW

       # ... rest of registrations ...
   ```

2. Verify all four functions are in registry

3. Test function lookup:
   ```python
   # In interactive Python or test
   library = FunctionLibrary(type_system)
   print('toDecimal' in library._functions)  # Should be True
   print('convertsToDecimal' in library._functions)  # Should be True
   print('toQuantity' in library._functions)  # Should be True
   print('convertsToQuantity' in library._functions)  # Should be True
   ```

**Validation**:
- All functions registered
- Function names correct (case-sensitive)
- No registration conflicts

**Expected Output**: All functions accessible via function library

---

#### Step 7: Write Comprehensive Unit Tests (2 hours)

**Objective**: Create unit tests covering all scenarios for each function.

**Key Activities**:
1. Create test file: `tests/unit/fhirpath/evaluator/test_type_conversion_functions.py`

2. Structure test file:
   ```python
   """
   Unit tests for FHIRPath type conversion functions

   Tests toDecimal(), convertsToDecimal(), toQuantity(), convertsToQuantity()
   """

   import pytest
   from decimal import Decimal
   from fhir4ds.fhirpath.evaluator.functions import FunctionLibrary
   from fhir4ds.fhirpath.types.fhir_types import FHIRTypeSystem
   from fhir4ds.fhirpath.evaluator.context import EvaluationContext


   class TestToDecimalFunction:
       """Test toDecimal() function"""

       def setup_method(self):
           self.type_system = FHIRTypeSystem()
           self.library = FunctionLibrary(self.type_system)
           self.context = EvaluationContext()

       def test_integer_to_decimal(self):
           """Integer converts to decimal"""
           result = self.library.fn_to_decimal(42, [], self.context)
           assert result == Decimal('42')

       def test_string_valid_to_decimal(self):
           """Valid string converts to decimal"""
           result = self.library.fn_to_decimal('123.45', [], self.context)
           assert result == Decimal('123.45')

       def test_string_invalid_to_decimal(self):
           """Invalid string returns empty collection"""
           result = self.library.fn_to_decimal('not-a-number', [], self.context)
           assert result == []

       def test_boolean_to_decimal(self):
           """Boolean returns empty collection"""
           result = self.library.fn_to_decimal(True, [], self.context)
           assert result == []
           result = self.library.fn_to_decimal(False, [], self.context)
           assert result == []

       def test_null_to_decimal(self):
           """Null returns empty collection"""
           result = self.library.fn_to_decimal(None, [], self.context)
           assert result == []

       def test_empty_collection_to_decimal(self):
           """Empty collection returns empty collection"""
           result = self.library.fn_to_decimal([], [], self.context)
           assert result == []

       def test_single_element_collection_to_decimal(self):
           """Single-element collection unwraps"""
           result = self.library.fn_to_decimal(['123.45'], [], self.context)
           assert result == Decimal('123.45')

       def test_multi_element_collection_to_decimal(self):
           """Multi-element collection returns empty"""
           result = self.library.fn_to_decimal([1, 2], [], self.context)
           assert result == []

       def test_decimal_precision_preserved(self):
           """Decimal precision is preserved"""
           result = self.library.fn_to_decimal('123.456789', [], self.context)
           assert result == Decimal('123.456789')

       def test_negative_decimal(self):
           """Negative decimals handled"""
           result = self.library.fn_to_decimal('-42.5', [], self.context)
           assert result == Decimal('-42.5')

       def test_scientific_notation(self):
           """Scientific notation handled"""
           result = self.library.fn_to_decimal('1.23e5', [], self.context)
           assert result == Decimal('123000')


   class TestConvertsToDecimalFunction:
       """Test convertsToDecimal() function"""

       def setup_method(self):
           self.type_system = FHIRTypeSystem()
           self.library = FunctionLibrary(self.type_system)
           self.context = EvaluationContext()

       def test_integer_converts_to_decimal(self):
           """Integer is convertible"""
           result = self.library.fn_converts_to_decimal(42, [], self.context)
           assert result is True

       def test_string_valid_converts_to_decimal(self):
           """Valid string is convertible"""
           result = self.library.fn_converts_to_decimal('123.45', [], self.context)
           assert result is True

       def test_string_invalid_not_converts_to_decimal(self):
           """Invalid string is not convertible"""
           result = self.library.fn_converts_to_decimal('not-a-number', [], self.context)
           assert result is False

       def test_boolean_not_converts_to_decimal(self):
           """Boolean is not convertible"""
           result = self.library.fn_converts_to_decimal(True, [], self.context)
           assert result is False

       def test_null_not_converts_to_decimal(self):
           """Null is not convertible"""
           result = self.library.fn_converts_to_decimal(None, [], self.context)
           assert result is False

       def test_consistency_with_to_decimal(self):
           """convertsToDecimal matches toDecimal behavior"""
           test_values = [42, '123.45', 'invalid', True, None, []]
           for value in test_values:
               can_convert = self.library.fn_converts_to_decimal(value, [], self.context)
               actual_result = self.library.fn_to_decimal(value, [], self.context)

               if can_convert:
                   # If convertsToDecimal is True, toDecimal should return Decimal
                   assert isinstance(actual_result, Decimal)
               else:
                   # If convertsToDecimal is False, toDecimal should return []
                   assert actual_result == []


   class TestToQuantityFunction:
       """Test toQuantity() function"""

       def setup_method(self):
           self.type_system = FHIRTypeSystem()
           self.library = FunctionLibrary(self.type_system)
           self.context = EvaluationContext()

       def test_quantity_with_unit(self):
           """Quantity with unit parsed correctly"""
           result = self.library.fn_to_quantity("5.5 'mg'", [], self.context)
           assert result == {'value': Decimal('5.5'), 'unit': 'mg'}

       def test_quantity_integer_value(self):
           """Quantity with integer value"""
           result = self.library.fn_to_quantity("100 'kg'", [], self.context)
           assert result == {'value': Decimal('100'), 'unit': 'kg'}

       def test_quantity_unitless(self):
           """Unitless quantity (just number)"""
           result = self.library.fn_to_quantity("42", [], self.context)
           assert result == {'value': Decimal('42'), 'unit': ''}

       def test_quantity_invalid_format(self):
           """Invalid quantity format returns empty"""
           result = self.library.fn_to_quantity("not-a-quantity", [], self.context)
           assert result == []

       def test_quantity_missing_quotes(self):
           """Unit without quotes is invalid"""
           result = self.library.fn_to_quantity("5.5 mg", [], self.context)
           assert result == []

       def test_quantity_negative_value(self):
           """Negative quantity values"""
           result = self.library.fn_to_quantity("-10.5 'mL'", [], self.context)
           assert result == {'value': Decimal('-10.5'), 'unit': 'mL'}

       def test_quantity_complex_unit(self):
           """Complex UCUM units"""
           result = self.library.fn_to_quantity("98.6 'degF'", [], self.context)
           assert result == {'value': Decimal('98.6'), 'unit': 'degF'}

       def test_quantity_whitespace_handling(self):
           """Extra whitespace handled"""
           result = self.library.fn_to_quantity("  5.5  'mg'  ", [], self.context)
           assert result == {'value': Decimal('5.5'), 'unit': 'mg'}

       def test_quantity_non_string_input(self):
           """Non-string inputs return empty"""
           result = self.library.fn_to_quantity(42, [], self.context)
           assert result == []

       def test_quantity_null_input(self):
           """Null input returns empty"""
           result = self.library.fn_to_quantity(None, [], self.context)
           assert result == []


   class TestConvertsToQuantityFunction:
       """Test convertsToQuantity() function"""

       def setup_method(self):
           self.type_system = FHIRTypeSystem()
           self.library = FunctionLibrary(self.type_system)
           self.context = EvaluationContext()

       def test_valid_quantity_converts(self):
           """Valid quantity string is convertible"""
           result = self.library.fn_converts_to_quantity("5.5 'mg'", [], self.context)
           assert result is True

       def test_invalid_quantity_not_converts(self):
           """Invalid quantity string is not convertible"""
           result = self.library.fn_converts_to_quantity("invalid", [], self.context)
           assert result is False

       def test_non_string_not_converts(self):
           """Non-string is not convertible"""
           result = self.library.fn_converts_to_quantity(42, [], self.context)
           assert result is False

       def test_consistency_with_to_quantity(self):
           """convertsToQuantity matches toQuantity behavior"""
           test_values = ["5.5 'mg'", "42", "invalid", 42, None]
           for value in test_values:
               can_convert = self.library.fn_converts_to_quantity(value, [], self.context)
               actual_result = self.library.fn_to_quantity(value, [], self.context)

               if can_convert:
                   # If convertsToQuantity is True, toQuantity should return dict
                   assert isinstance(actual_result, dict)
                   assert 'value' in actual_result
                   assert 'unit' in actual_result
               else:
                   # If convertsToQuantity is False, toQuantity should return []
                   assert actual_result == []
   ```

3. Run unit tests:
   ```bash
   PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/evaluator/test_type_conversion_functions.py -v
   ```

**Validation**:
- All unit tests pass
- Coverage >90% for new functions
- Edge cases handled correctly

**Expected Output**: Comprehensive unit test suite passing

---

#### Step 8: Validate Against Official Test Suite (1 hour)

**Objective**: Run official FHIRPath R4 test suite and measure improvement.

**Key Activities**:
1. Run official test suite:
   ```bash
   PYTHONPATH=. python3 tests/compliance/fhirpath/test_runner.py
   ```

2. Measure compliance improvement:
   - Baseline (after SP-014-004): 46% (~430/934 tests)
   - Target: 49-50% (~460/934 tests, +30 tests)
   - Stretch: 50%+ if all type conversion tests pass

3. Analyze type conversion test results:
   - Filter for toDecimal tests: should pass ~17 tests
   - Filter for convertsToDecimal tests: should pass ~14 tests
   - Filter for toQuantity/convertsToQuantity: may have fewer direct tests

4. Identify remaining failures:
   - Document specific failing test cases
   - Categorize by issue type (parsing, precision, edge cases)

5. Verify no regressions:
   - Compare pass counts for all other categories
   - Ensure no previously passing tests now fail

**Validation**:
- Compliance improves to at least 48% (conservative target)
- At least 28 of 31 type conversion tests passing (90% target)
- No regressions in other categories

**Expected Output**: Official test suite validation report

---

#### Step 9: Fix Remaining Edge Cases (1 hour, as needed)

**Objective**: Address any remaining type conversion failures from official test suite.

**Potential Edge Cases**:
1. **Decimal precision edge cases**: Very large or very small decimals
2. **Quantity unit variations**: Different UCUM unit formats
3. **Whitespace variations**: Unusual spacing in Quantity strings
4. **Empty string handling**: Empty strings should return empty collections
5. **Collection handling**: Nested collections or complex collection scenarios

**Approach for Each Edge Case**:
1. Analyze failing test to understand expected behavior
2. Consult FHIRPath specification for correct semantics
3. Implement fix for specific edge case
4. Add unit test for edge case
5. Re-run official test suite to verify

**Example Edge Case Fix**:
```python
# Edge case: Empty string to decimal
def test_empty_string_to_decimal():
    """Empty string returns empty collection"""
    result = self.library.fn_to_decimal('', [], self.context)
    assert result == []

# Fix in _try_parse_decimal:
def _try_parse_decimal(self, value_str: str) -> Union[Decimal, List]:
    if not value_str or not value_str.strip():  # Added strip() check
        return []
    # ... rest of implementation
```

**Validation**:
- Edge cases resolved
- Test count increases toward +31 target
- No new failures introduced

**Expected Output**: Edge cases handled, test pass rate maximized

---

### Alternative Approaches Considered

**Alternative 1: Implement Type Conversion in SQL Generation Layer**
- **Approach**: Generate SQL CAST operations for type conversions
- **Rejected Because**:
  - More complex to handle all edge cases in SQL
  - Different SQL syntax between DuckDB and PostgreSQL
  - Quantity parsing requires regex, difficult in SQL
  - Python evaluation is simpler and more maintainable

**Alternative 2: Create Full Quantity Class Hierarchy**
- **Approach**: Implement FHIR Quantity as full Python class with unit validation
- **Rejected Because**:
  - Over-engineering for current requirements
  - Simple dict representation sufficient for FHIRPath evaluation
  - Can refactor to class later if needed
  - Would increase implementation time significantly

**Alternative 3: Use External Decimal/Quantity Libraries**
- **Approach**: Use libraries like `pint` for quantity handling
- **Rejected Because**:
  - Adds external dependency
  - May not match FHIR/UCUM semantics exactly
  - Python's decimal module sufficient for precision
  - Regex parsing simple enough for FHIR format

**Alternative 4: Defer Quantity Functions to Later Sprint**
- **Approach**: Only implement toDecimal/convertsToDecimal now
- **Rejected Because**:
  - Quantity functions are simple extensions
  - Implementing all four functions together is more efficient
  - Provides complete type conversion support
  - Only adds ~2 hours to implementation time

---

## Testing Strategy

### Unit Testing

**New Tests Required**:
- `tests/unit/fhirpath/evaluator/test_type_conversion_functions.py`:
  - `TestToDecimalFunction` (12+ test methods)
    - Integer, string, boolean, null, collection inputs
    - Valid and invalid string formats
    - Precision preservation
    - Scientific notation
  - `TestConvertsToDecimalFunction` (6+ test methods)
    - All input type variations
    - Consistency with toDecimal()
  - `TestToQuantityFunction` (10+ test methods)
    - Quantity with unit
    - Unitless quantity
    - Invalid formats
    - Whitespace handling
    - Complex UCUM units
  - `TestConvertsToQuantityFunction` (4+ test methods)
    - Valid/invalid formats
    - Consistency with toQuantity()

**Modified Tests**: None expected (new functions shouldn't affect existing tests)

**Coverage Target**: >90% coverage of new function code paths

### Integration Testing

**Database Testing**:
1. **DuckDB**: Run full test suite with DuckDB backend
   ```bash
   PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k "type_conversion"
   ```

2. **PostgreSQL**: Run full test suite with PostgreSQL backend
   ```bash
   DATABASE_TYPE=postgresql PYTHONPATH=. python3 -m pytest tests/integration/fhirpath/ -k "type_conversion"
   ```

3. **Consistency Check**: Verify identical results from both databases

**Component Integration**:
- Test type conversion with other FHIRPath features:
  - With `.where()`: `Patient.age.toDecimal().where($this > 18)`
  - With arithmetic: `Observation.valueString.toDecimal() * 2.5`
  - With `.select()`: `Medication.doseQuantity.select($this.toQuantity())`
  - In comparisons: `'42'.toDecimal() = 42`

**End-to-End Testing**:
- Test complete FHIRPath expressions using type conversion
- Verify type conversion works in real FHIR resource queries

### Compliance Testing

**Official Test Suites**:
- Run FHIRPath R4 official test suite (all 934 tests)
- Focus on type conversion tests (31 tests total)
  - toDecimal: ~17 tests
  - convertsToDecimal: ~14 tests
  - toQuantity/convertsToQuantity: variable
- Target: At least 28 passing (90% of 31)
- Stretch: All 31 passing (100%)

**Regression Testing**:
- Run full test suite before and after implementation
- Compare pass counts for each category
- Ensure no regressions (pass count doesn't decrease anywhere)

**Performance Validation**:
- Benchmark type conversion performance:
  - toDecimal() should be <1ms for typical inputs
  - Quantity parsing should be <5ms (regex overhead)
- Compare performance between DuckDB and PostgreSQL

### Manual Testing

**Test Scenarios**:
1. **Basic Decimal Conversion**: `'123.45'.toDecimal()` → `123.45`
2. **Invalid Decimal**: `'not-a-number'.toDecimal()` → `{}`
3. **Decimal Validation**: `'123.45'.convertsToDecimal()` → `true`
4. **Quantity Parsing**: `"5.5 'mg'".toQuantity()` → `{value: 5.5, unit: 'mg'}`
5. **Unitless Quantity**: `"42".toQuantity()` → `{value: 42, unit: ''}`
6. **Quantity Validation**: `"5.5 'mg'".convertsToQuantity()` → `true`

**Edge Cases**:
1. **Precision**: Very large decimals (e.g., `'123456789.987654321'`)
2. **Scientific notation**: `'1.23e10'.toDecimal()`
3. **Negative quantities**: `"-10.5 'mL'".toQuantity()`
4. **Empty strings**: `''.toDecimal()` → `{}`
5. **Whitespace**: `"  5.5  'mg'  ".toQuantity()`

**Error Conditions**:
1. **Collection inputs**: How do functions handle collections?
2. **Type mismatches**: Non-string to Quantity
3. **Invalid formats**: Various malformed inputs

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Decimal precision issues | Medium | High | Use Python Decimal module, validate precision in tests |
| Quantity format ambiguity | Medium | Medium | Study FHIR spec carefully, test edge cases thoroughly |
| FHIRPath spec interpretation | Low | High | Consult official spec, check reference implementations |
| Integration with existing code | Low | Medium | Follow existing function patterns, thorough testing |
| Performance of regex parsing | Low | Low | Benchmark early, optimize if needed |

### Implementation Challenges

1. **Understanding FHIRPath Semantics**: Type conversion rules may be subtle
   - **Approach**: Study specification carefully, examine reference implementations
   - **Time Buffer**: Add 30 minutes for spec research

2. **Quantity Format Variations**: UCUM units have many formats
   - **Approach**: Start with basic format, expand if official tests reveal edge cases
   - **Testing**: Comprehensive regex testing with official test cases

3. **Decimal Precision**: Maintaining arbitrary precision
   - **Approach**: Use Python's `decimal.Decimal` throughout
   - **Validation**: Specific tests for precision edge cases

### Contingency Plans

- **If 31 tests seems unachievable**: Target 28 tests (90%), document remaining issues for future sprint
- **If Quantity parsing proves complex**: Implement basic toDecimal/convertsToDecimal first (21 tests), defer Quantity functions
- **If precision issues arise**: Consult with senior architect on FHIRPath precision requirements
- **If timeline extends beyond 8 hours**: Prioritize toDecimal/convertsToDecimal (higher test impact), defer Quantity functions to future task

---

## Estimation

### Time Breakdown

- **Step 1: Analyze Existing toDecimal**: 30 minutes
- **Step 2: Implement/Enhance toDecimal**: 1.5 hours
- **Step 3: Implement convertsToDecimal**: 1 hour
- **Step 4: Implement toQuantity**: 2 hours
- **Step 5: Implement convertsToQuantity**: 45 minutes
- **Step 6: Register Functions**: 15 minutes
- **Step 7: Unit Tests**: 2 hours
- **Step 8: Official Test Validation**: 1 hour
- **Step 9: Edge Cases**: 1 hour (as needed)
- **Total Estimate**: 10 hours

**Buffer**: Add 1 hour for unexpected issues = 11 hours total
**Adjusted for Junior Developer**: 11-12 hours (includes learning and debugging)

### Confidence Level

- [ ] High (90%+ confident in estimate)
- [x] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Type conversion implementation is well-defined with existing examples (toInteger, toString). Quantity parsing adds complexity but regex approach is straightforward. Conservative estimate accounts for specification research and edge case handling.

### Factors Affecting Estimate

- **Specification Complexity**: If FHIRPath semantics are unclear, could add 1-2 hours for research
- **Quantity Format Variations**: If UCUM units require more complex parsing, could add 1-2 hours
- **Edge Cases**: If many edge cases found in testing, could add 1-2 hours
- **Decimal Precision**: If precision issues arise, could add 1 hour for debugging
- **Junior Experience**: First time implementing type conversion functions may be slower

---

## Success Metrics

### Quantitative Measures

- **Test Pass Count**: At least +28 tests passing (target +31)
- **Compliance Improvement**: 46% → 49-50%
- **Function Coverage**:
  - toDecimal: ~17 tests passing
  - convertsToDecimal: ~14 tests passing
  - toQuantity/convertsToQuantity: all related tests passing
- **Code Coverage**: >90% coverage of new type conversion functions
- **Performance**: All conversion functions execute in <5ms for typical inputs

### Qualitative Measures

- **Code Quality**: Type conversion code is clean, well-documented, follows project patterns
- **Architecture Alignment**: Implementation aligns with existing function library architecture
- **Maintainability**: Future developers can understand and extend type conversion functions easily
- **Specification Compliance**: Implementation matches FHIRPath specification semantics exactly

### Compliance Impact

- **Specification Compliance**: Significant step toward 100% FHIRPath compliance
- **Test Suite Results**:
  - Baseline (after SP-014-004): ~430/934 passing (46%)
  - Conservative Target: 456/934 passing (48.8%, +26 tests)
  - Realistic Target: 461/934 passing (49.4%, +31 tests)
  - Optimistic Target: 465/934 passing (49.8%, +35 tests including indirect improvements)
- **Performance Impact**: Negligible (simple type conversions)

---

## Documentation Requirements

### Code Documentation

- [x] Inline comments for type conversion logic
- [x] Function/method documentation with FHIRPath spec references
- [x] Docstrings for all new methods (toDecimal, convertsToDecimal, toQuantity, convertsToQuantity)
- [x] Example usage in docstrings
- [x] Quantity format documentation

### Architecture Documentation

- [ ] Update FHIRPath function support matrix (document type conversion functions supported)
- [ ] Document Quantity representation (dict format, future class migration path)
- [ ] Add type conversion to FHIRPath function library guide (if exists)

### User Documentation

- [ ] Update FHIRPath expression guide with type conversion examples
- [ ] Add type conversion functions to FHIRPath function reference
- [ ] Include common type conversion patterns in troubleshooting guide

---

## Progress Tracking

### Status

- [x] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [ ] Completed
- [ ] Blocked

### Progress Updates

| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-10-28 | Not Started | Task created and documented | None | Begin implementation in Week 2 Day 8-9 |

### Completion Checklist

- [ ] Existing toDecimal() analyzed and enhanced
- [ ] convertsToDecimal() implemented and registered
- [ ] toQuantity() implemented with FHIR Quantity parsing
- [ ] convertsToQuantity() implemented with format validation
- [ ] All functions handle edge cases (null, empty, invalid inputs)
- [ ] Helper methods implemented (_try_parse_decimal, _parse_quantity)
- [ ] All functions registered in function library
- [ ] Unit tests written and passing (>90% coverage)
- [ ] Official test suite validation complete (+28 tests minimum)
- [ ] No regressions in other test categories
- [ ] Code reviewed and approved
- [ ] Documentation completed

---

## Review and Sign-off

### Self-Review Checklist

- [ ] Implementation matches FHIRPath specification exactly
- [ ] All tests pass in DuckDB environment
- [ ] PostgreSQL compatibility verified (if needed)
- [ ] Code follows established patterns (function decorator, error handling)
- [ ] toDecimal preserves precision using Decimal module
- [ ] convertsToDecimal matches toDecimal behavior
- [ ] Quantity parsing handles FHIR format correctly
- [ ] Invalid inputs return empty collections (not exceptions)
- [ ] Performance is acceptable (<5ms typical cases)
- [ ] Documentation is complete and accurate
- [ ] No regressions introduced

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [To be completed]
**Review Status**: Pending
**Review Comments**: [To be added by reviewer]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [To be completed]
**Status**: Pending
**Comments**: [Final approval decision]

---

## Post-Completion Analysis

### Actual vs. Estimated

- **Time Estimate**: 11-12 hours
- **Actual Time**: [To be recorded after completion]
- **Variance**: [To be calculated and analyzed]

### Lessons Learned

1. **[Lesson 1]**: [To be documented after completion]
2. **[Lesson 2]**: [To be documented after completion]

### Future Improvements

- **Process**: [To be documented after completion]
- **Technical**: [To be documented after completion]
- **Estimation**: [To be documented after completion]

---

**Task Created**: 2025-10-28 by Senior Solution Architect (comprehensive task planning)
**Last Updated**: 2025-10-28
**Status**: Not Started - Ready for Week 2 Implementation (Days 8-9)

---

*This task implements high-impact type conversion functions identified in SP-014-002 root cause analysis. Successful completion will improve compliance by approximately 3-4 percentage points and provide essential numeric type handling for FHIRPath expressions.*
