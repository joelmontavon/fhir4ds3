# FHIR R4 StructureDefinition Files

## Source
These files are from the official FHIR R4 specification:
- **URL**: https://hl7.org/fhir/R4/definitions.json.zip
- **Version**: FHIR R4 (4.0.1)
- **Downloaded**: 2025-10-18

## License
These FHIR specification files are released under the **CC0 1.0 Universal (CC0 1.0) Public Domain Dedication**:
https://creativecommons.org/publicdomain/zero/1.0/

## Contents
- `profiles-resources.json` - StructureDefinition files for all FHIR R4 resources
- `profiles-types.json` - StructureDefinition files for all FHIR R4 data types
- `profiles-others.json` - Additional profile definitions
- `valuesets.json` - FHIR value set definitions
- Other definition files for extensions, concept maps, etc.

## Usage
The `StructureDefinitionLoader` module (`structure_loader.py`) loads and parses these files to extract:
1. Resource type hierarchies (Patient → DomainResource → Resource)
2. BackboneElement structural definitions
3. Profile constraints (Age, Duration profiles of Quantity)
4. Element cardinality metadata (0..1 vs 0..*)

## Attribution
FHIR® is a registered trademark of HL7 International.
