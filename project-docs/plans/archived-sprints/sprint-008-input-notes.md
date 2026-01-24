# Sprint 008 Planning Input Notes

**Created**: 2025-10-09
**Source**: Sprint 007 Findings and Analysis
**Purpose**: Ensure critical insights from Sprint 007 inform Sprint 008 planning

---

## Critical Finding: convertsTo*() Categorization (SP-007-013)

### Decision Summary

**Finding**: `convertsTo*()` functions are **Type Conversion Functions** (FHIRPath Section 5.5), NOT path navigation operations.

**Source**: Complete analysis in `project-docs/investigations/convertsto-functions-categorization.md`

**Evidence**:
1. FHIRPath specification explicitly categorizes in "Conversion" category (Section 5.5)
2. Official test suite groups in "testTypes" category (73 tests total)
3. Implementation structure separates from path navigation code

### Impact on Sprint 008 Planning

#### DO NOT Include in Sprint 008

**Type Conversion Functions** (defer to future "Type System Sprint"):
- convertsToBoolean(), convertsToInteger(), convertsToDecimal() (13 tests each)
- convertsToString() (8 tests)
- convertsToDate(), convertsToDateTime(), convertsToTime() (3-9 tests each)
- convertsToQuantity() (12 tests)
- **Total: 73 tests to exclude from Sprint 008 scope**

#### DO Include in Sprint 008

**Core Path Navigation and Filtering** (FHIRPath Sections 5.1-5.2):
- Path traversal fixes from SP-007-011/012 findings
- Type operations: `is`, `as`, `ofType` (Filtering and Projection category)
- Core subsetting functions: `first`, `last`, `tail`, `skip`, `take`
- Existence functions: `exists`, `empty`, `all`
- Collection operations: `where`, `select`, array/path operations

### Recommended Sprint 008 Goal

**Recommended**: "Achieve 70% of path navigation and core filtering operations"
- Explicitly exclude type conversion from this goal
- Focus on structural navigation and filtering
- Achievable without the 73 convertsTo*() tests

### Future Planning

**Sprint 009 or later**: Create dedicated "Type System & Conversion" sprint
- Implement all convertsTo*() functions (8 functions, 73 tests)
- Implement all to*() conversion functions (actual conversion, not just testing)
- High-value sprint with significant test count improvement
- May discover shared validation logic between convertsTo*() and to*()

---

## Path Navigation Quick Wins (SP-007-012)

### Completed Improvements

[Note: Add findings from SP-007-012 implementation report when available]

### Remaining Work for Sprint 008

[Note: Add remaining path navigation tasks identified in SP-007-011/012 reports]

---

## Metric Clarifications for Sprint 008

### Path Navigation Metrics

**Updated Definition**: Path navigation metrics should **exclude** convertsTo*() functions.

**Correct Path Navigation Scope**:
- Structural path traversal (Patient.name, Observation.value)
- Navigation functions (where, select, first, ofType)
- Array/collection operations on paths
- Resource relationship navigation

**Separate Tracking**: Create "Type Conversion Functions" category for convertsTo*() and to*()

---

## Architecture Alignment Notes

### Specification Categories for Sprint Planning

FHIRPath specification has clear top-level function categories that map well to sprint boundaries:

1. **Existence Functions** (empty, exists, all) - Sprint 008 candidate
2. **Filtering and Projection** (where, select, ofType) - Sprint 008 PRIORITY
3. **Subsetting** (first, last, tail, skip, take) - Sprint 008 candidate
4. **Combining** (union, combine) - Sprint 008 candidate
5. **Conversion** (toBoolean, convertsToBoolean, etc.) - DEFER to Sprint 009+
6. **String Manipulation** - Sprint 007 COMPLETE ✅
7. **Math Functions** - Sprint 006 COMPLETE ✅
8. **Tree Navigation** (children, descendants) - Future sprint
9. **Utility Functions** - Assess per function

### Sprint Boundary Strategy

**Insight**: FHIRPath specification categories provide natural sprint boundaries.

**Application for Sprint 008**:
- Focus on Sections 5.1-5.2 (Filtering and Projection)
- Defer Section 5.5 (Conversion) to dedicated sprint
- Maximize test coverage within focused scope

---

## Quality and Compliance Notes

### Multi-Database Testing

**Requirement**: All Sprint 008 implementations must validate in both environments:
- DuckDB: Primary development and testing
- PostgreSQL: Production target validation

### Thin Dialect Pattern

**Mandate**: 100% compliance with thin dialect architecture
- All business logic in translator
- Dialects contain ONLY syntax differences
- Zero divergence in translation logic between databases

---

## Sprint 008 Success Metrics (Proposed)

### Test Coverage Targets

**Path Navigation and Filtering** (excluding convertsTo*() - 73 tests):
- Current: ~26 passing (19.8% of 131 tests)
- Target: 70%+ of actual path navigation tests (excluding convertsTo*())
- Note: Need to recalculate base after excluding convertsTo*() tests

**Overall Official Test Coverage**:
- Current: 62.5% (584/934 tests) after Sprint 006
- Sprint 007 target: 70%+ (654+/934 tests)
- Sprint 008 target: TBD based on Sprint 007 final results

### Quality Targets

- Unit test coverage: 92%+ maintained
- Multi-database consistency: 100% maintained
- Performance: <10ms average translation maintained
- Architecture compliance: 100% maintained (thin dialect pattern)

---

## Risk Considerations for Sprint 008

### Known Risks

1. **Path Navigation Complexity**: Investigation (SP-007-011) may reveal deeper issues than anticipated
2. **Test Categorization**: Ensure convertsTo*() properly excluded from metrics
3. **Multi-DB Differences**: Path navigation may expose database-specific challenges

### Mitigation Strategies

1. Use SP-007-011/012 findings to scope Sprint 008 realistically
2. Create separate metrics for path navigation vs type conversion
3. Test database-specific syntax early in sprint

---

## Action Items for Sprint 008 Planning

### Before Sprint 008 Starts

- [ ] Review final Sprint 007 test coverage results
- [ ] Recalculate path navigation metrics excluding convertsTo*() tests
- [ ] Review SP-007-011 investigation report for Sprint 008 scope
- [ ] Review SP-007-012 implementation report for lessons learned
- [ ] Create Sprint 008 plan with proper categorization

### Documentation Updates Needed

- [ ] Update Sprint 008 plan with convertsTo*() exclusion
- [ ] Add "Type Conversion Functions" as separate tracking category
- [ ] Reference SP-007-013 analysis in Sprint 008 scope definition
- [ ] Create backlog item for future "Type System Sprint"

---

## References

**Key Documents**:
- `project-docs/investigations/convertsto-functions-categorization.md` - SP-007-013 complete analysis
- `project-docs/plans/reviews/SP-007-013-review.md` - Senior architect approval
- `project-docs/plans/tasks/SP-007-013-analyze-convertsto-functions.md` - Task documentation
- `project-docs/investigations/2025-10-07-path-navigation-failures.md` - SP-007-011 investigation (when available)
- Sprint 007 plan: `project-docs/plans/current-sprint/sprint-007-plan.md`

**FHIRPath Specification Sections**:
- Section 5.2: Filtering and Projection (where, select, ofType) - Sprint 008 FOCUS
- Section 5.5: Conversion (convertsTo*(), to*()) - DEFER to Sprint 009+

---

**Document Owner**: Senior Solution Architect/Engineer
**Next Review**: During Sprint 008 planning session
**Status**: Active planning input - incorporate into Sprint 008 plan

---

*This document ensures SP-007-013 findings are not lost and properly inform Sprint 008 planning decisions.*
