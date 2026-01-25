# Task: SP-100-006 - Arithmetic Operator Type Coercion

**Created**: 2026-01-24
**Status**: Pending
**Priority**: P1 (High)
**Estimated Effort**: 15-20 hours

---

## Task Description

Implement spec-compliant type coercion for arithmetic operators. Current compliance is 25.0% (18/54 tests passing) due to incomplete type promotion rules.

## Current State

**Location**: `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py:2284-2921`

**Issues**:
- Division semantics not spec-compliant
- Modulo operation edge cases
- Mixed-type arithmetic (int + decimal)
- Type promotion rules incomplete

## Requirements

### FHIRPath Type Promotion Rules

1. **integer + integer** = integer
2. **integer + decimal** = decimal
3. **decimal + decimal** = decimal
4. **Division always returns decimal**
5. **Modulo preserves operand types**

## Acceptance Criteria

1. ✅ Arithmetic operators achieve 80%+ compliance
2. ✅ Type coercion matches spec behavior
3. ✅ All edge cases handled
4. ✅ Both dialects produce consistent results

---

**Task Owner**: TBD
