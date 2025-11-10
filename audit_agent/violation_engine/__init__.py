"""
Violation Engine: Execute SQL-based violation detection rules

Components:
- RuleExecutor: Run violation rules in parallel
- Results aggregation and reporting
"""

from audit_agent.violation_engine.rule_executor import RuleExecutor

__all__ = ["RuleExecutor"]
