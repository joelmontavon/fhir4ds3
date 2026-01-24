# Task: Debug Type Function Official Test Mismatch

**Task ID**: SP-006-028 | **Sprint**: 006 | **Estimate**: 10h | **Priority**: Critical
**Status**: ✅ COMPLETE
**Completed**: 2025-10-05
**Actual Effort**: 6h

## Overview
Investigate why `is()`, `as()`, and `ofType()` functions pass unit tests but fail official FHIRPath tests with "Unknown or unsupported function" errors.

## Context from SP-006-021

**Implementation Status**:
- ✅ `is()` implemented in SP-006-005 (commit 9580365, merged to main)
- ✅ `as()` implemented in SP-006-006 (merged to main)
- ✅ `ofType()` implemented in SP-006-007 (merged to main)
- ✅ Unit tests passing: 26/26 for `is()`, similar coverage for `as()` and `ofType()`

**Official Test Status**:
- 🔴 94 failed tests reporting "Unknown or unsupported function: is"
- 🔴 Type functions category: 12.1% coverage (13/107 tests)
- 🔴 Expected: 70%+ coverage given implementations

**The Mystery**:
- Unit tests: "Function works perfectly" ✅
- Official tests: "Function doesn't exist" ❌
- **Question**: What's the difference between how unit tests and official tests call these functions?

## Root Cause Investigation Steps

### 1. Compare Test Invocation Patterns (3h)

**Objective**: Understand how unit tests vs official tests invoke type functions.

**Unit Test Analysis**:
```python
# Review: tests/unit/fhirpath/sql/test_translator_type_operations.py
# How are unit tests calling is()?
# Example patterns from unit tests:
# - expr = "5 is Integer"
# - expr = "Patient.name is String"
# - expr = "Observation.value is Quantity"
```

**Official Test Analysis**:
```bash
# Extract all failed is() test expressions
grep -B 2 "Unknown or unsupported function: is" translation_report_all_expressions.json

# Compare patterns:
# - "Observation.value.is(Quantity)" vs "Observation.value is Quantity"
# - "@2015.is(Date)" vs "@2015 is Date"
# - Parentheses usage differences
# - Type specifier capitalization
```

**Questions to Answer**:
- Do official tests use `is()` as a function call vs operator syntax?
- Are type specifiers different (e.g., "FHIR.Integer" vs "Integer")?
- Are there namespace qualifications in official tests?
- Do official tests use parentheses differently?

### 2. Review Parser/AST Adapter Handling (3h)

**Objective**: Verify parser correctly handles both invocation patterns.

**Check Parser Output**:
```python
# Test both syntaxes through parser
from fhir4ds.fhirpath.parser import parse_fhirpath

# Syntax 1: Operator (what unit tests use)
ast1 = parse_fhirpath("5 is Integer")
print(f"AST for '5 is Integer': {ast1}")

# Syntax 2: Function call (what official tests might use)
ast2 = parse_fhirpath("5.is(Integer)")
print(f"AST for '5.is(Integer)': {ast2}")

# Are both producing TypeOperation nodes?
# Are both being handled by visit_type_operation()?
```

**Review AST Adapter**:
- `fhir4ds/fhirpath/ast/adapter.py` - TypeExpression handling (SP-006-001)
- Does adapter handle both `is` operator and `is()` function call?
- Are type specifiers being extracted correctly from both patterns?

**Review Translator**:
- `fhir4ds/fhirpath/sql/translator.py` - `visit_type_operation()` method
- Does translator expect specific AST node structure?
- Is function name matching case-sensitive?

### 3. Examine Official Test Data Format (2h)

**Objective**: Understand how official tests are structured and invoked.

**Review Integration Test**:
```python
# File: tests/integration/fhirpath/test_real_expressions_integration.py
# Function: test_all_official_expressions_duckdb

# How are official test expressions loaded?
# What preprocessing happens before execution?
# Are expressions being modified during loading?
```

**Check Test Data File**:
```bash
# Find official test data
find . -name "*official*" -o -name "*fhirpath*test*.json"

# Review structure of failing test cases
# - Are expressions stored as-is or transformed?
# - Are there metadata fields affecting interpretation?
```

### 4. Trace Execution Path (2h)

**Objective**: Follow a failing official test through the entire pipeline.

**Add Debug Logging**:
```python
# In translator.py visit_type_operation():
def visit_type_operation(self, node):
    print(f"DEBUG: visit_type_operation called")
    print(f"  Node type: {type(node)}")
    print(f"  Operation: {getattr(node, 'operation', 'N/A')}")
    print(f"  Children: {getattr(node, 'children', 'N/A')}")
    # ... existing code ...
```

**Run Single Failing Test**:
```python
# Create minimal reproduction
def test_is_function_official_pattern():
    """Reproduce exact pattern from failing official test."""
    # Use exact expression from translation_report_all_expressions.json
    expr = "Observation.value.is(Quantity)"  # Or whatever pattern fails

    # Run through full pipeline
    result = translate_and_execute(expr, test_data)

    # Observe where it fails
```

**Expected Outcomes**:
- Identify exact point where "Unknown or unsupported function" error is raised
- Determine if error comes from parser, adapter, or translator
- Understand what causes function to be "unknown" despite implementation

## Hypotheses to Test

### Hypothesis 1: Syntax Variant Not Supported
**Theory**: Official tests use `value.is(Type)` but we only support `value is Type`

**Test**:
```python
# Does parser handle both?
parse_fhirpath("x is String")  # Operator syntax
parse_fhirpath("x.is(String)") # Function call syntax
```

**Fix** (if true): Update parser/adapter to handle function call syntax

### Hypothesis 2: Type Namespace Issues
**Theory**: Official tests use qualified names like `FHIR.Integer` vs `Integer`

**Test**:
```python
# Check for namespace prefixes in failed tests
grep "is(FHIR\." translation_report_all_expressions.json
grep "is(System\." translation_report_all_expressions.json
```

**Fix** (if true): Update type resolution to handle namespaces

### Hypothesis 3: Case Sensitivity
**Theory**: Function name matching is case-sensitive ("is" vs "Is" vs "IS")

**Test**:
```python
# Check translator function dispatch
# Is function name lookup case-sensitive?
```

**Fix** (if true): Make function name matching case-insensitive

### Hypothesis 4: Node Type Mismatch
**Theory**: Parser produces different AST node type than translator expects

**Test**:
```python
# What node type does parser produce?
ast = parse_fhirpath("x is Integer")
print(type(ast))  # TypeOperation? FunctionCall? Something else?

# What node types does visit_type_operation() accept?
```

**Fix** (if true): Update visitor to handle additional node types

## Acceptance Criteria

- [x] Root cause identified for "Unknown or unsupported function: is" errors
- [x] Difference between unit test and official test patterns documented
- [x] Reproduction test case created demonstrating the issue
- [x] Fix approach determined and validated
- [x] Estimated effort for implementing fix

## Expected Outcomes

### Most Likely: Parser/Adapter Gap
The parser or AST adapter doesn't handle the specific syntax pattern used by official tests.

**Deliverable**:
- Documentation of unsupported syntax pattern
- Parser/adapter enhancement needed
- Estimated effort: 6-8h

### Alternative: Translation Logic Issue
The translator's function dispatch doesn't recognize certain invocation patterns.

**Deliverable**:
- Documentation of dispatch logic gap
- Translator enhancement needed
- Estimated effort: 4-6h

### Least Likely: Test Framework Issue
The integration test framework is preprocessing expressions incorrectly.

**Deliverable**:
- Documentation of test framework bug
- Test framework fix needed
- Estimated effort: 2-4h

## Deliverables

1. **Analysis Report** (`SP-006-028-type-function-mismatch-analysis.md`):
   - Exact syntax patterns in failing official tests
   - Comparison with unit test patterns
   - Root cause identification
   - Execution trace showing failure point

2. **Reproduction Test** (`tests/investigation/test_type_function_official_pattern.py`):
   - Minimal test reproducing the exact official test pattern
   - Currently failing (to be fixed in follow-up task)

3. **Fix Proposal**:
   - Detailed description of required changes
   - Code locations to modify
   - Estimated effort
   - Recommended follow-up task

## Dependencies
- SP-006-005, SP-006-006, SP-006-007 (type function implementations)
- SP-006-021 (coverage analysis identifying the issue)

## Success Metrics
- [x] Root cause identified with 100% confidence
- [x] Reproduction test created that fails in exact same way as official tests
- [x] Fix approach validated (manually tested or prototyped)
- [x] Clear path to 70%+ type function coverage identified

## Files to Review
- `fhir4ds/fhirpath/parser.py` - FHIRPath parser
- `fhir4ds/fhirpath/ast/adapter.py` - AST adapter (TypeExpression handling)
- `fhir4ds/fhirpath/sql/translator.py` - SQL translator (visit_type_operation)
- `tests/integration/fhirpath/test_real_expressions_integration.py` - Official test runner
- `translation_report_all_expressions.json` - Failed test data

## Files to Create
- `project-docs/plans/tasks/SP-006-028-type-function-mismatch-analysis.md`
- `tests/investigation/test_type_function_official_pattern.py`

## Follow-Up Tasks (to be created based on findings)
- ~~SP-007-00X: Fix parser to handle official test syntax (if applicable)~~ - NOT NEEDED
- ~~SP-007-00Y: Fix AST adapter type handling (if applicable)~~ - Future refactor (SP-007-XXX)
- **SP-006-029**: Fix translator function dispatch (IMMEDIATE - 4-6h effort)

---

## Investigation Results

**ROOT CAUSE IDENTIFIED**: ✅

The AST adapter converts ALL type function invocations (both operator and function call syntax) to `FunctionCallNode` instead of `TypeOperationNode`. The translator only handles type functions in `visit_type_operation()`, not in `visit_function_call()`, causing all parsed expressions to fail with "Unknown or unsupported function" errors.

**Why Unit Tests Passed**:
Unit tests created `TypeOperationNode` objects directly, bypassing the parser/adapter pipeline and calling `visit_type_operation()` directly.

**Files Created**:
1. ✅ `project-docs/plans/tasks/SP-006-028-type-function-mismatch-analysis.md` - Comprehensive root cause analysis
2. ✅ `tests/investigation/test_type_function_official_pattern.py` - Reproduction test suite
3. ✅ `work/debug_type_function_syntax.py` - Debug script validating root cause

**Fix Recommendation**:
Implement SP-006-029 to add type function handlers to `visit_function_call()` method (Hybrid Approach - immediate fix + future refactor).

**Estimated Impact**:
- Type functions category: 12.1% → 70%+ (94 failing tests fixed)
- Overall coverage: 53.5% → 63.6%+

---

**Task Complete**: 2025-10-05
**Analysis Report**: See `SP-006-028-type-function-mismatch-analysis.md` for full details
