from typing import Optional
from .exceptions import SQLGenerationError, UndefinedConstantError

class SQLGenerator:
    """
    A basic SQL generator for SQL-on-FHIR ViewDefinitions.

    Uses thin dialect architecture: database-specific SQL syntax is handled
    by dialect classes, while SQL generation logic remains database-agnostic.
    """

    def __init__(self, dialect: str = "duckdb"):
        """Initialize the SQL generator with a database dialect.

        Args:
            dialect: Database dialect name ('duckdb' or 'postgresql')
        """
        self.dialect = dialect
        self._generation_count = 0
        self._fhirpath_parser = None
        self._fhirpath_translator = None
        self._constants = {}

        # Initialize dialect instance for SQL generation
        # This follows the thin dialect architecture: syntax-only differences
        if dialect.lower() == "duckdb":
            from fhir4ds.dialects.duckdb import DuckDBDialect
            self._dialect_instance = DuckDBDialect()
        elif dialect.lower() == "postgresql":
            from fhir4ds.dialects.postgresql import PostgreSQLDialect
            # PostgreSQL requires connection string - use placeholder for now
            # In production, connection string should be provided externally
            self._dialect_instance = PostgreSQLDialect("postgresql://localhost/fhir")
        else:
            # Default to DuckDB if unknown dialect
            from fhir4ds.dialects.duckdb import DuckDBDialect
            self._dialect_instance = DuckDBDialect()

    def generate_sql(self, view_definition: dict) -> str:
        """Generate SQL from a ViewDefinition.

        Args:
            view_definition: A SQL-on-FHIR ViewDefinition.

        Returns:
            A SQL query string.
        """
        if not view_definition:
            raise SQLGenerationError("ViewDefinition is empty")

        self._generation_count += 1

        # Parse constants from ViewDefinition
        self._constants = self._parse_constants(view_definition)

        resource = view_definition.get("resource")
        if not resource:
            raise SQLGenerationError("ViewDefinition must have a resource")

        selects = view_definition.get("select")
        if not selects:
            raise SQLGenerationError("ViewDefinition must have at least one select")

        columns = []
        for select in selects:
            for column in select.get("column", []):
                path = column["path"]
                name = column["name"]
                column_type = column.get("type", "string")

                # Check if path requires FHIRPath translation (contains functions like ofType())
                # Substitute constants BEFORE checking, so FHIRPath sees the substituted values
                path_with_constants = self._substitute_constants(path)

                if self._needs_fhirpath_translation(path_with_constants):
                    # Use substituted path for FHIRPath translation
                    path = path_with_constants
                    # Use FHIRPath translator for complex expressions
                    extract_expr = self._translate_fhirpath_to_sql(path, resource)

                    # The FHIRPath translator uses json_extract() by default, but we need
                    # to use the correct extraction function based on the column type
                    # Replace json_extract( with the appropriate function for the type
                    if column_type in ["string", "id"]:
                        # For string types, use json_extract_string() to avoid JSON quotes
                        extract_expr = extract_expr.replace("json_extract(", "json_extract_string(", 1)
                    elif column_type == "boolean":
                        # Keep json_extract() and add boolean cast
                        extract_expr = f"({extract_expr})::BOOLEAN"
                    elif column_type in ["integer", "int"]:
                        # Keep json_extract() and add integer cast
                        extract_expr = f"({extract_expr})::INTEGER"
                    elif column_type in ["decimal", "number"]:
                        # Keep json_extract() and add decimal cast
                        extract_expr = f"({extract_expr})::DECIMAL"
                    # For other types, use as-is

                else:
                    # Use substituted path for simple JSON path conversion
                    path = path_with_constants

                    # Use simple JSON path conversion for basic paths
                    # Handle first() function by removing it and using [0] indexing
                    # ARCHITECTURAL FIX: Use array indexing for population-friendly first() function
                    # This maintains population-scale analytics capability (no LIMIT 1 anti-pattern)
                    if path.endswith('.first()'):
                        path_without_first = path[:-8]  # Remove '.first()'
                        # For paths like "name.family.first()", we need "name[0].family"
                        # Split at first dot to identify the collection
                        parts = path_without_first.split('.', 1)
                        if len(parts) == 2:
                            # e.g., "name.family" → "name[0].family"
                            collection, remainder = parts
                            json_path = f"$.{collection}[0].{remainder}"
                        else:
                            # e.g., "name" → "name[0]"
                            json_path = f"$.{parts[0]}[0]"
                    else:
                        json_path = "$." + path.replace('.', '[0].')

                    # Use thin dialect architecture: delegate to dialect for syntax
                    # Handle type conversion based on column type
                    if column_type == "boolean":
                        extract_expr = self._dialect_instance.extract_json_boolean('resource', json_path)
                    elif column_type in ["integer", "int"]:
                        extract_expr = self._dialect_instance.extract_json_integer('resource', json_path)
                    elif column_type in ["decimal", "number"]:
                        extract_expr = self._dialect_instance.extract_json_decimal('resource', json_path)
                    else:
                        # Default to string extraction
                        extract_expr = self._dialect_instance.extract_json_string('resource', json_path)

                columns.append(f'{extract_expr} AS {name}')

        if not columns:
            raise SQLGenerationError("ViewDefinition select must have at least one column")

        # Build WHERE clause using CTE infrastructure
        where_ctes, where_clause = self._build_where_clause(view_definition, resource)

        # Construct final SQL query with WHERE evaluation CTEs
        if where_ctes:
            # Build WITH clause manually from WHERE evaluation CTEs
            # Format: WITH cte1 AS (query1), cte2 AS (query2), ...
            cte_definitions = []
            for cte in where_ctes:
                cte_definitions.append(f"{cte.name} AS (\n{cte.query}\n)")

            with_clause = "WITH " + ",\n".join(cte_definitions)

            # Build query: WITH ... SELECT ... FROM ... WHERE ...
            sql_query = f"{with_clause}\nSELECT {', '.join(columns)} FROM {resource}"
            if where_clause:
                sql_query += f"\n{where_clause}"
        else:
            # No WHERE clause - simple SELECT
            sql_query = f"SELECT {', '.join(columns)} FROM {resource}"

        return sql_query

    # REMOVED: generate_from_fhirpath() method - architectural violation
    # This method created duplicate FHIRPath parsing logic that should be in Layer 2B (FHIRPath Engine)
    # Parsing expressions is not the responsibility of the SQL generator
    # Use FHIRPathParser directly for parsing, and generate_sql() for ViewDefinitions

    # REMOVED: get_dialect_specific_function() method - unused helper
    # Database-specific logic should be handled through proper dialect classes in Layer 5

    def _needs_fhirpath_translation(self, path: str) -> bool:
        """Check if a path requires FHIRPath translator (contains functions).

        Args:
            path: FHIRPath expression string

        Returns:
            True if path contains function calls that need translation
        """
        # Simple .first() at the end can be handled by simple path logic
        # Only use FHIRPath translator for complex cases
        if path.endswith('.first()'):
            # Check if there are OTHER functions besides .first() at the end
            path_without_trailing_first = path[:-8]  # Remove '.first()'
            # Check for functions in the remaining path
            complex_functions = ['ofType(', 'where(', 'exists(', 'all(', 'first(', 'last(',
                                'tail(', 'skip(', 'take(', 'select(', 'repeat(', 'empty(',
                                'distinct(', 'isDistinct(']
            return any(func in path_without_trailing_first for func in complex_functions)

        # Check for common FHIRPath functions that require translation
        fhirpath_functions = ['ofType(', 'where(', 'exists(', 'all(', 'first(', 'last(',
                             'tail(', 'skip(', 'take(', 'select(', 'repeat(', 'empty(',
                             'distinct(', 'isDistinct(']
        return any(func in path for func in fhirpath_functions)

    def _get_fhirpath_components(self, resource_type: str):
        """Lazy-load FHIRPath parser and translator.

        Args:
            resource_type: FHIR resource type for context

        Returns:
            Tuple of (parser, translator)
        """
        if self._fhirpath_parser is None:
            # Import here to avoid circular dependencies
            from fhir4ds.fhirpath.parser import FHIRPathParser
            self._fhirpath_parser = FHIRPathParser()

        # Always create a new translator with the current resource type
        # Dialect instance is already initialized in __init__
        from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator
        translator = ASTToSQLTranslator(self._dialect_instance, resource_type)

        # SP-023-004B: Return only parser and translator - no adapter needed
        return self._fhirpath_parser, translator

    def _translate_fhirpath_to_sql(self, path: str, resource_type: str) -> str:
        """Translate a FHIRPath expression to SQL using the FHIRPath translator.

        Args:
            path: FHIRPath expression string
            resource_type: FHIR resource type for context

        Returns:
            SQL expression string
        """
        # SP-023-004B: Get parser and translator (no adapter needed)
        parser, translator = self._get_fhirpath_components(resource_type)

        # Parse the FHIRPath expression
        parsed = parser.parse(path, context={"resourceType": resource_type})

        # SP-023-004B: Use EnhancedASTNode directly - translator handles it via accept()
        ast = parsed.get_ast()

        # Translate to SQL fragments
        fragments = translator.translate(ast)

        # For simple column selection, we expect a single fragment
        # Extract the SQL expression from the fragment
        if fragments and len(fragments) > 0:
            # Get the last fragment's expression (the final result)
            return fragments[-1].expression

        return ""

    def get_statistics(self) -> dict:
        """Get usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        # Basic statistics tracking
        return {
            "dialect": self.dialect,
            "generation_count": getattr(self, '_generation_count', 0)
        }

    def _parse_constants(self, view_definition: dict) -> dict:
        """Parse constants from ViewDefinition into lookup dictionary.

        Args:
            view_definition: SQL-on-FHIR ViewDefinition

        Returns:
            Dictionary mapping constant names to (type, value) tuples

        Example:
            {"SYSTEM_URL": ("string", "http://example.org"),
             "MAX_AGE": ("integer", 65)}
        """
        constants = {}
        for const in view_definition.get("constant", []):
            name = const.get("name")
            if not name:
                raise SQLGenerationError("Constant must have a name")

            # Check for duplicate constant names
            if name in constants:
                raise SQLGenerationError(f"Duplicate constant name: {name}")

            # Find the value[x] element
            value_key = None
            value = None
            for key in const.keys():
                if key.startswith("value"):
                    if value_key:
                        raise SQLGenerationError(f"Constant {name} has multiple values")
                    value_key = key
                    value = const[key]

            if not value_key:
                raise SQLGenerationError(f"Constant {name} has no value")

            # Extract type from valueXxx key (e.g., "valueString" → "string")
            const_type = value_key[5].lower() + value_key[6:]  # "valueString" → "string"

            constants[name] = (const_type, value)

        return constants

    def _substitute_constants(self, expression: str) -> str:
        """Replace constant references (%NAME) with actual values.

        Args:
            expression: FHIRPath expression potentially containing %NAME

        Returns:
            Expression with constants substituted

        Example:
            "identifier.where(system = %SYSTEM_URL)" →
            "identifier.where(system = 'http://example.org')"
        """
        import re

        # Find all %NAME patterns (case-insensitive for constant names)
        pattern = r'%([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.findall(pattern, expression)

        result = expression
        for const_name in matches:
            if const_name not in self._constants:
                available = ', '.join(self._constants.keys()) if self._constants else 'none'
                raise UndefinedConstantError(
                    f"Constant %{const_name} is not defined. "
                    f"Available constants: {available}"
                )

            const_type, const_value = self._constants[const_name]

            # Format value based on type
            if const_type in ["string", "code", "id", "uri", "url", "canonical"]:
                # Quote string types
                formatted = f"'{const_value}'"
            elif const_type in ["integer", "decimal", "positiveInt", "unsignedInt"]:
                # Numeric types - no quotes
                formatted = str(const_value)
            elif const_type == "boolean":
                # Boolean - lowercase true/false
                formatted = str(const_value).lower()
            elif const_type in ["date", "dateTime", "instant", "time"]:
                # Date/time - quote as string
                formatted = f"'{const_value}'"
            else:
                # Default: quote as string
                formatted = f"'{const_value}'"

            # Replace %NAME with formatted value
            result = result.replace(f"%{const_name}", formatted)

        return result

    def _build_where_clause(self, view_definition: dict, resource_type: str) -> tuple:
        """Build SQL WHERE clause using CTE infrastructure.

        Uses PEP-004 CTE infrastructure to evaluate WHERE expressions at population scale,
        following the CTE-First architectural principle.

        Args:
            view_definition: SQL-on-FHIR ViewDefinition
            resource_type: FHIR resource type for FHIRPath context

        Returns:
            Tuple of (where_ctes, where_clause):
            - where_ctes: List[CTE] for WHERE evaluation
            - where_clause: SQL WHERE clause string or empty string

        Example:
            ViewDefinition with where: [{"path": "active = true"}]
            Returns: ([CTE(...)], "WHERE resource.id IN (SELECT id FROM where_eval_1 WHERE result = true)")

        Architecture:
            Follows CTE-First design principle (CLAUDE.md line 175):
            - WHERE expressions translated using existing FHIRPath translator
            - CTEBuilder wraps fragments in population-level CTEs
            - Main query filters by joining with WHERE evaluation CTEs
            - Uniform execution model regardless of expression complexity
        """
        # Extract where elements from top-level of ViewDefinition
        where_elements = view_definition.get("where", [])
        if not where_elements:
            return ([], "")

        # Import CTE infrastructure
        from fhir4ds.fhirpath.sql.cte import CTEBuilder

        all_where_ctes = []
        where_cte_names = []

        for idx, where_elem in enumerate(where_elements):
            where_path = where_elem.get("path")
            if not where_path:
                # Skip empty where elements
                continue

            # Substitute constants in WHERE path
            where_path_with_constants = self._substitute_constants(where_path)

            try:
                # Parse and translate FHIRPath expression using existing translator
                # SP-023-004B: Get parser and translator (no adapter needed)
                parser, translator = self._get_fhirpath_components(resource_type)
                parsed = parser.parse(where_path_with_constants, context={"resourceType": resource_type})

                # SP-023-004B: Use EnhancedASTNode directly - translator handles via accept()
                ast = parsed.get_ast()

                # Translate to SQL fragments
                fragments = translator.translate(ast)

                # Build CTEs using PEP-004 infrastructure
                # CTEBuilder automatically creates: SELECT id, <boolean_expr> AS result FROM resource
                cte_builder = CTEBuilder(self._dialect_instance)

                # IMPORTANT: Update the first fragment's source_table to use actual resource type
                # The translator uses "resource" as a generic placeholder, but we need the
                # actual table name (e.g., "Patient") for the FROM clause
                if fragments and len(fragments) > 0:
                    # Only update the first fragment if it references "resource"
                    # This ensures the first CTE queries FROM the actual table
                    if fragments[0].source_table == "resource":
                        # Create a modified fragment with updated source_table
                        from fhir4ds.fhirpath.sql.fragments import SQLFragment
                        updated_fragment = SQLFragment(
                            expression=fragments[0].expression,
                            source_table=resource_type,
                            requires_unnest=fragments[0].requires_unnest,
                            is_aggregate=fragments[0].is_aggregate,
                            dependencies=list(fragments[0].dependencies) if fragments[0].dependencies else [],
                            metadata=dict(fragments[0].metadata)
                        )
                        # Replace the first fragment
                        fragments = [updated_fragment] + fragments[1:]

                where_ctes = cte_builder.build_cte_chain(fragments)

                # Rename CTEs to indicate they're WHERE evaluations
                # Build a name mapping and use rename_cte_chain() to update all references
                name_mapping = {}
                for i, cte in enumerate(where_ctes):
                    old_name = cte.name
                    new_name = f"where_eval_{idx + 1}_{i + 1}"
                    name_mapping[old_name] = new_name

                # Import CTE class to access static method
                from fhir4ds.fhirpath.sql.cte import CTE
                CTE.rename_cte_chain(where_ctes, name_mapping)

                all_where_ctes.extend(where_ctes)

                # Track the final CTE name for this WHERE condition
                if where_ctes:
                    where_cte_names.append(where_ctes[-1].name)

            except Exception as e:
                raise SQLGenerationError(
                    f"Failed to translate WHERE path '{where_path}': {e}\n"
                    f"Note: Known limitation - FHIRPath .where() function with filtering "
                    f"may not translate correctly. See translator bug documentation."
                )

        # Build WHERE clause that references the WHERE evaluation CTEs
        if not where_cte_names:
            return ([], "")

        # Combine multiple WHERE conditions with AND logic
        # Each WHERE CTE has: SELECT id, <boolean> AS result
        # Filter by: WHERE id IN (SELECT id FROM cte WHERE result = true)
        if len(where_cte_names) == 1:
            where_clause = (
                f"WHERE {resource_type}.id IN "
                f"(SELECT id FROM {where_cte_names[0]} WHERE result = true)"
            )
        else:
            # Multiple WHERE conditions - must pass ALL
            # Use INTERSECT for AND logic
            cte_selects = [
                f"(SELECT id FROM {cte_name} WHERE result = true)"
                for cte_name in where_cte_names
            ]
            intersected = "\nINTERSECT\n".join(cte_selects)
            where_clause = f"WHERE {resource_type}.id IN (\n{intersected}\n)"

        return (all_where_ctes, where_clause)
