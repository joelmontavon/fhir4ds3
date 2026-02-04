"""
DuckDB dialect implementation for FHIR4DS.

This module provides DuckDB-specific SQL syntax while maintaining the thin
dialect architecture principle: business logic in FHIRPath evaluator,
only syntax differences in dialects.
"""

import logging
from typing import Any, List, Optional

from .base import DatabaseDialect

# Optional import for DuckDB
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DuckDBDialect(DatabaseDialect):
    """
    DuckDB implementation of the database dialect.

    Provides DuckDB-specific SQL generation with emphasis on JSON operations
    and analytical performance for population-scale healthcare data.
    """

    def __init__(self, connection: Optional[Any] = None, database: str = ":memory:"):
        """Initialize DuckDB dialect."""
        super().__init__()

        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB is required but not installed. Install with: pip install duckdb")

        # DuckDB-specific settings
        self.name = "DUCKDB"
        self.supports_jsonb = False
        self.supports_json_functions = True
        self.json_type = "JSON"
        self.cast_syntax = "::"
        self.quote_char = '"'

        try:
            self.connection = connection or duckdb.connect(database)
            # Enable JSON extension
            self.connection.execute("INSTALL json; LOAD json;")
            logger.info(f"Initialized DuckDB dialect with database: {database}")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB dialect: {e}")
            raise

    def get_connection(self) -> Any:
        """Get the underlying DuckDB connection."""
        return self.connection

    def execute_query(self, sql: str) -> Any:
        """Execute a query and return raw results."""
        try:
            result = self.connection.execute(sql)
            return result.fetchall()
        except Exception as e:
            logger.error(f"DuckDB query execution failed: {e}\nSQL: {sql}")
            raise

    # JSON extraction methods

    def extract_json_field(self, column: str, path: str) -> str:
        """Extract JSON field as text using DuckDB's json_extract_string.

        Returns a JSON string value that may be a scalar, object, or array.
        The caller is responsible for casting to VARCHAR if needed for comparisons.
        """
        return f"json_extract_string({column}, '{path}')"

    def extract_json_object(self, column: str, path: str) -> str:
        """Extract JSON object using DuckDB's json_extract."""
        return f"json_extract({column}, '{path}')"

    def check_json_exists(self, column: str, path: str) -> str:
        """Check if JSON path exists in DuckDB."""
        return f"({self.extract_json_object(column, path)} IS NOT NULL)"

    def extract_primitive_value(self, column: str, path: str) -> str:
        """Extract FHIR primitive value handling both simple and complex representations.

        FHIR primitives can be: {"field": "value"} or {"field": {"value": "...", "extension": [...]}}
        This method uses COALESCE to try complex representation first, then simple.

        Note: Returns a JSON string. Cast to VARCHAR for comparisons with string literals.
        """
        # Try to extract from complex representation (path.value), fall back to simple (path)
        return f"COALESCE(json_extract_string({column}, '{path}.value'), json_extract_string({column}, '{path}'))"

    # Type-aware JSON extraction for SQL-on-FHIR ViewDefinitions

    def extract_json_string(self, column: str, path: str) -> str:
        """Extract JSON field as string using DuckDB's json_extract_string.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.id', '$.name[0].family')

        Returns:
            DuckDB SQL expression: json_extract_string(column, 'path')

        Example:
            >>> dialect.extract_json_string('resource', '$.id')
            "json_extract_string(resource, '$.id')"

        Note:
            Returns a JSON string that should be cast to VARCHAR for comparisons.
            Use CAST({expr} AS VARCHAR) when comparing with string literals.
        """
        return f"json_extract_string({column}, '{path}')"

    def extract_json_integer(self, column: str, path: str) -> str:
        """Extract JSON field as integer using DuckDB's json_extract with INTEGER cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.age', '$.value')

        Returns:
            DuckDB SQL expression: json_extract(column, 'path')::INTEGER

        Example:
            >>> dialect.extract_json_integer('resource', '$.age')
            "json_extract(resource, '$.age')::INTEGER"
        """
        return f"json_extract({column}, '{path}')::INTEGER"

    def extract_json_decimal(self, column: str, path: str) -> str:
        """Extract JSON field as decimal using DuckDB's json_extract with DECIMAL cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.value', '$.price')

        Returns:
            DuckDB SQL expression: json_extract(column, 'path')::DECIMAL

        Example:
            >>> dialect.extract_json_decimal('resource', '$.value')
            "json_extract(resource, '$.value')::DECIMAL"
        """
        return f"json_extract({column}, '{path}')::DECIMAL"

    def extract_json_boolean(self, column: str, path: str) -> str:
        """Extract JSON field as boolean using DuckDB's json_extract with BOOLEAN cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.active', '$.deceased')

        Returns:
            DuckDB SQL expression: json_extract(column, 'path')::BOOLEAN

        Example:
            >>> dialect.extract_json_boolean('resource', '$.active')
            "json_extract(resource, '$.active')::BOOLEAN"
        """
        return f"json_extract({column}, '{path}')::BOOLEAN"

    def get_json_type(self, column: str) -> str:
        """Get JSON value type using DuckDB's json_type."""
        return f"json_type({column})"

    def get_json_array_length(self, column: str, path: str = None) -> str:
        """Get JSON array length using DuckDB's json_array_length."""
        if path:
            return f"json_array_length(CAST({self.extract_json_object(column, path)} AS JSON))"
        else:
            return f"json_array_length(CAST({column} AS JSON))"

    # Array and collection operations

    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        """Generate SQL for unnesting JSON array elements using DuckDB's UNNEST.

        Args:
            column: Source column or table name containing JSON
            path: JSON path to the array (e.g., '$.name', '$.address')
            alias: Alias name for the unnested array elements

        Returns:
            DuckDB-specific SQL fragment for array unnesting

        Example:
            >>> dialect.unnest_json_array('resource', '$.name', 'name_item')
            'UNNEST(json_extract(resource, '$.name')) AS name_item(value)'
        """
        return f"UNNEST(json_extract({column}, '{path}')) AS {alias}(value)"

    def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:
        """Generate DuckDB-specific LATERAL UNNEST clause.

        Args:
            source_table: Table or CTE providing the array column. Retained for interface consistency.
            array_column: SQL expression that evaluates to the array being flattened.
            alias: Alias for the unnested elements.

        Returns:
            DuckDB LATERAL UNNEST SQL fragment.

        Example:
            >>> dialect.generate_lateral_unnest(
            ...     source_table="patient_resources",
            ...     array_column="json_extract(resource, '$.name')",
            ...     alias="name_item"
            ... )
            'LATERAL UNNEST(json_extract(resource, '$.name')) AS name_item'
        """
        return f"LATERAL UNNEST({array_column}) AS {alias}"

    def iterate_json_array(self, column: str, path: str) -> str:
        """Iterate over JSON array elements using DuckDB's json_each."""
        return f"json_each({column}, '{path}')"

    def aggregate_to_json_array(self, expression: str) -> str:
        """Aggregate values into JSON array using DuckDB lists (order-preserving)."""
        return f"CAST(to_json(list({expression})) AS JSON)"

    def prepare_unnest_source(self, array_expr: str) -> str:
        """Ensure UNNEST receives a DuckDB list when working with JSON arrays."""
        expr = array_expr.strip()
        if "[*]" in expr or expr.upper().startswith("UNNEST"):
            return array_expr
        wrapped = expr if expr.startswith("(") and expr.endswith(")") else f"({expr})"
        return f"json_extract({wrapped}, '$[*]')"

    def create_json_array(self, *args) -> str:
        """Create JSON array using DuckDB's json_array."""
        if args:
            return f"json_array({', '.join(str(arg) for arg in args)})"
        return "json_array()"

    def create_json_object(self, *args) -> str:
        """Create JSON object using DuckDB's json_object."""
        if args:
            return f"json_object({', '.join(str(arg) for arg in args)})"
        return "json_object()"

    def json_array_contains(self, array_expr: str, scalar_expr: str) -> str:
        """Check whether a JSON array contains the supplied scalar value."""
        normalized = f"COALESCE({array_expr}, '[]')"
        return (
            "EXISTS ("
            f"SELECT 1 FROM json_each({normalized}) AS elem "
            f"WHERE json_extract_string(elem.value, '$') = {scalar_expr}"
            ")"
        )

    # String operations

    def string_concat(self, left: str, right: str) -> str:
        """Concatenate strings using DuckDB's || operator."""
        return f"({left} || {right})"

    def substring(self, expression: str, start: str, length: str) -> str:
        """Extract substring using DuckDB's SUBSTRING function."""
        return f"SUBSTRING({expression}, ({start}) + 1, {length})"

    def split_string(self, expression: str, delimiter: str) -> str:
        """Split string into array using DuckDB's string_split."""
        return f"string_split(CAST({expression} AS VARCHAR), {delimiter})"

    def generate_string_join(self, collection_expr: str, delimiter_expr: str, is_json_collection: bool) -> str:
        """Generate SQL for joining string collections in DuckDB."""
        source_expr = (
            f"from_json({collection_expr}, '[\"VARCHAR\"]')"
            if is_json_collection
            else collection_expr
        )

        return (
            "CASE "
            f"WHEN {collection_expr} IS NULL THEN NULL "
            f"ELSE array_to_string({source_expr}, {delimiter_expr}) "
            "END"
        )

    # Type conversion operations

    def try_cast(self, expression: str, target_type: str) -> str:
        """Safe type conversion using DuckDB's TRY_CAST."""
        return f"TRY_CAST({expression} AS {target_type.upper()})"

    def cast_to_timestamp(self, expression: str) -> str:
        """Cast to timestamp using DuckDB."""
        return f"CAST({expression} AS TIMESTAMP)"

    def cast_to_time(self, expression: str) -> str:
        """Cast to time using DuckDB."""
        return f"CAST({expression} AS TIME)"

    # Mathematical functions

    def cast_to_double(self, expression: str) -> str:
        """Cast expression to double precision for DuckDB."""
        return f"CAST({expression} AS DOUBLE)"

    def is_finite(self, expression: str) -> str:
        """Check if numeric expression is finite in DuckDB."""
        return f"isfinite({expression})"

    def generate_math_function(self, function_name: str, *args: str) -> str:
        """Generate mathematical function SQL for DuckDB."""
        func_map = {
            'sqrt': 'sqrt',
            'ln': 'ln',
            'log': 'log10',
            'exp': 'exp',
            'power': 'pow',
            'ceiling': 'ceil',
            'floor': 'floor',
            'round': 'round',
            'abs': 'abs',
            'truncate': 'trunc'
        }
        sql_func = func_map.get(function_name.lower(), function_name.lower())
        return f"{sql_func}({', '.join(args)})"

    def generate_power_operation(self, base_expr: str, exponent_expr: str) -> str:
        """Generate power operation using DuckDB's pow function."""
        return f"pow({base_expr}, {exponent_expr})"

    # Boundary functions

    def generate_decimal_division(self, numerator: str, denominator: str) -> str:
        """Generate decimal division expression."""
        return f"(({numerator}) / ({denominator}))"

    def generate_integer_division(self, numerator: str, denominator: str) -> str:
        """Generate integer division that truncates toward zero."""
        division_expr = f"(({numerator}) / ({denominator}))"
        floor_expr = self.generate_math_function("floor", division_expr)
        ceil_expr = self.generate_math_function("ceiling", division_expr)
        return (
            f"(CASE "
            f"WHEN {division_expr} >= 0 THEN CAST({floor_expr} AS BIGINT) "
            f"ELSE CAST({ceil_expr} AS BIGINT) "
            "END)"
        )

    def generate_modulo(self, left: str, right: str) -> str:
        """Generate modulo expression."""
        return f"(({left}) % ({right}))"

    def generate_decimal_boundary(
        self,
        base_expr: str,
        target_precision: Optional[int],
        boundary_type: str
    ) -> str:
        """Generate SQL for decimal boundary calculation.

        Implements the uncertainty interval algorithm for decimal values:
        1. Detect input precision (count decimal places)
        2. Calculate uncertainty (0.5 × 10^-input_precision)
        3. Add (high) or subtract (low) uncertainty
        4. Round to target precision

        Args:
            base_expr: SQL expression for the input decimal value
            target_precision: Target precision (None = input precision + 5)
            boundary_type: 'high' or 'low'

        Returns:
            DuckDB-specific SQL for boundary calculation
        """
        # Input precision detection: count decimal places
        # Uses REGEXP_REPLACE to extract fractional part, then LENGTH
        precision_sql = f"""
            CASE
                WHEN {base_expr}::VARCHAR LIKE '%.%'
                THEN LENGTH(REGEXP_REPLACE({base_expr}::VARCHAR, '^[^.]*\\.', ''))
                ELSE 0
            END
        """

        # Target precision: explicit param or input_precision + 5 (max 31)
        if target_precision is not None:
            target_prec_sql = str(target_precision)
        else:
            target_prec_sql = f"CAST(LEAST(({precision_sql}) + 5, 31) AS INTEGER)"

        # Uncertainty calculation: 0.5 * 10^(-input_precision)
        uncertainty_sql = f"0.5 * pow(10, -({precision_sql}))"

        # Boundary calculation: add or subtract uncertainty
        if boundary_type == "high":
            boundary_sql = f"({base_expr}) + ({uncertainty_sql})"
        else:  # low
            boundary_sql = f"({base_expr}) - ({uncertainty_sql})"

        # Round to target precision
        result_sql = f"ROUND({boundary_sql}, {target_prec_sql})"

        return result_sql

    def generate_quantity_boundary(
        self,
        base_expr: str,
        target_precision: Optional[int],
        boundary_type: str
    ) -> str:
        """Generate SQL for quantity boundary calculation.

        For quantity values, we extract the numeric component, apply decimal
        boundary logic, then reconstruct with the unit.

        Args:
            base_expr: SQL expression for the input quantity value
            target_precision: Target precision (None = input precision + 5)
            boundary_type: 'high' or 'low'

        Returns:
            DuckDB-specific SQL for quantity boundary calculation
        """
        # Extract numeric value from quantity (e.g., "5.5 'mg'" -> 5.5)
        value_sql = f"CAST(SPLIT_PART({base_expr}, ' ', 1) AS DECIMAL)"

        # Extract unit from quantity (e.g., "5.5 'mg'" -> 'mg')
        unit_sql = f"TRIM(BOTH '''' FROM SPLIT_PART({base_expr}, ' ', 2))"

        # Apply decimal boundary to the value
        boundary_value_sql = self.generate_decimal_boundary(
            value_sql,
            target_precision,
            boundary_type
        )

        # Reconstruct quantity with bounded value and original unit
        result_sql = f"CONCAT({boundary_value_sql}, ' ''', {unit_sql}, '''')"

        return result_sql

    def generate_temporal_boundary(
        self,
        base_expr: str,
        input_type: str,
        precision: Optional[int],
        boundary_type: str,
        has_timezone: bool
    ) -> str:
        """Generate SQL for temporal boundary calculation.

        Handles date, dateTime, time, and instant types with precision-based
        boundary computation.

        Precision values:
        - Date: 4 (year), 6 (month), 8 (day)
        - DateTime: 10 (hour), 12 (minute), 14 (second), 17 (millisecond+tz)
        - Time: 9 (time millisecond)

        Args:
            base_expr: SQL expression for the input temporal value
            input_type: Temporal type (date, datetime, time, instant)
            precision: Target precision (None = input precision)
            boundary_type: 'high' or 'low'
            has_timezone: Whether the value includes timezone information

        Returns:
            DuckDB-specific SQL for temporal boundary calculation
        """
        # Normalize input type
        input_type_lower = input_type.lower()

        # Handle Date type
        if input_type_lower == 'date':
            if precision is None or precision == 4:
                # Year precision: first/last day of year
                if boundary_type == 'high':
                    return f"DATE_TRUNC('year', {base_expr}) + INTERVAL 1 YEAR - INTERVAL 1 DAY"
                else:  # low
                    return f"DATE_TRUNC('year', {base_expr})"
            elif precision == 6:
                # Month precision: first/last day of month
                if boundary_type == 'high':
                    return f"DATE_TRUNC('month', {base_expr}) + INTERVAL 1 MONTH - INTERVAL 1 DAY"
                else:  # low
                    return f"DATE_TRUNC('month', {base_expr})"
            else:  # precision == 8 or day precision
                # Day precision: return as-is
                return base_expr

        # Handle DateTime/Instant type
        elif input_type_lower in ('datetime', 'instant'):
            if precision is None or precision == 4:
                # Year precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('year', {base_expr}) + INTERVAL 1 YEAR - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('year', {base_expr})"
            elif precision == 6:
                # Month precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('month', {base_expr}) + INTERVAL 1 MONTH - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('month', {base_expr})"
            elif precision == 8:
                # Day precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('day', {base_expr}) + INTERVAL 1 DAY - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('day', {base_expr})"
            elif precision == 10:
                # Hour precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('hour', {base_expr}) + INTERVAL 1 HOUR - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('hour', {base_expr})"
            elif precision == 12:
                # Minute precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('minute', {base_expr}) + INTERVAL 1 MINUTE - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('minute', {base_expr})"
            elif precision == 14:
                # Second precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('second', {base_expr}) + INTERVAL 1 SECOND - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('second', {base_expr})"
            elif precision == 17:
                # Millisecond with timezone precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('millisecond', {base_expr}) + INTERVAL 1 MILLISECOND - INTERVAL 1 MICROSECOND"
                else:  # low
                    return f"DATE_TRUNC('millisecond', {base_expr})"
            else:
                # Default: return as-is
                return base_expr

        # Handle Time type
        elif input_type_lower == 'time':
            if precision is None or precision == 9:
                # Time millisecond precision
                if boundary_type == 'high':
                    # For time, wrap around at 24:00:00
                    return f"CASE WHEN {base_expr} + INTERVAL 1 MILLISECOND >= TIME '24:00:00' THEN TIME '23:59:59.999' ELSE {base_expr} + INTERVAL 1 MILLISECOND - INTERVAL 1 MICROSECOND END"
                else:  # low
                    return base_expr
            else:
                # Other time precisions: return as-is
                return base_expr

        # Default: return as-is
        return base_expr

    # String functions

    def generate_string_function(self, function_name: str, *args: str) -> str:
        """Generate string function SQL for DuckDB.

        Implements FHIRPath string functions using DuckDB's string functions:
        - substring(string, start[, length]): Extract substring
        - indexOf(string, search): Find position of substring (0-based)
        - length(string): Get string length
        - replace(string, search, replace): Replace substring

        Args:
            function_name: Name of the string function
            *args: Function arguments

        Returns:
            DuckDB-specific SQL for the string function

        Note:
            FHIRPath uses 0-based indexing while SQL typically uses 1-based.
            The translator handles index conversion.
        """
        func_name = function_name.lower()

        if func_name == 'substring':
            # DuckDB substring: substring(string, start, length)
            # args[0] = string, args[1] = start (1-based), args[2] = length (optional)
            if len(args) == 2:
                return f"substring({args[0]}, {args[1]})"
            elif len(args) == 3:
                return f"substring({args[0]}, {args[1]}, {args[2]})"
            else:
                raise ValueError(f"substring() requires 2 or 3 arguments, got {len(args)}")

        elif func_name == 'indexof':
            # DuckDB uses strpos() which returns 1-based index (0 if not found)
            # args[0] = string, args[1] = search
            if len(args) != 2:
                raise ValueError(f"indexOf() requires 2 arguments, got {len(args)}")
            # Return 0-based index by subtracting 1
            return f"(strpos({args[0]}, {args[1]}) - 1)"

        elif func_name == 'length':
            # DuckDB uses length()
            # args[0] = string
            if len(args) != 1:
                raise ValueError(f"length() requires 1 argument, got {len(args)}")
            return f"length({args[0]})"

        elif func_name == 'replace':
            # DuckDB uses replace()
            # args[0] = string, args[1] = search, args[2] = replace
            if len(args) != 3:
                raise ValueError(f"replace() requires 3 arguments, got {len(args)}")
            return f"replace({args[0]}, {args[1]}, {args[2]})"

        else:
            raise ValueError(f"Unknown string function: {function_name}")

    def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
        """Generate regex matching SQL for DuckDB.

        Uses DuckDB's regexp_matches() function for PCRE-compatible regex matching.

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern

        Returns:
            SQL expression using DuckDB's regexp_matches() function

        Example:
            generate_regex_match("patient_name", "'[A-Z][a-z]+'")
            → "regexp_matches(patient_name, '[A-Z][a-z]+')"
        """
        return f"regexp_matches({string_expr}, {regex_pattern})"

    def generate_regex_replace(self, string_expr: str, regex_pattern: str, substitution: str) -> str:
        """Generate regex replacement SQL for DuckDB.

        Uses DuckDB's regexp_replace() function for PCRE-compatible regex replacement.
        The 'g' flag enables global replacement (all matches replaced).

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern
            substitution: SQL expression for replacement string (can include $1, $2, etc.)

        Returns:
            SQL expression using DuckDB's regexp_replace() function

        Example:
            generate_regex_replace("patient_name", "'\\d+'", "'XXX'")
            → "regexp_replace(patient_name, '\\d+', 'XXX', 'g')"
        """
        return f"regexp_replace({string_expr}, {regex_pattern}, {substitution}, 'g')"

    def generate_json_children(self, json_expr: str) -> str:
        """Generate SQL to extract direct children from a JSON object for DuckDB.

        Uses DuckDB's json_keys() function to get all keys from the JSON object,
        then extracts each child value.

        Args:
            json_expr: SQL expression evaluating to a JSON object

        Returns:
            SQL expression returning a list of child element values

        Example:
            generate_json_children("resource")
            → "list(json_transform(resource, obj -> json_extract_string(obj, value))[1])"

        Note:
            - DuckDB doesn't have a direct way to get all child values
            - We use json_transform with json_keys to iterate and extract
            - Returns empty list for null input
        """
        # For DuckDB, we need to extract all child values from a JSON object
        # The approach: get keys, then for each key extract the value
        # json_transform allows us to iterate over key-value pairs
        return f"list((SELECT json_extract_string({json_expr}, key) FROM (SELECT unnest(json_keys({json_expr})) AS key)))"

    def generate_substring_check(self, string_expr: str, substring: str) -> str:
        """Generate substring check SQL for DuckDB.

        Uses standard SQL LIKE operator with concatenation for substring detection.

        Args:
            string_expr: SQL expression evaluating to string
            substring: SQL expression for substring to find

        Returns:
            SQL expression using LIKE operator with wildcards

        Example:
            generate_substring_check("patient_name", "'Smith'")
            → "(patient_name LIKE '%' || 'Smith' || '%')"
        """
        return f"({string_expr} LIKE '%' || {substring} || '%')"

    def generate_membership_test(self, collection_expr: str, value_expr: str) -> str:
        """Generate membership test SQL for DuckDB (contains operator).

        Uses json_each and EXISTS to check if value is in collection.

        Args:
            collection_expr: SQL expression evaluating to collection (JSON array)
            value_expr: SQL expression for value to find

        Returns:
            SQL expression using EXISTS with json_each

        Example:
            generate_membership_test("json_extract(resource, '$.tags')", "'active'")
            → "EXISTS (SELECT 1 FROM json_each(json_extract(resource, '$.tags')) WHERE value = 'active')"
        """
        # For string literals, wrap in to_json() for proper comparison with JSON values
        # Detect if value_expr is a string literal (starts and ends with single quote)
        value_stripped = value_expr.strip()
        if value_stripped.startswith("'") and value_stripped.endswith("'"):
            # String literal - wrap in to_json() for proper JSON comparison
            value_expr = f"to_json({value_expr})"

        # Handle JSON arrays - use json_each to iterate and check for matching value
        return f"EXISTS (SELECT 1 FROM json_each({collection_expr}) WHERE value = {value_expr})"

    def generate_prefix_check(self, string_expr: str, prefix: str) -> str:
        """Generate prefix check SQL for DuckDB (startsWith).

        Uses standard SQL LIKE operator with concatenation for prefix detection.

        Args:
            string_expr: SQL expression evaluating to string
            prefix: SQL expression for prefix to find

        Returns:
            SQL expression using LIKE operator for prefix matching

        Example:
            generate_prefix_check("patient_name", "'Mc'")
            → "(patient_name LIKE 'Mc' || '%')"
        """
        return f"({string_expr} LIKE {prefix} || '%')"

    def generate_suffix_check(self, string_expr: str, suffix: str) -> str:
        """Generate suffix check SQL for DuckDB (endsWith).

        Uses standard SQL LIKE operator with concatenation for suffix detection.

        Args:
            string_expr: SQL expression evaluating to string
            suffix: SQL expression for suffix to find

        Returns:
            SQL expression using LIKE operator for suffix matching

        Example:
            generate_suffix_check("patient_name", "'son'")
            → "(patient_name LIKE '%' || 'son')"
        """
        return f"({string_expr} LIKE '%' || {suffix})"

    def generate_case_conversion(self, string_expr: str, case_type: str) -> str:
        """Generate case conversion SQL for DuckDB.

        Uses standard SQL UPPER() and LOWER() functions for case conversion.

        Args:
            string_expr: SQL expression evaluating to string
            case_type: Type of conversion ('upper' or 'lower')

        Returns:
            SQL expression for case conversion

        Raises:
            ValueError: If case_type is not 'upper' or 'lower'

        Example:
            generate_case_conversion("patient_name", "upper")
            → "UPPER(patient_name)"
            generate_case_conversion("patient_name", "lower")
            → "LOWER(patient_name)"
        """
        if case_type == 'upper':
            return f"UPPER({string_expr})"
        elif case_type == 'lower':
            return f"LOWER({string_expr})"
        else:
            raise ValueError(f"Invalid case_type: {case_type}. Must be 'upper' or 'lower'")

    def generate_trim(self, string_expr: str) -> str:
        """Generate whitespace trimming SQL for DuckDB.

        Uses standard SQL TRIM() function to remove leading and trailing whitespace.

        Args:
            string_expr: SQL expression evaluating to string

        Returns:
            SQL expression for trimming whitespace

        Example:
            generate_trim("patient_name")
            → "TRIM(patient_name)"
        """
        return f"TRIM({string_expr})"

    def generate_char_array(self, string_expr: str) -> str:
        """Generate SQL to split string into character array for DuckDB.

        Uses CASE WHEN to handle empty strings specially (return empty array),
        and regexp_split_to_array with empty delimiter for non-empty strings.

        Args:
            string_expr: SQL expression evaluating to string

        Returns:
            SQL expression returning array of single-character strings

        Example:
            generate_char_array("'hello'")
            → "CASE WHEN length('hello') = 0 THEN [] ELSE regexp_split_to_array('hello', '') END"

        Note:
            - Empty string returns empty array []
            - regexp_split_to_array('', '') would return [''] (array with empty string)
            - CASE WHEN ensures correct empty array behavior
        """
        return f"CASE WHEN length({string_expr}) = 0 THEN [] ELSE regexp_split_to_array({string_expr}, '') END"

    # Date/time operations

    def generate_current_timestamp(self) -> str:
        """Generate current timestamp for DuckDB."""
        return "now()"

    def generate_current_date(self) -> str:
        """Generate current date for DuckDB."""
        return "current_date"

    def generate_current_time(self) -> str:
        """Generate current time for DuckDB."""
        return "current_time"

    def generate_date_diff(self, unit: str, start_date: str, end_date: str) -> str:
        """Generate date difference using DuckDB's DATE_DIFF."""
        return f"DATE_DIFF('{unit}', {start_date}, {end_date})"

    # Aggregate functions

    def generate_aggregate_function(self, function_name: str, expression: str,
                                  filter_condition: str = None, distinct: bool = False) -> str:
        """Generate aggregate function SQL for DuckDB."""
        func_map = {
            'variance': 'VAR_SAMP',
            'stddev': 'STDDEV_SAMP'
        }
        actual_func = func_map.get(function_name.lower(), function_name.upper())

        # Handle DISTINCT
        expr = f"DISTINCT {expression}" if distinct else expression

        # Generate function call
        sql = f"{actual_func}({expr})"

        # Add filter condition if provided
        if filter_condition:
            sql = f"{sql} FILTER (WHERE {filter_condition})"

        return sql

    # Collection operations

    def generate_where_clause_filter(self, collection_expr: str, condition_sql: str) -> str:
        """Generate WHERE clause filtering for collections in DuckDB."""
        return f"""(
            SELECT json_group_array(item.value)
            FROM json_each({collection_expr}) AS item
            WHERE {condition_sql.replace('$ITEM', 'item.value')}
        )"""

    def generate_select_transformation(self, collection_expr: str, transform_path: str) -> str:
        """Generate SELECT transformation for collections in DuckDB."""
        return f"""(
            SELECT json_group_array(json_extract(value, '$.{transform_path}'))
            FROM json_each({collection_expr})
        )"""

    def generate_collection_combine(self, first_collection: str, second_collection: str) -> str:
        """Generate collection combination SQL for DuckDB."""
        return f"""(
            CASE
                WHEN {first_collection} IS NULL AND {second_collection} IS NULL THEN NULL
                WHEN {first_collection} IS NULL THEN {second_collection}
                WHEN {second_collection} IS NULL THEN {first_collection}
                WHEN json_type({first_collection}) = 'ARRAY' AND json_type({second_collection}) = 'ARRAY' THEN (
                    SELECT json_group_array(value)
                    FROM (
                        SELECT value FROM json_each({first_collection})
                        UNION ALL
                        SELECT value FROM json_each({second_collection})
                    )
                )
                ELSE json_array({first_collection}, {second_collection})
            END
        )"""

    def generate_collection_exclude(self, collection_expr: str, exclusion_expr: str) -> str:
        """Generate collection exclusion SQL for DuckDB."""
        return (
            "COALESCE("
            f"to_json(list_filter(from_json({collection_expr}, '[\"VARCHAR\"]'), x -> x <> {exclusion_expr})), "
            "CAST('[]' AS JSON)"
            ")"
        )

    def wrap_json_array(self, expression: str) -> str:
        """Wrap scalar expression as single-element JSON array using DuckDB syntax.

        SP-108-003: Fixed to handle all expression types. Using to_json() to convert
        scalar values to JSON format before wrapping in array, which handles VARCHAR
        values from json_extract_string correctly.
        """
        # Always use to_json() to ensure the value is in JSON format before wrapping
        return f"json_array(to_json({expression}))"

    def serialize_json_value(self, expression: str) -> str:
        """Serialize JSON value to canonical text preserving type semantics."""
        return f"CAST({expression} AS VARCHAR)"

    def empty_json_array(self) -> str:
        """Return DuckDB empty JSON array literal."""
        return "json_array()"

    def is_json_array(self, expression: str) -> str:
        """Check if expression evaluates to a DuckDB JSON array.

        SP-108-003: Fixed to handle all expression types. Using to_json() instead of
        CAST(... AS JSON) because to_json() properly handles string values by converting
        them to JSON format (e.g., "value" -> "\"value\"").
        """
        # Use to_json() which handles all types correctly including VARCHAR from json_extract_string
        return f"(json_type(to_json({expression})) = 'ARRAY')"

    def enumerate_json_array(self, array_expr: str, value_alias: str, index_alias: str) -> str:
        """Enumerate JSON array into rows of (index, value) using DuckDB json_each().

        Note: value is returned as JSON type. For aggregate() operations, the translator
        may need to cast to appropriate numeric type (e.g., TRY_CAST(value AS DOUBLE)).
        """
        return (
            f"SELECT CAST(key AS INTEGER) AS {index_alias}, value AS {value_alias} "
            f"FROM json_each({array_expr})"
        )

    def generate_exists_check(self, fragment: str, is_collection: bool) -> str:
        """Generate exists/empty check SQL for DuckDB."""
        if is_collection:
            return f"(json_array_length({fragment}) > 0)"
        else:
            return f"({fragment} IS NOT NULL)"

    def generate_empty_check(self, collection_expr: str) -> str:
        """Generate empty check SQL for DuckDB.

        Returns true if collection is empty, false otherwise.
        Uses DuckDB's json_array_length function.

        Args:
            collection_expr: SQL expression representing a JSON array

        Returns:
            SQL expression: (json_array_length(collection) = 0)
        """
        return f"(json_array_length({collection_expr}) = 0)"

    def generate_boolean_not(self, expr: str) -> str:
        """Generate boolean NOT expression for DuckDB.

        Returns the logical negation of the input boolean expression.
        Uses standard SQL NOT operator.

        Args:
            expr: SQL expression evaluating to boolean

        Returns:
            SQL expression: NOT (expression)
        """
        return f"NOT ({expr})"

    def generate_all_check(self, column: str, path: str, element_alias: str, criteria_expr: str) -> str:
        """Generate universal quantifier check SQL for DuckDB.

        Uses bool_and() aggregate to check if all elements satisfy criteria.
        COALESCE handles empty arrays (NULL from bool_and) to return true.

        Args:
            column: Source table/column name
            path: JSON path to the collection
            element_alias: Alias for array elements
            criteria_expr: Already-translated criteria expression

        Returns:
            SQL expression checking if all elements satisfy criteria
        """
        # Extract the JSON array
        collection_expr = self.extract_json_field(column, path)

        # Generate SQL with bool_and aggregate
        # COALESCE returns true for empty arrays (vacuous truth)
        return f"""COALESCE(
    (SELECT bool_and({criteria_expr})
     FROM (SELECT unnest({collection_expr}) as {element_alias})),
    true
)"""

    def generate_array_skip(self, array_expr: str, skip_count: str) -> str:
        """Generate array skip SQL using OFFSET semantics."""
        empty_array = self.empty_json_array()
        cast_skip = self.cast_to_type(f"({skip_count})", "BIGINT")
        value_alias = "skip_value"
        index_alias = "skip_index"
        enumeration_sql = self.enumerate_json_array(array_expr, value_alias, index_alias)

        ordered_rows_sql = (
            f"SELECT {value_alias}, {index_alias} "
            f"FROM ({enumeration_sql}) AS skip_enum "
            f"ORDER BY {index_alias} "
            f"OFFSET {cast_skip}"
        )

        aggregate_expr = self.aggregate_to_json_array(f"{value_alias} ORDER BY {index_alias}")
        aggregated_sql = (
            f"SELECT {aggregate_expr} "
            f"FROM ({ordered_rows_sql}) AS skip_ordered"
        )

        return (
            "("
            "CASE "
            f"WHEN ({array_expr}) IS NULL THEN NULL "
            f"WHEN ({skip_count}) IS NULL THEN NULL "
            f"WHEN ({skip_count}) < 0 THEN {empty_array} "
            f"WHEN ({skip_count}) = 0 THEN {array_expr} "
            f"ELSE COALESCE(({aggregated_sql}), {empty_array}) "
            "END"
            ")"
        )

    def generate_array_take(self, array_expr: str, take_count: str) -> str:
        """Generate array take SQL using LIMIT semantics."""
        empty_array = self.empty_json_array()
        cast_take = self.cast_to_type(f"({take_count})", "BIGINT")
        value_alias = "take_value"
        index_alias = "take_index"
        enumeration_sql = self.enumerate_json_array(array_expr, value_alias, index_alias)

        limited_rows_sql = (
            f"SELECT {value_alias}, {index_alias} "
            f"FROM ({enumeration_sql}) AS take_enum "
            f"ORDER BY {index_alias} "
            f"LIMIT {cast_take}"
        )

        aggregate_expr = self.aggregate_to_json_array(f"{value_alias} ORDER BY {index_alias}")
        aggregated_sql = (
            f"SELECT {aggregate_expr} "
            f"FROM ({limited_rows_sql}) AS take_ordered"
        )

        return (
            "("
            "CASE "
            f"WHEN ({array_expr}) IS NULL THEN NULL "
            f"WHEN ({take_count}) IS NULL THEN NULL "
            f"WHEN ({take_count}) <= 0 THEN {empty_array} "
            f"ELSE COALESCE(({aggregated_sql}), {empty_array}) "
            "END"
            ")"
        )

    def generate_array_last(self, array_expr: str) -> str:
        """Generate SQL that returns the final element of a collection."""
        value_alias = "last_value"
        index_alias = "last_index"
        enumeration_sql = self.enumerate_json_array(array_expr, value_alias, index_alias)

        last_select_sql = (
            f"SELECT {value_alias} "
            f"FROM ({enumeration_sql}) AS last_enum "
            f"ORDER BY {index_alias} DESC "
            f"LIMIT 1"
        )

        return (
            "("
            "CASE "
            f"WHEN ({array_expr}) IS NULL THEN NULL "
            f"ELSE ({last_select_sql}) "
            "END"
            ")"
        )

    # Boolean operations

    def generate_logical_combine(self, left_condition: str, operator: str, right_condition: str) -> str:
        """Generate logical condition combination SQL for DuckDB."""
        return f"({left_condition}) {operator.upper()} ({right_condition})"

    def generate_date_literal(self, date_value: str) -> str:
        """Generate SQL date literal for DuckDB.

        Args:
            date_value: Date string in ISO format (YYYY-MM-DD)

        Returns:
            DuckDB date literal

        Example:
            @2024-01-01 → DATE '2024-01-01'
        """
        return f"DATE '{date_value}'"

    def generate_datetime_literal(self, datetime_value: str) -> str:
        """Generate SQL datetime literal for DuckDB.

        Handles partial precision timestamps by padding to full timestamp format.

        Args:
            datetime_value: DateTime string in ISO format (YYYY-MM-DDTHH:MM:SS)
                          Supports partial precision: @2015T, @2015-02T, @2015-02-04T14

        Returns:
            DuckDB timestamp literal

        Examples:
            @2024-01-01T12:30:00 → TIMESTAMP '2024-01-01 12:30:00'
            @2015T → TIMESTAMP '2015-01-01 00:00:00'
            @2015-02T → TIMESTAMP '2015-02-01 00:00:00'
            @2015-02-04T14 → TIMESTAMP '2015-02-04 14:00:00'
        """
        # Pad partial timestamps to full TIMESTAMP format
        padded_datetime = self._pad_partial_timestamp(datetime_value)

        # Convert ISO format (T separator) to SQL format (space separator)
        sql_datetime = padded_datetime.replace('T', ' ')
        return f"TIMESTAMP '{sql_datetime}'"

    def _pad_partial_timestamp(self, timestamp_str: str) -> str:
        """Pad partial FHIRPath timestamp to full format.

        FHIRPath supports partial precision timestamps. This method pads them
        to the full YYYY-MM-DDTHH:MM:SS.fff format required by SQL TIMESTAMP.

        SP-100-012: Enhanced to handle timezone suffixes (Z, +/-HH:MM).

        Args:
            timestamp_str: Partial or full timestamp string

        Returns:
            Padded timestamp in full format (without timezone suffix)

        Examples:
            @2015T → 2015-01-01T00:00:00
            @2015-02T → 2015-02-01T00:00:00
            @2015-02-04 → 2015-02-04T00:00:00
            @2015-02-04T14 → 2015-02-04T14:00:00
            @2015-02-04T14:30 → 2015-02-04T14:30:00
            @2015-02-04T14:30:45 → 2015-02-04T14:30:45 (no change)
            @2015-02-04T14:30:45Z → 2015-02-04T14:30:45 (timezone stripped)
        """
        # Remove @ prefix if present
        ts = timestamp_str.lstrip('@')

        # SP-100-012: Strip timezone suffix before processing
        # DuckDB will handle timezone conversion separately
        timezone = None
        if ts.endswith('Z'):
            timezone = 'Z'
            ts = ts[:-1]
        else:
            # Check for +/-HH:MM timezone offset
            import re
            tz_match = re.search(r'([+-]\d{2}:\d{2})$', ts)
            if tz_match:
                timezone = tz_match.group(1)
                ts = ts[:tz_match.start()]

        # Check if there's a 'T' separator
        if 'T' in ts:
            date_part, time_part = ts.split('T', 1)
        else:
            # Date-only format (e.g., @2015-02-04 or @2015T)
            date_part = ts.rstrip('T')
            time_part = ''

        # Pad date part: YYYY → YYYY-MM-DD
        date_parts = date_part.split('-')
        if len(date_parts) == 1:
            # Year only: @2015T → 2015-01-01
            date_part = f"{date_parts[0]}-01-01"
        elif len(date_parts) == 2:
            # Year-month: @2015-02T → 2015-02-01
            date_part = f"{date_parts[0]}-{date_parts[1]}-01"
        # else: already YYYY-MM-DD

        # Pad time part: HH → HH:MM:SS
        if not time_part:
            time_part = "00:00:00"
        else:
            time_parts = time_part.split(':')
            if len(time_parts) == 1:
                # Hour only: 14 → 14:00:00
                time_part = f"{time_parts[0]}:00:00"
            elif len(time_parts) == 2:
                # Hour:minute: 14:30 → 14:30:00
                time_part = f"{time_parts[0]}:{time_parts[1]}:00"
            # else: already HH:MM:SS or HH:MM:SS.fff

        return f"{date_part}T{time_part}"

    def generate_time_literal(self, time_value: str) -> str:
        """Generate SQL time literal for DuckDB.

        Handles partial time formats by padding to full HH:MM:SS format.
        Also strips timezone suffixes (Z, +/-HH:MM) as they're not supported
        in DuckDB TIME literals.

        Args:
            time_value: Time string (e.g., 'T14', 'T14:34', 'T14:34:28', 'T14:34:28Z')

        Returns:
            DuckDB time literal

        Examples:
            'T14' → TIME '14:00:00'
            'T14:34' → TIME '14:34:00'
            'T14:34:28' → TIME '14:34:28'
            'T14:34:28Z' → TIME '14:34:28' (timezone stripped)
        """
        import re

        # Remove @ prefix if present
        ts = time_value.lstrip('@')

        # Strip timezone suffix (Z or +/-HH:MM) - not supported in TIME literals
        if ts.endswith('Z'):
            ts = ts[:-1]
        else:
            tz_match = re.search(r'([+-]\d{2}:\d{2})$', ts)
            if tz_match:
                ts = ts[:tz_match.start()]

        # Remove 'T' prefix if present (FHIRPath time literal syntax)
        if ts.startswith('T'):
            ts = ts[1:]

        # Pad partial time to HH:MM:SS format
        time_parts = ts.split(':')
        if len(time_parts) == 1:
            # Hour only: 14 → 14:00:00
            ts = f"{time_parts[0]}:00:00"
        elif len(time_parts) == 2:
            # Hour:minute: 14:30 → 14:30:00
            ts = f"{time_parts[0]}:{time_parts[1]}:00"
        # else: already HH:MM:SS or HH:MM:SS.fff

        return f"TIME '{ts}'"

    def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
        """Generate SQL comparison operation for DuckDB.

        Args:
            left_expr: Left operand SQL expression
            operator: Comparison operator (=, !=, <, >, <=, >=)
            right_expr: Right operand SQL expression

        Returns:
            DuckDB comparison expression

        Example:
            ('age', '>=', '18') → '(age >= 18)'
        """
        return f"({left_expr} {operator} {right_expr})"

    def safe_cast_to_decimal(self, expression: str) -> str:
        """Safely cast expression to DECIMAL in DuckDB.

        Uses TRY_CAST which returns NULL instead of error for invalid input.
        """
        return f"TRY_CAST({expression} AS DECIMAL)"

    def safe_cast_to_integer(self, expression: str) -> str:
        """Safely cast expression to BIGINT in DuckDB.

        Uses TRY_CAST which returns NULL instead of error for invalid input.
        """
        return f"TRY_CAST({expression} AS BIGINT)"

    def strict_cast_to_decimal(self, expression: str) -> str:
        """Strictly cast expression to DECIMAL in DuckDB.

        SP-103-004: Uses CAST which throws error on type mismatch.
        """
        return f"CAST({expression} AS DECIMAL)"

    def strict_cast_to_integer(self, expression: str) -> str:
        """Strictly cast expression to BIGINT in DuckDB.

        SP-103-004: Uses CAST which throws error on type mismatch.
        """
        return f"CAST({expression} AS BIGINT)"

    def safe_cast_to_date(self, expression: str) -> str:
        """Safely cast expression to DATE in DuckDB.

        Uses TRY_CAST which returns NULL instead of error for invalid input.
        """
        return f"TRY_CAST({expression} AS DATE)"

    def safe_cast_to_timestamp(self, expression: str) -> str:
        """Safely cast expression to TIMESTAMP in DuckDB.

        Uses TRY_CAST which returns NULL instead of error for invalid input.
        """
        return f"TRY_CAST({expression} AS TIMESTAMP)"

    def safe_cast_to_boolean(self, expression: str) -> str:
        """Safely cast expression to BOOLEAN in DuckDB.

        Uses TRY_CAST which returns NULL instead of error for invalid input.
        """
        return f"TRY_CAST({expression} AS BOOLEAN)"

    def generate_conditional_expression(self, condition: str, true_expr: str, false_expr: str) -> str:
        """Generate conditional expression SQL for DuckDB."""
        return f"CASE WHEN {condition} THEN {true_expr} ELSE {false_expr} END"

    def generate_type_check(self, expression: str, fhirpath_type: str) -> str:
        """Generate SQL for PRIMITIVE type checking (is() operation) in DuckDB.

        THIN DIALECT PRINCIPLE: This method handles ONLY primitive types.
        Complex types are handled by translator's _generate_complex_type_check().

        This implementation inspects both native DuckDB scalar types (via
        ``typeof``) and JSON scalar payloads (via ``json_type``) so callers
        can provide either direct column values or JSON-extracted fragments.

        Args:
            expression: SQL expression to type-check
            fhirpath_type: PRIMITIVE FHIR type name (string, integer, boolean, etc.)

        Returns:
            DuckDB-specific SQL for checking if expression matches the primitive type

        Note:
            This method should NEVER be called with complex types (Patient, HumanName, etc.)
            The translator routes those to _generate_complex_type_check() instead.
        """
        normalized = (fhirpath_type or "").lower()

        # Treat derived primitives as their underlying string representation.
        type_family_map = {
            "uri": "string",
            "url": "string",
            "canonical": "string",
            "oid": "string",
            "uuid": "string",
            "id": "string",
            "code": "string",
            "markdown": "string",
            "instant": "datetime",  # instant is a datetime primitive
        }
        family = type_family_map.get(normalized, normalized)

        scalar_type_map = {
            "string": ["VARCHAR", "STRING", "TEXT", "CHAR"],
            "integer": ["INTEGER", "BIGINT", "UBIGINT", "SMALLINT", "TINYINT"],
            "decimal": ["DECIMAL", "DOUBLE", "FLOAT", "REAL", "HUGEINT"],
            "boolean": ["BOOLEAN"],
            "datetime": ["TIMESTAMP", "TIMESTAMP WITH TIME ZONE"],
            "date": ["DATE"],
            "time": ["TIME"],
        }
        json_type_map = {
            "string": ["VARCHAR"],
            "integer": ["UBIGINT", "BIGINT", "INTEGER", "SMALLINT"],
            "decimal": ["DOUBLE", "DECIMAL", "REAL"],
            "boolean": ["BOOLEAN"],
            "datetime": ["VARCHAR"],
            "date": ["VARCHAR"],
            "time": ["VARCHAR"],
        }
        # SP-108-002: Add boolean regex pattern to match FHIR boolean strings
        # FHIR boolean values are stored as JSON strings 'true' or 'false'
        # This pattern matches both lowercase and variants
        regex_patterns = {
            "boolean": r'^(true|false)$',
            "datetime": r'^\d{4}(-\d{2}(-\d{2})?)?T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$',
            "date": r'^\d{4}(-\d{2}(-\d{2})?)?$',
            "time": r'^\d{2}:\d{2}:\d{2}(\.\d+)?$',
        }

        scalar_types = scalar_type_map.get(family)
        if not scalar_types:
            logger.warning("Unknown FHIRPath type '%s' in type check, defaulting to false", fhirpath_type)
            return "false"

        json_types = json_type_map.get(family, [])

        def _format_types(type_list: list[str]) -> str:
            return ", ".join(f"'{t}'" for t in type_list)

        scalar_predicate = "true"
        json_predicate = "true"

        if family in regex_patterns:
            pattern = regex_patterns[family].replace("'", "''")
            scalar_value = f"CAST({expression} AS VARCHAR)"
            json_value = f"json_extract_string({expression}, '$')"
            scalar_predicate = f"regexp_matches({scalar_value}, '{pattern}')"
            json_predicate = (
                f"regexp_matches({json_value}, '{pattern}')"
                if json_types
                else "false"
            )

        json_branch = "false"
        if json_types:
            json_branch = (
                f"CASE WHEN json_type({expression}) IN ({_format_types(json_types)}) "
                f"THEN {json_predicate} ELSE false END"
            )

        # For temporal types (date, datetime, time), use regex as primary check
        # because partial dates like @2015 are stored as strings, not DATE types
        if family in regex_patterns:
            scalar_branch = (
                f"CASE "
                f"WHEN typeof({expression}) IN ({_format_types(scalar_types)}) THEN true "
                f"ELSE {scalar_predicate} "
                f"END"
            )
        else:
            scalar_branch = (
                f"CASE WHEN typeof({expression}) IN ({_format_types(scalar_types)}) "
                f"THEN {scalar_predicate} ELSE false END"
            )

        # Return NULL when input is NULL to propagate empty collections
        # SP-102-003: When is() is called on a non-existent field (NULL),
        # returning NULL instead of false ensures the row is filtered out,
        # producing an empty result set as expected by FHIRPath semantics.
        return (
            f"CASE "
            f"WHEN {expression} IS NULL THEN NULL "
            f"WHEN typeof({expression}) = 'JSON' THEN {json_branch} "
            f"ELSE {scalar_branch} "
            f"END"
        )

    def generate_type_cast(self, expression: str, target_type: str) -> str:
        """Generate SQL for type casting (as() operation) in DuckDB.

        Uses DuckDB's TRY_CAST() function to safely cast an expression to a specific
        type. Returns the casted value if successful, or null if the cast fails.

        This is a thin dialect method containing ONLY DuckDB syntax. Type mapping
        from FHIRPath types is handled in this method as part of syntax adaptation.

        Args:
            expression: SQL expression to cast
            target_type: FHIRPath type name (e.g., "DateTime", "Integer", "String")

        Returns:
            DuckDB SQL expression that performs the type cast

        Example:
            expression='123', target_type='Integer'
            → TRY_CAST(123 AS INTEGER)

            expression='2024-01-01', target_type='DateTime'
            → TRY_CAST(2024-01-01 AS TIMESTAMP)

        Note:
            Uses TRY_CAST for safe casting - returns NULL on failure instead of error.
            DuckDB type names: INTEGER, VARCHAR, DOUBLE, BOOLEAN, TIMESTAMP, DATE, TIME.
        """
        # Map FHIRPath types to DuckDB type names (uppercase)
        # This mapping is part of syntax adaptation, not business logic
        # SP-106-004: Use DECIMAL for FHIRPath decimal type to maintain precision
        # SP-108-001: Use DECIMAL(38,10) to support large decimal values with fractional parts
        # 38 total digits with 10 after decimal point preserves precision for most FHIRPath decimals
        type_map = {
            "string": "VARCHAR",
            "integer": "INTEGER",
            "decimal": "DECIMAL(38,10)",  # Support large decimals with fractional parts
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMP",
            "date": "DATE",
            "time": "TIME",
            "uri": "VARCHAR",
        }

        normalized_type = target_type.lower() if target_type else ""

        # Handle primitive subtypes (e.g., string1, code1, integer1)
        # These should be mapped to their base types
        base_type = normalized_type
        if base_type.endswith('1'):
            # Strip the '1' suffix to get the base type
            base_type = base_type[:-1]

        duckdb_type = type_map.get(base_type)

        if duckdb_type is None:
            # SP-110-003: Unknown FHIRPath types should fail at execution time
            # Generate SQL that will cause a conversion error
            invalid_type_name = target_type.replace("-", "_").upper()
            return f"CAST({expression} AS INVALID_FHIR_TYPE_{invalid_type_name})"

        # SP-104-006: Handle partial date strings for DateTime casting
        # When the parser strips the 'T' suffix from @2015T, we get just "2015"
        # We need to pad it to "2015-01-01" for TIMESTAMP casting
        if normalized_type == "datetime" and duckdb_type == "TIMESTAMP":
            # Check if expression is a simple string literal that might be a partial date
            # Pattern: expression looks like '2015' or '2015-02' (single-quoted string)
            import re
            # Extract string literal if present
            str_match = re.match(r"^'([^']+)'$", expression.strip())
            if str_match:
                date_str = str_match.group(1)
                # Check if it's a partial date (YYYY or YYYY-MM)
                if re.match(r'^\d{4}$', date_str):
                    # Year only: pad to YYYY-01-01
                    padded = f"{date_str}-01-01"
                    return f"TRY_CAST('{padded}' AS {duckdb_type})"
                elif re.match(r'^\d{4}-\d{2}$', date_str):
                    # Year-month: pad to YYYY-MM-01
                    padded = f"{date_str}-01"
                    return f"TRY_CAST('{padded}' AS {duckdb_type})"

        # Generate type casting SQL using DuckDB's TRY_CAST() function
        # TRY_CAST returns NULL on conversion failure instead of throwing error
        return f"TRY_CAST({expression} AS {duckdb_type})"

    def generate_collection_type_filter(self, expression: str, target_type: str) -> str:
        """Generate SQL for collection type filtering (ofType() operation) in DuckDB.

        Implementation uses ``json_each`` to iterate JSON arrays and filters by the
        recorded JSON scalar type. The result is re-aggregated with ``json_group_array``.
        """
        if not target_type:
            return f"COALESCE({expression}, '[]')"

        normalized = target_type.lower()

        # Handle primitive subtypes (e.g., string1, code1, integer1)
        # These should be mapped to their base types
        base_type = normalized
        if base_type.endswith('1'):
            # Strip the '1' suffix to get the base type
            base_type = base_type[:-1]

        type_family_map = {
            "uri": "string",
            "url": "string",
            "canonical": "string",
            "oid": "string",
            "uuid": "string",
            "id": "string",
            "code": "string",
            "markdown": "string",
        }
        family = type_family_map.get(base_type, base_type)

        value_type_map = {
            "string": ["VARCHAR"],
            "integer": ["UBIGINT", "BIGINT", "INTEGER", "SMALLINT"],
            "decimal": ["DOUBLE", "DECIMAL", "REAL"],
            "boolean": ["BOOLEAN"],
            "datetime": ["VARCHAR"],
            "date": ["VARCHAR"],
            "time": ["VARCHAR"],
        }
        regex_patterns = {
            "datetime": r'^\d{4}(-\d{2}(-\d{2})?)?T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$',
            "date": r'^\d{4}(-\d{2}(-\d{2})?)?$',
            "time": r'^\d{2}:\d{2}:\d{2}(\.\d+)?$',
        }

        # SP-110-003: Check if this is a complex FHIR type (not in value_type_map)
        # Complex types like HumanName, Patient, etc. are filtered by resourceType field
        if family not in value_type_map:
            # For complex types, check the resourceType field in JSON objects
            base_expr = f"COALESCE({expression}, '[]')"
            escaped_type = target_type.replace("'", "''")
            return (
                f"(SELECT COALESCE(json_group_array(elem.value), '[]') "
                f"FROM json_each({base_expr}) AS elem "
                f"WHERE json_extract_string(elem.value, '$.resourceType') = '{escaped_type}')"
            )

        value_types = value_type_map.get(family)
        if not value_types:
            logger.warning(
                "Type '%s' cannot be filtered in DuckDB ofType() (unsupported family '%s'), returning empty array",
                target_type,
                family,
            )
            return "[]"

        def _format_types(type_list: list[str]) -> str:
            return ", ".join(f"'{t}'" for t in type_list)

        base_expr = f"COALESCE({expression}, '[]')"
        type_column = 'elem."type"'
        type_condition = f"{type_column} IN ({_format_types(value_types)})"

        if family in regex_patterns:
            pattern = regex_patterns[family].replace("'", "''")
            scalar_condition = (
                f"regexp_matches(json_extract_string(elem.value, '$'), '{pattern}')"
            )
            type_condition = (
                f"{type_column} = 'VARCHAR' AND {scalar_condition}"
            )

        return (
            f"(SELECT COALESCE(json_group_array(elem.value), '[]') "
            f"FROM json_each({base_expr}) AS elem "
            f"WHERE {type_condition})"
        )

    def filter_extension_by_url(self, extensions_expr: str, url: str) -> str:
        """Filter extension array by URL using UNNEST and WHERE clause.

        SP-110 Phase 2: Fixed to use json_each() UNNEST with WHERE clause instead of
        list_filter(). DuckDB's list_filter() requires a LIST type (created with ['a','b']
        syntax), but we have JSON arrays from json_extract(). The solution is to UNNEST
        the JSON array and filter with WHERE, then re-aggregate with json_array().
        """
        escaped_url = url.replace("'", "''")
        base_expr = f"COALESCE({extensions_expr}, json_array())"

        # Use UNNEST + WHERE + re-aggregate instead of list_filter
        # DuckDB uses json_array() to aggregate values into a JSON array
        return (
            f"(SELECT json_array(enum_table.value) "
            f"FROM json_each({base_expr}) AS enum_table(key, value) "
            f"WHERE coalesce(json_extract_string(enum_table.value, '$.url'), '') = '{escaped_url}')"
        )

    def extract_extension_values(self, extensions_expr: str) -> str:
        """Extract value[x] payloads from extension objects in DuckDB.

        SP-110-EXT-FIX: Fixed lambda binding issue by replacing list_transform/list_filter
        with json_each() subquery. The lambda variables (ext, val) in list_transform()
        were causing "Referenced column 'ext' not found in FROM clause" errors when the
        result was wrapped in additional subqueries (e.g., extension().exists()).
        """
        base_expr = f"COALESCE({extensions_expr}, json_array())"
        value_paths = [
            "valueBoolean",
            "valueInteger",
            "valueDecimal",
            "valueBase64Binary",
            "valueInstant",
            "valueString",
            "valueUri",
            "valueDate",
            "valueDateTime",
            "valueTime",
            "valueCode",
            "valueOid",
            "valueId",
            "valueUnsignedInt",
            "valuePositiveInt",
            "valueMarkdown",
            "valueAnnotation",
            "valueAttachment",
            "valueIdentifier",
            "valueCodeableConcept",
            "valueCoding",
            "valueQuantity",
            "valueRange",
            "valuePeriod",
            "valueRatio",
            "valueSampledData",
            "valueSignature",
            "valueHumanName",
            "valueAddress",
            "valueContactPoint",
            "valueTiming",
            "valueReference",
            "valueMeta",
            "valueDosage",
            "valueDistance",
            "valueDuration",
            "valueCount",
            "valueMoney",
        ]
        # Build COALESCE expression for all value[x] paths
        coalesce_args = ", ".join(
            [f"json_extract(ext_table.value, '$.{path}')" for path in value_paths] + ["NULL"]
        )

        # Use json_each() instead of list_transform() to avoid lambda variable binding issues
        # This approach works correctly when nested in subqueries
        return (
            f"(SELECT json_array(coalesce({coalesce_args})) "
            f"FROM json_each({base_expr}) AS ext_table(key, value) "
            f"WHERE coalesce({coalesce_args}) IS NOT NULL)"
        )

    def project_json_array(self, array_expr: str, path_components: List[str]) -> str:
        """Project JSON array elements along nested path.

        SP-110-EXT-FIX: Fixed lambda binding issue by replacing list_transform()
        with json_each() subquery. The lambda variable (elem) in list_transform()
        was causing "Referenced column 'elem' not found in FROM clause" errors
        when the result was wrapped in additional subqueries.
        """
        if not path_components:
            return array_expr

        def build_path(components: List[str]) -> str:
            path = "$"
            for comp in components:
                if not comp:
                    continue
                if comp.startswith("["):
                    path += comp
                else:
                    path += f".{comp}"
            return path

        json_path = build_path(path_components)
        base_expr = f"COALESCE({array_expr}, json_array())"

        # Use json_each() instead of list_transform() to avoid lambda variable binding issues
        return (
            f"(SELECT json_array(json_extract_string(proj_table.value, '{json_path}')) "
            f"FROM json_each({base_expr}) AS proj_table(key, value))"
        )

    def generate_all_true(self, collection_expr: str) -> str:
        """Generate SQL for allTrue() using BOOL_AND aggregate.

        Returns TRUE if all elements are TRUE. Empty collections return TRUE (vacuous truth).
        Uses COALESCE to handle empty collections and NULL values are ignored by BOOL_AND.
        """
        return f"COALESCE((SELECT BOOL_AND(CAST(value AS BOOLEAN)) FROM json_each({collection_expr})), TRUE)"

    def generate_any_true(self, collection_expr: str) -> str:
        """Generate SQL for anyTrue() using BOOL_OR aggregate.

        Returns TRUE if any element is TRUE. Empty collections return FALSE.
        Uses COALESCE to handle empty collections and NULL values are ignored by BOOL_OR.
        """
        return f"COALESCE((SELECT BOOL_OR(CAST(value AS BOOLEAN)) FROM json_each({collection_expr})), FALSE)"

    def generate_all_false(self, collection_expr: str) -> str:
        """Generate SQL for allFalse() using BOOL_AND(NOT value).

        Returns TRUE if all elements are FALSE. Empty collections return TRUE (vacuous truth).
        Implemented as BOOL_AND on negated values.
        """
        return f"COALESCE((SELECT BOOL_AND(NOT CAST(value AS BOOLEAN)) FROM json_each({collection_expr})), TRUE)"

    def generate_any_false(self, collection_expr: str) -> str:
        """Generate SQL for anyFalse() using BOOL_OR(NOT value).

        Returns TRUE if any element is FALSE. Empty collections return FALSE.
        Implemented as BOOL_OR on negated values.
        """
        return f"COALESCE((SELECT BOOL_OR(NOT CAST(value AS BOOLEAN)) FROM json_each({collection_expr})), FALSE)"

    def generate_array_to_string(self, array_expr: str, separator: str) -> str:
        """Generate SQL for combine() using array_to_string.

        Joins array elements with separator. NULL elements are skipped.
        """
        return f"array_to_string({array_expr}, {separator})"

    def generate_distinct(self, expression: str) -> str:
        """Generate SQL for distinct() using DISTINCT keyword.

        Removes duplicates while preserving order of first occurrences.
        Note: This should be used in a SELECT context.
        """
        return f"DISTINCT {expression}"

    def generate_is_distinct(self, expression: str) -> str:
        """Generate SQL for isDistinct() comparing count to distinct count.

        Returns TRUE if all elements are unique (count equals distinct count).
        Empty collections return TRUE.
        """
        return f"(COUNT(*) = COUNT(DISTINCT {expression}))"

    def generate_lateral_json_enumeration(self, array_expr: str, enum_alias: str,
                                         value_col: str = "value", index_col: str = "key") -> str:
        """Generate LATERAL clause for JSON array enumeration with key/value columns.

        DuckDB uses json_each() function which returns (key, value) pairs.
        The key column contains the 0-based array index.

        Args:
            array_expr: Expression that produces a JSON array
            enum_alias: Table alias for the enumeration table
            value_col: Column name for the value (default: "value")
            index_col: Column name for the index/key (default: "key")

        Returns:
            SQL LATERAL clause string

        Example:
            generate_lateral_json_enumeration("resource->'name'", "enum_table", "value", "key")
            → "LATERAL json_each(resource->'name') AS enum_table(key, value)"
        """
        return f"LATERAL json_each({array_expr}) AS {enum_alias}({index_col}, {value_col})"

    # Encoding and decoding functions

    def generate_base64_encode(self, expression: str) -> str:
        """Generate SQL for base64 encoding using DuckDB's to_base64 function."""
        return f"to_base64({expression})"

    def generate_base64_decode(self, expression: str) -> str:
        """Generate SQL for base64 decoding using DuckDB's from_base64 function."""
        return f"from_base64({expression})"

    def generate_hex_encode(self, expression: str) -> str:
        """Generate SQL for hex encoding using DuckDB's to_hex function."""
        return f"to_hex({expression})"

    def generate_hex_decode(self, expression: str) -> str:
        """Generate SQL for hex decoding using DuckDB's from_hex function."""
        return f"from_hex({expression})"

    def generate_urlbase64_encode(self, expression: str) -> str:
        """Generate SQL for URL-safe base64 encoding.

        URL-safe base64 replaces '+' with '-' and '/' with '_'.
        Also removes trailing '=' padding.
        """
        # DuckDB: base64 then replace + with - and / with _, then remove padding
        return f"rtrim(replace(replace(base64({expression}), '+', '-'), '/', '_'), '=')"

    def generate_urlbase64_decode(self, expression: str) -> str:
        """Generate SQL for URL-safe base64 decoding.

        First restore the replaced characters, then decode.
        """
        # DuckDB: restore + and /, add padding if needed, then decode
        return f"base64_decode(replace(replace({expression}, '-', '+'), '_', '/'), 'UTF-8')"

    def generate_html_escape(self, expression: str) -> str:
        """Generate SQL for HTML escaping in DuckDB.

        Escapes &, <, >, ", ' characters.
        Order matters: escape & first to avoid double-escaping.
        """
        # DuckDB uses regexp_replace for character escaping
        return f"regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace({expression}, '&', '&amp;'), '<', '&lt;'), '>', '&gt;'), '\"', '&quot;'), '''', '&apos;')"

    def generate_json_escape(self, expression: str) -> str:
        """Generate SQL for JSON escaping in DuckDB.

        Escapes quotes and backslashes.
        """
        # JSON escaping: escape backslash first, then quotes
        return f"replace(replace({expression}, '\\\\', '\\\\\\\\'), '\"', '\\\\\"')"

    def generate_html_unescape(self, expression: str) -> str:
        """Generate SQL for HTML unescaping in DuckDB.

        Unescapes &amp;, &lt;, &gt;, &quot;, &apos;, &#39;.
        Order matters for longest matches first.
        """
        # DuckDB uses regexp_replace for character unescaping
        # Handle numeric entity &#39; first, then named entities
        return f"regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace({expression}, '&amp;', '&'), '&lt;', '<'), '&gt;', '>'), '&quot;', '\"'), '&apos;', '''')"

    def generate_json_unescape(self, expression: str) -> str:
        """Generate SQL for JSON unescaping in DuckDB.

        Unescapes escaped quotes and backslashes.
        Order: unescape \\\" first, then \\\\.
        """
        # Reverse of JSON escape: unescape quotes first, then backslashes
        return f"replace(replace({expression}, '\\\\\"', '\"'), '\\\\\\\\', '\\\\')"

    def generate_array_sort(self, array_expr: str, ascending: bool = True, element_type: Optional[str] = None) -> str:
        """Generate SQL for sorting array elements in DuckDB.

        DuckDB's array_sort function sorts in ascending order by default.
        For descending, we reverse the sorted array.

        Note: When array_expr is a JSON array (from union chains via aggregate_to_json_array),
        we need to convert it to a typed list first. The union produces a flat JSON array
        like '[1,2,3]' which we cast to VARCHAR (to get string representation) and then
        to a typed array (INTEGER[] for integers, VARCHAR[] for strings).

        Args:
            array_expr: SQL expression for the array to sort
            ascending: True for ascending order, False for descending
            element_type: Optional type hint for elements ("string", "integer", "decimal")
        """
        # For JSON arrays from union chains, we need to:
        # 1. Materialize the JSON array in a CTE (it's '[1,2,3]' from aggregate_to_json_array)
        # 2. Cast JSON to VARCHAR (gets string '[1,2,3]')
        # 3. Cast VARCHAR to typed array (INTEGER[] for integers, VARCHAR[] for strings)
        # 4. Apply array_sort and convert back to JSON

        # SP-110-XXX: Use element_type to determine correct array type
        # Default to INTEGER for backward compatibility if no type specified
        if element_type == "string":
            target_type = "VARCHAR[]"
        elif element_type == "decimal":
            target_type = "DECIMAL[]"
        else:
            # Default to INTEGER for integer or unknown types
            target_type = "INTEGER[]"

        order_fn = "array_sort" if ascending else "array_reverse(array_sort"

        return f"""
            (WITH json_arr AS (
                SELECT {array_expr} AS arr
            ),
            typed_arr AS (
                SELECT arr::VARCHAR::{target_type} AS typed_list
                FROM json_arr
            )
            SELECT to_json({order_fn}(typed_list){')' if not ascending else ''}) FROM typed_arr)
        """.strip()

    def generate_json_descendants(self, json_expr: str) -> str:
        """Generate SQL for getting all descendant elements of a JSON node.

        Returns a JSON array containing all descendant elements recursively.

        For DuckDB, we use a recursive CTE to traverse the JSON tree.
        This implementation extracts all values from nested JSON structures.

        SP-110-AUTOPILOT: Fixed to use DuckDB's list() instead of PostgreSQL's json_agg()
        """
        # DuckDB recursive CTE approach for descendants
        # This creates a recursive query that traverses all nested JSON structures
        # SP-110-AUTOPILOT: Use list() instead of json_agg() for DuckDB compatibility
        return f"""
            (WITH RECURSIVE descendants AS (
                -- Base case: start with current node's direct children
                SELECT key, value FROM json_each({json_expr})
                UNION ALL
                -- Recursive case: traverse nested objects/arrays
                SELECT d.key, d.value
                FROM descendants c
                CROSS JOIN json_each(CASE WHEN json_type(c.value) IN ('OBJECT', 'ARRAY') THEN c.value ELSE NULL END) d
            )
            SELECT list(value) FROM descendants)
        """.strip()
