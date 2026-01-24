# Task: Design Unified SQLGenerator Class

**Task ID**: SP-023-001
**Sprint**: 023
**Task Name**: Design the Unified SQLGenerator Architecture
**Assignee**: Junior Developer
**Created**: 2025-12-13
**Last Updated**: 2025-12-13

---

## Task Overview

### Description
Design and document the architecture for a new unified `SQLGenerator` class that will replace the current 4-component pipeline (AST Adapter → Translator → CTE Builder → CTE Assembler) with a single component.

This is a **design task** - no code changes yet. The output is a design document that will guide the implementation tasks.

### Why This Matters
The current architecture has 4 components with metadata being passed between them. This causes bugs where:
- Metadata gets lost at component boundaries
- Each component doesn't have full context
- Fixing one component breaks another

By consolidating into 1 component, we eliminate these interface bugs.

### Category
- [x] Architecture Design
- [x] Documentation

### Priority
- [x] Critical (Blocker for sprint goals)

---

## Requirements

### Deliverable
A design document (`project-docs/architecture/unified-sql-generator-design.md`) that includes:

1. **Class interface** - Public methods, parameters, return types
2. **Internal structure** - How the class is organized internally
3. **Data flow** - How an expression goes from input to SQL output
4. **Key design decisions** - With rationale for each

### Acceptance Criteria
- [x] Design document created and reviewed
- [x] Interface is simple: expression in → SQL out
- [x] No intermediate data formats (no fragments, no separate CTE assembly)
- [x] Design maintains thin dialect principle
- [x] Design supports future CQL library features

---

## Background: Current Architecture

### Current Pipeline (4 components)
```
┌─────────────┐    ┌────────────┐    ┌─────────────┐    ┌───────────────┐
│ AST Adapter │ → │ Translator │ → │ CTE Builder │ → │ CTE Assembler │
└─────────────┘    └────────────┘    └─────────────┘    └───────────────┘
     │                   │                  │                   │
     ▼                   ▼                  ▼                   ▼
 Core AST          SQLFragments          CTEs             Final SQL
```

**Problems:**
- 3 handoffs where metadata can be lost
- Translator produces fragments, doesn't know how they'll be assembled
- CTE Builder doesn't know the original expression intent
- CTE Assembler just combines without understanding content

### Files to Study
1. `fhir4ds/fhirpath/sql/translator.py` - Current translator (9,050 lines)
2. `fhir4ds/fhirpath/sql/cte.py` - CTE Builder + Assembler (~1,000 lines)
3. `fhir4ds/fhirpath/sql/ast_adapter.py` - AST conversion (~1,400 lines)
4. `fhir4ds/fhirpath/sql/fragments.py` - Fragment data structure (~180 lines)
5. `fhir4ds/fhirpath/sql/executor.py` - How components are orchestrated (~290 lines)

---

## Design Requirements

### 1. Simple Interface

```python
class SQLGenerator:
    def __init__(self, dialect: DatabaseDialect, resource_type: str):
        """Initialize with dialect and resource type."""

    def generate(self, expression: str) -> str:
        """
        Convert FHIRPath expression to SQL.

        Args:
            expression: FHIRPath expression string (e.g., "Patient.name.given.first()")

        Returns:
            Complete SQL query string ready for execution
        """
```

### 2. No Intermediate Formats

Current approach creates intermediate data:
```python
# BAD: Multiple intermediate formats
ast = adapter.convert(enhanced_ast)      # Format 1: Core AST
fragments = translator.translate(ast)     # Format 2: SQLFragments
ctes = builder.build_cte_chain(fragments) # Format 3: CTEs
sql = assembler.assemble_query(ctes)      # Format 4: SQL string
```

New approach should be direct:
```python
# GOOD: Direct conversion
sql = generator.generate("Patient.name.given.first()")  # Expression → SQL
```

### 3. Internal Organization

The class should be organized by **expression type**, not by **pipeline stage**:

```python
class SQLGenerator:
    # Path navigation
    def _generate_path(self, node: PathNode) -> str: ...

    # Function calls
    def _generate_function(self, node: FunctionCallNode) -> str: ...
    def _generate_first(self, node: FunctionCallNode) -> str: ...
    def _generate_count(self, node: FunctionCallNode) -> str: ...

    # Operators
    def _generate_comparison(self, node: BinaryOpNode) -> str: ...
    def _generate_boolean(self, node: BinaryOpNode) -> str: ...

    # Helpers
    def _wrap_in_cte(self, sql: str, cte_name: str) -> str: ...
    def _generate_unnest(self, array_expr: str) -> str: ...
```

### 4. CTE Generation Strategy

CTEs should be generated **inline** when needed, not as a separate step:

```python
def _generate_path_with_array(self, path_components: List[str]) -> str:
    """Generate SQL for path that traverses arrays."""
    # Build CTE directly here when needed
    if self._needs_unnest(path_components):
        return f"""
            WITH cte_1 AS (
                SELECT id, resource, item.unnest AS {alias}
                FROM resource, LATERAL UNNEST({array_expr}) AS item
            )
            SELECT * FROM cte_1
        """
    else:
        return f"SELECT {json_extract} FROM resource"
```

### 5. Maintain Thin Dialect Principle

The dialect should only provide **syntax helpers**, not business logic:

```python
# GOOD: Dialect provides syntax
sql = self.dialect.json_extract(column="resource", path="$.name")
sql = self.dialect.unnest_array(array_expr)

# BAD: Dialect contains logic (don't do this)
sql = self.dialect.generate_path_navigation(path)  # Too much logic!
```

---

## Design Document Template

Create the file `project-docs/architecture/unified-sql-generator-design.md` with this structure:

```markdown
# Unified SQLGenerator Design

## Overview
[Brief description of what this component does]

## Interface

### Public Methods
[Document each public method with signature and description]

### Constructor Parameters
[Document initialization parameters]

## Internal Architecture

### Class Structure
[Diagram showing internal organization]

### Method Categories
[Group methods by purpose: path navigation, functions, operators, etc.]

## Data Flow

### Simple Expression
[Show how "Patient.name" flows through the generator]

### Complex Expression
[Show how "Patient.name.given.first().count()" flows through]

## Key Design Decisions

### Decision 1: [Title]
- **Context**: [What problem we're solving]
- **Decision**: [What we decided]
- **Rationale**: [Why this approach]
- **Consequences**: [Trade-offs]

### Decision 2: ...

## Migration Path
[How to transition from current 4 components to this 1 component]

## Testing Strategy
[How to verify the new component works correctly]
```

---

## Step-by-Step Instructions

### Step 1: Study Current Components (2-3 hours)

Read these files to understand what each does:

1. **executor.py** - See how components are called in sequence
2. **translator.py** - Understand how AST → Fragments works (focus on `translate()` method)
3. **cte.py** - Understand how Fragments → CTEs → SQL works

Take notes on:
- What data is passed between components
- What metadata is needed at each stage
- Where bugs have been occurring (see recent commits)

### Step 2: Sketch the New Interface (1 hour)

Write out:
- The public method signatures
- What parameters they need
- What they return

Keep it simple - one main method: `generate(expression: str) -> str`

### Step 3: Design Internal Structure (2 hours)

Decide how to organize the internal methods:
- Group by expression type (paths, functions, operators)
- Identify shared helpers (CTE generation, UNNEST handling)
- Plan how recursion will work for nested expressions

### Step 4: Document Data Flow (1 hour)

Draw diagrams showing how different expressions flow through:
- Simple path: `Patient.name`
- Path with array: `Patient.name.given`
- Function call: `Patient.name.given.count()`
- Chained functions: `Patient.name.given.first().count()`

### Step 5: Write Design Document (2 hours)

Create the markdown file with all sections filled in.

### Step 6: Get Review (async)

Share the design document for review before implementation begins.

---

## Common Pitfalls to Avoid

1. **Don't copy the current structure** - We're simplifying, not reorganizing
2. **Don't add intermediate formats** - Go directly from AST to SQL
3. **Don't put logic in dialects** - Keep them thin (syntax only)
4. **Don't over-engineer** - Start simple, add complexity only when needed

---

## Resources

### Current Architecture Docs
- `project-docs/process/architecture-overview.md`
- `project-docs/architecture/fhirpath-execution-pipeline.md`

### FHIRPath Specification
- https://hl7.org/fhirpath/

### Example of Good Design
Look at how `executor.py` orchestrates the pipeline - your design should make this much simpler:

```python
# Current executor.py (simplified)
def execute_with_details(self, expression: str):
    parsed = self.parser.parse(expression)
    enhanced_ast = parsed.get_ast()
    fhirpath_ast = self.adapter.convert(enhanced_ast)
    fragments = self.translator.translate(fhirpath_ast)
    ctes = self.cte_builder.build_cte_chain(fragments)
    sql = self.cte_assembler.assemble_query(ctes)
    results = self.dialect.execute_query(sql)
    return results

# Target executor.py (simplified)
def execute_with_details(self, expression: str):
    parsed = self.parser.parse(expression)
    ast = parsed.get_ast()
    sql = self.generator.generate(ast)
    results = self.dialect.execute_query(sql)
    return results
```

---

## Progress Tracking

### Status
- [x] Completed

### Completion Checklist
- [x] Studied current components (translator.py, cte.py, ast_adapter.py)
- [x] Sketched public interface
- [x] Designed internal method structure
- [x] Documented data flow for various expression types
- [x] Created design document
- [x] Submitted for review
- [x] Addressed review feedback
- [x] Design approved

### Progress Updates

| Date | Status | Notes |
|------|--------|-------|
| 2025-12-16 | Completed | Design document created at `project-docs/architecture/unified-sql-generator-design.md`. Studied all 4 current components, designed unified SQLGenerator interface with inline CTE generation. Ready for senior architect review. |
| 2025-12-17 | Approved | Senior architect review completed. All acceptance criteria met. Merged to main. |

---

**Task Created**: 2025-12-13
**Task Completed**: 2025-12-17
**Status**: Completed
