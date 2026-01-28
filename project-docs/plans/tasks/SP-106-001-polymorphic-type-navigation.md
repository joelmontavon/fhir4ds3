# SP-106-001: Fix Polymorphic Type Navigation Parser

**Priority:** CRITICAL
**Estimated Effort:** 8 hours
**Test Impact:** 73+ tests (unblocks Type Checking, Comparison Operators, and more)

## Problem Statement

The FHIRPath parser fails to handle polymorphic type navigation, preventing expressions like `Observation.value.is(Quantity)` and `Observation.value.value > 180.0` from being parsed.

## Current Failures

**Type Checking (10 failures):**
- `Observation.value.is(Quantity)` - Parse fails
- `Observation.value is Quantity` - Parse fails
- `Observation.issued is instant` - Parse fails
- `Observation.value.as(Quantity).unit` - Parse fails

**Comparison Operators (33 failures):**
- `Observation.value.value > 180.0` - Parse fails
- `Observation.value.value > 0.0` - Parse fails
- `Observation.value.value < 190` - Parse fails

**Polymorphic Navigation (63 "Other" failures):**
- `Observation.value.unit` - Parse fails
- Many other polymorphic navigation patterns

## Root Cause

The parser doesn't properly handle:
1. **Polymorphic field navigation** - `Observation.value` where value can be multiple types
2. **Type operations on polymorphic results** - `.is()`, `.as()` after polymorphic navigation
3. **Chained navigation through polymorphic fields** - `.value.value` to access nested properties

## Architecture Alignment

This fix must align with unified FHIRPath architecture:
- **Parser responsibility** - Handle polymorphic type resolution during parsing
- **Type system integration** - Use FHIR StructureDefinition for type discrimination
- **Thin dialects** - Database-specific logic isolated to dialect layer only
- **Population-first** - Support polymorphic queries across populations

## Implementation Plan

### 1. Polymorphic Type Resolution

**Add polymorphic field detection:**
- Detect when navigating through fields with multiple possible types
- Use FHIR StructureDefinition to determine type choices
- Implement type discriminator logic

**Type discrimination patterns:**
```python
# Observation.value can be: Quantity, Ratio, SampledData, Period, etc.
# Need to add type discriminator based on actual resource structure
```

### 2. Parser Enhancement

**Update IdentifierNode navigation:**
- Handle polymorphic field traversal
- Add type context to navigation nodes
- Support chained navigation through polymorphic fields

**Type operation integration:**
- Allow `.is()`, `.as()` after polymorphic navigation
- Resolve type at parse time using structure definitions
- Generate appropriate AST nodes for type checking/casting

### 3. AST Extensions

**Add polymorphic context:**
```python
class PolymorphicNavigationNode(EnhancedASTNode):
    possible_types: List[str]  # ['Quantity', 'Ratio', 'Period', ...]
    type_discriminator: Optional[str]  # Field to discriminate type
```

### 4. SQL Translation

**Generate type-aware SQL:**
- Use UNION or CASE for polymorphic types
- Add type discriminator filters
- Handle nested navigation through polymorphic fields

Example SQL pattern:
```sql
-- For Observation.value.unit
SELECT
  o.resource,
  CASE
    WHEN json_extract(o.resource, '$.value.value') IS NOT NULL THEN 'Quantity'
    WHEN json_extract(o.resource, '$.value.start') IS NOT NULL THEN 'Period'
    ELSE 'Other'
  END AS value_type,
  CASE
    WHEN json_extract(o.resource, '$.value.value') IS NOT NULL
      THEN json_extract(o.resource, '$.value.unit')
    ELSE NULL
  END AS unit
FROM Observation o
```

## Testing Strategy

- Run official FHIRPath test suite for polymorphic types (73+ tests)
- Verify type operations on polymorphic fields
- Test chained navigation through polymorphic fields
- Validate SQL generation for all polymorphic patterns

## Success Criteria

- [ ] All 10 type checking tests pass
- [ ] All 33 comparison operator tests with polymorphic fields pass
- [ ] Polymorphic navigation works correctly
- [ ] Type discrimination logic is correct
- [ ] No regressions in existing functionality

## Dependencies

- Depends on: None (foundational parser fix)
- Blocks: SP-106-002 through SP-106-007 (most tests require polymorphic navigation)

## Technical Considerations

- FHIR StructureDefinition loading required for type resolution
- Performance impact of type discrimination must be minimized
- SQL UNION vs CASE trade-offs for polymorphic types
- Need to handle recursive polymorphic types (e.g., Extension)
