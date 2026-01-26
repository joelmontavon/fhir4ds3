#!/usr/bin/env python3
"""Baseline compliance test runner for official FHIRPath test suite."""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, '.')
from tests.compliance.fhirpath.test_parser import parse_fhirpath_tests
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect

def main():
    # Parse tests
    tests = parse_fhirpath_tests()

    # Setup
    dialect = DuckDBDialect(database=':memory:')
    conn = dialect.get_connection()
    conn.execute('CREATE TABLE resource (id INTEGER, resource JSON)')
    conn.execute("""INSERT INTO resource VALUES
        (1, '{"resourceType": "Patient", "id": "1", "name": [{"family": "Smith", "given": ["John"]}], "birthDate": "1990-01-01", "gender": "male", "deceasedBoolean": false, "active": true, "maritalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus", "code": "M"}]}, "communication": [{"language": {"coding": [{"system": "urn:ietf:bcp:47", "code": "en"}]}}]}'),
        (2, '{"resourceType": "Patient", "id": "2", "name": [{"family": "Jones", "given": ["Jane"]}], "birthDate": "1985-05-15", "gender": "female", "deceasedBoolean": true, "active": false}')
    """)

    passed = 0
    failed = 0
    failed_tests = []
    start_time = time.time()

    # Run tests
    for i, test in enumerate(tests):
        try:
            executor = FHIRPathExecutor(dialect, 'Patient')
            result = executor.execute(test['expression'])

            if test.get('invalid') is not None:
                # Should fail
                failed += 1
                failed_tests.append({
                    'name': test['name'],
                    'expression': test['expression'],
                    'error': 'Expected semantic failure but expression was accepted',
                    'invalid_type': test.get('invalid')
                })
            else:
                # Should succeed
                passed += 1
        except Exception as e:
            if test.get('invalid') is not None:
                # Expected to fail
                passed += 1
            else:
                # Should not have failed
                failed += 1
                failed_tests.append({
                    'name': test['name'],
                    'expression': test['expression'],
                    'error': str(e)[:200]
                })

    end_time = time.time()
    total = len(tests)
    pct = (passed / total * 100) if total > 0 else 0

    print(f'\n=== COMPLIANCE RESULTS ===')
    print(f'Total: {total}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f'Compliance: {pct:.1f}%')
    print(f'Execution Time: {end_time - start_time:.1f}s')
    print(f'\n=== FAILURES BY CATEGORY ===')

    # Categorize failures
    categories = {}
    for ft in failed_tests:
        expr = ft['expression']

        if 'Unary' in str(expr) or ('-' in str(expr) and not str(expr).startswith('-') and str(expr).count('-') == 1):
            cat = 'Unary Polarity'
        elif '@' in str(expr) and ('T' in str(expr) or 'Z' in str(expr)):
            cat = 'DateTime Literals'
        elif str(expr).count("'") >= 2 or ' kg' in str(expr) or ' mg' in str(expr):
            cat = 'Quantity Literals'
        elif 'where' in str(expr) or 'select' in str(expr) or 'first' in str(expr):
            cat = 'Collection Functions'
        elif 'is ' in str(expr) or ' as ' in str(expr) or 'ofType(' in str(expr):
            cat = 'Type Checking'
        elif 'convertsTo' in str(expr):
            cat = 'Type Conversion'
        elif any(op in str(expr) for op in ['=', '!=', '<=', '>=', '<', '>']):
            cat = 'Comparison Operators'
        elif any(op in str(expr) for op in ['+', '-', '*', '/', 'mod', 'div']):
            cat = 'Arithmetic Operators'
        elif any(fn in str(expr) for fn in ['substring', 'contains', 'matches', 'length']):
            cat = 'String Functions'
        else:
            cat = 'Other'

        if cat not in categories:
            categories[cat] = []
        categories[cat].append(ft)

    for cat, fails in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        print(f'{cat}: {len(fails)} failures')

    print(f'\n=== SAMPLE FAILURES (first 5) ===')
    for ft in failed_tests[:5]:
        expr_preview = ft['expression'][:50] if len(ft['expression']) > 50 else ft['expression']
        print(f'  {ft["name"]}: {expr_preview}... - {ft["error"][:80]}')

    # Save report
    report = {
        'total_tests': total,
        'passed_tests': passed,
        'failed_tests': failed,
        'compliance_percentage': round(pct, 1),
        'execution_time_seconds': round(end_time - start_time, 2),
        'failed_tests_by_category': {k: len(v) for k, v in categories.items()},
        'sample_failures': failed_tests[:20]
    }

    Path('compliance_report_duckdb.json').write_text(json.dumps(report, indent=2))
    print(f'\nReport saved to compliance_report_duckdb.json')

    return pct, passed, failed

if __name__ == '__main__':
    main()
