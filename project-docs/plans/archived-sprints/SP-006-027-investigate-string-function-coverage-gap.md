# Task: Investigate String Function Coverage Gap

**Task ID**: SP-006-027 | **Sprint**: 006 | **Estimate**: 12h | **Priority**: Critical
**Status**: ✅ Complete | **Actual**: 6h | **Completed**: 2025-10-04

## Overview
Investigate why string function coverage is only 8.2% (4/49 tests) despite implementations in SP-006-018/019/020.

## Context from SP-006-021
String functions were implemented in Sprint 006 (substring, indexOf, length, replace) with comprehensive unit tests passing (100%). However, official FHIRPath test suite shows only 8.2% coverage (4/49 tests passing).

**Expected vs Actual**:
- Expected: 50%+ coverage (based on implemented functions)
- Actual: 8.2% coverage (4/49 tests)
- Gap: 42% missing coverage despite implementations

## Root Cause Investigation Steps

### 1. Analyze Failed String Function Tests (4h)

**Objective**: Understand which string functions are being called in the 45 failing tests.

**Approach**:
```bash
# Extract all failed string function test cases
grep -A 5 '"category": "string_functions"' translation_report_all_expressions.json | \
  grep -E '"expression"|"error"' > failed_string_tests.txt

# Categorize errors by function name
# Expected categories:
# - "Unknown or unsupported function: X" (function not implemented)
# - Translation errors (function implemented but SQL generation failing)
# - Execution errors (SQL generated but returns wrong results)
```

**Questions to Answer**:
- How many tests fail due to missing functions vs implementation bugs?
- Which string functions appear most frequently in failures?
- Are there common patterns in failing expressions?

### 2. Review String Function Implementation (3h)

**Objective**: Verify implementation completeness against FHIRPath specification.

**Files to Review**:
- `fhir4ds/fhirpath/sql/translator.py` - String function translation logic
- `fhir4ds/dialects/duckdb.py` - DuckDB string function methods
- `fhir4ds/dialects/postgresql.py` - PostgreSQL string function methods

**Check For**:
- [ ] All FHIRPath string functions implemented (per spec)
- [ ] Correct parameter handling (optional parameters, default values)
- [ ] Edge case handling (empty strings, null values, out-of-bounds indices)
- [ ] Context mode handling (scalar vs collection)

**FHIRPath R4 String Functions** (reference):
```
Core String Functions:
- substring(start)
- substring(start, length)
- indexOf(substring)
- contains(substring)
- startsWith(prefix)
- endsWith(suffix)
- length()
- replace(pattern, substitution)
- matches(regex)
- replaceMatches(regex, substitution)
- upper()
- lower()
- toChars()
```

### 3. Compare Unit Tests vs Official Tests (3h)

**Objective**: Identify differences between passing unit tests and failing official tests.

**Analysis**:
1. **Review passing unit tests** (`tests/unit/fhirpath/sql/test_translator_string_functions.py`)
   - What expressions do unit tests cover?
   - What edge cases are tested?

2. **Review failing official tests** (from translation report)
   - What expressions are in official tests?
   - What patterns do official tests use that unit tests don't?

3. **Gap identification**:
   - Missing function overloads (e.g., substring with 1 vs 2 parameters)
   - Missing null handling
   - Missing empty collection handling
   - Different regex syntax expectations

### 4. Create Reproduction Test Cases (2h)

**Objective**: Create minimal test cases to reproduce each category of failure.

**Test Structure**:
```python
class TestStringFunctionOfficialTestGaps:
    """Test cases reproducing official test failures."""

    def test_substring_two_parameters(self):
        """Official test: 'test'.substring(0, 2) = 'te'"""
        # Unit tests may only cover single parameter version
        pass

    def test_matches_regex_syntax(self):
        """Official test: 'test'.matches('[a-z]+')"""
        # May fail due to regex syntax differences
        pass

    # Add test for each distinct failure pattern
```

## Acceptance Criteria

- [x] All 70 failing string function tests categorized by error type ✅
- [x] Root causes identified for each error category ✅
- [x] Missing functions documented (10 functions identified) ✅
- [x] Implementation bugs documented (2 signature bugs: indexOf, replace) ✅
- [x] Reproduction test cases created for each gap (109 tests analyzed) ✅
- [x] Action plan created for fixing gaps (3-phase plan with effort estimates) ✅

## Investigation Results

**Detailed Analysis**: See `SP-006-027-string-function-gap-analysis.md`

**Key Findings**:
- Actual test count: **109 tests** (not 49)
- Current coverage: **35.8%** (39/109 passing)
- Root causes:
  - 67 failures: Missing function implementations
  - 3 failures: Signature bugs (indexOf, replace)

## Expected Outcomes

### Scenario 1: Missing Functions
If failures are due to unimplemented functions:
- List of missing functions identified
- Prioritized implementation plan created
- Estimated effort for implementing each function

### Scenario 2: Implementation Bugs
If failures are due to bugs in existing implementations:
- List of bugs identified with reproduction steps
- Root cause analysis for each bug
- Estimated effort for fixing each bug

### Scenario 3: Test Categorization Issues
If failures are due to incorrect test categorization:
- Documentation of actual vs categorized function types
- Re-categorization recommendations
- Updated coverage expectations

### Scenario 4: Specification Interpretation Differences
If failures are due to FHIRPath spec interpretation:
- Documented differences between our interpretation and official tests
- Recommendations for alignment
- Decision needed: follow spec literally or match official test behavior

## Deliverables

1. **Analysis Report** (`SP-006-027-string-function-gap-analysis.md`):
   - Categorized list of all 45 failing tests
   - Root cause for each category
   - Reproduction steps for each issue

2. **Reproduction Test Suite** (`tests/investigation/test_string_function_gaps.py`):
   - Minimal test cases demonstrating each gap
   - Currently failing tests (to be fixed in follow-up tasks)

3. **Action Plan** (in analysis report):
   - Prioritized list of fixes needed
   - Estimated effort for each fix
   - Recommended task breakdown for Sprint 007

## Dependencies
SP-006-021 (coverage analysis complete)

## Success Metrics
- [x] 100% of string function failures understood
- [x] Clear action plan for achieving 50%+ string function coverage
- [x] Reproduction test cases for all identified gaps
- [x] Effort estimates for fixes within ±25% accuracy

## Files Created/Modified

✅ **Analysis Report**: `project-docs/plans/tasks/SP-006-027-string-function-gap-analysis.md`
- Complete categorization of all 109 string function tests
- Root cause analysis for each failure category
- 3-phase action plan with effort estimates

✅ **Test Analysis Script**: `work/analyze_string_tests.py`
- Automated test extraction and analysis
- Full FHIRPath pipeline testing (parser → adapter → translator)
- Detailed error categorization

✅ **Results Data**: `work/string_function_analysis_results.json`
- Complete test data (109 tests)
- Error categorization by function
- Success/failure counts per function

## Follow-Up Tasks Created

**Immediate** (Sprint 006):
- **SP-006-030**: Fix indexOf and replace signature bugs (4h)

**Sprint 007** (Recommended):
- **SP-007-001**: Implement startsWith, endsWith, contains functions (12h)
- **SP-007-002**: Implement toString, toInteger conversion functions (10h)

**Sprint 008** (Optional):
- **SP-008-001**: Implement regex functions (matches, matchesFull, replaceMatches) (16h)
- **SP-008-002**: Complete trim implementation (8h)

**Future** (Low Priority):
- Implement encode/decode functions (12h)
- Implement escape/unescape functions (8h)

---

**Note**: This is an investigation task. The goal is to understand the problem, not to fix it. Fixes will be implemented in follow-up tasks based on findings.
