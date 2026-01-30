# Sprint SP-109 Learnings

## Task SP-109-001: Type Functions - Unary Operator Precedence Fix

### Problem
The expression `-1.convertsToInteger()` was being parsed as `-(1.convertsToInteger())` instead of `(-1).convertsToInteger()`. This caused negative number type conversions to fail.

### Root Cause
The ANTLR grammar did not have a rule for unary operators with proper precedence. The unary minus `-` was treated as a binary operator in the `additiveExpression` rule, which has lower precedence than member invocation (`.`).

### Solution Implemented

#### 1. Grammar Changes (FHIRPath.g4)
- Added `unaryExpression` rule with HIGHER precedence than `termExpression`
- This ensures unary operators are evaluated before member invocation
- Fixed label naming conflict by renaming `invocationTerm` to `memberInvocationTerm` in expression rule
- Fixed escape sequence issue in STRING lexer rule

#### 2. ASTNodeAdapter Changes (ast_extensions.py)
- Updated `has_node_type_text()` to include new node types: `UnaryExpressionWrapper`, `UnaryPolarityTerm`, `MemberInvocationTerm`
- Updated `OPERATOR_EXPRESSION_TYPES` to use `UnaryPolarityTerm` instead of `PolarityExpression`
- Added special handling in `accept()` to unwrap `UnaryExpressionWrapper` to `UnaryPolarityTerm`
- Added `TermExpressionTerm` and `Invocation` to the list of wrapper nodes that should be unwrapped
- Fixed `_extract_function_name()` to handle both old and new grammar structures (direct Identifier child vs. Functn -> Identifier)

#### 3. Metadata Type Changes (metadata_types.py)
- Added `UnaryExpressionWrapper` to `OPERATOR` category for proper operator handling
- Removed `MemberInvocationTerm` from `FUNCTION_CALL` category (it's now CONDITIONAL or PATH_EXPRESSION)
- Added `MemberInvocationTerm` conditional logic (contains `(` → CONDITIONAL)

#### 4. ASTPathListener Changes (ASTPathListener.py)
- Updated `OPERATOR_EXPRESSION_TYPES` to use `UnaryPolarityTerm` instead of `PolarityExpression`

### Files Modified
1. `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar fix
2. `fhir4ds/main/fhirpath/parser_core/fhirpath_py/generated/*` - Regenerated parser files
3. `fhir4ds/main/fhirpath/parser_core/ast_extensions.py` - AST adapter changes
4. `fhir4ds/main/fhirpath/parser_core/metadata_types.py` - Metadata categorization
5. `fhir4ds/main/fhirpath/parser_core/fhirpath_py/ASTPathListener.py` - Listener updates

### Test Results
All test cases pass:
- `-1.convertsToInteger()` → `TRY_CAST((- 1) AS INTEGER)` ✓
- `-0.1.convertsToDecimal()` → `TRY_CAST((- 0.1) AS DECIMAL)` ✓
- `1.convertsToInteger()` → `TRY_CAST(1 AS INTEGER)` ✓
- `(-1).convertsToInteger()` → `TRY_CAST((- 1) AS INTEGER)` ✓

### Key Technical Discoveries
- Unary operators must be handled at the grammar level, not just in the AST processing
- Node type naming conflicts between grammar rules can cause parser generation errors
- The new grammar creates `UnaryExpressionWrapper` and `UnaryPolarityTerm` nodes that need special handling
- Wrapper nodes like `TermExpressionTerm` and `Invocation` must be unwrapped to avoid being treated as identifiers

## Task SP-109-002: Arithmetic Operators - Precedence Investigation

### Initial Problem Understanding (INCORRECT)
The task description mentioned:
- `-Patient.name.given.count()` fails due to precedence issues
- Need to fix unary polarity operator precedence

### Investigation Results

#### 1. Unary Precedence is Already CORRECT
- **Test Case**: `-Patient.name.given.count()`
- **Status**: PASSING ✓
- **Behavior**: Correctly negates the count result
- **AST Structure**: `PolarityExpression → InvocationExpression → ...`

#### 2. The `-1.convertsToInteger()` Case is Working as Specified
- **Expression**: `-1.convertsToInteger()`
- **Expected Behavior**: Should FAIL with execution error
- **Reason**: Interpreted as `-(1.convertsToInteger())`, which tries to negate a BOOLEAN
- **Test Status**: Tests marked as `invalid: execution` are CORRECTLY failing

#### 3. FHIRPath Spec Precedence Rules
According to FHIRPath R4 spec, precedence from highest to lowest:
1. Parentheses `()`
2. Literals and Member Invocation `.`
3. Unary operators `+`, `-`
4. Multiplicative `*`, `/`, `div`, `mod`
5. Additive `+`, `-`

This means `-1.convertsToInteger()` MUST be parsed as `-(1.convertsToInteger())`, NOT as `(-1).convertsToInteger()`.

#### 4. Incorrect Fix Attempted
I attempted to make `-1.convertsToInteger()` work like `(-1).convertsToInteger()` by:
1. Modifying the AST to rewrite the expression structure
2. Creating special handling in `OperatorNodeAdapter` and `PolarityExpression` handlers

**This was WRONG because**:
- It violated the FHIRPath specification
- It caused tests that should fail to pass
- It reduced compliance from 45.8% to 44.4%

### Corrected Understanding

The actual arithmetic operator failures (39 tests, 45.8% → 100% target) are likely due to:
1. **Decimal overflow/precision issues** - Large decimals causing overflow or precision loss
2. **Negative number comparisons** - Comparison logic issues with negative numbers
3. **Mixed type arithmetic** - Integer + Decimal operations, type coercion problems
4. **Edge cases** - Division by zero, infinity, NaN handling

### Key Learnings
- **ALWAYS verify test expectations against the FHIRPath specification**
- **Tests marked as `invalid: execution` are EXPECTED to fail** - they test error handling
- **Don't assume task descriptions are 100% accurate** - verify against actual test failures
- **Precedence rules are well-defined** - don't change them without careful consideration

### Recommended Approach for SP-109-002
1. **Identify the actual 39 failing tests** (not the `invalid: execution` ones)
2. **Categorize failures by type**:
   - Precision/overflow issues
   - Comparison issues
   - Type coercion issues
   - Edge cases
3. **Fix each category separately**
4. **Do NOT modify unary operator precedence** - it's working correctly

### Files Investigated
- `fhir4ds/main/fhirpath/parser_core/ast_extensions.py` - AST visitor and adapter logic
- `fhir4ds/main/fhirpath/parser_core/fhirpath_py/FHIRPath.g4` - Grammar definition
- `fhir4ds/main/fhirpath/sql/translator.py` - SQL translation logic
- `tests/compliance/fhirpath/official_tests.xml` - Test definitions
- `tests/integration/fhirpath/official_test_runner.py` - Test execution

### Conclusion
The SP-109-002 task description appears to be based on outdated or incorrect assumptions. The unary precedence issues mentioned have already been resolved (either in SP-109-001 or earlier sprints). The actual work needed is to investigate and fix the 39 specific arithmetic test failures, which are unrelated to unary precedence.
