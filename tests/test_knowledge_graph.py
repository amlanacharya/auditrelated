"""
Tests for Knowledge Graph components
"""

import pytest
import tempfile
from datetime import date
from pathlib import Path

from audit_agent.knowledge_graph import (
    KnowledgeGraphManager,
    ProcessGraph,
    EntityGraph,
    TableGraph,
    ViolationGraph,
)


class TestKnowledgeGraphManager:
    """Tests for KnowledgeGraphManager"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        yield db_path

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_initialization(self, temp_db):
        """Test KG initialization"""
        kg = KnowledgeGraphManager(temp_db)

        stats = kg.get_statistics()

        # All tables should exist with 0 rows
        assert "process_types" in stats
        assert "violation_rules" in stats

        kg.close()

    def test_audit_logging(self, temp_db):
        """Test audit trail logging"""
        kg = KnowledgeGraphManager(temp_db)

        kg.log_action(
            action="test_action",
            entity_type="test_entity",
            entity_id=123,
            user_id="test_user",
            details={"key": "value"}
        )

        # Verify log was created
        cursor = kg.conn.execute("SELECT COUNT(*) FROM audit_log")
        count = cursor.fetchone()[0]
        assert count == 1

        kg.close()


class TestViolationGraph:
    """Tests for ViolationGraph"""

    @pytest.fixture
    def violation_graph(self, temp_db):
        """Create ViolationGraph instance"""
        kg = KnowledgeGraphManager(temp_db)
        vg = ViolationGraph(kg)
        yield vg
        kg.close()

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        yield db_path

        Path(db_path).unlink(missing_ok=True)

    def test_create_rule(self, violation_graph):
        """Test creating a violation rule"""
        rule_id = violation_graph.create_rule(
            rule_id="TEST_001",
            rule_name="Test Rule",
            description="Test violation rule",
            severity="medium",
            sql_template="SELECT * FROM test WHERE condition = 1",
            effective_from=date(2024, 1, 1),
            created_by="test_user"
        )

        assert rule_id > 0

        # Retrieve the rule
        rule = violation_graph.get_rule_by_id("TEST_001")
        assert rule is not None
        assert rule["rule_name"] == "Test Rule"
        assert rule["severity"] == "medium"

    def test_rule_versioning(self, violation_graph):
        """Test rule version management"""
        # Create initial version
        violation_graph.create_rule(
            rule_id="VER_001",
            rule_name="Versioned Rule",
            description="Version 1",
            severity="low",
            sql_template="SELECT * FROM v1",
            effective_from=date(2024, 1, 1)
        )

        # Create new version
        violation_graph.create_rule(
            rule_id="VER_001",
            rule_name="Versioned Rule",
            description="Version 2",
            severity="high",
            sql_template="SELECT * FROM v2",
            effective_from=date(2024, 2, 1),
            change_reason="Increased severity"
        )

        # Latest version should be v2
        latest = violation_graph.get_rule_by_id("VER_001")
        assert latest["version"] == 2
        assert latest["description"] == "Version 2"

    def test_initialize_core_rules(self, violation_graph):
        """Test core rules initialization"""
        violation_graph.initialize_core_rules()

        active_rules = violation_graph.get_active_rules()
        assert len(active_rules) == 5

        rule_names = [r["rule_name"] for r in active_rules]
        assert "Self-Approval Detection" in rule_names
        assert "Duplicate Expense Detection" in rule_names


class TestEntityGraph:
    """Tests for EntityGraph"""

    @pytest.fixture
    def entity_graph(self, temp_db):
        """Create EntityGraph instance"""
        kg = KnowledgeGraphManager(temp_db)
        eg = EntityGraph(kg)
        yield eg
        kg.close()

    @pytest.fixture
    def temp_db(self):
        """Create temporary database"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        yield db_path

        Path(db_path).unlink(missing_ok=True)

    def test_approval_authority(self, entity_graph):
        """Test approval authority management"""
        # Add approval authority
        auth_id = entity_graph.add_approval_authority(
            employee_id=100,
            role="Manager",
            max_amount=5000.00,
            effective_from=date(2024, 1, 1)
        )

        assert auth_id > 0

        # Retrieve authority
        authority = entity_graph.get_approval_authority(100, date(2024, 3, 15))
        assert authority is not None
        assert authority["max_amount"] == 5000.00

    def test_approval_validation(self, entity_graph):
        """Test approval authority validation"""
        entity_graph.add_approval_authority(
            employee_id=200,
            role="Director",
            max_amount=10000.00,
            effective_from=date(2024, 1, 1)
        )

        # Within limit
        assert entity_graph.validate_approval_authority(
            employee_id=200,
            amount=8000.00,
            transaction_date=date(2024, 2, 15)
        ) is True

        # Exceeds limit
        assert entity_graph.validate_approval_authority(
            employee_id=200,
            amount=15000.00,
            transaction_date=date(2024, 2, 15)
        ) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
