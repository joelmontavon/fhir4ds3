# Error Handling Guide

This guide explains the common errors you might encounter when using FHIR4DS and how to handle them.

FHIR4DS uses a hierarchy of custom exceptions to allow for specific and predictable error handling.

## Exception Hierarchy

The base exception for the library is `FHIR4DSError`. All other exceptions in the library inherit from this base exception.

```
FHIR4DSError
├── FHIRPathError
├── CQLError
├── DatabaseError
└── ComplianceError
```

-   `FHIRPathError`: Raised for errors related to parsing or evaluating a FHIRPath expression.
-   `CQLError`: Raised for errors related to Clinical Quality Language (CQL) processing.
-   `DatabaseError`: Raised for errors related to database operations.
-   `ComplianceError`: Raised for errors related to specification compliance.

## Common Errors and Resolutions

### FHIRPathError

This is one of the most common errors you will encounter. It usually means there is a mistake in your FHIRPath expression.

**Example:**

```python
from fhir4ds.datastore import QuickConnect
from fhir4ds.sql import FHIRPathError

db = QuickConnect.duckdb()

invalid_view = {
    "resource": "Patient",
    "select": [
        # This FHIRPath expression is invalid
        {"column": "name", "path": "name.given[0]"} 
    ]
}

try:
    db.execute_to_dataframe(invalid_view)
except FHIRPathError as e:
    print(f"Caught a FHIRPathError: {e}")
```

**Resolution:**

1.  **Check your FHIRPath syntax:** Carefully review your FHIRPath expression for typos or incorrect syntax. Refer to the [official FHIRPath specification](http://hl7.org/fhirpath/N1/).
2.  **Check the resource structure:** Make sure the path you are trying to access exists in the FHIR resource. For example, `Patient.telecom.value` is valid, but `Patient.phone.number` is not.

### DatabaseError

A `DatabaseError` occurs when there is an issue with the underlying database.

**Common Causes:**

*   **Connection Issues:** The database is not running, or the connection string is incorrect.
*   **Permissions:** The database user does not have the required permissions to read or write data.
*   **Unsupported Features:** You are trying to use a feature that is not supported by your database dialect.

**Resolution:**

1.  **Check your database connection:** Ensure your database is running and that your connection string is correct.
2.  **Verify permissions:** Make sure the user has the necessary `SELECT`, `INSERT`, `CREATE`, etc. permissions.
3.  **Consult database logs:** The logs for your PostgreSQL or DuckDB instance will often contain more detailed information about the error.

### Handling Errors in Production

When using FHIR4DS in a production environment, it's important to have robust error handling.

```python
import logging
from fhir4ds.datastore import QuickConnect
from fhir4ds.sql import FHIR4DSError

logging.basicConfig(level=logging.INFO)

def process_fhir_data(view_definition):
    try:
        db = QuickConnect.postgresql("your_connection_string")
        df = db.execute_to_dataframe(view_definition)
        return df
    except FHIRPathError as e:
        logging.error(f"Invalid FHIRPath expression in view: {view_definition}. Error: {e}")
        # Potentially send a notification to the development team
        raise
    except DatabaseError as e:
        logging.error(f"Database connection or query failed. Error: {e}")
        # Potentially retry the operation or alert an administrator
        raise
    except FHIR4DSError as e:
        logging.error(f"An unexpected FHIR4DS error occurred: {e}")
        raise
```
