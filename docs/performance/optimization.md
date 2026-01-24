# Performance Optimization Guide

This guide provides strategies and best practices for optimizing the performance of your FHIR4DS queries, especially when working with large, population-scale datasets.

## General Principles

### 1. Filter as Early as Possible

The single most important thing you can do to improve performance is to reduce the amount of data that needs to be processed. Use the `where` clause in your `ViewDefinition` to filter data as early as possible.

**Good:**
```python
view = {
    "resource": "Observation",
    "select": [{"column": "value", "path": "valueQuantity.value"}],
    "where": ["code.coding.code = '85354-9'"] # Filter for COVID-19 test results
}
```

**Bad:**
```python
# Avoid filtering in Python after extracting all the data
view = {
    "resource": "Observation",
    "select": [
        {"column": "code", "path": "code.coding.code"},
        {"column": "value", "path": "valueQuantity.value"}
    ]
}
df = db.execute_to_dataframe(view)
covid_results = df[df['code'] == '85354-9']
```

### 2. Select Only the Columns You Need

Avoid using `select *`. Only select the columns that you need for your analysis. This reduces the amount of data that needs to be moved and processed.

### 3. Use Native JSON Processing

When loading data from JSON files, always use `use_native_json=True`. This allows the database to use its optimized JSON processing capabilities.

```python
db.load_from_json_file("my_data.json", use_native_json=True)
```

## Database-Specific Optimizations

### DuckDB

-   **Memory Management:** DuckDB is an in-memory database, so make sure you have enough RAM for your dataset. For very large datasets, DuckDB can spill to disk, but performance will be best if the data fits in memory.
-   **Parallelism:** DuckDB automatically parallelizes queries. You can control the number of threads using `db.execute("PRAGMA threads=4")`.

### PostgreSQL

-   **Indexing:** For large tables, creating indexes on frequently queried columns can dramatically improve performance. This is especially important for columns used in `where` clauses.

    ```sql
    CREATE INDEX patient_birthdate_idx ON patient (birthdate);
    ```

-   **Vacuum and Analyze:** Keep your database statistics up to date by running `VACUUM ANALYZE` regularly. This helps the query planner make better decisions.

## FHIRPath Performance

-   **`exists()` is your friend:** When you just need to check for the existence of something, `exists()` is very efficient. For example, `Condition.where(...).exists()` is much faster than `Condition.where(...).count() > 0`.
-   **Avoid overly complex expressions:** While FHIRPath is very powerful, extremely complex, nested expressions can be slow. If a FHIRPath expression becomes too complex, consider breaking it down into multiple `ViewDefinition`s and creating intermediate tables or views.

## Benchmarking and Profiling

FHIR4DS is instrumented to allow for performance profiling.

*(Note: The performance monitoring features are under active development. The following is a preview of how they will work.)*

```python
from fhir4ds.performance import profiler

with profiler.profile() as p:
    db.execute_to_dataframe(my_view)

p.print_stats()
```

This will give you a detailed breakdown of where time is being spent in the query, from FHIRPath parsing to SQL generation and execution.
