# Task: Create SQL Module Structure and Data Structures

**Task ID**: SP-005-001
**Sprint**: Sprint 005 - AST-to-SQL Translator
**Task Name**: Create SQL Module Structure and Core Data Structures
**Assignee**: Junior Developer
**Created**: 29-09-2025
**Last Updated**: 29-09-2025
**Status**: Completed
**Priority**: Critical
**Estimate**: 8 hours
**Actual Time**: 6 hours

---

## Task Overview

### Description
Create the foundational module structure for the AST-to-SQL translation layer and implement the core data structures (SQLFragment and TranslationContext) that will be used throughout the translator implementation. This task establishes the basic scaffolding for all subsequent translation work.

### Category
- [x] Architecture Enhancement
- [x] Feature Implementation
- [ ] Bug Fix
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
1. **Module Structure**: Create `fhir4ds/fhirpath/sql/` module with proper Python package structure
2. **SQLFragment DataClass**: Implement dataclass representing SQL fragment output from translation
3. **TranslationContext DataClass**: Implement dataclass managing state during AST traversal
4. **Module Exports**: Configure __init__.py to expose public API

### Non-Functional Requirements
- **Performance**: Data structures should be lightweight (<1KB memory overhead per instance)
- **Compliance**: Follow FHIR4DS coding standards (type hints, docstrings, dataclass patterns)
- **Database Support**: Data structures must work with both DuckDB and PostgreSQL
- **Error Handling**: Proper validation in data structure initialization

### Acceptance Criteria
- [x] fhir4ds/fhirpath/sql/ module created with __init__.py
- [x] SQLFragment dataclass implemented with all required fields
- [x] TranslationContext dataclass implemented with state management methods
- [x] Unit tests achieve 100% coverage for data structures
- [x] All type hints present and mypy validation passes
- [x] Documentation strings complete for all classes and methods
- [x] Code review approved by Senior Solution Architect ✅ APPROVED (30-09-2025)

---

## Technical Specifications

### Affected Components
- **New Module**: `fhir4ds/fhirpath/sql/` (create new)
- **Parser Integration**: Prepare for integration with `fhir4ds/fhirpath/parser.py` (PEP-002)
- **Dialect Layer**: Prepare for dialect method calls from translator

### File Modifications
- **fhir4ds/fhirpath/sql/__init__.py**: [NEW] - Module initialization and exports
- **fhir4ds/fhirpath/sql/fragments.py**: [NEW] - SQLFragment dataclass
- **fhir4ds/fhirpath/sql/context.py**: [NEW] - TranslationContext dataclass
- **tests/unit/fhirpath/sql/test_fragments.py**: [NEW] - SQLFragment tests
- **tests/unit/fhirpath/sql/test_context.py**: [NEW] - TranslationContext tests

### Database Considerations
- **DuckDB**: Data structures must accommodate DuckDB-specific SQL syntax patterns
- **PostgreSQL**: Data structures must accommodate PostgreSQL-specific SQL syntax patterns
- **Schema Changes**: None - this is application-level code only

---

## Dependencies

### Prerequisites
1. **PEP-003 Approved**: ✅ Complete - PEP-003 approved and ready for implementation
2. **PEP-002 Parser**: ✅ Complete - AST structures available for translation
3. **Development Environment**: Local Python 3.11+ environment with pytest

### Blocking Tasks
- None - this is the first task in the implementation sequence

### Dependent Tasks
- **SP-005-002**: Implement ASTToSQLTranslator base class (requires data structures)
- **SP-005-003**: Add unit tests for data structures (requires structures implemented)
- **All subsequent tasks**: All translation tasks depend on these data structures

---

## Implementation Approach

### High-Level Strategy
Create clean, simple dataclasses following Python best practices and FHIR4DS conventions. Focus on clarity and extensibility - these structures will be used throughout the translator and referenced by future PEP-004 (CTE Builder).

### Implementation Steps

1. **Create Module Structure** (1 hour)
   - Create `fhir4ds/fhirpath/sql/` directory
   - Create `__init__.py` with module docstring
   - Set up proper Python package structure
   - Validation: Directory exists, Python can import module

2. **Implement SQLFragment DataClass** (2 hours)
   - Create `fragments.py` file
   - Implement SQLFragment dataclass with fields:
     - `expression: str` - The SQL expression
     - `source_table: str` - Source table/CTE reference
     - `requires_unnest: bool = False` - Array operation flag
     - `is_aggregate: bool = False` - Aggregation flag
     - `dependencies: List[str]` - CTE dependencies
     - `metadata: Dict[str, Any]` - Extensible metadata
   - Add comprehensive docstrings
   - Add type hints for all fields
   - Validation: Dataclass instantiates correctly, all fields accessible

3. **Implement TranslationContext DataClass** (2 hours)
   - Create `context.py` file
   - Implement TranslationContext dataclass with fields:
     - `current_table: str = "resource"` - Current source
     - `current_resource_type: str = "Patient"` - FHIR resource type
     - `parent_path: List[str]` - Path components
     - `variable_bindings: Dict[str, str]` - Variable mappings
     - `cte_counter: int = 0` - CTE naming counter
   - Add helper methods:
     - `next_cte_name() -> str` - Generate unique CTE name
     - `push_path(component: str) -> None` - Add path component
     - `pop_path() -> str` - Remove path component
   - Add comprehensive docstrings and type hints
   - Validation: Context state management methods work correctly

4. **Configure Module Exports** (1 hour)
   - Update `__init__.py` to export public classes
   - Add module-level documentation
   - Configure proper imports
   - Validation: `from fhir4ds.fhirpath.sql import SQLFragment, TranslationContext` works

5. **Create Unit Tests** (2 hours)
   - Create test files for both data structures
   - Test SQLFragment instantiation and field access
   - Test TranslationContext state management methods
   - Test edge cases (empty lists, None values, etc.)
   - Achieve 100% test coverage
   - Validation: All tests pass, coverage report shows 100%

### Alternative Approaches Considered
- **Single Monolithic File**: Rejected - separate files cleaner for maintainability
- **Classes Instead of Dataclasses**: Rejected - dataclasses simpler, less boilerplate
- **Mutable vs Immutable**: Chose mutable for context (needs state updates), immutable-style for fragments

---

## Testing Strategy

### Unit Testing
- **New Tests Required**:
  - `test_sqlfragment_instantiation`: Test all fields initialize correctly
  - `test_sqlfragment_defaults`: Test default field values
  - `test_sqlfragment_metadata`: Test metadata dictionary functionality
  - `test_translationcontext_instantiation`: Test context initialization
  - `test_translationcontext_path_management`: Test push_path/pop_path
  - `test_translationcontext_cte_naming`: Test next_cte_name uniqueness
  - `test_translationcontext_variable_bindings`: Test variable storage/retrieval
- **Coverage Target**: 100% for both data structures

### Integration Testing
- **Database Testing**: Not applicable - data structures only
- **Component Integration**: Will be tested in SP-005-002 (translator implementation)

### Compliance Testing
- **Official Test Suites**: Not applicable for data structures
- **Regression Testing**: Unit tests prevent structural regressions

### Manual Testing
- **Test Scenarios**:
  - Create SQLFragment instances with various field combinations
  - Test TranslationContext state transitions
  - Verify type hints work correctly with mypy
- **Edge Cases**:
  - Empty lists and dictionaries
  - Very deep path nesting (100+ components)
  - Large metadata dictionaries
- **Error Conditions**:
  - Invalid field types
  - None values where not allowed

---

## Risk Assessment

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data structure design inadequate for future needs | Low | Medium | Follow PEP-003 spec closely, ensure extensibility via metadata dict |
| Performance overhead from dataclasses | Very Low | Low | Dataclasses are optimized, minimal overhead expected |
| Type hint complexity | Low | Low | Use simple, standard types (str, List, Dict) |

### Implementation Challenges
1. **Extensibility**: Ensure data structures can accommodate future needs without breaking changes
   - Approach: Use metadata dict for extensible fields, follow semantic versioning
2. **Documentation Clarity**: Make sure data structures are well-documented for future developers
   - Approach: Comprehensive docstrings, include usage examples

---

## Completion Criteria

### Code Quality
- [ ] All code follows PEP 8 style guide
- [ ] Type hints present and mypy validation passes
- [ ] Docstrings complete (Google style)
- [ ] No linting errors (flake8, black formatted)

### Testing
- [ ] Unit tests written and passing
- [ ] Test coverage 100% for data structures
- [ ] Edge cases covered

### Documentation
- [ ] Module docstrings complete
- [ ] Class/method docstrings complete
- [ ] Usage examples in docstrings

### Review
- [ ] Code review requested from Senior Solution Architect
- [ ] Review feedback addressed
- [ ] Final approval obtained

---

## Notes and Comments

### Design Decisions
1. **SQLFragment Mutability**: Fragments are mutable dataclasses to allow post-creation updates if needed (e.g., dependency addition)
2. **TranslationContext Mutability**: Context explicitly mutable as it tracks state during traversal
3. **Metadata Dictionary**: Provides extensibility without breaking changes to dataclass structure

### Future Considerations
- **PEP-004 Integration**: SQLFragment structure designed to be easily consumed by future CTE Builder
- **Additional Fields**: Metadata dict allows future additions without structural changes
- **Performance Monitoring**: Consider adding timing/profiling fields to metadata if needed

---

**Task Created**: 29-09-2025
**Estimated Completion**: 30-09-2025 (Day 1 of Sprint 005)
**Actual Completion**: 29-09-2025
**Milestone**: M004-AST-SQL-TRANSLATOR
**Phase**: Phase 1 - Core Infrastructure

---

## Progress Updates

| Date | Status | Progress | Blockers | Next Steps |
|------|--------|----------|----------|------------|
| 29-09-2025 | Completed | All data structures implemented with 100% test coverage (81 tests passing) | None | Ready for Senior Architect code review |

### Implementation Summary

**Completed Work**:
- Created `fhir4ds/fhirpath/sql/` module with proper package structure
- Implemented `SQLFragment` dataclass with validation, dependency management, and metadata support
- Implemented `TranslationContext` dataclass with path management, CTE naming, and variable bindings
- Created comprehensive unit tests (32 tests for SQLFragment, 49 tests for TranslationContext)
- Achieved 100% code coverage across all module files
- All tests passing (81/81)
- Module imports verified and working correctly

**Key Deliverables**:
1. `fhir4ds/fhirpath/sql/__init__.py` - Module initialization and exports
2. `fhir4ds/fhirpath/sql/fragments.py` - SQLFragment dataclass (26 statements, 100% coverage)
3. `fhir4ds/fhirpath/sql/context.py` - TranslationContext dataclass (31 statements, 100% coverage)
4. `tests/unit/fhirpath/sql/test_fragments.py` - Comprehensive SQLFragment tests
5. `tests/unit/fhirpath/sql/test_context.py` - Comprehensive TranslationContext tests

**Test Coverage**:
- Total: 61 statements, 0 missed, 100% coverage
- 81 tests passing in 0.97 seconds
- Edge cases covered: Unicode, deep nesting, special characters, boundary conditions

**Code Quality**:
- All type hints present
- Google-style docstrings for all classes and methods
- Comprehensive inline documentation
- Validation in `__post_init__` methods
- Clean, maintainable code following FHIR4DS standards

**Git Commit**: `ce96e3a` - feat(sql): create SQL module structure and core data structures

**Final Status**: ✅ FULLY COMPLETE - All acceptance criteria met (7/7)
**Review Document**: [SP-005-001-review.md](/project-docs/plans/archived-sprints/SP-005-001-review.md)
**Senior Architect Approval**: ✅ APPROVED FOR MERGE (30-09-2025)