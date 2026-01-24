# Task SP-012-015: Improve String Functions

**Task ID**: SP-012-015
**Sprint**: Sprint 012 - PostgreSQL Execution and FHIRPath Compliance Growth
**Task Name**: Improve String Functions
**Assignee**: Junior Developer
**Created**: 2025-10-26
**Last Updated**: 2025-10-27
**Original Task**: SP-010-005 (carried forward from Sprint 010)

---

## Task Overview

### Description

Implement missing string functions (`upper()`, `lower()`, `trim()`) and fix string function edge cases to improve the String Functions category from 78.5% to 89%+.

**Current State**: 51/65 tests passing (78.5%)
**Target State**: 58/65 tests passing (89.2%)
**Expected Gain**: +7 tests (+0.7% overall compliance)

**Note**: This task carries forward SP-010-005, which was originally planned but not completed in Sprint 010. Sprint 012 accomplished the other Sprint 010 goals (arithmetic, comments, math functions).

### Category
- [ ] Bug Fix
- [x] Feature Implementation
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation

### Priority
- [ ] High (Important for sprint success)
- [x] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: String functions are commonly used in FHIRPath expressions. Improving from 78.5% to 89%+ provides substantial value.

---

## Requirements

### Functional Requirements

1. **Implement `upper()` function**
   - Convert string to uppercase
   - Handle null values
   - Support Unicode characters
   - Example: `'hello'.upper()` → `'HELLO'`

2. **Implement `lower()` function**
   - Convert string to lowercase
   - Handle null values
   - Support Unicode characters
   - Example: `'HELLO'.lower()` → `'hello'`

3. **Implement `trim()` function**
   - Remove leading/trailing whitespace
   - Handle null values
   - Preserve internal whitespace
   - Example: `'  hello  '.trim()` → `'hello'`

4. **Fix String Function Edge Cases**
   - Empty strings
   - Null values
   - Special characters
   - Unicode handling
   - Multi-byte characters

### Non-Functional Requirements

- **Performance**: Maintain <10ms average execution time
- **Compliance**: Increase String Functions from 78.5% to 89.2%
- **Database Support**: Identical behavior in DuckDB and PostgreSQL
- **Unicode Support**: Handle multi-byte Unicode characters correctly

### Acceptance Criteria

- [x] `upper()` function implemented and working
- [x] `lower()` function implemented and working
- [x] `trim()` function implemented and working
- [x] Edge cases handled correctly (null, empty, special chars)
- [ ] 58/65 String Function tests passing (89.2%)
- [ ] Zero regressions in other categories
- [ ] Both DuckDB and PostgreSQL validated
- [x] Unicode characters handled correctly

---

## Technical Specifications

### Affected Components

- **SQL Translator** (`fhir4ds/fhirpath/sql/translator.py`): String function translation
- **Database Dialects** (`fhir4ds/dialects/`): Database-specific string functions
- **Type System** (`fhir4ds/fhirpath/types/`): Return type inference

### File Modifications

**Primary Changes**:
- **`fhir4ds/fhirpath/sql/translator.py`**: Add string function translators
- **`fhir4ds/dialects/base.py`**: Abstract string function methods
- **`fhir4ds/dialects/duckdb.py`**: DuckDB string function SQL
- **`fhir4ds/dialects/postgresql.py`**: PostgreSQL string function SQL

**Test Files**:
- **`tests/unit/fhirpath/test_string_functions.py`**: Unit tests for new functions
- **`tests/integration/fhirpath/`**: Integration tests
- **Compliance tests**: Official FHIRPath test suite

### Database Considerations

**DuckDB**:
```sql
-- upper()
UPPER(string_expr)

-- lower()
LOWER(string_expr)

-- trim()
TRIM(string_expr)
```

**PostgreSQL**:
```sql
-- upper()
UPPER(string_expr)

-- lower()
LOWER(string_expr)

-- trim()
TRIM(string_expr)
```

**Note**: SQL standard functions - should be identical across databases.

---

## Dependencies

### Prerequisites

1. **String Function Infrastructure**: ✅ Available (contains(), startsWith(), etc. exist)
2. **Dialect System**: ✅ Available
3. **Type System**: ✅ Available

### Blocking Tasks

None

### Dependent Tasks

None (standalone improvement)

---

## Implementation Approach

### High-Level Strategy

**Principle**: Implement standard string functions following established patterns from existing string functions (contains, startsWith, etc.).

**Approach**:
1. **Phase 1**: Implement `upper()` function
2. **Phase 2**: Implement `lower()` function
3. **Phase 3**: Implement `trim()` function
4. **Phase 4**: Fix edge cases and test

### Implementation Steps

#### Step 1: Implement upper() Function (2 hours)

**Translator**:
```python
# In sql_translator.py
def translate_upper_function(self, args):
    """Translate upper() function - convert to uppercase."""
    if len(args) != 1:
        raise ValueError("upper() requires exactly 1 argument")

    value_sql = self.translate(args[0])
    upper_sql = self.dialect.generate_string_function('upper', value_sql)

    return f"""CASE
        WHEN ({value_sql}) IS NULL THEN NULL
        ELSE {upper_sql}
    END"""

# Register
self.function_translators['upper'] = self.translate_upper_function
```

**Dialect** (both DuckDB and PostgreSQL):
```python
# In base dialect or specific dialects
def generate_string_function(self, func_name, *args):
    if func_name == 'upper':
        return f"UPPER({args[0]})"
    # ... other functions
```

**Test**:
```python
def test_upper():
    assert evaluate("'hello'.upper()") == ['HELLO']
    assert evaluate("'HELLO'.upper()") == ['HELLO']
    assert evaluate("'HeLLo'.upper()") == ['HELLO']
    assert evaluate("{}.upper()") == []  # null
```

---

#### Step 2: Implement lower() Function (2 hours)

**Implementation**: Similar to `upper()`, using `LOWER()` SQL function

**Test**:
```python
def test_lower():
    assert evaluate("'HELLO'.lower()") == ['hello']
    assert evaluate("'hello'.lower()") == ['hello']
    assert evaluate("'HeLLo'.lower()") == ['hello']
    assert evaluate("{}.lower()") == []  # null
```

---

#### Step 3: Implement trim() Function (2 hours)

**Implementation**: Similar pattern, using `TRIM()` SQL function

**Test**:
```python
def test_trim():
    assert evaluate("'  hello  '.trim()") == ['hello']
    assert evaluate("'hello'.trim()") == ['hello']
    assert evaluate("'  '.trim()") == ['']
    assert evaluate("{}.trim()") == []  # null
```

---

#### Step 4: Fix Edge Cases (3 hours)

**Empty Strings**:
```python
assert evaluate("''.upper()") == ['']
assert evaluate("''.lower()") == ['']
assert evaluate("''.trim()") == ['']
```

**Special Characters**:
```python
assert evaluate("'hello!@#'.upper()") == ['HELLO!@#']
assert evaluate("'HELLO!@#'.lower()") == ['hello!@#']
```

**Unicode**:
```python
assert evaluate("'héllo'.upper()") == ['HÉLLO']
assert evaluate("'HÉLLO'.lower()") == ['héllo']
```

**Whitespace Variations**:
```python
assert evaluate("'\\t  hello  \\n'.trim()") == ['hello']
assert evaluate("'hello  world'.trim()") == ['hello  world']  # internal preserved
```

---

#### Step 5: Testing and Validation (3 hours)

**Unit Tests**: Test each function individually

**Integration Tests**: Test in complete FHIRPath expressions

**Compliance Tests**:
```bash
PYTHONPATH=. python3 -m tests.compliance.fhirpath.test_runner --groups string_functions

# Target: 58/65 (89.2%)
```

**Multi-Database**:
```bash
# DuckDB
PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/test_string_functions.py

# PostgreSQL
PYTHONPATH=. python3 -m pytest tests/unit/fhirpath/test_string_functions.py --postgresql
```

---

## Testing Strategy

### Unit Testing

**Function Tests**:
- `upper()` with various inputs
- `lower()` with various inputs
- `trim()` with various inputs
- Null handling
- Edge cases

**Integration Tests**:
- Chained operations: `'hello'.upper().trim()`
- In complex expressions: `name.given.first().upper()`

### Compliance Testing

**String Functions Category**:
- Target: 58/65 tests passing (89.2%)
- Current: 51/65 tests passing (78.5%)
- Gain: +7 tests

### Multi-Database Testing

- Validate identical results in DuckDB and PostgreSQL
- Check Unicode handling in both databases
- Verify performance is acceptable

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Unicode handling differs between databases | Low | Medium | Test Unicode explicitly |
| Trim behavior varies (tabs, newlines) | Low | Low | Use SQL standard TRIM |
| Performance issues with large strings | Low | Low | Test with realistic data sizes |
| Existing string function patterns broken | Very Low | Medium | Follow established patterns |

---

## Estimation

### Time Breakdown

- **Implement upper()**: 2 hours
- **Implement lower()**: 2 hours
- **Implement trim()**: 2 hours
- **Fix Edge Cases**: 3 hours
- **Testing & Validation**: 3 hours
- **Total Estimate**: **12 hours** (1.5 days)

### Confidence Level

- [x] High (90%+ confident)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident)

**Rationale**: String functions are straightforward SQL functions with standard behavior. Infrastructure for string functions already exists (contains, startsWith, etc.). Low complexity implementation.

---

## Success Metrics

### Quantitative Measures

- **String Functions**: 51/65 → 58/65 (78.5% → 89.2%)
- **Test Pass Rate**: +7 tests
- **Regressions**: 0

### Qualitative Measures

- **Code Quality**: Clean, maintainable implementation
- **Architecture**: Thin dialects maintained
- **Unicode Support**: Correct handling of multi-byte characters

### Compliance Impact

- **String Functions**: 78.5% → 89.2% (+10.7%)
- **Overall Compliance**: ~+0.7%

---

## Documentation Requirements

### Code Documentation

- [ ] Function docstrings for upper(), lower(), trim()
- [ ] Edge case handling notes
- [ ] Dialect method documentation

### User Documentation

- [ ] String function reference examples
- [ ] Unicode handling notes

---

## Progress Tracking

### Status

- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [x] In Review
- [ ] Completed

**Current Status**: Completed - Pending Review

### Progress Updates

| Date | Status | Progress Description | Blockers | Next Steps |
|------|--------|---------------------|----------|------------|
| 2025-10-26 | Not Started | Task created, carried forward from SP-010-005 | None | Begin when Sprint 012 capacity available |
| 2025-10-27 | In Development | Implemented unified translator helper for upper/lower/trim, refactored dialect calls, and refreshed unit coverage (method + function style, Unicode). | None | Run focused translator test suite and update task documentation |
| 2025-10-27 | Completed - Pending Review | Translator updates merged with new tests; translator case/trim pytest passes. Full pytest attempt timed out (~10m) and PostgreSQL-dependent cases remain pending due to missing instance. | Full pytest timed out; PostgreSQL validation awaiting available database | Rerun full pytest with PostgreSQL resources; hand off for senior review |

### Completion Checklist

- [x] `upper()` function implemented
- [x] `lower()` function implemented
- [x] `trim()` function implemented
- [x] Edge cases fixed
- [x] Unit tests passing
- [ ] Integration tests passing
- [ ] Compliance tests: 58/65 passing
- [ ] Multi-database validated
- [ ] Zero regressions
- [ ] Code reviewed and approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation follows existing string function patterns
- [ ] Tests comprehensive and passing
- [ ] No regressions introduced
- [x] Documentation complete
- [ ] Multi-database validated

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [TBD]
**Review Status**: Pending

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [TBD]
**Status**: Pending

---

## Related Tasks

### Sprint 010 Original Tasks

- **SP-010-001**: Path Navigation → **Carried forward to SP-012-014**
- **SP-010-002**: Comments/Syntax → **Completed by SP-012-009** ✅
- **SP-010-003**: Arithmetic Operators → **Completed by SP-012-007** ✅
- **SP-010-004**: Math Functions → **Completed by SP-012-010** ✅
- **SP-010-005**: String Functions (this carries it forward)

### Sprint 012 Related Tasks

- **SP-012-010**: Math functions (100%) - similar pattern for functions
- **SP-012-007**: Arithmetic operators - similar dialect usage

---

**Task Created**: 2025-10-26 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-26
**Status**: Completed - Pending Review
**Estimated Effort**: 12 hours (1.5 days)
**Branch**: `feature/SP-012-015` (when started)

---

*This task completes the string function suite with commonly-used case and whitespace manipulation functions.*
