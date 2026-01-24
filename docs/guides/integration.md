# Integration Guide

This guide provides instructions on how to integrate FHIR4DS with your existing data infrastructure, with a focus on DuckDB and PostgreSQL.

## Integrating with DuckDB

DuckDB is an in-process analytical database that is easy to use and requires no external dependencies. This makes it a great choice for local development, research, and embedding analytics into Python applications.

### Connecting to an Existing DuckDB Database

If you already have a DuckDB database with other data, you can easily connect to it and use FHIR4DS alongside your existing tables.

```python
from fhir4ds.datastore import QuickConnect

db = QuickConnect.duckdb("my_existing_database.db")

# You can now use FHIR4DS to load FHIR data, and it will be stored
# in the same database file, allowing you to join FHIR data
# with your other tables.
```

### Accessing FHIR4DS Data from other Tools

Since FHIR4DS stores data in standard DuckDB tables, you can access the data from any tool that supports DuckDB. For example, you can use the DuckDB CLI to query the data directly:

```bash
duckdb fhir_analytics.db

> .tables
> SELECT * FROM patient;
```

## Integrating with PostgreSQL

PostgreSQL is a powerful, open-source object-relational database system with over 30 years of active development that has earned it a strong reputation for reliability, feature robustness, and performance.

### Connecting to a PostgreSQL Database

To connect to a PostgreSQL database, you will need to provide a connection string.

```python
from fhir4ds.datastore import QuickConnect

# Make sure you have the psycopg2-binary package installed: pip install psycopg2-binary

connection_string = "postgresql://user:password@host:port/database_name"
db = QuickConnect.postgresql(connection_string)
```

### Schema Management

When working with a shared PostgreSQL database, it's a good practice to use a dedicated schema for your FHIR data.

```python
# Create a new schema for your FHIR data
db.create_schema("fhir_data")

# When loading data, you can specify the schema
db.load_resources(fhir_resources, schema="fhir_data")
```

## Exporting Data

FHIR4DS provides several options for exporting data, which makes it easy to integrate with other systems.

### Pandas DataFrame

The most common way to work with data in Python is using Pandas DataFrames.

```python
dataframe = db.execute_to_dataframe(my_view_definition)
```

### Parquet, CSV, and Excel

For larger datasets or for integration with other systems, you can export to various file formats.

```python
# Export to Parquet for efficient storage and use with systems like Spark
db.execute_to_parquet(my_view_definition, "output.parquet")

# Export to CSV
db.execute_to_csv(my_view_definition, "output.csv")

# Export multiple views to a single Excel file with multiple sheets
db.execute_to_excel([view1, view2], "report.xlsx")
```

## Using FHIR4DS in a Data Pipeline

Here is an example of how you might use FHIR4DS in a larger data pipeline, for example, using a workflow orchestrator like Airflow.

```python
# This could be an Airflow task
def run_fhir_analysis():
    from fhir4ds.datastore import QuickConnect

    # Connect to the production database
    db = QuickConnect.postgresql("postgresql://user:pass@prod_host:5432/analytics")

    # Define the analysis
    daily_admissions_view = {
        "resource": "Encounter",
        "select": [
            {"column": "id", "path": "id"},
            {"column": "start_date", "path": "period.start"}
        ],
        "where": [
            "period.start >= today() - 1.day"
        ]
    }

    # Run the analysis and save to a table
    db.create_table(daily_admissions_view, "daily_admissions_report", schema="reports")

if __name__ == "__main__":
    run_fhir_analysis()
```
