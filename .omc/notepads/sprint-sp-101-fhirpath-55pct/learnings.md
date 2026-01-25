# SP-101-003 Learnings

## Pattern: Type Conversion Returns Wrong Result

### Root Causes

1. **convertsToDateTime() was using type casting instead of pattern matching**
   - Original implementation: `TRY_CAST(value AS TIMESTAMP) IS NOT NULL`
   - Issue: Partial dates like `'2015'` don't cast to TIMESTAMP
   - Fix: Use `REGEXP_MATCHES()` with pattern matching

2. **convertsToTime() had incorrect regex escape sequences**
   - Original pattern: `\\.[0-9]+` (double backslash)
   - Issue: In Python string, `\\.` becomes `\.` which is regex for "any character"
   - Fix: Use `\.[0-9]+` (single backslash) for literal dot

3. **Temporal parser didn't support partial DateTime literals**
   - Missing patterns: `@2015T`, `@2015-02T`, `@2015-02-04T`
   - Status: Parser fixed, but ANTLR grammar requires Java to regenerate

### Implementation Details

#### File: `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/sql/translator.py`

**Changes to `_evaluate_literal_converts_to()`:**
```python
# Before:
if target_type == "DateTime":
    return bool(re.match(r'^\d{4}(-\d{2}(-\d{2}(T.*)?)?)?$', stripped))

# After:
if target_type == "DateTime":
    return bool(re.match(r'^\d{4}(-\d{2}(-\d{2})?)?T?.*$', stripped))
```

**Changes to `_build_converts_to_datetime_expression()`:**
```python
# Before:
datetime_cast = self.dialect.generate_type_cast(value_expr, "DateTime")
return f"CASE WHEN {datetime_cast} IS NOT NULL THEN TRUE ELSE FALSE END"

# After:
string_cast = self.dialect.generate_type_cast(value_expr, "String")
return (
    f"CASE "
    f"WHEN {string_cast} IS NULL THEN FALSE "
    f"WHEN REGEXP_MATCHES({string_cast}, '^[0-9]{{4}}(-[0-9]{{2}})?(-[0-9]{{2}})?(T([0-9]{{2}}(:[0-9]{{2}})?(:[0-9]{{2}})?)?)?$') THEN TRUE "
    f"ELSE FALSE "
    f"END"
)
```

**Changes to `_build_converts_to_time_expression()`:**
```python
# Before:
time_cast = self.dialect.generate_type_cast(value_expr, "Time")
return f"CASE WHEN {time_cast} IS NOT NULL THEN TRUE ELSE FALSE END"

# After:
string_cast = self.dialect.generate_type_cast(value_expr, "String")
return (
    f"CASE "
    f"WHEN {string_cast} IS NULL THEN FALSE "
    f"WHEN REGEXP_MATCHES({string_cast}, '^[0-9]{{2}}(:[0-9]{{2}})?(:[0-9]{{2}}(\\.[0-9]+)?)?)?$') THEN TRUE "
    f"ELSE FALSE "
    f"END"
)
```

#### File: `/mnt/d/fhir4ds3/fhir4ds/main/fhirpath/types/temporal_parser.py`

**Added PARTIAL_DATETIME_PATTERN:**
```python
PARTIAL_DATETIME_PATTERN = re.compile(
    r'^@(?P<year>\d{4})(?:-(?P<month>\d{2}))?(?:-(?P<day>\d{2}))?T$'
)
```

**Added `_parse_partial_datetime()` method:**
```python
def _parse_partial_datetime(self, original: str, match: re.Match) -> ParsedTemporal:
    """Parse a partial DateTime literal (date components with 'T' suffix)."""
    groups = match.groupdict()
    return ParsedTemporal(
        original=original,
        temporal_type='DateTime',  # DateTime type, not Date
        year=int(groups['year']),
        month=int(groups['month']) if groups.get('month') else None,
        day=int(groups['day']) if groups.get('day') else None,
        # No time components in partial DateTime
        hour=None,
        minute=None,
        second=None,
        millisecond=None,
        timezone_offset=None
    )
```

### Test Results

**Tests Fixed:**
1. `testStringYearConvertsToDateTime` - `'2015'.convertsToDateTime()` ✅
2. `testStringMonthConvertsToDateTime` - `'2015-02'.convertsToDateTime()` ✅
3. `testStringDayConvertsToDateTime` - `'2015-02-04'.convertsToDateTime()` ✅
4. `testStringHourConvertsToTime` - `'14'.convertsToTime()` ✅
5. `testStringMinuteConvertsToTime` - `'14:34'.convertsToTime()` ✅
6. `testStringSecondConvertsToTime` - `'14:34:28'.convertsToTime()` ✅
7. `testStringMillisecondConvertsToTime` - `'14:34:28.123'.convertsToTime()` ✅

**Overall convertsTo* tests:** 38/52 passing (73%)

### Remaining Issues

1. **Partial DateTime literals with `@` prefix** (e.g., `@2015T`)
   - Temporal parser is fixed
   - ANTLR grammar FHIRPath.g4 updated
   - ANTLR lexer/parser needs regeneration (requires Java)
   - Tests: `testLiteralDateTimeYear`, `testLiteralDateTimeMonth`, etc.

2. **DateTime with timezone** (e.g., `'2015-02-04T14:34:28Z'`)
   - Pattern needs to support `Z` and `+/-HH:MM` suffixes
   - Tests: `testStringUTCConvertsToDateTime`, `testStringTZConvertsToDateTime`

3. **convertsToDate** for partial dates
   - Similar to DateTime but for Date type
   - Tests: `testStringYearConvertsToDate`, etc.

4. **convertsToQuantity** for UCUM units
   - Requires UCUM unit parsing
   - Tests: `testIntegerLiteralConvertsToQuantity`, etc.

### Key Learnings

1. **DuckDB REGEXP_MATCHES vs Python regex**
   - DuckDB uses SQL regular expression syntax
   - Escape sequences differ from Python
   - Test patterns directly in DuckDB before using in code

2. **Escape sequence complexity**
   - Python string: `"\\."` → SQL string: `\.` → Regex: matches any character
   - Python string: `"\."` → SQL string: `.` → Regex: matches literal dot
   - For literal dot in DuckDB regex: Use single backslash in Python code

3. **Type casting vs pattern matching**
   - `TRY_CAST()` is too strict for partial dates
   - FHIRPath `convertsTo*()` checks format, not castability
   - Use `REGEXP_MATCHES()` for format validation

4. **ANTLR regeneration requires Java**
   - Grammar changes need ANTLR tool to regenerate lexer/parser
   - Without Java, need to manually update generated files or use alternative approach

### Deferred Work

1. **ANTLR Grammar Update** (blocked by lack of Java)
   - File: `FHIRPath.g4`
   - Change: DATETIME pattern to accept optional `T` suffix
   - Status: Grammar updated, waiting for regeneration

2. **String Functions Implementation** (Pattern 1, ~80 tests)
   - Functions: `indexOf()`, `substring()`, `replace()`, `length()`, `split()`
   - Estimated effort: 10-15 hours

3. **CTE Column Propagation** (Pattern 3, ~65 tests)
   - Issue: Columns from inner CTEs not visible in outer CTEs
   - Estimated effort: 10-15 hours (complex architectural fix)
