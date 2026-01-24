# Sprint 008 – testObservations Investigation (SP-008-004)

## Context
- Scope covers the ten `testObservations` entries in `tests/compliance/fhirpath/official_tests.xml`.
- Goal: explain the four current failures (60.0% pass rate) and outline the fix strategy for SP-008-005.
- Data source: `tests/fixtures/sample_fhir_data/observation-example.xml` (Observation resource with `valueQuantity` only).

## Execution Summary
- Ran the enhanced runner against a filtered test set for both dialect targets to keep results focused.
- Command:
  ```bash
  python3 - <<'PY'
  import xml.etree.ElementTree as ET
  from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
  def load(group):
      tree = ET.parse('tests/compliance/fhirpath/official_tests.xml')
      return [
          {
              'name': test.get('name'),
              'expression': test.find('expression').text.strip(),
              'outputs': [
                  {'type': o.get('type'), 'value': o.get('value')}
                  for o in test.findall('output')
              ],
              'invalid': test.find('expression').get('invalid')
          }
          for grp in tree.getroot().findall('group')
          if grp.get('name') == group
          for test in grp.findall('test')
      ]
  tests = load('testObservations')
  for db in ['duckdb', 'postgresql']:
      runner = EnhancedOfficialTestRunner(db)
      runner.test_results = [runner._execute_single_test(t) for t in tests]
      report = runner._generate_compliance_report(sum(r.execution_time_ms for r in runner.test_results))
      print(db, report.passed_tests, report.failed_tests)
  PY
  ```
- Result: DuckDB 6/4, PostgreSQL 6/4 (parity confirmed).

## Failure Inventory
| Test | Expression | Expected Behaviour (official suite) | Observed Behaviour | Root Cause | Complexity |
|------|------------|--------------------------------------|--------------------|------------|------------|
| testPolymorphismB | Observation.valueQuantity.unit | Semantic error (invalid FHIRPath alias for `value[x]`) | Parser marks expression valid and runner treats absence of explicit output as failure | No semantic validation of choice-type aliases in `FHIRPathParser` (`fhir4ds/fhirpath/parser.py:156-191`) | Medium |
| testPolymorphismIsA3 | Observation.issued is instant | Empty result (example Observation omits `issued`) | Parser returns metadata; runner expects empty collection but only gets parse metadata | `evaluate()` stub does not execute AST or verify cardinality (`fhir4ds/fhirpath/parser.py:156-191`) | High |
| testPolymorphismAsB | (Observation.value as Period).unit | Semantic error (`Period` has no `unit`) | Parser marks expression valid instead of raising | Missing post-cast property validation against FHIR types (no hook into `TypeRegistry`) | Medium |
| testPolymorphismAsBFunction | Observation.value.as(Period).start | Empty result (no Period instances) | Parser returns metadata; runner cannot assert zero results | No evaluation layer to materialise type-filtered results | High |

## Root Cause Detail
- **Semantic validation gaps**  
  - `FHIRPathParser.parse` delegates to the `EnhancedFHIRPathParser`, which currently performs syntactic checks only.  
  - Choice-type aliases (`valueQuantity`) and post-cast paths (`… as Period`) are never validated against resource structure metadata.  
  - Impacted files: `fhir4ds/fhirpath/parser.py:124-154`, `fhir4ds/fhirpath/parser_core/enhanced_parser.py` (no linkage to `TypeRegistry`).

- **Evaluation stub instead of execution**  
  - `FHIRPathParser.evaluate` returns structural metadata (expression text, path components, AST shape) but never evaluates against the Observation fixture.  
  - Tests that rely on expected cardinality (0 results) therefore always fail because `_validate_test_result` receives a non-empty metadata dict.  
  - Impacted file: `fhir4ds/fhirpath/parser.py:156-194`.  
  - Similar behaviour occurs for both DuckDB and PostgreSQL because the parser is database-agnostic at this stage.

## Patterns and Recommendations
- **Introduce FHIR-aware path validation**  
  1. Load Observation structure definitions (or precomputed metadata) through `TypeRegistry` / `FHIRTypeSystem`.  
  2. During AST decoration, verify that each identifier or post-cast property is valid for the inferred base type.  
  3. Emit `FHIRPathParseError` (parser layer) or `FHIRPathTypeError` (evaluation layer) when invalid properties are accessed.

- **Unlock collection cardinality checks**  
  - Short term: extend `EnhancedOfficialTestRunner._validate_test_result` to honour expected empty collections by accepting the current metadata response when `expected_count == 0`.  
  - Long term: implement actual evaluation via `FHIRPathEvaluationEngine` (`fhir4ds/fhirpath/evaluator/engine.py`) so that `evaluate()` returns resolved values and type-filtered collections.

- **Ensure polymorphic handling parity**  
  - Add dedicated tests around `Observation.value[x]` and `ofType()/as()` conversions once evaluation exists.  
  - Validate across both dialects once translator emits SQL fragments.

## Recommended Success Criteria for SP-008-005
1. Parser rejects `Observation.valueQuantity.unit` and `(Observation.value as Period).unit` with clear semantic errors.  
2. Evaluation workflow (temporary or final) can demonstrate that `Observation.issued is instant` and `Observation.value.as(Period).start` return empty collections against the sample resource.  
3. Updated official-suite harness recognises expected-empty results without manual intervention.  
4. Regression tests exercise polymorphic navigation across both DuckDB and PostgreSQL dialect contexts.

## Risks & Dependencies
- Requires reliable access to FHIR structure metadata (StructureDefinitions or curated registry).  
- Evaluation updates will depend on the AST-to-SQL translator (PEP-003) or an interim in-memory evaluator.  
- Tight coupling with compliance runner; changes must keep DuckDB/PostgreSQL parity.

## Status
- Investigation complete on 2025-10-10.  
- Four failures documented with root causes, complexity tags, and remediation guidance prepared for SP-008-005.
