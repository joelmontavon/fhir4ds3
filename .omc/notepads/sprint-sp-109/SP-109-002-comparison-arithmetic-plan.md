# Task SP-109-002: Comparison Operators with Arithmetic

**Created:** 2026-01-29
**Sprint:** SP-109
**Status:** Starting
**Constraint:** NO PARSER CHANGES - Work within existing FHIRPath.g4 grammar

---

## Objective

Fix comparison operators that involve arithmetic expressions to improve FHIRPath compliance. Focus on issues that can be resolved **without modifying the parser grammar**.

---

## Current State

**Comparison Operators: 6.5% (22/338 tests passing)**
**Overall: 16.0% (149/934 tests passing)**

### Analysis of Failures

From initial testing of 95 comparison-with-arithmetic tests:
- **Passed: 19/30** (63%)
- **Failed: 11/30** (37%)

### Key Failure Categories

#### 1. Parser-Level Issues (CANNOT FIX - Parser Constraint)

These failures require grammar changes and are **out of scope**:
- `$this` keyword not recognized by lexer
- Lambda expressions with `$this`
- `aggregate()` function with lambda
- `repeat()` function variants

**Examples:**
```
Patient.name.given.where(substring($this.length()-3) = 'out')
(1|2|3|4|5|6|7|8|9).aggregate($this+$total, 0) = 45
```

#### 2. Semantic Validation Issues (CAN FIX)

These are in the semantic validator, not the parser:
- URL validation in string literals (`Invalid element name 'hl7'`)
- Context root validation for different resource types

**Examples:**
```
Patient.maritalStatus.coding.exists(code = 'P' and system = 'http://terminology.hl7.org/CodeSystem/v3-MaritalStatus')
```

#### 3. Translator/SQL Generation Issues (CAN FIX)

These are in the SQL translation layer:
- Type coercion in comparisons
- Negative number comparisons
- Arithmetic in comparison contexts

**Examples:**
```
-Patient.name.given.count() = -5
Patient.name.given.count() = 1 + 4
```

---

## Implementation Plan

### Phase 1: Analysis & Categorization (2 hours)

**Goal:** Understand the full scope of fixable issues

1. Run full compliance test suite
2. Categorize all 316 comparison failures into:
   - Parser issues (cannot fix)
   - Semantic validation issues (can fix)
   - Translator issues (can fix)
   - Test data issues (wrong resource type)

**Deliverable:** Detailed categorization report

### Phase 2: Semantic Validation Fixes (2-3 hours)

**Goal:** Fix validation issues that block tests

**Files to Modify:**
- `fhir4ds/main/fhirpath/parser_core/semantic_validator.py`

**Issues to Fix:**
1. URL detection in string literals
   - Current: Treats URLs as FHIR element names
   - Fix: Detect URL patterns and skip validation

2. Context root validation relaxation
   - Current: Strict validation blocks cross-resource tests
   - Fix: Allow for test scenarios

### Phase 3: Translator/SQL Fixes (4-6 hours)

**Goal:** Fix SQL generation for comparison with arithmetic

**Files to Modify:**
- `fhir4ds/main/fhirpath/sql/translator.py`
- `fhir4ds/main/fhirpath/sql/cte.py`
- `fhir4ds/main/dialects/duckdb.py`
- `fhir4ds/main/dialects/postgresql.py`

**Issues to Fix:**
1. **Type coercion in comparisons**
   - Integer vs Decimal comparisons
   - String to number comparisons
   - Boolean to number comparisons

2. **Negative number handling**
   - Unary minus in comparison contexts
   - Negative literals on right side of comparison

3. **Arithmetic in comparisons**
   - Precedence handling
   - Subexpression evaluation
   - Aggregate function results in comparisons

### Phase 4: Testing & Validation (2 hours)

**Goal:** Verify all fixes work correctly

1. Run full compliance suite
2. Verify expected improvements
3. Check for regressions
4. Test on both DuckDB and PostgreSQL

---

## Success Criteria

- [ ] Categorized all 316 comparison failures
- [ ] Fixed semantic validation issues
- [ ] Fixed translator issues for arithmetic in comparisons
- [ ] Improved comparison operator compliance (target: 20%+ → 40%+)
- [ ] No regressions in other categories
- [ ] Both DuckDB and PostgreSQL tests passing

---

## Constraints

**CRITICAL:** No modifications to:
- FHIRPath.g4 grammar file
- Generated parser files
- Lexer/Parser ANTLR rules

**Allowed modifications:**
- Semantic validator (post-parse validation)
- SQL translator (post-parse translation)
- CTE generator
- Dialect-specific SQL generation

---

## Expected Impact

**Conservative estimate:** Fix 30-50 additional tests
**Optimistic estimate:** Fix 50-80 additional tests

This represents a **9-24% improvement** in the comparison operators category (from 6.5% to 15-30%).

---

## Risk Assessment

**Risk Level:** Low

**Risks:**
- Limited scope due to parser constraint
- Some failures cannot be fixed without grammar changes
- May uncover deeper architectural issues

**Mitigation:**
- Focus on fixable issues only
- Document unfixable issues for future sprints
- Keep changes localized to translator layer
- Thorough testing to prevent regressions

---

## Next Steps

1. Run full categorization of comparison failures
2. Prioritize fixable issues
3. Implement semantic validation fixes
4. Implement translator fixes
5. Run comprehensive tests
