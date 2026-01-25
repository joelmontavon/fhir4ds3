"""
FHIR Temporal Value Parser

Parses FHIR date, dateTime, time, and instant values from string literals,
preserving precision and timezone information for boundary calculations.

Handles FHIRPath temporal literal syntax:
    - Date: @2014, @2014-01, @2014-01-05
    - DateTime: @2014-01-05T10:30, @2014-01-05T10:30:00.000, @2014-01-05T10:30:00.000-05:00
    - Time: @T10:30, @T10:30:00, @T10:30:00.000
    - Instant: @2014-01-05T10:30:00.000Z (always includes timezone)
"""

from typing import Optional, Tuple
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemporalPrecision:
    """Represents precision information for temporal values."""
    year: bool = False
    month: bool = False
    day: bool = False
    hour: bool = False
    minute: bool = False
    second: bool = False
    millisecond: bool = False
    has_timezone: bool = False

    def get_precision_value(self) -> int:
        """
        Get numeric precision value per FHIRPath specification.

        Returns:
            Precision as character count:
                4 = year (YYYY)
                6 = month (YYYY-MM)
                8 = day (YYYY-MM-DD)
                10 = hour (YYYY-MM-DDTHH)
                13 = minute (YYYY-MM-DDTHH:MM)
                16 = second (YYYY-MM-DDTHH:MM:SS)
                17 = millisecond with timezone (YYYY-MM-DDTHH:MM:SS.sss±HH:MM)
                9 = time millisecond (THH:MM:SS.sss)
        """
        if self.millisecond and self.has_timezone:
            return 17
        elif self.millisecond:
            return 16  # or 9 for Time
        elif self.second:
            return 16
        elif self.minute:
            return 13
        elif self.hour:
            return 10
        elif self.day:
            return 8
        elif self.month:
            return 6
        elif self.year:
            return 4
        else:
            return 4  # Default to year


@dataclass
class ParsedTemporal:
    """Result of parsing a FHIR temporal value."""
    original: str
    temporal_type: str  # 'Date', 'DateTime', 'Time', 'Instant'
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    second: Optional[int] = None
    millisecond: Optional[int] = None
    timezone_offset: Optional[str] = None  # e.g., "-05:00", "+14:00", "Z"
    precision: Optional[TemporalPrecision] = None

    def __post_init__(self):
        """Automatically determine precision after initialization."""
        if self.precision is None:
            self.precision = TemporalPrecision(
                year=self.year is not None,
                month=self.month is not None,
                day=self.day is not None,
                hour=self.hour is not None,
                minute=self.minute is not None,
                second=self.second is not None,
                millisecond=self.millisecond is not None,
                has_timezone=self.timezone_offset is not None
            )

    def get_precision_value(self) -> int:
        """Get numeric precision value."""
        if self.precision:
            # Special case for Time type
            if self.temporal_type == 'Time' and self.millisecond is not None:
                return 9  # Time with milliseconds
            return self.precision.get_precision_value()
        return 4  # Default


class FHIRTemporalParser:
    """
    Parser for FHIR temporal literals in FHIRPath expressions.

    Handles the full range of FHIR date/time formats with precision preservation.
    """

    # Regex patterns for different temporal formats
    # Date: @YYYY, @YYYY-MM, @YYYY-MM-DD
    DATE_PATTERN = re.compile(
        r'^@(?P<year>\d{4})(?:-(?P<month>\d{2}))?(?:-(?P<day>\d{2}))?$'
    )

    # Partial DateTime: @YYYYT, @YYYY-MMT, @YYYY-MM-DDT (no time components, just T suffix)
    # These are DateTime literals (not Date) because they have the 'T' suffix
    PARTIAL_DATETIME_PATTERN = re.compile(
        r'^@(?P<year>\d{4})(?:-(?P<month>\d{2}))?(?:-(?P<day>\d{2}))?T$'
    )

    # DateTime: @YYYY-MM-DDTHH:MM:SS.sss±HH:MM
    DATETIME_PATTERN = re.compile(
        r'^@(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
        r'T(?P<hour>\d{2})(?::(?P<minute>\d{2}))?(?::(?P<second>\d{2}))?'
        r'(?:\.(?P<millisecond>\d{3}))?'
        r'(?P<timezone>[+-]\d{2}:\d{2}|Z)?$'
    )

    # Time: @THH:MM:SS.sss
    TIME_PATTERN = re.compile(
        r'^@T(?P<hour>\d{2})(?::(?P<minute>\d{2}))?(?::(?P<second>\d{2}))?'
        r'(?:\.(?P<millisecond>\d{3}))?$'
    )

    def __init__(self):
        """Initialize temporal parser."""
        pass

    def parse(self, temporal_literal: str) -> Optional[ParsedTemporal]:
        """
        Parse a FHIR temporal literal string.

        Args:
            temporal_literal: Temporal literal (e.g., "@2014-01-05T10:30-05:00")

        Returns:
            ParsedTemporal object with extracted components, or None if invalid

        Examples:
            >>> parser = FHIRTemporalParser()
            >>> result = parser.parse("@2014")
            >>> result.temporal_type
            'Date'
            >>> result.year
            2014
            >>> result.precision.year
            True
            >>> result.precision.month
            False
        """
        if not temporal_literal or not temporal_literal.startswith('@'):
            return None

        # Try DateTime pattern first (most specific - full date with time)
        match = self.DATETIME_PATTERN.match(temporal_literal)
        if match:
            return self._parse_datetime(temporal_literal, match)

        # Try Partial DateTime pattern (date components with 'T' suffix but no time)
        # SP-101-003: Handle @YYYYT, @YYYY-MMT, @YYYY-MM-DDT as partial DateTime
        match = self.PARTIAL_DATETIME_PATTERN.match(temporal_literal)
        if match:
            return self._parse_partial_datetime(temporal_literal, match)

        # Try Time pattern
        match = self.TIME_PATTERN.match(temporal_literal)
        if match:
            return self._parse_time(temporal_literal, match)

        # Try Date pattern (least specific)
        match = self.DATE_PATTERN.match(temporal_literal)
        if match:
            return self._parse_date(temporal_literal, match)

        logger.warning(f"Failed to parse temporal literal: {temporal_literal}")
        return None

    def _parse_date(self, original: str, match: re.Match) -> ParsedTemporal:
        """Parse a Date literal."""
        groups = match.groupdict()

        return ParsedTemporal(
            original=original,
            temporal_type='Date',
            year=int(groups['year']),
            month=int(groups['month']) if groups.get('month') else None,
            day=int(groups['day']) if groups.get('day') else None
        )

    def _parse_partial_datetime(self, original: str, match: re.Match) -> ParsedTemporal:
        """Parse a partial DateTime literal (date components with 'T' suffix).

        SP-101-003: FHIRPath allows partial DateTime literals like:
        - @2015T (year-only DateTime)
        - @2015-02T (year-month DateTime)
        - @2015-02-04T (year-month-day DateTime with no time)

        These are distinct from Date literals because they include the 'T' suffix,
        indicating they are DateTime types (even though time components are omitted).
        """
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

    def _parse_datetime(self, original: str, match: re.Match) -> ParsedTemporal:
        """Parse a DateTime literal."""
        groups = match.groupdict()

        timezone = groups.get('timezone')
        if timezone == 'Z':
            timezone = '+00:00'  # Convert Z to explicit +00:00

        return ParsedTemporal(
            original=original,
            temporal_type='DateTime',
            year=int(groups['year']),
            month=int(groups['month']),
            day=int(groups['day']),
            hour=int(groups['hour']),
            minute=int(groups['minute']) if groups.get('minute') else None,
            second=int(groups['second']) if groups.get('second') else None,
            millisecond=int(groups['millisecond']) if groups.get('millisecond') else None,
            timezone_offset=timezone
        )

    def _parse_time(self, original: str, match: re.Match) -> ParsedTemporal:
        """Parse a Time literal."""
        groups = match.groupdict()

        return ParsedTemporal(
            original=original,
            temporal_type='Time',
            hour=int(groups['hour']),
            minute=int(groups['minute']) if groups.get('minute') else None,
            second=int(groups['second']) if groups.get('second') else None,
            millisecond=int(groups['millisecond']) if groups.get('millisecond') else None
        )

    def detect_type(self, temporal_literal: str) -> Optional[str]:
        """
        Quickly detect the type of a temporal literal without full parsing.

        Args:
            temporal_literal: Temporal literal string

        Returns:
            'Date', 'DateTime', 'Time', or None if not recognized
        """
        if not temporal_literal or not temporal_literal.startswith('@'):
            return None

        if temporal_literal.startswith('@T'):
            return 'Time'
        elif 'T' in temporal_literal:
            # SP-101-003: Any 'T' in the literal (excluding @T prefix) indicates DateTime
            return 'DateTime'
        else:
            return 'Date'


# Global parser instance
_global_parser: Optional[FHIRTemporalParser] = None


def get_temporal_parser() -> FHIRTemporalParser:
    """
    Get the global temporal parser instance.

    Returns:
        Global FHIRTemporalParser instance
    """
    global _global_parser
    if _global_parser is None:
        _global_parser = FHIRTemporalParser()
    return _global_parser


def parse_temporal(temporal_literal: str) -> Optional[ParsedTemporal]:
    """
    Convenience function to parse temporal using global parser.

    Args:
        temporal_literal: Temporal literal string

    Returns:
        ParsedTemporal object or None
    """
    parser = get_temporal_parser()
    return parser.parse(temporal_literal)
