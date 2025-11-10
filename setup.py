from setuptools import setup, find_packages

setup(
    name="audit-agent",
    version="0.1.0",
    description="Intelligent Audit Agent - 90% SQL + 10% AI for compliance-grade violation detection",
    author="Audit Agent Team",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "duckdb>=0.9.0",
        "pyarrow>=14.0.0",
        "pandas>=2.0.0",
        "sqlalchemy>=2.0.0",
        "faker>=20.0.0",
        "numpy>=1.24.0",
        "structlog>=23.0.0",
        "prometheus-client>=0.19.0",
        "psycopg2-binary>=2.9.0",
        "python-dateutil>=2.8.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ]
    },
)
