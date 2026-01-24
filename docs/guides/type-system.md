# FHIR Type System Guide

This guide explains how FHIR4DS handles FHIR data types and how you can work with them in your queries.

## FHIR Type System Overview

FHIR defines a rich set of data types, from simple primitives like `string` and `boolean` to complex types like `CodeableConcept` and `Timing`. FHIR4DS is designed to handle these types correctly and efficiently.

When you load FHIR resources, FHIR4DS maps the FHIR types to the appropriate database types. For complex types, FHIR4DS stores them as JSON objects in the database.

## Working with Complex Types

Most of the time, you will interact with complex types through FHIRPath expressions. The FHIRPath engine in FHIR4DS knows how to navigate these complex structures.

**Example: Accessing data in a `CodeableConcept`**

A `CodeableConcept` is a complex type that represents a concept, often from a terminology like SNOMED CT or LOINC. It can contain multiple codings.

Let's say you have a `Condition` resource with a `code` that is a `CodeableConcept`:

```json
{
  "resourceType": "Condition",
  "code": {
    "coding": [
      {
        "system": "http://snomed.info/sct",
        "code": "44054006",
        "display": "Type 2 diabetes mellitus"
      }
    ]
  }
}
```

To select conditions with a specific SNOMED CT code, you can use the following FHIRPath expression in a `where` clause:

```python
view_definition = {
    "resource": "Condition",
    "select": [{"column": "id", "path": "id"}],
    "where": [
        "code.coding.where(system = 'http://snomed.info/sct' and code = '44054006').exists()"
    ]
}
```

## Type Casting and Conversion

FHIRPath includes functions for casting and converting between types.

-   `as(type)`: Converts the input to a specific type. If the conversion is not possible, the result is an empty collection.
-   `is(type)`: Returns `true` if the input is of a specific type.

**Example: Working with `dateTime`**

FHIR `dateTime` values can have varying precision (e.g., year, year-month, full date). FHIR4DS preserves this precision.

```python
# Select patients born in 1974
view_definition = {
    "resource": "Patient",
    "select": [{"column": "id", "path": "id"}],
    "where": [
        "birthDate.toDateTime().year = 1974"
    ]
}
```

## Handling Missing Data

In FHIR, it's common for elements to be optional. When you write FHIRPath queries, you need to account for the possibility of missing data.

The `exists()` function is very useful for this.

**Example: Find patients who have a telecom number**

```python
view_definition = {
    "resource": "Patient",
    "select": [{"column": "id", "path": "id"}],
    "where": [
        "telecom.exists()"
    ]
}
```

If you try to access a path that doesn't exist, the result will be an empty collection, and it will not cause an error. This is a key concept in FHIRPath.

## Best Practices

*   **Always use `where` clauses with `exists()`** to check for the presence of data before trying to access it, especially for nested elements.
*   **Be specific in your `CodeableConcept` queries.** Always specify the `system` and `code` to avoid ambiguity.
*   **Understand the structure of the FHIR resources** you are working with. The official FHIR documentation is an excellent resource.
