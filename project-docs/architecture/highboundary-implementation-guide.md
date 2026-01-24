# highBoundary() and lowBoundary() Implementation Guide

**Document Version**: 1.0
**Date**: 2025-10-17
**Task**: SP-009-016, SP-009-017
**Author**: Senior Solution Architect/Engineer

---

## Overview

This guide provides complete implementation guidance for `highBoundary()` and `lowBoundary()` functions, including solutions to the two blockers identified by the junior developer.

## Blockers Solved

### Blocker #1: Path-to-Type Resolution ✅ SOLVED

**Problem**: Translator doesn't know if `Patient.birthDate.highBoundary()` is a Date, DateTime, Decimal, etc.

**Solution**: New `FHIRElementTypeResolver` utility provides path-to-type mapping.

**Location**: `fhir4ds/fhirpath/types/element_type_resolver.py`

### Blocker #2: Temporal Parsing with Timezones ✅ SOLVED

**Problem**: AST doesn't preserve timezone information in temporal literals like `@2014-01-01T08:05-05:00`.

**Solution**: New `FHIRTemporalParser` utility parses temporal literals with full precision and timezone preservation.

**Location**: `fhir4ds/fhirpath/types/temporal_parser.py`

---

## Implementation Pattern for Translator

### Step 1: Import Required Utilities

```python
# In fhir4ds/fhirpath/sql/translator.py

from ..types import (
    get_element_type_resolver,
    get_temporal_parser,
    ParsedTemporal
)
```

### Step 2: Implement `_translate_high_boundary()` Method

```python
def _translate_high_boundary(self, node: FunctionCallNode) -> SQLFragment:
    """
    Translate highBoundary() function to SQL.

    Handles:
    - Literal values (decimals, dates, times)
    - Resource paths (Patient.birthDate, Observation.valueQuantity)
    - Precision parameter (optional)

    Examples:
        1.587.highBoundary() → decimal boundary
        Patient.birthDate.highBoundary() → date boundary
        @2014-01-01T08.highBoundary(17) → datetime boundary with precision 17
    """

    # Step 1: Get base expression from invocation context
    base_fragment = self.visit(node.invocation_context)
    base_expr = base_fragment.expression

    # Step 2: Extract precision parameter if provided
    precision_param = None
    if node.arguments and len(node.arguments) > 0:
        precision_arg = node.arguments[0]
        # Extract integer literal from precision argument
        if hasattr(precision_arg, 'value') and isinstance(precision_arg.value, int):
            precision_param = precision_arg.value

    # Step 3: Determine input type
    input_type = self._determine_boundary_input_type(node.invocation_context)

    # Step 4: Route to appropriate boundary calculation
    if input_type in ['integer', 'decimal', 'Quantity', 'Age', 'Duration']:
        return self._translate_decimal_boundary(
            base_expr, precision_param, boundary_type='high'
        )
    elif input_type in ['date', 'dateTime', 'time', 'instant']:
        return self._translate_temporal_boundary(
            base_expr, precision_param, input_type, boundary_type='high'
        )
    else:
        raise FHIRPathTranslationError(
            f"highBoundary() not supported for type {input_type}"
        )
```

### Step 3: Implement Type Determination Logic

```python
def _determine_boundary_input_type(self, context_node: FHIRPathASTNode) -> str:
    """
    Determine the FHIR type of the input to boundary function.

    Handles:
    - Literal nodes (detect from literal value)
    - Path nodes (resolve from resource + path)
    - Function call results (infer from function semantics)

    Args:
        context_node: AST node representing the input expression

    Returns:
        FHIR type name (e.g., 'date', 'dateTime', 'decimal', 'Quantity')
    """
    from ..ast.nodes import LiteralNode, IdentifierNode, FunctionCallNode

    # Case 1: Literal value (e.g., 1.587, @2014, @T10:30)
    if isinstance(context_node, LiteralNode):
        return self._determine_literal_type(context_node)

    # Case 2: Resource path (e.g., Patient.birthDate, Observation.valueQuantity)
    elif isinstance(context_node, IdentifierNode):
        return self._resolve_path_type(context_node)

    # Case 3: Function call result (e.g., first(), single())
    elif isinstance(context_node, FunctionCallNode):
        # Recursively determine type of function's input
        return self._determine_boundary_input_type(context_node.invocation_context)

    else:
        # Default: assume decimal
        logger.warning(f"Could not determine type for {context_node}, defaulting to decimal")
        return 'decimal'

def _determine_literal_type(self, literal_node: LiteralNode) -> str:
    """
    Determine FHIR type from a literal node.

    Examples:
        1.587 → 'decimal'
        1 → 'integer'
        @2014 → 'date'
        @2014-01-01T08 → 'dateTime'
        @T10:30 → 'time'
    """
    value = literal_node.value

    # Check if it's a temporal literal (starts with @)
    if isinstance(value, str) and value.startswith('@'):
        # Use temporal parser to detect type
        temporal_parser = get_temporal_parser()
        detected_type = temporal_parser.detect_type(value)
        if detected_type:
            return detected_type.lower()  # 'Date' → 'date'

    # Check for numeric literals
    if isinstance(value, int):
        return 'integer'
    elif isinstance(value, (float, Decimal)):
        return 'decimal'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, str):
        return 'string'

    # Default
    return 'string'

def _resolve_path_type(self, identifier_node: IdentifierNode) -> str:
    """
    Resolve FHIR type from resource path.

    Uses FHIRElementTypeResolver to map paths like "Patient.birthDate" to "date".

    Examples:
        Patient.birthDate → 'date'
        Observation.valueQuantity → 'Quantity'
        Observation.effectiveDateTime → 'dateTime'
    """
    # Get element type resolver
    resolver = get_element_type_resolver()

    # Build full path from context
    # The context maintains the current resource type and path components
    resource_type = self.context.current_resource_type

    # Get the full element path from identifier
    element_path = identifier_node.identifier

    # Resolve type
    resolved_type = resolver.resolve_element_type(resource_type, element_path)

    if resolved_type:
        logger.debug(f"Resolved {resource_type}.{element_path} → {resolved_type}")
        return resolved_type.lower()  # Normalize to lowercase
    else:
        logger.warning(
            f"Could not resolve type for {resource_type}.{element_path}, "
            f"defaulting to 'string'"
        )
        return 'string'
```

### Step 4: Implement Decimal Boundary Translation

```python
def _translate_decimal_boundary(
    self,
    base_expr: str,
    precision_param: Optional[int],
    boundary_type: str  # 'high' or 'low'
) -> SQLFragment:
    """
    Translate decimal/quantity boundary to SQL.

    Implements uncertainty interval algorithm:
    1. Detect input precision (count decimal places)
    2. Calculate uncertainty (0.5 × 10^-input_precision)
    3. Add (high) or subtract (low) uncertainty
    4. Round to target precision

    Args:
        base_expr: SQL expression for input value
        precision_param: Target precision (None = input precision + 5)
        boundary_type: 'high' or 'low'

    Returns:
        SQLFragment with boundary calculation SQL
    """

    # Call dialect method with all parameters
    sql_expr = self.dialect.generate_decimal_boundary(
        base_expr=base_expr,
        target_precision=precision_param,
        boundary_type=boundary_type
    )

    return SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table,
        is_scalar=True,
        requires_unnest=False
    )
```

### Step 5: Implement Temporal Boundary Translation

```python
def _translate_temporal_boundary(
    self,
    base_expr: str,
    precision_param: Optional[int],
    input_type: str,  # 'date', 'dateTime', 'time', 'instant'
    boundary_type: str  # 'high' or 'low'
) -> SQLFragment:
    """
    Translate temporal boundary to SQL.

    Handles date, dateTime, time, and instant types with precision.

    Args:
        base_expr: SQL expression for input value
        precision_param: Target precision (4=year, 6=month, 8=day, 17=millisecond+tz)
        input_type: Temporal type
        boundary_type: 'high' or 'low'

    Returns:
        SQLFragment with boundary calculation SQL
    """

    # For literal temporals, parse to get timezone info
    has_timezone = False
    if base_expr.startswith("'@"):
        # It's a literal temporal value
        literal_value = base_expr.strip("'")
        temporal_parser = get_temporal_parser()
        parsed = temporal_parser.parse(literal_value)
        if parsed and parsed.timezone_offset:
            has_timezone = True

    # Call dialect method
    sql_expr = self.dialect.generate_temporal_boundary(
        base_expr=base_expr,
        input_type=input_type,
        precision=precision_param,
        boundary_type=boundary_type,
        has_timezone=has_timezone
    )

    return SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table,
        is_scalar=True,
        requires_unnest=False
    )
```

---

## Usage Examples with New Utilities

### Example 1: Using Element Type Resolver

```python
from fhir4ds.fhirpath.types import get_element_type_resolver

resolver = get_element_type_resolver()

# Resolve Patient.birthDate
type1 = resolver.resolve_element_type("Patient", "birthDate")
print(type1)  # Output: 'date'

# Resolve Observation.valueQuantity
type2 = resolver.resolve_element_type("Observation", "valueQuantity")
print(type2)  # Output: 'Quantity'

# Resolve Observation.effectiveDateTime
type3 = resolver.resolve_element_type("Observation", "effectiveDateTime")
print(type3)  # Output: 'dateTime'

# Get all date/time elements for a resource
date_elements = resolver.get_all_date_time_elements("Patient")
print(date_elements)  # Output: {'birthDate', 'deceasedDateTime'}
```

### Example 2: Using Temporal Parser

```python
from fhir4ds.fhirpath.types import get_temporal_parser

parser = get_temporal_parser()

# Parse date
parsed1 = parser.parse("@2014")
print(parsed1.temporal_type)  # 'Date'
print(parsed1.year)  # 2014
print(parsed1.month)  # None
print(parsed1.get_precision_value())  # 4 (year precision)

# Parse datetime with timezone
parsed2 = parser.parse("@2014-01-01T08:05-05:00")
print(parsed2.temporal_type)  # 'DateTime'
print(parsed2.hour)  # 8
print(parsed2.minute)  # 5
print(parsed2.timezone_offset)  # '-05:00'
print(parsed2.get_precision_value())  # 17 (millisecond with timezone)

# Parse time
parsed3 = parser.parse("@T10:30:00.000")
print(parsed3.temporal_type)  # 'Time'
print(parsed3.millisecond)  # 0
print(parsed3.get_precision_value())  # 9 (time millisecond)

# Quick type detection (without full parsing)
type1 = parser.detect_type("@2014-01-01T08")
print(type1)  # 'DateTime'

type2 = parser.detect_type("@T10:30")
print(type2)  # 'Time'
```

### Example 3: Complete highBoundary() Translation Flow

```python
# Input: Patient.birthDate.highBoundary(6)

# Step 1: Visit function call node
node = FunctionCallNode(
    function_name='highBoundary',
    invocation_context=IdentifierNode(identifier='birthDate'),
    arguments=[LiteralNode(value=6)]
)

# Step 2: Translator calls _translate_high_boundary()
fragment = translator._translate_high_boundary(node)

# Step 3: Inside _translate_high_boundary():
#   - Determine input type:
#     - Node is IdentifierNode('birthDate')
#     - Resolver: Patient.birthDate → 'date'
#   - Route to temporal boundary:
#     - input_type='date', precision=6 (month), boundary_type='high'
#   - Call dialect.generate_temporal_boundary(...)
#   - Generate SQL for: "last month of year at month precision"

# Step 4: Result
# SQL: "@2014.highBoundary(6)" → "@2014-12"
```

---

## Dialect Implementation Guidance

### Abstract Method in Base Dialect

```python
# In fhir4ds/dialects/base.py

@abstractmethod
def generate_decimal_boundary(
    self,
    base_expr: str,
    target_precision: Optional[int],
    boundary_type: str
) -> str:
    """Generate SQL for decimal boundary calculation."""
    pass

@abstractmethod
def generate_temporal_boundary(
    self,
    base_expr: str,
    input_type: str,
    precision: Optional[int],
    boundary_type: str,
    has_timezone: bool
) -> str:
    """Generate SQL for temporal boundary calculation."""
    pass
```

### DuckDB Implementation Outline

```python
# In fhir4ds/dialects/duckdb.py

def generate_decimal_boundary(
    self,
    base_expr: str,
    target_precision: Optional[int],
    boundary_type: str
) -> str:
    """
    DuckDB-specific decimal boundary SQL.

    Uses:
    - POWER() for exponentiation
    - ROUND() for rounding
    - REGEXP_REPLACE() for precision detection
    """
    # Implementation follows algorithm from senior architect's guide
    # (See previous specification for complete algorithm)
    pass

def generate_temporal_boundary(
    self,
    base_expr: str,
    input_type: str,
    precision: Optional[int],
    boundary_type: str,
    has_timezone: bool
) -> str:
    """
    DuckDB-specific temporal boundary SQL.

    Uses:
    - DATE_TRUNC() for truncation
    - INTERVAL arithmetic for boundary calculation
    - Timezone handling functions
    """
    # Implementation for date/time boundaries
    pass
```

---

## Testing Strategy

### Unit Tests for Element Type Resolver

```python
# tests/unit/fhirpath/types/test_element_type_resolver.py

def test_resolve_patient_birth_date():
    resolver = get_element_type_resolver()
    result = resolver.resolve_element_type("Patient", "birthDate")
    assert result == 'date'

def test_resolve_observation_value_quantity():
    resolver = get_element_type_resolver()
    result = resolver.resolve_element_type("Observation", "valueQuantity")
    assert result == 'Quantity'

def test_resolve_unknown_returns_none():
    resolver = get_element_type_resolver()
    result = resolver.resolve_element_type("Patient", "unknownField")
    assert result is None
```

### Unit Tests for Temporal Parser

```python
# tests/unit/fhirpath/types/test_temporal_parser.py

def test_parse_date_year_precision():
    parser = get_temporal_parser()
    result = parser.parse("@2014")
    assert result.temporal_type == 'Date'
    assert result.year == 2014
    assert result.month is None
    assert result.get_precision_value() == 4

def test_parse_datetime_with_timezone():
    parser = get_temporal_parser()
    result = parser.parse("@2014-01-01T08:05-05:00")
    assert result.temporal_type == 'DateTime'
    assert result.timezone_offset == '-05:00'
    assert result.get_precision_value() == 17

def test_parse_time_millisecond():
    parser = get_temporal_parser()
    result = parser.parse("@T10:30:00.000")
    assert result.temporal_type == 'Time'
    assert result.millisecond == 0
    assert result.get_precision_value() == 9
```

### Integration Tests

```python
# tests/integration/test_highboundary.py

def test_patient_birthdate_highboundary():
    """Test Patient.birthDate.highBoundary() translation."""
    translator = get_translator('duckdb')
    ast = parse_fhirpath("Patient.birthDate.highBoundary()")
    fragment = translator.translate(ast)[0]

    # Verify SQL generated correctly
    assert 'birthDate' in fragment.expression
    # Execute and verify result matches specification

def test_decimal_literal_highboundary():
    """Test 1.587.highBoundary() translation."""
    translator = get_translator('duckdb')
    ast = parse_fhirpath("1.587.highBoundary()")
    fragment = translator.translate(ast)[0]

    # Verify decimal boundary algorithm applied
    # Expected output: 1.58750000
```

---

## Next Steps for Junior Developer

### Phase 1: Integration (1 hour)
1. ✅ Review new utilities (element_type_resolver.py, temporal_parser.py)
2. ✅ Import utilities in translator.py
3. ✅ Test utilities independently with unit tests

### Phase 2: Translator Implementation (3-4 hours)
1. Implement `_translate_high_boundary()` method
2. Implement `_determine_boundary_input_type()` helper
3. Implement `_determine_literal_type()` helper
4. Implement `_resolve_path_type()` helper
5. Implement `_translate_decimal_boundary()` method
6. Implement `_translate_temporal_boundary()` method

### Phase 3: Dialect Implementation (4-5 hours)
1. Add abstract methods to base dialect
2. Implement DuckDB decimal boundary generation
3. Implement DuckDB temporal boundary generation
4. Implement PostgreSQL decimal boundary generation
5. Implement PostgreSQL temporal boundary generation

### Phase 4: Testing (2-3 hours)
1. Unit tests for translator methods
2. Unit tests for dialect methods
3. Integration tests with official fixtures
4. Validate all 24 highBoundary tests pass

**Total Revised Estimate: 10-13 hours** (more realistic than original 6h estimate)

---

## Questions?

Contact senior architect if you need:
- ✅ Clarification on element type mappings (add more resource types)
- ✅ Clarification on temporal parsing edge cases
- ✅ SQL syntax guidance for specific boundary calculations
- ✅ Test case interpretation
- ✅ Performance optimization strategies

**Both blockers are now solved - you have all the infrastructure needed to implement highBoundary() and lowBoundary() correctly!** 🎯

---

**Document Created**: 2025-10-17
**Status**: Ready for Implementation
**Blockers**: None - All resolved ✅
