# FHIRPath Evaluation Architecture

## Overview

FHIR4DS has **TWO SEPARATE** FHIRPath evaluation systems that serve different purposes.

## System 1: In-Memory FHIRPath Evaluator (COMPLETE)

**Purpose**: Full FHIRPath specification compliance, used for testing and validation

**Location**: `fhir4ds/fhirpath/evaluator/engine.py`

**Capabilities**:
- ✅ Full FHIRPath specification support (91%+ compliance)
- ✅ Handles all operators, functions, path navigation
- ✅ Returns Python objects (lists, dicts, primitives, None for NULL)
- ✅ Used by official compliance test harness

**Architecture**:
```
FHIRPath Expression (string)
         ↓
    Parser (PEP-002)
         ↓
    AST (Abstract Syntax Tree)
         ↓
    In-Memory Evaluator (Visitor Pattern)
         ↓
    Python Result (list/dict/int/bool/None)
```

**Example**:
```python
parser = FHIRPathParser()
result = parser.evaluate("Patient.name.family", context=patient_data)
# Returns: ["Smith", "Jones"] (Python list)
```

**Use Cases**:
- Official FHIRPath compliance testing
- Quick validation of expressions
- Development and debugging
- Small data sets

**Status**: ✅ **MATURE** - 91%+ specification compliance

---

## System 2: SQL Translator (PEP-003) (IN DEVELOPMENT)

**Purpose**: Translate FHIRPath to SQL for population-scale analytics

**Location**: `fhir4ds/fhirpath/sql/translator.py`

**Capabilities**:
- ⚠️ **PARTIAL** - Only ~10% of FHIRPath operations supported
- ✅ Literals (strings, numbers, dates, booleans)
- ✅ Path navigation (Patient.name.family)
- ✅ Basic comparisons (=, !=, <, >, <=, >=)
- ✅ where() function
- ❌ Most functions NOT implemented yet
- ❌ Complex expressions NOT supported yet

**Architecture**:
```
FHIRPath Expression (string)
         ↓
    Parser (PEP-002)
         ↓
    AST (Abstract Syntax Tree)
         ↓
    SQL Translator (Visitor Pattern)
         ↓
    SQL Fragments
         ↓
    CTE Builder (PEP-004 - FUTURE)
         ↓
    Complete SQL Query
         ↓
    DuckDB/PostgreSQL
         ↓
    Database Result Set
```

**Example** (What Works Today):
```python
translator = ASTToSQLTranslator(dialect)
fragments = translator.translate(ast)
# Returns: [SQLFragment(expression="Patient.name.family = 'Smith'", ...)]
```

**Example** (What Doesn't Work Yet):
```python
# These will FAIL - not implemented yet:
expression = "Patient.name.count()"  # ❌ count() not implemented
expression = "Patient.name.select(given)"  # ❌ select() not implemented
expression = "Patient.name.exists()"  # ❌ exists() not fully implemented
expression = "5 + 3 * 2"  # ❌ arithmetic not implemented
```

**Use Cases**:
- Population-scale analytics (millions of patients)
- SQL-on-FHIR view generation
- CQL translation (future)
- High-performance queries on FHIR databases

**Status**: ⚠️ **IN DEVELOPMENT** - Only ~10% complete (PEP-003)

---

## The Key Distinction

### Official Compliance Harness Uses System 1 (In-Memory)

**File**: `tests/integration/fhirpath/official_test_runner.py`

**Current Flow**:
```python
# Line 128: Uses In-Memory Evaluator
result = self.parser.evaluate(expression, context=context)

# Line 131-135: Validates result (CURRENTLY STUBBED!)
passed = self._validate_test_result(
    result,
    expected_outputs,
    invalid_flag=invalid_flag
)

# Line 219-220: THE STUB
# TODO: Implement full FHIRPath evaluation and result comparison
return True  # ← ALWAYS RETURNS TRUE!
```

**What SP-009-000 Needs**: Fix the stub at line 219-220 to **compare actual vs expected** results.

### SP-008-008 Used System 2 (SQL Translator)

**What SP-008-008 Fixed**: Temporal comparison logic in SQL translator

**Files Modified**:
- `fhir4ds/fhirpath/sql/translator.py` - Added CASE logic for NULL comparisons
- `fhir4ds/fhirpath/sql/ast_adapter.py` - Added temporal metadata extraction
- `fhir4ds/dialects/*.py` - Added time literal syntax

**Result**: SQL translator now generates correct CASE statements for temporal comparisons with precision mismatches.

**BUT**: This doesn't help the compliance harness because **the harness doesn't use the SQL translator!**

---

## The Junior Developer's Mistake

### What They Did ❌
1. Replaced compliance harness evaluation with SQL translator
2. Changed: `result = self.parser.evaluate()` → `result = translator.translate(ast)`
3. Tried to execute SQL instead of in-memory evaluation

### Why It Failed ❌
- SQL translator only supports ~10% of FHIRPath operations
- 90% of tests use operations not yet implemented in SQL translator
- Result: 880/934 tests failed (94% failure rate)

### What They Should Have Done ✅
1. Fix the stubbed comparison logic (lines 219-220)
2. Keep using in-memory evaluator (it already works!)
3. Just add proper result comparison (actual vs expected)

---

## Visual Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FHIRPath Expression                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                Parser (PEP-002) - COMPLETE                  │
│                  Converts string → AST                      │
└────────────┬───────────────────────────┬────────────────────┘
             │                           │
             ↓                           ↓
┌────────────────────────┐  ┌───────────────────────────────┐
│  In-Memory Evaluator   │  │    SQL Translator (PEP-003)   │
│  ✅ COMPLETE (91%)     │  │    ⚠️ IN DEV (~10%)          │
│  engine.py             │  │    translator.py              │
└────────────┬───────────┘  └──────────┬────────────────────┘
             │                         │
             ↓                         ↓
┌────────────────────────┐  ┌───────────────────────────────┐
│   Python Objects       │  │    SQL Fragments              │
│   (list/dict/None)     │  │    (SQLFragment objects)      │
└────────────┬───────────┘  └──────────┬────────────────────┘
             │                         │
             ↓                         ↓
┌────────────────────────┐  ┌───────────────────────────────┐
│   Compliance Harness   │  │    CTE Builder (PEP-004)      │
│   ← USES THIS!         │  │    ← NOT USED BY HARNESS      │
│   ← NEEDS FIX HERE     │  │    ← FUTURE WORK              │
└────────────────────────┘  └───────────────────────────────┘
```

---

## Roadmap to 100% SQL Translation

The SQL translator will eventually support all operations, but that's a **multi-sprint effort**:

### Sprint 005-007 (DONE ✅)
- Basic infrastructure
- Literals, paths, basic operators
- where() function
- Comparison operators with temporal logic

### Sprint 008-010 (CURRENT/FUTURE)
- Type operations (is, as, ofType) - DONE ✅
- Membership operations (in, contains) - DONE ✅
- More functions (select, first, count, exists)
- Arithmetic operations
- String functions

### Sprint 011+ (FUTURE)
- Aggregations (sum, avg, min, max)
- Date/time operations
- Complex nested expressions
- Full function library

**Until SQL translator reaches 100%, the compliance harness MUST use the in-memory evaluator.**

---

## The Correct Fix for SP-009-000

### What to Change
**File**: `tests/integration/fhirpath/official_test_runner.py`
**Method**: `_validate_test_result`
**Lines**: 215-220

### Current (WRONG)
```python
# Parser succeeded - check if success was expected
# If we have expected outputs with types/values, success is expected
if expected_outputs:
    # For now, consider any non-empty expected_outputs as expecting success
    # TODO: Implement full FHIRPath evaluation and result comparison
    return True  # ← ALWAYS RETURNS TRUE!
```

### Fixed (RIGHT)
```python
# Parser succeeded - now compare actual vs expected results
if expected_outputs:
    actual_value = actual_result.get('result')

    for expected in expected_outputs:
        expected_value = expected.get('value')
        expected_type = expected.get('type')

        # Handle NULL as valid expected outcome
        if expected_value is None or expected_type == 'null':
            if actual_value is None:
                return True
            continue

        # Compare values
        if self._values_match(actual_value, expected_value, expected_type):
            return True

    return False  # No match found
```

**Estimate**: 5 hours (not 22 hours!)
**Regressions**: ZERO (still using in-memory evaluator)

---

## Summary

1. **Two Systems**: In-memory evaluator (mature) and SQL translator (in development)
2. **Compliance Harness**: Uses in-memory evaluator, NOT SQL translator
3. **SP-009-000 Fix**: ~10 lines of comparison logic in harness
4. **SP-008-008 Work**: Enhanced SQL translator (separate system)
5. **Junior Dev Mistake**: Confused the two systems, replaced evaluation engine

**The fix is simple**: Compare actual vs expected results. That's it.
