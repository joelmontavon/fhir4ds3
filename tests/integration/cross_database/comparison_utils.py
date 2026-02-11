"""
Comparison utilities for cross-database testing.

Provides type-aware result comparison, normalization, and diff formatting
to ensure accurate comparison of DuckDB and PostgreSQL query results.
"""

import json
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal


@dataclass
class ComparisonResult:
    """Result of comparing two database results."""
    equal: bool
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    normalized_left: Any = None
    normalized_right: Any = None


@dataclass
class ResultDifference:
    """Detailed difference between two results."""
    path: str
    left_value: Any
    right_value: Any
    difference_type: str  # 'type', 'value', 'structure', 'missing'
    tolerance: Optional[float] = None


@dataclass
class ComparisonSummary:
    """Summary of comparison across multiple tests."""
    total_comparisons: int
    equal_comparisons: int
    different_comparisons: int
    equality_percentage: float
    differences: List[ResultDifference] = field(default_factory=list)


class ResultNormalizer:
    """
    Normalize database results for comparison.

    Handles dialect-specific formatting differences while preserving
    semantic meaning.
    """

    # Default tolerance for floating-point comparison
    DEFAULT_FLOAT_TOLERANCE = 1e-9

    def __init__(self, float_tolerance: float = DEFAULT_FLOAT_TOLERANCE):
        """Initialize normalizer with configurable tolerance."""
        self.float_tolerance = float_tolerance

    def normalize(self, value: Any, dialect: str) -> Any:
        """
        Normalize a value for comparison.

        Args:
            value: The value to normalize
            dialect: Database dialect ('duckdb' or 'postgresql')

        Returns:
            Normalized value suitable for comparison
        """
        if value is None:
            return None

        # Handle different types
        if isinstance(value, float) or isinstance(value, Decimal):
            return self._normalize_number(value, dialect)

        if isinstance(value, str):
            return self._normalize_string(value, dialect)

        if isinstance(value, (list, tuple)):
            return self._normalize_list(value, dialect)

        if isinstance(value, dict):
            return self._normalize_dict(value, dialect)

        if isinstance(value, (datetime, date)):
            return self._normalize_datetime(value, dialect)

        if isinstance(value, bool):
            return value

        # For integers and other types, return as-is
        return value

    def _normalize_number(self, value: Union[float, Decimal], dialect: str) -> float:
        """Normalize numeric values for comparison."""
        # Convert to float for consistent comparison
        normalized = float(value)

        # Round to tolerance to avoid precision differences
        if self.float_tolerance > 0:
            precision = int(-math.log10(self.float_tolerance))
            normalized = round(normalized, precision)

        # Handle NaN consistently
        if math.isnan(normalized):
            return float('nan')

        # Handle infinity consistently
        if math.isinf(normalized):
            return normalized

        return normalized

    def _normalize_string(self, value: str, dialect: str) -> str:
        """Normalize string values for comparison."""
        # Strip whitespace that might differ between databases
        normalized = value.strip()

        # PostgreSQL may have different NULL string representations
        if normalized.lower() in ('null', 'none'):
            return None

        return normalized

    def _normalize_list(self, value: Union[list, tuple], dialect: str) -> list:
        """Normalize list/tuple for comparison."""
        return [self.normalize(item, dialect) for item in value]

    def _normalize_dict(self, value: dict, dialect: str) -> dict:
        """Normalize dictionary for comparison."""
        normalized = {}
        for key, val in value.items():
            normalized[key] = self.normalize(val, dialect)
        return normalized

    def _normalize_datetime(self, value: Union[datetime, date], dialect: str) -> str:
        """Normalize datetime/date for comparison."""
        # Convert to ISO format string for consistent comparison
        if isinstance(value, datetime):
            return value.isoformat()
        return value.isoformat()


class ValueComparator:
    """
    Compare normalized values with type-aware logic.

    Handles floating-point tolerance, JSON structures, and FHIR types.
    """

    def __init__(self, float_tolerance: float = ResultNormalizer.DEFAULT_FLOAT_TOLERANCE):
        """Initialize comparator with configurable tolerance."""
        self.float_tolerance = float_tolerance
        self.normalizer = ResultNormalizer(float_tolerance)

    def compare(self, left: Any, right: Any,
                left_dialect: str = 'duckdb',
                right_dialect: str = 'postgresql',
                path: str = '') -> ComparisonResult:
        """
        Compare two values with normalization and type-aware logic.

        Args:
            left: Left value to compare
            right: Right value to compare
            left_dialect: Dialect of left value
            right_dialect: Dialect of right value
            path: Path for error reporting (for nested structures)

        Returns:
            ComparisonResult with equality status and details
        """
        # Normalize values first
        norm_left = self.normalizer.normalize(left, left_dialect)
        norm_right = self.normalizer.normalize(right, right_dialect)

        # Handle None values
        if norm_left is None and norm_right is None:
            return ComparisonResult(equal=True, normalized_left=None, normalized_right=None)

        if norm_left is None or norm_right is None:
            return ComparisonResult(
                equal=False,
                reason=f"One value is None: left={norm_left}, right={norm_right}",
                normalized_left=norm_left,
                normalized_right=norm_right
            )

        # Type-based comparison
        left_type = type(norm_left)
        right_type = type(norm_right)

        # Check for type mismatches
        if left_type != right_type:
            # Try to coerce for comparison
            return self._compare_mixed_types(norm_left, norm_right, path)

        # Compare based on type
        if isinstance(norm_left, float):
            return self._compare_floats(norm_left, norm_right, path)
        elif isinstance(norm_left, (int, bool, str)):
            return self._compare_exact(norm_left, norm_right, path)
        elif isinstance(norm_left, (list, tuple)):
            return self._compare_lists(list(norm_left), list(norm_right),
                                      left_dialect, right_dialect, path)
        elif isinstance(norm_left, dict):
            return self._compare_dicts(norm_left, norm_right,
                                      left_dialect, right_dialect, path)
        else:
            return ComparisonResult(
                equal=False,
                reason=f"Unsupported type for comparison: {type(norm_left)}",
                normalized_left=norm_left,
                normalized_right=norm_right
            )

    def _compare_floats(self, left: float, right: float, path: str) -> ComparisonResult:
        """Compare floats with tolerance."""
        # Handle NaN
        if math.isnan(left) and math.isnan(right):
            return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)

        if math.isnan(left) or math.isnan(right):
            return ComparisonResult(
                equal=False,
                reason=f"One value is NaN: left={left}, right={right}",
                normalized_left=left,
                normalized_right=right
            )

        # Handle infinity
        if math.isinf(left) and math.isinf(right):
            return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)

        if math.isinf(left) or math.isinf(right):
            return ComparisonResult(
                equal=False,
                reason=f"One value is infinite: left={left}, right={right}",
                normalized_left=left,
                normalized_right=right
            )

        # Compare with tolerance
        diff = abs(left - right)
        if diff <= self.float_tolerance:
            return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)

        return ComparisonResult(
            equal=False,
            reason=f"Float difference {diff} exceeds tolerance {self.float_tolerance}",
            details={'difference': diff, 'tolerance': self.float_tolerance},
            normalized_left=left,
            normalized_right=right
        )

    def _compare_exact(self, left: Any, right: Any, path: str) -> ComparisonResult:
        """Compare values for exact equality."""
        if left == right:
            return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)

        return ComparisonResult(
            equal=False,
            reason=f"Values differ: {left} != {right}",
            normalized_left=left,
            normalized_right=right
        )

    def _compare_mixed_types(self, left: Any, right: Any, path: str) -> ComparisonResult:
        """Compare values of different types, attempting coercion."""
        # Try numeric coercion
        try:
            left_num = float(left)
            right_num = float(right)
            return self._compare_floats(left_num, right_num, path)
        except (ValueError, TypeError):
            pass

        # Try string coercion
        try:
            left_str = str(left).strip()
            right_str = str(right).strip()
            if left_str == right_str:
                return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)
        except Exception:
            pass

        return ComparisonResult(
            equal=False,
            reason=f"Type mismatch: {type(left).__name__} != {type(right).__name__}",
            normalized_left=left,
            normalized_right=right
        )

    def _compare_lists(self, left: list, right: list,
                       left_dialect: str, right_dialect: str,
                       path: str) -> ComparisonResult:
        """Compare lists element-wise."""
        if len(left) != len(right):
            return ComparisonResult(
                equal=False,
                reason=f"List length mismatch: {len(left)} != {len(right)}",
                details={'left_length': len(left), 'right_length': len(right)},
                normalized_left=left,
                normalized_right=right
            )

        # Compare elements
        for i, (l_item, r_item) in enumerate(zip(left, right)):
            item_path = f"{path}[{i}]" if path else f"[{i}]"
            result = self.compare(l_item, r_item, left_dialect, right_dialect, item_path)
            if not result.equal:
                result.reason = f"At index {i}: {result.reason}"
                return result

        return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)

    def _compare_dicts(self, left: dict, right: dict,
                       left_dialect: str, right_dialect: str,
                       path: str) -> ComparisonResult:
        """Compare dictionaries key by key."""
        left_keys = set(left.keys())
        right_keys = set(right.keys())

        # Check for key differences
        if left_keys != right_keys:
            missing_left = right_keys - left_keys
            missing_right = left_keys - right_keys
            return ComparisonResult(
                equal=False,
                reason=f"Key mismatch: missing in left={missing_left}, missing in right={missing_right}",
                details={'missing_in_left': missing_left, 'missing_in_right': missing_right},
                normalized_left=left,
                normalized_right=right
            )

        # Compare values
        for key in left_keys:
            key_path = f"{path}.{key}" if path else key
            result = self.compare(left[key], right[key], left_dialect, right_dialect, key_path)
            if not result.equal:
                result.reason = f"At key '{key}': {result.reason}"
                return result

        return ComparisonResult(equal=True, normalized_left=left, normalized_right=right)


class ResultsetComparator:
    """
    Compare database result sets.

    Handles multi-row results and provides detailed difference reporting.
    """

    def __init__(self, float_tolerance: float = ResultNormalizer.DEFAULT_FLOAT_TOLERANCE):
        """Initialize resultset comparator."""
        self.comparator = ValueComparator(float_tolerance)

    def compare_resultsets(self,
                           left_results: List[Dict[str, Any]],
                           right_results: List[Dict[str, Any]],
                           left_dialect: str = 'duckdb',
                           right_dialect: str = 'postgresql',
                           key_columns: Optional[List[str]] = None) -> ComparisonSummary:
        """
        Compare two result sets from database queries.

        Args:
            left_results: Results from first database
            right_results: Results from second database
            left_dialect: Dialect of first database
            right_dialect: Dialect of second database
            key_columns: Columns to use as row identifiers (for row matching)

        Returns:
            ComparisonSummary with detailed differences
        """
        differences = []
        total_comparisons = 0
        equal_comparisons = 0

        # If result counts differ, record that
        if len(left_results) != len(right_results):
            differences.append(ResultDifference(
                path='row_count',
                left_value=len(left_results),
                right_value=len(right_results),
                difference_type='structure'
            ))

        # Compare rows
        max_rows = max(len(left_results), len(right_results))
        for i in range(max_rows):
            left_row = left_results[i] if i < len(left_results) else None
            right_row = right_results[i] if i < len(right_results) else None

            if left_row is None:
                differences.append(ResultDifference(
                    path=f'row[{i}]',
                    left_value=None,
                    right_value=right_row,
                    difference_type='missing'
                ))
                total_comparisons += 1
                continue

            if right_row is None:
                differences.append(ResultDifference(
                    path=f'row[{i}]',
                    left_value=left_row,
                    right_value=None,
                    difference_type='missing'
                ))
                total_comparisons += 1
                continue

            # Compare row
            row_result = self._compare_rows(left_row, right_row,
                                           left_dialect, right_dialect, i)
            total_comparisons += 1

            if row_result.equal:
                equal_comparisons += 1
            else:
                # Parse reason to create structured differences
                diff = self._create_difference_from_row_result(row_result, i)
                differences.append(diff)

        different_comparisons = total_comparisons - equal_comparisons
        equality_percentage = (equal_comparisons / total_comparisons * 100) if total_comparisons > 0 else 0

        return ComparisonSummary(
            total_comparisons=total_comparisons,
            equal_comparisons=equal_comparisons,
            different_comparisons=different_comparisons,
            equality_percentage=equality_percentage,
            differences=differences
        )

    def _compare_rows(self, left_row: Dict[str, Any], right_row: Dict[str, Any],
                      left_dialect: str, right_dialect: str, row_index: int) -> ComparisonResult:
        """Compare two rows from result sets."""
        # Get all columns
        all_columns = set(left_row.keys()) | set(right_row.keys())

        # Compare each column
        for col in all_columns:
            left_val = left_row.get(col)
            right_val = right_row.get(col)

            result = self.comparator.compare(left_val, right_val,
                                            left_dialect, right_dialect,
                                            f'row[{row_index}].{col}')
            if not result.equal:
                return result

        return ComparisonResult(equal=True)

    def _create_difference_from_row_result(self, result: ComparisonResult, row_index: int) -> ResultDifference:
        """Create a ResultDifference from a ComparisonResult."""
        return ResultDifference(
            path=result.reason or f'row[{row_index}]',
            left_value=result.normalized_left,
            right_value=result.normalized_right,
            difference_type='value',
            tolerance=self.comparator.float_tolerance
        )


class DiffFormatter:
    """Format comparison differences for human-readable output."""

    @staticmethod
    def format_difference(diff: ResultDifference) -> str:
        """Format a single difference for display."""
        output = [f"  Path: {diff.path}"]

        if diff.difference_type == 'missing':
            output.append(f"  Type: {diff.difference_type}")
            if diff.left_value is None:
                output.append(f"  Missing in left, present in right: {diff.right_value}")
            else:
                output.append(f"  Present in left, missing in right: {diff.left_value}")
        else:
            output.append(f"  Type: {diff.difference_type}")
            output.append(f"  Left:  {DiffFormatter._format_value(diff.left_value)}")
            output.append(f"  Right: {DiffFormatter._format_value(diff.right_value)}")

            if diff.tolerance is not None:
                output.append(f"  Tolerance: {diff.tolerance}")

        return '\n'.join(output)

    @staticmethod
    def _format_value(value: Any, max_length: int = 100) -> str:
        """Format a value for display."""
        if value is None:
            return 'None'

        if isinstance(value, (list, dict)):
            json_str = json.dumps(value, indent=2, default=str)
            if len(json_str) > max_length:
                return json_str[:max_length] + '...'
            return json_str

        return str(value)

    @staticmethod
    def format_summary(summary: ComparisonSummary) -> str:
        """Format a comparison summary for display."""
        lines = [
            "Comparison Summary:",
            f"  Total comparisons: {summary.total_comparisons}",
            f"  Equal: {summary.equal_comparisons}",
            f"  Different: {summary.different_comparisons}",
            f"  Equality: {summary.equality_percentage:.1f}%"
        ]

        if summary.differences:
            lines.append(f"\nFirst {min(10, len(summary.differences))} differences:")
            for diff in summary.differences[:10]:
                lines.append('\n' + DiffFormatter.format_difference(diff))

        return '\n'.join(lines)


def compare_database_results(duckdb_result: Any,
                            postgresql_result: Any,
                            float_tolerance: float = ResultNormalizer.DEFAULT_FLOAT_TOLERANCE) -> ComparisonResult:
    """
    Convenience function to compare results from DuckDB and PostgreSQL.

    Args:
        duckdb_result: Result from DuckDB
        postgresql_result: Result from PostgreSQL
        float_tolerance: Tolerance for floating-point comparison

    Returns:
        ComparisonResult with comparison details
    """
    comparator = ValueComparator(float_tolerance)
    return comparator.compare(duckdb_result, postgresql_result,
                             left_dialect='duckdb',
                             right_dialect='postgresql')


def normalize_for_comparison(value: Any,
                            dialect: str,
                            float_tolerance: float = ResultNormalizer.DEFAULT_FLOAT_TOLERANCE) -> Any:
    """
    Convenience function to normalize a value for comparison.

    Args:
        value: Value to normalize
        dialect: Database dialect ('duckdb' or 'postgresql')
        float_tolerance: Tolerance for floating-point normalization

    Returns:
        Normalized value
    """
    normalizer = ResultNormalizer(float_tolerance)
    return normalizer.normalize(value, dialect)


# Export default tolerance at module level for convenience
DEFAULT_FLOAT_TOLERANCE = ResultNormalizer.DEFAULT_FLOAT_TOLERANCE


__all__ = [
    'ComparisonResult',
    'ResultDifference',
    'ComparisonSummary',
    'ResultNormalizer',
    'ValueComparator',
    'ResultsetComparator',
    'DiffFormatter',
    'ComparisonResult',
    'ComparisonSummary',
    'ResultDifference',
    'compare_database_results',
    'normalize_for_comparison',
    'DEFAULT_FLOAT_TOLERANCE',
]
