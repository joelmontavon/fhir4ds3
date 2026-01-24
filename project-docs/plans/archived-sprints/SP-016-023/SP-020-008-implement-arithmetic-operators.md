# Task: Implement FHIRPath Arithmetic Operators

**Task ID**: SP-020-008
**Sprint**: 020
**Task Name**: Implement FHIRPath Arithmetic Operators for SQL Translator
**Assignee**: Junior Developer
**Created**: 2025-11-18
**Last Updated**: 2025-11-18
**Priority**: Medium (Would improve compliance from 42.4% to ~48%)
**Estimated Effort**: 32-48 hours (1-1.5 weeks)

---

## Task Overview

### Description

Implement the missing FHIRPath arithmetic operators in the SQL translator to improve specification compliance from 42.4% to approximately 48%. Currently, 53 of 72 arithmetic operator tests are failing.

**Current State**: 19/72 tests passing (26.4%)
**Target State**: 65+/72 tests passing (90%+)
**Impact**: +5-6% overall FHIRPath compliance

**Key Operators to Implement**:
1. **Unary Operators**: `-` (negation), `+` (positive)
2. **Binary Arithmetic**: `+`, `-`, `*`, `/`, `div`, `mod`
3. **Quantity Arithmetic**: Operations on FHIR Quantity types
4. **Type Promotion**: Automatic integer → decimal conversion
5. **Division by Zero**: Proper handling (return empty, not error)
6. **Null Propagation**: Null + anything = null

### Category
- [x] Feature Implementation
- [ ] Bug Fix

### Priority
- [ ] Critical
- [ ] High
- [x] Medium (Valuable improvement)
- [ ] Low

---

## Requirements

### Functional Requirements

1. **Unary Operators**
   - `-value`: Negate number
   - `+value`: Positive (identity operation)
   - Example: `-5` → -5, `+3.14` → 3.14

2. **Binary Arithmetic Operators**
   - `a + b`: Addition
   - `a - b`: Subtraction
   - `a * b`: Multiplication
   - `a / b`: Division (decimal result)
   - `a div b`: Integer division (truncate)
   - `a mod b`: Modulo (remainder)

3. **Type Promotion**
   - Integer + Decimal → Decimal
   - Integer / Integer → Decimal (not integer)
   - Preserve precision for decimal operations

4. **Quantity Arithmetic**
   - Support arithmetic on FHIR Quantity types
   - Unit validation: can only add/subtract same units
   - Example: `5 'mg' + 3 'mg'` → `8 'mg'`
   - Example: `5 'mg' + 3 'g'` → error (incompatible units)

5. **Error Handling**
   - Division by zero → empty (not error)
   - Null + anything → null
   - Incompatible types → empty
   - Incompatible units → empty

### Acceptance Criteria

- [ ] All unary operators: 10+ tests passing
- [ ] All binary operators: 40+ tests passing
- [ ] Type promotion: 8+ tests passing
- [ ] Quantity arithmetic: 10+ tests passing
- [ ] Overall arithmetic: 65+/72 tests passing (90%+)
- [ ] Zero regressions
- [ ] Both DuckDB and PostgreSQL

---

## Technical Specifications

### Affected Components

- **FHIRPath SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): ~600 lines added
- **Dialect Classes** (`fhir4ds/dialects/`): Database-specific operators
- **Type Registry** (`fhir4ds/fhirpath/types/type_registry.py`): Type promotion rules

### File Modifications

- **`fhir4ds/fhirpath/sql/translator.py`**: Add ~600 lines
  - `_translate_unary_operator()` - new method (~100 lines)
  - `_translate_binary_operator()` - enhance existing (~200 lines)
  - `_translate_arithmetic()` - new helper (~150 lines)
  - `_translate_quantity_arithmetic()` - new method (~150 lines)

- **`fhir4ds/dialects/duckdb.py`**: Add ~80 lines
  - Safe division operators
  - Type casting for promotion

- **`fhir4ds/dialects/postgresql.py`**: Add ~80 lines
  - NULLIF for division by zero
  - Type casting for promotion

- **`tests/unit/fhirpath/sql/test_translator_arithmetic.py`**: New file (~400 lines)

---

## Implementation Approach

### Implementation Steps

#### Step 1: Implement Unary Operators (6-8 hours)

**Activities**:
- Implement `_translate_unary_operator(node)` method
- Handle `-` (negation) and `+` (identity)
- Generate appropriate SQL

**Example SQL**:
```sql
-- DuckDB: -5
-(5)

-- DuckDB: +value
+(json_extract_string(resource, '$.value'))
```

**Validation**: 10+ unary operator tests passing

---

#### Step 2: Implement Binary Arithmetic Operators (12-16 hours)

**Activities**:
- Enhance `_translate_binary_operator()` for arithmetic
- Implement type promotion logic
- Handle division by zero safely
- Support all six operators: +, -, *, /, div, mod

**Example SQL**:
```sql
-- DuckDB: 5 + 3
(5 + 3)

-- DuckDB: 10 / 0 (safe division)
CASE WHEN 0 = 0 THEN NULL ELSE (10 / 0) END

-- PostgreSQL: 7 div 2 (integer division)
(7 / 2)::integer

-- DuckDB: 10 mod 3 (modulo)
(10 % 3)
```

**Type Promotion**:
```python
def _promote_types(self, left_type, right_type):
    """Promote types for arithmetic operations."""
    if left_type == 'decimal' or right_type == 'decimal':
        return 'decimal'
    if left_type == 'integer' and right_type == 'integer':
        # Integer + Integer → stays integer (except division)
        return 'integer'
    return 'decimal'  # Default to decimal
```

**Validation**: 40+ binary operator tests passing

---

#### Step 3: Implement Quantity Arithmetic (8-12 hours)

**Activities**:
- Parse Quantity literals: `5 'mg'`
- Extract value and unit from Quantity objects
- Validate unit compatibility
- Perform arithmetic and rebuild Quantity

**Example SQL**:
```sql
-- DuckDB: 5 'mg' + 3 'mg'
CASE
    WHEN '5 mg'.unit = '3 mg'.unit THEN
        json_object(
            'value', 5 + 3,
            'unit', 'mg'
        )
    ELSE NULL  -- Incompatible units
END
```

**Validation**: 10+ Quantity tests passing

---

#### Step 4: Integration and Testing (6-8 hours)

**Activities**:
- Run full compliance suite
- Fix regressions
- Test both databases
- Optimize performance

**Validation**:
- Arithmetic: 65+/72 passing (90%+)
- Overall: 45-48% (up from 42.4%)

---

## Testing Strategy

### Unit Testing

**Test File**: `tests/unit/fhirpath/sql/test_translator_arithmetic.py`

**Test Categories**:
1. **Unary Operators**: Negation, positive, edge cases
2. **Binary Operators**: All six operators, type combinations
3. **Type Promotion**: Integer + Decimal scenarios
4. **Division by Zero**: Safe handling
5. **Quantity Arithmetic**: Unit validation, operations
6. **Null Propagation**: Null in arithmetic

**Coverage Target**: 95%+

### Integration Testing

- DuckDB and PostgreSQL parity
- Arithmetic in complex expressions
- Performance validation

### Compliance Testing

```bash
# Expected improvement:
# Before: 396/934 (42.4%)
# After:  420-450/934 (45-48%)
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Type promotion complexity | Medium | Medium | Use clear rules, test extensively |
| Quantity unit validation | Medium | Low | Start with simple cases, defer complex units |
| Division by zero edge cases | Low | Low | Use CASE WHEN pattern consistently |
| Performance overhead | Low | Low | Use native database operators |

---

## Estimation

### Time Breakdown

- **Analysis**: 4 hours
- **Implementation**: 26-36 hours
  - Step 1: Unary operators: 6-8 hours
  - Step 2: Binary operators: 12-16 hours
  - Step 3: Quantity arithmetic: 8-12 hours
- **Testing**: 12-16 hours
- **Documentation**: 4-6 hours
- **Review**: 4-6 hours

**Total**: 50-68 hours (1.25-1.7 weeks)
**Conservative**: 60 hours (1.5 weeks)

### Confidence Level
- [x] High (90%+ confident)

**Rationale**: Arithmetic operators are straightforward, well-documented in both FHIRPath spec and database documentation.

---

## Success Metrics

### Quantitative
- Arithmetic tests: 19 → 65+ passing (26.4% → 90%+)
- Overall compliance: 42.4% → 45-48%
- Zero regressions

### Qualitative
- Clean, readable code
- Fast performance (<10ms per operation)
- Comprehensive error handling

---

## Documentation Requirements

### Code Documentation
- [x] Inline comments for type promotion logic
- [x] Function documentation with arithmetic examples
- [x] Quantity arithmetic rules documented

### Architecture Documentation
- [ ] Update translator architecture docs
- [ ] Document type promotion rules
- [ ] Add arithmetic examples to guide

---

## Progress Tracking

### Status
- [x] Not Started

### Completion Checklist
- [ ] All arithmetic operators implemented
- [ ] 65+/72 tests passing
- [ ] Code reviewed
- [ ] Documentation complete

---

**Task Created**: 2025-11-18 by Senior Solution Architect/Engineer
**Status**: Not Started
**Priority**: Medium (+5-6% compliance improvement)

---

*This task improves arithmetic operator support, a fundamental requirement for quality measure calculations.*
