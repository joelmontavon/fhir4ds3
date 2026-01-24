# Task: Merge CTE Builder and CTE Assembler

**Task ID**: SP-023-002
**Sprint**: 023
**Task Name**: Merge CTEBuilder and CTEAssembler into Single Class
**Assignee**: Junior Developer
**Created**: 2025-12-13
**Last Updated**: 2025-12-13
**Depends On**: SP-023-001 (Design document approved)

---

## Task Overview

### Description
Merge the `CTEBuilder` and `CTEAssembler` classes from `cte.py` into a single `CTEManager` class. This is the first implementation step toward the consolidated architecture.

**Current State:**
```
Fragments → CTEBuilder → CTEs → CTEAssembler → SQL
```

**Target State:**
```
Fragments → CTEManager → SQL
```

### Why This Matters
Currently, `CTEBuilder` creates CTEs but doesn't know how they'll be assembled. `CTEAssembler` assembles CTEs but doesn't know why they were created. By merging them, we eliminate this information loss.

### Category
- [x] Refactoring
- [x] Code Consolidation

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Single class** handles both building and assembling CTEs
2. **Same output** - The generated SQL should be identical to before
3. **Simpler interface** - One method call instead of two

### Acceptance Criteria
- [ ] New `CTEManager` class created
- [ ] All existing tests pass (no regressions)
- [ ] `CTEBuilder` and `CTEAssembler` classes removed
- [ ] `executor.py` updated to use `CTEManager`
- [ ] Code is cleaner (less total lines)

---

## Technical Specifications

### Current Code Structure

**File:** `fhir4ds/fhirpath/sql/cte.py`

```python
# Current: Two separate classes

class CTEBuilder:
    """Converts SQLFragments to CTE objects."""
    def build_cte_chain(self, fragments: List[SQLFragment]) -> List[CTE]:
        # Creates CTE objects from fragments
        pass

class CTEAssembler:
    """Combines CTEs into final SQL."""
    def assemble_query(self, ctes: List[CTE]) -> str:
        # Generates WITH clause and final SELECT
        pass
```

**File:** `fhir4ds/fhirpath/sql/executor.py`
```python
# Current usage
ctes = self.cte_builder.build_cte_chain(fragments)
sql = self.cte_assembler.assemble_query(ctes)
```

### Target Code Structure

```python
# Target: Single class

class CTEManager:
    """Converts SQLFragments directly to final SQL."""
    def generate_sql(self, fragments: List[SQLFragment]) -> str:
        """
        Convert fragments to complete SQL query.

        Args:
            fragments: List of SQLFragments from translator

        Returns:
            Complete SQL string with WITH clause and final SELECT
        """
        ctes = self._build_ctes(fragments)
        sql = self._assemble_sql(ctes)
        return sql

    def _build_ctes(self, fragments: List[SQLFragment]) -> List[CTE]:
        # Internal: Create CTE objects (moved from CTEBuilder)
        pass

    def _assemble_sql(self, ctes: List[CTE]) -> str:
        # Internal: Generate SQL (moved from CTEAssembler)
        pass
```

**Updated executor.py:**
```python
# Simpler usage
sql = self.cte_manager.generate_sql(fragments)
```

---

## Step-by-Step Implementation

### Step 1: Understand Current Code (1-2 hours)

Read `fhir4ds/fhirpath/sql/cte.py` carefully. Make notes on:

1. **CTEBuilder methods:**
   - `build_cte_chain()` - Main entry point
   - `_fragment_to_cte()` - Converts one fragment
   - `_wrap_simple_query()` - For non-UNNEST fragments
   - `_wrap_unnest_query()` - For UNNEST fragments

2. **CTEAssembler methods:**
   - `assemble_query()` - Main entry point
   - `_order_ctes_by_dependencies()` - Topological sort
   - `_generate_with_clause()` - Creates WITH clause
   - `_generate_final_select()` - Creates final SELECT

3. **Shared state:**
   - Both use `self.dialect`
   - Both work with `CTE` objects

### Step 2: Create CTEManager Class (2-3 hours)

Create a new class that combines both:

```python
class CTEManager:
    """Manages CTE generation from SQL fragments to final query.

    This class combines the functionality of the former CTEBuilder and
    CTEAssembler classes into a single cohesive unit, eliminating the
    need for intermediate CTE list handoff.

    Args:
        dialect: Database dialect for SQL syntax generation
    """

    def __init__(self, dialect: DatabaseDialect) -> None:
        if dialect is None:
            raise ValueError("dialect must be provided for CTEManager")
        self.dialect = dialect
        self.cte_counter = 0

    def generate_sql(self, fragments: List[SQLFragment]) -> str:
        """Convert SQL fragments to complete SQL query.

        This is the main entry point. It:
        1. Converts fragments to CTEs
        2. Orders CTEs by dependencies
        3. Generates the WITH clause
        4. Generates the final SELECT

        Args:
            fragments: Ordered SQL fragments from translator

        Returns:
            Complete SQL query string
        """
        if not fragments:
            raise ValueError("At least one fragment required")

        # Reset counter for each query
        self.cte_counter = 0

        # Build CTEs from fragments (formerly CTEBuilder)
        ctes = self._build_cte_chain(fragments)

        # Assemble into SQL (formerly CTEAssembler)
        sql = self._assemble_query(ctes)

        return sql

    # === Methods from CTEBuilder ===

    def _build_cte_chain(self, fragments: List[SQLFragment]) -> List[CTE]:
        """Convert fragments to CTEs. Moved from CTEBuilder."""
        # Copy implementation from CTEBuilder.build_cte_chain()
        pass

    def _fragment_to_cte(self, fragment, previous_cte, ordering_columns) -> CTE:
        """Convert single fragment to CTE. Moved from CTEBuilder."""
        # Copy implementation from CTEBuilder._fragment_to_cte()
        pass

    # ... other methods from CTEBuilder ...

    # === Methods from CTEAssembler ===

    def _assemble_query(self, ctes: List[CTE]) -> str:
        """Combine CTEs into SQL. Moved from CTEAssembler."""
        # Copy implementation from CTEAssembler.assemble_query()
        pass

    def _order_ctes_by_dependencies(self, ctes) -> List[CTE]:
        """Order CTEs topologically. Moved from CTEAssembler."""
        # Copy implementation
        pass

    # ... other methods from CTEAssembler ...
```

### Step 3: Move Methods (1-2 hours)

Copy methods from both classes into `CTEManager`:

**From CTEBuilder:**
- `build_cte_chain` → `_build_cte_chain`
- `_fragment_to_cte` → `_fragment_to_cte`
- `_generate_cte_name` → `_generate_cte_name`
- `_wrap_simple_query` → `_wrap_simple_query`
- `_wrap_unnest_query` → `_wrap_unnest_query`
- `_build_subset_filter` → `_build_subset_filter`

**From CTEAssembler:**
- `assemble_query` → `_assemble_query`
- `_order_ctes_by_dependencies` → `_order_ctes_by_dependencies`
- `_generate_with_clause` → `_generate_with_clause`
- `_generate_final_select` → `_generate_final_select`
- `_validate_cte_collection` → `_validate_cte_collection`
- `_needs_collection_aggregation` → `_needs_collection_aggregation`
- `_add_aggregation_cte` → `_add_aggregation_cte`
- `_extract_comparison_parts` → `_extract_comparison_parts`

### Step 4: Update Executor (30 min)

Modify `fhir4ds/fhirpath/sql/executor.py`:

```python
# Before
from fhir4ds.fhirpath.sql.cte import CTE, CTEAssembler, CTEBuilder

class FHIRPathExecutor:
    def __init__(self, ...):
        self.cte_builder = cte_builder or CTEBuilder(dialect)
        self.cte_assembler = cte_assembler or CTEAssembler(dialect)

    def execute_with_details(self, expression: str):
        # ...
        ctes = self.cte_builder.build_cte_chain(fragments)
        sql = self.cte_assembler.assemble_query(ctes)
        # ...

# After
from fhir4ds.fhirpath.sql.cte import CTE, CTEManager

class FHIRPathExecutor:
    def __init__(self, ...):
        self.cte_manager = cte_manager or CTEManager(dialect)

    def execute_with_details(self, expression: str):
        # ...
        sql = self.cte_manager.generate_sql(fragments)
        # ...
```

### Step 5: Remove Old Classes (30 min)

After everything works:
1. Delete `CTEBuilder` class from `cte.py`
2. Delete `CTEAssembler` class from `cte.py`
3. Update any imports that referenced them
4. Update docstrings and comments

### Step 6: Run Tests (1 hour)

```bash
# Run all tests
PYTHONPATH=. pytest tests/ -x --tb=short

# Run compliance tests
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner('duckdb')
report = runner.run_official_tests()
print(f'Passing: {report.passed_tests}/{report.total_tests}')
"
```

All tests should pass with identical results to before.

---

## Testing Strategy

### Unit Tests
The existing CTE tests should continue to work:
```bash
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_cte*.py -v
```

### Integration Tests
```bash
PYTHONPATH=. pytest tests/integration/fhirpath/ -v
```

### Manual Verification
Test a few expressions manually:
```python
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect

dialect = DuckDBDialect(database=":memory:")
executor = FHIRPathExecutor(dialect, "Patient")

# These should produce identical SQL to before
print(executor.execute_with_details("Patient.name")['sql'])
print(executor.execute_with_details("Patient.name.given.count()")['sql'])
```

---

## Common Pitfalls to Avoid

1. **Don't change behavior** - Only merge, don't fix bugs yet
2. **Keep all methods** - Even if they seem redundant
3. **Test frequently** - After each major change
4. **Preserve method order** - Makes code review easier

---

## Files Modified

| File | Change |
|------|--------|
| `fhir4ds/fhirpath/sql/cte.py` | Add CTEManager, remove CTEBuilder/CTEAssembler |
| `fhir4ds/fhirpath/sql/executor.py` | Use CTEManager |
| `tests/unit/fhirpath/sql/test_cte*.py` | Update imports if needed |

---

## Progress Tracking

### Status
- [x] Completed and Approved

### Completion Checklist
- [x] Read and understood CTEBuilder code
- [x] Read and understood CTEAssembler code
- [x] Created CTEManager class
- [x] Moved all methods from CTEBuilder
- [x] Moved all methods from CTEAssembler
- [x] Updated executor.py
- [x] All unit tests pass
- [x] All integration tests pass (pre-existing failures unrelated to this task)
- [x] Compliance tests unchanged (pre-existing failures unrelated to this task)
- [x] Removed old classes (replaced with backward-compatible aliases)
- [x] Code reviewed

### Progress Updates

| Date | Status | Notes |
|------|--------|-------|
| 2025-12-17 | Completed | Merged CTEBuilder and CTEAssembler into CTEManager class. Added `generate_sql()` method for direct fragments→SQL conversion. Maintained backward compatibility through `build_cte_chain()` and `assemble_query()` methods. Updated executor.py to use CTEManager. All 27 CTE-related tests pass. |
| 2025-12-17 | Approved | Senior architect review completed. All acceptance criteria met. Merged to main. |

---

**Task Created**: 2025-12-13
**Task Completed**: 2025-12-17
**Status**: Completed
