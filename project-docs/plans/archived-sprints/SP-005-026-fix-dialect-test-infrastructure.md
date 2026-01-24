# Task: Fix Dialect Test Infrastructure Issues

**Task ID**: SP-005-026 | **Sprint**: 005 | **Estimate**: 4h | **Priority**: Medium | **Status**: Completed
**Created**: 2025-09-30 | **Completed**: 2025-09-30 | **Type**: Bug Fix / Technical Debt

## Overview

Address pre-existing test infrastructure issues in dialect unit tests identified during SP-005-007 review. These issues exist on the main branch and are not regressions, but should be resolved to maintain test suite health.

## Background

During senior review of SP-005-007, 8 pre-existing test failures were identified:
1. **DuckDB**: `test_execute_query_success` - Mock setup issue with return values
2. **PostgreSQL Factory Tests**: 7 tests failing due to PostgreSQL connection requirements

These failures exist on main branch (confirmed by checkout and test execution) and are unrelated to recent changes.

## Acceptance Criteria

- [x] Fix `test_execute_query_success` DuckDB mock setup
- [x] Address PostgreSQL factory test connection requirements
- [x] All 137 dialect tests passing (100%)
- [x] No changes to production code (test-only changes)
- [x] Documentation of test environment requirements if needed

## Issues to Address

### 1. DuckDB Mock Test Failure

**File**: `tests/unit/dialects/test_duckdb_dialect.py:51-57`

**Current Issue**:
```python
def test_execute_query_success(self, dialect, mock_connection):
    """Test successful query execution."""
    mock_connection.execute.return_value.fetchall.return_value = [('test',)]
    # Error: 'NoneType' object has no attribute 'fetchall'
```

**Root Cause**:
- `mock_connection.execute.return_value` is set to `None` in fixture
- Attempting to set `.fetchall.return_value` on None fails

**Solution Approach**:
- Fix mock_connection fixture to properly chain return values
- Ensure `mock_connection.execute()` returns a mock result object with `fetchall()` method

### 2. PostgreSQL Factory Tests

**Files**: `tests/unit/dialects/test_factory.py`

**Failing Tests** (7 total):
- `test_create_dialect_postgresql_explicit`
- `test_create_dialect_auto_detect_duckdb`
- `test_create_dialect_auto_detect_postgresql`
- `test_create_dialect_with_creation_failure`
- `test_create_from_config`
- `test_case_insensitive_database_type`
- `test_postgresql_alias_handling`

**Current Issue**:
```
psycopg2.OperationalError: connection to server at "localhost" (127.0.0.1), port 5432 failed:
fe_sendauth: no password supplied
```

**Root Cause**:
- Tests attempt to create real PostgreSQL connections
- Mocking not properly intercepting dialect creation
- Test isolation compromised

**Solution Approaches**:
1. **Option A**: Improve mocking to prevent actual connection attempts
2. **Option B**: Add pytest markers for tests requiring real database connections
3. **Option C**: Use test fixtures with proper mock patching at module level

## Implementation Plan

### Step 1: Fix DuckDB Mock Test

1. Update `mock_connection` fixture in `test_duckdb_dialect.py`
2. Properly chain mock return values
3. Verify test passes with correct mock setup

### Step 2: Fix PostgreSQL Factory Tests

1. Analyze each failing test's mocking strategy
2. Ensure mocks intercept connection creation at correct level
3. Consider using `patch.object()` or module-level patching
4. Verify tests pass without requiring PostgreSQL server

### Step 3: Validate Test Suite

1. Run full dialect test suite: `pytest tests/unit/dialects/ -v`
2. Confirm 137/137 tests passing (100%)
3. Verify no regressions in related tests

### Step 4: Documentation

1. Document test fixture patterns
2. Add comments explaining mock setup where complex
3. Update test documentation if needed

## Dependencies

- None (isolated test infrastructure work)

## Phase

- **Phase**: Maintenance / Technical Debt
- **Sprint**: SP-005
- **Related Tasks**: SP-005-007 (identified these issues during review)

## Architecture Notes

- No production code changes required
- Test-only modifications
- Maintains existing test patterns where possible
- Improves test isolation and reliability

## Success Metrics

- ✅ 137/137 dialect tests passing (100%)
- ✅ No actual database connections required for unit tests
- ✅ Improved test isolation and mocking patterns
- ✅ Clearer test documentation

## Notes

- These are pre-existing issues, not regressions
- Task can be completed in parallel with other work
- Low priority but improves overall project health
- Consider adding CI/CD checks to prevent similar issues

## References

- **Review Document**: `project-docs/plans/reviews/SP-005-007-review.md`
- **Test Files**:
  - `tests/unit/dialects/test_duckdb_dialect.py`
  - `tests/unit/dialects/test_factory.py`
  - `tests/unit/dialects/test_postgresql_dialect.py`

## Completion Summary

**Completed**: 2025-09-30
**Total Time**: ~1.5 hours (under 4h estimate)
**Result**: All 137 dialect tests passing (100%)

### Changes Made

#### 1. Fixed DuckDB Mock Test (`test_duckdb_dialect.py`)
- **Issue**: `mock_connection` fixture returned `None` for `execute()`, causing AttributeError when test tried to chain `.fetchall()`
- **Solution**: Properly configured mock chain:
  - Created `mock_result` with `fetchall()` method
  - Set `mock_conn.execute.return_value = mock_result`
  - Updated test assertion to check last call instead of using `assert_called_once_with()` (accounts for dialect initialization call)

#### 2. Fixed PostgreSQL Factory Tests (`test_factory.py`)
- **Issue**: Tests attempted to create real PostgreSQL connections, failing with authentication errors
- **Root Cause**: Mocking at wrong level - patching `PostgreSQLDialect` class didn't prevent `psycopg2.connect()` call in `__init__`
- **Solution**: Mock `psycopg2.connect()` directly in each test:
  - Changed from `@patch('fhir4ds.dialects.factory.PostgreSQLDialect')`
  - To `@patch('fhir4ds.dialects.postgresql.psycopg2')`
  - Updated assertions to check dialect properties instead of mock instances

**Fixed Tests** (7 total):
1. `test_create_dialect_postgresql_explicit` - Now mocks psycopg2.connect
2. `test_create_dialect_auto_detect_postgresql` - Now mocks psycopg2.connect
3. `test_create_dialect_auto_detect_duckdb` - Now mocks duckdb.connect correctly
4. `test_create_dialect_with_creation_failure` - Now mocks at duckdb level
5. `test_create_from_config` - Now mocks duckdb.connect, removed invalid extra_param
6. `test_case_insensitive_database_type` - Now mocks duckdb.connect
7. `test_postgresql_alias_handling` - Now mocks psycopg2.connect

### Test Results
```
============================= 137 passed in 0.64s ==============================
```

### Key Patterns Applied
1. **Proper Mock Chaining**: Mock return values at each level of call chain
2. **Mock at Correct Level**: Mock external dependencies (psycopg2, duckdb) rather than internal classes
3. **Test Isolation**: Unit tests now properly isolated from database dependencies
4. **No Production Code Changes**: All fixes were test-only, maintaining principle

### Architecture Compliance
- ✅ No business logic in tests
- ✅ Proper test isolation maintained
- ✅ Follows FHIR4DS testing standards
- ✅ Both DuckDB and PostgreSQL test coverage maintained
