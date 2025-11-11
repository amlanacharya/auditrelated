"""
Template Library: Pre-built audit workflow templates

Provides industry-standard templates that users can adopt
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import pandas as pd
import structlog

logger = structlog.get_logger()


@dataclass
class WorkflowTemplate:
    """Represents a pre-built workflow template"""
    id: str
    name: str
    description: str
    industry: str
    steps: List[Dict]
    rules: List[Dict]
    compliance_standards: List[str]
    use_count: int = 0  # How many orgs use this
    match_confidence: float = 0.0  # How well it matches current data


class TemplateLibrary:
    """Library of pre-built audit workflow templates"""

    def __init__(self):
        """Initialize template library"""
        self.templates = self._load_templates()

    def _load_templates(self) -> List[WorkflowTemplate]:
        """Load pre-built templates"""

        templates = []

        # Template 1: Corporate Expense Reimbursement (SOX Compliant)
        templates.append(WorkflowTemplate(
            id='TPL_EXPENSE_SOX',
            name='Corporate Expense Reimbursement (SOX Compliant)',
            description='Complete expense reimbursement workflow with SOX 404 controls',
            industry='corporate',
            steps=[
                {
                    'name': 'initiation',
                    'sequence': 1,
                    'table': 'expenses',
                    'description': 'Employee submits expense with receipt',
                    'duration_minutes': 0
                },
                {
                    'name': 'policy_validation',
                    'sequence': 2,
                    'table': 'validation_checks',
                    'description': 'Automated policy compliance check',
                    'duration_minutes': 5
                },
                {
                    'name': 'manager_approval',
                    'sequence': 3,
                    'table': 'approvals',
                    'description': 'Manager reviews and approves',
                    'duration_minutes': 2880,  # 2 days
                    'conditions': [
                        {'if': 'amount > 10000', 'then': 'require_dual_approval'}
                    ]
                },
                {
                    'name': 'finance_review',
                    'sequence': 4,
                    'table': 'finance_approvals',
                    'description': 'Finance team final review',
                    'duration_minutes': 1440  # 1 day
                },
                {
                    'name': 'payment',
                    'sequence': 5,
                    'table': 'payments',
                    'description': 'Payment processed',
                    'duration_minutes': 4320  # 3 days
                },
                {
                    'name': 'reconciliation',
                    'sequence': 6,
                    'table': 'reconciliations',
                    'description': 'Post-payment reconciliation',
                    'duration_minutes': 1440  # 1 day
                }
            ],
            rules=[
                {
                    'rule_id': 'SOX_001',
                    'name': 'Self-Approval Detection',
                    'severity': 'critical',
                    'applies_to_step': 'manager_approval'
                },
                {
                    'rule_id': 'SOX_002',
                    'name': 'Duplicate Expense Detection',
                    'severity': 'high',
                    'applies_to_step': 'policy_validation'
                },
                {
                    'rule_id': 'SOX_003',
                    'name': 'Missing Approval Detection',
                    'severity': 'critical',
                    'applies_to_step': 'payment'
                },
                {
                    'rule_id': 'SOX_004',
                    'name': 'Timeline Violation Detection',
                    'severity': 'high',
                    'applies_to_step': 'reconciliation'
                },
                {
                    'rule_id': 'SOX_005',
                    'name': 'Split Transaction Detection',
                    'severity': 'medium',
                    'applies_to_step': 'policy_validation'
                },
                {
                    'rule_id': 'SOX_006',
                    'name': 'Receipt Verification',
                    'severity': 'high',
                    'applies_to_step': 'finance_review'
                },
                {
                    'rule_id': 'SOX_007',
                    'name': 'Amount Match Check',
                    'severity': 'critical',
                    'applies_to_step': 'reconciliation'
                }
            ],
            compliance_standards=['SOX 404', 'COSO', 'PCAOB'],
            use_count=2347
        ))

        # Template 2: Small Business Simplified
        templates.append(WorkflowTemplate(
            id='TPL_SIMPLE',
            name='Small Business Expense Review',
            description='Simplified workflow for small businesses with basic controls',
            industry='small_business',
            steps=[
                {
                    'name': 'initiation',
                    'sequence': 1,
                    'table': 'expenses',
                    'description': 'Employee submits expense',
                    'duration_minutes': 0
                },
                {
                    'name': 'approval',
                    'sequence': 2,
                    'table': 'approvals',
                    'description': 'Manager or owner approves',
                    'duration_minutes': 1440  # 1 day
                },
                {
                    'name': 'payment',
                    'sequence': 3,
                    'table': 'payments',
                    'description': 'Payment processed',
                    'duration_minutes': 2880  # 2 days
                }
            ],
            rules=[
                {
                    'rule_id': 'SIMPLE_001',
                    'name': 'Self-Approval Detection',
                    'severity': 'critical',
                    'applies_to_step': 'approval'
                },
                {
                    'rule_id': 'SIMPLE_002',
                    'name': 'Duplicate Expense Detection',
                    'severity': 'high',
                    'applies_to_step': 'payment'
                },
                {
                    'rule_id': 'SIMPLE_003',
                    'name': 'Missing Approval Detection',
                    'severity': 'critical',
                    'applies_to_step': 'payment'
                }
            ],
            compliance_standards=['Basic Internal Controls'],
            use_count=892
        ))

        # Template 3: Travel & Entertainment Specific
        templates.append(WorkflowTemplate(
            id='TPL_TRAVEL',
            name='Travel & Entertainment Audit',
            description='Specialized workflow for T&E compliance with per diem and policy checks',
            industry='corporate',
            steps=[
                {
                    'name': 'initiation',
                    'sequence': 1,
                    'table': 'expenses',
                    'description': 'Employee submits T&E expense',
                    'duration_minutes': 0
                },
                {
                    'name': 'policy_check',
                    'sequence': 2,
                    'table': 'policy_checks',
                    'description': 'Automated T&E policy validation',
                    'duration_minutes': 5
                },
                {
                    'name': 'per_diem_validation',
                    'sequence': 3,
                    'table': 'per_diem_checks',
                    'description': 'Validate against GSA per diem rates',
                    'duration_minutes': 5
                },
                {
                    'name': 'manager_approval',
                    'sequence': 4,
                    'table': 'approvals',
                    'description': 'Manager approval',
                    'duration_minutes': 2880
                },
                {
                    'name': 'payment',
                    'sequence': 5,
                    'table': 'payments',
                    'description': 'Payment processed',
                    'duration_minutes': 4320
                }
            ],
            rules=[
                {
                    'rule_id': 'TE_001',
                    'name': 'Per Diem Limit Check',
                    'severity': 'high',
                    'applies_to_step': 'per_diem_validation'
                },
                {
                    'rule_id': 'TE_002',
                    'name': 'Client Entertainment Policy',
                    'severity': 'medium',
                    'applies_to_step': 'policy_check'
                },
                {
                    'rule_id': 'TE_003',
                    'name': 'Travel Class Policy',
                    'severity': 'medium',
                    'applies_to_step': 'policy_check'
                },
                {
                    'rule_id': 'TE_004',
                    'name': 'Weekend Travel Check',
                    'severity': 'low',
                    'applies_to_step': 'policy_check'
                }
            ],
            compliance_standards=['GSA Per Diem', 'IRS Business Expense'],
            use_count=456
        ))

        return templates

    def match_template(self, data_context: Dict) -> Optional[WorkflowTemplate]:
        """
        Find best matching template based on data characteristics

        Args:
            data_context: Context about uploaded data (tables, columns, patterns)

        Returns:
            Best matching template with confidence score
        """
        logger.info("template_matching_started", context=data_context)

        best_match = None
        best_score = 0.0

        for template in self.templates:
            score = self._calculate_match_score(template, data_context)

            if score > best_score:
                best_score = score
                best_match = template

        if best_match:
            best_match.match_confidence = best_score
            logger.info("template_matched",
                       template=best_match.name,
                       confidence=best_score)

        return best_match

    def _calculate_match_score(self, template: WorkflowTemplate, data_context: Dict) -> float:
        """Calculate how well a template matches the data"""

        score = 0.0
        checks = 0

        # Check 1: Required tables present
        required_tables = set(step['table'] for step in template.steps)
        available_tables = set(data_context.get('tables', []))

        if required_tables:
            checks += 1
            table_match = len(required_tables & available_tables) / len(required_tables)
            score += table_match * 0.4  # 40% weight

        # Check 2: Column patterns match
        if 'columns' in data_context:
            checks += 1
            expense_indicators = ['amount', 'vendor', 'category', 'receipt']
            present_indicators = sum(
                1 for ind in expense_indicators
                if any(ind in str(col).lower() for col in data_context['columns'])
            )
            score += (present_indicators / len(expense_indicators)) * 0.3  # 30% weight

        # Check 3: Data volume (complexity)
        if 'row_count' in data_context:
            checks += 1
            row_count = data_context['row_count']

            # Small business template for < 5000 records
            if template.id == 'TPL_SIMPLE':
                if row_count < 5000:
                    score += 0.3
                else:
                    score += 0.1

            # Corporate template for >= 5000 records
            elif template.id == 'TPL_EXPENSE_SOX':
                if row_count >= 5000:
                    score += 0.3
                else:
                    score += 0.1

        # Normalize score
        return score / checks if checks > 0 else 0.0

    def get_all_templates(self) -> List[WorkflowTemplate]:
        """Get all available templates"""
        return sorted(self.templates, key=lambda t: t.use_count, reverse=True)

    def get_template_by_id(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get specific template by ID"""
        for template in self.templates:
            if template.id == template_id:
                return template
        return None
