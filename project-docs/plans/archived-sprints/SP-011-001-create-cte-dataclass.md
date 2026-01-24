# Task SP-011-001: Create CTE Dataclass and Module Structure

**Task ID**: SP-011-001
**Sprint**: Sprint 011 (PEP-004 Implementation)
**Task Name**: Create CTE Dataclass and Module Structure
**Assignee**: Junior Developer
**Created**: 2025-10-19
**Last Updated**: 2025-10-19

---

## Task Overview

### Description

Create the foundational CTE infrastructure module with the `CTE` dataclass that represents a Common Table Expression. This dataclass is the fundamental data structure for the entire CTE infrastructure, containing all metadata needed for CTE generation, dependency tracking, and SQL assembly.

This task establishes the module structure (`fhir4ds/fhirpath/sql/cte.py`) and implements the core `CTE` dataclass with comprehensive documentation, type hints, and helper methods.

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

1. **CTE Dataclass**: Create `CTE` dataclass with all required fields (name, query, depends_on, requires_unnest, source_fragment, metadata)
2. **Module Structure**: Create `fhir4ds/fhirpath/sql/cte.py` module with proper imports and organization
3. **Type Hints**: All fields have proper type hints (Python 3.10+ style)
4. **Documentation**: Comprehensive docstrings explaining purpose, usage, and field meanings
5. **Validation**: Optional validation methods for CTE structure correctness

### Non-Functional Requirements

- **Performance**: Dataclass creation should be instantaneous (dataclasses are efficient)
- **Compliance**: Follows Python dataclass best practices, PEP 8 style guide
- **Database Support**: Database-agnostic data structure (no DuckDB/PostgreSQL specifics)
- **Error Handling**: Clear error messages if invalid CTE structures created

### Acceptance Criteria

- [ ] `fhir4ds/fhirpath/sql/cte.py` module created with proper structure
- [ ] `CTE` dataclass implemented with all required fields
- [ ] All fields have comprehensive docstrings and type hints
- [ ] Module-level docstring explains CTE infrastructure purpose
- [ ] Example usage in docstring demonstrates CTE creation
- [ ] No linting errors (passes ruff, mypy)
- [ ] Architecture review approved by senior architect

---

## Technical Specifications

### Affected Components

- **fhir4ds/fhirpath/sql/cte.py** (NEW): Main CTE infrastructure module

### File Modifications

- **fhir4ds/fhirpath/sql/cte.py**: Create new file with CTE dataclass and supporting code

### Database Considerations

- **DuckDB**: No database-specific code (dataclass is database-agnostic)
- **PostgreSQL**: No database-specific code (dataclass is database-agnostic)
- **Schema Changes**: None (this is a Python data structure, not a database schema)

---

## Dependencies

### Prerequisites

1. **PEP-004 Approval**: ✅ Complete (PEP-004 accepted 2025-10-19)
2. **Python 3.10+**: ✅ Available (development environment ready)
3. **dataclasses module**: ✅ Available (Python standard library)

### Blocking Tasks

- None (this is the first task in Sprint 011)

### Dependent Tasks

- **SP-011-002**: CTEBuilder requires CTE dataclass
- **SP-011-003**: CTEAssembler requires CTE dataclass
- **SP-011-004**: Unit tests require CTE dataclass

---

## Implementation Approach

### High-Level Strategy

Create a clean, well-documented `CTE` dataclass following Python best practices. The dataclass should be simple yet extensible, with all necessary fields for CTE generation and metadata tracking. Use Python 3.10+ features (type hints, dataclasses) for clean, maintainable code.

### Implementation Steps

1. **Create Module File** (30 minutes)
   - Create `fhir4ds/fhirpath/sql/cte.py`
   - Add module-level docstring explaining CTE infrastructure
   - Add necessary imports (dataclasses, typing, etc.)
   - **Validation**: File exists, imports correct

2. **Implement CTE Dataclass** (2 hours)
   - Define `@dataclass` decorator
   - Add all required fields with type hints:
     - `name: str` - Unique CTE name
     - `query: str` - SELECT statement for this CTE
     - `depends_on: List[str]` - CTE names this depends on
     - `requires_unnest: bool` - Flag for LATERAL UNNEST
     - `source_fragment: Optional[SQLFragment]` - Original fragment (for debugging)
     - `metadata: Dict[str, Any]` - Extensible metadata
   - Add field defaults using `field(default_factory=...)` for mutable defaults
   - Add comprehensive docstrings for class and each field
   - **Validation**: Dataclass instantiates correctly, all fields accessible

3. **Add Helper Methods** (1.5 hours)
   - `__repr__()` - Already provided by dataclass, verify output is useful
   - Optional: `validate()` method to check CTE structure correctness
   - Optional: `to_dict()` method for serialization (if needed for debugging)
   - **Validation**: Methods work correctly, useful for debugging

4. **Add Example Usage** (30 minutes)
   - Add example usage in module-level docstring
   - Show how to create CTE instances
   - Demonstrate field usage and metadata
   - **Validation**: Examples are clear and accurate

5. **Documentation and Review** (1.5 hours)
   - Ensure all docstrings are comprehensive
   - Verify type hints are correct and complete
   - Run linting (ruff, mypy) and fix any issues
   - Request senior architect code review
   - **Validation**: No linting errors, architecture review approved

**Estimated Time**: 8h total

### Alternative Approaches Considered

- **Named Tuple**: Rejected - dataclass is more Pythonic and provides better IDE support
- **Regular Class**: Rejected - dataclass is cleaner and provides automatic `__init__`, `__repr__`, etc.
- **Pydantic Model**: Rejected - overkill for internal data structure, dataclass is sufficient

---

## Testing Strategy

### Unit Testing

This task establishes the data structure that will be tested in SP-011-004. Basic validation:

- **Import Verification**: Module imports without errors
- **Instantiation**: CTE instances can be created with all field combinations
- **Type Checking**: mypy validates all type hints
- **Docstring Accuracy**: Examples in docstrings actually work

### Integration Testing

Not applicable for this task (dataclass only, no integration points yet).

### Compliance Testing

Not applicable for this task (no FHIRPath functionality yet).

### Manual Testing

- **Create CTE Instance**: Manually create CTE in Python REPL, verify all fields work
- **Default Values**: Verify default values (empty lists, False for requires_unnest) work correctly
- **Repr Output**: Verify `repr(cte)` output is readable and useful for debugging

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dataclass field types incorrect | Low | Low | Careful review of PEP-004 specification, senior review |
| Missing required fields | Low | Medium | Review PEP-004 spec thoroughly, validate against use cases |
| Mutable default values | Medium | Low | Use `field(default_factory=...)` for lists and dicts |

### Implementation Challenges

1. **Choosing Right Field Types**: Ensure types match PEP-004 specification exactly
   - **Approach**: Review PEP-004 specification, consult senior architect if unclear
2. **Comprehensive Documentation**: Docstrings must explain WHY fields exist, not just WHAT they are
   - **Approach**: Focus on use cases and purpose in docstrings

### Contingency Plans

- **If field types need modification**: Easy to change in dataclass, won't affect other tasks yet
- **If additional fields needed**: Can add fields later without breaking existing code (dataclass is extensible)

---

## Estimation

### Time Breakdown

- **Analysis and Design**: 0.5h (review PEP-004 spec, plan dataclass structure)
- **Implementation**: 4h (create module, implement dataclass, add helper methods)
- **Documentation**: 2h (comprehensive docstrings, examples, review)
- **Review and Refinement**: 1.5h (linting, senior review, address feedback)
- **Total Estimate**: 8h

### Confidence Level

- [x] High (90%+ confident in estimate)
- [ ] Medium (70-89% confident)
- [ ] Low (<70% confident - needs further analysis)

**Rationale**: Creating a dataclass is straightforward. Time estimate accounts for comprehensive documentation and review process.

### Factors Affecting Estimate

- Senior architect availability for review: Could add 0-2h if review delayed
- Unexpected field requirements from PEP-004 spec: Could add 1-2h if fields need redesign

---

## Success Metrics

### Quantitative Measures

- **Lines of Code**: ~100-150 lines (including comprehensive docstrings)
- **Docstring Coverage**: 100% (class + all fields documented)
- **Type Hint Coverage**: 100% (all fields have type hints)
- **Linting Score**: 0 errors, 0 warnings (ruff, mypy)

### Qualitative Measures

- **Code Quality**: Clean, Pythonic dataclass implementation
- **Architecture Alignment**: Matches PEP-004 specification exactly
- **Maintainability**: Easy to understand and extend in future

### Compliance Impact

- **Specification Compliance**: Foundational data structure for CTE infrastructure
- **Test Suite Results**: No tests yet (tested in SP-011-004)
- **Performance Impact**: None (dataclass creation is instantaneous)

---

## Documentation Requirements

### Code Documentation

- [x] Module-level docstring explaining CTE infrastructure purpose
- [x] CTE dataclass docstring with usage examples
- [x] Each field documented with purpose and usage
- [x] Example usage in module docstring

### Architecture Documentation

- [ ] No ADR needed (follows established dataclass patterns)
- [ ] No component interaction diagrams needed yet (just data structure)
- [ ] No database schema documentation (Python data structure only)

### User Documentation

Not applicable for internal data structure.

---

## Progress Tracking

### Progress Updates

| Date | Status | Work Completed | Blockers | Next Steps |
|------|--------|----------------|----------|------------|
| 2025-10-19 | In Review | Created CTE dataclass module with all required fields, comprehensive documentation, validation, helper methods. Passed flake8 and mypy linting. Manual testing verified all functionality. | None | Senior architect code review |
| 2025-10-19 | Completed | Senior review approved with excellent ratings. Merged to main branch. Feature branch deleted. Task documentation updated. | None | Proceed to SP-011-002 (CTEBuilder) |

### Status
- [ ] Not Started
- [ ] In Analysis
- [ ] In Development
- [ ] In Testing
- [ ] In Review
- [x] Completed
- [ ] Blocked

### Completion Checklist

- [x] Module file created (`fhir4ds/fhirpath/sql/cte.py`)
- [x] CTE dataclass implemented with all required fields
- [x] All fields have type hints and docstrings
- [x] Module-level docstring with examples
- [x] Linting passes (flake8, mypy)
- [x] Senior architect code review approved

---

## Review and Sign-off

### Self-Review Checklist

- [x] Implementation matches PEP-004 specification
- [x] All fields necessary and sufficient for CTE infrastructure
- [x] Code follows established patterns and standards
- [x] Docstrings are comprehensive and accurate
- [x] Type hints are correct and complete
- [x] Example usage in docstring works correctly

### Peer Review

**Reviewer**: Senior Solution Architect/Engineer
**Review Date**: 2025-10-19
**Review Status**: Approved
**Review Comments**: See project-docs/plans/reviews/SP-011-001-review.md for comprehensive review

### Final Approval

**Approver**: Senior Solution Architect/Engineer
**Approval Date**: 2025-10-19
**Status**: Approved - Merged to main
**Comments**: Exceptional implementation that exceeds expectations. Code quality is outstanding, documentation is comprehensive, and architecture compliance is perfect (100%). This establishes an excellent foundation for the remainder of Sprint 011.

---

**Task Created**: 2025-10-19 by Senior Solution Architect/Engineer
**Last Updated**: 2025-10-19
**Status**: Completed - Approved and Merged to Main (2025-10-19)

---

*This task establishes the foundational CTE dataclass for the entire CTE infrastructure, following Python best practices and PEP-004 specifications.*
