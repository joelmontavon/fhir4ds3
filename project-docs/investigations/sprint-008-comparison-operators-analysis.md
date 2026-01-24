# Sprint 008 – Comparison Operator Investigation (SP-008-007)

## Context
- Scope: all comparison-focused official FHIRPath groups – `testLessThan`, `testLessOrEqual`, `testGreaterThan`, and `testGreatorOrEqual`.
- Objective: explain the uniform 88.9 % pass rate (24/27) by documenting the 12 failing cases and outlining implementation guidance for SP-008-008.
- Data source: `tests/compliance/fhirpath/official_tests.xml`; analysis performed against the current AST-to-SQL translator.

## Execution Summary
- Filtered official tests to the four comparison groups and translated each expression to SQL to inspect the emitted operator and literal handling.
- Command:
  ```bash
  python3 - <<'PY'
  import xml.etree.ElementTree as ET
  from pathlib import Path
  from fhir4ds.fhirpath.parser import FHIRPathParser
  from fhir4ds.fhirpath.sql import ASTToSQLTranslator, convert_enhanced_ast_to_fhirpath_ast
  from fhir4ds.dialects.duckdb import DuckDBDialect

  parser = FHIRPathParser()
  translator = ASTToSQLTranslator(DuckDBDialect(), "Patient")
  tree = ET.parse(Path("tests/compliance/fhirpath/official_tests.xml"))

  for group_name in ["testLessThan", "testLessOrEqual", "testGreaterThan", "testGreatorOrEqual"]:
      group = next(g for g in tree.getroot().findall("group") if g.get("name") == group_name)
      for test in group.findall("test"):
          name = test.get("name")
          if not name.endswith(("23", "24", "25")):
              continue
          expr = test.find("expression").text.strip()
          enhanced = parser.parse(expr).get_ast()
          sql = translator.translate(convert_enhanced_ast_to_fhirpath_ast(enhanced))[-1].expression
          print(group_name, name, expr, "=>", sql)
  PY
  ```
  - Translator always emitted `!=` for the operator token, confirming an upstream mapping issue.
  - The 12 failing expressions all compare partial temporals (month-only dates, minute-only times) against higher-precision values; FHIRPath expects an indeterminate (`null`) result, yet the translator produces a non-null boolean via string inequality.
- Confirmed that no database-specific logic is triggered – output is identical for DuckDB and PostgreSQL because all literals are treated as plain strings.

## Failure Inventory
| Group | Test | Expression | Expected (FHIRPath) | Observed SQL | Root Cause | Complexity |
|-------|------|------------|----------------------|--------------|------------|------------|
| testLessThan | testLessThan23 | `@2018-03 < @2018-03-01` | `null` (precision mismatch) | `'@2018-03' != '@2018-03-01'` | Missing temporal precision handling + operator decoding | High |
| testLessThan | testLessThan24 | `@2018-03-01T10:30 < @2018-03-01T10:30:00` | `null` | `'@2018-03-01T10:30' != '@2018-03-01T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testLessThan | testLessThan25 | `@T10:30 < @T10:30:00` | `null` | `'@T10:30' != '@T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testLessOrEqual | testLessOrEqual23 | `@2018-03 <= @2018-03-01` | `null` | `'@2018-03' != '@2018-03-01'` | Missing temporal precision handling + operator decoding | High |
| testLessOrEqual | testLessOrEqual24 | `@2018-03-01T10:30 <= @2018-03-01T10:30:00` | `null` | `'@2018-03-01T10:30' != '@2018-03-01T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testLessOrEqual | testLessOrEqual25 | `@T10:30 <= @T10:30:00` | `null` | `'@T10:30' != '@T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testGreaterThan | testGreaterThan23 | `@2018-03 > @2018-03-01` | `null` | `'@2018-03' != '@2018-03-01'` | Missing temporal precision handling + operator decoding | High |
| testGreaterThan | testGreaterThan24 | `@2018-03-01T10:30 > @2018-03-01T10:30:00` | `null` | `'@2018-03-01T10:30' != '@2018-03-01T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testGreaterThan | testGreaterThan25 | `@T10:30 > @T10:30:00` | `null` | `'@T10:30' != '@T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testGreatorOrEqual | testGreatorOrEqual23 | `@2018-03 >= @2018-03-01` | `null` | `'@2018-03' != '@2018-03-01'` | Missing temporal precision handling + operator decoding | High |
| testGreatorOrEqual | testGreatorOrEqual24 | `@2018-03-01T10:30 >= @2018-03-01T10:30:00` | `null` | `'@2018-03-01T10:30' != '@2018-03-01T10:30:00'` | Missing temporal precision handling + operator decoding | High |
| testGreatorOrEqual | testGreatorOrEqual25 | `@T10:30 >= @T10:30:00` | `null` | `'@T10:30' != '@T10:30:00'` | Missing temporal precision handling + operator decoding | High |

## Root Cause Detail
1. **Operator token lost in AST adapter**  
   - `EnhancedFHIRPathParser` represents `<`, `<=`, `>`, and `>=` using the `InequalityExpression` node type.  
   - `ASTAdapter._infer_operator_from_node_type()` hard-codes that node type to `"!="` (`fhir4ds/fhirpath/sql/ast_adapter.py:331-346`), so every relational operator is emitted as inequality.  
   - Result: downstream translator never generates the intended comparator, masking ordering semantics and forcing boolean results where FHIRPath expects `null`.

2. **FHIR literal typing gaps**  
   - `_infer_literal_value_type()` (`fhir4ds/fhirpath/sql/ast_adapter.py:148-202`) falls back to `"string"` for any literal it does not recognise.  
   - Temporal literals – including partial month (`@2018-03`), partial datetime (`@2018-03-01T10:30`), and partial time (`@T10:30`) – therefore become plain strings without precision metadata.  
   - Translator consequently calls the string branch in `visit_literal()` (`fhir4ds/fhirpath/sql/translator.py:470-507`) instead of the dialect hooks for `DATE`, `TIMESTAMP`, or `TIME`, preventing any chance of precision-aware comparison.

3. **No representation of precision ranges**  
   - FHIRPath defines comparisons on partial temporals in terms of overlapping ranges. The current translator has no facility to represent start/end bounds, nor a way to surface `null` when ranges overlap.  
   - Even after correcting the operator token, the system will continue to emit `TRUE/FALSE` because both operands are naive strings. End-state requires range generation (e.g., `[start, end)` tuples) and SQL that yields `NULL` when intervals overlap.

## Patterns and Recommendations
- **Operator recovery (short-term, prerequisite for SP-008-008)**  
  1. Enrich `EnhancedASTNode` conversion with token context – slice the original expression using child node offsets or inspect `node.source_text` once populated.  
  2. Extend `_infer_operator_from_node_type()` to detect the actual symbol for `InequalityExpression`, populating the translator node with `<`, `<=`, `>`, or `>=` as appropriate.

- **Temporal literal typing (short-term)**  
  - Introduce regex-based detection for FHIR date, dateTime, and time literals (including partial precisions) inside `_infer_literal_value_type()`.  
  - Emit dedicated literal types (`date`, `datetime`, `time`, plus precision metadata) so `visit_literal()` can hand off to dialect hooks. Provide unit coverage around month-only, minute-only, and fractional-second cases.

- **Precision-aware comparison (core of SP-008-008)**  
  - Define a helper (e.g., `TemporalRange` dataclass) that derives `start`/`end` instants from a parsed FHIR literal based on precision.  
  - Augment translator comparison logic to generate SQL akin to:
    ```sql
    CASE
      WHEN upper(left_range) <= lower(right_range) THEN TRUE
      WHEN lower(left_range) >= upper(right_range) THEN FALSE
      ELSE NULL
    END
    ```
    where `lower/upper` use dialect-specific casting.  
  - Ensure identical behaviour in DuckDB and PostgreSQL; add unit + integration coverage executing generated SQL.

- **Harness alignment**  
  - Update compliance harness expectations to assert `NULL` results explicitly once comparison semantics exist, preventing the current “metadata == pass” blind spot.

## Additional Observations
- Correcting operator decoding exposes broader inaccuracies: 46 of 108 comparison tests currently rely on the `!=` fallback. Once evaluation logic inspects actual result values, these will surface as failures unless SP-008-008 addresses them.  
- The enhanced compliance runner (`tests/integration/fhirpath/official_test_runner.py`) presently treats the metadata returned by `FHIRPathParser.evaluate()` as success, so it cannot detect these semantic issues. Full evaluation (either via the new SQL pipeline or the in-memory evaluator) must be integrated before closing SP-008-008.

## Next Steps
1. Implement operator token recovery in `ASTAdapter` and add regression tests covering `<`, `<=`, `>`, and `>=`.  
2. Extend literal typing to classify FHIR temporals with precision metadata, then surface that through `LiteralNode`.  
3. Design and implement precision-aware comparison SQL (including range helpers and dialect hooks) as part of SP-008-008.  
4. Update the compliance harness to assert `NULL` outcomes and add cross-database integration tests ensuring DuckDB/PostgreSQL parity.
