# Sprint 018 - Remaining Tasks Summary

**Created**: 2025-11-11
**Status**: Task outlines for creation

---

## Completed Task Documents

✅ **SP-018-002**: Fix Literal Evaluation (CRITICAL - 20-25h)
✅ **SP-018-003**: Implement Type Conversions (HIGH - 15-18h)

---

## Tasks to Create (Outlines Provided)

### SP-018-004: Implement Union Operator and Core Functions

**Priority**: High
**Estimate**: 10-15 hours
**Dependencies**: SP-018-002 (literal fix)
**Expected Gain**: +30-40 tests

**Scope**:
1. **Union Operator (|)**:
   - Implement collection union in SQL translator
   - Generate SQL UNION for combining collections
   - Handle duplicate removal (union semantics)
   - Example: `(1|2|3)` → SQL UNION of collections

2. **not() Function**:
   - Boolean negation
   - `true.not()` → `false`
   - Required for Boolean logic category

3. **today() Function**:
   - Return current date
   - `today()` → `CURRENT_DATE` in SQL
   - No time component

4. **now() Function**:
   - Return current datetime
   - `now()` → `CURRENT_TIMESTAMP` in SQL
   - Includes time

5. **Boolean Aggregate Functions**:
   - `allTrue()`: All values true
   - `anyTrue()`: At least one true
   - `allFalse()`: All values false
   - `anyFalse()`: At least one false

**Implementation Notes**:
- Union operator: Use SQL UNION for collections, handle type compatibility
- today()/now(): Simple dialect methods (`CURRENT_DATE`, `CURRENT_TIMESTAMP`)
- Boolean aggregates: SQL aggregate functions (`BOOL_AND`, `BOOL_OR`)
- Test both DuckDB and PostgreSQL syntax

**Files to Modify**:
- `fhir4ds/fhirpath/sql/translator.py`: Add translation methods
- `fhir4ds/dialects/duckdb.py`: Add dialect-specific methods
- `fhir4ds/dialects/postgresql.py`: Add dialect-specific methods

---

### SP-018-005: Complete Easy Win Categories to 100%

**Priority**: Medium
**Estimate**: 8-12 hours
**Dependencies**: SP-018-002, SP-018-003, SP-018-004
**Expected Gain**: +15 tests

**Target Categories** (Near 100% already):
1. **DateTime_Functions**: 83.3% (5/6) → 100% (+1 test)
2. **Path_Navigation**: 80.0% (8/10) → 100% (+2 tests)
3. **Math_Functions**: 71.4% (20/28) → 100% (+8 tests)
4. **Boolean_Logic**: 33.3% (2/6) → 100% (+4 tests)

**Approach**:
1. Run official test suite to identify specific failing tests
2. Investigate each failure (may be fixed by prior tasks)
3. Implement missing functionality for each category
4. Validate 100% pass rate

**Expected**:
- Some tests may already pass after SP-018-002/003/004
- Focus on truly missing functionality
- Psychological win: 4 categories at 100%

---

### SP-018-006: Multi-Database Validation

**Priority**: Medium
**Estimate**: 4-6 hours
**Dependencies**: All prior Sprint 018 tasks
**Expected Gain**: 0 tests (validation task)

**Scope**:
1. **PostgreSQL Test Suite Execution**:
   - Run all unit tests with PostgreSQL
   - Run official FHIRPath suite with PostgreSQL
   - Compare results to DuckDB

2. **Dialect Parity Verification**:
   - Verify identical test results
   - Document any differences
   - Fix dialect-specific issues

3. **Performance Comparison**:
   - Measure literal evaluation performance
   - Measure type conversion performance
   - Document performance characteristics

**Validation Commands**:
```bash
# DuckDB (default)
pytest tests/unit/fhirpath/ -v
python3 -c "from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner; EnhancedOfficialTestRunner(database_type='duckdb').run_official_tests()"

# PostgreSQL
FHIR4DS_TEST_DB=postgresql pytest tests/unit/fhirpath/ -v
python3 -c "from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner; EnhancedOfficialTestRunner(database_type='postgresql', postgresql_conn_string='postgresql://postgres:postgres@localhost:5432/postgres').run_official_tests()"
```

**Success Criteria**:
- Identical pass/fail results between databases
- No database-specific failures
- Performance within 20% between databases

---

### SP-018-007: Documentation - Compliance Improvement Report (STRETCH)

**Priority**: Low (Stretch Goal)
**Estimate**: 3-4 hours
**Dependencies**: All Sprint 018 tasks complete

**Deliverable**: Comprehensive report documenting Sprint 018 achievements

**Contents**:
1. **Executive Summary**:
   - Compliance improvement (42.2% → actual result)
   - Key fixes implemented
   - Tests gained by category

2. **Technical Analysis**:
   - Literal evaluation bug root cause and fix
   - Type conversion implementation approach
   - Union operator and core functions

3. **Test Results**:
   - Before/after comparison
   - Category-by-category breakdown
   - Regression analysis

4. **Lessons Learned**:
   - What worked well
   - What was challenging
   - Recommendations for Sprint 019

5. **Next Steps**:
   - Remaining gaps for 100% compliance
   - Recommended priorities for Sprint 019

**Location**: `project-docs/test-results/SPRINT-018-COMPLIANCE-REPORT.md`

---

### SP-018-008: Fix Pre-Existing Test Failures (STRETCH)

**Priority**: Low (Stretch Goal)
**Estimate**: 6-8 hours
**Dependencies**: None (independent)

**Scope**: Fix the 6 pre-existing test failures from main branch

**Tests to Fix**:
1. `test_repeat_literal_returns_expression`
2. `test_repeat_with_literal_string`
3. `test_repeat_literal_case_works`
4. `test_select_with_simple_field_projection`
5. `test_where_with_simple_equality`
6. `test_where_duckdb_syntax`

**Root Cause** (from review): `_StubDialect` missing `cast_to_double()` method

**Fix**:
Add missing method to test stub:
```python
class _StubDialect:
    def cast_to_double(self, expression: str) -> str:
        return f"CAST({expression} AS DOUBLE)"
```

**Note**: These are test infrastructure issues, not production bugs.

---

## Sprint 018 Task Summary

| Task ID | Task Name | Priority | Estimate | Status | Expected Gain |
|---------|-----------|----------|----------|--------|---------------|
| SP-018-002 | Fix Literal Evaluation | Critical | 20-25h | ✅ Created | +100-150 tests |
| SP-018-003 | Implement Type Conversions | High | 15-18h | ✅ Created | +40-50 tests |
| SP-018-004 | Union Operator & Core Functions | High | 10-15h | 📝 Outlined | +30-40 tests |
| SP-018-005 | Complete Easy Win Categories | Medium | 8-12h | 📝 Outlined | +15 tests |
| SP-018-006 | Multi-Database Validation | Medium | 4-6h | 📝 Outlined | 0 (validation) |
| SP-018-007 | Compliance Report (Stretch) | Low | 3-4h | 📝 Outlined | 0 (documentation) |
| SP-018-008 | Fix Pre-Existing Failures (Stretch) | Low | 6-8h | 📝 Outlined | 6 tests (cleanup) |

**Total**: 66-88 hours
**Expected Compliance**: 42.2% → 60-70% (+185-260 tests)

---

## Next Steps

1. **Junior Developer**: Start with SP-018-002 (literal evaluation fix)
2. **Senior Architect**: Create full task documents for SP-018-004, SP-018-005, SP-018-006 using this outline
3. **Team**: Monitor progress, adjust priorities as needed

---

**Document Created**: 2025-11-11
**Purpose**: Task planning for Sprint 018 completion
**Status**: Outlines ready for expansion into full task documents

---

*Use this summary to create full task documents using the task template when ready. The first two tasks (SP-018-002, SP-018-003) are fully documented and ready for implementation.*
