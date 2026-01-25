#!/usr/bin/env python3
"""
Categorize FHIRPath test failures by error type and identify top patterns.
"""

import json
import re
from collections import defaultdict, Counter
from typing import Dict, List, Any
from pathlib import Path

def load_compliance_report(path: str) -> Dict[str, Any]:
    """Load the compliance report JSON."""
    with open(path) as f:
        return json.load(f)

def extract_error_details(result: Dict[str, Any]) -> tuple:
    """
    Extract error type and error message from a test result.

    Returns:
        tuple: (error_category, error_subtype, description)
    """
    if result.get('passed', False):
        return None, None, None

    error_msg = result.get('error_message', '')
    actual_result = result.get('actual_result', {})

    # Check if there's an error_type in the actual_result
    error_type = actual_result.get('error_type', 'Unknown')
    error = actual_result.get('error', '')

    # Categorize by error message and error type
    if 'Expected semantic failure' in error_msg:
        return 'semantic_validation', 'expected_semantic_failure', error_msg
    elif 'Expected valid expression with empty result set' in error_msg:
        return 'empty_result', 'expected_empty', error_msg
    elif 'Unexpected evaluation outcome' in error_msg:
        # This is a result logic mismatch - need to dig deeper
        return 'result_logic', 'unexpected_outcome', error_msg
    elif error_type == 'BinderException':
        return 'binder_error', 'binder_exception', error
    elif error_type == 'InvalidInputException':
        return 'invalid_input', 'invalid_input_exception', error
    elif error_type == 'ConversionException':
        return 'conversion_error', 'conversion_exception', error
    elif error_type == 'ValueError':
        return 'value_error', 'value_error', error
    elif error_type == 'parse':
        return 'parse_error', 'parse_error', error
    elif error_type == 'FHIRPathTranslationError':
        return 'translation_error', 'translation_error', error
    else:
        return 'unknown', error_type, error_msg

def categorize_failures(report: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """
    Categorize all failures by their root cause pattern.
    """
    failed_tests = []

    # Get all failed tests from the report
    # The report only has first 10 in failed_test_analysis, so we need to extract from raw results
    # But we don't have that. Let me parse the test output instead.

    return {}

def parse_test_output(log_path: str) -> List[Dict[str, Any]]:
    """
    Parse the test output log to extract all failure details.
    """
    import sys
    sys.path.insert(0, '/mnt/d/fhir4ds3')

    failures = []

    # First, let's run the tests again and capture all results
    from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner

    runner = EnhancedOfficialTestRunner(database_type='duckdb')
    runner.run_official_tests(max_tests=None)

    for result in runner.test_results:
        if not result.passed:
            failures.append({
                'name': result.name,
                'expression': result.expression,
                'error_message': result.error_message,
                'error_type': result.actual_result.get('error_type') if result.actual_result else None,
                'error': result.actual_result.get('error') if result.actual_result else None,
                'is_valid': result.actual_result.get('is_valid') if result.actual_result else None,
                'result': result.actual_result.get('result') if result.actual_result else None,
            })

    return failures

def analyze_pattern(failures: List[Dict]) -> List[Dict]:
    """
    Analyze failures to identify patterns by root cause.
    """
    patterns = defaultdict(lambda: {
        'count': 0,
        'tests': [],
        'error_types': Counter(),
        'examples': []
    })

    for failure in failures:
        error_msg = failure.get('error_message', '')
        error_type = failure.get('error_type', 'unknown')
        error = failure.get('error', '')

        # Categorize by root cause pattern
        pattern_key = None

        # Pattern 1: Semantic validation errors (should fail but don't)
        if 'Expected semantic failure but expression was accepted' in error_msg:
            pattern_key = 'semantic_validation: should_fail_but_passes'

        # Pattern 2: Binder errors - SQL column binding issues
        elif error_type == 'BinderException':
            if 'not found in FROM clause' in error:
                pattern_key = 'binder: column_not_found_in_from'
            elif 'No function matches' in error:
                pattern_key = 'binder: no_function_matches'
            elif 'Invalid LIST argument during lambda function binding' in error:
                pattern_key = 'binder: lambda_binding'
            else:
                pattern_key = f'binder: other'

        # Pattern 3: Result logic mismatches (wrong result type/value)
        elif 'Unexpected evaluation outcome' in error_msg:
            # Further categorize by what kind of mismatch
            result = failure.get('result')
            if result is not None:
                if isinstance(result, list):
                    if len(result) == 1:
                        pattern_key = 'result_logic: single_value_instead_of_empty'
                    else:
                        pattern_key = f'result_logic: got_{len(result)}_values'
                elif isinstance(result, bool):
                    pattern_key = 'result_logic: boolean_instead_of_empty'
                else:
                    pattern_key = f'result_logic: {type(result).__name__}_result'
            else:
                pattern_key = 'result_logic: none_result'

        # Pattern 4: Invalid input (malformed JSON, etc.)
        elif error_type == 'InvalidInputException':
            if 'Malformed JSON' in error:
                pattern_key = 'invalid_input: malformed_json'
            else:
                pattern_key = 'invalid_input: other'

        # Pattern 5: Conversion errors
        elif error_type == 'ConversionException':
            if 'Could not convert' in error:
                pattern_key = 'conversion: type_conversion_failed'
            else:
                pattern_key = 'conversion: other'

        # Pattern 6: Function signature errors
        elif error_type == 'ValueError':
            if 'requires exactly' in error and 'arguments' in error:
                pattern_key = 'function_signature: argument_count_mismatch'
            elif 'Unknown unary operator' in error:
                pattern_key = 'operator: unknown_unary_operator'
            else:
                pattern_key = f'value_error: {error[:50]}'

        # Pattern 7: Translation errors
        elif error_type == 'FHIRPathTranslationError':
            if 'Unknown FHIR type' in error:
                pattern_key = 'translation: unknown_fhir_type'
            else:
                pattern_key = 'translation: other'

        # Pattern 8: Expected empty result but got error
        elif 'Expected valid expression with empty result set' in error_msg:
            if error_type == 'BinderException':
                pattern_key = 'empty_result: binder_error_instead_of_empty'
            elif error_type == 'InvalidInputException':
                pattern_key = 'empty_result: invalid_input_instead_of_empty'
            else:
                pattern_key = f'empty_result: {error_type}_instead_of_empty'

        else:
            pattern_key = f'uncategorized: {error_type}'

        if pattern_key:
            patterns[pattern_key]['count'] += 1
            patterns[pattern_key]['error_types'][error_type] += 1

            # Keep first few examples per pattern
            if len(patterns[pattern_key]['examples']) < 3:
                patterns[pattern_key]['examples'].append({
                    'name': failure['name'],
                    'expression': failure['expression'],
                    'error': error[:200] if error else error_msg,
                })

            # Store all test names for reference
            patterns[pattern_key]['tests'].append(failure['name'])

    # Convert to sorted list
    sorted_patterns = []
    for key, data in patterns.items():
        sorted_patterns.append({
            'pattern': key,
            'count': data['count'],
            'error_types': dict(data['error_types']),
            'examples': data['examples'],
            'test_names': data['tests']
        })

    sorted_patterns.sort(key=lambda x: x['count'], reverse=True)
    return sorted_patterns

def main():
    """Main categorization workflow."""
    print("=" * 80)
    print("SP-101-003: FHIRPath Test Failure Categorization")
    print("=" * 80)
    print()

    print("Step 1: Running tests to capture all failures...")
    failures = parse_test_output(None)

    print(f"Step 2: Analyzing {len(failures)} failures...")
    patterns = analyze_pattern(failures)

    print()
    print("=" * 80)
    print("FAILURE PATTERNS ANALYSIS")
    print("=" * 80)
    print()

    # Print top patterns
    for i, pattern in enumerate(patterns[:15], 1):
        print(f"{i}. {pattern['pattern']}")
        print(f"   Count: {pattern['count']} tests")
        print(f"   Error types: {pattern['error_types']}")
        print(f"   Example tests:")
        for ex in pattern['examples'][:2]:
            print(f"     - {ex['name']}: {ex['expression']}")
            if ex['error']:
                print(f"       Error: {ex['error'][:100]}...")
        print()

    # Save categorization report
    report = {
        'total_failures': len(failures),
        'patterns': patterns,
        'top_3_patterns': patterns[:3],
        'timestamp': str(Path.cwd())
    }

    output_path = Path('/mnt/d/fhir4ds3/project-docs/plans/tasks/SP-101-003-categorization.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Categorization saved to: {output_path}")
    print()

    # Create markdown report
    md_path = Path('/mnt/d/fhir4ds3/project-docs/plans/tasks/SP-101-003-categorization.md')
    with open(md_path, 'w') as f:
        f.write("# SP-101-003: Failure Categorization Report\n\n")
        f.write(f"**Generated**: 2026-01-25\n\n")
        f.write(f"**Total Failures**: {len(failures)}\n\n")
        f.write("## Top 3 Patterns\n\n")

        for i, pattern in enumerate(patterns[:3], 1):
            f.write(f"### Pattern {i}: {pattern['pattern']}\n\n")
            f.write(f"- **Test Count**: {pattern['count']}\n")
            f.write(f"- **Error Types**: {', '.join(pattern['error_types'].keys())}\n\n")
            f.write("**Root Cause**:\n")
            f.write(f"- Description: {pattern['examples'][0]['error'] if pattern['examples'] else 'N/A'}\n\n")
            f.write("**Example Tests**:\n")
            for test in pattern['test_names'][:5]:
                f.write(f"- {test}\n")
            f.write(f"\n... and {pattern['count'] - 5} more\n\n")
            f.write("**Recommended Fix Approach**:\n")
            f.write(f"- To be determined\n\n")

        f.write("\n## All Patterns\n\n")
        for i, pattern in enumerate(patterns, 1):
            f.write(f"{i}. **{pattern['pattern']}**: {pattern['count']} tests\n")

    print(f"Markdown report saved to: {md_path}")

    return patterns

if __name__ == '__main__':
    main()
