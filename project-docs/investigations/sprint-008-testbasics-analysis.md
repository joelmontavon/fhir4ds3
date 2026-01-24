# Sprint 008 – testBasics Investigation (SP-008-005)

## Context
- Scope covers the seven `testBasics` entries in `tests/compliance/fhirpath/official_tests.xml`.
- Goal: explain the three current failures (57.1 % pass rate) and define the remediation approach for SP-008-006.
- Data source: `tests/fixtures/sample_fhir_data/patient-example.xml` (Patient resource used across the group).

## Execution Summary
- Filtered the official suite to the `testBasics` group and executed the enhanced runner for both dialect targets.
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
              'inputfile': test.get('inputfile'),
              'invalid': test.find('expression').get('invalid')
          }
          for grp in tree.getroot().findall('group')
          if grp.get('name') == group
          for test in grp.findall('test')
      ]
  tests = load('testBasics')
  for db in ['duckdb', 'postgresql']:
      runner = EnhancedOfficialTestRunner(db)
      runner.test_results = [runner._execute_single_test(t) for t in tests]
      report = runner._generate_compliance_report(sum(r.execution_time_ms for r in runner.test_results))
      print(db, report.passed_tests, report.failed_tests)
  PY
  ```
- Result: DuckDB 4/3, PostgreSQL 4/3 (parity confirmed).

## Failure Inventory
| Test | Expression | Expected Behaviour (official suite) | Observed Behaviour | Root Cause | Complexity |
|------|------------|--------------------------------------|--------------------|------------|------------|
| testSimpleNone | `name.suffix` | Valid navigation should yield empty collection (suffix not populated) | Parser returns metadata; runner classifies empty expected outputs as failure | `_validate_test_result` misinterprets zero-output expectations and `evaluate()` never materialises collections | Medium |
| testSimpleFail | `name.given1` | Semantic error (no `given1` element on HumanName) | Parser marks expression valid; runner therefore flags mismatch | Missing structure-definition validation for element names in `FHIRPathParser.parse` | Medium |
| testSimpleWithWrongContext | `Encounter.name.given` | Semantic error (Patient example, Encounter root invalid) | Parser treats cross-resource navigation as valid | No context-aware type validation linking test input resource to allowed roots | High |

## Root Cause Detail
- **Harness assumption about empty outputs**  
  - `_validate_test_result` assumes missing expected outputs signal an intentional failure case; official `testSimpleNone` instead expects an empty result set from a valid path.  
  - Because `FHIRPathParser.evaluate` only emits parse metadata, the harness has no way to differentiate “valid + empty collection” from “should fail”.  
  - A short-term mitigation is to treat tests without outputs and without an `invalid` flag as success when parsing succeeds; long-term fix is to integrate real evaluation (e.g., `fhir4ds.fhirpath.evaluator.engine`) so the runner can assert cardinality.

- **Lack of semantic validation**  
  - `FHIRPathParser.parse` delegates to the enhanced parser, which currently checks syntax only.  
  - Choice/component validation against StructureDefinitions is absent, so typos like `given1` slip through.  
  - Impacts both DuckDB/PostgreSQL equally because parser is database-agnostic.

- **Missing context binding for root types**  
  - Official suite supplies `inputfile="patient-example.xml"`, implying Patient context.  
  - The parser does not tie evaluation context to input resource type, so expressions starting with `Encounter` are not rejected.  
  - Future translator/evaluator work must carry resource-type context through parsing and validation.

## Patterns and Recommendations
- Introduce a context-aware validation layer that loads element metadata from the FHIR type registry before marking expressions as valid. This should handle both intra-resource element checks (`name.given1`) and cross-resource root validation (`Encounter.…` in Patient scope).
- Update the enhanced runner to interpret the `invalid` attribute from the XML. If `invalid` is absent and the parser succeeds, treat zero expected outputs as a pass until real evaluation exists. Pair this change with unit coverage to prevent regressions.
- Prioritise wiring `FHIRPathParser.evaluate` to the in-memory evaluator (or a thin stub that at least returns actual element collections) so foundational tests can assert real results ahead of AST-to-SQL execution.

## Recommended Success Criteria for SP-008-006
1. Parser rejects `name.given1` and `Encounter.name.given` with explicit semantic errors derived from FHIR structure metadata.
2. Official test runner interprets zero-output expectations correctly (no false failures for valid-but-empty navigations).
3. Evaluation path returns concrete values or cardinalities so basic navigation results can be asserted prior to SQL translation.
4. DuckDB and PostgreSQL remain in lockstep once semantic validation is introduced (tests continue to report identical pass/fail counts).

## Risks & Dependencies
- Requires authoritative structure-definition data (FHIR R4 metadata set) or an interim curated registry to power semantic checks.
- Runner adjustments must coexist with future full evaluation to avoid masking legitimate failures.
- Semantic validation/Context binding will affect other official groups; coordinate with SP-008-006 to stage incremental roll-out.
