# ADR: Remove Python Evaluator (SP-018-001)

**Date**: 2025-11-11
**Status**: Implemented
**Context**: Sprint 018

---

## Context

FHIR4DS had two execution paths for FHIRPath expressions:
1. **SQL Translator** (Production): Translates FHIRPath to SQL for population-scale analytics
2. **Python Evaluator** (Non-Production): Python-based evaluation for single-resource processing

### Problem

The Python evaluator was explicitly marked "NOT FOR PRODUCTION USE" but was still being used by the official compliance test suite. This created several issues:

- **Measurement Gap**: Official tests measured Python evaluator compliance (42.2%), not SQL translator (production) compliance
- **Misleading Metrics**: Sprint 016 completed 13 tasks improving the SQL translator, but compliance showed no improvement because tests used the Python evaluator
- **Architecture Violation**: Violated "population-first" principle by having patient-by-patient evaluation code
- **Confusion**: Developers unclear which code path was production
- **Dead Code**: ~3,000 lines of non-production code requiring maintenance

### Decision Drivers

1. **Architectural Alignment**: FHIR4DS is built on "population-first" principles
2. **Meaningful Metrics**: Compliance must measure production capabilities
3. **Development Focus**: Resources should target production code only
4. **Code Clarity**: One execution path eliminates confusion
5. **Maintenance Burden**: Remove ~3,000 lines of unused production code

---

## Decision

**Remove the Python evaluator entirely and update official test runner to use SQL translation exclusively.**

### Changes Made

1. **Deleted Evaluator Code**:
   - Removed `fhir4ds/fhirpath/evaluator/` directory (~3,000 lines)
   - Removed `tests/unit/fhirpath/evaluator/` test directory

2. **Updated Official Test Runner**:
   - Changed from hybrid (SQL + Python fallback) to SQL-only execution
   - Official compliance tests now measure production SQL translator
   - Removed all Python evaluator fallback paths

3. **Fixed Semantic Validator**:
   - Replaced `FunctionLibrary` import with static function list
   - No dependencies on evaluator module

4. **Cleaned Up Imports**:
   - Removed evaluator exports from `fhir4ds/fhirpath/__init__.py`
   - Cleaned up unused evaluator imports in test files
   - Removed evaluator-dependent test files

---

## Consequences

###Positive

- ✅ **Accurate Compliance**: Official tests now measure production SQL translator capabilities
- ✅ **Architectural Alignment**: Testing matches "population-first" architecture
- ✅ **Development Focus**: All work improves production code
- ✅ **Code Clarity**: Single execution path (SQL translation only)
- ✅ **Reduced Maintenance**: ~3,000 lines of code removed
- ✅ **Meaningful Metrics**: Compliance improvements will be real and visible

### Considerations

- ⚠️ **Compliance Numbers May Change**: Tests now measure SQL translator, which may show different percentages initially (more accurate)
- ⚠️ **Test Infrastructure**: Need to maintain SQL-based test data loading
- ⚠️ **Complex Expressions**: Some expressions may fail until SQL translator supports them (reflects reality)

---

## Implementation Details

### Files Removed
```
fhir4ds/fhirpath/evaluator/
├── __init__.py
├── collection_operations.py  (~18KB)
├── context.py                (~11KB)
├── context_loader.py         (~4KB)
├── engine.py                 (~47KB - main evaluator)
├── error_handler.py          (~13KB)
└── functions.py              (~50KB - function library)

tests/unit/fhirpath/evaluator/
├── test_arithmetic_operators.py
├── test_collection_operations.py
├── test_context.py
├── test_context_loader.py
├── test_engine.py
├── test_functions.py
└── test_type_conversion_functions.py

tests/unit/fhirpath/exceptions/test_error_handler.py
tests/performance/test_collection_operations_performance.py
```

### Files Modified
- `tests/integration/fhirpath/official_test_runner.py` - SQL-only execution
- `fhir4ds/fhirpath/parser_core/semantic_validator.py` - Static function list
- `fhir4ds/fhirpath/__init__.py` - Removed evaluator exports
- `tests/unit/fhirpath/test_operator_edge_cases.py` - Removed unused imports
- `tests/integration/test_multi_database.py` - Removed unused imports

---

## Validation

### Test Results
- SQL translator unit tests: ✅ Passing (1380+/1383 tests)
- Official test runner: ✅ Working with SQL-only execution (70% on sample)
- No import errors or missing module issues

### Compliance Measurement
Official tests now execute using SQL translation:
```bash
python3 -c "from tests.integration.fhirpath.official_test_runner import run_compliance_measurement; run_compliance_measurement(max_tests=10)"
```

Result: 70% passing (7/10 tests) - measuring real SQL translator capabilities

---

## Related Documents

- **Task Documentation**: `project-docs/plans/tasks/SP-018-001-remove-python-evaluator.md`
- **Sprint 016 Retrospective**: `project-docs/plans/retrospectives/SPRINT-016-RETROSPECTIVE.md`
- **Architecture Principles**: `CLAUDE.md` (Unified FHIRPath Architecture section)

---

## Notes

This change represents a significant architectural clarification: FHIR4DS uses SQL translation exclusively for FHIRPath evaluation, aligned with the "population-first" design principle. All future development will focus on improving the SQL translator, and compliance metrics will accurately reflect production capabilities.

The removal enables meaningful progress tracking - when we improve the SQL translator, compliance metrics will immediately reflect those improvements.

---

**Implemented By**: Claude Code (Junior Developer)
**Reviewed By**: Pending
**Sprint**: 018
