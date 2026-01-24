# Advanced Usage and Best Practices

This guide covers advanced features and best practices to help you get the most out of FHIR4DS.

## Advanced ViewDefinitions

### Joins between Resources

FHIRPath allows you to traverse references between resources, which enables you to perform joins.

**Example: Get the name of the managing organization for each patient**

```python
view_definition = {
    "resource": "Patient",
    "select": [
        {"column": "patient_id", "path": "id"},
        {
            "column": "organization_name",
            "path": "managingOrganization.resolve().name"
        }
    ]
}
```

The `resolve()` function is a powerful feature that follows the reference to the `Organization` resource.

### Using Variables

You can define variables within your `ViewDefinition` to simplify complex expressions and improve readability.

```python
view_definition = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"}
    ],
    "where": [
        "%loinc_hba1c_code = '4548-4'",
        "Observation.where(code.coding.code = %loinc_hba1c_code and valueQuantity.value > 7.5).exists()"
    ]
}
```

## Performance Best Practices

### 1. Use Native JSON Types

When loading data with `load_from_json_file`, always set `use_native_json=True`. This leverages the database's native JSON support and is significantly faster.

### 2. Filter Early and Often

Use `where` clauses to filter your data as much as possible. The more specific your `where` clauses are, the less data the database has to process.

### 3. Create Indexes

If you are frequently querying on specific fields, consider creating indexes on those columns in your database. This is particularly important for PostgreSQL.

For example, if you often search for patients by name, you could create an index on the `name` column of the `Patient` table.

### 4. Use `execute_to_parquet` for Large Exports

When exporting large amounts of data, Parquet is the most efficient format. It's a columnar storage format that is highly compressed and optimized for analytics.

## Working with Clinical Quality Language (CQL)

FHIR4DS has experimental support for CQL. The CQL engine translates CQL expressions into FHIRPath, which is then converted to SQL.

```python
from fhir4ds.cql.core.engine import CQLEngine

# Initialize the CQL engine
cql_engine = CQLEngine(dialect="duckdb")

# Evaluate a simple CQL expression
sql_query = cql_engine.evaluate_expression("Patient.name.family")

# You can then execute this SQL query against your database
```

### Population-Based Queries

The CQL engine is optimized for population-based queries.

```python
cql_engine.set_population_context({
    'ageRange': (30, 50),
    'gender': 'male'
})

# This will now be executed in the context of males between 30 and 50
sql_for_population = cql_engine.evaluate_expression("Condition.code.coding.display")
```

## Contributing to FHIR4DS

We welcome contributions! Please see the `CONTRIBUTING.md` file for more information on how to contribute to the project.
