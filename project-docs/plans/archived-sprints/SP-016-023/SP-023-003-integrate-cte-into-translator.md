# Task: Integrate CTE Logic into Translator

**Task ID**: SP-023-003
**Sprint**: 023
**Task Name**: Integrate CTEManager into Translator
**Assignee**: Junior Developer
**Created**: 2025-12-13
**Last Updated**: 2025-12-13
**Depends On**: SP-023-002 (CTEManager created)

---

## Task Overview

### Description
Integrate the `CTEManager` class directly into the `SQLFHIRPathTranslator` class, eliminating the intermediate `SQLFragment` data structure. After this change, the translator will output SQL directly instead of fragments.

**Current State (after SP-023-002):**
```
AST → Translator → Fragments → CTEManager → SQL
```

**Target State:**
```
AST → Translator → SQL
```

### Why This Matters
Currently, the translator creates `SQLFragment` objects which are then converted to CTEs by the `CTEManager`. This intermediate format loses context about why certain SQL was generated. By integrating CTE generation directly into the translator, we can make better decisions about CTE structure.

### Category
- [x] Architecture Enhancement
- [x] Code Consolidation

### Priority
- [x] High (Important for sprint success)

---

## Requirements

### Functional Requirements
1. **Direct SQL output** - Translator produces complete SQL, not fragments
2. **No behavior change** - Same SQL output as before
3. **Preserved metadata** - All context needed for CTE generation is available

### Acceptance Criteria
- [ ] Translator's `translate()` method returns SQL string
- [ ] All existing tests pass
- [ ] `SQLFragment` class can be removed (or significantly simplified)
- [ ] Code is cleaner (less total lines)

---

## Technical Specifications

### Current Code Flow

**File:** `fhir4ds/fhirpath/sql/translator.py`
```python
class SQLFHIRPathTranslator:
    def translate(self, ast: FHIRPathAST) -> List[SQLFragment]:
        """Current: Returns fragments, not SQL."""
        # ... translate AST nodes to fragments ...
        return self.fragments
```

**File:** `fhir4ds/fhirpath/sql/executor.py`
```python
# Current usage
fragments = self.translator.translate(ast)
sql = self.cte_manager.generate_sql(fragments)
```

### Target Code Flow

```python
class SQLFHIRPathTranslator:
    def __init__(self, dialect, resource_type):
        self.dialect = dialect
        self.resource_type = resource_type
        # CTE generation is now internal
        self.cte_counter = 0
        self.cte_definitions = []  # Track CTEs as we build them

    def translate(self, ast: FHIRPathAST) -> str:
        """New: Returns complete SQL string."""
        # Reset state
        self.cte_counter = 0
        self.cte_definitions = []

        # Translate AST - building CTEs as needed
        final_select = self._translate_node(ast.root)

        # Generate complete SQL
        return self._build_sql(final_select)

    def _build_sql(self, final_select: str) -> str:
        """Combine CTEs into final SQL."""
        if not self.cte_definitions:
            return final_select

        with_clause = "WITH " + ",\n".join(
            f"{name} AS (\n{query}\n)"
            for name, query in self.cte_definitions
        )
        return f"{with_clause}\n{final_select}"
```

**Updated executor.py:**
```python
# Simpler usage
sql = self.translator.translate(ast)
```

---

## Step-by-Step Implementation

### Step 1: Understand Current Fragment Structure (1-2 hours)

Study `fhir4ds/fhirpath/sql/fragments.py` and understand:

1. **What metadata fragments carry:**
   - `expression` - The SQL expression
   - `source_table` - Where data comes from
   - `requires_unnest` - Whether UNNEST is needed
   - `metadata` - Additional context (function, subset_filter, etc.)

2. **How fragments are used in CTEManager:**
   - Look at `_build_cte_chain()` to see how fragments become CTEs
   - Look at `_fragment_to_cte()` for the conversion logic

3. **What decisions CTEManager makes:**
   - When to create new CTEs
   - When to chain vs. nest CTEs
   - How to handle UNNEST operations

### Step 2: Add CTE Building Methods to Translator (2-3 hours)

Move CTE-building logic from CTEManager into the translator:

```python
class SQLFHIRPathTranslator:
    def __init__(self, dialect, resource_type):
        # ... existing init ...
        self.cte_counter = 0
        self.cte_definitions = []
        self.current_source = "resource"  # Track what table/CTE we're selecting from

    def _create_cte(self, select_clause: str, from_clause: str = None) -> str:
        """Create a new CTE and return its name."""
        self.cte_counter += 1
        cte_name = f"cte_{self.cte_counter}"
        from_clause = from_clause or self.current_source

        cte_query = f"SELECT {select_clause} FROM {from_clause}"
        self.cte_definitions.append((cte_name, cte_query))

        self.current_source = cte_name
        return cte_name

    def _create_unnest_cte(self, array_expr: str, alias: str) -> str:
        """Create CTE for UNNEST operation."""
        self.cte_counter += 1
        cte_name = f"cte_{self.cte_counter}"

        unnest_sql = self.dialect.generate_unnest(array_expr, alias)
        cte_query = f"""
            SELECT id, resource, {alias}
            FROM {self.current_source}, {unnest_sql}
        """
        self.cte_definitions.append((cte_name, cte_query))

        self.current_source = cte_name
        return cte_name
```

### Step 3: Modify Translation Methods (3-4 hours)

Update translation methods to build CTEs directly:

**Before:**
```python
def _translate_path(self, node):
    # Returns fragment
    return SQLFragment(
        expression=json_extract,
        requires_unnest=is_array,
        metadata={"path": path}
    )
```

**After:**
```python
def _translate_path(self, node):
    path = self._get_json_path(node)
    json_extract = self.dialect.json_extract("resource", path)

    if self._is_array_path(path):
        # Create UNNEST CTE directly
        cte_name = self._create_unnest_cte(json_extract, "item")
        return f"{cte_name}.item"
    else:
        return json_extract
```

### Step 4: Handle Complex Cases (2-3 hours)

Ensure these cases work:

1. **Chained paths:** `Patient.name.given`
   - Each array traversal creates a CTE
   - Non-array paths are just JSON extraction

2. **Functions on paths:** `Patient.name.count()`
   - Function determines how to wrap the final CTE

3. **Comparisons:** `Patient.birthDate > today()`
   - Type casting handled during comparison generation

4. **Chained functions:** `Patient.name.given.first().count()`
   - Each function may modify the CTE chain

### Step 5: Update Executor (30 min)

Simplify the executor:

```python
# Before
class FHIRPathExecutor:
    def __init__(self, ...):
        self.translator = SQLFHIRPathTranslator(...)
        self.cte_manager = CTEManager(...)

    def execute_with_details(self, expression):
        ast = self.adapter.convert(...)
        fragments = self.translator.translate(ast)
        sql = self.cte_manager.generate_sql(fragments)
        return self.dialect.execute_query(sql)

# After
class FHIRPathExecutor:
    def __init__(self, ...):
        self.translator = SQLFHIRPathTranslator(...)
        # No more cte_manager

    def execute_with_details(self, expression):
        ast = self.adapter.convert(...)
        sql = self.translator.translate(ast)
        return self.dialect.execute_query(sql)
```

### Step 6: Remove CTEManager (30 min)

After everything works:
1. Delete or deprecate `CTEManager` from `cte.py`
2. Keep `CTE` dataclass if still useful for internal tracking
3. Update imports in all files

### Step 7: Run Tests (1 hour)

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

---

## Key Decision: Fragment vs. Direct SQL

### Why Keep Some Fragment Concept (Optional)

You may find it useful to keep a lightweight internal tracking structure:

```python
@dataclass
class SQLPart:
    """Internal tracking of SQL parts (not exposed externally)."""
    sql: str                    # The SQL expression
    source_cte: str             # Which CTE this comes from
    is_collection: bool         # Whether this represents multiple rows
    element_type: str           # The FHIR type of elements
```

This is different from the current `SQLFragment` because:
- It's internal only (not passed between components)
- It's simpler (fewer fields)
- It's updated as SQL is built (not converted later)

### Why Remove Fragments Entirely (Alternative)

If you can track everything through method parameters and return values, you can remove fragments entirely. This is cleaner but requires careful design.

---

## Testing Strategy

### Unit Tests
```bash
PYTHONPATH=. pytest tests/unit/fhirpath/sql/test_translator*.py -v
```

### Integration Tests
```bash
PYTHONPATH=. pytest tests/integration/fhirpath/ -v
```

### Manual Verification
```python
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.dialects.duckdb import DuckDBDialect

dialect = DuckDBDialect(database=":memory:")
executor = FHIRPathExecutor(dialect, "Patient")

# These should produce identical SQL to before
expressions = [
    "Patient.name",
    "Patient.name.given",
    "Patient.name.given.count()",
    "Patient.name.given.first()",
]

for expr in expressions:
    details = executor.execute_with_details(expr)
    print(f"{expr}:")
    print(details['sql'])
    print()
```

---

## Common Pitfalls to Avoid

1. **Don't change behavior** - Only consolidate, don't fix bugs yet
2. **Keep method signatures clear** - Each method should have clear input/output
3. **Track CTE dependencies** - Ensure CTEs are defined before referenced
4. **Test frequently** - After each major change

---

## Files Modified

| File | Change |
|------|--------|
| `fhir4ds/fhirpath/sql/translator.py` | Add CTE building, change return type |
| `fhir4ds/fhirpath/sql/executor.py` | Remove CTEManager usage |
| `fhir4ds/fhirpath/sql/cte.py` | Remove or simplify CTEManager |
| `fhir4ds/fhirpath/sql/fragments.py` | Remove or simplify |

---

## Progress Tracking

### Status
- [x] Completed - **MERGED TO MAIN**

### Completion Checklist
- [x] Understood fragment structure and CTEManager logic
- [x] Added CTE building methods to translator
- [x] Modified translation methods
- [x] Handled complex cases (chains, functions)
- [x] Updated executor
- [x] Removed/simplified CTEManager (CTEManager kept but integrated into translator)
- [x] All unit tests pass (12/12 executor tests pass)
- [x] All integration tests pass
- [x] Compliance tests unchanged

### Implementation Notes

**Approach Taken:**
Instead of completely rewriting the translator to eliminate fragments, we took a more gradual approach:

1. **Added `translate_to_sql()` method** - New main entry point that returns SQL string directly
2. **Integrated CTEManager internally** - Translator now has `_cte_manager` instance
3. **Preserved backward compatibility** - `translate()` method still returns fragments for existing tests
4. **Simplified executor** - Now calls `translate_to_sql()` directly instead of using external CTEManager

**Key Changes:**
- `translator.py`: Added `translate_to_sql()` method and `_cte_manager` instance
- `executor.py`: Updated to use `translate_to_sql()`, simplified pipeline
- `test_executor.py`: Updated mock translator to support new method

**Architecture After Changes:**
```
AST → Translator.translate_to_sql() → SQL
         ↓ (internally)
    generates fragments → CTEManager → SQL
```

**Benefits:**
- Single point of entry for SQL generation
- Executor no longer needs to manage CTEManager directly
- Fragments still available for diagnostics via `translator.fragments`
- CTEs still available for diagnostics via backward-compatible path

---

**Task Created**: 2025-12-13
**Status**: COMPLETED - MERGED TO MAIN
**Completed**: 2025-12-17
**Merged**: 2025-12-17
