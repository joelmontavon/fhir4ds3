# Task SP-011-013-Part-2: Array Navigation Completion

**Task ID**: SP-011-013-part-2
**Parent Task**: SP-011-013 (End-to-End Integration with PEP-003 Translator)
**Sprint**: TBD (requires translator UNNEST completion)
**Assignee**: Pending
**Created**: 2025-10-20
**Status**: Not Started (Blocked by translator UNNEST support)

---

## Task Overview

Complete the remaining scope for SP-011-013 by enabling full support for Path Navigation expressions that require array flattening. This task activates once the PEP-003 translator emits UNNEST-ready SQL fragments for array traversal.

### Objectives

1. Execute the seven outstanding array/nested expressions end-to-end:
   - `Patient.name`
   - `Patient.telecom`
   - `Patient.address`
   - `Patient.identifier`
   - `Patient.name.given`
   - `Patient.name.family`
   - `Patient.address.line`
2. Expand the integration test suite to 20+ tests with full coverage of array behavior.
3. Validate multi-database parity (DuckDB/PostgreSQL) for all new expressions.
4. Re-run performance validation at population scale once UNNEST support lands.

### Dependencies

- **Blocking**: Translator UNNEST implementation (PEP-003 updates)
- **Upstream Tasks**: SP-011-007 through SP-011-012 (CTE UNNEST + assembly) – already complete

### Acceptance Criteria

- [ ] Translator emits `SQLFragment` objects with `requires_unnest=True` and populated metadata for the expressions above
- [ ] Executor integration tests exercise all 10 planned Path Navigation expressions (scalar + array)
- [ ] Coverage remains ≥90% for executor + integration modules
- [ ] PostgreSQL parity confirmed with real execution (no stubbed results)
- [ ] Documentation updated (task doc, architecture notes, sprint log)

### Progress Tracking

| Date | Status | Notes |
|------|--------|-------|
| 2025-10-20 | Not Started | Awaiting translator UNNEST support to begin implementation |

### Next Steps Once Unblocked

1. Coordinate with translator owners to confirm fragment metadata contract.
2. Re-enable xfailed integration tests and extend fixtures as needed.
3. Add additional edge-case tests (empty arrays, null values, mixed resource data).
4. Recompute performance and coverage metrics; update documentation.

---

*Created automatically during SP-011-013 review follow-up to ensure remaining scope is tracked explicitly.*
