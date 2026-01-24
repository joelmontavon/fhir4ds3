"""
Unit tests for cross-database comparison utilities.

Tests the normalization, comparison, and formatting logic
that ensures accurate cross-database validation.
"""

import pytest
import math
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any

from tests.integration.cross_database.comparison_utils import (
    ResultNormalizer,
    ValueComparator,
    ResultsetComparator,
    DiffFormatter,
    ComparisonResult,
    ComparisonSummary,
    ResultDifference,
    compare_database_results,
    normalize_for_comparison,
    DEFAULT_FLOAT_TOLERANCE,
)


class TestResultNormalizer:
    """Test result normalization for cross-database comparison."""

    def test_normalize_none(self):
        """Test None value normalization."""
        normalizer = ResultNormalizer()
        assert normalizer.normalize(None, 'duckdb') is None
        assert normalizer.normalize(None, 'postgresql') is None

    def test_normalize_integer(self):
        """Test integer value normalization."""
        normalizer = ResultNormalizer()
        assert normalizer.normalize(42, 'duckdb') == 42
        assert normalizer.normalize(42, 'postgresql') == 42

    def test_normalize_float_with_tolerance(self):
        """Test float normalization with tolerance rounding."""
        normalizer = ResultNormalizer(float_tolerance=1e-6)

        # Floats should be rounded to tolerance precision
        result = normalizer.normalize(3.14159265359, 'duckdb')
        assert isinstance(result, float)
        assert abs(result - 3.141593) < 1e-6

    def test_normalize_float_nan(self):
        """Test NaN normalization."""
        normalizer = ResultNormalizer()
        result = normalizer.normalize(float('nan'), 'duckdb')
        assert math.isnan(result)

    def test_normalize_float_infinity(self):
        """Test infinity normalization."""
        normalizer = ResultNormalizer()
        pos_inf = normalizer.normalize(float('inf'), 'duckdb')
        neg_inf = normalizer.normalize(float('-inf'), 'postgresql')

        assert math.isinf(pos_inf)
        assert math.isinf(neg_inf)

    def test_normalize_string_whitespace(self):
        """Test string whitespace normalization."""
        normalizer = ResultNormalizer()
        assert normalizer.normalize("  test  ", 'duckdb') == "test"
        assert normalizer.normalize("\tvalue\n", 'postgresql') == "value"

    def test_normalize_string_null_variants(self):
        """Test normalization of null-like strings."""
        normalizer = ResultNormalizer()
        assert normalizer.normalize("null", 'duckdb') is None
        assert normalizer.normalize("NULL", 'postgresql') is None
        assert normalizer.normalize("None", 'duckdb') is None

    def test_normalize_list(self):
        """Test list normalization."""
        normalizer = ResultNormalizer()
        result = normalizer.normalize([1, 2.5, "test"], 'duckdb')
        assert result == [1, 2.5, "test"]

    def test_normalize_dict(self):
        """Test dictionary normalization."""
        normalizer = ResultNormalizer()
        result = normalizer.normalize({"a": 1, "b": 2.5}, 'postgresql')
        assert result == {"a": 1, "b": 2.5}

    def test_normalize_datetime(self):
        """Test datetime normalization."""
        normalizer = ResultNormalizer()
        dt = datetime(2024, 1, 15, 12, 30, 45)
        result = normalizer.normalize(dt, 'duckdb')
        assert isinstance(result, str)
        assert "2024-01-15" in result

    def test_normalize_date(self):
        """Test date normalization."""
        normalizer = ResultNormalizer()
        d = date(2024, 1, 15)
        result = normalizer.normalize(d, 'postgresql')
        assert isinstance(result, str)
        assert "2024-01-15" in result

    def test_normalize_decimal(self):
        """Test Decimal normalization."""
        normalizer = ResultNormalizer()
        result = normalizer.normalize(Decimal("3.14159"), 'duckdb')
        assert isinstance(result, float)


class TestValueComparator:
    """Test value comparison with type-aware logic."""

    def test_compare_identical_integers(self):
        """Test comparison of identical integers."""
        comparator = ValueComparator()
        result = comparator.compare(42, 42)
        assert result.equal is True

    def test_compare_different_integers(self):
        """Test comparison of different integers."""
        comparator = ValueComparator()
        result = comparator.compare(42, 43)
        assert result.equal is False
        assert "differ" in result.reason.lower()

    def test_compare_floats_within_tolerance(self):
        """Test comparison of floats within tolerance."""
        comparator = ValueComparator(float_tolerance=1e-6)
        result = comparator.compare(3.14159265359, 3.14159265358)
        assert result.equal is True

    def test_compare_floats_outside_tolerance(self):
        """Test comparison of floats outside tolerance."""
        comparator = ValueComparator(float_tolerance=1e-9)
        result = comparator.compare(1.0, 1.001)
        assert result.equal is False
        assert "tolerance" in result.reason.lower()

    def test_compare_floats_both_nan(self):
        """Test comparison of two NaN values."""
        comparator = ValueComparator()
        result = comparator.compare(float('nan'), float('nan'))
        assert result.equal is True

    def test_compare_float_one_nan(self):
        """Test comparison when one value is NaN."""
        comparator = ValueComparator()
        result = comparator.compare(float('nan'), 1.0)
        assert result.equal is False

    def test_compare_floats_both_infinity(self):
        """Test comparison of two infinity values."""
        comparator = ValueComparator()
        result = comparator.compare(float('inf'), float('inf'))
        assert result.equal is True

        result = comparator.compare(float('-inf'), float('-inf'))
        assert result.equal is True

    def test_compare_floats_mixed_infinity(self):
        """Test comparison of positive and negative infinity."""
        comparator = ValueComparator()
        result = comparator.compare(float('inf'), float('-inf'))
        assert result.equal is False

    def test_compare_strings_identical(self):
        """Test comparison of identical strings."""
        comparator = ValueComparator()
        result = comparator.compare("test", "test")
        assert result.equal is True

    def test_compare_strings_different(self):
        """Test comparison of different strings."""
        comparator = ValueComparator()
        result = comparator.compare("test1", "test2")
        assert result.equal is False

    def test_compare_strings_whitespace_normalized(self):
        """Test that string comparison normalizes whitespace."""
        comparator = ValueComparator()
        result = comparator.compare("  test  ", "test")
        assert result.equal is True

    def test_compare_booleans_identical(self):
        """Test comparison of identical booleans."""
        comparator = ValueComparator()
        assert comparator.compare(True, True).equal is True
        assert comparator.compare(False, False).equal is True

    def test_compare_booleans_different(self):
        """Test comparison of different booleans."""
        comparator = ValueComparator()
        result = comparator.compare(True, False)
        assert result.equal is False

    def test_compare_lists_identical(self):
        """Test comparison of identical lists."""
        comparator = ValueComparator()
        result = comparator.compare([1, 2, 3], [1, 2, 3])
        assert result.equal is True

    def test_compare_lists_different_length(self):
        """Test comparison of lists with different lengths."""
        comparator = ValueComparator()
        result = comparator.compare([1, 2, 3], [1, 2])
        assert result.equal is False
        assert "length" in result.reason.lower()

    def test_compare_lists_different_values(self):
        """Test comparison of lists with different values."""
        comparator = ValueComparator()
        result = comparator.compare([1, 2, 3], [1, 2, 4])
        assert result.equal is False
        assert "index 2" in result.reason.lower()

    def test_compare_lists_float_tolerance(self):
        """Test list comparison with float tolerance."""
        comparator = ValueComparator(float_tolerance=1e-6)
        result = comparator.compare([1.0, 2.0], [1.000001, 2.0])
        assert result.equal is True

    def test_compare_dicts_identical(self):
        """Test comparison of identical dictionaries."""
        comparator = ValueComparator()
        result = comparator.compare({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result.equal is True

    def test_compare_dicts_different_keys(self):
        """Test comparison of dictionaries with different keys."""
        comparator = ValueComparator()
        result = comparator.compare({"a": 1}, {"b": 1})
        assert result.equal is False
        assert "key" in result.reason.lower()

    def test_compare_dicts_different_values(self):
        """Test comparison of dictionaries with different values."""
        comparator = ValueComparator()
        result = comparator.compare({"a": 1}, {"a": 2})
        assert result.equal is False
        assert "key 'a'" in result.reason.lower()

    def test_compare_dicts_nested(self):
        """Test comparison of nested dictionaries."""
        comparator = ValueComparator()
        result = comparator.compare(
            {"a": {"b": 1}},
            {"a": {"b": 1}}
        )
        assert result.equal is True

    def test_compare_none_values(self):
        """Test comparison of None values."""
        comparator = ValueComparator()
        result = comparator.compare(None, None)
        assert result.equal is True

    def test_compare_one_none(self):
        """Test comparison when one value is None."""
        comparator = ValueComparator()
        result = comparator.compare(None, 1)
        assert result.equal is False
        assert "none" in result.reason.lower()

    def test_compare_mixed_types_numeric_coercion(self):
        """Test comparison with numeric type coercion."""
        comparator = ValueComparator()
        # Integer and float should compare as numbers
        result = comparator.compare(1, 1.0)
        assert result.equal is True

    def test_compare_mixed_types_string_coercion(self):
        """Test comparison with string type coercion."""
        comparator = ValueComparator()
        result = comparator.compare("test", " test ")
        assert result.equal is True  # Whitespace normalized

    def test_compare_incompatible_types(self):
        """Test comparison of incompatible types."""
        comparator = ValueComparator()
        result = comparator.compare([1, 2], {"a": 1})
        assert result.equal is False
        assert "type" in result.reason.lower()


class TestResultsetComparator:
    """Test result set comparison for database query results."""

    def test_compare_empty_resultsets(self):
        """Test comparison of empty result sets."""
        comparator = ResultsetComparator()
        summary = comparator.compare_resultsets([], [], 'duckdb', 'postgresql')

        assert summary.total_comparisons == 0
        assert summary.equal_comparisons == 0
        assert summary.equality_percentage == 0

    def test_compare_identical_single_row(self):
        """Test comparison of identical single-row results."""
        comparator = ResultsetComparator()
        left = [{"id": 1, "value": 10}]
        right = [{"id": 1, "value": 10}]

        summary = comparator.compare_resultsets(left, right, 'duckdb', 'postgresql')

        assert summary.total_comparisons == 1
        assert summary.equal_comparisons == 1
        assert summary.different_comparisons == 0
        assert summary.equality_percentage == 100.0

    def test_compare_different_row_counts(self):
        """Test comparison with different row counts."""
        comparator = ResultsetComparator()
        left = [{"id": 1}, {"id": 2}]
        right = [{"id": 1}]

        summary = comparator.compare_resultsets(left, right, 'duckdb', 'postgresql')

        assert summary.total_comparisons == 2
        assert len(summary.differences) > 0

        # Check that row_count difference is recorded
        row_count_diff = next((d for d in summary.differences if d.path == 'row_count'), None)
        assert row_count_diff is not None
        assert row_count_diff.difference_type == 'structure'

    def test_compare_row_value_differences(self):
        """Test comparison with value differences in rows."""
        comparator = ResultsetComparator()
        left = [{"id": 1, "value": 10}]
        right = [{"id": 1, "value": 20}]

        summary = comparator.compare_resultsets(left, right, 'duckdb', 'postgresql')

        assert summary.total_comparisons == 1
        assert summary.different_comparisons == 1

        # Find the value difference
        value_diff = next((d for d in summary.differences if 'value' in d.path), None)
        assert value_diff is not None
        assert value_diff.left_value == 10
        assert value_diff.right_value == 20

    def test_compare_with_float_tolerance(self):
        """Test result set comparison with float tolerance."""
        comparator = ResultsetComparator(float_tolerance=0.01)
        left = [{"id": 1, "value": 3.141}]
        right = [{"id": 1, "value": 3.142}]

        summary = comparator.compare_resultsets(left, right, 'duckdb', 'postgresql')

        assert summary.total_comparisons == 1
        assert summary.equal_comparisons == 1

    def test_compare_missing_rows(self):
        """Test comparison with missing rows."""
        comparator = ResultsetComparator()
        left = [{"id": 1}]
        right = []

        summary = comparator.compare_resultsets(left, right, 'duckdb', 'postgresql')

        assert summary.total_comparisons == 1

        # Check for missing difference
        missing_diff = next((d for d in summary.differences if d.difference_type == 'missing'), None)
        assert missing_diff is not None


class TestDiffFormatter:
    """Test formatting of comparison differences."""

    def test_format_difference_basic(self):
        """Test basic difference formatting."""
        diff = ResultDifference(
            path="test.path",
            left_value=1,
            right_value=2,
            difference_type="value"
        )

        formatted = DiffFormatter.format_difference(diff)

        assert "test.path" in formatted
        assert "1" in formatted
        assert "2" in formatted
        assert "value" in formatted

    def test_format_difference_missing(self):
        """Test formatting of missing value difference."""
        diff = ResultDifference(
            path="row[0]",
            left_value=None,
            right_value={"id": 1},
            difference_type="missing"
        )

        formatted = DiffFormatter.format_difference(diff)

        assert "missing" in formatted.lower()
        assert "row[0]" in formatted

    def test_format_difference_with_tolerance(self):
        """Test formatting of difference with tolerance."""
        diff = ResultDifference(
            path="value",
            left_value=3.14159,
            right_value=3.14160,
            difference_type="value",
            tolerance=1e-5
        )

        formatted = DiffFormatter.format_difference(diff)

        assert "tolerance" in formatted.lower()

    def test_format_value_simple(self):
        """Test formatting of simple values."""
        assert "42" in DiffFormatter._format_value(42)
        assert "test" in DiffFormatter._format_value("test")
        assert "None" in DiffFormatter._format_value(None)

    def test_format_value_dict(self):
        """Test formatting of dictionary values."""
        value = {"a": 1, "b": 2}
        formatted = DiffFormatter._format_value(value)
        assert "a" in formatted
        assert "b" in formatted

    def test_format_value_list(self):
        """Test formatting of list values."""
        value = [1, 2, 3]
        formatted = DiffFormatter._format_value(value)
        assert "1" in formatted
        assert "2" in formatted
        assert "3" in formatted

    def test_format_value_long_truncation(self):
        """Test truncation of long values."""
        long_value = {"key": "x" * 200}
        formatted = DiffFormatter._format_value(long_value, max_length=50)
        assert len(formatted) < 200  # Should be truncated
        assert "..." in formatted

    def test_format_summary_perfect(self):
        """Test formatting of perfect summary (100% match)."""
        summary = ComparisonSummary(
            total_comparisons=100,
            equal_comparisons=100,
            different_comparisons=0,
            equality_percentage=100.0,
            differences=[]
        )

        formatted = DiffFormatter.format_summary(summary)

        assert "100" in formatted
        assert "0" in formatted
        assert "100.0%" in formatted

    def test_format_summary_with_differences(self):
        """Test formatting of summary with differences."""
        summary = ComparisonSummary(
            total_comparisons=100,
            equal_comparisons=90,
            different_comparisons=10,
            equality_percentage=90.0,
            differences=[
                ResultDifference("path1", 1, 2, "value"),
                ResultDifference("path2", 3, 4, "value"),
            ]
        )

        formatted = DiffFormatter.format_summary(summary)

        assert "90" in formatted  # equal comparisons
        assert "10" in formatted  # different comparisons
        assert "90.0%" in formatted
        assert "path1" in formatted


class TestConvenienceFunctions:
    """Test convenience functions for comparison."""

    def test_compare_database_results_identical(self):
        """Test compare_database_results with identical results."""
        result = compare_database_results(42, 42)
        assert result.equal is True

    def test_compare_database_results_different(self):
        """Test compare_database_results with different results."""
        result = compare_database_results(42, 43)
        assert result.equal is False

    def test_compare_database_results_float_tolerance(self):
        """Test compare_database_results with float tolerance."""
        result = compare_database_results(3.14159265359, 3.14159265358, float_tolerance=1e-6)
        assert result.equal is True

    def test_normalize_for_comparison_duckdb(self):
        """Test normalize_for_comparison for DuckDB."""
        result = normalize_for_comparison(3.14159, 'duckdb')
        assert isinstance(result, float)

    def test_normalize_for_comparison_postgresql(self):
        """Test normalize_for_comparison for PostgreSQL."""
        result = normalize_for_comparison(3.14159, 'postgresql')
        assert isinstance(result, float)

    def test_normalize_for_comparison_custom_tolerance(self):
        """Test normalize_for_comparison with custom tolerance."""
        result = normalize_for_comparison(3.14159265359, 'duckdb', float_tolerance=1e-3)
        # Should be rounded to 3 decimal places
        assert abs(result - 3.142) < 0.001


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_compare_very_large_floats(self):
        """Test comparison of very large float values."""
        comparator = ValueComparator()
        result = comparator.compare(1e308, 1e308)
        assert result.equal is True

    def test_compare_very_small_floats(self):
        """Test comparison of very small float values."""
        comparator = ValueComparator(float_tolerance=1e-20)
        result = comparator.compare(1e-20, 1.1e-20)
        assert result.equal is True  # Within tolerance

    def test_compare_empty_structures(self):
        """Test comparison of empty structures."""
        comparator = ValueComparator()

        assert comparator.compare([], []).equal is True
        assert comparator.compare({}, {}).equal is True
        assert comparator.compare("", "").equal is True

    def test_compare_deeply_nested_structures(self):
        """Test comparison of deeply nested structures."""
        comparator = ValueComparator()
        left = {"a": {"b": {"c": {"d": 1}}}}
        right = {"a": {"b": {"c": {"d": 1}}}}

        result = comparator.compare(left, right)
        assert result.equal is True

    def test_compare_unicode_strings(self):
        """Test comparison of Unicode strings."""
        comparator = ValueComparator()
        result = comparator.compare("Hello 世界", "Hello 世界")
        assert result.equal is True

    def test_compare_special_characters(self):
        """Test comparison of strings with special characters."""
        comparator = ValueComparator()
        result = comparator.compare("test\n\t\r", "test")  # Whitespace normalized
        assert result.equal is True

    def test_zero_vs_negative_zero(self):
        """Test comparison of zero vs negative zero."""
        comparator = ValueComparator()
        result = comparator.compare(0, -0.0)
        assert result.equal is True
