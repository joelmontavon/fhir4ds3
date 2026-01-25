# SP-101-003: Failure Categorization Report

**Generated**: 2026-01-25

**Total Failures**: 470

## Top 3 Patterns

### Pattern 1: result_logic: none_result

- **Test Count**: 185
- **Error Types**: ConversionException, parse, ParserException, translator_unsupported, semantic, execution, InvalidInputException, ValueError

**Root Cause**:
- Description: Conversion Error: time field value out of range: "14", expected format is ([YYYY-MM-DD ]HH:MM:SS[.MS])

**Example Tests**:
- testLiteralTimeHour
- testDateNotEqualTimeSecond
- testDateNotEqualTimeMinute
- testStringYearConvertsToDate
- testStringMonthConvertsToDate

... and 180 more

**Recommended Fix Approach**:
- To be determined

### Pattern 2: result_logic: single_value_instead_of_empty

- **Test Count**: 92
