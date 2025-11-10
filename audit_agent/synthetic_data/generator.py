"""
Dataset Generator: Create synthetic audit data with realistic violations

Generates quarterly data with intentional violations:
- Self-approvals: 50 (5%)
- Duplicates: 30 (3%)
- Split transactions: 20 (2%)
- Missing approvals: 200 (20%)
- Timeline violations: 100 (10%)
"""

import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
import numpy as np
from faker import Faker
import structlog

logger = structlog.get_logger()

fake = Faker()
Faker.seed(42)  # Reproducible data
random.seed(42)
np.random.seed(42)


class DatasetGenerator:
    """Generate synthetic audit datasets"""

    def __init__(
        self,
        num_employees: int = 500,
        num_expenses: int = 10000,
        start_date: str = "2024-01-01",
        end_date: str = "2024-03-31"
    ):
        """
        Initialize dataset generator

        Args:
            num_employees: Number of employees to generate
            num_expenses: Number of expense transactions
            start_date: Start of data period
            end_date: End of data period
        """
        self.num_employees = num_employees
        self.num_expenses = num_expenses
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")

        # Violation targets
        self.violation_config = {
            "self_approvals": 50,
            "duplicates": 30,
            "split_transactions": 20,
            "missing_approvals": 200,
            "timeline_violations": 100,
        }

        self.employees = None
        self.vendors = None
        self.expenses = None
        self.approvals = None
        self.payments = None

    def generate_dataset(self, output_dir: str = "data/raw") -> Dict:
        """
        Generate complete dataset

        Args:
            output_dir: Directory to save CSV files

        Returns:
            Dict with dataset statistics
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("dataset_generation_started",
                    employees=self.num_employees,
                    expenses=self.num_expenses)

        # Generate core entities
        self.employees = self._generate_employees()
        self.vendors = self._generate_vendors()
        self.expenses = self._generate_expenses()
        self.approvals = self._generate_approvals()
        self.payments = self._generate_payments()

        # Save to CSV
        self.employees.to_csv(output_path / "employees.csv", index=False)
        self.vendors.to_csv(output_path / "vendors.csv", index=False)
        self.expenses.to_csv(output_path / "expenses.csv", index=False)
        self.approvals.to_csv(output_path / "approvals.csv", index=False)
        self.payments.to_csv(output_path / "payments.csv", index=False)

        stats = {
            "employees": len(self.employees),
            "vendors": len(self.vendors),
            "expenses": len(self.expenses),
            "approvals": len(self.approvals),
            "payments": len(self.payments),
            "violations_injected": self.violation_config,
            "output_directory": str(output_path),
        }

        logger.info("dataset_generation_completed", **stats)

        return stats

    def _generate_employees(self) -> pd.DataFrame:
        """Generate employee data with reporting hierarchy"""

        employees = []

        # Create organizational structure
        # Level 1: CEO (1)
        # Level 2: Directors (10)
        # Level 3: Managers (50)
        # Level 4: Employees (439)

        employee_id = 1

        # CEO
        employees.append({
            "employee_id": employee_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": f"ceo@company.com",
            "department": "Executive",
            "title": "CEO",
            "manager_id": None,
            "approval_limit": 1000000,
            "hire_date": fake.date_between(start_date="-10y", end_date="-5y"),
        })
        ceo_id = employee_id
        employee_id += 1

        # Directors
        director_ids = []
        departments = ["Finance", "Operations", "Sales", "Marketing", "Engineering",
                      "HR", "Legal", "IT", "Product", "Customer Success"]

        for dept in departments:
            director_id = employee_id
            director_ids.append(director_id)

            employees.append({
                "employee_id": director_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": f"{dept.lower()}.director@company.com",
                "department": dept,
                "title": "Director",
                "manager_id": ceo_id,
                "approval_limit": 10000,
                "hire_date": fake.date_between(start_date="-8y", end_date="-3y"),
            })
            employee_id += 1

        # Managers (5 per department)
        manager_ids = []
        for director_id in director_ids:
            dept = [e for e in employees if e["employee_id"] == director_id][0]["department"]

            for i in range(5):
                manager_id = employee_id
                manager_ids.append(manager_id)

                employees.append({
                    "employee_id": manager_id,
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "email": fake.email(),
                    "department": dept,
                    "title": "Manager",
                    "manager_id": director_id,
                    "approval_limit": 5000,
                    "hire_date": fake.date_between(start_date="-5y", end_date="-1y"),
                })
                employee_id += 1

        # Regular employees
        remaining = self.num_employees - len(employees)
        for i in range(remaining):
            manager_id = random.choice(manager_ids)
            dept = [e for e in employees if e["employee_id"] == manager_id][0]["department"]

            employees.append({
                "employee_id": employee_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.email(),
                "department": dept,
                "title": random.choice(["Senior Associate", "Associate", "Junior Associate", "Specialist"]),
                "manager_id": manager_id,
                "approval_limit": 1000,
                "hire_date": fake.date_between(start_date="-3y", end_date="-1m"),
            })
            employee_id += 1

        return pd.DataFrame(employees)

    def _generate_vendors(self) -> pd.DataFrame:
        """Generate vendor data"""

        vendors = []

        vendor_categories = [
            ("Office Supplies", ["Staples", "Office Depot", "Amazon Business"]),
            ("Travel", ["Delta", "United", "Hilton", "Marriott", "Uber", "Lyft"]),
            ("Meals", ["Subway", "Chipotle", "Starbucks", "Restaurant Group"]),
            ("Software", ["Adobe", "Microsoft", "Salesforce", "Slack"]),
            ("Equipment", ["Dell", "Apple", "HP", "Lenovo"]),
        ]

        vendor_id = 1

        for category, vendor_names in vendor_categories:
            for vendor_name in vendor_names:
                vendors.append({
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "category": category,
                    "tax_id": fake.ssn(),
                })
                vendor_id += 1

        # Add more generic vendors
        for i in range(200 - len(vendors)):
            vendors.append({
                "vendor_id": vendor_id,
                "vendor_name": fake.company(),
                "category": random.choice(["Services", "Consulting", "Supplies"]),
                "tax_id": fake.ssn(),
            })
            vendor_id += 1

        return pd.DataFrame(vendors)

    def _generate_expenses(self) -> pd.DataFrame:
        """Generate expense transactions with violations"""

        expenses = []
        expense_id = 1

        # Helper: random date in quarter
        def random_date():
            delta = self.end_date - self.start_date
            random_days = random.randint(0, delta.days)
            return self.start_date + timedelta(days=random_days)

        # Helper: realistic expense amount (Pareto distribution)
        def random_amount():
            amount = np.random.pareto(2) * 50
            return round(min(amount, 5000), 2)

        # Track violation expense IDs for later
        self.violation_expense_ids = {
            "self_approvals": [],
            "duplicates": [],
            "split_transactions": [],
            "missing_approvals": [],
            "timeline_violations": [],
        }

        # Generate normal expenses first
        normal_count = self.num_expenses - sum(self.violation_config.values())

        for i in range(normal_count):
            employee_id = random.randint(1, self.num_employees)
            vendor_id = random.randint(1, len(self.vendors))

            expenses.append({
                "expense_id": expense_id,
                "employee_id": employee_id,
                "vendor_id": vendor_id,
                "amount": random_amount(),
                "transaction_date": random_date(),
                "description": fake.sentence(),
                "category": self.vendors.loc[vendor_id - 1, "category"],
                "status": "paid",
                "approver_id": None,  # Will be set in approvals
            })
            expense_id += 1

        # Generate violation expenses

        # 1. Self-approvals
        for i in range(self.violation_config["self_approvals"]):
            employee_id = random.randint(1, self.num_employees)

            expenses.append({
                "expense_id": expense_id,
                "employee_id": employee_id,
                "vendor_id": random.randint(1, len(self.vendors)),
                "amount": random_amount(),
                "transaction_date": random_date(),
                "description": fake.sentence(),
                "category": "Travel",
                "status": "paid",
                "approver_id": employee_id,  # Self-approval!
            })

            self.violation_expense_ids["self_approvals"].append(expense_id)
            expense_id += 1

        # 2. Duplicates (pairs of identical expenses)
        for i in range(self.violation_config["duplicates"] // 2):
            employee_id = random.randint(1, self.num_employees)
            vendor_id = random.randint(1, len(self.vendors))
            amount = random_amount()
            date = random_date()

            # Original expense
            expenses.append({
                "expense_id": expense_id,
                "employee_id": employee_id,
                "vendor_id": vendor_id,
                "amount": amount,
                "transaction_date": date,
                "description": "Business meal",
                "category": "Meals",
                "status": "paid",
                "approver_id": None,
            })
            expense_id += 1

            # Duplicate (within 48 hours)
            expenses.append({
                "expense_id": expense_id,
                "employee_id": employee_id,
                "vendor_id": vendor_id,
                "amount": amount,
                "transaction_date": date + timedelta(hours=random.randint(1, 48)),
                "description": "Business meal",
                "category": "Meals",
                "status": "paid",
                "approver_id": None,
            })

            self.violation_expense_ids["duplicates"].append(expense_id - 1)
            self.violation_expense_ids["duplicates"].append(expense_id)
            expense_id += 1

        # 3. Split transactions (multiple expenses just below $1000 threshold)
        for i in range(self.violation_config["split_transactions"] // 2):
            employee_id = random.randint(1, self.num_employees)
            vendor_id = random.randint(1, len(self.vendors))
            date = random_date()

            # Two expenses at $975 each (total $1950, but individually below threshold)
            for j in range(2):
                expenses.append({
                    "expense_id": expense_id,
                    "employee_id": employee_id,
                    "vendor_id": vendor_id,
                    "amount": random.uniform(950, 999),
                    "transaction_date": date,
                    "description": "Equipment purchase",
                    "category": "Equipment",
                    "status": "paid",
                    "approver_id": None,
                })

                self.violation_expense_ids["split_transactions"].append(expense_id)
                expense_id += 1

        # 4. Missing approvals (will not create approval records for these)
        for i in range(self.violation_config["missing_approvals"]):
            expenses.append({
                "expense_id": expense_id,
                "employee_id": random.randint(1, self.num_employees),
                "vendor_id": random.randint(1, len(self.vendors)),
                "amount": random_amount(),
                "transaction_date": random_date(),
                "description": fake.sentence(),
                "category": "Supplies",
                "status": "paid",
                "approver_id": None,
            })

            self.violation_expense_ids["missing_approvals"].append(expense_id)
            expense_id += 1

        # 5. Timeline violations (approval after payment)
        for i in range(self.violation_config["timeline_violations"]):
            expenses.append({
                "expense_id": expense_id,
                "employee_id": random.randint(1, self.num_employees),
                "vendor_id": random.randint(1, len(self.vendors)),
                "amount": random_amount(),
                "transaction_date": random_date(),
                "description": fake.sentence(),
                "category": "Travel",
                "status": "paid",
                "approver_id": None,
            })

            self.violation_expense_ids["timeline_violations"].append(expense_id)
            expense_id += 1

        return pd.DataFrame(expenses)

    def _generate_approvals(self) -> pd.DataFrame:
        """Generate approval records"""

        approvals = []
        approval_id = 1

        # Approvals for all expenses except missing_approvals
        missing_approval_ids = set(self.violation_expense_ids["missing_approvals"])

        for _, expense in self.expenses.iterrows():
            if expense["expense_id"] in missing_approval_ids:
                continue  # Skip - this is a missing approval violation

            # Find appropriate approver
            employee_id = expense["employee_id"]
            employee = self.employees[self.employees["employee_id"] == employee_id].iloc[0]

            # Use manager as approver (unless self-approval violation)
            if expense["expense_id"] in self.violation_expense_ids["self_approvals"]:
                approver_id = employee_id  # Self-approval
            else:
                approver_id = employee["manager_id"]
                if pd.isna(approver_id):  # CEO has no manager
                    continue

            # Approval date
            # Normal: 1-5 days after expense
            # Timeline violation: AFTER payment date (will set later)
            if expense["expense_id"] in self.violation_expense_ids["timeline_violations"]:
                approval_date = expense["transaction_date"] + timedelta(days=random.randint(10, 20))
            else:
                approval_date = expense["transaction_date"] + timedelta(days=random.randint(1, 5))

            approvals.append({
                "approval_id": approval_id,
                "expense_id": expense["expense_id"],
                "approver_id": int(approver_id),
                "approval_date": approval_date,
                "status": "approved",
            })

            # Update approver_id in expenses DataFrame
            self.expenses.loc[self.expenses["expense_id"] == expense["expense_id"], "approver_id"] = int(approver_id)

            approval_id += 1

        return pd.DataFrame(approvals)

    def _generate_payments(self) -> pd.DataFrame:
        """Generate payment records"""

        payments = []
        payment_id = 1

        for _, expense in self.expenses.iterrows():
            if expense["status"] != "paid":
                continue

            # Payment date
            # Normal: 7-14 days after expense
            # Timeline violation: BEFORE approval
            if expense["expense_id"] in self.violation_expense_ids["timeline_violations"]:
                payment_date = expense["transaction_date"] + timedelta(days=random.randint(3, 7))
            else:
                payment_date = expense["transaction_date"] + timedelta(days=random.randint(7, 14))

            payments.append({
                "payment_id": payment_id,
                "expense_id": expense["expense_id"],
                "payment_date": payment_date,
                "amount": expense["amount"],
                "payment_method": random.choice(["ACH", "Wire", "Check", "Corporate Card"]),
            })

            payment_id += 1

        return pd.DataFrame(payments)

    def get_violation_summary(self) -> pd.DataFrame:
        """Get summary of injected violations"""

        summary = []

        for violation_type, expense_ids in self.violation_expense_ids.items():
            summary.append({
                "violation_type": violation_type,
                "count": len(expense_ids),
                "expense_ids": expense_ids[:5],  # Sample
            })

        return pd.DataFrame(summary)
