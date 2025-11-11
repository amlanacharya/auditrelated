"""
Data Analyzer: Statistical analysis and anomaly detection

Analyzes uploaded data to find:
- Statistical anomalies (Benford's Law, outliers)
- Temporal patterns (weekend activity, end-of-period spikes)
- Behavioral patterns (unusual employee behavior)
- Schema gaps (missing critical columns)
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import structlog

logger = structlog.get_logger()


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    type: str  # 'statistical', 'temporal', 'behavioral', 'schema'
    severity: str  # 'critical', 'high', 'medium', 'low'
    title: str
    description: str
    evidence: Dict
    suggested_action: Dict
    confidence: float  # 0.0 to 1.0


class DataAnalyzer:
    """Analyzes audit data for anomalies and patterns"""

    def __init__(self):
        """Initialize analyzer"""
        self.anomalies = []

    def analyze(self, df: pd.DataFrame, table_name: str) -> List[Anomaly]:
        """
        Comprehensive data analysis

        Args:
            df: DataFrame to analyze
            table_name: Name of the table

        Returns:
            List of detected anomalies
        """
        logger.info("data_analysis_started", table=table_name, rows=len(df))

        self.anomalies = []

        # Run all analysis modules
        self.analyze_schema(df, table_name)

        if 'amount' in df.columns:
            self.analyze_benfords_law(df)
            self.analyze_round_numbers(df)
            self.analyze_threshold_gaming(df)

        if 'transaction_date' in df.columns or any('date' in col.lower() for col in df.columns):
            self.analyze_temporal_patterns(df)

        if 'employee_id' in df.columns:
            self.analyze_employee_behavior(df)

        if table_name == 'expenses' and 'approver_id' in df.columns:
            self.analyze_self_approvals(df)

        logger.info("data_analysis_completed",
                   table=table_name,
                   anomalies=len(self.anomalies))

        return sorted(self.anomalies, key=lambda x: (
            {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x.severity],
            -x.confidence
        ))

    def analyze_schema(self, df: pd.DataFrame, table_name: str):
        """Analyze schema for missing critical columns"""

        critical_columns = {
            'expenses': ['expense_id', 'employee_id', 'amount', 'transaction_date'],
            'approvals': ['approval_id', 'expense_id', 'approver_id', 'approval_date'],
            'employees': ['employee_id', 'manager_id', 'department']
        }

        if table_name in critical_columns:
            expected = set(critical_columns[table_name])
            actual = set(df.columns)
            missing = expected - actual

            if missing:
                self.anomalies.append(Anomaly(
                    type='schema',
                    severity='high',
                    title=f"Missing Critical Columns in {table_name}",
                    description=f"The {table_name} table is missing {len(missing)} critical columns: {', '.join(missing)}",
                    evidence={
                        'missing_columns': list(missing),
                        'present_columns': list(actual),
                        'table': table_name
                    },
                    suggested_action={
                        'type': 'data_quality_check',
                        'action': 'Review data source and ensure all required columns are present'
                    },
                    confidence=1.0
                ))

    def analyze_benfords_law(self, df: pd.DataFrame):
        """
        Check if amounts follow Benford's Law (natural distribution)

        Fabricated numbers often don't follow Benford's Law
        """
        if 'amount' not in df.columns or df['amount'].isna().all():
            return

        # Get first digits
        first_digits = df['amount'].apply(lambda x: int(str(abs(x)).replace('.', '')[0]) if x > 0 else 0)
        first_digits = first_digits[first_digits > 0]

        if len(first_digits) < 30:  # Need sufficient sample
            return

        # Expected Benford distribution
        benford_expected = {
            1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
            6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
        }

        # Actual distribution
        actual_dist = first_digits.value_counts(normalize=True).to_dict()

        # Chi-square test
        observed = [actual_dist.get(i, 0) * len(first_digits) for i in range(1, 10)]
        expected = [benford_expected[i] * len(first_digits) for i in range(1, 10)]

        chi2, p_value = stats.chisquare(observed, expected)

        # If p-value < 0.05, distribution doesn't match Benford's Law
        if p_value < 0.05:
            import json
            self.anomalies.append(Anomaly(
                type='statistical',
                severity='high',
                title="Amount Distribution Anomaly (Benford's Law)",
                description="The first digit distribution of amounts doesn't follow natural patterns. "
                           "This could indicate fabricated or manipulated numbers.",
                evidence={
                    'chi_square': round(chi2, 2),
                    'p_value': round(p_value, 4),
                    'sample_size': len(first_digits),
                    'expected_distribution': json.dumps(benford_expected),  # Convert dict to JSON string
                    'actual_distribution': json.dumps({k: round(v, 3) for k, v in actual_dist.items()})
                },
                suggested_action={
                    'type': 'create_rule',
                    'rule_name': 'Benford\'s Law Check',
                    'description': 'Periodically check if amount distributions follow natural patterns'
                },
                confidence=0.85
            ))

    def analyze_round_numbers(self, df: pd.DataFrame):
        """Detect excessive round numbers (possible fabrication)"""
        if 'amount' not in df.columns:
            return

        # Count amounts ending in .00
        round_amounts = df[df['amount'] % 1 == 0]
        round_pct = len(round_amounts) / len(df) * 100

        # Natural expenses have ~20-30% round numbers
        # Higher percentages suggest fabrication
        if round_pct > 50:
            self.anomalies.append(Anomaly(
                type='statistical',
                severity='medium',
                title="High Percentage of Round-Number Amounts",
                description=f"{round_pct:.1f}% of amounts are round numbers (e.g., $50.00, $100.00). "
                           f"Natural expenses typically have 20-30% round numbers.",
                evidence={
                    'round_number_count': len(round_amounts),
                    'total_count': len(df),
                    'percentage': round(round_pct, 1),
                    'sample_amounts': round_amounts['amount'].head(10).tolist()
                },
                suggested_action={
                    'type': 'manual_review',
                    'action': 'Review round-number expenses for authenticity'
                },
                confidence=0.70
            ))

    def analyze_threshold_gaming(self, df: pd.DataFrame):
        """Detect expenses clustered just below approval thresholds"""
        if 'amount' not in df.columns:
            return

        # Common thresholds
        thresholds = [100, 500, 1000, 5000, 10000]

        for threshold in thresholds:
            # Count expenses in $threshold - 50 to $threshold - 1 range
            window = 50
            just_below = df[
                (df['amount'] >= threshold - window) &
                (df['amount'] < threshold)
            ]

            if len(just_below) > 10:  # Meaningful sample
                # Calculate if this is unusually high
                total_in_band = len(df[
                    (df['amount'] >= threshold - window) &
                    (df['amount'] < threshold + window)
                ])

                if len(just_below) > total_in_band * 0.6:  # >60% just below
                    self.anomalies.append(Anomaly(
                        type='statistical',
                        severity='high',
                        title=f"Threshold Gaming Detected (${threshold})",
                        description=f"{len(just_below)} expenses found just below the ${threshold} threshold. "
                                   f"This pattern suggests intentional splitting to avoid approval requirements.",
                        evidence={
                            'threshold': threshold,
                            'count_just_below': len(just_below),
                            'percentage_just_below': round(len(just_below) / total_in_band * 100, 1),
                            'sample_amounts': just_below['amount'].head(10).tolist(),
                            'avg_amount': round(just_below['amount'].mean(), 2)
                        },
                        suggested_action={
                            'type': 'create_rule',
                            'rule_name': f'Split Transaction Detection (${threshold})',
                            'sql_template': f"""
                                SELECT expense_id, employee_id, amount,
                                       'Expense just below ${threshold} threshold' as violation_reason
                                FROM expenses
                                WHERE amount BETWEEN {threshold - window} AND {threshold - 1}
                            """
                        },
                        confidence=0.90
                    ))

    def analyze_temporal_patterns(self, df: pd.DataFrame):
        """Analyze timing patterns for anomalies"""

        # Find date column
        date_col = None
        for col in df.columns:
            if 'date' in col.lower():
                date_col = col
                break

        if not date_col:
            return

        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df_valid = df[df[date_col].notna()].copy()

        if len(df_valid) < 10:
            return

        # Weekend activity
        df_valid['weekday'] = df_valid[date_col].dt.dayofweek
        weekend_count = len(df_valid[df_valid['weekday'].isin([5, 6])])
        weekend_pct = weekend_count / len(df_valid) * 100

        if weekend_pct > 10:  # >10% on weekends is unusual
            self.anomalies.append(Anomaly(
                type='temporal',
                severity='medium',
                title="High Weekend Activity",
                description=f"{weekend_pct:.1f}% of transactions occur on weekends. "
                           f"This could indicate after-hours manipulation or unusual business practices.",
                evidence={
                    'weekend_count': weekend_count,
                    'total_count': len(df_valid),
                    'percentage': round(weekend_pct, 1),
                    'saturday_count': len(df_valid[df_valid['weekday'] == 5]),
                    'sunday_count': len(df_valid[df_valid['weekday'] == 6])
                },
                suggested_action={
                    'type': 'create_rule',
                    'rule_name': 'Weekend Activity Check',
                    'description': 'Flag transactions submitted or approved on weekends'
                },
                confidence=0.75
            ))

        # End-of-month/quarter spikes
        df_valid['day'] = df_valid[date_col].dt.day
        last_days = df_valid[df_valid['day'] >= 28]
        last_days_pct = len(last_days) / len(df_valid) * 100

        if last_days_pct > 20:  # >20% in last few days
            self.anomalies.append(Anomaly(
                type='temporal',
                severity='medium',
                title="End-of-Period Activity Spike",
                description=f"{last_days_pct:.1f}% of transactions occur in the last 3 days of the month. "
                           f"This could indicate quota stuffing or period manipulation.",
                evidence={
                    'last_days_count': len(last_days),
                    'total_count': len(df_valid),
                    'percentage': round(last_days_pct, 1)
                },
                suggested_action={
                    'type': 'manual_review',
                    'action': 'Review end-of-month transactions for legitimacy'
                },
                confidence=0.70
            ))

    def analyze_employee_behavior(self, df: pd.DataFrame):
        """Detect unusual employee behavior patterns"""
        if 'employee_id' not in df.columns or 'amount' not in df.columns:
            return

        # Aggregate by employee
        emp_stats = df.groupby('employee_id').agg({
            'amount': ['count', 'mean', 'std', 'sum']
        })

        emp_stats.columns = ['count', 'mean', 'std', 'sum']
        emp_stats = emp_stats[emp_stats['count'] >= 3]  # Need reasonable sample

        if len(emp_stats) < 5:  # Need multiple employees
            return

        # Z-score outliers
        scaler = StandardScaler()
        features = emp_stats[['count', 'mean', 'sum']].fillna(0)
        scaled = scaler.fit_transform(features)

        # Find outliers (|z-score| > 3)
        z_scores = np.abs(scaled).max(axis=1)
        outliers = emp_stats[z_scores > 3]

        if len(outliers) > 0:
            for emp_id, row in outliers.head(5).iterrows():
                self.anomalies.append(Anomaly(
                    type='behavioral',
                    severity='medium',
                    title=f"Unusual Employee Behavior: Employee #{emp_id}",
                    description=f"Employee #{emp_id} shows unusual spending patterns compared to peers.",
                    evidence={
                        'employee_id': int(emp_id),
                        'transaction_count': int(row['count']),
                        'avg_amount': round(row['mean'], 2),
                        'total_amount': round(row['sum'], 2),
                        'std_dev': round(row['std'], 2) if not pd.isna(row['std']) else 0,
                        'comparison': 'significantly higher than peer average'
                    },
                    suggested_action={
                        'type': 'manual_review',
                        'action': f'Review all expenses for employee #{emp_id}'
                    },
                    confidence=0.75
                ))

    def analyze_self_approvals(self, df: pd.DataFrame):
        """Detect self-approval violations"""
        if 'employee_id' not in df.columns or 'approver_id' not in df.columns:
            return

        self_approvals = df[df['employee_id'] == df['approver_id']]

        if len(self_approvals) > 0:
            total_amount = self_approvals['amount'].sum() if 'amount' in df.columns else 0

            self.anomalies.append(Anomaly(
                type='compliance',
                severity='critical',
                title="Self-Approval Violations Detected",
                description=f"{len(self_approvals)} instances found where employees approved their own expenses. "
                           f"This violates segregation of duties principles.",
                evidence={
                    'violation_count': len(self_approvals),
                    'total_amount': round(total_amount, 2) if total_amount > 0 else 0,
                    'affected_employees': self_approvals['employee_id'].unique().tolist()[:10],
                    'sample_expenses': self_approvals['expense_id'].head(5).tolist() if 'expense_id' in df.columns else []
                },
                suggested_action={
                    'type': 'create_rule',
                    'rule_name': 'Self-Approval Detection',
                    'description': 'Automatically flag and block self-approvals',
                    'priority': 'critical'
                },
                confidence=1.0
            ))
