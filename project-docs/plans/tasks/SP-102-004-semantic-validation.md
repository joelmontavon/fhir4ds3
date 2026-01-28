# Task SP-102-004: Semantic Validation for Invalid Expressions

**Priority:** P1 (HIGH)
**Estimated Effort:** 4-6 hours
**Dependencies:** None
**Tests Fixed:** 3
**Status:** Pending

---

## Task Description

Enhance the semantic validator to properly reject syntactically/semantically invalid expressions that are currently being accepted by the parser.

## Failing Tests

- `testComment7`: `2 + 2 /` (incomplete operator)
- `testComment8`: `2 + 2 /* not finished` (unterminated comment)
- `testLiteralIntegerNegative1Invalid`: `-1.convertsToInteger()` (invalid negative literal syntax)

## Root Cause Analysis

**Current Behavior:**
The parser accepts invalid expressions and only fails during SQL translation or execution. However, the test framework expects these to fail at semantic validation time.

**Expected Behavior:**
These expressions should be rejected during semantic validation with appropriate error messages.

## Implementation Strategy

### Phase 1: Understand Semantic Validation

**File:** `fhir4ds/main/fhirpath/parser_core/semantic_validator.py`

1. Review existing semantic validation logic
2. Understand when validation errors should be raised
3. Identify missing validation rules

### Phase 2: Add Validation Rules

**Rule 1: Incomplete Operators**
```python
def validate_binary_operator(self, node: OperatorNode):
    if node.operator in ('+', '-', '*', '/', 'div', 'mod'):
        if not node.right:
            raise FHIRPathValidationError(
                f"Incomplete operator expression: {node.operator}"
            )
```

**Rule 2: Unterminated Comments**
```python
# This should be caught during parsing, but add semantic check
def validate_comments(self, expression: str):
    if '/*' in expression and '*/' not in expression[expression.index('/*'):]:
        raise FHIRPathValidationError("Unterminated block comment")
```

**Rule 3: Negative Literal Syntax**
```python
def validate_negative_literal(self, node: LiteralNode):
    # FHIRPath doesn't allow -1.convertsToInteger()
    # Must use (-1).convertsToInteger() or 1.convertsToInteger() * -1
    if node.value < 0 and hasattr(node, 'parent'):
        if isinstance(node.parent, FunctionCallNode):
            raise FHIRPathValidationError(
                "Negative literals cannot be used directly in function calls"
            )
```

### Phase 3: Test Validation

Ensure all invalid expressions are caught early.

## Acceptance Criteria

- [ ] `testComment7` fails with semantic error
- [ ] `testComment8` fails with semantic error
- [ ] `testLiteralIntegerNegative1Invalid` fails with semantic error
- [ ] Valid expressions still work
- [ ] Clear error messages
- [ ] No false positives

## Testing Commands

```bash
# Semantic validation tests
python3 -m pytest tests/unit/fhirpath/test_semantic_validator.py -v

# Compliance tests
python3 -m pytest tests/integration/fhirpath/official_test_runner.py -v
```

## Risk Assessment

**Risk Level:** MEDIUM

**Risks:**
1. May reject valid expressions
2. Could break existing functionality

**Mitigation:**
1. Comprehensive testing of valid expressions
2. Clear validation rules

## Dependencies

**Blocks:** None

**Blocked By:** None

## Notes

- Important for spec compliance
- Improves error messages
- Prevents confusing runtime errors

---

**Task Status:** Pending
**Assigned To:** Unassigned
**Review Status:** Not Started
**Completion Date:** TBD
