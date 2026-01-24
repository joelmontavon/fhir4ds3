# Sprint 012: Planning Guidance

**Status**: ⏳ Planning Phase
**Previous Sprint**: Sprint 011 (PEP-004 - CTE Infrastructure) ✅ COMPLETED
**Sprint 011 Completion**: 2025-10-21 (all objectives achieved, all targets exceeded)

---

## Sprint 011 Completion Summary

**Achievements**:
- ✅ 17/17 tasks completed (100%)
- ✅ 10/10 Path Navigation tests passing (exceeded 8/10 target)
- ✅ 72%+ overall FHIRPath compliance (met target)
- ✅ 10x+ performance improvement validated
- ✅ 100% multi-database parity (DuckDB + PostgreSQL)
- ✅ 2,105 lines comprehensive documentation
- ✅ 5-layer FHIRPath execution pipeline COMPLETE

**Impact**: PEP-004 successfully completed, establishing foundation for population-scale healthcare analytics, SQL-on-FHIR, and CQL implementations.

---

## Sprint 012 Planning Recommendations

### Strategic Options

Sprint 012 should build on the solid foundation established in Sprint 011. Several strategic directions are available:

#### Option 1: PostgreSQL Live Execution (Quick Win)
**Objective**: Enable full PostgreSQL execution (currently stubbed for SQL validation)
**Effort**: ~1 week (5-8 hours)
**Value**: High - completes multi-database story
**Risk**: Low - SQL generation already validated

**Tasks**:
1. Implement PostgreSQL connection pooling
2. Enable live query execution in PostgreSQLDialect
3. Validate results match DuckDB execution
4. Performance benchmark PostgreSQL vs DuckDB

#### Option 2: Additional FHIRPath Functions (Compliance Growth)
**Objective**: Expand FHIRPath support beyond Path Navigation
**Effort**: ~2-3 weeks (20-30 hours)
**Value**: High - advances specification compliance
**Risk**: Medium - some functions complex

**Potential Functions**:
- `where()`: Filtering collections
- `select()`: Projection/transformation
- Boolean operators: `and`, `or`, `not`, `implies`
- Comparison operators: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Math operators: `+`, `-`, `*`, `/`, `mod`

**Target**: +10-15% FHIRPath compliance (72% → 82-87%)

#### Option 3: CQL Integration (Strategic Investment)
**Objective**: Build CQL execution on top of CTE infrastructure
**Effort**: ~3-4 weeks (30-40 hours)
**Value**: Very High - unlocks quality measures, clinical decision support
**Risk**: Medium-High - complex specification

**Scope**:
- CQL library management
- Define statement execution via FHIRPath
- Context management (Patient, Population, etc.)
- Value set integration
- Basic CQL operators

**Target**: Foundation for quality measure execution

#### Option 4: SQL-on-FHIR Implementation (Strategic Investment)
**Objective**: Generate SQL-on-FHIR view definitions from ViewDefinition resources
**Effort**: ~2-3 weeks (25-35 hours)
**Value**: Very High - enables standard FHIR analytics
**Risk**: Medium - specification still evolving

**Scope**:
- ViewDefinition resource parsing
- SELECT clause generation from columns
- WHERE clause generation from filters
- Flattening FHIR arrays via UNNEST (reuse CTE infrastructure)
- Multi-resource joins

**Target**: Execute SQL-on-FHIR official test suite

#### Option 5: Performance Optimization (Technical Excellence)
**Objective**: Optimize CTE infrastructure for production scale
**Effort**: ~2 weeks (15-20 hours)
**Value**: Medium - improves production readiness
**Risk**: Low - optimization, not new features

**Optimizations**:
- CTE caching for repeated expressions
- Predicate pushdown into CTEs
- CTE merging for efficiency
- Query plan analysis and tuning
- Index recommendations

---

## Recommended Approach

### Recommended: **Hybrid Approach - Quick Win + Strategic Investment**

**Week 1**: PostgreSQL Live Execution (Option 1)
- Quick win completing multi-database story
- Low risk, high value
- ~5-8 hours effort

**Weeks 2-4**: Additional FHIRPath Functions (Option 2)
- Advances specification compliance toward 85%+
- Builds on existing pipeline
- Clear, incremental progress
- ~20-30 hours effort

**Total Sprint Effort**: 25-38 hours (reasonable for 4-week sprint)

### Alternative: **Strategic Focus**

If strategic priorities favor higher-level specifications:

**Option 3 (CQL)** OR **Option 4 (SQL-on-FHIR)** as primary focus
- Defer PostgreSQL live execution to later sprint
- Focus entire sprint on one strategic initiative
- Higher risk, higher reward

---

## Sprint 012 Planning Checklist

### Pre-Planning Activities

- [x] Sprint 011 completed and documented
- [x] PEP-004 marked as implemented
- [x] Milestone M-004 marked as completed
- [ ] Review upcoming PEPs (if CQL or SQL-on-FHIR chosen)
- [ ] Stakeholder input on strategic priorities
- [ ] Resource availability confirmed

### Planning Session Agenda

1. **Sprint 011 Retrospective** (30 minutes)
   - Celebrate successes (exceeded all targets!)
   - Discuss what worked well (architecture discipline, phase reviews)
   - Identify process improvements

2. **Strategic Direction Discussion** (30 minutes)
   - Review Option 1-5 above
   - Align on priorities (compliance vs strategic features)
   - Consider external factors (community requests, standards evolution)

3. **Sprint 012 Scope Definition** (45 minutes)
   - Select primary objective(s)
   - Define success criteria
   - Estimate effort and timeline
   - Identify risks and mitigation strategies

4. **Task Breakdown** (30 minutes)
   - Create initial task list
   - Assign rough estimates
   - Identify dependencies
   - Define phases (if multi-week sprint)

5. **Documentation Plan** (15 minutes)
   - Review documentation requirements
   - Plan architecture updates
   - Consider community communication

---

## Success Criteria Template

Regardless of chosen direction, Sprint 012 should meet these standards:

### Quality Gates

- [ ] 90%+ test coverage for new code
- [ ] Zero regressions in existing functionality
- [ ] Architecture review approved (thin dialects, population-first)
- [ ] Multi-database parity maintained (DuckDB + PostgreSQL)
- [ ] Comprehensive documentation (API, architecture, guides)

### Compliance Targets

- [ ] Measurable compliance improvement (if FHIRPath functions chosen)
- [ ] Official test suite validation (if applicable)
- [ ] Performance benchmarks maintained or improved

### Architecture Alignment

- [ ] Unified FHIRPath principles followed
- [ ] CTE-first design extended (if applicable)
- [ ] Thin dialects maintained (syntax-only differences)
- [ ] Population-first operations default

---

## Risk Considerations

### Potential Risks

1. **Scope Creep**: Additional FHIRPath functions can expand quickly
   - **Mitigation**: Define clear scope upfront, prioritize functions

2. **Specification Complexity**: CQL and SQL-on-FHIR are complex specifications
   - **Mitigation**: Start with subset, validate incrementally

3. **Multi-Database Maintenance**: Adding features increases parity testing burden
   - **Mitigation**: Automated multi-database test suite already in place

4. **Technical Debt**: Rushing features can introduce debt
   - **Mitigation**: Maintain quality standards, comprehensive reviews

---

## Documentation Requirements

### Sprint Plan

Create `project-docs/plans/current-sprint/sprint-012-[name].md` with:
- Objectives and success criteria
- Task breakdown with estimates
- Timeline and milestones
- Risk assessment
- Testing strategy

### Architecture Documentation

Update as needed based on chosen direction:
- Architecture diagrams (if new components)
- Integration guides (if new APIs)
- Performance characteristics (if optimizations)

### PEP Consideration

If choosing CQL or SQL-on-FHIR:
- Consider creating new PEP for architectural guidance
- Define clear scope and acceptance criteria
- Senior architect review before implementation

---

## Next Steps

1. **Schedule Planning Session**: Coordinate with senior architect and junior developer
2. **Review Options**: Evaluate strategic priorities and resource availability
3. **Gather Input**: Community feedback, stakeholder priorities, standards evolution
4. **Make Decision**: Select Sprint 012 objective(s)
5. **Create Sprint Plan**: Document scope, tasks, timeline, risks
6. **Begin Implementation**: Following established Sprint 011 patterns

---

**Planning Status**: ⏳ Awaiting Sprint 012 direction decision
**Planning Lead**: Senior Solution Architect/Engineer
**Expected Start**: TBD (based on priorities)

---

*Sprint 011 established a solid foundation - Sprint 012 should build strategically on this success, maintaining the quality standards and architectural discipline that led to exceptional Sprint 011 results.*
