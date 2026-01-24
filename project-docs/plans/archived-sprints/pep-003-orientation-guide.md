# PEP-003 Implementation Orientation Guide

**PEP**: PEP-003 - FHIRPath AST-to-SQL Translator
**Implementation Duration**: 30-09-2025 to 18-12-2025 (7 weeks)
**Your Role**: Junior Developer
**Lead**: Senior Solution Architect/Engineer
**Sprint**: Sprint 005
**Milestone**: M004-AST-SQL-TRANSLATOR

---

## Welcome to AST-to-SQL Translator Implementation

You are implementing the **critical translation layer** that converts FHIRPath Abstract Syntax Trees into database-executable SQL fragments. This is the **keystone component** of FHIR4DS's unified FHIRPath architecture, filling the gap between the parser (PEP-002, completed) and SQL execution.

**Why This Matters**: Without this translator, FHIR4DS cannot execute FHIRPath expressions, cannot achieve population-scale performance (10x+ improvements), and cannot implement SQL-on-FHIR or CQL specifications. You're building the foundation that enables everything else.

You are implementing **PEP-003: FHIRPath AST-to-SQL Translator** across 7 weeks with 25 tasks organized into 6 phases.

---

## 1. Initial Review and Context

### Required Reading (in order - CRITICAL)
1. **CLAUDE.md** - Development workflow and principles (READ FIRST - 30 minutes)
2. **project-docs/peps/accepted/pep-003-ast-to-sql-translator.md** - The PEP you're implementing (CRITICAL - 2 hours)
3. **project-docs/plans/current-sprint/sprint-005-ast-to-sql-translator.md** - Current sprint plan (1 hour)
4. **project-docs/plans/milestones/milestone-m004-ast-to-sql-translator.md** - Overall milestone context (1 hour)
5. **project-docs/architecture/README.md** - Unified FHIRPath architecture (1 hour)
6. **project-docs/peps/implemented/pep-002-fhirpath-core-implementation.md** - Parser that creates your input (1 hour)

**Total Initial Reading**: ~6-7 hours - DO NOT SKIP THIS

### Key Concepts to Understand

#### 1. **Visitor Pattern**
The translator uses the visitor pattern to traverse AST nodes. Each node type (LiteralNode, IdentifierNode, OperatorNode, etc.) has a corresponding `visit_*()` method that generates SQL for that node type.

**Resources**:
- [Visitor Pattern Explanation](https://refactoring.guru/design-patterns/visitor)
- See `fhir4ds/fhirpath/evaluator/engine.py` for visitor pattern example (in-memory evaluator)
- PEP-003 Appendix A has complete translation examples

#### 2. **SQL Fragments**
The translator outputs `SQLFragment` objects, not complete SQL queries. Each fragment represents one logical operation. Future PEP-004 (CTE Builder) will wrap these fragments in CTEs and assemble them into final SQL.

**Key Point**: You're translating logic, not building complete queries yet.

#### 3. **Translation Context**
`TranslationContext` maintains state during AST traversal (current table, path components, variables, CTE counter). Understanding context management is critical for correct SQL generation.

#### 4. **Thin Dialect Architecture**
The translator calls dialect methods (e.g., `dialect.extract_json_field()`) for database-specific SQL syntax. You never write database-specific SQL directly - always call dialect methods. This maintains the "thin dialect" principle: **business logic in translator, only syntax differences in dialects**.

#### 5. **Population-First Design**
All translation must preserve population-scale capability. For example:
- Use `json_extract(resource, '$.name[0]')` for `first()` (array indexing)
- **NOT** `SELECT * FROM ... LIMIT 1` (per-patient anti-pattern)

This is a core architectural principle - violating it blocks population analytics.

---

## 2. Your AST-to-SQL Translator Implementation Tasks

### Phase 1: Core Infrastructure (Week 1)
1. **SP-005-001**: Create SQL module structure and data structures (8h) **[CRITICAL START]**
2. **SP-005-002**: Implement ASTToSQLTranslator base class (12h) **[CRITICAL]**
3. **SP-005-003**: Add unit tests for data structures (8h)

### Phase 2: Basic Node Translation (Week 2)
4. **SP-005-004**: Implement literal node translation (10h)
5. **SP-005-005**: Implement identifier/path navigation (12h)
6. **SP-005-006**: Implement operator translation (12h)
7. **SP-005-007**: Add dialect method extensions (8h)

### Phase 3: Complex Operations (Weeks 3-4)
8. **SP-005-008**: Implement where() function translation (16h) **[COMPLEX]**
9. **SP-005-009**: Implement select() and first() functions (12h)
10. **SP-005-010**: Implement exists() function (8h)
11. **SP-005-011**: Implement aggregation functions (12h)
12. **SP-005-012**: Add array operation dialect methods (10h)

### Phase 4: Multi-Step Expressions (Week 5)
13. **SP-005-013**: Implement expression chain traversal (14h) **[CRITICAL]**
14. **SP-005-014**: Handle context updates between operations (10h)
15. **SP-005-015**: Implement dependency tracking (8h)
16. **SP-005-016**: Test complex multi-operation expressions (12h)

### Phase 5: Dialect Implementations (Week 6)
17. **SP-005-017**: Complete DuckDB dialect methods (12h)
18. **SP-005-018**: Complete PostgreSQL dialect methods (12h)
19. **SP-005-019**: Validate SQL syntax correctness (8h)
20. **SP-005-020**: Test multi-database consistency (10h) **[CRITICAL]**

### Phase 6: Integration and Documentation (Week 7)
21. **SP-005-021**: Integration with FHIRPath parser (10h) **[CRITICAL]**
22. **SP-005-022**: Integration testing with real expressions (12h)
23. **SP-005-023**: API documentation and examples (10h)
24. **SP-005-024**: Architecture documentation (8h)
25. **SP-005-025**: Performance benchmarking (8h)

**Total**: 252 hours across 7 weeks (~36 hours/week - realistic for focused work)

### Task Locations
All detailed task specifications are in: `project-docs/plans/tasks/SP-005-[XXX]-[task-name].md`

**Example**: `project-docs/plans/tasks/SP-005-001-create-sql-module-structure.md`

---

## 3. Development Workflow

### Branch Management
- Create a new branch for each task: `sp-005-[xxx]-[brief-name]`
- Example: `sp-005-001-sql-module-structure`
- Example: `sp-005-008-where-function-translation`
- Commit frequently with descriptive messages: `feat(sql): implement SQLFragment dataclass`
- Follow conventional commits: `type(scope): description`

### Daily Workflow (IMPORTANT)
**Every working day, you MUST:**

1. **Morning**: Review current task document, understand acceptance criteria
2. **Throughout Day**: Write code, tests, documentation
3. **End of Day**: Update task status, document progress/blockers
4. **Before Committing**: Run tests, ensure all pass in both DuckDB and PostgreSQL

### Progress Tracking Requirements
**For EVERY task, update these documents as you work:**

#### A. Task Document Updates
Location: `project-docs/plans/tasks/SP-005-[XXX]-[task-name].md`

Add daily progress entry to "Progress Updates" section:
```markdown
## Progress Updates

| Date | Status | Progress | Blockers | Next Steps |
|------|--------|----------|----------|------------|
| 30-09-2025 | In Progress | Implemented SQLFragment dataclass | None | Add unit tests |
| 01-10-2025 | In Testing | All tests written, 2 failing | Type hint issue | Fix type hints, get to 100% passing |
| 02-10-2025 | Completed | All tests pass, code reviewed | None | Move to SP-005-002 |
```

Update status:
- `**Status**: Not Started` → `**Status**: In Analysis` → `**Status**: In Development` → `**Status**: In Testing` → `**Status**: In Review` → `**Status**: Completed`

Mark acceptance criteria as you complete them:
- `- [ ] Criterion not met` → `- [x] Criterion met`

#### B. Sprint Plan Updates
Location: `project-docs/plans/current-sprint/sprint-005-ast-to-sql-translator.md`

Update task status in appropriate phase table:
```markdown
| SP-005-001 | Create SQL module structure | Junior Developer | 8h | None | ✅ COMPLETE |
```

#### C. Weekly Summary
At end of each week, add summary to sprint plan:
```markdown
## Week 1 Summary (30-09-2025 to 06-10-2025)
- **Completed**: SP-005-001, SP-005-002, SP-005-003
- **In Progress**: SP-005-004
- **Blockers**: None
- **Key Achievements**: Core infrastructure complete, base translator class working
- **Next Week Focus**: Basic node translation (literals, identifiers, operators)
```

---

## 4. Implementation Guidelines

### Code Quality Standards (FROM CLAUDE.md - MUST FOLLOW)

#### General Principles
- **Simplicity is Paramount**: Make the simplest possible change
- **Document As You Go**: Clear code comments, docstrings, progress tracking
- **Keep Workspace Tidy**: No dead code, no unused imports, no temp files
- **Never Change Tests Without Approval**: If test seems wrong, ask Senior Architect first
- **Address Root Causes**: Fix root cause, never band-aid solutions
- **Understand Context First**: Review all relevant code before starting

#### FHI R4DS-Specific Standards
- **No Hardcoded Values**: Use configuration, never hardcode paths, URLs, constants
- **Multi-Database Support**: Every feature must work on both DuckDB and PostgreSQL
- **Population-First Design**: Default to population queries, avoid LIMIT 1 patterns
- **Thin Dialect Architecture**: Business logic in translator, only syntax in dialects
- **Error Handling**: Comprehensive error handling with clear messages
- **Type Hints**: All functions/methods must have complete type hints
- **Docstrings**: Google-style docstrings for all classes/methods

### Testing Requirements (CRITICAL - DO NOT SKIP)

#### Unit Tests (90%+ Coverage Required)
```python
# Example unit test structure
def test_sqlfragment_instantiation():
    """Test SQLFragment creates correctly with all fields."""
    fragment = SQLFragment(
        expression="SELECT * FROM resource",
        source_table="resource",
        requires_unnest=False,
        is_aggregate=False
    )
    assert fragment.expression == "SELECT * FROM resource"
    assert fragment.source_table == "resource"
    assert not fragment.requires_unnest
```

**Run tests after every change**:
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/fhirpath/sql/test_translator.py

# Run with coverage
pytest --cov=fhir4ds.fhirpath.sql tests/
```

#### Integration Tests (Multi-Database)
**CRITICAL**: Every feature must be tested on BOTH DuckDB and PostgreSQL.

```bash
# Test DuckDB
pytest tests/integration/ --database=duckdb

# Test PostgreSQL (ensure PostgreSQL running)
pytest tests/integration/ --database=postgresql

# Test both
pytest tests/integration/
```

PostgreSQL connection: `postgresql://postgres:postgres@localhost:5432/postgres`

#### Compliance Tests
Validate translation against FHIRPath official test suite:
```bash
pytest tests/compliance/fhirpath/
```

### Documentation Standards

#### Code Comments
```python
def _translate_where(self, node: FunctionCallNode) -> SQLFragment:
    """
    Translate where() function to SQL with LATERAL UNNEST.

    This generates complete SQL including array unnesting, NOT just a flag.
    Design decision: Translator has all context needed, keeping fragments
    self-contained simplifies future CTE Builder (PEP-004).

    Args:
        node: FunctionCallNode representing where() function call

    Returns:
        SQLFragment with complete LATERAL UNNEST SQL

    Example:
        Input: Patient.name.where(use='official')
        Output: SELECT resource.id, cte_1_item
                FROM resource, LATERAL UNNEST(json_extract(resource, '$.name')) AS cte_1_item
                WHERE json_extract(cte_1_item, '$.use') = 'official'
    """
    # Get array path from current context
    array_path = "$." + ".".join(self.context.parent_path)

    # Translate filter condition
    condition_fragment = self.visit(node.arguments[0])

    # ... rest of implementation
```

#### Docstring Template
```python
class ASTToSQLTranslator(ASTVisitor[SQLFragment]):
    """
    Translates FHIRPath AST to SQL fragments using visitor pattern.

    Core component that converts each AST node type to database-specific SQL
    by calling dialect methods. Outputs sequence of SQL fragments representing
    logical operations, which future PEP-004 (CTE Builder) will wrap in CTEs.

    Attributes:
        dialect: DatabaseDialect instance for SQL generation
        context: TranslationContext tracking traversal state
        fragments: List of generated SQL fragments

    Example:
        >>> translator = ASTToSQLTranslator(duckdb_dialect, "Patient")
        >>> fragments = translator.translate(ast_root)
        >>> for fragment in fragments:
        ...     print(fragment.expression)
    """
```

---

## 5. Common Patterns and Examples

### Pattern 1: Basic Visitor Method
```python
def visit_literal(self, node: LiteralNode) -> SQLFragment:
    """Translate literal values to SQL."""
    # Handle different literal types
    if node.literal_type == "string":
        sql_expr = f"'{node.value.replace(\"'\", \"''\")}'"  # Escape quotes
    elif node.literal_type == "integer":
        sql_expr = str(node.value)
    elif node.literal_type == "boolean":
        sql_expr = "TRUE" if node.value else "FALSE"

    return SQLFragment(
        expression=sql_expr,
        source_table=self.context.current_table
    )
```

### Pattern 2: Calling Dialect Methods
```python
def visit_identifier(self, node: IdentifierNode) -> SQLFragment:
    """Translate path navigation to JSON extraction."""
    # Build JSON path
    json_path = "$." + ".".join(self.context.parent_path + [node.identifier])

    # Call dialect method (NOT hardcoded SQL!)
    sql_expr = self.dialect.extract_json_field(
        column=self.context.current_table,
        path=json_path
    )

    return SQLFragment(expression=sql_expr, source_table=self.context.current_table)
```

### Pattern 3: Context Management
```python
def _translate_where(self, node: FunctionCallNode) -> SQLFragment:
    """Translate where() with context updates."""
    # Save current state
    old_table = self.context.current_table

    # Generate SQL...
    cte_name = self.context.next_cte_name()  # Generate unique name
    # ... build SQL ...

    # Update context for next operation
    self.context.current_table = cte_name

    return SQLFragment(expression=sql, source_table=cte_name)
```

### Pattern 4: Multi-Database Testing
```python
@pytest.mark.parametrize("dialect", [
    DuckDBDialect(),
    PostgreSQLDialect()
])
def test_where_translation(dialect):
    """Test where() works on both dialects."""
    translator = ASTToSQLTranslator(dialect)
    fragment = translator._translate_where(where_node)

    # Both should generate UNNEST/array logic (syntax differs)
    assert fragment.requires_unnest
    assert "WHERE" in fragment.expression
```

---

## 6. Critical Success Factors

### DO
✅ Read PEP-003 completely before starting (2 hours well spent)
✅ Follow task sequence strictly (dependencies matter!)
✅ Update documentation daily (don't let it pile up)
✅ Test on BOTH databases for every feature
✅ Call dialect methods, never write database-specific SQL directly
✅ Ask Senior Architect when uncertain (better to ask than implement wrong)
✅ Commit frequently with clear messages
✅ Run full test suite before code review requests

### DON'T
❌ Skip reading PEP-003 or CLAUDE.md
❌ Change task sequence (you'll hit dependency issues)
❌ Let documentation fall behind (update daily!)
❌ Test only on DuckDB (PostgreSQL differences will break things)
❌ Write `if dialect == "duckdb"` in translator (use dialect methods!)
❌ Use `LIMIT 1` patterns (violates population-first principle)
❌ Modify tests without Senior Architect approval
❌ Leave dead code, temp files, or hardcoded values

---

## 7. Getting Help

### When to Ask for Help
- **Immediately**: If blocked for >2 hours
- **Before implementing**: If unsure about approach
- **Before changing tests**: Always get approval first
- **When finding bugs**: In parser (PEP-002) or dialects

### How to Ask for Help
1. **Document the issue**: What you're trying to do, what's not working
2. **Show your work**: What you've tried, error messages, code snippets
3. **Propose solution**: What you think might work (even if unsure)
4. **Update task document**: Add blocker to progress table

### Communication Channels
- **Daily**: Update task documents with progress/blockers
- **Weekly**: Friday 2PM review with Senior Architect
- **As Needed**: Request code review, technical discussion, clarification

---

## 8. Phase Completion Checklist

### Before Moving to Next Phase
- [ ] All tasks in current phase completed
- [ ] All unit tests passing (90%+ coverage)
- [ ] All integration tests passing (both databases)
- [ ] Code review approved by Senior Architect
- [ ] Documentation updated (code comments, docstrings, progress tracking)
- [ ] No dead code, temp files, or TODOs left behind
- [ ] Sprint plan updated with phase completion
- [ ] Clean git history (meaningful commit messages)

---

## 9. Milestone Completion Criteria

### Final Deliverables (Week 7)
When you complete all 25 tasks, the milestone is complete when:
- [ ] 90%+ unit test coverage for translator module
- [ ] 80%+ FHIRPath operation translation coverage
- [ ] <10ms translation performance validated
- [ ] 100% multi-database logic consistency
- [ ] All tests pass (unit, integration, compliance)
- [ ] Complete documentation (API docs, examples, integration guide)
- [ ] Senior Architect sign-off
- [ ] Implementation summary created
- [ ] PEP-003 moved to `implemented/` directory

---

## 10. Resources and References

### Key Documents
- **PEP-003**: `project-docs/peps/accepted/pep-003-ast-to-sql-translator.md`
- **Sprint Plan**: `project-docs/plans/current-sprint/sprint-005-ast-to-sql-translator.md`
- **Milestone**: `project-docs/plans/milestones/milestone-m004-ast-to-sql-translator.md`
- **CLAUDE.md**: Development workflow (root directory)
- **Architecture**: `project-docs/architecture/README.md`

### Code References
- **Parser (PEP-002)**: `fhir4ds/fhirpath/parser.py` - Creates AST input
- **Evaluator Example**: `fhir4ds/fhirpath/evaluator/engine.py` - Visitor pattern example
- **Dialect Base**: `fhir4ds/dialects/base.py` - Dialect interface
- **DuckDB Dialect**: `fhir4ds/dialects/duckdb.py` - DuckDB implementation
- **PostgreSQL Dialect**: `fhir4ds/dialects/postgresql.py` - PostgreSQL implementation

### External Resources
- **Visitor Pattern**: https://refactoring.guru/design-patterns/visitor
- **FHIRPath Specification**: https://hl7.org/fhirpath/
- **Python Type Hints**: https://docs.python.org/3/library/typing.html
- **pytest Documentation**: https://docs.pytest.org/

---

## 11. Quick Start Checklist

### Day 1 - Setup and Reading
- [ ] Read CLAUDE.md (30 minutes)
- [ ] Read PEP-003 completely (2 hours)
- [ ] Read Sprint 005 plan (1 hour)
- [ ] Read Milestone M004 (1 hour)
- [ ] Review architecture documentation (1 hour)
- [ ] Set up development environment (test both databases)
- [ ] Create branch for SP-005-001

### Day 2 - First Task
- [ ] Read SP-005-001 task document completely
- [ ] Understand acceptance criteria
- [ ] Create module structure
- [ ] Implement SQLFragment dataclass
- [ ] Update task document with progress
- [ ] Commit: `feat(sql): create module structure and SQLFragment`

### Week 1 Goal
- [ ] Complete Phase 1 (SP-005-001, SP-005-002, SP-005-003)
- [ ] Core infrastructure working
- [ ] 100% test coverage for data structures
- [ ] Code review approved
- [ ] Sprint plan updated

---

**Good luck! You're building a critical component of FHIR4DS. Take your time, follow the process, ask questions, and focus on quality over speed. The Senior Architect is here to help.**

**Remember**: This translator is the foundation for SQL-on-FHIR, CQL, and population-scale analytics. Your work directly enables FHIR4DS to achieve its goal of 100% healthcare interoperability specification compliance.

---

**Orientation Guide Created**: 29-09-2025
**Last Updated**: 29-09-2025
**Owner**: Senior Solution Architect/Engineer
**For**: Junior Developer implementing PEP-003