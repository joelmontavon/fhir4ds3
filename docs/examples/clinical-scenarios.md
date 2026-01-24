# Clinical Scenarios Examples

This page provides practical examples of how to use FHIR4DS for common healthcare analytics scenarios.

## 1. Finding Patients on a Specific Medication

This example shows how to find all patients who are actively taking Lisinopril (RxNorm code `203521`).

```python
from fhir4ds.datastore import QuickConnect

db = QuickConnect.duckdb()
# Assume data is loaded

lisinopril_patients_view = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"},
        {"column": "family_name", "path": "name.family"},
        {"column": "given_name", "path": "name.given"}
    ],
    "where": [
        "MedicationRequest.where(medicationCodeableConcept.coding.where(system='http://www.nlm.nih.gov/research/umls/rxnorm' and code='203521').exists() and status='active').exists()"
    ]
}

df = db.execute_to_dataframe(lisinopril_patients_view)
print(df)
```

## 2. Calculating Average BMI for a Population

This example demonstrates how to calculate the average Body Mass Index (BMI) for all patients in the database. BMI is calculated from height and weight observations.

```python
# First, we create a view to extract height and weight for each patient.
# LOINC code for Body Height: 8302-2
# LOINC code for Body Weight: 29463-7

patient_vitals_view = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"},
        {
            "column": "height_m",
            "path": "Observation.where(code.coding.code='8302-2').valueQuantity.value / 100"
        },
        {
            "column": "weight_kg",
            "path": "Observation.where(code.coding.code='29463-7').valueQuantity.value"
        }
    ]
}

# Now, we can use the created view to calculate BMI.
# We can do this with a subsequent SQL query on the created view or table,
# or in pandas after extracting the data.

df = db.execute_to_dataframe(patient_vitals_view)

# Calculate BMI in pandas
df['bmi'] = df['weight_kg'] / (df['height_m'] ** 2)

# Calculate the average BMI
average_bmi = df['bmi'].mean()

print(f"The average BMI for the population is: {average_bmi:.2f}")
```

## 3. Identifying Patients with Multiple Chronic Conditions

This example shows how to identify patients who have been diagnosed with both Type 2 Diabetes and Hypertension.

-   SNOMED CT code for Type 2 Diabetes: `44054006`
-   SNOMED CT code for Hypertension: `38341003`

```python
multi_chronic_view = {
    "resource": "Patient",
    "select": [
        {"column": "id", "path": "id"},
        {"column": "family_name", "path": "name.family"}
    ],
    "where": [
        "Condition.where(code.coding.where(system='http://snomed.info/sct' and code='44054006').exists()).exists()",
        "and",
        "Condition.where(code.coding.where(system='http://snomed.info/sct' and code='38341003').exists()).exists()"
    ]
}

df = db.execute_to_dataframe(multi_chronic_view)
print("Patients with both Diabetes and Hypertension:")
print(df)
```
