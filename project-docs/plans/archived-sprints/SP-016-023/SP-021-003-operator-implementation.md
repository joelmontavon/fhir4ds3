# Task: Implement Missing FHIRPath Operators

**Task ID**: SP-021-003-OPERATOR-IMPLEMENTATION
**Sprint**: Current Sprint
**Task Name**: Implement Missing FHIRPath Unary and Binary Operators
**Assignee**: TBD
**Created**: 2025-11-28
**Last Updated**: 2025-11-28
**Status**: NOT STARTED
**Priority**: **HIGH** (Second-highest compliance impact: +15-20 tests)

---

## Task Overview

### Description

Implement missing FHIRPath operators identified in SP-021-001 investigation, including:
- Unary operators (e.g., unary minus `-value`)
- Operator parameter handling improvements
- Edge cases in existing operator implementations

Currently, ~20 compliance tests fail with errors like:
```
Error: Unknown unary operator: -
Error: List index out of range in operator handling
```

This task is identified as **Priority 2** from the SP-021-001 investigation findings, with projected compliance improvement of +15-20 tests.

### Category
- [x] Feature Implementation
- [x] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation

### Priority
- [ ] Critical (Blocker for compliance progress)
- [x] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

**Rationale**: Operator implementation blocks ~20 compliance tests and is foundational for mathematical and logical expressions.

---

## Requirements

### Functional Requirements

1. **Unary Operators**: Implement unary minus and plus
   - Example: `-5` should return -5
   - Example: `+value` should return value

2. **Operator Precedence**: Ensure correct precedence for all operators
   - Unary operators bind tighter than binary operators
   - Parentheses override precedence

3. **Operator Parameter Validation**: Improve error handling for invalid operands
   - Type checking for operators
   - Clear error messages

4. **Multi-Database Support**: Ensure identical behavior in DuckDB and PostgreSQL

### Acceptance Criteria

- [ ] Unary minus operator works correctly
- [ ] Unary plus operator works correctly
- [ ] Operator precedence follows FHIRPath specification
- [ ] Compliance reaches 419+ tests passing (minimum +15 tests improvement)
- [ ] Zero regressions in existing tests
- [ ] Both DuckDB and PostgreSQL produce identical results

---

## Technical Specifications

### Affected Components

- **Parser** (`fhir4ds/fhirpath/parser_core/`): Add unary operator recognition
- **ASTToSQLTranslator** (`fhir4ds/fhirpath/sql/translator.py`): Add unary operator translation
- **Operator Handlers**: Improve parameter validation and error handling

### Implementation Steps

1. **Parser Updates** (2-3 hours): Recognize unary operators in grammar
2. **Translator Updates** (3-4 hours): Translate unary operators to SQL
3. **Parameter Validation** (2 hours): Improve operator parameter handling
4. **Unit Tests** (2-3 hours): Test all operator types
5. **Compliance Testing** (1-2 hours): Validate improvement

---

## Estimation

- **Total Estimate**: 10-14 hours
- **Confidence Level**: High (90%+)
- **Expected Impact**: +15-20 tests (from 404/934 to 419-424/934, 45-45.4% compliance)

---

## References

- **Investigation Findings**: `work/SP-021-001-INVESTIGATION-FINDINGS.md` (Priority 2)
- **FHIRPath Specification**: Operators (Section 6)
- **Predecessor**: SP-021-002 (variable binding recommended first)

---

**Task Created**: 2025-11-28
**Priority**: HIGH (Second-highest compliance impact)
**Estimated Impact**: +15-20 tests
