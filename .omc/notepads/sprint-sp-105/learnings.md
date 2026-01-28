# Learnings - SP-105 Comparison Operators

## Temporal Literal Comparison Type Coercion

### Problem
The `_translate_temporal_literal_comparison_if_applicable` method was being called before visiting children, so the `temporal_info` attribute wasn't available on the raw AST nodes. This caused partial temporal comparisons (e.g., `@2018-03 < @2018-03-01`) to fall back to direct comparison instead of generating precision-aware CASE expressions.

### Solution
Enhanced the `_extract_temporal_info` method to handle both:
1. **Visited nodes** - Nodes that already have `temporal_info` attribute set by the `LiteralNodeAdapter`
2. **Raw AST nodes** - Nodes that need temporal info parsed directly from their text

Added helper methods:
- `_find_literal_node()`: Traverses TermExpression wrappers to find the actual literal node
- `_parse_temporal_literal_from_text()`: Parses temporal literals from text
- `_parse_date_literal_from_text()`: Parses date literals (@YYYY, @YYYY-MM, @YYYY-MM-DD)
- `_parse_time_literal_from_text()`: Parses time literals (@T10, @T10:30, @T10:30:00)
- `_parse_datetime_literal_from_text()`: Parses dateTime literals
- `_parse_partial_datetime_literal_from_text()`: Parses partial dateTime literals (@YYYYT, @YYYY-MMT)
- `_format_datetime_iso()`: Formats datetime for SQL
- `_format_time_iso()`: Formats time for SQL

### Key Insight
The visitor pattern creates adapters (LiteralNodeAdapter) that add attributes like `temporal_info`, but the operator node's `children` reference the raw EnhancedASTNode objects. To access temporal info before visiting children, we need to parse it directly from the node text.

### Test Results
- All 5 temporal comparison tests now pass
- All 11 type casting tests pass
- 20/20 comparison-related tests pass

## String Comparison Dialect Method

### Problem
The `_CastingDialect` test mock was missing the `extract_json_string` method, causing AttributeError when comparing JSON-extracted strings with string literals.

### Solution
Added `extract_json_string` method to the `_CastingDialect` test mock in `test_translator_type_casting.py`.

### Test Results
- All 11 type casting tests pass

## Syntax Error Fix

### Problem
Another worker had introduced a syntax error in `ast_extensions.py` with an incorrectly formatted regex pattern for duration literals.

### Solution
Fixed the regex pattern string by using double quotes instead of mixing single and double quotes incorrectly.

### Files Changed
1. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`:
   - Added `timedelta` to imports
   - Enhanced `_extract_temporal_info()` to parse temporal info from raw nodes
   - Added 7 new helper methods for temporal literal parsing

2. `/mnt/d/fhir4ds3/tests/unit/fhirpath/sql/test_translator_type_casting.py`:
   - Added `extract_json_string` method to `_CastingDialect` test mock

3. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser_core/ast_extensions.py`:
   - Fixed regex syntax error in duration literal parsing

## Comparison Operators Supported
- `<` (less than)
- `<=` (less than or equal)
- `>` (greater than)
- `>=` (greater than or equal)
- `=` (equals)
- `!=` (not equals)
- `~` (equivalent)
- `!~` (not equivalent)

## Type Coercion Scenarios
1. **JSON field vs typed literal**: Casts JSON VARCHAR to target type
2. **Typed literal vs JSON field**: Casts JSON VARCHAR to target type
3. **String literal vs string**: No casting needed (direct comparison)
4. **Temporal literals**: Precision-aware range-based comparison with CASE expressions

## Type Operations (is, as, ofType)

### Problem 1: FHIRPathExpression wrapper not handled in translate()
The `translate()` method expected an AST node with `node_type` attribute, but sometimes it received a `FHIRPathExpression` wrapper object instead, causing AttributeError.

### Solution 1
Added handling for `FHIRPathExpression` wrapper in `translate()` method to extract the actual AST using `get_ast()` before processing.

### Problem 2: Function call syntax (`.as(Type)`) parsed incorrectly
When type operations use function call syntax like `.as(Quantity)` instead of space syntax like ` as Quantity`, the parser categorizes them as TYPE_OPERATION nodes with text like `as()`. The `_extract_operation_and_type()` method in `TypeOperationNodeAdapter` only checked for:
- `ofType()` or `ofType(` pattern
- ` is ` (with space) pattern
- ` as ` (with space) pattern

This caused `.as(Quantity)` to fall through to the default `'is'` operation instead of `'as'`.

### Solution 2
Added checks for `as()` and `is()` function call syntax patterns:
```python
if text == 'as()' or 'as(' in text:
    target_type = self._extract_type_from_children(node)
    return 'as', target_type or 'Unknown'
if text == 'is()' or 'is(' in text:
    target_type = self._extract_type_from_children(node)
    return 'is', target_type or 'Unknown'
```

### Problem 3: value_expression not used for function call syntax
The `_translate_as_operation()` method used `node.children[0]` to get the expression to cast, but for function call syntax (`.as(Quantity)`), the value expression is stored in `node.value_expression` attribute (extracted from the parent's children by the `TypeOperationNodeAdapter`).

### Solution 3
Updated `_translate_as_operation()` to use `node.value_expression` if available:
```python
if hasattr(node, 'value_expression') and node.value_expression is not None:
    child_node = node.value_expression
elif node.children:
    child_node = node.children[0]
else:
    raise ValueError("as() operation requires an expression to cast")
```

### Problem 4: Missing datetime import
The `_format_datetime_iso()` method referenced `datetime` type but the import was missing.

### Solution 4
Added `from datetime import datetime` to translator.py imports.

### Files Changed
1. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`:
   - Added `datetime` to imports
   - Enhanced `translate()` to handle `FHIRPathExpression` wrapper
   - Updated `_translate_as_operation()` to use `value_expression` attribute

2. `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/parser_core/ast_extensions.py`:
   - Added `as()` and `is()` function call syntax pattern matching in `TypeOperationNodeAdapter._extract_operation_and_type()`

### Test Results
- All 9 complex type cast tests pass (PostgreSQL)
- All 8 TypeExpressionParsing tests pass
- All 5 is() operation error handling tests pass
- All 4 as() operation basic type tests pass
- All 3 ofType() operation basic type tests pass

### Key Insights
1. The FHIRPath parser wraps results in `FHIRPathExpression` objects - always call `get_ast()` to get the actual AST
2. Type operations can have two syntaxes: space (` as Type`) and function call (`.as(Type)`)
3. The AST structure differs between the two syntaxes:
   - Space syntax: `TypeExpression` node with operation in metadata
   - Function call syntax: `functionCall` node with TYPE_OPERATION category
4. For function call syntax, the value expression must be extracted from the parent's children
