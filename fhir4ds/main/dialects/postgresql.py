"""
PostgreSQL dialect implementation for FHIR4DS.

This module provides PostgreSQL-specific SQL syntax while maintaining the thin
dialect architecture principle: business logic in FHIRPath evaluator,
only syntax differences in dialects.
"""

import logging
import time
from functools import wraps
from typing import Any, List, Optional, Tuple, Set

from .base import DatabaseDialect

# Optional import for PostgreSQL
try:
    import psycopg2
    from psycopg2 import pool, Error, OperationalError, InterfaceError, ProgrammingError, DataError
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

logger = logging.getLogger(__name__)


class PostgreSQLDialect(DatabaseDialect):
    """
    PostgreSQL implementation of the database dialect.

    Provides PostgreSQL-specific SQL generation with emphasis on JSONB operations
    and enterprise-grade performance for production healthcare data workloads.
    """

    def __init__(self, connection_string: str, pool_size: int = 5, max_retries: int = 3,
                 retry_backoff: float = 2.0, timeout_seconds: int = 30):
        """Initialize PostgreSQL dialect with connection pooling.

        Args:
            connection_string: PostgreSQL connection string (e.g., 'postgresql://user:pass@host:port/db')
            pool_size: Maximum number of connections in the pool (default: 5)
            max_retries: Maximum number of retry attempts for transient failures (default: 3)
            retry_backoff: Backoff factor for exponential retry delays (default: 2.0)
            timeout_seconds: Query timeout in seconds (default: 30)
        """
        super().__init__()

        if not POSTGRESQL_AVAILABLE:
            raise ImportError("psycopg2 is required but not installed. Install with: pip install psycopg2-binary")

        # PostgreSQL-specific settings
        self.name = "POSTGRESQL"
        self.supports_jsonb = True
        self.supports_json_functions = True
        self.json_type = "JSONB"
        self.cast_syntax = "::"
        self.quote_char = '"'

        # Connection pool settings
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.timeout_seconds = timeout_seconds
        self._timeout_configured_connections: Set[int] = set()
        # Manual fallback for mocked connections that cannot re-enter psycopg2 pool.
        self._manual_connection_pool: List[Any] = []

        try:
            # Initialize connection pool using positional DSN argument so tests can
            # replace psycopg2.connect with lightweight fakes without supporting kwargs.
            self.connection_pool = pool.SimpleConnectionPool(
                1,
                pool_size,
                connection_string,
            )
            logger.info(f"Initialized PostgreSQL dialect with connection pool (size: {pool_size})")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise

    def get_connection(self) -> Any:
        """Acquire a connection from the pool.

        Returns:
            PostgreSQL database connection from the pool

        Raises:
            Error: If connection pool is exhausted or connection fails
        """
        try:
            if self._manual_connection_pool:
                return self._manual_connection_pool.pop()
            conn = self.connection_pool.getconn()
            if conn is None:
                raise OperationalError("Connection pool exhausted")
            return conn
        except Exception as e:
            logger.error(f"Failed to acquire connection from pool: {e}")
            raise

    def release_connection(self, conn: Any) -> None:
        """Return a connection to the pool.

        Args:
            conn: Database connection to return to the pool
        """
        if conn is None:
            return

        try:
            if not hasattr(conn, "closed"):
                setattr(conn, "closed", False)
            if not hasattr(conn, "info"):
                setattr(conn, "info", None)
            self.connection_pool.putconn(conn)
        except Exception as e:
            logger.debug("Falling back to manual connection pool: %s", e)
            self._manual_connection_pool.append(conn)
        finally:
            conn_id = id(conn)
            if conn_id in self._timeout_configured_connections:
                self._timeout_configured_connections.discard(conn_id)

    def close_all_connections(self) -> None:
        """Close all connections in the pool.

        Call this when shutting down the application to ensure proper cleanup.
        """
        try:
            self.connection_pool.closeall()
            logger.info("Closed all PostgreSQL connections")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")

    def __del__(self):
        """Cleanup connection pool on object destruction."""
        try:
            if hasattr(self, 'connection_pool') and self.connection_pool:
                self.close_all_connections()
        except Exception:
            pass  # Suppress errors during cleanup

    def _with_retry(self, operation_name: str):
        """Decorator for retry logic with exponential backoff.

        Args:
            operation_name: Name of the operation for logging

        Returns:
            Decorated function with retry logic
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(self.max_retries):
                    try:
                        return func(*args, **kwargs)
                    except (OperationalError, InterfaceError) as e:
                        # Transient connection errors - retry
                        if attempt < self.max_retries - 1:
                            sleep_time = self.retry_backoff ** attempt
                            logger.warning(
                                f"{operation_name} - Retry {attempt + 1}/{self.max_retries} "
                                f"after {sleep_time}s due to transient error: {e}"
                            )
                            time.sleep(sleep_time)
                        else:
                            logger.error(f"{operation_name} - Max retries ({self.max_retries}) exceeded: {e}")
                            raise
                    except (ProgrammingError, DataError) as e:
                        # Query/data errors - don't retry
                        logger.error(f"{operation_name} - Query error (no retry): {e}")
                        raise
                    except Exception as e:
                        # Other errors - don't retry
                        logger.error(f"{operation_name} - Unexpected error (no retry): {e}")
                        raise
            return wrapper
        return decorator

    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """Execute SQL query and return results with retry logic.

        Args:
            sql: SQL query to execute
            params: Optional query parameters for parameterized queries

        Returns:
            List of tuples representing query results

        Raises:
            OperationalError: If connection fails after retries
            ProgrammingError: If query syntax is invalid
            DataError: If data types are incompatible
        """
        @self._with_retry("execute_query")
        def _execute():
            conn = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()

                # Set query timeout once per connection
                conn_id = id(conn)
                if conn_id not in self._timeout_configured_connections:
                    cursor.execute(f"SET statement_timeout = {self.timeout_seconds * 1000}")
                    self._timeout_configured_connections.add(conn_id)

                # Execute query
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                # Fetch results (only for queries that return data)
                # DDL statements (CREATE, DROP, ALTER) don't return results
                if cursor.description is not None:
                    results = cursor.fetchall()
                else:
                    results = []  # No results for DDL/command statements

                # Commit transaction
                if hasattr(conn, "commit"):
                    conn.commit()

                return results

            except Exception as e:
                logger.error(f"PostgreSQL query execution error: {e}")
                logger.debug(f"Failed query: {sql}")
                if conn and hasattr(conn, "rollback"):
                    conn.rollback()
                raise
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    self.release_connection(conn)

        return _execute()

    # JSON extraction methods

    def extract_json_field(self, column: str, path: str) -> str:
        """Extract JSON field as text using PostgreSQL's jsonb_extract_path_text."""
        # Convert JSONPath to PostgreSQL path format
        path_parts = path.strip('$').strip('.').split('.')
        path_args = ', '.join(f"'{part}'" for part in path_parts if part)
        return f"jsonb_extract_path_text({column}, {path_args})"

    def extract_json_object(self, column: str, path: str) -> str:
        """Extract JSON object using PostgreSQL's jsonb_extract_path."""
        # Convert JSONPath to PostgreSQL path format
        path_parts = path.strip('$').strip('.').split('.')
        path_args = ', '.join(f"'{part}'" for part in path_parts if part)
        return f"jsonb_extract_path({column}, {path_args})"

    def check_json_exists(self, column: str, path: str) -> str:
        """Check if JSON path exists in PostgreSQL."""
        return f"({self.extract_json_object(column, path)} IS NOT NULL)"

    def extract_primitive_value(self, column: str, path: str) -> str:
        """Extract FHIR primitive value handling both simple and complex representations.

        FHIR primitives can be: {"field": "value"} or {"field": {"value": "...", "extension": [...]}}
        This method uses COALESCE to try complex representation first, then simple.

        Note: PostgreSQL's jsonb_extract_path_text already returns TEXT type, so no
        explicit cast is needed (unlike DuckDB which requires CAST AS VARCHAR).
        """
        # Convert JSONPath to PostgreSQL path format for complex representation (path.value)
        path_with_value = path + '.value'
        path_parts_complex = path_with_value.strip('$').strip('.').split('.')
        path_args_complex = ', '.join(f"'{part}'" for part in path_parts_complex if part)

        # Convert JSONPath to PostgreSQL path format for simple representation (path)
        path_parts_simple = path.strip('$').strip('.').split('.')
        path_args_simple = ', '.join(f"'{part}'" for part in path_parts_simple if part)

        # Try to extract from complex representation (path.value), fall back to simple (path)
        # jsonb_extract_path_text already returns TEXT, so no cast needed
        return f"COALESCE(jsonb_extract_path_text({column}, {path_args_complex}), jsonb_extract_path_text({column}, {path_args_simple}))"

    # Type-aware JSON extraction for SQL-on-FHIR ViewDefinitions

    def extract_json_string(self, column: str, path: str) -> str:
        """Extract JSON field as string using PostgreSQL's ->> operator.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.id', '$.name[0].family')
                  Note: PostgreSQL uses different path syntax without $ prefix

        Returns:
            PostgreSQL SQL expression: resource->>'path'

        Example:
            >>> dialect.extract_json_string('resource', 'id')
            "resource->>'id'"

        Note:
            This method expects paths without the $ prefix. If a path contains $,
            it will be stripped. Array indexing like [0] is handled by stripping
            the $ and . prefixes.
        """
        # Strip $ prefix and leading . if present
        clean_path = path.lstrip('$').lstrip('.')

        # SP-022-007: Handle empty path (extracting the JSON value itself as text)
        # This is needed when comparing UNNEST results to string literals
        if not clean_path:
            # Use #>> '{}' to extract JSONB scalar as text
            return f"{column} #>> '{{}}'"

        return f"{column}->>'{clean_path}'"

    def extract_json_integer(self, column: str, path: str) -> str:
        """Extract JSON field as integer using PostgreSQL's -> operator with cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.age', '$.value')

        Returns:
            PostgreSQL SQL expression: (resource->'path')::integer

        Example:
            >>> dialect.extract_json_integer('resource', 'age')
            "(resource->'age')::integer"
        """
        # Strip $ prefix and leading . if present
        clean_path = path.lstrip('$').lstrip('.')
        return f"({column}->'{clean_path}')::integer"

    def extract_json_decimal(self, column: str, path: str) -> str:
        """Extract JSON field as decimal using PostgreSQL's -> operator with cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.value', '$.price')

        Returns:
            PostgreSQL SQL expression: (resource->'path')::decimal

        Example:
            >>> dialect.extract_json_decimal('resource', 'value')
            "(resource->'value')::decimal"
        """
        # Strip $ prefix and leading . if present
        clean_path = path.lstrip('$').lstrip('.')
        return f"({column}->'{clean_path}')::decimal"

    def extract_json_boolean(self, column: str, path: str) -> str:
        """Extract JSON field as boolean using PostgreSQL's -> operator with cast.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.active', '$.deceased')

        Returns:
            PostgreSQL SQL expression: (resource->'path')::boolean

        Example:
            >>> dialect.extract_json_boolean('resource', 'active')
            "(resource->'active')::boolean"
        """
        # Strip $ prefix and leading . if present
        clean_path = path.lstrip('$').lstrip('.')
        return f"({column}->'{clean_path}')::boolean"

    def get_json_type(self, column: str) -> str:
        """Get JSON value type using PostgreSQL's jsonb_typeof."""
        return f"jsonb_typeof({column})"

    def get_json_array_length(self, column: str, path: str = None) -> str:
        """Get JSON array length using PostgreSQL's jsonb_array_length."""
        if path:
            return f"jsonb_array_length({self.extract_json_object(column, path)})"
        else:
            return f"jsonb_array_length({column})"

    # Array and collection operations

    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        """Generate SQL for unnesting JSON array elements using PostgreSQL's jsonb_array_elements.

        Args:
            column: Source column or table name containing JSON
            path: JSON path to the array (e.g., '$.name', '$.address')
            alias: Alias name for the unnested array elements

        Returns:
            PostgreSQL-specific SQL fragment for array unnesting

        Example:
            >>> dialect.unnest_json_array('resource', '$.name', 'name_item')
            'jsonb_array_elements(jsonb_extract_path(resource, 'name')) AS name_item'
        """
        # Extract the JSON object first, then unnest the array
        json_obj = self.extract_json_object(column, path)
        return f"jsonb_array_elements({json_obj}) AS {alias}(unnest)"

    def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:
        """Generate PostgreSQL-specific LATERAL UNNEST syntax using jsonb_array_elements().

        Args:
            source_table: Name of the table or CTE providing the array column (kept for interface parity).
            array_column: SQL expression evaluating to the JSONB array that should be unnested.
            alias: Alias assigned to each unnested JSONB element.

        Returns:
            PostgreSQL SQL fragment implementing a LATERAL UNNEST via jsonb_array_elements().

        Example:
            >>> dialect.generate_lateral_unnest("patient_cte", "json_extract(resource, '$.name')", "name_item")
            'LATERAL jsonb_array_elements(json_extract(resource, '$.name')) AS name_item'
        """
        _ = source_table  # PostgreSQL syntax does not require referencing the source table.
        return f"LATERAL jsonb_array_elements({array_column}) AS {alias}(unnest)"

    def iterate_json_array(self, column: str, path: str) -> str:
        """Iterate over JSON array elements using PostgreSQL's jsonb_array_elements."""
        return f"jsonb_array_elements({self.extract_json_object(column, path)})"

    def aggregate_to_json_array(self, expression: str) -> str:
        """Aggregate values into JSON array using PostgreSQL's jsonb_agg."""
        return f"jsonb_agg({expression})"

    def create_json_array(self, *args) -> str:
        """Create JSON array using PostgreSQL's jsonb_build_array."""
        if args:
            return f"jsonb_build_array({', '.join(str(arg) for arg in args)})"
        return "jsonb_build_array()"

    def create_json_object(self, *args) -> str:
        """Create JSON object using PostgreSQL's jsonb_build_object."""
        if args:
            return f"jsonb_build_object({', '.join(str(arg) for arg in args)})"
        return "jsonb_build_object()"

    def json_array_contains(self, array_expr: str, scalar_expr: str) -> str:
        """Check whether a JSON array contains the supplied scalar using jsonb semantics."""
        normalized = f"COALESCE(({array_expr})::jsonb, '[]'::jsonb)"
        return (
            "EXISTS ("
            f"SELECT 1 FROM jsonb_array_elements({normalized}) AS elem "
            f"WHERE btrim(elem::text, '\"') = {scalar_expr}"
            ")"
        )

    # String operations

    def string_concat(self, left: str, right: str) -> str:
        """Concatenate strings using PostgreSQL's || operator."""
        return f"({left} || {right})"

    def substring(self, expression: str, start: str, length: str) -> str:
        """Extract substring using PostgreSQL's SUBSTRING function."""
        return f"SUBSTRING({expression} FROM ({start}) + 1 FOR {length})"

    def split_string(self, expression: str, delimiter: str) -> str:
        """Split string into array using PostgreSQL's string_to_array."""
        return f"string_to_array({expression}, {delimiter})"

    def generate_string_join(self, collection_expr: str, delimiter_expr: str, is_json_collection: bool) -> str:
        """Generate SQL for joining string collections in PostgreSQL."""
        if is_json_collection:
            source_expr = f"ARRAY(SELECT jsonb_array_elements_text({collection_expr}))"
        else:
            source_expr = collection_expr

        return (
            "(CASE "
            f"WHEN {collection_expr} IS NULL THEN NULL "
            f"ELSE array_to_string({source_expr}, {delimiter_expr}) "
            "END)"
        )

    # Type conversion operations

    def try_cast(self, expression: str, target_type: str) -> str:
        """Safe type conversion using PostgreSQL's CASE expression."""
        return f"""(
            CASE
                WHEN {expression} ~ '^[0-9]+$' AND '{target_type}' IN ('integer', 'bigint')
                THEN {expression}::{target_type}
                WHEN {expression} ~ '^[0-9]+(\\.[0-9]+)?$' AND '{target_type}' IN ('decimal', 'numeric', 'double precision')
                THEN {expression}::{target_type}
                WHEN LOWER({expression}) IN ('true', 'false', 't', 'f', '1', '0') AND '{target_type}' = 'boolean'
                THEN {expression}::boolean
                ELSE NULL
            END
        )"""

    def cast_to_timestamp(self, expression: str) -> str:
        """Cast to timestamp using PostgreSQL."""
        return f"CAST({expression} AS TIMESTAMP)"

    def cast_to_time(self, expression: str) -> str:
        """Cast to time using PostgreSQL."""
        return f"CAST({expression} AS TIME)"

    # Mathematical functions

    def cast_to_double(self, expression: str) -> str:
        """Cast expression to double precision for PostgreSQL."""
        return f"CAST({expression} AS DOUBLE PRECISION)"

    def is_finite(self, expression: str) -> str:
        """Check if numeric expression is finite in PostgreSQL."""
        return f"isfinite({expression})"

    def generate_math_function(self, function_name: str, *args: str) -> str:
        """Generate mathematical function SQL for PostgreSQL."""
        func_map = {
            'sqrt': 'sqrt',
            'ln': 'ln',
            'log': 'log',
            'exp': 'exp',
            'power': 'power',
            'ceiling': 'ceil',
            'floor': 'floor',
            'round': 'round',
            'abs': 'abs',
            'truncate': 'trunc'
        }
        sql_func = func_map.get(function_name.lower(), function_name.lower())
        return f"{sql_func}({', '.join(args)})"

    def generate_power_operation(self, base_expr: str, exponent_expr: str) -> str:
        """Generate power operation using PostgreSQL's power function."""
        return f"power({base_expr}, {exponent_expr})"

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
            PostgreSQL-specific SQL for boundary calculation
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
            target_prec_sql = f"LEAST(({precision_sql}) + 5, 31)"

        # Uncertainty calculation: 0.5 * 10^(-input_precision)
        uncertainty_sql = f"0.5 * power(10, -({precision_sql}))"

        # Boundary calculation: add or subtract uncertainty
        if boundary_type == "high":
            boundary_sql = f"({base_expr}) + ({uncertainty_sql})"
        else:  # low
            boundary_sql = f"({base_expr}) - ({uncertainty_sql})"

        # Round to target precision
        result_sql = f"ROUND(({boundary_sql})::NUMERIC, ({target_prec_sql}))"

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
            PostgreSQL-specific SQL for quantity boundary calculation
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
            PostgreSQL-specific SQL for temporal boundary calculation
        """
        # Normalize input type
        input_type_lower = input_type.lower()

        # Handle Date type
        if input_type_lower == 'date':
            if precision is None or precision == 4:
                # Year precision: first/last day of year
                if boundary_type == 'high':
                    return f"DATE_TRUNC('year', {base_expr}) + INTERVAL '1 year' - INTERVAL '1 day'"
                else:  # low
                    return f"DATE_TRUNC('year', {base_expr})"
            elif precision == 6:
                # Month precision: first/last day of month
                if boundary_type == 'high':
                    return f"DATE_TRUNC('month', {base_expr}) + INTERVAL '1 month' - INTERVAL '1 day'"
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
                    return f"DATE_TRUNC('year', {base_expr}) + INTERVAL '1 year' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('year', {base_expr})"
            elif precision == 6:
                # Month precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('month', {base_expr}) + INTERVAL '1 month' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('month', {base_expr})"
            elif precision == 8:
                # Day precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('day', {base_expr}) + INTERVAL '1 day' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('day', {base_expr})"
            elif precision == 10:
                # Hour precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('hour', {base_expr}) + INTERVAL '1 hour' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('hour', {base_expr})"
            elif precision == 12:
                # Minute precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('minute', {base_expr}) + INTERVAL '1 minute' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('minute', {base_expr})"
            elif precision == 14:
                # Second precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('second', {base_expr}) + INTERVAL '1 second' - INTERVAL '1 microsecond'"
                else:  # low
                    return f"DATE_TRUNC('second', {base_expr})"
            elif precision == 17:
                # Millisecond with timezone precision
                if boundary_type == 'high':
                    return f"DATE_TRUNC('millisecond', {base_expr}) + INTERVAL '1 millisecond' - INTERVAL '1 microsecond'"
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
                    return f"CASE WHEN {base_expr} + INTERVAL '1 millisecond' >= TIME '24:00:00' THEN TIME '23:59:59.999' ELSE {base_expr} + INTERVAL '1 millisecond' - INTERVAL '1 microsecond' END"
                else:  # low
                    return base_expr
            else:
                # Other time precisions: return as-is
                return base_expr

        # Default: return as-is
        return base_expr

    # String functions

    def generate_string_function(self, function_name: str, *args: str) -> str:
        """Generate string function SQL for PostgreSQL.

        Implements FHIRPath string functions using PostgreSQL's string functions:
        - substring(string, start[, length]): Extract substring
        - indexOf(string, search): Find position of substring (0-based)
        - length(string): Get string length
        - replace(string, search, replace): Replace substring

        Args:
            function_name: Name of the string function
            *args: Function arguments

        Returns:
            PostgreSQL-specific SQL for the string function

        Note:
            FHIRPath uses 0-based indexing while SQL typically uses 1-based.
            The translator handles index conversion.
        """
        func_name = function_name.lower()

        if func_name == 'substring':
            # PostgreSQL substring: substring(string FROM start FOR length)
            # args[0] = string, args[1] = start (1-based), args[2] = length (optional)
            if len(args) == 2:
                return f"substring({args[0]} FROM {args[1]})"
            elif len(args) == 3:
                return f"substring({args[0]} FROM {args[1]} FOR {args[2]})"
            else:
                raise ValueError(f"substring() requires 2 or 3 arguments, got {len(args)}")

        elif func_name == 'indexof':
            # PostgreSQL uses position() which returns 1-based index (0 if not found)
            # args[0] = string, args[1] = search
            if len(args) != 2:
                raise ValueError(f"indexOf() requires 2 arguments, got {len(args)}")
            # Return 0-based index by subtracting 1
            return f"(position({args[1]} in {args[0]}) - 1)"

        elif func_name == 'length':
            # PostgreSQL uses length()
            # args[0] = string
            if len(args) != 1:
                raise ValueError(f"length() requires 1 argument, got {len(args)}")
            return f"length({args[0]})"

        elif func_name == 'replace':
            # PostgreSQL uses replace()
            # args[0] = string, args[1] = search, args[2] = replace
            if len(args) != 3:
                raise ValueError(f"replace() requires 3 arguments, got {len(args)}")
            return f"replace({args[0]}, {args[1]}, {args[2]})"

        else:
            raise ValueError(f"Unknown string function: {function_name}")

    def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
        """Generate regex matching SQL for PostgreSQL.

        Uses PostgreSQL's ~ regex operator for POSIX-compatible regex matching.

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern

        Returns:
            SQL expression using PostgreSQL's ~ operator

        Example:
            generate_regex_match("patient_name", "'[A-Z][a-z]+'")
            → "(patient_name ~ '[A-Z][a-z]+')"
        """
        return f"({string_expr} ~ {regex_pattern})"

    def generate_regex_replace(self, string_expr: str, regex_pattern: str, substitution: str) -> str:
        """Generate regex replacement SQL for PostgreSQL.

        Uses PostgreSQL's regexp_replace() function for POSIX-compatible regex replacement.
        The 'g' flag enables global replacement (all matches replaced).

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern
            substitution: SQL expression for replacement string (can include \1, \2, etc.)

        Returns:
            SQL expression using PostgreSQL's regexp_replace() function

        Example:
            generate_regex_replace("patient_name", "'\\d+'", "'XXX'")
            → "regexp_replace(patient_name, '\\d+', 'XXX', 'g')"
        """
        return f"regexp_replace({string_expr}, {regex_pattern}, {substitution}, 'g')"

    def generate_json_children(self, json_expr: str) -> str:
        """Generate SQL to extract direct children from a JSON object for PostgreSQL.

        Uses PostgreSQL's jsonb_object_keys() function to get all keys from the JSON object,
        then extracts each child value.

        Args:
            json_expr: SQL expression evaluating to a JSONB object

        Returns:
            SQL expression returning an array of child element values

        Example:
            generate_json_children("resource")
            → "array_agg(resource->jsonb_object_keys(resource))"

        Note:
            - PostgreSQL has jsonb_object_keys() which returns a set of keys
            - We use the -> operator to extract values for each key
            - Returns empty array for null input
        """
        # For PostgreSQL, we can use jsonb_object_keys to get all keys
        # Then extract each value using the -> operator
        return f"array_agg({json_expr} -> jsonb_object_keys({json_expr}))"

    def generate_substring_check(self, string_expr: str, substring: str) -> str:
        """Generate substring check SQL for PostgreSQL.

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
        """Generate membership test SQL for PostgreSQL (contains operator).

        Uses jsonb_array_elements and EXISTS to check if value is in collection.

        Args:
            collection_expr: SQL expression evaluating to collection (JSONB array)
            value_expr: SQL expression for value to find

        Returns:
            SQL expression using EXISTS with jsonb_array_elements

        Example:
            generate_membership_test("resource->'tags'", "'active'")
            → "EXISTS (SELECT 1 FROM jsonb_array_elements(resource->'tags') WHERE value = 'active')"
        """
        # For string literals, wrap in to_jsonb() for proper comparison with JSONB values
        # Detect if value_expr is a string literal (starts and ends with single quote)
        value_stripped = value_expr.strip()
        if value_stripped.startswith("'") and value_stripped.endswith("'"):
            # String literal - wrap in to_jsonb() for proper JSON comparison
            value_expr = f"to_jsonb({value_expr})"

        # Cast to jsonb for array elements function
        return f"EXISTS (SELECT 1 FROM jsonb_array_elements(CAST({collection_expr} AS jsonb)) WHERE value = {value_expr})"

    def generate_prefix_check(self, string_expr: str, prefix: str) -> str:
        """Generate prefix check SQL for PostgreSQL (startsWith).

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
        """Generate suffix check SQL for PostgreSQL (endsWith).

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
        """Generate case conversion SQL for PostgreSQL.

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
        """Generate whitespace trimming SQL for PostgreSQL.

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
        """Generate SQL to split string into character array for PostgreSQL.

        Uses CASE WHEN to handle empty strings specially (return empty array),
        and regexp_split_to_array with empty delimiter for non-empty strings.

        Args:
            string_expr: SQL expression evaluating to string

        Returns:
            SQL expression returning array of single-character strings

        Example:
            generate_char_array("'hello'")
            → "CASE WHEN length('hello') = 0 THEN ARRAY[]::text[] ELSE regexp_split_to_array('hello', '') END"

        Note:
            - Empty string returns empty array ARRAY[]::text[]
            - regexp_split_to_array('', '') would return [''] (array with empty string)
            - CASE WHEN ensures correct empty array behavior
            - Need explicit type cast for empty array in PostgreSQL
        """
        return f"CASE WHEN length({string_expr}) = 0 THEN ARRAY[]::text[] ELSE regexp_split_to_array({string_expr}, '') END"

    # Date/time operations

    def generate_current_timestamp(self) -> str:
        """Generate current timestamp for PostgreSQL."""
        return "CURRENT_TIMESTAMP"

    def generate_current_date(self) -> str:
        """Generate current date for PostgreSQL."""
        return "CURRENT_DATE"

    def generate_current_time(self) -> str:
        """Generate current time for PostgreSQL."""
        return "CURRENT_TIME"

    def generate_date_diff(self, unit: str, start_date: str, end_date: str) -> str:
        """Generate date difference using PostgreSQL's EXTRACT."""
        if unit.lower() == 'day':
            return f"({end_date}::date - {start_date}::date)"
        elif unit.lower() == 'year':
            return f"EXTRACT(year FROM AGE({end_date}::date, {start_date}::date))"
        elif unit.lower() == 'month':
            return f"(EXTRACT(year FROM AGE({end_date}::date, {start_date}::date)) * 12 + EXTRACT(month FROM AGE({end_date}::date, {start_date}::date)))"
        else:
            return f"EXTRACT(epoch FROM ({end_date}::timestamp - {start_date}::timestamp)) / EXTRACT(epoch FROM INTERVAL '1 {unit}')"

    # Aggregate functions

    def generate_aggregate_function(self, function_name: str, expression: str,
                                  filter_condition: str = None, distinct: bool = False) -> str:
        """Generate aggregate function SQL for PostgreSQL."""
        func_map = {
            'variance': 'var_samp',
            'stddev': 'stddev_samp'
        }
        actual_func = func_map.get(function_name.lower(), function_name.lower())

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
        """Generate WHERE clause filtering for collections in PostgreSQL."""
        return f"""(
            SELECT jsonb_agg(item.value)
            FROM jsonb_array_elements({collection_expr}) AS item(value)
            WHERE {condition_sql.replace('$ITEM', 'item.value')}
        )"""

    def generate_select_transformation(self, collection_expr: str, transform_path: str) -> str:
        """Generate SELECT transformation for collections in PostgreSQL."""
        path_parts = transform_path.split('.')
        path_args = ', '.join(f"'{part}'" for part in path_parts)
        return f"""(
            SELECT jsonb_agg(jsonb_extract_path(value, {path_args}))
            FROM jsonb_array_elements({collection_expr}) AS item(value)
        )"""

    def generate_collection_combine(self, first_collection: str, second_collection: str) -> str:
        """Generate collection combination SQL for PostgreSQL."""
        return f"""(
            CASE
                WHEN {first_collection} IS NULL AND {second_collection} IS NULL THEN NULL
                WHEN {first_collection} IS NULL THEN {second_collection}
                WHEN {second_collection} IS NULL THEN {first_collection}
                WHEN jsonb_typeof({first_collection}) = 'array' AND jsonb_typeof({second_collection}) = 'array'
                THEN {first_collection} || {second_collection}
                ELSE jsonb_build_array({first_collection}, {second_collection})
            END
        )"""

    def generate_collection_exclude(self, collection_expr: str, exclusion_expr: str) -> str:
        """Generate collection exclusion SQL for PostgreSQL."""
        return f"""(
            CASE
                WHEN {collection_expr} IS NULL THEN '[]'::jsonb
                ELSE COALESCE(
                    (
                        SELECT jsonb_agg(to_jsonb(value::text))
                        FROM (
                            SELECT jsonb_array_elements_text({collection_expr}) AS value
                        ) AS elements
                        WHERE value <> ({exclusion_expr})::text
                    ),
                    '[]'::jsonb
                )
            END
        )"""

    def wrap_json_array(self, expression: str) -> str:
        """Wrap scalar expression as single-element JSON array using PostgreSQL syntax."""
        return f"jsonb_build_array({expression})"

    def serialize_json_value(self, expression: str) -> str:
        """Serialize JSON value to canonical text preserving type semantics.

        SP-110-001: Use ->> operator for proper JSON text extraction instead of ::text cast.
        Casting to ::text can create invalid JSON when the value is already a JSON string.
        The ->> operator extracts the text content from JSONB values properly.
        """
        return f"({expression} ->> 0)"

    def empty_json_array(self) -> str:
        """Return PostgreSQL empty JSON array literal."""
        return "'[]'::jsonb"

    def is_json_array(self, expression: str) -> str:
        """Check if expression evaluates to a PostgreSQL JSON array.

        The implementation uses a simple strategy: cast everything to jsonb and check.
        This works because ::jsonb casting is valid for jsonb, json, text, and unknown
        types. Casting jsonb to jsonb is a no-op, so there's no performance penalty.

        This replaces the old implementation that used to_jsonb() which fails on text
        expressions with 'unknown' type (string literals) with the error:
        "could not determine polymorphic type because input has type unknown"

        The fix ensures compatibility with all expression types that the FHIRPath
        translator might generate, including column references, JSON path operations,
        and string literals.
        """
        return f"(CASE WHEN {expression} IS NULL THEN NULL ELSE jsonb_typeof({expression}::jsonb) = 'array' END)"

    def enumerate_json_array(self, array_expr: str, value_alias: str, index_alias: str) -> str:
        """Enumerate JSON array into rows of (index, value) using jsonb_array_elements()."""
        return (
            f"SELECT (ordinality - 1) AS {index_alias}, value AS {value_alias} "
            f"FROM jsonb_array_elements({array_expr}) WITH ORDINALITY AS elem(value, ordinality)"
        )

    def generate_exists_check(self, fragment: str, is_collection: bool) -> str:
        """Generate exists/empty check SQL for PostgreSQL."""
        if is_collection:
            return f"(jsonb_array_length({fragment}) > 0)"
        else:
            return f"({fragment} IS NOT NULL)"

    def generate_empty_check(self, collection_expr: str) -> str:
        """Generate empty check SQL for PostgreSQL.

        Returns true if collection is empty, false otherwise.
        Uses PostgreSQL's jsonb_array_length function.

        Args:
            collection_expr: SQL expression representing a JSONB array

        Returns:
            SQL expression: (jsonb_array_length(collection) = 0)
        """
        return f"(jsonb_array_length({collection_expr}) = 0)"

    def generate_boolean_not(self, expr: str) -> str:
        """Generate boolean NOT expression for PostgreSQL.

        Returns the logical negation of the input boolean expression.
        Uses standard SQL NOT operator.

        Args:
            expr: SQL expression evaluating to boolean

        Returns:
            SQL expression: NOT (expression)
        """
        return f"NOT ({expr})"

    def generate_all_check(self, column: str, path: str, element_alias: str, criteria_expr: str) -> str:
        """Generate universal quantifier check SQL for PostgreSQL.

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
     FROM jsonb_array_elements({collection_expr}) as {element_alias}),
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
        """Generate logical condition combination SQL for PostgreSQL."""
        return f"({left_condition}) {operator.upper()} ({right_condition})"

    def generate_date_literal(self, date_value: str) -> str:
        """Generate SQL date literal for PostgreSQL.

        Args:
            date_value: Date string in ISO format (YYYY-MM-DD)

        Returns:
            PostgreSQL date literal

        Example:
            @2024-01-01 → DATE '2024-01-01'
        """
        return f"DATE '{date_value}'"

    def generate_datetime_literal(self, datetime_value: str) -> str:
        """Generate SQL datetime literal for PostgreSQL.

        Handles partial precision timestamps by padding to full timestamp format.

        Args:
            datetime_value: DateTime string in ISO format (YYYY-MM-DDTHH:MM:SS)
                          Supports partial precision: @2015T, @2015-02T, @2015-02-04T14

        Returns:
            PostgreSQL timestamp literal

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
        # PostgreSQL will handle timezone conversion separately
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
        """Generate SQL time literal for PostgreSQL."""
        return f"TIME '{time_value}'"

    def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
        """Generate SQL comparison operation for PostgreSQL.

        Args:
            left_expr: Left operand SQL expression
            operator: Comparison operator (=, !=, <, >, <=, >=)
            right_expr: Right operand SQL expression

        Returns:
            PostgreSQL comparison expression

        Example:
            ('age', '>=', '18') → '(age >= 18)'
        """
        return f"({left_expr} {operator} {right_expr})"

    def safe_cast_to_decimal(self, expression: str) -> str:
        """Safely cast expression to DECIMAL in PostgreSQL.

        PostgreSQL doesn't have TRY_CAST, so we use a regex check to validate
        numeric format before casting.
        """
        return (
            f"(CASE WHEN ({expression}) ~ '^-?[0-9]+(\\.[0-9]+)?([eE][+-]?[0-9]+)?$' "
            f"THEN ({expression})::DECIMAL ELSE NULL END)"
        )

    def safe_cast_to_integer(self, expression: str) -> str:
        """Safely cast expression to BIGINT in PostgreSQL.

        PostgreSQL doesn't have TRY_CAST, so we use a regex check to validate
        integer format before casting.
        """
        return (
            f"(CASE WHEN ({expression}) ~ '^-?[0-9]+$' "
            f"THEN ({expression})::BIGINT ELSE NULL END)"
        )

    def strict_cast_to_decimal(self, expression: str) -> str:
        """Strictly cast expression to DECIMAL in PostgreSQL.

        SP-103-004: Uses direct cast which throws error on type mismatch.
        """
        return f"({expression})::DECIMAL"

    def strict_cast_to_integer(self, expression: str) -> str:
        """Strictly cast expression to BIGINT in PostgreSQL.

        SP-103-004: Uses direct cast which throws error on type mismatch.
        """
        return f"({expression})::BIGINT"

    def safe_cast_to_date(self, expression: str) -> str:
        """Safely cast expression to DATE in PostgreSQL.

        PostgreSQL doesn't have TRY_CAST, so we use a regex check to validate
        date format (YYYY-MM-DD) before casting.
        """
        return (
            f"(CASE WHEN ({expression}) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$' "
            f"THEN ({expression})::DATE ELSE NULL END)"
        )

    def safe_cast_to_timestamp(self, expression: str) -> str:
        """Safely cast expression to TIMESTAMP in PostgreSQL.

        PostgreSQL doesn't have TRY_CAST, so we use a regex check to validate
        datetime format before casting.
        """
        return (
            f"(CASE WHEN ({expression}) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}(T| )[0-9]{{2}}:[0-9]{{2}}' "
            f"THEN ({expression})::TIMESTAMP ELSE NULL END)"
        )

    def safe_cast_to_boolean(self, expression: str) -> str:
        """Safely cast expression to BOOLEAN in PostgreSQL.

        PostgreSQL doesn't have TRY_CAST, so we use a CASE to check for
        valid boolean values before casting.
        """
        return (
            f"(CASE WHEN LOWER({expression}) IN ('true', 'false', 't', 'f', 'yes', 'no', '1', '0') "
            f"THEN ({expression})::BOOLEAN ELSE NULL END)"
        )

    def generate_conditional_expression(self, condition: str, true_expr: str, false_expr: str) -> str:
        """Generate conditional expression SQL for PostgreSQL."""
        return f"CASE WHEN {condition} THEN {true_expr} ELSE {false_expr} END"

    def generate_type_check(self, expression: str, fhirpath_type: str) -> str:
        """Generate SQL for PRIMITIVE type checking (is() operation) in PostgreSQL.

        THIN DIALECT PRINCIPLE: This method handles ONLY primitive types.
        Complex types are handled by translator's _generate_complex_type_check().

        Args:
            expression: SQL expression to type-check
            fhirpath_type: PRIMITIVE FHIR type name (string, integer, boolean, etc.)

        Returns:
            PostgreSQL-specific SQL for checking if expression matches the primitive type

        Note:
            This method should NEVER be called with complex types (Patient, HumanName, etc.)
            The translator routes those to _generate_complex_type_check() instead.
        """
        normalized = (fhirpath_type or "").lower()

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
            "string": ["text", "character varying", "varchar", "character", "char", "unknown"],
            "integer": ["integer", "bigint", "smallint", "int", "int2", "int4", "int8"],
            "decimal": ["numeric", "decimal", "double precision", "real", "float8", "float4"],
            "boolean": ["boolean", "bool"],
            "datetime": ["timestamp without time zone", "timestamp with time zone", "timestamp", "timestamptz",
                         "text", "character varying", "varchar", "character", "char", "unknown"],
            "date": ["date", "text", "character varying", "varchar", "character", "char", "unknown"],
            "time": ["time without time zone", "time with time zone", "time", "timetz",
                     "text", "character varying", "varchar", "character", "char", "unknown"],
        }
        json_type_map = {
            "string": ["string"],
            "integer": ["number"],
            "decimal": ["number"],
            "boolean": ["boolean"],
            "datetime": ["string"],
            "date": ["string"],
            "time": ["string"],
        }
        regex_patterns = {
            "datetime": r'^\d{4}(-\d{2}(-\d{2})?)?T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$',
            "date": r'^\d{4}(-\d{2}(-\d{2})?)?$',
            "time": r'^\d{2}:\d{2}:\d{2}(\.\d+)?$',
        }

        scalar_types = scalar_type_map.get(family)
        if not scalar_types:
            logger.warning("Unknown FHIRPath type '%s' in type check, defaulting to false", fhirpath_type)
            return "false"

        json_types = json_type_map.get(family, [])

        def _format(types: list[str]) -> str:
            return ", ".join(f"'{t}'" for t in types)

        json_predicate = "true"
        if family == "integer":
            json_predicate = f"(jsonb_typeof(({expression})::jsonb) = 'number' AND (({expression})::jsonb)::text ~ '^-?[0-9]+$')"
        elif family == "decimal":
            json_predicate = f"(jsonb_typeof(({expression})::jsonb) = 'number')"
        elif family == "boolean":
            json_predicate = f"(jsonb_typeof(({expression})::jsonb) = 'boolean')"
        elif family in regex_patterns:
            pattern = regex_patterns[family].replace("'", "''")
            json_predicate = (
                "jsonb_typeof(({expr})::jsonb) = 'string' AND "
                "btrim((({expr})::jsonb)::text, '\"') ~ '{pat}'"
            ).format(expr=expression, pat=pattern)
        else:
            if json_types:
                json_predicate = f"jsonb_typeof(({expression})::jsonb) = '{json_types[0]}'"

        json_branch = "false"
        if json_types:
            json_branch = (
                f"CASE WHEN pg_typeof({expression})::text IN ('json', 'jsonb') "
                f"THEN {json_predicate} ELSE false END"
            )

        scalar_predicate = "true"
        if family == "integer":
            scalar_predicate = (
                f"({expression})::text ~ '^-?[0-9]+$' OR "
                f"pg_typeof({expression})::text IN ('integer', 'bigint', 'smallint', 'int', 'int2', 'int4', 'int8')"
            )
        elif family == "decimal":
            scalar_predicate = "true"
        elif family == "boolean":
            scalar_predicate = "true"
        elif family in regex_patterns:
            pattern = regex_patterns[family].replace("'", "''")
            string_types = ["text", "character varying", "varchar", "character", "char", "unknown"]
            typed_types = [t for t in scalar_types if t not in string_types]
            parts = []
            if typed_types:
                parts.append(f"pg_typeof({expression})::text IN ({_format(typed_types)})")
            string_check = (
                f"(pg_typeof({expression})::text IN ({_format(string_types)}) "
                f"AND ({expression})::text ~ '{pattern}')"
            )
            parts.append(string_check)
            scalar_predicate = " OR ".join(parts)

        scalar_branch = (
            f"CASE WHEN pg_typeof({expression})::text IN ({_format(scalar_types)}) "
            f"THEN {scalar_predicate} ELSE false END"
        )

        # Return NULL when input is NULL to propagate empty collections
        # SP-102-003: When is() is called on a non-existent field (NULL),
        # returning NULL instead of false ensures the row is filtered out,
        # producing an empty result set as expected by FHIRPath semantics.
        return (
            f"CASE "
            f"WHEN {expression} IS NULL THEN NULL "
            f"WHEN pg_typeof({expression})::text IN ('json', 'jsonb') THEN {json_branch} "
            f"ELSE {scalar_branch} "
            f"END"
        )

    def generate_type_cast(self, expression: str, target_type: str) -> str:
        """Generate SQL for type casting (as() operation) in PostgreSQL.

        Uses PostgreSQL's casting syntax and exception handling to safely cast an 
        expression to a specific type. Returns the casted value if successful, 
        or null if the cast fails.

        This is a thin dialect method containing ONLY PostgreSQL syntax. Type mapping
        from FHIRPath types is handled in this method as part of syntax adaptation.

        Args:
            expression: SQL expression to cast
            target_type: FHIRPath type name (e.g., "DateTime", "Integer", "String")

        Returns:
            PostgreSQL SQL expression that performs the type cast

        Example:
            expression='123', target_type='Integer'
            → (123)::INTEGER

            expression='2024-01-01', target_type='DateTime'
            → (2024-01-01)::TIMESTAMP

        Note:
            Uses PostgreSQL's :: casting syntax with exception handling.
            PostgreSQL type names: INTEGER, TEXT, NUMERIC, BOOLEAN, TIMESTAMP, DATE, TIME.
        """
        # Map FHIRPath types to PostgreSQL type names (uppercase for consistency)
        # This mapping is part of syntax adaptation, not business logic
        type_map = {
            "string": "TEXT",
            "integer": "INTEGER",
            "decimal": "NUMERIC",
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMP",
            "date": "DATE",
            "time": "TIME",
            "uri": "TEXT",
            "code": "TEXT",
            "id": "TEXT",
        }

        normalized_type = target_type.lower() if target_type else ""

        # Handle primitive subtypes (e.g., string1, code1, integer1)
        # These should be mapped to their base types
        base_type = normalized_type
        if base_type.endswith('1'):
            # Strip the '1' suffix to get the base type
            base_type = base_type[:-1]

        pg_type = type_map.get(base_type)

        if pg_type is None:
            # Unknown FHIRPath type - return NULL
            # SP-110-003: Unknown FHIRPath types should fail at execution time
            # Generate SQL that will cause a conversion error
            invalid_type_name = target_type.replace("-", "_").upper()
            return f"({expression})::INVALID_FHIR_TYPE_{invalid_type_name}"

        # Generate type casting SQL using PostgreSQL's :: casting syntax
        # Use a function to handle casting safely (returns NULL on failure)
        return f"""(
            CASE
                WHEN {expression} IS NULL THEN NULL
                ELSE
                    CASE
                        WHEN '{pg_type}' = 'TEXT' THEN ({expression})::TEXT
                        WHEN '{pg_type}' = 'INTEGER' THEN
                            CASE WHEN ({expression})::text ~ '^-?[0-9]+$' THEN ({expression})::INTEGER ELSE NULL END
                        WHEN '{pg_type}' = 'NUMERIC' THEN
                            CASE WHEN ({expression})::text ~ '^-?[0-9]*\.?[0-9]+$' THEN ({expression})::NUMERIC ELSE NULL END
                        WHEN '{pg_type}' = 'BOOLEAN' THEN
                            CASE WHEN ({expression})::text IN ('true', 'false', 't', 'f', '1', '0') THEN ({expression})::BOOLEAN ELSE NULL END
                        WHEN '{pg_type}' = 'TIMESTAMP' THEN
                            CASE WHEN ({expression})::text ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}' THEN ({expression})::TIMESTAMP ELSE NULL END
                        WHEN '{pg_type}' = 'DATE' THEN
                            CASE WHEN ({expression})::text ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}' THEN ({expression})::DATE ELSE NULL END
                        WHEN '{pg_type}' = 'TIME' THEN
                            CASE WHEN ({expression})::text ~ '^[0-9]{{2}}:[0-9]{{2}}:[0-9]{{2}}' THEN ({expression})::TIME ELSE NULL END
                        ELSE NULL
                    END
            END
        )"""

    def generate_collection_type_filter(self, expression: str, target_type: str) -> str:
        """Generate SQL for collection type filtering (ofType() operation) in PostgreSQL."""
        normalized = target_type.lower() if target_type else ""
        if not normalized:
            return f"COALESCE(({expression})::jsonb, '[]'::jsonb)"

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
            "string": "string",
            "integer": "number",
            "decimal": "number",
            "boolean": "boolean",
            "datetime": "string",
            "date": "string",
            "time": "string",
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
            json_array_expr = f"COALESCE(({expression})::jsonb, '[]'::jsonb)"
            escaped_type = target_type.replace("'", "''")
            elem_alias = "elem"
            return (
                f"(SELECT jsonb_agg(jsonb_extract_path_text({elem_alias}, '{{}}')) "
                f"FROM jsonb_array_elements({json_array_expr}) AS {elem_alias} "
                f"WHERE jsonb_extract_path_text({elem_alias}, '{{resourceType}}') = '{escaped_type}')"
            )

        json_value_type = value_type_map.get(family)
        if not json_value_type:
            logger.warning(
                "Type '%s' cannot be filtered in PostgreSQL ofType() (unsupported family '%s'), returning empty array",
                target_type,
                family,
            )
            return "'[]'::jsonb"

        elem_alias = "elem"
        json_array_expr = f"COALESCE(({expression})::jsonb, '[]'::jsonb)"

        if family == "integer":
            condition = (
                f"jsonb_typeof({elem_alias}) = 'number' "
                f"AND {elem_alias}::text ~ '^-?[0-9]+$'"
            )
        elif family == "decimal":
            condition = f"jsonb_typeof({elem_alias}) = 'number'"
        elif family == "boolean":
            condition = f"jsonb_typeof({elem_alias}) = 'boolean'"
        elif family in regex_patterns:
            pattern = regex_patterns[family].replace("'", "''")
            condition = (
                f"jsonb_typeof({elem_alias}) = 'string' "
                f"AND btrim({elem_alias}::text, '\"') ~ '{pattern}'"
            )
        else:
            condition = f"jsonb_typeof({elem_alias}) = '{json_value_type}'"

        return (
            f"(SELECT COALESCE(jsonb_agg({elem_alias}), '[]'::jsonb) "
            f"FROM jsonb_array_elements({json_array_expr}) AS {elem_alias} "
            f"WHERE {condition})"
        )

    def filter_extension_by_url(self, extensions_expr: str, url: str) -> str:
        """Filter extension array by URL using PostgreSQL JSONB functions."""
        escaped_url = url.replace("'", "''")
        return f"""(
            SELECT COALESCE(jsonb_agg(ext_elem), '[]'::jsonb)
            FROM jsonb_array_elements(COALESCE({extensions_expr}, '[]'::jsonb)) AS ext_elem
            WHERE COALESCE(ext_elem->>'url', '') = '{escaped_url}'
        )"""

    def extract_extension_values(self, extensions_expr: str) -> str:
        """Extract value[x] payloads from extension objects in PostgreSQL."""
        value_fields = [
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
        coalesce_args = ", ".join([f"ext_elem->'{field}'" for field in value_fields] + ["NULL::jsonb"])
        value_expr = f"COALESCE({coalesce_args})"
        return f"""(
            SELECT COALESCE(jsonb_agg(val), '[]'::jsonb)
            FROM (
                SELECT {value_expr} AS val
                FROM jsonb_array_elements(COALESCE({extensions_expr}, '[]'::jsonb)) AS ext_elem
            ) AS extracted
            WHERE val IS NOT NULL
        )"""

    def project_json_array(self, array_expr: str, path_components: List[str]) -> str:
        """Project JSON array elements along a nested path in PostgreSQL."""
        if not path_components:
            return array_expr

        def build_access(components: List[str]) -> str:
            parts: list[str] = []
            for comp in components:
                if not comp:
                    continue
                if comp.startswith("[") and comp.endswith("]"):
                    index = comp[1:-1]
                    if index.isdigit():
                        parts.append(f"->{index}")
                    else:
                        parts.append(f"->'{comp}'")
                else:
                    parts.append(f"->'{comp}'")
            return "".join(parts)

        access_chain = build_access(path_components)
        return f"""(
            SELECT COALESCE(jsonb_agg(elem{access_chain}), '[]'::jsonb)
            FROM jsonb_array_elements(COALESCE({array_expr}, '[]'::jsonb)) AS elem
        )"""

    def generate_truthiness_type_check(self, value_var: str, elem_var: str) -> str:
        """Generate SQL for FHIRPath truthiness evaluation - PostgreSQL syntax.

        PostgreSQL-specific implementation using jsonb_typeof() for type detection.
        The FHIRPath truthiness rules are part of the specification and are
        identical across all dialects.

        Args:
            value_var: Not used in PostgreSQL (kept for interface compatibility)
            elem_var: Variable name for jsonb_array_elements() context (default: "elem")

        Returns:
            SQL CASE expression implementing FHIRPath truthiness rules
        """
        # FHIRPath truthiness rules (from specification):
        # - Strings: empty=false, non-empty=true
        # - Numbers (integer, number): 0=false, non-zero=true
        # - Booleans: actual value
        # - null: false
        # - Arrays/Objects (array, object): true (non-empty)
        return (f"CASE WHEN jsonb_typeof({elem_var}) = 'string' THEN LENGTH({elem_var}) > 0 "
                f"WHEN jsonb_typeof({elem_var}) = 'integer' OR jsonb_typeof({elem_var}) = 'number' THEN CAST({elem_var} AS DOUBLE PRECISION) <> 0 "
                f"WHEN jsonb_typeof({elem_var}) = 'boolean' THEN ({elem_var}::text)::boolean "
                f"WHEN jsonb_typeof({elem_var}) = 'null' THEN FALSE "
                f"ELSE TRUE END")

    def generate_all_true(self, collection_expr: str) -> str:
        """Generate SQL for allTrue() using BOOL_AND aggregate.

        Returns TRUE if all elements are TRUE. Empty collections return TRUE (vacuous truth).
        Uses COALESCE to handle empty collections and NULL values are ignored by BOOL_AND.

        Uses centralized FHIRPath truthiness rules via generate_truthiness_type_check().
        """
        truthiness = self.generate_truthiness_type_check("value", "elem")
        return f"COALESCE((SELECT BOOL_AND({truthiness}) FROM jsonb_array_elements({collection_expr}) AS elem), TRUE)"

    def generate_any_true(self, collection_expr: str) -> str:
        """Generate SQL for anyTrue() using BOOL_OR aggregate.

        Returns TRUE if any element is TRUE. Empty collections return FALSE.
        Uses COALESCE to handle empty collections and NULL values are ignored by BOOL_OR.

        Uses centralized FHIRPath truthiness rules via generate_truthiness_type_check().
        """
        truthiness = self.generate_truthiness_type_check("value", "elem")
        return f"COALESCE((SELECT BOOL_OR({truthiness}) FROM jsonb_array_elements({collection_expr}) AS elem), FALSE)"

    def generate_all_false(self, collection_expr: str) -> str:
        """Generate SQL for allFalse() using BOOL_AND(NOT value).

        Returns TRUE if all elements are FALSE. Empty collections return TRUE (vacuous truth).
        Implemented as BOOL_AND on negated values.

        Uses centralized FHIRPath truthiness rules via generate_truthiness_type_check().
        """
        truthiness = self.generate_truthiness_type_check("value", "elem")
        return f"COALESCE((SELECT BOOL_AND(NOT {truthiness}) FROM jsonb_array_elements({collection_expr}) AS elem), TRUE)"

    def generate_any_false(self, collection_expr: str) -> str:
        """Generate SQL for anyFalse() using BOOL_OR(NOT value).

        Returns TRUE if any element is FALSE. Empty collections return FALSE.
        Implemented as BOOL_OR on negated values.

        Uses centralized FHIRPath truthiness rules via generate_truthiness_type_check().
        """
        truthiness = self.generate_truthiness_type_check("value", "elem")
        return f"COALESCE((SELECT BOOL_OR(NOT {truthiness}) FROM jsonb_array_elements({collection_expr}) AS elem), FALSE)"

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

        PostgreSQL uses jsonb_array_elements() with WITH ORDINALITY, which returns
        (value, ordinality) where ordinality is 1-based. For 0-based indexing, the
        translator must use (ordinality - 1).

        Args:
            array_expr: Expression that produces a JSON array
            enum_alias: Table alias for the enumeration table
            value_col: Column name for the value (default: "value")
            index_col: Column name for the index/key (default: "key")

        Returns:
            SQL LATERAL clause string

        Example:
            generate_lateral_json_enumeration("resource->'name'", "enum_table", "value", "key")
            → "LATERAL jsonb_array_elements(resource->'name') WITH ORDINALITY AS enum_table(value, ordinality)"

        Note:
            The returned SQL uses 'ordinality' as the column name regardless of index_col
            parameter. The translator must map this to the desired index column name
            (typically "ordinality - 1" for 0-based indexing).
        """
        # PostgreSQL uses jsonb_array_elements() with WITH ORDINALITY
        # The column order is (value, ordinality) where ordinality is 1-based
        return f"LATERAL jsonb_array_elements({array_expr}) WITH ORDINALITY AS {enum_alias}({value_col}, ordinality)"

    # Encoding and decoding functions

    def generate_base64_encode(self, expression: str) -> str:
        """Generate SQL for base64 encoding using PostgreSQL's encode function."""
        return f"encode({expression}::bytea, 'base64')"

    def generate_base64_decode(self, expression: str) -> str:
        """Generate SQL for base64 decoding using PostgreSQL's decode function."""
        return f"decode({expression}, 'base64')::text"

    def generate_hex_encode(self, expression: str) -> str:
        """Generate SQL for hex encoding using PostgreSQL's encode function."""
        return f"encode({expression}::bytea, 'hex')"

    def generate_hex_decode(self, expression: str) -> str:
        """Generate SQL for hex decoding using PostgreSQL's decode function."""
        return f"decode({expression}, 'hex')::text"

    def generate_urlbase64_encode(self, expression: str) -> str:
        """Generate SQL for URL-safe base64 encoding.

        URL-safe base64 replaces '+' with '-' and '/' with '_'.
        Also removes trailing '=' padding.
        """
        # PostgreSQL: encode then replace + with - and / with _, then remove padding
        return f"rtrim(replace(replace(encode({expression}::bytea, 'base64'), '+', '-'), '/', '_'), '=')"

    def generate_urlbase64_decode(self, expression: str) -> str:
        """Generate SQL for URL-safe base64 decoding.

        First restore the replaced characters, then decode.
        """
        # PostgreSQL: restore + and /, add padding if needed, then decode
        return f"decode(replace(replace({expression}, '-', '+'), '_', '/'), 'base64')::text"

    def generate_html_escape(self, expression: str) -> str:
        """Generate SQL for HTML escaping in PostgreSQL.

        Escapes &, <, >, ", ' characters.
        Order matters: escape & first to avoid double-escaping.
        """
        # PostgreSQL uses regexp_replace for character escaping
        return f"regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace({expression}, '&', '&amp;', 'g'), '<', '&lt;', 'g'), '>', '&gt;', 'g'), '\"', '&quot;', 'g'), '''', '&apos;', 'g')"

    def generate_json_escape(self, expression: str) -> str:
        """Generate SQL for JSON escaping in PostgreSQL.

        Escapes quotes and backslashes.
        """
        # JSON escaping: escape backslash first, then quotes
        return f"replace(replace({expression}, '\\\\', '\\\\\\\\'), '\"', '\\\\\"')"

    def generate_html_unescape(self, expression: str) -> str:
        """Generate SQL for HTML unescaping in PostgreSQL.

        Unescapes &amp;, &lt;, &gt;, &quot;, &apos;, &#39;.
        Order matters for longest matches first.
        """
        # PostgreSQL uses regexp_replace for character unescaping
        # Handle numeric entity &#39; first, then named entities
        return f"regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace({expression}, '&amp;', '&', 'g'), '&lt;', '<', 'g'), '&gt;', '>', 'g'), '&quot;', '\"', 'g'), '&apos;', '''', 'g')"

    def generate_json_unescape(self, expression: str) -> str:
        """Generate SQL for JSON unescaping in PostgreSQL.

        Unescapes escaped quotes and backslashes.
        Order: unescape \\\" first, then \\\\.
        """
        # Reverse of JSON escape: unescape quotes first, then backslashes
        return f"replace(replace({expression}, '\\\\\"', '\"'), '\\\\\\\\', '\\\\')"

    def generate_array_sort(self, array_expr: str, ascending: bool = True, element_type: Optional[str] = None) -> str:
        """Generate SQL for sorting array elements in PostgreSQL.

        PostgreSQL doesn't have a native array_sort function, so we need to use
        array_agg with ORDER BY on unnested elements.

        Args:
            array_expr: SQL expression for the array to sort
            ascending: True for ascending order, False for descending
            element_type: Optional type hint (not used in PostgreSQL as unnest handles types)
        """
        if ascending:
            return f"(SELECT array_agg(x ORDER BY x) FROM unnest({array_expr}) AS x)"
        else:
            return f"(SELECT array_agg(x ORDER BY x DESC) FROM unnest({array_expr}) AS x)"

    def generate_json_descendants(self, json_expr: str) -> str:
        """Generate SQL for getting all descendant elements of a JSON node.

        Returns a JSON array containing all descendant elements recursively.

        For PostgreSQL, we use a recursive CTE with jsonb_array_elements and
        jsonb_each to traverse the JSON tree.
        """
        # PostgreSQL recursive CTE approach for descendants
        # This creates a recursive query that traverses all nested JSON structures
        return f"""
            (WITH RECURSIVE descendants AS (
                -- Base case: start with current node's direct children
                SELECT key, value FROM jsonb_each({json_expr}::jsonb)
                UNION ALL
                -- Recursive case: traverse nested objects/arrays
                SELECT d.key, d.value
                FROM descendants c
                CROSS JOIN jsonb_each(CASE WHEN jsonb_typeof(c.value) IN ('object', 'array') THEN c.value ELSE NULL END) d
            )
            SELECT jsonb_agg(value) FROM descendants)
        """.strip()

    def generate_decimal_precision(self, decimal_expr: str) -> str:
        """Generate SQL to count decimal places in a decimal number.

        For PostgreSQL, we convert to string and count characters after decimal point.
        """
        # Convert to string and count characters after decimal point
        # Pattern: find position of '.', then calculate length of substring after it
        return f"""
            CASE
                WHEN {decimal_expr}::VARCHAR ~ '^(-?[0-9]+\\.)?[0-9]+$'
                THEN LENGTH(SUBSTRING({decimal_expr}::VARCHAR, STRPOS({decimal_expr}::VARCHAR, '.') + 1))
                ELSE 0
            END
        """.strip()

    def generate_comparable_check(self, base_expr: str, arg_expr: str) -> str:
        """Generate SQL to check if two quantities are comparable.

        Simplified implementation: check if both have units and units are equal.
        A full implementation would use UCUM dimensional analysis.
        """
        # Extract units from both quantities using ->> operator for JSONB
        base_unit = f"{base_expr}->>'unit'"
        arg_unit = f"{arg_expr}->>'unit'"

        # Both must have units and units must be compatible (simplified: equal)
        # For now, we just check if units are equal (not full dimensional analysis)
        return f"""
            ({base_unit} IS NOT NULL AND {arg_unit} IS NOT NULL AND {base_unit} = {arg_unit})
        """.strip()
