# Task: Implement ASTToSQLTranslator Base Class

**Task ID**: SP-005-002
**Sprint**: Sprint 005 - AST-to-SQL Translator
**Task Name**: Implement ASTToSQLTranslator Base Class with Visitor Pattern
**Assignee**: Junior Developer
**Created**: 29-09-2025
**Last Updated**: 30-09-2025
**Status**: Completed
**Priority**: Critical
**Estimate**: 12 hours
**Actual Time**: 10 hours

---

## Task Overview

### Description
Implement the core ASTToSQLTranslator class that uses the visitor pattern to traverse FHIRPath AST nodes and generate SQL fragments. This class serves as the foundation for all translation work, establishing the visitor pattern, dialect integration, and translation orchestration.

### Category
- [x] Feature Implementation
- [x] Architecture Enhancement

### Priority
- [x] Critical (Blocker for sprint goals)

---

## Requirements

### Functional Requirements
1. **ASTToSQLTranslator Class**: Implement base translator class extending ASTVisitor[SQLFragment]
2. **Visitor Method Stubs**: Create stub methods for all node types (literal, identifier, function, operator, etc.)
3. **Dialect Integration**: Initialize with DatabaseDialect instance, call dialect methods for SQL generation
4. **Translation Orchestration**: Implement translate() method that coordinates translation and accumulates fragments
5. **Context Management**: Initialize and maintain TranslationContext throughout translation

### Acceptance Criteria
- [x] ASTToSQLTranslator class implemented extending ASTVisitor[SQLFragment]
- [x] All visitor method stubs created (visit_literal, visit_identifier, visit_function_call, visit_operator, visit_conditional, visit_aggregation, visit_type_operation)
- [x] Dialect integration working (accepts dialect in __init__, stores for use)
- [x] translate() method implemented and working
- [x] TranslationContext initialized and accessible
- [x] Unit tests for base class structure (37 tests, 100% pass rate)
- [x] Type hints complete, comprehensive docstrings
- [x] Ready for code review

---

## Implementation Approach

### High-Level Strategy
Create the skeletal translator class with all required structure but minimal implementation. Visitor methods will be stubs that raise NotImplementedError initially - they'll be implemented in subsequent tasks. Focus is on establishing the visitor pattern, dialect integration, and overall structure.

### Implementation Steps

1. **Create Translator Module** (2 hours)
   - Create `fhir4ds/fhirpath/sql/translator.py`
   - Import required types (ASTVisitor, SQLFragment, TranslationContext, dialect types)
   - Add module docstring

2. **Implement ASTToSQLTranslator Class** (4 hours)
   - Extend ASTVisitor[SQLFragment]
   - __init__ method: Accept dialect and resource_type parameters
   - Initialize TranslationContext
   - Store dialect reference
   - Initialize fragments list
   - Add class docstring with examples

3. **Implement translate() Method** (2 hours)
   - Main entry point: `translate(ast_root: FHIRPathASTNode) -> List[SQLFragment]`
   - Clear fragments list
   - Call _translate_node() for root
   - Return accumulated fragments list
   - Handle errors appropriately

4. **Create Visitor Method Stubs** (3 hours)
   - visit_literal(node: LiteralNode) -> SQLFragment: raise NotImplementedError
   - visit_identifier(node: IdentifierNode) -> SQLFragment: raise NotImplementedError
   - visit_function_call(node: FunctionCallNode) -> SQLFragment: raise NotImplementedError
   - visit_operator(node: OperatorNode) -> SQLFragment: raise NotImplementedError
   - visit_conditional(node: ConditionalNode) -> SQLFragment: raise NotImplementedError
   - visit_aggregation(node: AggregationNode) -> SQLFragment: raise NotImplementedError
   - visit_type_operation(node: TypeOperationNode) -> SQLFragment: raise NotImplementedError
   - Each with proper docstring and type hints

5. **Write Unit Tests** (1 hour)
   - Test class instantiation
   - Test dialect storage
   - Test context initialization
   - Test visitor methods raise NotImplementedError
   - Test translate() method structure

---

## Dependencies

### Prerequisites
- **SP-005-001**: SQL module structure and data structures (MUST be complete)

### Dependent Tasks
- **All Phase 2-6 tasks**: All subsequent work depends on this base class

---

## Completion Criteria

### Code Quality
- [ ] Type hints complete, mypy passes
- [ ] Docstrings for class and all methods
- [ ] Clean code structure

### Testing
- [ ] Unit tests passing
- [ ] 80%+ test coverage

### Review
- [ ] Code review approved

---

**Task Created**: 29-09-2025
**Phase**: Phase 1 - Core Infrastructure
**Blocking**: All Phase 2-6 tasks

---

## Progress Updates

| Date | Status | Progress | Blockers | Next Steps |
|------|--------|----------|----------|------------|
| 30-09-2025 | Completed | All implementation complete, 37 tests passing (118 total in SQL module) | None | ✅ Senior review approved, merged to main |

### Implementation Summary

**Completed Work**:
- Created `fhir4ds/fhirpath/sql/translator.py` with complete ASTToSQLTranslator class
- Implemented visitor pattern extending ASTVisitor[SQLFragment]
- All 7 visitor method stubs created with descriptive NotImplementedError messages
- translate() method fully implemented with fragment accumulation and context management
- Dialect integration working (stores DatabaseDialect, accessible for SQL generation)
- TranslationContext properly initialized and managed
- Module exports updated in `__init__.py`
- Comprehensive test suite created (37 tests, 100% pass rate)
- All tests passing: 118 tests total in SQL module

**Key Deliverables**:
1. `fhir4ds/fhirpath/sql/translator.py` - Complete translator base class (32 statements)
2. `tests/unit/fhirpath/sql/test_translator.py` - Comprehensive test suite (37 tests)
3. Updated `fhir4ds/fhirpath/sql/__init__.py` - Module exports

**Test Coverage**:
- 37 new tests for translator base class
- 118 total tests passing in SQL module
- All acceptance criteria met
- Tests cover: instantiation, dialect storage, context management, translate() method, visitor stubs, error handling, docstrings

**Code Quality**:
- Complete type hints throughout
- Google-style docstrings for all methods
- Clear NotImplementedError messages referencing future task IDs
- Follows visitor pattern correctly
- Integrates properly with existing AST and dialect infrastructure

**Architecture Alignment**:
- Extends ASTVisitor[SQLFragment] correctly
- Thin dialect pattern maintained (only syntax in dialects)
- Population-first principles ready for implementation
- Context management supports CTE generation
- Clear separation between translator and dialect responsibilities

**Git Branch**: feature/SP-005-002-translator-base-class (merged and deleted)
**Merged to main**: ef46c75
**Review**: [SP-005-002-review.md](../reviews/SP-005-002-review.md)

**Final Status**: ✅ APPROVED AND MERGED - All acceptance criteria met (7/7)
**Completion Date**: 30-09-2025
**Review Status**: ✅ Approved by Senior Solution Architect/Engineer