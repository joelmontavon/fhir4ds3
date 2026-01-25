# SP-101-003 Implementation TODOs

## Phase 1: Categorization - COMPLETE
- [x] Run test suite with detailed logging
- [x] Analyze ~470 failures by error type
- [x] Identify top 3 patterns
- [x] Document findings in SP-101-003-categorization.md

## Phase 2: Implementation (Target: 60+ tests passing)

### Pattern 2: Type Conversion Returns Wrong Result (92 tests) - IN PROGRESS

#### Sub-pattern: String convertsToDateTime validation - COMPLETE
- [x] Update `_evaluate_literal_converts_to()` to accept partial date formats
- [x] Update `_build_converts_to_datetime_expression()` SQL generation with REGEXP_MATCHES
- [x] Test with testStringYearConvertsToDateTime, testStringMonthConvertsToDateTime, etc.
- **Result**: 3 tests passing (year, month, day)

#### Sub-pattern: String convertsToTime validation - COMPLETE
- [x] Update `_evaluate_literal_converts_to()` to accept hour-only format
- [x] Update `_build_converts_to_time_expression()` SQL generation
- [x] Fix regex escape sequence (use single backslash for literal dot)
- **Result**: 4 tests passing (hour, minute, second, millisecond)

#### Sub-pattern: Partial DateTime Literals (Requires grammar update) - DEFERRED
- [x] Fix temporal parser to accept partial DateTime literals: `@2015T`, `@2015-02T`, `@2015-02-04T`
- [ ] Update DATETIME_PATTERN regex in FHIRPath.g4 (requires ANTLR regeneration)
- [ ] Regenerate ANTLR lexer/parser (requires Java)
- **Status**: Temporal parser fixed, but ANTLR grammar requires Java to regenerate

#### Sub-pattern: Other convertsTo* issues - PENDING
- [ ] Fix convertsToDate for partial date formats (similar to DateTime)
- [ ] Fix convertsToDateTime for timezone formats (Z, +/-HH:MM)
- [ ] Fix convertsToQuantity for UCUM unit parsing
- [ ] Review collection operation edge cases (exists, empty on collections)

### Pattern 3: SQL Column Not Found in FROM Clause (65 tests) - PENDING
- [ ] Analyze CTE builder chaining logic
- [ ] Fix column propagation through CTE chain
- [ ] Test with testDollarThis1, testDollarOrderAllowed, etc.

### Pattern 1 Priority 1: String Functions (~80 tests) - PENDING
- [ ] Implement indexOf() function
- [ ] Implement substring() function
- [ ] Implement replace() function
- [ ] Implement length() function
- [ ] Implement split() function

## Progress Summary

**Tests Fixed**: 7 convertsTo* tests (DateTime and Time)

**Remaining Work**:
- Pattern 2: ~85 more tests to fix (Date, DateTime with timezone, Quantity)
- Pattern 3: 65 tests (requires CTE architecture fix)
- Pattern 1: 80 tests (requires string function implementation)

**Key Learnings**:
1. DuckDB REGEXP_MATCHES uses SQL regular expressions, not Python regex
2. Escape sequences: Single backslash in Python string = literal character in SQL regex
3. Temporal parser partial DateTime support requires ANTLR grammar update
4. convertsTo* functions should use regex pattern matching, not type casting

## Verification
- [ ] Run full test suite after fixes
- [ ] Ensure no regression on existing passing tests
- [ ] Document remaining patterns

## Commit
- [ ] Create commit: "feat(SP-101-003): convertsTo DateTime/Time pattern fixes"
