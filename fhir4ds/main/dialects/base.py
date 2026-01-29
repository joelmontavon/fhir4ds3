"""
Abstract base class for database dialect implementations.

This module defines the interface that all database dialects must implement
to support FHIR data operations with metadata-aware SQL generation.
Following the thin dialect architecture: business logic in FHIRPath evaluator,
only syntax differences in database dialects.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class DatabaseDialect(ABC):
    """
    Abstract base class for database dialect implementations.

    Provides the interface for database-specific SQL generation while maintaining
    the thin dialect architecture principle: business logic belongs in the
    FHIRPath evaluator, dialects contain only syntax differences.
    """

    def __init__(self):
        """Initialize dialect with common properties."""
        self.name = self.__class__.__name__.replace('Dialect', '').upper()
        self.supports_jsonb = False
        self.supports_json_functions = True
        self.json_type = "JSON"
        self.cast_syntax = "::"
        self.quote_char = '"'

    # Core database operations

    @abstractmethod
    def get_connection(self) -> Any:
        """Get the underlying database connection."""
        pass

    @abstractmethod
    def execute_query(self, sql: str) -> Any:
        """Execute a query and return raw results."""
        pass

    # JSON extraction methods with metadata awareness

    @abstractmethod
    def extract_json_field(self, column: str, path: str) -> str:
        """Extract JSON field as text for string operations."""
        pass

    @abstractmethod
    def extract_json_object(self, column: str, path: str) -> str:
        """Extract JSON object preserving structure."""
        pass

    @abstractmethod
    def check_json_exists(self, column: str, path: str) -> str:
        """Check if JSON path exists."""
        pass

    @abstractmethod
    def extract_primitive_value(self, column: str, path: str) -> str:
        """Extract FHIR primitive type value, handling both simple and complex representations.

        FHIR primitive types can be stored in two ways:
        1. Simple: {"gender": "male"}
        2. Complex (with extensions): {"gender": {"value": "male", "extension": [...]}}

        This method generates SQL that extracts just the primitive value, using COALESCE
        to handle both representations transparently.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path to the primitive field (e.g., '$.birthDate', '$.gender')

        Returns:
            Database-specific SQL expression using COALESCE to extract primitive value

        Example:
            DuckDB: COALESCE(
                json_extract_string(resource, '$.birthDate.value'),
                json_extract_string(resource, '$.birthDate')
            )
            PostgreSQL: COALESCE(
                resource->'birthDate'->>'value',
                resource->>'birthDate'
            )
        """
        pass

    # Type-aware JSON extraction methods for SQL-on-FHIR ViewDefinitions
    # These methods support the thin dialect architecture by isolating database syntax

    @abstractmethod
    def extract_json_string(self, column: str, path: str) -> str:
        """Extract JSON field as string with database-specific syntax.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.id', '$.name[0].family')

        Returns:
            Database-specific SQL expression for string extraction

        Example:
            DuckDB: json_extract_string(resource, '$.id')
            PostgreSQL: resource->>'id'
        """
        pass

    @abstractmethod
    def extract_json_integer(self, column: str, path: str) -> str:
        """Extract JSON field as integer with database-specific syntax.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.age', '$.value')

        Returns:
            Database-specific SQL expression for integer extraction

        Example:
            DuckDB: json_extract(resource, '$.age')::INTEGER
            PostgreSQL: (resource->'age')::integer
        """
        pass

    @abstractmethod
    def extract_json_decimal(self, column: str, path: str) -> str:
        """Extract JSON field as decimal with database-specific syntax.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.value', '$.price')

        Returns:
            Database-specific SQL expression for decimal extraction

        Example:
            DuckDB: json_extract(resource, '$.value')::DECIMAL
            PostgreSQL: (resource->'value')::decimal
        """
        pass

    @abstractmethod
    def extract_json_boolean(self, column: str, path: str) -> str:
        """Extract JSON field as boolean with database-specific syntax.

        Args:
            column: Column name containing JSON (usually 'resource')
            path: JSON path (e.g., '$.active', '$.deceased')

        Returns:
            Database-specific SQL expression for boolean extraction

        Example:
            DuckDB: json_extract(resource, '$.active')::BOOLEAN
            PostgreSQL: (resource->'active')::boolean
        """
        pass

    @abstractmethod
    def get_json_type(self, column: str) -> str:
        """Get JSON value type."""
        pass

    @abstractmethod
    def get_json_array_length(self, column: str, path: str = None) -> str:
        """Get JSON array length."""
        pass

    # Array and collection operations

    @abstractmethod
    def unnest_json_array(self, column: str, path: str, alias: str) -> str:
        """Generate SQL for unnesting JSON array elements.

        This method generates database-specific SQL for unnesting (flattening)
        a JSON array into individual rows. This is critical for the where()
        function translation, which filters array elements using LATERAL UNNEST.

        Args:
            column: Source column or table name containing JSON
            path: JSON path to the array (e.g., '$.name', '$.address')
            alias: Alias name for the unnested array elements

        Returns:
            Database-specific SQL fragment for array unnesting

        Example:
            DuckDB: UNNEST(json_extract(resource, '$.name')) AS name_item
            PostgreSQL: jsonb_array_elements(resource->'name') AS name_item
        """
        pass

    def generate_lateral_unnest(self, source_table: str, array_column: str, alias: str) -> str:
        """Generate database-specific LATERAL UNNEST clause.

        Args:
            source_table: Name of the table or CTE providing the array column.
            array_column: SQL expression that evaluates to the array being flattened.
            alias: Alias assigned to each unnested element.

        Returns:
            SQL fragment representing the database-specific LATERAL UNNEST syntax.

        Note:
            This method must not contain business logic. Implementations should
            only format the appropriate syntax for the target database.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement generate_lateral_unnest()"
        )

    @abstractmethod
    def iterate_json_array(self, column: str, path: str) -> str:
        """Iterate over JSON array elements."""
        pass

    @abstractmethod
    def aggregate_to_json_array(self, expression: str) -> str:
        """Aggregate values into JSON array."""
        pass

    def prepare_unnest_source(self, array_expr: str) -> str:
        """Prepare array expression for UNNEST operations."""
        return array_expr

    @abstractmethod
    def create_json_array(self, *args) -> str:
        """Create JSON array from arguments."""
        pass

    @abstractmethod
    def create_json_object(self, *args) -> str:
        """Create JSON object from key-value pairs."""
        pass

    @abstractmethod
    def json_array_contains(self, array_expr: str, scalar_expr: str) -> str:
        """Return SQL expression that evaluates whether JSON array contains scalar."""
        pass

    # String operations

    @abstractmethod
    def string_concat(self, left: str, right: str) -> str:
        """Concatenate strings."""
        pass

    @abstractmethod
    def substring(self, expression: str, start: str, length: str) -> str:
        """Extract substring."""
        pass

    @abstractmethod
    def split_string(self, expression: str, delimiter: str) -> str:
        """Split string into array."""
        pass

    @abstractmethod
    def generate_string_join(self, collection_expr: str, delimiter_expr: str, is_json_collection: bool) -> str:
        """Generate SQL for joining string collections.

        Args:
            collection_expr: SQL expression representing the collection to join
            delimiter_expr: SQL expression for the delimiter string
            is_json_collection: True if collection_expr is a JSON value, False if native array/list
        """
        pass

    @abstractmethod
    def generate_case_conversion(self, string_expr: str, case_type: str) -> str:
        """Generate SQL for case conversion (upper/lower).

        Returns string expression with case converted. This is a thin dialect
        method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            case_type: Type of conversion ('upper' or 'lower')

        Returns:
            SQL expression for case conversion

        Example:
            DuckDB: UPPER(string_expr) or LOWER(string_expr)
            PostgreSQL: UPPER(string_expr) or LOWER(string_expr)

        Note:
            - Both databases use standard SQL UPPER/LOWER functions
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    @abstractmethod
    def generate_trim(self, string_expr: str) -> str:
        """Generate SQL for whitespace trimming.

        Returns string expression with leading and trailing whitespace removed.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string

        Returns:
            SQL expression for trimming whitespace

        Example:
            DuckDB: TRIM(string_expr)
            PostgreSQL: TRIM(string_expr)

        Note:
            - Both databases use standard SQL TRIM function
            - Removes leading and trailing whitespace
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    # Type conversion operations

    @abstractmethod
    def try_cast(self, expression: str, target_type: str) -> str:
        """Safe type conversion returning NULL on failure."""
        pass

    @abstractmethod
    def cast_to_timestamp(self, expression: str) -> str:
        """Cast to timestamp type."""
        pass

    @abstractmethod
    def cast_to_time(self, expression: str) -> str:
        """Cast to time type."""
        pass

    # Mathematical functions

    @abstractmethod
    def cast_to_double(self, expression: str) -> str:
        """Cast expression to double precision for numeric operations."""
        pass

    @abstractmethod
    def is_finite(self, expression: str) -> str:
        """Return SQL boolean expression that is true when expression is finite."""
        pass

    @abstractmethod
    def generate_math_function(self, function_name: str, *args: str) -> str:
        """Generate mathematical function SQL."""
        pass

    @abstractmethod
    def generate_power_operation(self, base_expr: str, exponent_expr: str) -> str:
        """Generate power operation SQL."""
        pass

    @abstractmethod
    def generate_decimal_division(self, numerator: str, denominator: str) -> str:
        """Generate SQL for decimal division (/) operator."""
        pass

    @abstractmethod
    def generate_integer_division(self, numerator: str, denominator: str) -> str:
        """Generate SQL for integer division (div) operator."""
        pass

    @abstractmethod
    def generate_modulo(self, left: str, right: str) -> str:
        """Generate SQL for modulo (mod) operator."""
        pass

    # String functions

    @abstractmethod
    def generate_string_function(self, function_name: str, *args: str) -> str:
        """Generate string function SQL.

        Args:
            function_name: Name of the string function (substring, indexOf, length, replace)
            *args: Function arguments (varies by function)

        Returns:
            Database-specific SQL for the string function
        """
        pass

    @abstractmethod
    def generate_regex_match(self, string_expr: str, regex_pattern: str) -> str:
        """Generate regex matching SQL.

        Returns boolean expression indicating if string matches regex pattern.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern (string literal or variable)

        Returns:
            SQL expression returning boolean

        Example:
            DuckDB: regexp_matches(string_expr, regex_pattern)
            PostgreSQL: (string_expr ~ regex_pattern)

        Note: Both databases handle NULL consistently (NULL input → NULL output).
        """
        pass

    @abstractmethod
    def generate_regex_replace(self, string_expr: str, regex_pattern: str, substitution: str) -> str:
        """Generate regex replacement SQL.

        Returns string expression with all regex matches replaced by substitution.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            regex_pattern: SQL expression for regex pattern (string literal or variable)
            substitution: SQL expression for replacement string (can include capture group references)

        Returns:
            SQL expression returning string with replacements applied

        Example:
            DuckDB: regexp_replace(string_expr, regex_pattern, substitution, 'g')
            PostgreSQL: regexp_replace(string_expr, regex_pattern, substitution, 'g')

        Note:
            - Both databases support global replacement with 'g' flag
            - Both support capture group references ($1, $2, etc.)
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    @abstractmethod
    def generate_substring_check(self, string_expr: str, substring: str) -> str:
        """Generate substring check SQL.

        Returns boolean expression indicating if string contains substring.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            substring: SQL expression for substring to find

        Returns:
            SQL expression returning boolean (true if substring found)

        Example:
            DuckDB: (string_expr LIKE '%' || substring || '%')
            PostgreSQL: (string_expr LIKE '%' || substring || '%')

        Note:
            - Case-sensitive matching
            - Empty substring returns true
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    @abstractmethod
    def generate_membership_test(self, collection_expr: str, value_expr: str) -> str:
        """Generate membership test SQL (contains operator).

        Returns boolean expression indicating if value is in collection.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            collection_expr: SQL expression evaluating to collection (JSON array)
            value_expr: SQL expression for value to find

        Returns:
            SQL expression returning boolean (true if value found in collection)

        Example:
            DuckDB: EXISTS (SELECT 1 FROM json_each(collection_expr) WHERE value = value_expr)
            PostgreSQL: EXISTS (SELECT 1 FROM jsonb_array_elements(collection_expr) WHERE value = value_expr)

        Note:
            - Uses equality comparison
            - Empty collection returns false
            - NULL handling: NULL collection → NULL output
        """
        pass

    @abstractmethod
    def generate_prefix_check(self, string_expr: str, prefix: str) -> str:
        """Generate prefix check SQL (startsWith).

        Returns boolean expression indicating if string starts with prefix.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            prefix: SQL expression for prefix to find

        Returns:
            SQL expression returning boolean (true if string starts with prefix)

        Example:
            DuckDB: (string_expr LIKE prefix || '%')
            PostgreSQL: (string_expr LIKE prefix || '%')

        Note:
            - Case-sensitive matching
            - Empty prefix returns true
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    @abstractmethod
    def generate_suffix_check(self, string_expr: str, suffix: str) -> str:
        """Generate suffix check SQL (endsWith).

        Returns boolean expression indicating if string ends with suffix.
        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string
            suffix: SQL expression for suffix to find

        Returns:
            SQL expression returning boolean (true if string ends with suffix)

        Example:
            DuckDB: (string_expr LIKE '%' || suffix)
            PostgreSQL: (string_expr LIKE '%' || suffix)

        Note:
            - Case-sensitive matching
            - Empty suffix returns true
            - NULL handling: NULL input → NULL output (both databases)
        """
        pass

    @abstractmethod
    def generate_char_array(self, string_expr: str) -> str:
        """Generate SQL to split string into character array (toChars).

        Returns array expression where each element is a single character
        from the input string. This is a thin dialect method - contains
        ONLY syntax differences.

        Args:
            string_expr: SQL expression evaluating to string

        Returns:
            SQL expression returning array of single-character strings

        Example:
            'hello' → ['h', 'e', 'l', 'l', 'o']
            'ab' → ['a', 'b']
            '' → []

        Note:
            - Empty string returns empty array
            - NULL handling: NULL input → empty array (both databases)
            - Each character becomes a separate array element
        """
        pass

    # Date/time operations

    @abstractmethod
    def generate_current_timestamp(self) -> str:
        """Generate current timestamp SQL."""
        pass

    @abstractmethod
    def generate_current_date(self) -> str:
        """Generate current date SQL."""
        pass

    @abstractmethod
    def generate_current_time(self) -> str:
        """Generate current time SQL."""
        pass

    @abstractmethod
    def generate_date_diff(self, unit: str, start_date: str, end_date: str) -> str:
        """Generate date difference SQL."""
        pass

    @abstractmethod
    def generate_date_literal(self, date_value: str) -> str:
        """Generate SQL date literal.

        Args:
            date_value: Date string in ISO format (YYYY-MM-DD)

        Returns:
            Database-specific SQL date literal

        Example:
            @2024-01-01 → DATE '2024-01-01'
        """
        pass

    @abstractmethod
    def generate_datetime_literal(self, datetime_value: str) -> str:
        """Generate SQL datetime literal.

        Args:
            datetime_value: DateTime string in ISO format (YYYY-MM-DDTHH:MM:SS)

        Returns:
            Database-specific SQL datetime literal

        Example:
            @2024-01-01T12:30:00 → TIMESTAMP '2024-01-01 12:30:00'
        """
        pass

    @abstractmethod
    def generate_time_literal(self, time_value: str) -> str:
        """Generate SQL time literal.

        Args:
            time_value: Time string in ISO format (HH:MM[:SS[.ffffff]])

        Returns:
            Database-specific SQL time literal

        Example:
            @T12:30 → TIME '12:30'
        """
        pass

    @abstractmethod
    def generate_comparison(self, left_expr: str, operator: str, right_expr: str) -> str:
        """Generate SQL comparison operation.

        Args:
            left_expr: Left operand SQL expression
            operator: Comparison operator (=, !=, <, >, <=, >=)
            right_expr: Right operand SQL expression

        Returns:
            Database-specific SQL comparison expression

        Example:
            ('age', '>=', '18') → '(age >= 18)'
        """
        pass

    # Type casting methods for comparison operations

    @abstractmethod
    def safe_cast_to_decimal(self, expression: str) -> str:
        """Safely cast expression to DECIMAL, returning NULL on failure.

        Used when comparing JSON-extracted VARCHAR values with numeric literals.
        Must use TRY_CAST or equivalent to avoid errors on invalid input.

        Args:
            expression: SQL expression to cast (typically VARCHAR from JSON extraction)

        Returns:
            Database-specific SQL for safe cast to DECIMAL

        Example:
            DuckDB: TRY_CAST(expr AS DECIMAL)
            PostgreSQL: (CASE WHEN expr ~ '^-?[0-9]+(\\.[0-9]+)?$' THEN expr::DECIMAL ELSE NULL END)
        """
        pass

    @abstractmethod
    def safe_cast_to_integer(self, expression: str) -> str:
        """Safely cast expression to BIGINT, returning NULL on failure.

        Used when comparing JSON-extracted VARCHAR values with integer literals.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for safe cast to BIGINT/INTEGER
        """
        pass

    @abstractmethod
    def strict_cast_to_decimal(self, expression: str) -> str:
        """Strictly cast expression to DECIMAL, throwing error on failure.

        SP-103-004: Used for type validation in comparisons. When comparing
        numeric values with incompatible types (e.g., string literals), this
        will cause a SQL execution error as expected by FHIRPath semantics.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for strict cast to DECIMAL

        Example:
            DuckDB: CAST(expr AS DECIMAL)
            PostgreSQL: expr::DECIMAL
        """
        pass

    @abstractmethod
    def strict_cast_to_integer(self, expression: str) -> str:
        """Strictly cast expression to INTEGER, throwing error on failure.

        SP-103-004: Used for type validation in comparisons. When comparing
        integer values with incompatible types (e.g., string literals), this
        will cause a SQL execution error as expected by FHIRPath semantics.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for strict cast to INTEGER

        Example:
            DuckDB: CAST(expr AS BIGINT)
            PostgreSQL: expr::BIGINT
        """
        pass

    @abstractmethod
    def safe_cast_to_date(self, expression: str) -> str:
        """Safely cast expression to DATE, returning NULL on failure.

        Used when comparing JSON-extracted VARCHAR date strings with DATE literals.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for safe cast to DATE
        """
        pass

    @abstractmethod
    def safe_cast_to_timestamp(self, expression: str) -> str:
        """Safely cast expression to TIMESTAMP, returning NULL on failure.

        Used when comparing JSON-extracted VARCHAR datetime strings with TIMESTAMP literals.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for safe cast to TIMESTAMP
        """
        pass

    @abstractmethod
    def safe_cast_to_boolean(self, expression: str) -> str:
        """Safely cast expression to BOOLEAN, returning NULL on failure.

        Used when comparing JSON-extracted VARCHAR values with boolean literals.

        Args:
            expression: SQL expression to cast

        Returns:
            Database-specific SQL for safe cast to BOOLEAN
        """
        pass

    # Aggregate functions

    @abstractmethod
    def generate_aggregate_function(self, function_name: str, expression: str,
                                  filter_condition: str = None, distinct: bool = False) -> str:
        """Generate aggregate function SQL."""
        pass

    # Collection operations

    @abstractmethod
    def generate_where_clause_filter(self, collection_expr: str, condition_sql: str) -> str:
        """Generate WHERE clause filtering for collections."""
        pass

    @abstractmethod
    def generate_select_transformation(self, collection_expr: str, transform_path: str) -> str:
        """Generate SELECT transformation for collections."""
        pass

    @abstractmethod
    def generate_collection_combine(self, first_collection: str, second_collection: str) -> str:
        """Generate collection combination SQL."""
        pass

    @abstractmethod
    def generate_collection_exclude(self, collection_expr: str, exclusion_expr: str) -> str:
        """Generate SQL for collection exclusion (remove items equal to exclusion_expr)."""
        pass

    @abstractmethod
    def wrap_json_array(self, expression: str) -> str:
        """Wrap scalar expression as single-element JSON array (syntax only)."""
        pass

    @abstractmethod
    def serialize_json_value(self, expression: str) -> str:
        """Serialize JSON value to canonical text preserving type semantics."""
        pass

    @abstractmethod
    def empty_json_array(self) -> str:
        """Return database-specific empty JSON array literal."""
        pass

    @abstractmethod
    def is_json_array(self, expression: str) -> str:
        """Return boolean SQL expression indicating if input expression is JSON array."""
        pass

    @abstractmethod
    def enumerate_json_array(self, array_expr: str, value_alias: str, index_alias: str) -> str:
        """Enumerate JSON array into rows of (index, value) - syntax only."""
        pass

    @abstractmethod
    def generate_exists_check(self, fragment: str, is_collection: bool) -> str:
        """Generate exists/empty check SQL."""
        pass

    @abstractmethod
    def generate_empty_check(self, collection_expr: str) -> str:
        """Generate empty check SQL for collections.

        Generates database-specific SQL to check if a collection is empty.
        Returns a boolean expression (true if empty, false if not empty).

        This method contains ONLY syntax differences between databases. All business
        logic is in the translator.

        Args:
            collection_expr: SQL expression representing a collection (JSON array)

        Returns:
            SQL expression that evaluates to boolean (true if collection is empty)

        Example:
            DuckDB: (json_array_length(collection) = 0)
            PostgreSQL: (jsonb_array_length(collection) = 0)

        Note:
            This is a thin dialect method - contains ONLY database syntax differences.
        """
        pass

    @abstractmethod
    def generate_boolean_not(self, expr: str) -> str:
        """Generate boolean NOT expression.

        Generates database-specific SQL for boolean negation. Returns a boolean
        expression representing the logical NOT of the input expression.

        This method contains ONLY syntax differences between databases. All business
        logic is in the translator.

        Args:
            expr: SQL expression evaluating to boolean

        Returns:
            SQL expression performing boolean negation

        Example:
            DuckDB: NOT (expression)
            PostgreSQL: NOT (expression)

        Note:
            This is a thin dialect method - contains ONLY database syntax differences.
            Both DuckDB and PostgreSQL use standard SQL NOT syntax, so implementations
            will be identical. However, we maintain the method pattern for consistency
            and future extensibility.
        """
        pass

    @abstractmethod
    def generate_all_check(self, column: str, path: str, element_alias: str, criteria_expr: str) -> str:
        """Generate universal quantifier check SQL for collections.

        Generates database-specific SQL to check if ALL elements in a collection
        satisfy a criteria expression. Returns true if all elements satisfy the
        criteria, false if any don't, and true for empty collections (vacuous truth).

        This method contains ONLY syntax differences between databases. All business
        logic is in the translator.

        Args:
            column: Source table/column name containing the JSON data
            path: JSON path to the collection/array
            element_alias: Alias for individual array elements in unnesting
            criteria_expr: SQL expression for the criteria to check (already translated)

        Returns:
            SQL expression that evaluates to boolean (true if all satisfy criteria)

        Example:
            DuckDB:
                COALESCE(
                    (SELECT bool_and(criteria_expr)
                     FROM (SELECT unnest(json_extract(column, 'path')) as element_alias)),
                    true
                )

            PostgreSQL:
                COALESCE(
                    (SELECT bool_and(criteria_expr)
                     FROM jsonb_array_elements(jsonb_extract_path(column, 'path')) as element_alias),
                    true
                )

        Note:
            - COALESCE handles empty arrays (NULL from bool_and) → returns true
            - This is a thin dialect method - contains ONLY database syntax differences
        """
        pass

    @abstractmethod
    def generate_array_skip(self, array_expr: str, skip_count: str) -> str:
        """Generate array skip/slice SQL for collections.

        Generates database-specific SQL to skip the first N elements of an array
        and return the remaining elements. Handles edge cases per FHIRPath spec:
        - If skip_count <= 0, returns entire array
        - If skip_count >= array length, returns empty array

        This method contains ONLY syntax differences between databases. All business
        logic is in the translator.

        Args:
            array_expr: SQL expression representing a JSON array
            skip_count: SQL expression for number of elements to skip (integer)

        Returns:
            SQL expression that evaluates to array with first N elements skipped

        Example:
            DuckDB:
                list_slice(array_expr, skip_count + 1, NULL)
                OR
                array_expr[skip_count + 1:]

            PostgreSQL:
                (array_expr)[skip_count + 1:]

        Note:
            - Array indices are 1-based in SQL (skip 1 means start at index 2)
            - This is a thin dialect method - contains ONLY database syntax differences
        """
        pass

    @abstractmethod
    def generate_array_take(self, array_expr: str, take_count: str) -> str:
        """Generate array take/slice SQL for collections.

        Generates database-specific SQL to take the first N elements of an array
        and return them. Handles edge cases per FHIRPath spec:
        - If take_count <= 0, returns empty array
        - If take_count >= array length, returns entire array

        This method contains ONLY syntax differences between databases. All business
        logic is in the translator.

        Args:
            array_expr: SQL expression representing a JSON array
            take_count: SQL expression for number of elements to take (integer)

        Returns:
            SQL expression that evaluates to array with first N elements

        Example:
            DuckDB:
                list_slice(array_expr, 1, take_count)
                OR
                array_expr[1:take_count]

            PostgreSQL:
                (array_expr)[1:take_count]

        Note:
            - Array indices are 1-based in SQL (take 2 means indices 1 and 2)
            - This is a thin dialect method - contains ONLY database syntax differences
        """
        pass

    @abstractmethod
    def generate_array_last(self, array_expr: str) -> str:
        """Generate SQL that returns the last element from a collection."""
        pass

    @abstractmethod
    def generate_decimal_boundary(
        self,
        base_expr: str,
        target_precision: Optional[int],
        boundary_type: str
    ) -> str:
        """Generate SQL for decimal boundary calculation."""
        pass

    @abstractmethod
    def generate_quantity_boundary(
        self,
        base_expr: str,
        target_precision: Optional[int],
        boundary_type: str
    ) -> str:
        """Generate SQL for quantity boundary calculation."""
        pass

    @abstractmethod
    def generate_temporal_boundary(
        self,
        base_expr: str,
        input_type: str,
        precision: Optional[int],
        boundary_type: str,
        has_timezone: bool
    ) -> str:
        """Generate SQL for temporal boundary calculation."""
        pass

    # Boolean operations

    @abstractmethod
    def generate_logical_combine(self, left_condition: str, operator: str, right_condition: str) -> str:
        """Generate logical condition combination SQL."""
        pass

    def generate_xor(self, left_condition: str, right_condition: str) -> str:
        """Generate XOR (exclusive or) SQL.

        XOR returns true if operands have different boolean values.
        Empty collections are treated as false.

        Truth table:
          true XOR false = true
          false XOR true = true
          true XOR true = false
          false XOR false = false

        This is a thin dialect method - contains ONLY syntax differences.

        Args:
            left_condition: Left boolean SQL expression
            right_condition: Right boolean SQL expression

        Returns:
            SQL expression performing XOR operation

        Example:
            DuckDB/PostgreSQL: ((left) OR (right)) AND NOT ((left) AND (right))

        Note:
            Both databases don't have native XOR operator, so we use the pattern:
            (a OR b) AND NOT (a AND b)

            This default implementation uses standard SQL patterns that work across
            DuckDB and PostgreSQL. Dialects can override if database-specific
            syntax is needed.
        """
        return f"(({left_condition}) OR ({right_condition})) AND NOT (({left_condition}) AND ({right_condition}))"

    @abstractmethod
    def generate_conditional_expression(self, condition: str, true_expr: str, false_expr: str) -> str:
        """Generate conditional expression SQL."""
        pass

    # Type operations

    @abstractmethod
    def generate_type_check(self, expression: str, fhirpath_type: str) -> str:
        """Generate SQL for type checking (is() operation).

        Generates database-specific SQL to check if an expression is of a specific
        FHIRPath type. Returns a boolean expression (true/false).

        This method contains ONLY syntax differences between databases. All business
        logic (type mapping, collection handling) is in the translator.

        Args:
            expression: SQL expression to check type of
            fhirpath_type: FHIRPath type name (e.g., "String", "Integer", "Boolean")

        Returns:
            SQL expression that evaluates to boolean

        Example:
            DuckDB: Uses json_type() or TRY_CAST() for type checking
            PostgreSQL: Uses jsonb_typeof() or casting with exception handling

        Note:
            This is a thin dialect method - contains ONLY database syntax differences.
            Type mapping from FHIRPath types happens in the translator.
        """
        pass

    @abstractmethod
    def generate_type_cast(self, expression: str, target_type: str) -> str:
        """Generate SQL for type casting (as() operation).

        Generates database-specific SQL to cast an expression to a specific type.
        Returns the casted value if successful, or null if the cast fails.

        This method contains ONLY syntax differences between databases. All business
        logic (type mapping, error handling) is in the translator.

        Args:
            expression: SQL expression to cast
            target_type: FHIRPath type name (e.g., "DateTime", "Integer", "String")

        Returns:
            SQL expression that performs the type cast

        Example:
            DuckDB: CAST(expression AS target_type)
            PostgreSQL: (expression)::target_type

        Note:
            This is a thin dialect method - contains ONLY database syntax differences.
            Type mapping from FHIRPath types to SQL types happens in the dialect.
        """
        pass

    @abstractmethod
    def generate_collection_type_filter(self, expression: str, target_type: str) -> str:
        """Generate SQL for collection type filtering (ofType() operation).

        Generates database-specific SQL to filter a collection to only include items
        that match the specified type. Uses array filtering with type checking.

        This method contains ONLY syntax differences between databases. All business
        logic (filtering semantics, type matching) is in the translator.

        Args:
            expression: SQL expression representing a collection (array)
            target_type: FHIRPath type name to filter by (e.g., "String", "Integer")

        Returns:
            SQL expression that filters the collection by type

        Example:
            DuckDB: list_filter(expression, x -> typeof(x) = 'INTEGER')
            PostgreSQL: (SELECT array_agg(elem) FROM unnest(expression) elem
                        WHERE pg_typeof(elem) = 'integer'::regtype)

        Note:
            This is a thin dialect method - contains ONLY database syntax differences.
            Type filtering logic and semantics are defined in FHIRPath specification.
        """
        pass

    @abstractmethod
    def filter_extension_by_url(self, extensions_expr: str, url: str) -> str:
        """Filter extension array by URL, returning matching extension objects."""
        pass

    @abstractmethod
    def extract_extension_values(self, extensions_expr: str) -> str:
        """Extract value[x] payloads from filtered extension array."""
        pass

    @abstractmethod
    def project_json_array(self, array_expr: str, path_components: List[str]) -> str:
        """Project array elements to nested JSON path, returning transformed array."""
        pass

    @abstractmethod
    def generate_all_true(self, collection_expr: str) -> str:
        """Generate SQL for allTrue() aggregate - returns TRUE if all values are TRUE."""
        pass

    @abstractmethod
    def generate_any_true(self, collection_expr: str) -> str:
        """Generate SQL for anyTrue() aggregate - returns TRUE if any value is TRUE."""
        pass

    @abstractmethod
    def generate_all_false(self, collection_expr: str) -> str:
        """Generate SQL for allFalse() aggregate - returns TRUE if all values are FALSE."""
        pass

    @abstractmethod
    def generate_any_false(self, collection_expr: str) -> str:
        """Generate SQL for anyFalse() aggregate - returns TRUE if any value is FALSE."""
        pass

    @abstractmethod
    def generate_array_to_string(self, array_expr: str, separator: str) -> str:
        """Generate SQL for combine() - joins array elements with a separator.

        Args:
            array_expr: SQL expression evaluating to an array
            separator: SQL expression for separator string

        Returns:
            SQL expression returning joined string

        Example:
            DuckDB: array_to_string(array_expr, separator)
            PostgreSQL: array_to_string(array_expr, separator)

        Note:
            - NULL array elements are skipped (not converted to empty string)
            - NULL separator defaults to empty string
            - Empty array returns empty string
        """
        pass

    @abstractmethod
    def generate_distinct(self, expression: str) -> str:
        """Generate SQL for distinct() - removes duplicates from collection.

        Args:
            expression: SQL expression evaluating to a collection

        Returns:
            SQL expression returning collection with duplicates removed

        Example:
            DuckDB: DISTINCT expression (in SELECT clause context)
            PostgreSQL: DISTINCT expression (in SELECT clause context)

        Note:
            - Preserves first occurrence order
            - NULL values are treated as duplicates of each other
            - Works with any data type
        """
        pass

    @abstractmethod
    def generate_is_distinct(self, expression: str) -> str:
        """Generate SQL for isDistinct() - checks if all elements are unique.

        Args:
            expression: SQL expression evaluating to a collection

        Returns:
            SQL expression returning boolean (TRUE if all elements unique)

        Example:
            DuckDB: (COUNT(*) = COUNT(DISTINCT expression))
            PostgreSQL: (COUNT(*) = COUNT(DISTINCT expression))

        Note:
            - Returns TRUE for empty or single-element collections
            - NULL values are treated as duplicates of each other
            - Works with any data type
        """
        pass

    # Utility methods

    def quote_identifier(self, identifier: str) -> str:
        """Quote identifier for the dialect."""
        return f"{self.quote_char}{identifier}{self.quote_char}"

    def cast_to_type(self, expression: str, target_type: str) -> str:
        """Generate type casting SQL."""
        return f"{expression}{self.cast_syntax}{target_type}"

    def supports_feature(self, feature: str) -> bool:
        """Check if dialect supports a specific feature."""
        features = {
            'jsonb': self.supports_jsonb,
            'json_functions': self.supports_json_functions,
        }
        return features.get(feature, False)
