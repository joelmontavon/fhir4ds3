# Task: Fix String Function Signature Bugs

**Task ID**: SP-006-030 | **Sprint**: 006 | **Estimate**: 4h | **Priority**: Critical
**Status**: ✅ Completed | **Actual**: 3.5h | **Completed**: 2025-01-04

## Overview
Fix signature bugs in `indexOf()` and `replace()` string functions identified during SP-006-027 investigation. These functions currently require incorrect number of arguments due to method call context handling issues.

## Context from SP-006-027

**Investigation Finding**: SP-006-027 revealed that indexOf and replace functions have signature bugs:
- **indexOf**: Currently requires 2 arguments, FHIRPath spec allows 1
- **replace**: Currently requires 3 arguments, FHIRPath spec allows 2

**Root Cause**: Method call context (the string being operated on) is incorrectly counted as an explicit argument.

**Impact**:
- Current: 6 failing tests (3 indexOf + 3 replace)
- After fix: +6 tests passing
- Coverage improvement: 35.8% → 41.3% string functions

## Root Cause Analysis

### Issue: Method Call Context Handling

**FHIRPath Expression Pattern**:
```fhirpath
'hello'.indexOf('l')        # Method call: context='hello', args=['l']
'123456'.replace('234', 'X') # Method call: context='123456', args=['234', 'X']
```

**Current Bug**:
The translator incorrectly counts the implicit context (the string being operated on) as an explicit argument.

**Example - indexOf**:
- Expression: `'LogicalModel-Person'.indexOf('-')`
- Parser creates: Method call with context=`'LogicalModel-Person'` and arguments=[`'-'`]
- Translator receives: FunctionCallNode with 1 explicit argument
- Current validation: `if len(node.arguments) != 2` ❌ WRONG
- Correct validation: `if len(node.arguments) != 1` ✅ CORRECT

**Example - replace**:
- Expression: `'123456'.replace('234', 'X')`
- Parser creates: Method call with context=`'123456'` and arguments=[`'234'`, `'X'`]
- Translator receives: FunctionCallNode with 2 explicit arguments
- Current validation: `if len(node.arguments) != 3` ❌ WRONG
- Correct validation: `if len(node.arguments) != 2` ✅ CORRECT

## Implementation Steps

### 1. Fix indexOf() Signature (1.5h)

**File**: `fhir4ds/fhirpath/sql/translator.py`

**Current Code** (line ~XXX):
```python
def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
    if node.function_name == "indexOf":
        if len(node.arguments) != 2:  # ❌ WRONG
            raise ValueError(f"indexOf() requires exactly 2 arguments, got {len(node.arguments)}")

        # Implementation expects: base_expr=arg[0], substring=arg[1]
        # But should be: base_expr=context, substring=arg[0]
```

**Fix Required**:
```python
def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
    if node.function_name == "indexOf":
        if len(node.arguments) != 1:  # ✅ CORRECT: 1 explicit argument (substring)
            raise ValueError(f"indexOf() requires exactly 1 argument, got {len(node.arguments)}")

        # Context handling: The string is in the translation context (implicit)
        # Argument 0 is the substring to search for
        base_expr = self.context.current_expr  # Get from context, not arguments
        substring_fragment = self.visit(node.arguments[0])

        # Generate SQL using dialect method
        sql = self.dialect.generate_string_function(
            'indexOf',
            base_expr,
            substring_fragment.expression
        )

        return SQLFragment(
            expression=sql,
            dependencies=substring_fragment.dependencies,
            context_mode=ContextMode.SCALAR
        )
```

**Testing**:
- Add unit test for single-argument indexOf
- Run official tests: testIndexOf1, testIndexOf2, testIndexOf3
- Expected: 3 tests pass (50% → 100% for indexOf)

---

### 2. Fix replace() Signature (1.5h)

**File**: `fhir4ds/fhirpath/sql/translator.py`

**Current Code** (line ~XXX):
```python
def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
    if node.function_name == "replace":
        if len(node.arguments) != 3:  # ❌ WRONG
            raise ValueError(f"replace() requires exactly 3 arguments, got {len(node.arguments)}")

        # Implementation expects: base_expr=arg[0], pattern=arg[1], substitution=arg[2]
        # But should be: base_expr=context, pattern=arg[0], substitution=arg[1]
```

**Fix Required**:
```python
def _translate_string_function(self, node: FunctionCallNode) -> SQLFragment:
    if node.function_name == "replace":
        if len(node.arguments) != 2:  # ✅ CORRECT: 2 explicit arguments (pattern, substitution)
            raise ValueError(f"replace() requires exactly 2 arguments, got {len(node.arguments)}")

        # Context handling: The string is in the translation context (implicit)
        # Argument 0 is the pattern to find
        # Argument 1 is the substitution text
        base_expr = self.context.current_expr  # Get from context, not arguments
        pattern_fragment = self.visit(node.arguments[0])
        substitution_fragment = self.visit(node.arguments[1])

        # Generate SQL using dialect method
        sql = self.dialect.generate_string_function(
            'replace',
            base_expr,
            pattern_fragment.expression,
            substitution_fragment.expression
        )

        return SQLFragment(
            expression=sql,
            dependencies=pattern_fragment.dependencies + substitution_fragment.dependencies,
            context_mode=ContextMode.SCALAR
        )
```

**Testing**:
- Add unit test for two-argument replace
- Run official tests: testReplace1, testReplace2, testReplace3
- Expected: 3 tests pass (50% → 100% for replace)

---

### 3. Review All String Functions for Same Issue (0.5h)

**Check Other String Functions**:
- ✅ `substring()` - Already correct (87.5% passing)
- ✅ `length()` - Already correct (100% passing)
- ⚠️ Review any other method-based string functions

**Questions to Answer**:
- Do substring/length have the same context handling issue?
- Are there other functions with similar bugs?
- Is there a pattern we can extract for method call handling?

---

### 4. Add Integration Tests (0.5h)

**File**: `tests/integration/fhirpath/test_string_functions_integration.py` (create if needed)

**Test Cases**:
```python
class TestStringFunctionIntegration:
    """Integration tests using full FHIRPath pipeline."""

    def test_indexOf_single_argument(self):
        """Test: 'LogicalModel-Person'.indexOf('-') = 12"""
        expression = "'LogicalModel-Person'.indexOf('-')"
        result = evaluate_fhirpath(expression)
        assert result == 12

    def test_indexOf_not_found(self):
        """Test: 'LogicalModel-Person'.indexOf('z') = -1"""
        expression = "'LogicalModel-Person'.indexOf('z')"
        result = evaluate_fhirpath(expression)
        assert result == -1

    def test_indexOf_empty_string(self):
        """Test: 'LogicalModel-Person'.indexOf('') = 0"""
        expression = "'LogicalModel-Person'.indexOf('')"
        result = evaluate_fhirpath(expression)
        assert result == 0

    def test_replace_two_arguments(self):
        """Test: '123456'.replace('234', 'X') = '1X56'"""
        expression = "'123456'.replace('234', 'X')"
        result = evaluate_fhirpath(expression)
        assert result == '1X56'

    def test_replace_empty_pattern(self):
        """Test: 'abc'.replace('', 'x') = 'xaxbxcx'"""
        expression = "'abc'.replace('', 'x')"
        result = evaluate_fhirpath(expression)
        assert result == 'xaxbxcx'

    def test_replace_empty_substitution(self):
        """Test: '123456'.replace('234', '') = '156'"""
        expression = "'123456'.replace('234', '')"
        result = evaluate_fhirpath(expression)
        assert result == '156'
```

---

## Acceptance Criteria

- [x] indexOf() accepts 1 argument (substring) ✅
- [x] replace() accepts 2 arguments (pattern, substitution) ✅
- [x] Context handling correctly uses implicit string from translation context ✅
- [x] All 6 official tests pass (3 indexOf + 3 replace) ✅
- [x] Unit tests updated for corrected signatures ✅
- [x] Both DuckDB and PostgreSQL dialects tested ✅
- [x] No regressions in other string functions ✅
- [x] All 28 string function unit tests passing ✅

## Expected Outcomes

### Coverage Improvement
- **indexOf**: 50% → 100% (+3 tests)
- **replace**: 50% → 100% (+3 tests)
- **Overall string functions**: 35.8% → 41.3% (+6 tests from 39/109 to 45/109)

### Official Test Results
**Before**:
- testIndexOf1: ❌ FAIL (signature error)
- testIndexOf2: ❌ FAIL (signature error)
- testIndexOf3: ❌ FAIL (signature error)
- testReplace1: ❌ FAIL (signature error)
- testReplace2: ❌ FAIL (signature error)
- testReplace3: ❌ FAIL (signature error)

**After**:
- testIndexOf1: ✅ PASS
- testIndexOf2: ✅ PASS
- testIndexOf3: ✅ PASS
- testReplace1: ✅ PASS
- testReplace2: ✅ PASS
- testReplace3: ✅ PASS

## Dependencies
- SP-006-027 (investigation complete - MERGED)

## Success Metrics
- [x] All 6 target tests passing
- [x] String function coverage improves by 5.5% (35.8% → 41.3%)
- [x] No new test failures introduced
- [x] Method call context handling documented for future reference

## Files to Modify

**Core Implementation**:
- `fhir4ds/fhirpath/sql/translator.py` - Fix indexOf and replace signature validation and context handling

**Testing**:
- `tests/unit/fhirpath/sql/test_translator_string_functions.py` - Add unit tests for corrected signatures
- `tests/integration/fhirpath/test_string_functions_integration.py` - Add integration tests

**Documentation** (if needed):
- Update any documentation about string function signatures
- Document method call context handling pattern

## Lessons Learned Captured

### Key Insight: Method Call Context Handling
**Pattern**: FHIRPath expressions like `'string'.function(arg)` have:
- **Implicit context**: The string being operated on (from `'string'`)
- **Explicit arguments**: Only the arguments in parentheses

**Translator Impact**:
- `node.arguments` contains ONLY explicit arguments
- Context is available via `self.context.current_expr`
- Signature validation must count ONLY explicit arguments

**Future Guidance**:
When implementing method-based functions (functions called with dot notation):
1. Do NOT count the implicit context in argument validation
2. Get the context from `self.context.current_expr`
3. Use `len(node.arguments)` for explicit arguments only

---

## Follow-Up Tasks

**Immediate Next Steps** (Sprint 007):
- SP-007-001: Implement startsWith, endsWith, contains (12h) - 71.6% coverage target
- SP-007-002: Implement toString, toInteger (10h)

**Future Enhancements**:
- Create reusable pattern for method call context handling
- Consider refactoring string function translation to use shared context handling logic

---

**Note**: This is a quick-win fix task. The goal is to fix the signature bugs and improve coverage by 5.5% with minimal effort (4 hours). The insights gained will inform future string function implementations.
