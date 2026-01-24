# Getting Started with FHIR4DS

This guide provides a detailed walkthrough of setting up FHIR4DS, loading data, and running your first healthcare analysis.

## 1. Installation

First, install FHIR4DS using pip:

```bash
pip install fhir4ds
```

## 2. Database Setup

FHIR4DS supports both DuckDB and PostgreSQL. For this tutorial, we will use DuckDB, which is a fast, in-process analytical database.

```python
from fhir4ds.datastore import QuickConnect

# This will create a new DuckDB database file in your current directory.
db = QuickConnect.duckdb("fhir_analytics.db")
```

## 3. Downloading Sample Data

For this tutorial, we will use sample FHIR data. You can download a sample bundle from the official FHIR website. For example, you can download a sample patient bundle:

```bash
wget https://www.hl7.org/fhir/patient-example-bundle.json
```

## 4. Loading FHIR Data

Now, let's load the sample data into our database.

```python
# Load the downloaded FHIR bundle
db.load_from_json_file("patient-example-bundle.json", use_native_json=True)
```

`use_native_json=True` tells FHIR4DS to use the database's native JSON processing capabilities, which is highly recommended for performance.

## 5. Defining a ViewDefinition

A `ViewDefinition` is a powerful feature in FHIR4DS that allows you to define a cohort of patients and the data you want to extract from their records. It's a structured JSON object that uses FHIRPath expressions.

Let's create a `ViewDefinition` to extract the name, gender, and birth date of all patients.

```python
patient_demographics_view = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"},
        {"column": "family_name", "path": "name.family"},
        {"column": "given_name", "path": "name.given"},
        {"column": "gender", "path": "gender"},
        {"column": "birth_date", "path": "birthDate"}
    ]
}
```

## 6. Executing the ViewDefinition

Now that we have defined our view, let's execute it and retrieve the data as a Pandas DataFrame.

```python
# Execute the view and get a DataFrame
patient_df = db.execute_to_dataframe(patient_demographics_view)

# Display the first 5 rows of the DataFrame
print(patient_df.head())
```

## 7. A More Complex Example: Patients with a Specific Condition

Let's create a more complex `ViewDefinition` to find all patients who have a diagnosis of Type 2 Diabetes (SNOMED CT code `44054006`).

```python
diabetes_patients_view = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"},
        {"column": "family_name", "path": "name.family"},
        {"column": "given_name", "path": "name.given"}
    ],
    "where": [
        "Condition.where(code.coding.where(system = 'http://snomed.info/sct' and code = '44054006').exists()).exists()"
    ]
}

# Execute the view
diabetes_patients_df = db.execute_to_dataframe(diabetes_patients_view)

# Display the results
print(diabetes_patients_df)
```

This example shows how you can use `where` clauses with FHIRPath expressions to filter patients based on their conditions.

## 8. Next Steps

Congratulations! You have successfully installed FHIR4DS, loaded data, and performed your first analyses.

From here, you can explore more advanced topics:

*   **[Integration Guide](./integration.md)**: Learn how to integrate FHIR4DS into your existing data pipelines.
*   **[API Reference](../api/README.md)**: Dive deep into the FHIR4DS API.
*   **[Examples](../examples/README.md)**: Explore more complex and real-world examples.
