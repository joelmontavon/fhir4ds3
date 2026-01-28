# Sprint SP-103 Orientation Guide

## Sprint Overview

**Goal:** Achieve 100% compliance on official FHIRPath test suite (934 tests)  
**Starting Point:** 54.8% (512/934 passing, 422 failing)  
**Target:** 100% (934/934 passing)

## Project Structure

```
/mnt/d/fhir4ds3/                    # Main repo
├── fhir4ds/
│   ├── fhirpath/
│   │   ├── parser.py              # FHIRPath parser
│   │   ├── sql/
│   │   │   ├── translator.py      # SQL translation engine
│   │   │   ├── cte_builder.py     # CTE construction
│   │   │   └── executor.py        # Query executor
│   │   └── fhir_types/            # FHIR type system
│   ├── dialects/
│   │   ├── base.py                # Base dialect
│   │   ├── duckdb.py              # DuckDB dialect
│   │   └── postgresql.py          # PostgreSQL dialect
│   └── ...
├── tests/
│   ├── integration/fhirpath/
│   │   └── official_test_runner.py  # Official test runner
│   ├── compliance/fhirpath/
│   │   └── official_tests.xml       # HL7 test suite
│   └── unit/fhirpath/sql/           # Unit tests
└── project-docs/
    └── plans/
        ├── current-sprint/          # Active sprint
        └── tasks/                   # Task documents
```

## Key Architecture Principles

### 1. Unified FHIRPath Architecture
- FHIRPath is the foundation for all expression languages
- CTE-first design for population-scale performance
- Thin dialects (syntax ONLY, no business logic)

### 2. Database Dialect Requirements
**CRITICAL:** Dialect implementations must contain ONLY syntax differences.
- No business logic in dialect classes
- Use method overriding for database-specific syntax
- Example: `generate_json_extract()` differs, but `translate_is()` is identical

### 3. Test-Driven Development
- Run official test suite before and after each change
- Use specific test filters to validate fixes
- Maintain dual-database parity (DuckDB + PostgreSQL)

## Running Tests

### Quick Validation (50 tests)
```python
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=50)
"
```

### Full Suite (934 tests)
```python
PYTHONPATH=. timeout 512 python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=None)
"
```

### Specific Test Filter
```python
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='convertsTo')
```

### Unit Tests
```bash
python3 -m pytest tests/unit/fhirpath/sql/ -v
```

## Common Work Patterns

### 1. Fixing a Function
```python
# 1. Find failing tests
python3 -c "
from tests.integration.fhirpath.official_test_runner import EnhancedOfficialTestRunner
runner = EnhancedOfficialTestRunner(database_type='duckdb')
report = runner.run_official_tests(test_filter='substring')

for result in runner.test_results:
    if not result.passed:
        print(f'{result.name}: {result.expression}')
        print(f'  Expected: {result.expected_outputs}')
        print(f'  Actual: {result.actual_result}')
        print(f'  Error: {result.error_message}')
"

# 2. Locate implementation
# fhir4ds/fhirpath/sql/translator.py

# 3. Implement fix
# 4. Run tests to validate
# 5. Create unit tests
# 6. Commit with task ID
```

### 2. Adding Type Support
```python
# 1. Check FHIR type system
# fhir4ds/fhirpath/fhir_types/

# 2. Add type definition
# 3. Update type registry
# 4. Add conversion logic if needed
# 5. Test with official suite
```

### 3. CTE Column Propagation
```python
# Common issue: "Referenced column 'X' not found"
# Cause: CTE columns not propagated through function chain
# Fix: Update CTE builder to track columns

# fhir4ds/fhirpath/sql/cte_builder.py
```

## Known Issues & Patterns

### DateTime Literals
**Problem:** `@2015T`, `@T14:34:28Z` not recognized  
**Location:** Parser literal handling  
**Fix:** Add partial date/time patterns

### Unary Polarity
**Problem:** `-expr.convertsToInteger()` fails  
**Location:** SQL translation of unary operators  
**Fix:** Proper parenthesization in SQL generation

### convertsTo Functions
**Problem:** Type conversion validation incorrect  
**Location:** Type checking logic  
**Fix:** Implement proper type inference

### Collection Functions
**Problem:** CTE column propagation failures  
**Location:** CTE builder column tracking  
**Fix:** Maintain column metadata through CTE chain

## Git Workflow

```bash
# Create worktree (one-time)
git worktree add ../sprint-SP-103 sprint/SP-103
cd ../sprint-SP-103

# Create task branch
git checkout -b SP-103-001-datetime-literals

# Implement fix
# ...

# Test
PYTHONPATH=. python3 -c "
from tests.integration.fhirpath.official_test_runner import run_compliance_measurement
run_compliance_measurement(database_type='duckdb', max_tests=50)
"

# Commit
git add .
git commit -m "feat(SP-103-001): add datetime literal parsing support"

# Return to sprint branch
git checkout sprint-SP-103
git merge SP-103-001-datetime-literals --no-ff

# Delete task branch
git branch -d SP-103-001-datetime-literals
```

## Code Review Checklist

Before marking a task complete:
- [ ] All affected tests passing
- [ ] Unit tests added/updated
- [ ] No architectural violations
- [ ] Dual-database parity maintained
- [ ] Code follows project style
- [ ] Documentation updated

## Getting Help

### Architectural Questions
- Review: `CLAUDE.md`
- Architecture: `project-docs/architecture/`

### Test Failures
- Check: `tests/compliance/fhirpath/README.md`
- Run: Specific test filter for debugging

### CTE Issues
- Reference: `fhir4ds/fhirpath/sql/cte_builder.py`
- Patterns: Look for similar functions that work

## Success Metrics

Each task should show measurable improvement:
- Specific test count increase
- Compliance percentage increase
- Zero regressions in other areas

---

**Remember:** Focus on simplicity. Make the smallest change that fixes the issue. Test thoroughly before committing.
