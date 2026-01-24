"""
Unit tests for SQLGenerator constant support.

Tests the parsing, substitution, and integration of ViewDefinition constants
into SQL generation.
"""

import pytest
from fhir4ds.sql.generator import SQLGenerator
from fhir4ds.sql.exceptions import SQLGenerationError, UndefinedConstantError


class TestConstantParsing:
    """Tests for constant parsing from ViewDefinitions."""

    def test_parse_string_constant(self):
        """Test parsing a string constant."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "SYSTEM_URL", "valueString": "http://example.org"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {"SYSTEM_URL": ("string", "http://example.org")}

    def test_parse_integer_constant(self):
        """Test parsing an integer constant."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "MAX_AGE", "valueInteger": 65}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {"MAX_AGE": ("integer", 65)}

    def test_parse_boolean_constant(self):
        """Test parsing a boolean constant."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "INCLUDE_INACTIVE", "valueBoolean": False}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {"INCLUDE_INACTIVE": ("boolean", False)}

    def test_parse_decimal_constant(self):
        """Test parsing a decimal constant."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "PI", "valueDecimal": 3.14}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {"PI": ("decimal", 3.14)}

    def test_parse_date_constant(self):
        """Test parsing a date constant."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "CUTOFF_DATE", "valueDate": "2023-01-01"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {"CUTOFF_DATE": ("date", "2023-01-01")}

    def test_parse_multiple_constants(self):
        """Test parsing multiple constants."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [
                {"name": "SYSTEM_URL", "valueString": "http://example.org"},
                {"name": "MAX_AGE", "valueInteger": 65},
                {"name": "INCLUDE_INACTIVE", "valueBoolean": True}
            ],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert len(constants) == 3
        assert constants["SYSTEM_URL"] == ("string", "http://example.org")
        assert constants["MAX_AGE"] == ("integer", 65)
        assert constants["INCLUDE_INACTIVE"] == ("boolean", True)

    def test_parse_no_constants(self):
        """Test parsing ViewDefinition with no constants."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        constants = generator._parse_constants(view_def)
        assert constants == {}

    def test_parse_constant_without_name_raises_error(self):
        """Test that constant without name raises error."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"valueString": "test"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        with pytest.raises(SQLGenerationError, match="Constant must have a name"):
            generator._parse_constants(view_def)

    def test_parse_constant_without_value_raises_error(self):
        """Test that constant without value raises error."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "TEST"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        with pytest.raises(SQLGenerationError, match="Constant TEST has no value"):
            generator._parse_constants(view_def)

    def test_parse_duplicate_constant_name_raises_error(self):
        """Test that duplicate constant names raise error."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [
                {"name": "SYSTEM_URL", "valueString": "http://example.org"},
                {"name": "SYSTEM_URL", "valueString": "http://other.org"}
            ],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        with pytest.raises(SQLGenerationError, match="Duplicate constant name"):
            generator._parse_constants(view_def)


class TestConstantSubstitution:
    """Tests for constant substitution in expressions."""

    def test_substitute_string_constant(self):
        """Test substituting a string constant."""
        generator = SQLGenerator()
        generator._constants = {"URL": ("string", "http://example.org")}
        result = generator._substitute_constants("system = %URL")
        assert result == "system = 'http://example.org'"

    def test_substitute_integer_constant(self):
        """Test substituting an integer constant."""
        generator = SQLGenerator()
        generator._constants = {"MAX": ("integer", 65)}
        result = generator._substitute_constants("age < %MAX")
        assert result == "age < 65"

    def test_substitute_boolean_constant(self):
        """Test substituting a boolean constant."""
        generator = SQLGenerator()
        generator._constants = {"ACTIVE": ("boolean", True)}
        result = generator._substitute_constants("active = %ACTIVE")
        assert result == "active = true"

    def test_substitute_decimal_constant(self):
        """Test substituting a decimal constant."""
        generator = SQLGenerator()
        generator._constants = {"PI": ("decimal", 3.14)}
        result = generator._substitute_constants("value > %PI")
        assert result == "value > 3.14"

    def test_substitute_date_constant(self):
        """Test substituting a date constant."""
        generator = SQLGenerator()
        generator._constants = {"CUTOFF": ("date", "2023-01-01")}
        result = generator._substitute_constants("birthDate >= %CUTOFF")
        assert result == "birthDate >= '2023-01-01'"

    def test_substitute_multiple_constants(self):
        """Test substituting multiple constants in one expression."""
        generator = SQLGenerator()
        generator._constants = {
            "MIN_AGE": ("integer", 18),
            "MAX_AGE": ("integer", 65)
        }
        result = generator._substitute_constants("age >= %MIN_AGE and age <= %MAX_AGE")
        assert result == "age >= 18 and age <= 65"

    def test_substitute_constant_multiple_times(self):
        """Test substituting the same constant multiple times."""
        generator = SQLGenerator()
        generator._constants = {"SYSTEM": ("string", "http://example.org")}
        result = generator._substitute_constants("system = %SYSTEM or identifier.system = %SYSTEM")
        assert result == "system = 'http://example.org' or identifier.system = 'http://example.org'"

    def test_substitute_no_constants(self):
        """Test substitution when no constants in expression."""
        generator = SQLGenerator()
        generator._constants = {"URL": ("string", "http://example.org")}
        result = generator._substitute_constants("system = 'literal'")
        assert result == "system = 'literal'"

    def test_undefined_constant_raises_error(self):
        """Test that undefined constant reference raises error."""
        generator = SQLGenerator()
        generator._constants = {}
        with pytest.raises(UndefinedConstantError, match="Constant %MISSING is not defined"):
            generator._substitute_constants("system = %MISSING")

    def test_case_sensitive_constant_names(self):
        """Test that constant names are case-sensitive."""
        generator = SQLGenerator()
        generator._constants = {"name_use": ("string", "official")}
        result = generator._substitute_constants("use = %name_use")
        assert result == "use = 'official'"


class TestConstantIntegration:
    """Tests for constant integration into SQL generation."""

    def test_generate_sql_with_string_constant_in_simple_path(self):
        """Test SQL generation with string constant in simple path (array index)."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "constant": [{"name": "name_index", "valueInteger": 1}],
            "select": [{
                "column": [
                    {"name": "id", "path": "id", "type": "id"},
                    {"name": "family", "path": "name[%name_index].family", "type": "string"}
                ]
            }]
        }
        sql = generator.generate_sql(view_def)
        assert "name[1]" in sql
        assert "FROM Patient" in sql

    def test_generate_sql_with_no_constants(self):
        """Test that SQL generation works with no constants."""
        generator = SQLGenerator()
        view_def = {
            "resource": "Patient",
            "select": [{
                "column": [
                    {"name": "id", "path": "id", "type": "id"}
                ]
            }]
        }
        sql = generator.generate_sql(view_def)
        assert "SELECT" in sql
        assert "FROM Patient" in sql

    def test_constants_persisted_across_generation(self):
        """Test that constants are parsed fresh for each generation."""
        generator = SQLGenerator()
        view_def1 = {
            "resource": "Patient",
            "constant": [{"name": "CONST1", "valueString": "value1"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        generator.generate_sql(view_def1)
        assert "CONST1" in generator._constants

        view_def2 = {
            "resource": "Patient",
            "constant": [{"name": "CONST2", "valueString": "value2"}],
            "select": [{"column": [{"name": "id", "path": "id"}]}]
        }
        generator.generate_sql(view_def2)
        # CONST1 should be replaced by CONST2
        assert "CONST2" in generator._constants
        assert "CONST1" not in generator._constants
