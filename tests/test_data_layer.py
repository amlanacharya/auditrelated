"""
Tests for Data Layer (Parquet + DuckDB)
"""

import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path

from audit_agent.data_layer import DataIngestion, QueryEngine, SchemaExtractor


class TestDataIngestion:
    """Tests for DataIngestion class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_csv(self, temp_dir):
        """Create sample CSV file"""
        csv_path = Path(temp_dir) / "test_data.csv"

        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "amount": [100.50, 200.75, 300.25],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"]
        })

        df.to_csv(csv_path, index=False)
        return str(csv_path)

    def test_csv_to_parquet_basic(self, sample_csv, temp_dir):
        """Test basic CSV to Parquet conversion"""
        ingestion = DataIngestion(output_base_path=temp_dir)

        metadata = ingestion.load_csv_to_parquet(
            csv_path=sample_csv,
            table_name="test_table"
        )

        assert metadata["table_name"] == "test_table"
        assert metadata["row_count"] == 3
        assert metadata["column_count"] == 4

    def test_csv_to_parquet_with_partitioning(self, sample_csv, temp_dir):
        """Test CSV to Parquet with partitioning"""
        ingestion = DataIngestion(output_base_path=temp_dir)

        metadata = ingestion.load_csv_to_parquet(
            csv_path=sample_csv,
            table_name="partitioned_table",
            date_column="date",
            partition_cols=["year", "month"]
        )

        assert metadata["partitioned"] is True
        assert metadata["partition_cols"] == ["year", "month"]


class TestQueryEngine:
    """Tests for QueryEngine class"""

    @pytest.fixture
    def sample_parquet_dir(self, tmp_path):
        """Create sample Parquet files"""
        df = pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "category": ["A", "B", "A", "C", "B"],
            "value": [10, 20, 30, 40, 50]
        })

        parquet_dir = tmp_path / "test_data"
        parquet_dir.mkdir()

        df.to_parquet(parquet_dir / "data.parquet")

        return str(tmp_path)

    def test_register_and_query(self, sample_parquet_dir):
        """Test registering table and executing query"""
        engine = QueryEngine(parquet_base_path=sample_parquet_dir)

        engine.register_parquet_table("test_data")

        result = engine.execute_query("SELECT COUNT(*) as count FROM test_data")

        assert len(result) == 1
        assert result["count"].iloc[0] == 5

        engine.close()

    def test_query_with_filter(self, sample_parquet_dir):
        """Test query with WHERE clause"""
        engine = QueryEngine(parquet_base_path=sample_parquet_dir)

        engine.register_parquet_table("test_data")

        result = engine.execute_query(
            "SELECT * FROM test_data WHERE category = 'A'"
        )

        assert len(result) == 2
        assert all(result["category"] == "A")

        engine.close()


class TestSchemaExtractor:
    """Tests for SchemaExtractor class"""

    @pytest.fixture
    def sample_parquet_data(self, tmp_path):
        """Create sample Parquet data"""
        df = pd.DataFrame({
            "employee_id": [1, 2, 3],
            "manager_id": [10, 10, 20],
            "salary": [50000, 60000, 70000]
        })

        parquet_dir = tmp_path / "employees"
        parquet_dir.mkdir()

        df.to_parquet(parquet_dir / "data.parquet")

        return str(tmp_path)

    def test_schema_extraction(self, sample_parquet_data):
        """Test schema extraction"""
        extractor = SchemaExtractor(parquet_base_path=sample_parquet_data)

        schema = extractor.extract_schema("employees")

        assert schema["table_name"] == "employees"
        assert schema["column_count"] == 3

        # Check column metadata
        column_names = [col["name"] for col in schema["columns"]]
        assert "employee_id" in column_names
        assert "manager_id" in column_names

    def test_relationship_inference(self, sample_parquet_data):
        """Test foreign key relationship inference"""
        extractor = SchemaExtractor(parquet_base_path=sample_parquet_data)

        # Extract schema first
        extractor.extract_schema("employees")

        # Infer relationships
        relationships = extractor.infer_relationships()

        # Should detect manager_id as foreign key
        fk_columns = [rel["from_column"] for rel in relationships]
        assert "manager_id" in fk_columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
