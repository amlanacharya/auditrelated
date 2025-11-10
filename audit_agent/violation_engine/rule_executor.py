"""
Rule Executor: Run violation detection rules and aggregate results

Features:
- Parallel rule execution
- Result deduplication
- Severity-based prioritization
- Full audit trail
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from datetime import date
import pandas as pd
import structlog

from audit_agent.data_layer import QueryEngine
from audit_agent.knowledge_graph import KnowledgeGraphManager, ViolationGraph
from audit_agent.observability import MetricsCollector

logger = structlog.get_logger()


class RuleExecutor:
    """Execute violation detection rules"""

    def __init__(
        self,
        parquet_path: str = "data/parquet",
        kg_db_path: str = "data/kg.db",
        num_threads: int = 4
    ):
        """
        Initialize rule executor

        Args:
            parquet_path: Path to Parquet files
            kg_db_path: Path to Knowledge Graph database
            num_threads: Number of parallel execution threads
        """
        self.query_engine = QueryEngine(parquet_path, num_threads=num_threads)
        self.kg_manager = KnowledgeGraphManager(kg_db_path)
        self.violation_graph = ViolationGraph(self.kg_manager)
        self.metrics = MetricsCollector()
        self.num_threads = num_threads

        # Register Parquet tables
        self._register_tables()

    def _register_tables(self):
        """Register all Parquet tables with DuckDB"""
        tables = ["employees", "vendors", "expenses", "approvals", "payments"]

        for table_name in tables:
            try:
                self.query_engine.register_parquet_table(table_name)
                logger.info("table_registered", table=table_name)
            except Exception as e:
                logger.warning("table_registration_failed", table=table_name, error=str(e))

    def run_all_rules(
        self,
        as_of_date: Optional[date] = None,
        parallel: bool = True
    ) -> pd.DataFrame:
        """
        Execute all active violation rules

        Args:
            as_of_date: Date to check rules for (default: today)
            parallel: Run rules in parallel (default: True)

        Returns:
            DataFrame with all violations detected
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get active rules
        active_rules = self.violation_graph.get_active_rules(as_of_date)

        if not active_rules:
            logger.warning("no_active_rules")
            return pd.DataFrame()

        logger.info("executing_rules",
                    count=len(active_rules),
                    parallel=parallel)

        all_violations = []

        if parallel:
            # Execute rules in parallel
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                future_to_rule = {
                    executor.submit(self._execute_rule, rule): rule
                    for rule in active_rules
                }

                for future in as_completed(future_to_rule):
                    rule = future_to_rule[future]
                    try:
                        violations = future.result()
                        if not violations.empty:
                            all_violations.append(violations)
                    except Exception as e:
                        logger.error("rule_execution_failed",
                                    rule=rule["rule_name"],
                                    error=str(e))
        else:
            # Execute rules sequentially
            for rule in active_rules:
                try:
                    violations = self._execute_rule(rule)
                    if not violations.empty:
                        all_violations.append(violations)
                except Exception as e:
                    logger.error("rule_execution_failed",
                                rule=rule["rule_name"],
                                error=str(e))

        # Combine all violations
        if all_violations:
            combined = pd.concat(all_violations, ignore_index=True)

            # Sort by severity and amount
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            combined["severity_rank"] = combined["severity"].map(severity_order)
            combined = combined.sort_values(["severity_rank", "amount"], ascending=[True, False])
            combined = combined.drop("severity_rank", axis=1)

            logger.info("rule_execution_completed",
                       total_violations=len(combined),
                       unique_expenses=combined["expense_id"].nunique())

            return combined
        else:
            logger.info("no_violations_detected")
            return pd.DataFrame()

    def _execute_rule(self, rule: Dict) -> pd.DataFrame:
        """
        Execute a single violation rule

        Args:
            rule: Rule dict from KG

        Returns:
            DataFrame of violations
        """
        rule_name = rule["rule_name"]
        severity = rule["severity"]
        sql = rule["sql_template"]

        start_time = time.time()

        try:
            # Execute SQL query
            violations = self.query_engine.execute_query(
                sql,
                query_name=rule_name,
                return_df=True
            )

            duration = time.time() - start_time

            # Record metrics
            self.metrics.record_violation_detection(
                rule_name=rule_name,
                severity=severity,
                violation_count=len(violations),
                query_duration=duration
            )

            # Add metadata if violations found
            if not violations.empty and "rule_name" not in violations.columns:
                violations["rule_name"] = rule_name
                violations["severity"] = severity
                violations["detected_at"] = pd.Timestamp.now()

            return violations

        except Exception as e:
            logger.error("rule_execution_error",
                        rule=rule_name,
                        error=str(e))
            raise

    def run_single_rule(
        self,
        rule_id: str,
        as_of_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Execute a specific rule by ID

        Args:
            rule_id: Rule identifier
            as_of_date: Date to check rule for (default: today)

        Returns:
            DataFrame of violations
        """
        if as_of_date is None:
            as_of_date = date.today()

        rule = self.violation_graph.get_rule_by_id(rule_id)

        if not rule:
            logger.error("rule_not_found", rule_id=rule_id)
            return pd.DataFrame()

        return self._execute_rule(rule)

    def get_violation_summary(self, violations: pd.DataFrame) -> Dict:
        """
        Get summary statistics for violations

        Args:
            violations: DataFrame of violations

        Returns:
            Summary dict
        """
        if violations.empty:
            return {
                "total_violations": 0,
                "by_severity": {},
                "by_rule": {},
                "total_financial_impact": 0,
            }

        summary = {
            "total_violations": len(violations),
            "by_severity": violations["severity"].value_counts().to_dict(),
            "by_rule": violations["rule_name"].value_counts().to_dict(),
            "unique_expenses": violations["expense_id"].nunique() if "expense_id" in violations.columns else 0,
        }

        # Calculate financial impact if amount column exists
        if "amount" in violations.columns:
            summary["total_financial_impact"] = float(violations["amount"].sum())
            summary["avg_violation_amount"] = float(violations["amount"].mean())

        return summary

    def export_violations(
        self,
        violations: pd.DataFrame,
        output_path: str,
        format: str = "csv"
    ):
        """
        Export violations to file

        Args:
            violations: DataFrame of violations
            output_path: Path to save file
            format: Output format (csv, json, excel)
        """
        if format == "csv":
            violations.to_csv(output_path, index=False)
        elif format == "json":
            violations.to_json(output_path, orient="records", indent=2)
        elif format == "excel":
            violations.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info("violations_exported",
                   path=output_path,
                   count=len(violations),
                   format=format)

    def close(self):
        """Clean up resources"""
        self.query_engine.close()
        self.kg_manager.close()
        logger.info("rule_executor_closed")
