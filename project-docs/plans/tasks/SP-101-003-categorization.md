# SP-101-003: Failure Categorization Report

**Generated**: 2026-01-25
**Status**: Phase 1 Complete - Moving to Phase 2
**Total Tests**: 934
**Total Failures**: 470
**Current Compliance**: 50.1%

---

## Executive Summary

Phase 1 categorization is complete. Analysis of 470 failing tests revealed **16 distinct patterns**. The top 3 patterns account for **342 tests (73% of all failures)**.

**Key Finding**: Most failures are result logic mismatches (wrong results) rather than crashes or syntax errors, indicating the SQL translator is generating syntactically valid but semantically incorrect SQL.

---

## Top 3 Patterns (Target for Phase 2)

### Pattern 1: Function Not Yet Implemented (185 tests)

**Error Category**: `result_logic: none_result`
**Impact**: 185 tests (39% of failures)
**Primary Error Types**:
- `parse` (126 tests) - Unknown functions
- `ConversionException` (26 tests) - Time/date conversion issues
- `ParserException` (12 tests) - Syntax errors in translation
- `translator_unsupported` (10 tests) - Explicit translator limitations

**Root Cause**:
Multiple sub-categories of unimplemented functionality:

1. **String Functions** (~80 tests): Functions not yet implemented:
   - `indexOf()`, `substring()`, `replace()`, `length()`, `split()`
   - `matches()`, `replaceMatches()`, `combine()`, `distinct()`
   - `toChars()`, `encodeBase64()`, `decodeBase64()`, `escapeHtml()`, etc.

2. **Time Literals** (~26 tests): Time literal parsing/conversion issues:
   - `@T14` (hour-only time) fails with "time field value out of range"
   - TIME to TIMESTAMP cast not implemented

3. **Collection Functions** (~40 tests):
   - `subsetOf()`, `supersetOf()`, `allTrue()`
   - `sort()`, `repeat()`, `trace()`, `indexer`

4. **Boolean Logic** (~20 tests):
   - `xor`, `implies` operators
   - Boolean collection operations

5. **Math Functions** (~10 tests):
   - `exp()`, `power()`, `truncate()`

6. **Other** (~9 tests):
   - `conformsTo()`, `type()`, `ofType()`, `as()`
   - Boundary tests (`lowBoundary()`, `highBoundary()`)

**Example Tests**:
```
testLiteralTimeHour:         @T14.is(Time)
testDateNotEqualTimeSecond:  Patient.birthDate != @T12:14:15
testIndexOf1:                'LogicalModel-Person'.indexOf('-')
testSubstring1:              '12345'.substring(2) = '345'
testAllTrue1:                (true | false).allTrue()
testXor1:                    true xor false
testExp1:                    2.exp()
```

**Recommended Fix Approach**:

**Priority 1 (Quick wins - ~80 tests)**:
- Implement missing string functions: `indexOf()`, `substring()`, `replace()`, `length()`, `split()`
- These are well-defined FHIRPath functions with clear semantics
- Use DuckDB/PostgreSQL built-in string functions

**Priority 2 (Medium effort - ~40 tests)**:
- Implement collection functions: `subsetOf()`, `supersetOf()`, `allTrue()`, `distinct()`
- Fix time literal parsing to support hour-only format `@T14`

**Priority 3 (Lower priority - ~65 tests)**:
- Boolean operators: `xor`, `implies`
- Math functions: `exp()`, `power()`, `truncate()`
- Encoding functions: `encodeBase64()`, `decodeBase64()`, etc.
- Type functions: `conformsTo()`, boundary tests

**Estimated Effort**: 20-30 hours to implement Priority 1 and 2 (targeting ~120 tests)

---

### Pattern 2: Type Conversion Returns Wrong Result (92 tests)

**Error Category**: `result_logic: single_value_instead_of_empty`
**Impact**: 92 tests (20% of failures)
**Primary Error Types**: `null` (test returns result but expects empty)

**Root Cause**:
Functions return a value when they should return empty (no match). This indicates incorrect type checking or conversion logic.

**Sub-categories**:

1. **Type Conversion Functions** (~40 tests):
   - `convertsToDateTime()`, `convertsToTime()`, `convertsToQuantity()`
   - `convertsToString()`, `convertsToInteger()`
   - Functions return `true` when should return `{}` (empty)

2. **`is()` Type Checks** (~15 tests):
   - Literals like `@2015T.is(DateTime)` return wrong result
   - Partial date/time literals not handled correctly

3. **Quantity Literals** (~15 tests):
   - `1 'cm'` syntax not parsed/converted correctly
   - UCUM unit handling issues

4. **Collection Operations** (~20 tests):
   - `select()`, `repeat()`, `take()`, `skip()`, `indexer`
   - `exists()`, `empty()` returning wrong boolean

5. **String Operations** (~10 tests):
   - `startsWith()`, `endsWith()`, `contains()`
   - Index edge cases

**Example Tests**:
```
testLiteralDateTimeYear:          @2015T.is(DateTime)  -> returns true, should be {}
testStringYearConvertsToDateTime: '2015'.convertsToDateTime() -> returns true, should be {}
testLiteralQuantityDecimal:       2.0 'cm' -> wrong result
testExists2:                      {}.exists() -> returns false, should be {}
testSelect1:                      Patient.name.select(given | family)
```

**Recommended Fix Approach**:

**Root Issue**: Type conversion functions don't validate input format. They return `true` for any input that doesn't crash, rather than checking if the input is a valid representation of the target type.

**Fix Strategy**:
1. Add proper format validation to each `convertsTo*()` function
2. For `is()` checks: Ensure literal type inference handles partial dates/times
3. For quantity literals: Parse UCUM units correctly in literal expression visitor
4. Review collection operation edge cases (empty input, single element)

**Estimated Effort**: 8-12 hours (high impact, well-defined fixes)

---

### Pattern 3: SQL Column Not Found in FROM Clause (65 tests)

**Error Category**: `binder: column_not_found_in_from`
**Impact**: 65 tests (14% of failures)
**Primary Error Types**: `BinderException`

**Root Cause**:
CTE (Common Table Expression) chains generate SQL with incorrect column references. Inner CTEs reference columns from outer CTEs that aren't in scope.

**Technical Details**:
The CTE builder creates nested CTEs but doesn't properly propagate column aliases through the chain. When a later CTE tries to reference a column from an earlier CTE, the column isn't visible in the FROM clause.

**Affected Operations**:
1. **Chained Path Navigation** (~30 tests):
   ```
   Patient.name.skip(1).given
   Patient.name.take(2).given
   Patient.name.first().given
   ```

2. **`$this` in Predicates** (~10 tests):
   ```
   Patient.name.given.where(substring($this.length()-3) = 'out')
   ```

3. **String Functions on Paths** (~25 tests):
   ```
   Patient.name.given.indexOf('test')
   Patient.name.given.substring(0, 2)
   Patient.name.given.length()
   Patient.birthDate.replace('1974', '1975')
   ```

**Example Tests**:
```
testDollarThis1:        Patient.name.given.where(substring($this.length()-3) = 'out')
testDollarOrderAllowed: Patient.name.skip(1).given
testSubstring1:         '12345'.substring(2) = '345'  -- even string literals fail!
testIndexOf1:           'LogicalModel-Person'.indexOf('-')
testReplace1:           '123456'.replace('234', 'X')
```

**Why Even String Literals Fail**:
The string literal handling creates a CTE with the literal as a column, but then tries to reference that column in a function call outside the CTE's scope.

**Recommended Fix Approach**:

**Root Issue**: CTE scoping - columns defined in inner CTEs aren't visible to outer CTEs or the final SELECT.

**Fix Strategy**:
1. **Immediate**: Ensure each CTE outputs all columns that downstream CTEs need
2. **Structural**: Review CTE chaining logic in `fhirpath/sql/cte.py`
3. **Column Propagation**: When building CTE chains, track which columns each CTE produces and which the next CTE consumes

**File Locations**:
- `/mnt/d/fhir4ds3/fhir4ds/fhirpath/sql/cte.py` - CTEBuilder, CTEAssembler
- `/mnt/d/fhir4ds3/fhir4ds/fhirpath/sql/translator.py` - ASTToSQLTranslator

**Estimated Effort**: 10-15 hours (complex, requires understanding CTE architecture)

---

## Remaining Patterns (Deferred to Future Sprints)

| Pattern | Count | Priority | Notes |
|---------|-------|----------|-------|
| binder: other | 26 | P3 | Type casting issues, date arithmetic |
| semantic_validation: should_fail_but_passes | 25 | P2 | Invalid expressions accepted |
| result_logic: got_0_values | 23 | P2 | Functions return empty when should return value |
| empty_result: None_instead_of_empty | 18 | P3 | Polymorphic type checks |
| empty_result: parse_instead_of_empty | 7 | P3 | Boundary functions not implemented |
| conversion: other | 6 | P3 | DateTime format conversion |
| invalid_input: malformed_json | 5 | P3 | Timezone handling in date literals |
| result_logic: got_3_values | 4 | P3 | Collection operations returning wrong count |
| result_logic: got_9_values | 4 | P3 | Self-equality on paths |
| result_logic: got_2_values | 3 | P3 | Tail/skip/take count issues |
| result_logic: got_5_values | 2 | P3 | Nested collection operations |
| conversion: type_conversion_failed | 2 | P3 | Empty string to type conversion |
| binder: no_function_matches | 2 | P2 | Function signature issues |
| function_signature: argument_count_mismatch | 1 | P3 | Edge case in power() |

---

## Phase 2 Implementation Plan

### Target
Fix top 3 patterns (342 tests) with estimated 60+ tests passing.

### Priority Order

1. **Pattern 2: Type Conversion Returns Wrong Result** (92 tests)
   - **Quickest wins** (8-12 hours)
   - Well-defined fixes in conversion logic
   - High impact on compliance

2. **Pattern 3: SQL Column Not Found in FROM Clause** (65 tests)
   - **Medium complexity** (10-15 hours)
   - Architectural fix in CTE builder
   - Enables many other functions to work

3. **Pattern 1 Priority 1**: String Functions (80 tests)
   - **High value** (10-15 hours)
   - Standard FHIRPath functions
   - Clear implementation path

### Success Criteria
- At least 60 tests from this batch now passing
- No regression on existing passing tests
- Remaining patterns documented with estimates

### Risk Mitigation
- If Pattern 3 proves too complex, focus on Patterns 1 and 2
- Time checkpoint: Stop after 30 hours and document remaining work

---

## Appendix: Full Test Lists by Pattern

See `SP-101-003-categorization.json` for complete test lists for each pattern.
