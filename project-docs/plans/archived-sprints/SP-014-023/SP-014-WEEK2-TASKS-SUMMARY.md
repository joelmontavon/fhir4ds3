# Sprint 014 Week 2 Tasks Summary

**Created**: 2025-10-28  
**Sprint**: Sprint 014 - Regression Analysis and Recovery  
**Phase**: Week 2 Implementation Tasks (Days 6-10)  
**Created By**: SP-014-003 Task Planning

---

## Overview

This document provides a comprehensive overview of all Week 2 implementation tasks created based on SP-014-002 root cause analysis. These tasks prioritize highest-impact fixes to improve compliance from 38.0% baseline to 50-55% target.

### Task Execution Order

**Priority 1 (Days 6-7)**: Critical path, highest impact
- ✅ **SP-014-004**: Union Operator Implementation - 12-14h, +84 tests → 46-47%

**Priority 2 (Day 7)**: Stability critical
- **SP-014-005**: List Bounds Checking Fix - 3-4h, +7 tests (prevents crashes)

**Priority 3 (Days 8-9)**: High-impact features  
- **SP-014-006**: Type Conversion Functions - 6-8h, +31 tests → 49-50%
- **SP-014-007**: String Comparison Fix - 3-5h, +30 tests → 52-55%

**Priority 4 (Day 10)**: Optional stretch goals
- **SP-014-008**: Additional fixes if time permits

---

## Task Details

### SP-014-004: Union Operator Implementation

**Status**: ✅ Complete task document (773 lines)  
**File**: `project-docs/plans/tasks/SP-014-004-implement-union-operator.md`  
**Priority**: CRITICAL  
**Estimated Effort**: 12-14 hours  
**Expected Impact**: +84 tests, 38.0% → 46-47% compliance

**Summary**: Implement FHIRPath union operator (`|`) which combines two collections preserving duplicates. Highest-impact single fix from SP-014-002 analysis.

**Key Implementation Steps**:
1. Add union operator to parser grammar (1h)
2. Implement AST adapter handler (2h)
3. Create dialect-specific SQL generation (2h)
4. Implement scalar-to-collection promotion (1h)
5. Write comprehensive unit tests (2h)
6. Validate against official test suite (1h)
7. Fix remaining edge cases (1-2h)

**Success Criteria**:
- At least 60 of 84 union operator tests passing (70% target)
- No regressions in other categories
- Works in both DuckDB and PostgreSQL

---

### SP-014-005: Fix List Index Out of Range Errors

**Priority**: CRITICAL (System Stability)  
**Estimated Effort**: 3-4 hours  
**Expected Impact**: +7 tests, prevents runtime crashes

#### Problem Description

"list index out of range" runtime errors occur when AST node children arrays are accessed without bounds checking. Identified in 7 tests, particularly with unary operators like unary minus `-(5.5'mg')`.

**Root Cause**: AST visitor code accesses `node.children[i]` without verifying array length first.

#### Implementation Approach

**Step 1: Identify All Unsafe List Access** (1 hour)
- Search codebase for `node.children[i]` patterns
- Search for similar patterns: `node.operands[i]`, `node.arguments[i]`
- Focus on AST visitor methods, particularly operator handling
- Create inventory of all locations

**Step 2: Add Defensive Bounds Checking** (1 hour)
```python
# Before (unsafe):
def visit_unary_operator(self, node):
    operand = node.children[0]  # Crashes if children is empty!
    operator = node.operator
    # ...

# After (safe):
def visit_unary_operator(self, node):
    if len(node.children) < 1:
        raise ValueError(f"Unary operator requires 1 operand, got {len(node.children)}")
    operand = node.children[0]
    operator = node.operator
    # ...
```

**Step 3: Write Unit Tests for Edge Cases** (1 hour)
- Test empty children arrays
- Test insufficient children for operators
- Test boundary conditions
- Verify graceful error messages

**Step 4: Validate Fix** (30 min)
- Run official test suite
- Verify 7 "list index out of range" tests now pass
- Ensure no regressions

#### Files to Modify
- `fhir4ds/fhirpath/sql/ast_adapter.py` - Main AST visitor
- `fhir4ds/fhirpath/sql/translator.py` - Expression translator
- Any other files with AST node access

#### Success Criteria
- [ ] No "list index out of range" crashes in test suite
- [ ] 7 affected tests passing
- [ ] Graceful error messages for malformed AST
- [ ] All unit tests passing

---

### SP-014-006: Implement Type Conversion Functions

**Priority**: HIGH  
**Estimated Effort**: 6-8 hours  
**Expected Impact**: +31 tests, 46% → 49-50% compliance

#### Problem Description

Type conversion functions `toDecimal()`, `convertsToDecimal()`, `toQuantity()`, and `convertsToQuantity()` are not implemented. These functions are essential for type casting and validation in FHIRPath expressions.

**Failing Tests**: 17 for toDecimal, 14 for convertsToDecimal

#### Implementation Approach

**Step 1: Implement toDecimal() Function** (2 hours)
- Add to function registry
- Handle conversions from:
  - Integer → Decimal (trivial)
  - String → Decimal (parse and validate)
  - Boolean → Empty (per spec)
  - Invalid input → Empty collection

```python
def to_decimal(value):
    """Convert value to decimal, or return empty if invalid."""
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except:
            return []  # Empty collection for invalid
    return []  # Empty for non-convertible types
```

**Step 2: Implement convertsToDecimal() Function** (1.5 hours)
- Returns true if value can be converted, false otherwise
- Test conversion without actually converting

```python
def converts_to_decimal(value):
    """Check if value can be converted to decimal."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            Decimal(value)
            return True
        except:
            return False
    return False
```

**Step 3: Implement toQuantity() and convertsToQuantity()** (2 hours)
- Similar pattern to decimal functions
- Handle FHIR Quantity type: `5.5'mg'`
- Parse value and unit

**Step 4: SQL Generation** (1 hour)
- Generate appropriate SQL for each function
- DuckDB and PostgreSQL implementations
- Handle type casting in SQL

**Step 5: Testing** (1.5 hours)
- Unit tests for each function
- Test all input types
- Official test suite validation

#### Files to Modify
- `fhir4ds/fhirpath/functions/` - Add type conversion functions
- Function registry - Register new functions
- Dialect files - SQL generation for type conversions

#### Success Criteria
- [ ] toDecimal() working for all input types
- [ ] convertsToDecimal() correct validation
- [ ] toQuantity() basic implementation
- [ ] convertsToQuantity() basic implementation
- [ ] +31 tests passing (all toDecimal/convertsToDecimal)
- [ ] No regressions

---

### SP-014-007: Fix String Comparison Case Sensitivity

**Priority**: MEDIUM  
**Estimated Effort**: 3-5 hours  
**Expected Impact**: +30 tests, 50% → 52-55% compliance

#### Problem Description

String comparisons may be case-insensitive when FHIRPath specification requires case-sensitive comparisons. This affects string equality, inequality, and comparison operators.

**Root Cause**: Database collation defaults may use case-insensitive comparison, or SQL generation doesn't specify binary/case-sensitive collation.

#### Implementation Approach

**Step 1: Investigate Current Behavior** (1 hour)
- Test current string comparison behavior:
  ```sql
  SELECT 'ABC' = 'abc';  -- Should be false, might be true
  ```
- Check DuckDB default collation
- Check PostgreSQL default collation
- Identify where comparisons are generated

**Step 2: Implement Case-Sensitive Comparison** (1.5 hours)

**DuckDB**:
```sql
-- Add binary collation
SELECT 'ABC' = 'abc' COLLATE binary;  -- Returns false
```

**PostgreSQL**:
```sql
-- Add C collation
SELECT 'ABC' = 'abc' COLLATE "C";  -- Returns false
```

**Update comparison SQL generation**:
```python
def generate_string_comparison(self, left, right, operator):
    if operator in ['=', '!=', '<', '>', '<=', '>=']:
        # Add collation for string comparisons
        return f"{left} {operator} {right} COLLATE {self.collation}"
```

**Step 3: Update Dialect Classes** (1 hour)
- Add collation property to each dialect
- DuckDB: `collation = "binary"`
- PostgreSQL: `collation = '"C"'`
- Apply to all string comparison operations

**Step 4: Testing** (1.5 hours)
- Unit tests for case-sensitive comparison
- Test: `'ABC' = 'abc'` → false
- Test: `'ABC' = 'ABC'` → true
- Test: `'test  ' = 'test'` → false (whitespace)
- Official test suite validation

#### Files to Modify
- `fhir4ds/fhirpath/sql/translator.py` - Comparison operator SQL generation
- `fhir4ds/fhirpath/dialects/duckdb.py` - DuckDB collation
- `fhir4ds/fhirpath/dialects/postgresql.py` - PostgreSQL collation

#### Success Criteria
- [ ] String comparisons are case-sensitive
- [ ] 'ABC' = 'abc' returns false
- [ ] +30 string comparison tests passing
- [ ] No regressions in string_functions category
- [ ] Works in both databases

---

## Week 2 Execution Plan

### Day 6-7 (Monday-Tuesday)

**Focus**: Union Operator (Highest Impact)

- Start SP-014-004 implementation
- Target completion by end of Day 7
- Expected result: 38% → 46-47% compliance

**Validation**: Run official test suite after Day 7, confirm +60-84 tests passing

---

### Day 7 Afternoon (Tuesday PM)

**Focus**: List Bounds Checking (Quick Win, Stability)

- SP-014-005 implementation (3-4 hours)
- Can run parallel to union operator validation
- Expected result: +7 tests, no more crashes

**Validation**: No "list index out of range" errors in test suite

---

### Day 8-9 (Wednesday-Thursday)

**Focus**: Type Conversion Functions

- SP-014-006 implementation
- Focus on toDecimal/convertsToDecimal (highest impact)
- toQuantity/convertsToQuantity if time permits
- Expected result: 46% → 49-50% compliance

**Validation**: Run official test suite, confirm +20-31 tests

---

### Day 9-10 (Thursday-Friday)

**Focus**: String Comparison + Week 2 Validation

- SP-014-007 implementation (Day 9)
- Final testing and validation (Day 10)
- Sprint 014 completion report
- Expected result: 50% → 52-55% compliance

**Validation**: Full test suite run, comprehensive compliance report

---

## Expected Week 2 Outcomes

### Conservative Estimate (70% confidence)
- **Tasks Completed**: 3-4 (union, bounds, type conversion partial)
- **Tests Fixed**: +90-110
- **Final Compliance**: 48-50%
- **Improvement**: +10-12 percentage points

### Realistic Estimate (50% confidence)
- **Tasks Completed**: 4 (union, bounds, type conversion, string partial)
- **Tests Fixed**: +120-140
- **Final Compliance**: 51-53%
- **Improvement**: +13-15 percentage points

### Optimistic Estimate (30% confidence)
- **Tasks Completed**: 4-5 (all planned tasks)
- **Tests Fixed**: +140-160
- **Final Compliance**: 53-55%
- **Improvement**: +15-17 percentage points

---

## Risk Mitigation

### Technical Risks
1. **Union operator more complex than expected**
   - Mitigation: Allocate 2 full days, ask for help if needed
   - Contingency: Defer edge cases to Sprint 015

2. **Type conversion functions have hidden complexity**
   - Mitigation: Focus on toDecimal only if time constrained
   - Contingency: Defer toQuantity to Sprint 015

3. **Database dialect differences cause issues**
   - Mitigation: Test both databases early and often
   - Contingency: DuckDB priority, PostgreSQL stretch

### Schedule Risks
1. **Week 2 insufficient for all tasks**
   - Mitigation: Clear prioritization, defer low-priority items
   - Contingency: String comparison becomes Sprint 015 task

2. **Unexpected blockers or bugs**
   - Mitigation: Daily progress tracking, early escalation
   - Contingency: Reduce scope, focus on highest-impact fixes

---

## Success Criteria for Week 2

**Minimum Success** (Must achieve):
- [ ] SP-014-004 complete (+60 tests minimum)
- [ ] SP-014-005 complete (+7 tests)
- [ ] Compliance ≥ 48%
- [ ] No regressions

**Target Success** (Goal to achieve):
- [ ] SP-014-004 complete (+70-84 tests)
- [ ] SP-014-005 complete (+7 tests)
- [ ] SP-014-006 partial (+20 tests)
- [ ] Compliance ≥ 50%
- [ ] No regressions

**Stretch Success** (Best case):
- [ ] All 4 tasks complete
- [ ] Compliance ≥ 52%
- [ ] No regressions
- [ ] Clean, maintainable code

---

**Summary Document Created**: 2025-10-28  
**Next Action**: Begin Week 2 implementation with SP-014-004  
**Review Status**: Ready for senior architect approval

---

*This summary consolidates all Week 2 task planning from SP-014-003. Individual task documents provide detailed implementation guidance for each fix.*
