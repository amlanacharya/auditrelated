"""
Suggestion Engine: Generate workflow and rule suggestions

Provides:
- Workflow improvement recommendations
- Missing step detection
- Rule creation suggestions
- Template matching
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import structlog

from audit_agent.ai_assistant.analyzer import Anomaly

logger = structlog.get_logger()


@dataclass
class Suggestion:
    """Represents an AI suggestion"""
    id: str
    type: str  # 'missing_step', 'new_rule', 'data_issue', 'pattern', 'template'
    priority: str  # 'critical', 'high', 'medium', 'low'
    category: str
    title: str
    description: str
    reasoning: str
    evidence: Dict
    suggested_action: Dict
    confidence: float
    user_feedback: Optional[str] = None  # 'accepted', 'dismissed', 'deferred'
    created_at: str = None
    expires_at: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class SuggestionEngine:
    """Generate intelligent suggestions for audit workflows"""

    def __init__(self):
        """Initialize suggestion engine"""
        self.suggestions = []
        self.feedback_history = []

    def generate_from_anomalies(self, anomalies: List[Anomaly]) -> List[Suggestion]:
        """
        Convert detected anomalies into actionable suggestions

        Args:
            anomalies: List of detected anomalies

        Returns:
            List of suggestions
        """
        suggestions = []

        for idx, anomaly in enumerate(anomalies):
            suggestion = Suggestion(
                id=f"sugg_{datetime.now().strftime('%Y%m%d')}_{idx:03d}",
                type='data_issue' if anomaly.type in ['schema', 'compliance'] else 'pattern',
                priority=anomaly.severity,
                category=anomaly.type,
                title=anomaly.title,
                description=anomaly.description,
                reasoning=self._generate_reasoning(anomaly),
                evidence=anomaly.evidence,
                suggested_action=anomaly.suggested_action,
                confidence=anomaly.confidence
            )
            suggestions.append(suggestion)

        return suggestions

    def _generate_reasoning(self, anomaly: Anomaly) -> str:
        """Generate natural language reasoning for an anomaly"""

        reasoning_templates = {
            'statistical': "This pattern is unusual from a statistical perspective. "
                          "Natural data typically follows certain distributions, and deviations "
                          "can indicate manipulation or fabrication.",

            'temporal': "The timing pattern is abnormal. Legitimate business activities typically "
                       "follow regular schedules, and unusual timing can indicate fraud or policy violations.",

            'behavioral': "This employee's behavior significantly deviates from peer norms. "
                         "While individual variation is natural, extreme outliers warrant investigation.",

            'compliance': "This violates fundamental audit controls and segregation of duties principles. "
                         "It represents a critical compliance risk.",

            'schema': "Missing critical data columns can prevent effective auditing and indicate "
                     "data quality issues that need to be addressed."
        }

        base_reasoning = reasoning_templates.get(anomaly.type, "This pattern warrants investigation.")

        # Add specific context
        if anomaly.type == 'statistical' and 'benford' in anomaly.title.lower():
            base_reasoning += " Benford's Law states that in natural datasets, about 30% of numbers start with 1, " \
                            "17.6% with 2, and so on. When this distribution is violated, it often indicates fabricated data."

        elif 'threshold' in anomaly.title.lower():
            base_reasoning += " This is a known fraud technique called 'structuring' or 'smurfing', where " \
                            "transactions are deliberately kept below approval limits to avoid scrutiny."

        elif 'self-approval' in anomaly.title.lower():
            base_reasoning += " Self-approval is prohibited under SOX Section 404 and most corporate policies " \
                            "because it creates an opportunity for fraudulent expense submissions."

        return base_reasoning

    def suggest_missing_steps(
        self,
        current_steps: List[Dict],
        data_context: Dict
    ) -> List[Suggestion]:
        """
        Suggest missing workflow steps based on best practices

        Args:
            current_steps: List of current workflow steps
            data_context: Context about the data (tables, columns, etc.)

        Returns:
            List of workflow improvement suggestions
        """
        suggestions = []
        step_names = [step.get('name', '').lower() for step in current_steps]

        # Check for missing validation step
        if 'validation' not in ' '.join(step_names) and 'check' not in ' '.join(step_names):
            suggestions.append(Suggestion(
                id=f"workflow_val_{datetime.now().strftime('%Y%m%d')}",
                type='missing_step',
                priority='high',
                category='workflow_gap',
                title='Add Pre-Approval Validation Step',
                description='Your workflow lacks an upfront validation step to catch policy violations before approval.',
                reasoning='Industry best practice includes automated policy checks before human approval. '
                         'This prevents approvers from wasting time on invalid requests and ensures consistency.',
                evidence={
                    'current_workflow': [step.get('name') for step in current_steps],
                    'missing_step': 'validation',
                    'typical_position': 'after_initiation'
                },
                suggested_action={
                    'type': 'add_workflow_step',
                    'step_name': 'Policy Validation',
                    'insert_after': current_steps[0].get('name') if current_steps else None,
                    'rules_to_apply': ['amount_limit_check', 'category_policy_check', 'duplicate_check']
                },
                confidence=0.85
            ))

        # Check for missing dual approval for high-value
        has_conditional = any('condition' in str(step) for step in current_steps)
        if not has_conditional and data_context.get('has_amount_column'):
            suggestions.append(Suggestion(
                id=f"workflow_dual_{datetime.now().strftime('%Y%m%d')}",
                type='missing_step',
                priority='high',
                category='workflow_gap',
                title='Add Dual Approval for High-Value Items',
                description='High-value transactions should require approval from two independent reviewers.',
                reasoning='Dual approval for amounts over a threshold (typically $5,000-$10,000) is a fundamental '
                         'fraud prevention control. It reduces the risk of collusion and provides additional oversight '
                         'for financially material items.',
                evidence={
                    'current_workflow': [step.get('name') for step in current_steps],
                    'missing_control': 'dual_approval',
                    'recommended_threshold': 10000
                },
                suggested_action={
                    'type': 'add_conditional_branch',
                    'condition': 'amount > 10000',
                    'branch_name': 'Dual Approval Required',
                    'additional_approvers': 1
                },
                confidence=0.90
            ))

        # Check for missing reconciliation
        has_reconciliation = any('reconcil' in step.get('name', '').lower() for step in current_steps)
        if not has_reconciliation and len(current_steps) >= 3:
            suggestions.append(Suggestion(
                id=f"workflow_recon_{datetime.now().strftime('%Y%m%d')}",
                type='missing_step',
                priority='medium',
                category='workflow_gap',
                title='Add Post-Payment Reconciliation',
                description='Your workflow lacks a final reconciliation step to ensure payment matches approval.',
                reasoning='Reconciliation closes the loop and ensures that what was approved matches what was paid. '
                         'This catches errors, overpayments, and duplicate payments.',
                evidence={
                    'current_workflow': [step.get('name') for step in current_steps],
                    'missing_step': 'reconciliation',
                    'typical_position': 'after_payment'
                },
                suggested_action={
                    'type': 'add_workflow_step',
                    'step_name': 'Payment Reconciliation',
                    'insert_after': 'payment',
                    'rules_to_apply': ['amount_match_check', 'timing_check']
                },
                confidence=0.80
            ))

        return suggestions

    def suggest_rules_from_context(
        self,
        data_summary: Dict,
        existing_rules: List[str]
    ) -> List[Suggestion]:
        """
        Suggest additional rules based on data context

        Args:
            data_summary: Summary of data characteristics
            existing_rules: List of existing rule names

        Returns:
            List of rule suggestions
        """
        suggestions = []

        # Weekend activity rule
        if data_summary.get('has_date_column') and 'weekend' not in ' '.join(existing_rules).lower():
            suggestions.append(Suggestion(
                id=f"rule_weekend_{datetime.now().strftime('%Y%m%d')}",
                type='new_rule',
                priority='medium',
                category='fraud_detection',
                title='Weekend Activity Detection Rule',
                description='Flag transactions that occur on weekends for additional review.',
                reasoning='While some businesses operate on weekends, unusual weekend activity can indicate '
                         'after-hours manipulation or unauthorized access.',
                evidence={
                    'data_has_dates': True,
                    'rule_gap': 'weekend_check'
                },
                suggested_action={
                    'type': 'create_rule',
                    'rule_id': 'WEEKEND_001',
                    'rule_name': 'Weekend Activity Check',
                    'severity': 'medium',
                    'sql_template': """
                        SELECT expense_id, employee_id, transaction_date,
                               'Transaction on weekend' as violation_reason
                        FROM expenses
                        WHERE CAST(strftime('%w', transaction_date) AS INTEGER) IN (0, 6)
                    """
                },
                confidence=0.75
            ))

        # Rapid transaction rule
        if data_summary.get('has_date_column') and 'rapid' not in ' '.join(existing_rules).lower():
            suggestions.append(Suggestion(
                id=f"rule_rapid_{datetime.now().strftime('%Y%m%d')}",
                type='new_rule',
                priority='medium',
                category='fraud_detection',
                title='Rapid Transaction Detection Rule',
                description='Flag multiple transactions by the same employee within a short timeframe.',
                reasoning='Rapid-fire transactions can indicate automated fraud, card testing, or transaction splitting.',
                evidence={
                    'data_has_dates': True,
                    'rule_gap': 'rapid_transactions'
                },
                suggested_action={
                    'type': 'create_rule',
                    'rule_id': 'RAPID_001',
                    'rule_name': 'Rapid Transaction Check',
                    'severity': 'high',
                    'sql_template': """
                        SELECT e1.expense_id, e1.employee_id, e1.transaction_date,
                               COUNT(*) as transaction_count,
                               'Multiple transactions within 1 hour' as violation_reason
                        FROM expenses e1
                        JOIN expenses e2
                          ON e1.employee_id = e2.employee_id
                          AND e1.expense_id < e2.expense_id
                          AND (JULIANDAY(e2.transaction_date) - JULIANDAY(e1.transaction_date)) * 24 < 1
                        GROUP BY e1.expense_id, e1.employee_id, e1.transaction_date
                        HAVING COUNT(*) >= 3
                    """
                },
                confidence=0.80
            ))

        return suggestions

    def record_feedback(
        self,
        suggestion_id: str,
        action: str,
        reason: Optional[str] = None
    ):
        """
        Record user feedback on a suggestion

        Args:
            suggestion_id: ID of the suggestion
            action: User action ('accepted', 'dismissed', 'deferred')
            reason: Optional reason for the action
        """
        feedback = {
            'suggestion_id': suggestion_id,
            'action': action,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }

        self.feedback_history.append(feedback)

        # Update suggestion status
        for suggestion in self.suggestions:
            if suggestion.id == suggestion_id:
                suggestion.user_feedback = action
                break

        logger.info("suggestion_feedback_recorded",
                   suggestion_id=suggestion_id,
                   action=action)

    def get_suggestions_by_priority(self) -> Dict[str, List[Suggestion]]:
        """Group suggestions by priority"""
        grouped = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for suggestion in self.suggestions:
            if suggestion.user_feedback is None:  # Only show pending suggestions
                grouped[suggestion.priority].append(suggestion)

        return grouped

    def export_suggestions(self, filepath: str):
        """Export suggestions to JSON file"""
        data = {
            'suggestions': [s.to_dict() for s in self.suggestions],
            'feedback_history': self.feedback_history,
            'exported_at': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info("suggestions_exported", path=filepath, count=len(self.suggestions))
