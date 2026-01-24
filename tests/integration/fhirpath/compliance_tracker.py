"""
FHIRPath Compliance Tracking and Measurement System

Automated compliance tracking, trend analysis, and reporting for FHIRPath
specification compliance across multiple test runs and database environments.
"""

import json
import sqlite3
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from tests.integration.fhirpath.official_test_runner import ComplianceReport, EnhancedOfficialTestRunner


@dataclass
class ComplianceTrend:
    """Compliance trend analysis over time"""
    timeframe: str
    start_date: str
    end_date: str
    compliance_change: float
    performance_change_ms: float
    test_count_change: int
    trend_direction: str  # "improving", "declining", "stable"
    confidence: float  # 0.0 to 1.0


@dataclass
class ComplianceMetrics:
    """Comprehensive compliance metrics"""
    current_compliance: float
    target_compliance: float
    compliance_gap: float
    days_to_target: Optional[int]
    improvement_rate: float  # compliance % per day
    recent_trend: str
    quality_score: float  # Overall quality assessment


class ComplianceDatabase:
    """SQLite database for storing compliance history"""

    def __init__(self, db_path: str = "compliance_history.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize compliance tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                database_type TEXT NOT NULL,
                parser_type TEXT NOT NULL,
                total_tests INTEGER NOT NULL,
                passed_tests INTEGER NOT NULL,
                failed_tests INTEGER NOT NULL,
                compliance_percentage REAL NOT NULL,
                execution_time_total_ms REAL NOT NULL,
                execution_time_average_ms REAL NOT NULL,
                report_data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON compliance_reports(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_database_type
            ON compliance_reports(database_type)
        """)

        conn.commit()
        conn.close()

    def store_report(self, report: ComplianceReport) -> int:
        """Store compliance report in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO compliance_reports (
                timestamp, database_type, parser_type, total_tests,
                passed_tests, failed_tests, compliance_percentage,
                execution_time_total_ms, execution_time_average_ms, report_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.timestamp,
            report.database_type,
            report.parser_type,
            report.total_tests,
            report.passed_tests,
            report.failed_tests,
            report.compliance_percentage,
            report.execution_time_total_ms,
            report.execution_time_average_ms,
            json.dumps(asdict(report))
        ))

        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return report_id

    def get_reports(self,
                   database_type: Optional[str] = None,
                   days_back: Optional[int] = None,
                   limit: Optional[int] = None) -> List[ComplianceReport]:
        """Retrieve compliance reports from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT report_data FROM compliance_reports"
        params = []

        conditions = []
        if database_type:
            conditions.append("database_type = ?")
            params.append(database_type)

        if days_back:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            conditions.append("timestamp >= ?")
            params.append(cutoff_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        reports = []
        for row in rows:
            report_data = json.loads(row[0])
            reports.append(ComplianceReport(**report_data))

        return reports


class ComplianceTracker:
    """
    Automated Compliance Tracking and Measurement System

    Tracks FHIRPath compliance over time, measures improvement trends,
    and provides actionable insights for achieving compliance targets.
    """

    def __init__(self, db_path: str = "compliance_history.db"):
        self.database = ComplianceDatabase(db_path)
        self.target_compliance = 60.0  # Target 60% as per task requirements

    def track_compliance(self, database_type: str = "duckdb", max_tests: Optional[int] = None) -> ComplianceReport:
        """
        Run compliance measurement and store results

        Args:
            database_type: Database type for testing
            max_tests: Maximum number of tests (None for all)

        Returns:
            Compliance report with tracking metadata
        """
        print(f"Running compliance tracking for {database_type}...")

        # Run official test suite
        runner = EnhancedOfficialTestRunner(database_type)
        report = runner.run_official_tests(max_tests=max_tests)

        # Store in database
        report_id = self.database.store_report(report)
        print(f"Compliance report stored with ID: {report_id}")

        return report

    def analyze_compliance_trend(self,
                                database_type: str = "duckdb",
                                days_back: int = 30) -> ComplianceTrend:
        """
        Analyze compliance trend over specified timeframe

        Args:
            database_type: Database type to analyze
            days_back: Number of days to look back

        Returns:
            Trend analysis results
        """
        reports = self.database.get_reports(database_type=database_type, days_back=days_back)

        if len(reports) < 2:
            return ComplianceTrend(
                timeframe=f"{days_back} days",
                start_date="",
                end_date="",
                compliance_change=0.0,
                performance_change_ms=0.0,
                test_count_change=0,
                trend_direction="insufficient_data",
                confidence=0.0
            )

        # Sort by timestamp
        reports.sort(key=lambda r: r.timestamp)
        start_report = reports[0]
        end_report = reports[-1]

        compliance_change = end_report.compliance_percentage - start_report.compliance_percentage
        performance_change = end_report.execution_time_average_ms - start_report.execution_time_average_ms
        test_count_change = end_report.total_tests - start_report.total_tests

        # Determine trend direction
        if compliance_change > 1.0:
            trend_direction = "improving"
        elif compliance_change < -1.0:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        # Calculate confidence based on number of data points and consistency
        confidence = min(len(reports) / 10.0, 1.0)  # More reports = higher confidence

        return ComplianceTrend(
            timeframe=f"{days_back} days",
            start_date=start_report.timestamp,
            end_date=end_report.timestamp,
            compliance_change=compliance_change,
            performance_change_ms=performance_change,
            test_count_change=test_count_change,
            trend_direction=trend_direction,
            confidence=confidence
        )

    def get_compliance_metrics(self, database_type: str = "duckdb") -> ComplianceMetrics:
        """
        Get comprehensive compliance metrics and projections

        Args:
            database_type: Database type to analyze

        Returns:
            Compliance metrics with projections
        """
        # Get recent reports (don't filter by days for metrics calculation)
        recent_reports = self.database.get_reports(database_type=database_type, limit=10)

        if not recent_reports:
            return ComplianceMetrics(
                current_compliance=0.0,
                target_compliance=self.target_compliance,
                compliance_gap=self.target_compliance,
                days_to_target=None,
                improvement_rate=0.0,
                recent_trend="no_data",
                quality_score=0.0
            )

        current_compliance = recent_reports[0].compliance_percentage
        compliance_gap = self.target_compliance - current_compliance

        # Calculate improvement rate
        improvement_rate = 0.0
        days_to_target = None

        if len(recent_reports) >= 2:
            sorted_reports = sorted(recent_reports, key=lambda r: r.timestamp)
            oldest = sorted_reports[0]
            newest = sorted_reports[-1]

            date_diff = (
                datetime.fromisoformat(newest.timestamp) -
                datetime.fromisoformat(oldest.timestamp)
            ).days

            if date_diff > 0:
                compliance_diff = newest.compliance_percentage - oldest.compliance_percentage
                improvement_rate = compliance_diff / date_diff

                if improvement_rate > 0 and compliance_gap > 0:
                    days_to_target = int(compliance_gap / improvement_rate)

        # Determine trend
        trend = self.analyze_compliance_trend(database_type=database_type)
        recent_trend = trend.trend_direction

        # Calculate quality score (based on compliance, performance, and trend)
        quality_score = min(current_compliance / 100.0, 1.0)  # Base score from compliance
        if recent_trend == "improving":
            quality_score += 0.1
        elif recent_trend == "declining":
            quality_score -= 0.1

        # Performance factor (lower execution time is better)
        avg_exec_time = statistics.mean([r.execution_time_average_ms for r in recent_reports])
        if avg_exec_time < 50:  # Under 50ms is good
            quality_score += 0.1

        quality_score = max(0.0, min(1.0, quality_score))

        return ComplianceMetrics(
            current_compliance=current_compliance,
            target_compliance=self.target_compliance,
            compliance_gap=compliance_gap,
            days_to_target=days_to_target,
            improvement_rate=improvement_rate,
            recent_trend=recent_trend,
            quality_score=quality_score
        )

    def generate_compliance_dashboard(self, database_types: List[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive compliance dashboard

        Args:
            database_types: List of database types to include (defaults to ["duckdb", "postgresql"])

        Returns:
            Dashboard data with metrics for all database types
        """
        if database_types is None:
            database_types = ["duckdb", "postgresql"]

        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "target_compliance": self.target_compliance,
            "databases": {}
        }

        for db_type in database_types:
            metrics = self.get_compliance_metrics(db_type)
            trend = self.analyze_compliance_trend(db_type)
            recent_reports = self.database.get_reports(database_type=db_type, limit=5)

            dashboard["databases"][db_type] = {
                "metrics": asdict(metrics),
                "trend": asdict(trend),
                "recent_compliance_history": [
                    {
                        "timestamp": r.timestamp,
                        "compliance": r.compliance_percentage,
                        "tests": r.total_tests,
                        "avg_time_ms": r.execution_time_average_ms
                    }
                    for r in recent_reports
                ]
            }

        return dashboard

    def print_compliance_summary(self, database_type: str = "duckdb") -> None:
        """Print formatted compliance tracking summary"""
        metrics = self.get_compliance_metrics(database_type)
        trend = self.analyze_compliance_trend(database_type)

        print("\n" + "="*60)
        print("COMPLIANCE TRACKING SUMMARY")
        print("="*60)
        print(f"Database Type: {database_type}")
        print(f"Current Compliance: {metrics.current_compliance:.1f}%")
        print(f"Target Compliance: {metrics.target_compliance:.1f}%")
        print(f"Compliance Gap: {metrics.compliance_gap:.1f}%")
        print(f"Quality Score: {metrics.quality_score:.2f}/1.0")

        print(f"\nTrend Analysis ({trend.timeframe}):")
        print(f"  Direction: {trend.trend_direction}")
        print(f"  Compliance Change: {trend.compliance_change:+.1f}%")
        print(f"  Performance Change: {trend.performance_change_ms:+.1f}ms")
        print(f"  Confidence: {trend.confidence:.1f}/1.0")

        if metrics.improvement_rate > 0:
            print(f"\nProjections:")
            print(f"  Improvement Rate: {metrics.improvement_rate:.2f}% per day")
            if metrics.days_to_target:
                print(f"  Estimated Days to Target: {metrics.days_to_target}")
        else:
            print(f"\nNote: No consistent improvement trend detected")

    def export_compliance_data(self, output_path: Path, database_type: Optional[str] = None) -> Path:
        """Export compliance data to JSON file"""
        dashboard = self.generate_compliance_dashboard(
            database_types=[database_type] if database_type else None
        )

        with open(output_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

        return output_path


def track_fhirpath_compliance(database_type: str = "duckdb", max_tests: Optional[int] = None) -> ComplianceMetrics:
    """
    Convenience function for compliance tracking

    Args:
        database_type: Database type for testing
        max_tests: Maximum number of tests to run

    Returns:
        Current compliance metrics
    """
    tracker = ComplianceTracker()

    # Run compliance measurement
    report = tracker.track_compliance(database_type, max_tests)

    # Get metrics and print summary
    metrics = tracker.get_compliance_metrics(database_type)
    tracker.print_compliance_summary(database_type)

    return metrics


if __name__ == "__main__":
    # Demonstrate compliance tracking
    print("Demonstrating FHIRPath compliance tracking...")

    # Track compliance for DuckDB with limited tests
    metrics = track_fhirpath_compliance(database_type="duckdb", max_tests=100)

    # Export compliance data
    tracker = ComplianceTracker()
    output_path = tracker.export_compliance_data(Path("compliance_dashboard.json"))
    print(f"\nCompliance dashboard exported to: {output_path}")