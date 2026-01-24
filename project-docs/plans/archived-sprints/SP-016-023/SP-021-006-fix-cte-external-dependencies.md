# Task: Fix CTE Assembly to Handle External Table Dependencies

**Task ID**: SP-021-006-FIX-CTE-EXTERNAL-DEPENDENCIES
**Status**: ✅ **COMPLETED - MERGED (2025-11-29)**
**Review**: project-docs/plans/reviews/SP-021-006-review.md
**Priority**: 🔴 **CRITICAL BLOCKER**
**Actual Impact**: +0 tests (bug fixed but not the primary blocker)
**Actual Effort**: 4 hours
**Completion Date**: 2025-11-29

---

## Critical Discovery

During deep investigation of SP-021-003, we discovered that **the CTE assembly infrastructure has a fundamental bug** that prevents execution of complex FHIRPath expressions.

**The Real Blocker**: `CTEAssembler._order_ctes_by_dependencies()` treats the `resource` table as a missing CTE dependency instead of recognizing it as an external table dependency.

**Impact**: This blocks:
- ✅ String functions that ARE implemented (substring, length, indexOf, replace)
- ✅ Variable binding that WORKS ($this, $index, $total)
- ✅ Any expression using where(), select(), exists() with function calls
- ✅ Any CTE that references the base `resource` table

---

## Evidence

### Minimal Reproducer

```python
# This expression TRANSLATES successfully but FAILS at CTE assembly
expression = "Patient.name.given.where(substring($this.length()-3) = 'out')"

# Translation: ✅ WORKS
translator = ASTToSQLTranslator(dialect, "Patient")
fragments = translator.translate(ast)  # SUCCESS

# CTE Building: ✅ WORKS
cte_builder = CTEBuilder(dialect)
ctes = cte_builder.build_cte_chain(fragments)  # SUCCESS

# CTE Assembly: ❌ FAILS
cte_assembler = CTEAssembler(dialect)
query = cte_assembler.assemble_query(ctes)
# ValueError: Missing CTE dependencies: resource
```

### Error Location

**File**: `fhir4ds/fhirpath/sql/cte.py`
**Method**: `_order_ctes_by_dependencies()`
**Line**: 747

```python
if missing:
    missing_list = ", ".join(sorted(missing))
    raise ValueError(f"Missing CTE dependencies: {missing_list}")
```

### Root Cause

The dependency resolution algorithm assumes ALL dependencies must be CTEs. It doesn't recognize that `resource` is an **external table** that exists in the database context.

---

## Why This Matters

### Previous Tasks Had Zero Impact Because of This Bug

**SP-021-001** (Primitive extraction):
- Implementation: ✅ Correct
- Result: +0 tests ❌
- Reason: CTE assembly fails before code executes

**SP-021-002** (Variable binding):
- Implementation: ✅ Correct
- Result: +0 tests ❌
- Reason: CTE assembly fails before variables are bound

**Planned SP-021-008** (String functions):
- Functions: ✅ Already implemented!
- Would achieve: +0 tests ❌
- Reason: CTE assembly blocks execution

---

## Requirements

### Functional Requirements

1. **Recognize External Tables**: Modify `_order_ctes_by_dependencies()` to distinguish between:
   - CTE dependencies (must exist in the CTE list)
   - External table dependencies (exist in database context)

2. **Known External Tables**: Maintain list of known external dependencies:
   - `resource` (base FHIR resource table)
   - Any other tables that might exist in execution context

3. **Dependency Validation**: Only raise "Missing CTE dependencies" for dependencies that:
   - Are NOT in the CTE list
   - Are NOT in the external tables list

### Non-Functional Requirements

- **Zero Regressions**: 404 currently passing tests must continue to pass
- **Clear Error Messages**: If a CTE dependency is truly missing, error should be clear
- **Performance**: No measurable impact on CTE assembly time

### Acceptance Criteria

- [ ] CTEs with `resource` dependency assemble successfully
- [ ] Minimal reproducer (substring test) executes without "Missing CTE dependencies" error
- [ ] Re-run compliance tests shows improvement (target: +50-300 tests)
- [ ] All 404 currently passing tests still pass
- [ ] Unit tests added for external table dependency handling

---

## Implementation Approach

### Step 1: Locate the Bug (1-2 hours)

**File**: `fhir4ds/fhirpath/sql/cte.py`
**Method**: `_order_ctes_by_dependencies()`

Read the current implementation to understand:
- How dependencies are collected
- How missing dependencies are detected
- Where the check happens

### Step 2: Design Fix (2-4 hours)

**Option A**: Add `external_tables` parameter
```python
def _order_ctes_by_dependencies(
    self,
    ctes: List[CTE],
    external_tables: Set[str] = None
) -> List[CTE]:
    if external_tables is None:
        external_tables = {"resource"}  # Default known tables

    # When checking for missing dependencies:
    missing = all_deps - cte_names - external_tables  # Exclude external tables
```

**Option B**: Auto-detect external tables
```python
# Recognize common patterns for external tables
EXTERNAL_TABLE_PATTERNS = {"resource", "valueset", "codesystem"}

def _is_external_table(self, table_name: str) -> bool:
    return table_name in EXTERNAL_TABLE_PATTERNS
```

**Recommended**: Option A (explicit is better than implicit)

### Step 3: Implement Fix (4-8 hours)

1. Modify `_order_ctes_by_dependencies()` signature
2. Add external_tables parameter with default {"resource"}
3. Update missing dependency check to exclude external tables
4. Update call sites to pass external_tables if needed

### Step 4: Test with Minimal Reproducer (2-3 hours)

```python
# Test that the exact failing case now works
expression = "Patient.name.given.where(substring($this.length()-3) = 'out')"
context = {"resourceType": "Patient", "name": [{"given": ["Theodore"]}]}

# Should execute without "Missing CTE dependencies" error
# Should return correct result: ["Theodore"] (ends with "ore", not "out")
```

### Step 5: Run Full Compliance Suite (2-3 hours)

```bash
PYTHONPATH=. DB_TYPE=duckdb python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
report = run_compliance_measurement(database_type='duckdb', max_tests=None)
print(f'Before fix: 404/934 (43.3%)')
print(f'After fix: {report.passed_tests}/934 ({report.compliance_percentage:.1f}%)')
print(f'Improvement: +{report.passed_tests - 404} tests')
"
```

**Expected**: +50-300 tests (massive improvement)

### Step 6: Validate Previous Implementations (2-4 hours)

Now that CTE assembly works, verify that previous implementations actually work:

**Test SP-021-001** (Primitive extraction):
- Run tests that use primitive arrays
- Measure actual impact now that execution works

**Test SP-021-002** (Variable binding):
- Run tests with $this, $index, $total
- Measure actual impact now that execution works

### Step 7: Write Unit Tests (4-6 hours)

```python
# tests/unit/fhirpath/sql/test_cte_assembly.py

class TestCTEExternalDependencies:
    def test_resource_table_recognized_as_external(self):
        """CTE with 'resource' dependency should not raise error."""
        # Create CTE that depends on 'resource'
        # Should assemble without "Missing CTE dependencies" error

    def test_unknown_dependency_raises_error(self):
        """CTE with unknown dependency should raise error."""
        # Create CTE that depends on 'foo_table'
        # Should raise "Missing CTE dependencies: foo_table"

    def test_multiple_external_tables(self):
        """Multiple external tables can be specified."""
        # Pass external_tables={"resource", "valueset"}
        # Both should be recognized
```

---

## Expected Impact

### Immediate Impact (After Fix)

**Projected Improvement**: +50-300 tests

**Why This Range**:
- **Minimum (+50)**: Tests using basic lambda functions with external deps
- **Likely (+150)**: Tests using where/select/exists with function calls
- **Maximum (+300)**: If most failures were CTE-blocked

**Categories Likely to Improve**:
- String_Functions: 42/65 → 60/65+ (functions work, were just blocked)
- Collection_Functions: 26/141 → 80/141+ (may work, were blocked)
- Function_Calls: 47/113 → 80/113+ (were blocked by CTE)
- Type_Functions: 28/116 → 60/116+ (may work, were blocked)

### Secondary Impact (Validation)

After fix, we can validate:
- **SP-021-001**: May NOW show +10-50 test improvement
- **SP-021-002**: May NOW show +20-40 test improvement
- **Total from "failed" tasks**: +30-90 tests that were blocked

### Updated Compliance Projection

**Current**: 404/934 (43.3%)
**After CTE fix**: 454-704/934 (48.6%-75.4%)
**After validating previous tasks**: 484-794/934 (51.8%-85.0%)

**Realistic Target**: 60-70% compliance after this single fix

---

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Fix breaks existing CTEs | Medium | High | Comprehensive regression testing |
| Impact estimate too optimistic | Medium | Medium | Start with minimal fix, measure, iterate |
| Other blockers exist beyond CTE | High | Medium | This investigation found ONE blocker, may be others |
| External tables concept incomplete | Low | Medium | Start with just "resource", add others as needed |

---

## Dependencies

### Prerequisites
- ✅ SP-021-003 investigation complete
- ✅ Minimal reproducer created
- ✅ Root cause identified

### Blocking Tasks
None - this IS the blocker

### Dependent Tasks
**ALL other SP-021 tasks** depend on this fix:
- SP-021-007 (Arithmetic) - may be unblocked
- SP-021-008 (Strings) - will be unblocked (functions exist!)
- SP-021-009 (iif) - may be unblocked
- SP-021-010 (Collections) - likely unblocked
- SP-021-011 (Polymorphism) - may be separate issue

---

## References

- **Deep Dive Summary**: `work/SP-021-003-DEEP-DIVE-SUMMARY.md`
- **Investigation Report**: `work/SP-021-003-INVESTIGATION-REPORT.md`
- **CTE Infrastructure**: `fhir4ds/fhirpath/sql/cte.py`
- **Test Runner**: `tests/integration/fhirpath/official_test_runner.py`

---

## Critical Question

**Should we PAUSE all other SP-021 tasks until this is fixed?**

**Recommendation**: YES
- Fixing this ONE infrastructure bug could unlock 100-300 tests
- All other tasks may be solving problems that don't exist or are blocked by this
- Effort: 20-40 hours vs. 170-248 hours for current roadmap
- ROI: Potentially 5-10x better

---

**Task Created**: 2025-11-28
**Priority**: 🔴 CRITICAL BLOCKER
**Expected Impact**: +50-300 tests (10-32% compliance improvement)
**Part Of**: Infrastructure fix that unblocks entire compliance improvement effort

---

*This task fixes the fundamental execution blocker preventing complex FHIRPath expressions from running, regardless of whether the underlying functionality is implemented.*

---

## Implementation Summary

### What Was Implemented

Modified `CTEAssembler._order_ctes_by_dependencies()` in `fhir4ds/fhirpath/sql/cte.py` to handle external table dependencies:

1. **Added `external_tables` parameter**: Optional parameter with default value `{"resource"}`
2. **Updated missing dependency check**: Excludes external tables from "Missing CTE dependencies" error
3. **Fixed adjacency graph building**: Only builds edges for CTE-to-CTE dependencies
4. **Fixed indegree calculation**: Counts only CTE dependencies, not external tables

### Implementation Details

**File**: `fhir4ds/fhirpath/sql/cte.py:710-784`

**Key Changes**:
- Line 713: Added `external_tables: Optional[Set[str]] = None` parameter
- Line 740: Initialize default `external_tables = {"resource"}` if None
- Lines 754-758: Check for missing dependencies excluding external tables
- Lines 777-779: Build adjacency edges only for CTE-to-CTE dependencies  
- Lines 783-784: Calculate indegree counting only CTE dependencies

### Testing

**Unit Tests**: `tests/unit/fhirpath/sql/test_cte_external_dependencies.py`
- 8 comprehensive test cases covering all scenarios
- All tests passing

**Minimal Reproducer**: `test_minimal_reproducer.py`
- Tests the exact failing case from the task
- Validates fix works correctly
- All tests passing

### Results

**Compliance Impact**: +0 tests (404/934 still at 43.3%)

**Root Cause Analysis**:
The "Missing CTE dependencies: resource" error was REAL and is now FIXED. However, this particular error was not blocking the official compliance tests. The compliance tests are failing for OTHER reasons earlier in the pipeline.

**Value Delivered**:
1. ✅ Fixed a real infrastructure bug preventing CTEs from referencing external tables
2. ✅ Comprehensive test coverage ensures robustness
3. ✅ No regressions introduced (all existing tests still pass)
4. ✅ Better error messages (distinguishes missing CTEs from external tables)

### Lessons Learned

The hypothesis that this was "THE blocker" was incorrect. While the bug was real and needed fixing:
- The error wasn't actually occurring in the compliance test execution path
- Other blockers exist earlier in the pipeline preventing tests from reaching CTE assembly
- Further investigation needed to identify the actual primary blocker(s)

### Next Steps Recommendations

1. Investigate why compliance tests aren't reaching CTE assembly phase
2. Review test execution logs to find the actual failure points
3. Consider SP-021-003 findings may need deeper analysis
4. This fix enables future work that depends on external table references

---

**Completed By**: Junior Developer (via /junior-complete-task)
**Completion Date**: 2025-11-29
**Branch**: feature/SP-021-006-fix-cte-external-dependencies
**Status**: ✅ COMPLETED - Ready for senior review and merge
