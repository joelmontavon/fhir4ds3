# Task: Performance Benchmarking
**Task ID**: SP-006-024 | **Sprint**: 006 | **Estimate**: 8h | **Priority**: High
**Status**: ⏳ Pending

## Overview
Benchmark translation performance for all new functions to ensure <10ms target maintained.

## Acceptance Criteria
- [ ] Average translation time: <10ms per expression
- [ ] Type functions: <10ms
- [ ] Collection functions: <15ms (acceptable for complex operations)
- [ ] Math functions: <5ms (simple operations)
- [ ] String functions: <10ms
- [ ] Performance report generated

## Dependencies
SP-006-023

**Phase**: 5 - Integration and Validation

## Benchmarking Approach
```python
import time

def benchmark_function_category(expressions, iterations=100):
    """Benchmark translation performance."""
    start = time.time()

    for _ in range(iterations):
        for expr in expressions:
            parser = FHIRPathParser()
            parsed = parser.parse(expr)
            translator = ASTToSQLTranslator(dialect)
            fragments = translator.translate(parsed)

    duration = (time.time() - start) / (len(expressions) * iterations)
    return duration * 1000  # Convert to ms

# Benchmark categories:
# - Type functions (is, as, ofType)
# - Collection functions (empty, all, skip, etc.)
# - Math functions (abs, sqrt, etc.)
# - String functions (substring, indexOf, etc.)
```

## Files Modified
- `tests/performance/test_function_benchmarks.py` (new)
- `performance_report_sprint006.json` (new)
- `project-docs/plans/tasks/SP-006-024-performance-results.md` (new)

## Success Metrics
- [ ] All categories meet performance targets
- [ ] No regressions from Sprint 005
- [ ] Optimization opportunities identified
