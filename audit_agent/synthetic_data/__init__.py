"""
Synthetic Data Generation: Create realistic POC datasets with violations

Generates:
- Employees (500) with reporting hierarchies
- Expenses (10,000) with intentional violations
- Approvals, Payments, Vendors
"""

from audit_agent.synthetic_data.generator import DatasetGenerator

__all__ = ["DatasetGenerator"]
