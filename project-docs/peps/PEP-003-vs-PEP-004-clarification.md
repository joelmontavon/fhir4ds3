# PEP-003 vs PEP-004: Clarification and Status

**Document Type**: Architectural Clarification
**Date Created**: 2025-10-19
**Author**: Senior Solution Architect/Engineer
**Purpose**: Clarify the relationship, status, and dependencies between PEP-003 and PEP-004

---

## Executive Summary

**Key Points**:
1. **PEP-003 (AST-to-SQL Translator)**: ✅ Implemented but **incomplete** for full FHIRPath compliance
2. **PEP-004 (CTE Infrastructure)**: ❌ **Not implemented** - critical architectural gap
3. **Dependency**: PEP-004 is **required** for PEP-003 to achieve full specification compliance
4. **Current Blocker**: Path navigation (67% of failures) cannot be fixed without PEP-004

---

## PEP-003: AST-to-SQL Translator

### Status: ⚠️ Partially Implemented

**Completion Summary** (from `peps/summaries/pep-003-ast-to-sql-translator/implementation-summary.md`):
- **Implementation Date**: 2025-09-30 to 2025-10-02 (Sprint 005)
- **Status**: ✅ Marked as "IMPLEMENTED"
- **Healthcare Use Cases**: 95.1% success rate ✅
- **Official FHIRPath Tests**: 45-60% (now measured at 36-65%)

### What PEP-003 Does

**Responsibility**: Convert FHIRPath AST nodes → SQL fragments

**Example**:
```python
# Input: FHIRPath expression "Patient.name.given"
# Output: List of SQL fragments
fragments = [
    SQLFragment("json_extract(resource, '$.name')"),
    SQLFragment("LATERAL UNNEST(...)", requires_unnest=True),
    SQLFragment("json_extract(name_item, '$.given')")
]
```

**Capability**: Generates **SQL fragments**, not complete SQL queries

### What PEP-003 Does NOT Do

❌ **Does NOT wrap fragments in CTEs**
❌ **Does NOT generate WITH clauses**
❌ **Does NOT assemble fragments into executable SQL**
❌ **Does NOT resolve CTE dependencies**

**These are PEP-004 responsibilities.**

### PEP-003 Success Areas

✅ **Literal translation**: Strings, numbers, booleans, dates (100%)
✅ **Basic operators**: Arithmetic, comparison, logical (100%)
✅ **Simple path navigation**: `Patient.birthDate` (works)
✅ **Healthcare patterns**: LOINC, SNOMED, demographics (95.1%)
✅ **Architecture**: Thin dialects, multi-database (100%)

### PEP-003 Current Limitations

❌ **Array navigation**: `Patient.name.given` (BLOCKED by missing PEP-004)
❌ **Nested arrays**: Multi-level UNNEST (requires PEP-004)
❌ **Complete SQL generation**: Fragments need CTE wrapping (PEP-004)
❌ **Path Navigation**: 0/9 tests (0%) - **CRITICAL BLOCKER**

**Root Cause**: PEP-003 generates fragments, but nothing converts them to executable SQL.

---

## PEP-004: CTE Infrastructure

### Status: ❌ Not Implemented

**Current State**:
- **Draft PEP**: Created 2025-10-19
- **Implementation**: Not started
- **Status**: Needs review and approval
- **Priority**: **CRITICAL** - unblocks Sprint 010

### What PEP-004 Does

**Responsibility**: Convert SQL fragments → Executable SQL queries

**Components**:
1. **CTEBuilder**: Wraps fragments in CTE structures with UNNEST support
2. **CTEAssembler**: Combines CTEs into monolithic queries with dependency ordering

**Example**:
```python
# Input: SQL fragments from PEP-003
fragments = [...]

# CTEBuilder wraps in CTEs
builder = CTEBuilder(dialect=duckdb_dialect)
ctes = builder.build_cte_chain(fragments)

# CTEAssembler creates complete SQL
assembler = CTEAssembler(dialect=duckdb_dialect)
sql = assembler.assemble_query(ctes)

# Output: Complete executable SQL with WITH clause
"""
WITH
  cte_1 AS (...),
  cte_2 AS (... LATERAL UNNEST ...),
  cte_3 AS (...)
SELECT * FROM cte_3;
"""
```

### What PEP-004 Enables

✅ **Array navigation**: `Patient.name.given` execution
✅ **Nested UNNEST**: Multi-level array flattening
✅ **Complete SQL**: Executable queries from fragments
✅ **Path Navigation**: 0% → 80%+ (8/10 tests)
✅ **Population analytics**: 10x+ performance improvements
✅ **Monolithic queries**: CTE-based execution

### Why PEP-004 is Required

**Architectural Reality**:
```
Parser (PEP-002) ✅ → Translator (PEP-003) ✅ → ??? ❌ → Database Execution ✅
                                                      ↑
                                         Missing: CTE Infrastructure (PEP-004)
```

**Current Situation**:
- PEP-003 generates: `List[SQLFragment]`
- Database executes: Complete SQL strings
- **Gap**: No component converts fragments → SQL

**Impact**: 67% of Path Navigation tests blocked

---

## Dependency Relationship

### Design Decision (from PEP-003 specification)

**From `peps/accepted/pep-003-ast-to-sql-translator.md`**:

> "Future PEP-004 will build on this foundation to add:
> - CTE Builder (wraps fragments)
> - CTE Optimizer (merges, pushes predicates)
> - CTE Assembler (combines into monolithic SQL)"

**Intentional Separation**:
- **PEP-003**: Translation logic (AST → SQL fragments)
- **PEP-004**: Structure and assembly (Fragments → Complete SQL)

**Why Separate?**:
1. **Focused scope**: Each PEP tackles one well-defined component
2. **Incremental delivery**: Can implement and test translator independently
3. **Clear dependencies**: PEP-004 depends on PEP-003 translator output
4. **Parallel development**: Different developers can work on each PEP

### Execution Pipeline

**Complete Pipeline**:
```
1. Parser (PEP-002)     → Creates FHIRPath AST from expression string
2. Translator (PEP-003) → Converts AST nodes → SQL fragments
3. CTE Builder (PEP-004) → Wraps fragments → CTE structures
4. CTE Assembler (PEP-004) → Combines CTEs → Complete SQL query
5. Database Execution   → Executes SQL and returns results
```

**Current State**:
```
1. Parser (PEP-002)     ✅ COMPLETE
2. Translator (PEP-003) ✅ COMPLETE
3. CTE Builder (PEP-004) ❌ MISSING ← BLOCKER
4. CTE Assembler (PEP-004) ❌ MISSING ← BLOCKER
5. Database Execution   ✅ COMPLETE (but nothing to execute)
```

---

## Status Clarification

### PEP-003 "Implemented" Status

**Question**: If PEP-003 is marked "Implemented", why does it need PEP-004?

**Answer**: PEP-003 is implemented **as specified** in its original scope:
- ✅ AST → SQL fragment translation (COMPLETE)
- ✅ Visitor pattern implementation (COMPLETE)
- ✅ Dialect method calls for syntax (COMPLETE)
- ✅ Healthcare use case coverage 95.1% (COMPLETE)

**However**: PEP-003 specification explicitly deferred CTE generation to future work:

> "This translator outputs a sequence of `SQLFragment` objects. Future components (CTE Builder, CTE Assembler) combine fragments into complete queries."

**Conclusion**:
- PEP-003 is complete **as designed**
- PEP-003 **intentionally does not** include CTE infrastructure
- PEP-004 is the **documented next step** to complete the pipeline

### Why This Matters Now

**From Sprint 009 Completion Analysis**:
- Path Navigation: 0/9 tests (0%) ← **BLOCKED**
- Overall Compliance: 36-65% ← **Below target**
- Sprint 010 Goal: 72% compliance ← **Unachievable without PEP-004**

**From SP-010-001 Review** (Senior Architect rejection):

> "The actual blocker is the missing CTE (Common Table Expression) infrastructure. PEP-003 translator generates SQL fragments, but there's no component to:
> 1. Wrap these fragments in WITH clauses (CTEs)
> 2. Handle LATERAL UNNEST for array flattening
> 3. Assemble fragments into a complete, executable SQL query"

**Architectural Decision**:
- **Prohibited**: Python-based row-by-row processing (fhirpathpy fallback)
- **Required**: SQL-based population-scale execution
- **Blocker**: Cannot generate executable SQL without PEP-004

---

## Implementation Priority

### Why PEP-004 is CRITICAL Now

**1. Unblocks Sprint 010 Goals**:
- Target: 72% compliance (from 36-65%)
- Path Navigation: 0% → 80%+ (enables +60-70% in this category)
- Without PEP-004: Goal **unachievable**

**2. Completes Documented Architecture**:
- Architecture explicitly defines 5-layer pipeline
- Layers 1, 2, 5 complete (Parser, Translator, Execution)
- Layers 3, 4 missing (CTE Builder, CTE Assembler)
- PEP-004 fills critical gap

**3. Enables Future Features**:
- SQL-on-FHIR v2.0: Requires CTE-based execution
- CQL Framework: Depends on multi-expression CTE assembly
- Quality Measures: Needs monolithic query performance
- Population Analytics: Requires 10x+ improvements (promised in architecture)

**4. Prevents Technical Debt**:
- Workarounds (fhirpathpy) violate architecture
- Row-by-row processing creates 100x performance degradation
- Proper CTE solution avoids future rework

### Recommended Timeline

**Sprint 010** (Immediate - Next 3-4 weeks):
- **Week 1**: PEP-004 review and approval
- **Weeks 1-4**: PEP-004 implementation (CTE infrastructure)
- **Week 5**: SP-010-001 execution (Path Navigation unblocked)

**Sprint 011** (Follow-up):
- Complete remaining FHIRPath functions
- Achieve 85-90% compliance
- Begin SQL-on-FHIR implementation

---

## Recommendations

### For Sprint 010

**1. PRIORITY: Approve and Implement PEP-004**

**Justification**:
- Unblocks 60-70% of Path Navigation tests
- Enables Sprint 010 compliance target (72%)
- Completes documented architectural pipeline
- Prevents accumulation of technical debt

**Effort**: 3-4 weeks (MVP scope)

**Status**: PEP-004 draft ready for review

**2. Defer Path Navigation Until PEP-004 Complete**

**Rationale**:
- SP-010-001 cannot proceed without CTE infrastructure
- Attempting workarounds violates architecture
- Senior architect already rejected alternative approaches

**3. Re-assess PEP-003 "Complete" Status**

**Options**:
- **Option A**: Keep PEP-003 as "Implemented" with note: "Requires PEP-004 for full compliance"
- **Option B**: Change to "Partially Implemented" until PEP-004 complete
- **Recommendation**: **Option A** - PEP-003 met its defined scope, PEP-004 was always planned

### For Documentation

**1. Update PEP-003 Implementation Summary**

Add section:
> **Limitations**: PEP-003 generates SQL fragments as designed. CTE infrastructure (PEP-004) required to convert fragments into executable SQL for array operations and path navigation.

**2. Create Cross-Reference**

In PEP-003:
> **See Also**: PEP-004 (CTE Infrastructure) - Required companion for complete SQL generation

In PEP-004:
> **Depends On**: PEP-003 (AST-to-SQL Translator) - Provides SQL fragments as input

**3. Update Architecture Docs**

Clarify 5-layer pipeline with current status:
- Layer 1: Parser (PEP-002) ✅
- Layer 2: Translator (PEP-003) ✅
- Layer 3: CTE Builder (PEP-004) ❌ ← PRIORITY
- Layer 4: CTE Assembler (PEP-004) ❌ ← PRIORITY
- Layer 5: Database Execution ✅

---

## Conclusion

**PEP-003 and PEP-004 are complementary components**:

- **PEP-003**: Handles translation logic (AST → Fragments) ✅ **COMPLETE**
- **PEP-004**: Handles structure and assembly (Fragments → SQL) ❌ **REQUIRED**

**Current Blocker**: Missing PEP-004 prevents:
- Path Navigation execution (0/9 tests)
- Array operation support
- Monolithic SQL generation
- Sprint 010 compliance targets

**Recommendation**: **Implement PEP-004 immediately** as Sprint 010 top priority.

**Timeline**: 3-4 weeks for MVP implementation.

**Impact**: Unblocks 60-70% of Path Navigation, enables 72% overall compliance target.

---

**Status**: Active - Sprint 010 planning in progress
**Next Action**: PEP-004 review and approval
**Owner**: Senior Solution Architect/Engineer

---

*This clarification establishes the relationship between PEP-003 and PEP-004, confirming that PEP-004 implementation is the critical priority for Sprint 010 success.*
