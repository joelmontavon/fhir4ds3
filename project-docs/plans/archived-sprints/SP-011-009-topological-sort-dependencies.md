# Task SP-011-009: Implement Topological Sort for CTE Dependencies

**Task ID**: SP-011-009
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Implement Topological Sort for CTE Dependencies
**Assignee**: Junior Developer
**Created**: 2025-10-20
**Last Updated**: 2025-10-20

---

## Task Overview

### Description

Implement the `_order_ctes_by_dependencies()` method in the CTEAssembler class to perform topological sorting of CTE objects based on their dependency relationships. This method ensures that CTEs are defined before they are referenced in the WITH clause, preventing SQL execution errors from forward references. The implementation must handle complex dependency chains, detect circular dependencies, and maintain the thin dialect architecture principle (zero business logic in dialects).

**Context**: This task is the first component of Phase 3 (CTE Assembly and Dependencies). The topological sort is critical for assembling multiple CTEs into a valid WITH clause where each CTE can only reference CTEs that appear before it in the definition order. Currently, Phase 1 established the CTE data structures with `depends_on` field tracking, and Phase 2 implemented UNNEST operations. This task enables correct ordering of those CTEs for execution.

**Example Scenario**:
```python
# Input CTEs (potentially out of order)
ctes = [
    CTE(name="cte_3", query="...", depends_on=["cte_2"]),
    CTE(name="cte_1", query="...", depends_on=[]),
    CTE(name="cte_2", query="...", depends_on=["cte_1"])
]

# After topological sort
ordered_ctes = [
    CTE(name="cte_1", query="...", depends_on=[]),      # No dependencies - first
    CTE(name="cte_2", query="...", depends_on=["cte_1"]),  # Depends on cte_1
    CTE(name="cte_3", query="...", depends_on=["cte_2"])   # Depends on cte_2
]
```

### Category
- [x] Feature Implementation
- [ ] Bug Fix
- [ ] Architecture Enhancement
- [ ] Performance Optimization
- [ ] Testing
- [ ] Documentation
- [ ] Process Improvement

### Priority
- [x] Critical (Blocker for sprint goals)
- [ ] High (Important for sprint success)
- [ ] Medium (Valuable but not essential)
- [ ] Low (Stretch goal)

---

## Requirements

### Functional Requirements

1. **Topological Sort Implementation**: Implement standard topological sort algorithm (Kahn's algorithm or DFS-based)
   - Build dependency graph from CTE objects
   - Perform topological ordering
   - Return ordered list of CTEs

2. **Circular Dependency Detection**: Detect and report circular dependencies
   - Identify cycles in dependency graph
   - Provide clear error message with cycle path
   - Example: `cte_1 → cte_2 → cte_3 → cte_1` is invalid

3. **Missing Dependency Detection**: Validate that all dependencies exist
   - Check that each CTE in `depends_on` list exists in input
   - Provide clear error message listing missing CTEs
   - Example: If `cte_2` depends on `cte_5` but `cte_5` not in list, raise error

4. **Empty Dependency Handling**: Correctly handle CTEs with no dependencies
   - CTEs with empty `depends_on` list should appear first
   - Multiple independent CTEs can appear in any order relative to each other

5. **Stability Preservation**: Maintain relative order of independent CTEs
   - If `cte_1` and `cte_2` have no dependencies, preserve their input order
   - Enables predictable, testable output

### Non-Functional Requirements

- **Performance**: O(V + E) time complexity where V = number of CTEs, E = number of dependencies
- **Correctness**: 100% correct ordering (no SQL forward reference errors)
- **Error Messages**: Clear, actionable error messages for circular/missing dependencies
- **Code Quality**: Clean, well-documented implementation following Python best practices

### Acceptance Criteria

- [ ] `_order_ctes_by_dependencies()` method implemented in CTEAssembler
- [ ] Topological sort algorithm working correctly for valid dependency graphs
- [ ] Circular dependency detection with clear error message
- [ ] Missing dependency detection with clear error message
- [ ] Empty dependency (independent CTE) handling correct
- [ ] Stability preservation for independent CTEs
- [ ] Unit tests written and passing (15+ tests covering all cases)
- [ ] Integration tests with real CTE chains passing
- [ ] Code review approved by Senior Solution Architect/Engineer
- [ ] No business logic in dialect classes (thin dialect maintained)

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/cte.py**: Implement `_order_ctes_by_dependencies()` in CTEAssembler class
  - Method signature: `def _order_ctes_by_dependencies(self, ctes: List[CTE]) -> List[CTE]`
  - Returns topologically sorted list of CTEs
  - Raises ValueError for circular or missing dependencies

### File Modifications

- **fhir4ds/fhirpath/sql/cte.py** (MODIFY):
  - Implement `_order_ctes_by_dependencies()` method (currently returns input list unchanged)
  - Add helper methods for graph building and cycle detection
  - Update docstrings with algorithm details

### Database Considerations

- **DuckDB**: No database-specific logic (algorithm is database-agnostic)
- **PostgreSQL**: No database-specific logic (algorithm is database-agnostic)
- **Schema Changes**: None (algorithmic implementation only)

---

## Dependencies

### Prerequisites

1. **SP-011-001**: ✅ Complete (CTE dataclass with `depends_on` field)
2. **SP-011-003**: ✅ Complete (CTEAssembler class structure)
3. **Python Standard Library**: ✅ Available (collections module for graph algorithms)

### Blocking Tasks

- **SP-011-003**: CTEAssembler class structure (provides method stub)

### Dependent Tasks

- **SP-011-010**: `_generate_with_clause()` implementation (needs ordered CTEs)
- **SP-011-011**: `_generate_final_select()` implementation (needs ordered CTEs)
- **SP-011-012**: Assembly unit tests (validates ordering correctness)

---

## Implementation Approach

### High-Level Strategy

Implement **Kahn's Algorithm** for topological sorting with explicit cycle detection. This algorithm is intuitive, efficient (O(V + E)), and provides clear structure for detecting circular dependencies. The implementation will:

1. Build a dependency graph from CTE objects
2. Calculate in-degree (number of dependencies) for each CTE
3. Process CTEs with zero in-degree, removing their edges
4. Detect cycles if any CTEs remain with non-zero in-degree

**Key Design Decisions**:
1. **Algorithm Choice**: Kahn's algorithm over DFS-based approach (clearer for cycle detection)
2. **Stability**: Use queue (not set) to preserve input order for independent CTEs
3. **Error Reporting**: Include full cycle path in error message for debugging
4. **No Dialect Logic**: Algorithm entirely in CTEAssembler, zero dialect involvement

### Implementation Steps

1. **Implement Graph Building** (2 hours)
   - Extract all CTE names from input list
   - Build adjacency list: {cte_name: [list of dependent ctes]}
   - Calculate in-degree for each CTE: {cte_name: count of dependencies}
   - Validation: Check that all dependencies exist
   - **Validation**: Graph structure correct, missing dependencies detected

2. **Implement Topological Sort** (3 hours)
   - Initialize queue with zero in-degree CTEs (preserve order)
   - While queue not empty:
     - Dequeue CTE, add to result list
     - For each dependent of current CTE:
       - Decrement its in-degree
       - If in-degree becomes 0, enqueue it
   - **Validation**: Ordering correct for valid graphs

3. **Implement Circular Dependency Detection** (2 hours)
   - After topological sort, check if any CTEs remain unprocessed
   - If yes, circular dependency exists
   - Trace cycle path using remaining CTEs and dependency graph
   - Raise ValueError with cycle path: "Circular dependency: cte_1 → cte_2 → cte_1"
   - **Validation**: Cycles detected and reported correctly

4. **Add Stability Preservation** (1 hour)
   - Use collections.deque (not set) for queue to maintain insertion order
   - When enqueuing multiple zero in-degree CTEs, preserve input order
   - **Validation**: Independent CTEs maintain relative order

5. **Add Comprehensive Error Messages** (1 hour)
   - Missing dependency: "CTE 'cte_2' depends on 'cte_5' which does not exist"
   - Circular dependency: "Circular dependency detected: cte_1 → cte_2 → cte_3 → cte_1"
   - Include helpful debugging information
   - **Validation**: Error messages clear and actionable

6. **Write Unit Tests** (3 hours)
   - Test valid DAG (directed acyclic graph) ordering
   - Test circular dependency detection
   - Test missing dependency detection
   - Test empty dependency handling
   - Test single CTE
   - Test complex multi-level dependencies
   - Test stability preservation
   - **Validation**: 15+ tests passing, 100% code coverage for method

7. **Integration Testing** (1 hour)
   - Test with real CTE chains from Phase 2 UNNEST operations
   - Verify ordering works with CTEBuilder output
   - Test with CTEAssembler.assemble_query() integration
   - **Validation**: End-to-end ordering working correctly

8. **Code Review and Refinement** (1 hour)
   - Self-review for code quality
   - Check docstrings and inline comments
   - Verify thin dialect principle maintained
   - Request senior architect code review
   - **Validation**: Code review approved

**Estimated Time**: 14h total (increased from 10h in sprint plan for comprehensive error handling and testing)

### Alternative Approaches Considered

- **DFS-Based Topological Sort**: Depth-first search with post-order traversal - **Considered but Kahn's algorithm preferred** (Kahn's provides clearer cycle detection and more intuitive implementation)
- **Sort by Name**: Simply sort CTEs alphabetically - **Rejected** (ignores dependencies entirely, would cause SQL errors)
- **Trust Input Order**: Assume CTEs already ordered - **Rejected** (no validation, fragile to translator changes)

---

## Testing Strategy

### Unit Testing

**Test Organization** (in `tests/unit/fhirpath/sql/test_cte_data_structures.py`):

```python
class TestCTEAssemblerTopologicalSort:
    """Validate topological sorting of CTE dependencies."""

    def test_order_ctes_simple_chain(self, assembler):
        """Simple dependency chain: cte_1 → cte_2 → cte_3."""
        ctes = [
            CTE(name="cte_3", query="...", depends_on=["cte_2"]),
            CTE(name="cte_1", query="...", depends_on=[]),
            CTE(name="cte_2", query="...", depends_on=["cte_1"])
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        assert [c.name for c in ordered] == ["cte_1", "cte_2", "cte_3"]

    def test_order_ctes_independent(self, assembler):
        """Multiple independent CTEs maintain input order."""
        ctes = [
            CTE(name="cte_2", query="...", depends_on=[]),
            CTE(name="cte_1", query="...", depends_on=[]),
            CTE(name="cte_3", query="...", depends_on=[])
        ]
        ordered = assembler._order_ctes_by_dependencies(ctes)
        # Should preserve input order for independent CTEs
        assert [c.name for c in ordered] == ["cte_2", "cte_1", "cte_3"]

    def test_order_ctes_detects_circular_dependency(self, assembler):
        """Circular dependency raises ValueError with cycle path."""
        ctes = [
            CTE(name="cte_1", query="...", depends_on=["cte_3"]),
            CTE(name="cte_2", query="...", depends_on=["cte_1"]),
            CTE(name="cte_3", query="...", depends_on=["cte_2"])
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            assembler._order_ctes_by_dependencies(ctes)

    def test_order_ctes_detects_missing_dependency(self, assembler):
        """Missing dependency raises ValueError listing missing CTE."""
        ctes = [
            CTE(name="cte_1", query="...", depends_on=[]),
            CTE(name="cte_2", query="...", depends_on=["cte_5"])  # cte_5 missing
        ]
        with pytest.raises(ValueError, match="cte_5.*does not exist"):
            assembler._order_ctes_by_dependencies(ctes)

    # ... 11 more tests for complex graphs, empty lists, single CTEs, etc.
```

**Test Coverage Requirements**:
- **Happy Path**: Valid DAGs with various structures (10 tests)
- **Error Cases**: Circular dependencies, missing dependencies (5 tests)
- **Edge Cases**: Empty list, single CTE, all independent (5 tests)
- **Stability**: Preserve order of independent CTEs (3 tests)
- **Integration**: Real CTE chains from CTEBuilder (3 tests)

### Integration Testing

- **With CTEBuilder**: Build CTE chain, verify sorting handles UNNEST dependencies
- **With CTEAssembler**: Full assembly pipeline including sort
- **Multi-Database**: Verify sorted CTEs execute on both DuckDB and PostgreSQL

### Compliance Testing

- **FHIRPath Semantics**: Verify ordering maintains FHIRPath expression semantics
- **Population-First**: Ensure sorted CTEs support population-scale queries
- **No Regression**: Existing Phase 1 and Phase 2 tests continue passing

### Manual Testing

Not applicable - automated test suite is comprehensive.

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Algorithm complexity errors | Low | High | Use well-known Kahn's algorithm, comprehensive unit tests |
| Cycle detection edge cases | Medium | Medium | Test various cycle patterns, include self-loops |
| Performance on large graphs | Low | Medium | O(V + E) is efficient, typical CTE chains <20 nodes |
| Integration with CTEBuilder | Low | Medium | Phase 2 already provides well-formed CTEs with depends_on |

### Implementation Challenges

1. **Cycle Path Tracing**: Building readable error message with full cycle path
   - **Approach**: Track parent relationships during graph traversal, reconstruct path when cycle detected

2. **Stability Preservation**: Maintaining input order for independent CTEs
   - **Approach**: Use deque (not set), process CTEs in input order when ties exist

### Contingency Plans

- **If Kahn's algorithm proves complex**: Fall back to DFS-based topological sort (still O(V + E))
- **If cycle detection difficult**: Implement basic detection first, enhance error messages later
- **If timeline extends**: Prioritize correct ordering over perfect stability (document limitation)

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 1h (review topological sort algorithms, design error messages)
- **Implementation**: 10h (graph building, sorting, cycle detection, error handling)
- **Testing**: 3h (unit tests, integration tests, edge case validation)
- **Documentation**: 1h (docstrings, inline comments, algorithm explanation)
- **Review and Refinement**: 1h (self-review, senior review, refinements)
- **Total Estimate**: 16h (increased from 10h in sprint plan for comprehensive implementation)

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Topological sort is a well-understood algorithm with standard implementations. Primary complexity is in error handling and testing, which is straightforward. Similar to Phase 1 data structure work in complexity.

### Factors Affecting Estimate

- **Cycle Detection Complexity**: +2h if cycle path tracing more complex than expected
- **Edge Case Discovery**: +1h if testing reveals additional edge cases
- **Integration Issues**: +2h if CTEBuilder output requires special handling

---

## Success Metrics

### Quantitative Measures

- **Test Count**: 15+ tests implemented for topological sort
- **Test Pass Rate**: 100% (all tests passing)
- **Code Coverage**: 100% for `_order_ctes_by_dependencies()` method
- **Algorithm Complexity**: O(V + E) verified through code review
- **Performance**: <1ms for typical CTE chains (<20 CTEs)

### Qualitative Measures

- **Code Quality**: Clean, readable implementation of Kahn's algorithm
- **Error Messages**: Clear, actionable messages for circular/missing dependencies
- **Maintainability**: Well-documented algorithm with inline comments

### Compliance Impact

- **Specification Compliance**: Enables correct CTE assembly (prerequisite for FHIRPath execution)
- **Architecture Alignment**: Maintains thin dialect principle (zero dialect logic)
- **Sprint Goal**: Critical component for Phase 3 completion (required for 72%+ compliance)

---

## Documentation Requirements

### Code Documentation

- [x] Method docstring explaining topological sort algorithm
- [x] Inline comments for graph building logic
- [x] Inline comments for cycle detection logic
- [x] Example usage in docstring

### Architecture Documentation

- [ ] No ADR needed (standard algorithm implementation)
- [ ] No architecture changes (implements existing design)

### User Documentation

Not applicable for internal algorithm implementation.

---

## Progress Tracking

### Status
- [x] Not Started
- [x] In Analysis
- [x] In Development
- [x] In Testing
- [x] In Review
- [x] Completed
- [ ] Blocked

**Current Status**: Completed - Pending Review

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-20 | Not Started | Task document created | Awaiting SP-011-008 senior review completion | Begin implementation after Phase 2 approved |
| 2025-10-20 | Completed - Pending Review | Implemented dependency graph ordering with cycle/missing validation; added 16 unit tests and ran full CTE assembler suite | None | Await senior architect review and integration sign-off |

### Completion Checklist

- [x] Graph building logic implemented
- [x] Topological sort (Kahn's algorithm) implemented
- [x] Circular dependency detection working
- [x] Missing dependency detection working
- [x] Stability preservation working
- [x] Error messages clear and actionable
- [x] 15+ unit tests written and passing
- [x] Integration tests passing
- [ ] Code coverage 100% for method
- [x] Self-review complete
- [ ] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches Kahn's algorithm specification
- [x] All error cases handled with clear messages
- [x] Stability preserved for independent CTEs
- [x] Code is clean, readable, and well-documented
- [x] Unit tests cover all branches and edge cases
- [x] Integration with CTEBuilder/CTEAssembler working
- [x] No business logic in dialect classes

**Notes**: Implemented stable Kahn ordering with detailed diagnostics; unit suite exercises missing and cyclic paths, plus integration scenarios.

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: [Pending]
**Review Status**: Pending
**Review Comments**: [To be completed during review]

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: [Pending]
**Status**: Pending
**Comments**: [To be completed upon approval]

---

**Task Created**: 2025-10-20 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-20
**Status**: Completed - Pending Review

---

*This task implements topological sorting for CTE dependency resolution, enabling correct WITH clause generation and preventing SQL forward reference errors in Phase 3 of PEP-004 implementation.*
