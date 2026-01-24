# Task: Fix Parser Double Quote Support

**Task ID**: SP-021-015-FIX-PARSER-DOUBLE-QUOTES
**Status**: READY TO START
**Priority**: 🔴 HIGH - Blocking ~50-100 tests
**Created**: 2025-12-05
**Estimated Effort**: 4-8 hours
**Expected Impact**: +50-100 tests (+5-10% compliance)

---

## Objective

Fix FHIRPath parser to accept double-quoted strings per FHIRPath specification.

**Current Behavior**: Parser rejects double quotes
```fhirpath
Patient.name.where($this = "value")  // ✗ Parse error!
```

**Expected Behavior**: Parser accepts both single and double quotes
```fhirpath
Patient.name.where($this = "value")  // ✓ Should work
Patient.name.where($this = 'value')  // ✓ Already works
```

---

## Problem Statement

### Root Cause

**FHIRPath Specification**: Both single (`'`) and double (`"`) quotes are valid for string literals per the official FHIRPath specification.

**Current Implementation**: The parser/lexer only accepts single quotes.

**Evidence**:
```python
# Test with double quotes
expr = 'Patient.name.where($this = "value")'
parser.parse(expr)
# Error: LexerNoViableAltException('"')

# Test with single quotes
expr = "Patient.name.where($this = 'value')"
parser.parse(expr)
# ✓ Success
```

### Impact

**Affected Tests**: ~50-100 compliance tests
- All tests using double-quoted strings
- `$this` variable tests with string comparisons
- Function calls with quoted string parameters

**Example Failing Tests**:
- `testDollarThis2`: `Patient.name.given.where(substring($this.length()-3) = "ter")`
- Any test with `where($this = "value")`
- String function tests using double quotes

---

## Investigation Summary

### Parser Architecture

**File**: `fhir4ds/fhirpath/parser.py`
**Grammar**: Uses ANTLR4-based parsing
**Lexer**: Tokenizes input into grammar elements

**String Literal Handling**:
- Defined in lexer grammar rules
- Currently only recognizes single-quote strings
- Needs to also recognize double-quote strings

### FHIRPath Specification Reference

From FHIRPath specification:
> String literals are surrounded by single or double quotes and may use \ escapes.

**Examples from spec**:
```fhirpath
'hello'        // ✓ Valid
"hello"        // ✓ Valid
'can\'t'       // ✓ Valid with escape
"can't"        // ✓ Valid (no escape needed)
"say \"hi\""   // ✓ Valid with escape
```

---

## Implementation Plan

### Phase 1: Locate Lexer Configuration (2 hours)

**Objective**: Find where string literals are defined in the grammar.

**Files to Check**:
1. `fhir4ds/fhirpath/parser.py` - Main parser
2. `fhir4ds/fhirpath/grammar/` - Grammar definitions (if separate)
3. Any `.g4` ANTLR grammar files

**What to Look For**:
```antlr
// Current (likely):
STRING : '\'' (~[\'\\] | ESC)* '\'' ;

// Need to add:
STRING :
    '\'' (~[\'\\] | ESC)* '\''
  | '"' (~["\\] | ESC)* '"'
  ;
```

**Action Steps**:
1. Search for `STRING` or `Literal` token definitions
2. Review lexer rules for quote handling
3. Document current implementation
4. Identify exact location of change needed

**Success Criteria**:
- [ ] Located exact lexer rule for string literals
- [ ] Documented current grammar syntax
- [ ] Identified escape sequence handling

---

### Phase 2: Update Grammar (2-3 hours)

**Objective**: Modify grammar to accept both quote styles.

**Change Pattern**:

```antlr
// BEFORE (single quotes only)
STRING_LITERAL
    : '\'' ( ~[\'\\] | '\\' . )* '\''
    ;

// AFTER (both single and double quotes)
STRING_LITERAL
    : '\'' ( ~[\'\\] | '\\' . )* '\''
    | '"' ( ~["\\] | '\\' . )* '"'
    ;
```

**Escape Sequences**:
Ensure proper handling of:
- `\'` in single-quoted strings
- `\"` in double-quoted strings
- `\\` for literal backslash
- Other escapes: `\n`, `\r`, `\t`

**Action Steps**:
1. Create backup of current grammar file
2. Update STRING_LITERAL rule to accept both quote types
3. Verify escape sequence handling for both styles
4. Regenerate parser if using ANTLR (may be pre-generated)

**Success Criteria**:
- [ ] Grammar updated to accept both quote styles
- [ ] Escape sequences work correctly for both
- [ ] No regex conflicts between quote rules

---

### Phase 3: Test Parser Changes (1-2 hours)

**Objective**: Verify parser accepts both quote styles correctly.

**Test Cases**:

```python
# Test 1: Simple double-quoted string
test_expr = 'Patient.name.where($this = "value")'
assert parser.parse(test_expr) is not None

# Test 2: Simple single-quoted string (regression)
test_expr = "Patient.name.where($this = 'value')"
assert parser.parse(test_expr) is not None

# Test 3: Escaped quote in double-quoted string
test_expr = 'Patient.name.where($this = "say \\"hi\\"")'
assert parser.parse(test_expr) is not None

# Test 4: Escaped quote in single-quoted string (regression)
test_expr = "Patient.name.where($this = 'can\\'t')"
assert parser.parse(test_expr) is not None

# Test 5: Mixed quotes (don't need escaping)
test_expr = 'Patient.name.where($this = "it\'s fine")'
assert parser.parse(test_expr) is not None

# Test 6: Complex expression from failing test
test_expr = 'Patient.name.given.where(substring($this.length()-3) = "ter")'
parsed = parser.parse(test_expr)
assert parsed is not None
assert parsed.is_valid()
```

**Action Steps**:
1. Create `test_parser_quotes.py` in `tests/unit/fhirpath/`
2. Add all test cases above
3. Run tests with `pytest tests/unit/fhirpath/test_parser_quotes.py -v`
4. Fix any issues discovered

**Success Criteria**:
- [ ] All 6 test cases pass
- [ ] No regressions in existing parser tests
- [ ] Both quote styles parse to identical AST

---

### Phase 4: Compliance Testing (1-2 hours)

**Objective**: Verify fix improves compliance test results.

**Baseline** (before fix):
- Total: 934 tests
- Passing: 452 (48.4%)

**Expected** (after fix):
- Passing: 500-550 (53-59%)
- Gain: +50-100 tests

**Specific Tests to Verify**:
```python
# Test the previously failing tests
failing_tests = [
    'testDollarThis2',  # Uses "ter"
    # ... add others with double quotes
]

for test_name in failing_tests:
    result = runner.run_official_tests(test_filter=test_name)
    assert result.test_results[0].passed, f"{test_name} should now pass"
```

**Action Steps**:
1. Run full compliance suite: `python tests/integration/fhirpath/official_test_runner.py`
2. Check improvement in test count
3. Review new failures (if any) - document as follow-up tasks
4. Verify no regressions in previously passing tests

**Success Criteria**:
- [ ] Compliance improved by at least +40 tests
- [ ] `testDollarThis2` now passes
- [ ] No regressions in existing passing tests

---

## Acceptance Criteria

### Functional Requirements
- [ ] Parser accepts single-quoted strings (no regression)
- [ ] Parser accepts double-quoted strings
- [ ] Escape sequences work in both quote styles
- [ ] Both styles parse to semantically identical AST
- [ ] `testDollarThis2` compliance test passes

### Testing Requirements
- [ ] Unit tests created for both quote styles
- [ ] Unit tests cover escape sequences
- [ ] All existing parser tests still pass
- [ ] Compliance tests improve by +40 tests minimum

### Quality Requirements
- [ ] Code follows project coding standards
- [ ] Changes documented in code comments
- [ ] Grammar changes clearly documented
- [ ] No hardcoded quote type assumptions

---

## Dependencies

**Prerequisites**:
- None - can start immediately

**Blocks**:
- ~50-100 compliance tests currently failing due to this issue
- String comparison tests
- Variable tests with string literals

---

## Risk Assessment

### Technical Risks

**LOW**: Parser modification is well-isolated
- Lexer change doesn't affect translator or executor
- Grammar change is localized to string literal rules
- Can rollback easily if issues arise

**MEDIUM**: Potential escape sequence complexity
- Mitigation: Thorough testing of all escape scenarios
- Mitigation: Review FHIRPath spec escape rules

### Testing Risks

**LOW**: Comprehensive test coverage available
- Official compliance tests validate correctness
- Can add unit tests for edge cases

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/fhirpath/test_parser_quotes.py`

```python
import pytest
from fhir4ds.fhirpath.parser import FHIRPathParser

class TestParserQuoteSupport:
    """Test parser support for both single and double quotes."""

    def test_single_quotes_basic(self):
        """Single quotes should work (regression test)."""
        parser = FHIRPathParser()
        result = parser.parse("Patient.name.where($this = 'value')")
        assert result.is_valid()

    def test_double_quotes_basic(self):
        """Double quotes should work (new functionality)."""
        parser = FHIRPathParser()
        result = parser.parse('Patient.name.where($this = "value")')
        assert result.is_valid()

    def test_single_quote_escape(self):
        """Escaped single quote in single-quoted string."""
        parser = FHIRPathParser()
        result = parser.parse("Patient.name.where($this = 'can\\'t')")
        assert result.is_valid()

    def test_double_quote_escape(self):
        """Escaped double quote in double-quoted string."""
        parser = FHIRPathParser()
        result = parser.parse('Patient.name.where($this = "say \\"hi\\"")')
        assert result.is_valid()

    def test_mixed_quotes_no_escape(self):
        """Single quote in double-quoted string needs no escape."""
        parser = FHIRPathParser()
        result = parser.parse('Patient.name.where($this = "it\'s fine")')
        assert result.is_valid()

    def test_complex_expression(self):
        """Complex expression from failing compliance test."""
        parser = FHIRPathParser()
        expr = 'Patient.name.given.where(substring($this.length()-3) = "ter")'
        result = parser.parse(expr)
        assert result.is_valid()
```

### Integration Tests

Run against actual compliance tests to verify improvement.

---

## Implementation Checklist

### Pre-Implementation
- [ ] Read this task document completely
- [ ] Review FHIRPath specification on string literals
- [ ] Review current parser implementation
- [ ] Set up development environment

### Phase 1: Investigation
- [ ] Locate lexer grammar file
- [ ] Document current STRING_LITERAL rule
- [ ] Identify escape sequence handling
- [ ] Create backup of grammar file

### Phase 2: Implementation
- [ ] Update STRING_LITERAL to accept both quote types
- [ ] Verify escape sequence rules for both
- [ ] Regenerate parser if needed (ANTLR)
- [ ] Test parser can import without errors

### Phase 3: Unit Testing
- [ ] Create `test_parser_quotes.py`
- [ ] Write 6+ unit tests covering both quote types
- [ ] Run unit tests: all pass
- [ ] Run existing parser tests: no regressions

### Phase 4: Integration Testing
- [ ] Run full compliance suite
- [ ] Document before/after results
- [ ] Verify +40 test minimum improvement
- [ ] Check for any new failures

### Phase 5: Documentation
- [ ] Update task with results
- [ ] Document grammar changes in code comments
- [ ] Update parser documentation if exists
- [ ] Note any follow-up issues discovered

---

## Common Pitfalls (For Junior Developer)

### Pitfall #1: Forgetting Escape Sequences
**Wrong**:
```antlr
STRING : '"' ~["]* '"' ;  // Doesn't handle \" escape
```

**Right**:
```antlr
STRING : '"' (~["\\] | '\\' .)* '"' ;  // Handles escapes
```

### Pitfall #2: Not Testing Regressions
Always test that single quotes STILL work after adding double quote support.

### Pitfall #3: Inconsistent AST
Both quote styles should produce identical AST:
```python
ast1 = parser.parse('where($this = "value")').get_ast()
ast2 = parser.parse("where($this = 'value')").get_ast()
# ast1 and ast2 should be semantically identical
```

### Pitfall #4: Not Regenerating Parser
If grammar uses ANTLR, you may need to run:
```bash
antlr4 -Dlanguage=Python3 FHIRPath.g4
```

---

## Success Metrics

### Primary Metrics
- [ ] Parser accepts double-quoted strings without error
- [ ] Compliance tests improve by +40 minimum (+50-100 expected)
- [ ] `testDollarThis2` passes

### Secondary Metrics
- [ ] No regressions in existing tests
- [ ] Code coverage maintained or improved
- [ ] All escape sequences work correctly

---

## Resources

### FHIRPath Specification
- **Official Spec**: https://hl7.org/fhirpath/
- **Grammar**: https://hl7.org/fhirpath/grammar.html
- **String Literals**: Section on lexical elements

### ANTLR Resources
- **ANTLR4 Documentation**: https://github.com/antlr/antlr4/blob/master/doc/index.md
- **Lexer Rules**: https://github.com/antlr/antlr4/blob/master/doc/lexer-rules.md

### Project Files
- Parser: `fhir4ds/fhirpath/parser.py`
- Tests: `tests/unit/fhirpath/`
- Compliance: `tests/integration/fhirpath/official_test_runner.py`

---

## Notes for Junior Developer

### Getting Started
1. **Read the FHIRPath spec** - Understand what string literals should support
2. **Examine current code** - See how single quotes are handled
3. **Start small** - Get one double-quoted test passing first
4. **Test frequently** - Run tests after each change

### When You're Stuck
1. **Check error messages** - Parser errors are usually descriptive
2. **Look at existing tests** - See how single quotes are tested
3. **Ask for help** - If stuck for >30 minutes, ask questions

### Before Submitting
1. **All tests pass** - Unit + integration
2. **Code formatted** - Follow project standards
3. **Documentation updated** - This task + code comments
4. **Results documented** - Update task with before/after metrics

---

**Created**: 2025-12-05
**Status**: Ready to start
**Assignee**: Junior Developer
**Reviewer**: Senior Solution Architect
**Estimated Duration**: 4-8 hours
**Expected Impact**: +50-100 tests (+5-10% compliance)
