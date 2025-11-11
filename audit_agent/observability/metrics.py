"""
Metrics Collector: Track system performance and data quality

Metrics tracked:
- Data health: row counts, schema drift, null percentages
- Detection performance: violations by type, false positive rate
- System performance: query times, memory usage
"""

import time
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, REGISTRY
import structlog

logger = structlog.get_logger()


class MetricsCollector:
    """Collect and track system metrics"""

    def __init__(self):
        """Initialize metrics collectors (idempotent - safe to call multiple times)"""

        # Data health metrics - use existing if already registered
        try:
            self.table_row_counts = Gauge(
                "audit_table_row_count",
                "Number of rows in each table",
                ["table_name"]
            )
        except ValueError:
            # Metric already exists, retrieve it
            self.table_row_counts = REGISTRY._names_to_collectors.get("audit_table_row_count")

        try:
            self.schema_drift_alerts = Counter(
                "audit_schema_drift_total",
                "Number of schema drift incidents",
                ["table_name"]
            )
        except ValueError:
            self.schema_drift_alerts = REGISTRY._names_to_collectors.get("audit_schema_drift_total")

        # Detection metrics
        try:
            self.violations_detected = Counter(
                "audit_violations_detected_total",
                "Number of violations detected",
                ["rule_name", "severity"]
            )
        except ValueError:
            self.violations_detected = REGISTRY._names_to_collectors.get("audit_violations_detected_total")

        try:
            self.query_duration = Histogram(
                "audit_query_duration_seconds",
                "Query execution time",
                ["query_type"]
            )
        except ValueError:
            self.query_duration = REGISTRY._names_to_collectors.get("audit_query_duration_seconds")

        # System metrics
        try:
            self.active_rules = Gauge(
                "audit_active_rules",
                "Number of active violation rules"
            )
        except ValueError:
            self.active_rules = REGISTRY._names_to_collectors.get("audit_active_rules")

        self.metrics_data = {
            "data_quality": [],
            "violations": [],
            "performance": [],
        }

    def record_table_ingestion(
        self,
        table_name: str,
        row_count: int,
        column_count: int,
        duration_seconds: float
    ):
        """
        Record metrics for data ingestion

        Args:
            table_name: Name of ingested table
            row_count: Number of rows
            column_count: Number of columns
            duration_seconds: Time taken
        """
        self.table_row_counts.labels(table_name=table_name).set(row_count)

        self.metrics_data["data_quality"].append({
            "timestamp": datetime.now(),
            "table_name": table_name,
            "row_count": row_count,
            "column_count": column_count,
            "duration_seconds": duration_seconds,
        })

        logger.info("ingestion_metrics",
                    table=table_name,
                    rows=row_count,
                    duration=duration_seconds)

    def record_violation_detection(
        self,
        rule_name: str,
        severity: str,
        violation_count: int,
        query_duration: float
    ):
        """
        Record violation detection metrics

        Args:
            rule_name: Name of the rule
            severity: Severity level
            violation_count: Number of violations found
            query_duration: Time taken to run rule
        """
        self.violations_detected.labels(
            rule_name=rule_name,
            severity=severity
        ).inc(violation_count)

        self.query_duration.labels(query_type="violation_rule").observe(query_duration)

        self.metrics_data["violations"].append({
            "timestamp": datetime.now(),
            "rule_name": rule_name,
            "severity": severity,
            "violation_count": violation_count,
            "query_duration": query_duration,
        })

        if violation_count > 0:
            logger.warning("violations_found",
                          rule=rule_name,
                          count=violation_count,
                          severity=severity)

    def record_query_performance(
        self,
        query_name: str,
        duration_seconds: float,
        row_count: int
    ):
        """
        Record query performance

        Args:
            query_name: Name of the query
            duration_seconds: Execution time
            row_count: Rows returned
        """
        self.query_duration.labels(query_type="adhoc").observe(duration_seconds)

        self.metrics_data["performance"].append({
            "timestamp": datetime.now(),
            "query_name": query_name,
            "duration_seconds": duration_seconds,
            "row_count": row_count,
        })

    def record_schema_drift(self, table_name: str, details: Dict):
        """
        Record schema drift alert

        Args:
            table_name: Table with schema change
            details: Details of the drift
        """
        self.schema_drift_alerts.labels(table_name=table_name).inc()

        logger.error("schema_drift_detected",
                    table=table_name,
                    details=details)

    def get_data_quality_report(self) -> pd.DataFrame:
        """Get data quality metrics as DataFrame"""
        if not self.metrics_data["data_quality"]:
            return pd.DataFrame()

        return pd.DataFrame(self.metrics_data["data_quality"])

    def get_violation_summary(self) -> pd.DataFrame:
        """Get violation detection summary"""
        if not self.metrics_data["violations"]:
            return pd.DataFrame()

        df = pd.DataFrame(self.metrics_data["violations"])

        # Aggregate by rule and severity
        summary = df.groupby(["rule_name", "severity"]).agg({
            "violation_count": "sum",
            "query_duration": "mean"
        }).reset_index()

        return summary

    def get_performance_summary(self) -> Dict:
        """Get performance statistics"""
        if not self.metrics_data["performance"]:
            return {}

        df = pd.DataFrame(self.metrics_data["performance"])

        return {
            "total_queries": len(df),
            "avg_duration": df["duration_seconds"].mean(),
            "max_duration": df["duration_seconds"].max(),
            "total_rows_processed": df["row_count"].sum(),
        }

    def check_health(self) -> Dict:
        """
        Check system health

        Returns:
            Health status dict
        """
        health = {
            "status": "healthy",
            "checks": [],
        }

        # Check: Recent violations
        recent_violations = pd.DataFrame(self.metrics_data["violations"])
        if not recent_violations.empty:
            critical_count = recent_violations[
                recent_violations["severity"] == "critical"
            ]["violation_count"].sum()

            if critical_count > 100:
                health["checks"].append({
                    "check": "critical_violations",
                    "status": "warning",
                    "message": f"{critical_count} critical violations detected"
                })
                health["status"] = "degraded"

        # Check: Query performance
        perf_stats = self.get_performance_summary()
        if perf_stats and perf_stats["avg_duration"] > 10:
            health["checks"].append({
                "check": "query_performance",
                "status": "warning",
                "message": f"Average query time: {perf_stats['avg_duration']:.2f}s"
            })
            health["status"] = "degraded"

        if not health["checks"]:
            health["checks"].append({
                "check": "overall",
                "status": "ok",
                "message": "All systems operational"
            })

        return health

    def export_metrics(self, output_path: str):
        """
        Export all metrics to JSON

        Args:
            output_path: Path to save metrics
        """
        import json

        export_data = {
            "data_quality": [
                {**m, "timestamp": m["timestamp"].isoformat()}
                for m in self.metrics_data["data_quality"]
            ],
            "violations": [
                {**m, "timestamp": m["timestamp"].isoformat()}
                for m in self.metrics_data["violations"]
            ],
            "performance": [
                {**m, "timestamp": m["timestamp"].isoformat()}
                for m in self.metrics_data["performance"]
            ],
            "exported_at": datetime.now().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info("metrics_exported", path=output_path)
