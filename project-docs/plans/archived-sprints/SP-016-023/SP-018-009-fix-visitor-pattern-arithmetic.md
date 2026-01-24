# Task: Fix Visitor Pattern for Arithmetic Expressions

**Task ID**: SP-018-009
**Sprint**: 018
**Task Name**: Fix Visitor Pattern for Arithmetic Expressions
**Assignee**: Senior Solution Architect/Engineer
**Created**: 2025-11-14
**Priority**: CRITICAL

---

## Task Overview

### Description

**CRITICAL BUG DISCOVERED**: All 72 arithmetic tests are failing (0/72, 0% passing) due to a visitor pattern implementation bug. The `FHIRPathExpression` AST node class is missing the `accept()` method required by the visitor pattern, causing ALL arithmetic operations to fail.

**Current State**:
- Arithmetic compliance: 0/72 (0%)
- Error: `'FHIRPathExpression' object has no attribute 'accept'`
- Affects: `+`, `-`, `*`, `/`, `div`, `mod`, and all math functions

**Expected State**:
- Arithmetic compliance: 50-70/72 (69-97%)
- All basic arithmetic operators working
- Math functions operational

**Impact**: CRITICAL - This is blocking ~72 compliance tests and is a fundamental architecture issue

### Category
- [ ] Feature Implementation
- [x] Bug Fix (CRITICAL)
- [x] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [x] Critical (Blocker for compliance progress)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **Add accept() method to FHIRPathExpression**:
   - Implement visitor pattern correctly
   - Ensure all arithmetic operators work
   - Test with: `1 + 1`, `5 - 3`, `2 * 4`, `10 / 2`, `5 div 2`, `5 mod 2`

2. **Verify all arithmetic operators**:
   - Addition (`+`)
   - Subtraction (`-`)
   - Multiplication (`*`)
   - Division (`/`)
   - Integer division (`div`)
   - Modulo (`mod`)

3. **Implement missing math functions**:
   - `exp()` - exponential function
   - `truncate()` - truncate decimal
   - Verify existing: `round()`, `sqrt()`, `abs()`, `ceiling()`, `floor()`, `ln()`, `log()`, `power()`

### Non-Functional Requirements

- **Zero Regressions**: Must not break any currently passing tests
- **Multi-Database**: Must work in both DuckDB and PostgreSQL
- **Performance**: No performance degradation
- **Architecture**: Must maintain thin dialect pattern

### Acceptance Criteria

- [ ] FHIRPathExpression has accept() method implemented
- [ ] All basic arithmetic operators working (`+`, `-`, `*`, `/`, `div`, `mod`)
- [ ] Math functions implemented: `exp()`, `truncate()`
- [ ] Arithmetic compliance: 50+/72 tests passing (69%+)
- [ ] Zero regressions in other test categories
- [ ] Both DuckDB and PostgreSQL passing
- [ ] Unit tests passing (1886+ tests)
- [ ] Compliance tests improved significantly

---

## Technical Specifications

### Root Cause Analysis

**Parser Issue**: The `FHIRPathExpression` class in `fhir4ds/fhirpath/parser.py` doesn't implement the visitor pattern's `accept()` method.

**Visitor Pattern Expected**:
```python
class ASTNode:
    def accept(self, visitor):
        """Accept a visitor and call the appropriate visit method."""
        return visitor.visit(self)
```

**Current Error Chain**:
1. Parser creates `FHIRPathExpression` for `1 + 1`
2. Translator calls `translator.visit(ast)`
3. Visitor tries to call `ast.accept(visitor)`
4. **ERROR**: `'FHIRPathExpression' object has no attribute 'accept'`

### Files to Modify

**PRIMARY**:
- `fhir4ds/fhirpath/parser.py` - Add `accept()` method to `FHIRPathExpression`

**SECONDARY** (if needed):
- `fhir4ds/fhirpath/sql/translator.py` - Add math function translations
- `fhir4ds/dialects/duckdb.py` - DuckDB-specific math functions (if needed)
- `fhir4ds/dialects/postgresql.py` - PostgreSQL-specific math functions (if needed)

### Implementation Approach

**Step 1: Fix Visitor Pattern** (30 minutes)
```python
# In fhir4ds/fhirpath/parser.py

class FHIRPathExpression:
    def accept(self, visitor):
        """Accept a visitor following the visitor pattern."""
        return visitor.visit(self)
```

**Step 2: Verify Arithmetic Operators** (15 minutes)
- Test each operator: `+`, `-`, `*`, `/`, `div`, `mod`
- Ensure translator has handlers for each

**Step 3: Implement Missing Math Functions** (45 minutes)
- Add `exp()` function translation
- Add `truncate()` function translation
- Map to SQL equivalents in dialects

**Step 4: Test** (30 minutes)
- Run arithmetic compliance tests
- Verify 50+ tests now passing
- Check for regressions

---

## Dependencies

### Prerequisites

- Parser exists with `FHIRPathExpression` class
- Translator exists with visitor pattern infrastructure
- Basic arithmetic operators already implemented (just not accessible)

### Blocking Tasks

- None - this is a critical bug fix that should be done immediately

---

## Estimation

### Time Breakdown

- **Root Cause Investigation**: 15 minutes (COMPLETED)
- **Fix accept() method**: 30 minutes
- **Verify arithmetic operators**: 15 minutes
- **Implement missing math functions**: 45 minutes
- **Testing and validation**: 30 minutes
- **Documentation**: 15 minutes

- **Total Estimate**: **2.5 hours**

### Confidence Level

- [x] High (90%+ confident in estimate)
- Reason: Root cause identified, fix is straightforward

---

## Success Metrics

### Primary Metrics
- **Arithmetic Compliance**: 0/72 → 50+/72 (0% → 69%+)
- **Overall Compliance**: 396/934 → 446+/934 (42.4% → 47.7%+)

### Secondary Metrics
- **Zero regressions**: All currently passing tests still pass
- **Multi-database**: Works in DuckDB and PostgreSQL

---

## Risk Assessment

### High Impact
- This fix could immediately unlock 50-70 additional compliance tests
- May reveal other underlying issues once arithmetic works

### Low Risk
- Fix is localized to visitor pattern implementation
- Well-understood problem with clear solution

---

## Notes for Implementation

**Critical Finding**:
The error `'FHIRPathExpression' object has no attribute 'accept'` indicates the parser's AST nodes aren't properly implementing the visitor pattern. This is preventing ALL arithmetic from working.

**Quick Win Potential**:
Once fixed, we could jump from 42.4% to 47-50% compliance immediately, as all the arithmetic logic already exists - it's just not accessible.

**Math Functions to Add**:
- `exp(x)` → SQL: `EXP(x)` (both DuckDB and PostgreSQL)
- `truncate()` → SQL: `TRUNC(x)` (both databases)

---

**Task Created**: 2025-11-14 by Senior Solution Architect/Engineer
**Status**: ⚠️ PARTIALLY COMPLETED - DEEPER ISSUE FOUND

---

## Investigation Summary

### Work Completed (2025-11-14)

1. ✅ **Added accept() method to FHIRPathExpression** (fhir4ds/fhirpath/parser.py:111-131)
2. ✅ **Added accept() method to EnhancedASTNode** (fhir4ds/fhirpath/parser_core/ast_extensions.py:143-207)
3. ✅ **Identified root cause**: Enhanced parser metadata miscategorization

### Critical Finding

**The problem is deeper than initially diagnosed:**

**Issue #1**: Visitor Pattern ✅ FIXED
- `FHIRPathExpression` was missing `accept()` method
- `EnhancedASTNode` was missing `accept()` method
- Both now implemented

**Issue #2**: Metadata Miscategorization ❌ NOT FIXED
- Enhanced parser categorizes arithmetic operators as `PATH_EXPRESSION` instead of `OPERATOR`
- Example: `1 + 1` creates `AdditiveExpression` node with category `PATH_EXPRESSION`
- This causes visitor to route to `visit_identifier()` instead of `visit_operator()`

**Issue #3**: Adapter Attribute Mismatch ❌ NOT FIXED
- Current adapter classes missing required attributes
- `IdentifierNode` requires `identifier` attribute
- `OperatorNode` requires `operator` attribute
- `LiteralNode` requires `value` and `literal_type` attributes

### Test Results

**Before Fix**: 0/72 arithmetic tests - Error: `'FHIRPathExpression' object has no attribute 'accept'`
**After Partial Fix**: 0/72 arithmetic tests - Error: `'IdentifierNodeAdapter' object has no attribute 'identifier'`

**Progress**: Visitor pattern now works, but metadata/adapter issues remain

### Files Modified

1. `fhir4ds/fhirpath/parser.py` - Added FHIRPathExpression.accept()
2. `fhir4ds/fhirpath/parser_core/ast_extensions.py` - Added EnhancedASTNode.accept() with adapters

### Follow-Up Required

Created **SP-019-001** to complete the arithmetic fix with proper approach:
- Option A: Fix enhanced parser metadata categorization
- Option B: Rewrite adapters with proper attribute mapping
- Option C: Replace enhanced parser with direct AST node creation

**Estimated Additional Work**: 4-6 hours

---

**Task Outcome**: Partial success - visitor pattern infrastructure fixed, but arithmetic still broken due to metadata/adapter issues. Follow-up task SP-019-001 created for Sprint 019.

*The visitor pattern infrastructure is now in place, but arithmetic operations require deeper parser/metadata fixes to become operational.*
