# FHIR Type Hierarchy Review

**Task**: SP-009-002 – FHIR Type Hierarchy Review  
**Sprint**: 009 – Phase 1 (testInheritance Deep Dive)  
**Author**: Junior Developer (with Senior Architect consultation)  
**Date**: 2025-10-16

---

## 1. Purpose and Scope
- Establish a canonical reference for the FHIR R4 type system needed to fix `testInheritance`.
- Document inheritance relationships across primitives, complex data types, resources, and profiles.
- Capture polymorphism rules (`value[x]`, type substitution) and resulting FHIRPath requirements.
- Identify concrete integration points for FHIR4DS (`TypeRegistry`, translator `is()/as()/ofType()`, dialect hooks).

---

## 2. FHIR R4 Type System Overview

| Category | Description | Representative Types | Key Notes |
|----------|-------------|----------------------|-----------|
| Primitive | Leaf scalar values encoded as JSON scalars | `boolean`, `string`, `integer`, `decimal`, `date`, `dateTime`, `time`, `code`, `uri`, `canonical`, `url`, `uuid`, `markdown`, `base64Binary`, `oid`, `id`, `unsignedInt`, `positiveInt` | Have lowercase names; inheritance is alias-based (e.g., `code` → `string`, `canonical` → `uri`) |
| Complex | JSON objects composed of named elements | `Quantity`, `CodeableConcept`, `Coding`, `Identifier`, `HumanName`, `Address`, `Reference`, `Annotation`, `Attachment`, `Period`, `Range`, `Ratio`, `SampledData`, `Signature`, `Timing`, `UsageContext` | Some are profiled derivatives of another complex type (`Age`, `Duration`, `Count`, `Distance` → `Quantity`) |
| Backbone | Inline complex elements that have no standalone profile but follow inheritance | `Element`, `BackboneElement`, `Dosage`, `Timing.repeat`, `Bundle.entry`, etc. | Backbone elements inherit from `Element` or `BackboneElement` and behave like complex types in FHIRPath |
| Resource | Top-level entities accessible via REST | `Resource`, `DomainResource`, `Patient`, `Observation`, `Condition`, `Procedure`, `Encounter`, `Medication`, `MedicationRequest`, `DiagnosticReport`, ... | All resources inherit from `Resource`; Domain resources also inherit from `DomainResource` to gain narrative, extensions |
| Special | Abstract FHIRPath helper types | `Any`, `Collection`, `System.String` etc. | Used internally for FHIRPath typing; map to real FHIR types during evaluation |

---

## 3. Primitive Type Hierarchy and Aliases

| Type | Canonical Base | Notes for Translator |
|------|----------------|-----------------------|
| `boolean` | `boolean` | Direct primitive |
| `integer` | `integer` | Includes `int` alias in codebase |
| `integer64` | `integer` | R4B addition used for large counts |
| `decimal` | `decimal` | Accepts scientific notation |
| `string` | `string` | Base for many aliases (`code`, `id`) |
| `code` | `string` | Value set-bound enumerations; compared as strings |
| `id` | `string` | Regex-limited string (1-64 chars) |
| `markdown` | `string` | Allows inline HTML subset |
| `uri` | `string` | Base URI; `url`, `canonical`, `uuid`, `oid` extend it |
| `url` | `uri` | More restrictive (absolute) |
| `canonical` | `uri` | References canonical resources |
| `uuid` | `uri` | RFC 4122 format |
| `oid` | `uri` | ISO object identifier |
| `base64Binary` | `base64Binary` | Byte sequences |
| `instant` | `dateTime` | Must include time zone |
| `dateTime` | `dateTime` | Second or millisecond precision + timezone |
| `date` | `dateTime` | Truncated precision (year/month/day) |
| `time` | `time` | Clock time only |
| `unsignedInt` | `integer` | ≥ 0 |
| `positiveInt` | `integer` | ≥ 1 |

**Implications**:
- Translator must canonicalise lower-case identifiers to match `FHIRDataType` enum values.
- `TypeRegistry.get_canonical_name` needs alias map for all primitives listed above (`code`, `id`, `url`, `canonical`, `uuid`, `oid`, `positiveInt`, `unsignedInt`).
- Type comparisons (`is()`, `as()`, `ofType()`) should treat alias and base as compatible (e.g., `value is string` true for `code`).

---

## 4. Complex and Profiled Type Hierarchy

### 4.1 Core Complex Types

| Complex Type | Base Type | Notes |
|--------------|-----------|-------|
| `Element` | *root* | Base for every FHIR node; carries `id`, `extension` |
| `BackboneElement` | `Element` | Adds `modifierExtension`; base for inline structures |
| `Quantity` | `Element` | value/system/code/unit/comparator |
| `CodeableConcept` | `Element` | Holds list of `Coding` + `text` |
| `Coding` | `Element` | code/system/display/version/userSelected |
| `Identifier` | `Element` | system/value/type/period/assigner |
| `HumanName` | `Element` | use/family/given/prefix/suffix |
| `Address` | `Element` | use/type/text/line/city/state/postalCode/country |
| `ContactPoint` | `Element` | system/value/use/rank/period |
| `Reference` | `Element` | reference/type/identifier/display |
| `Attachment` | `Element` | contentType/language/data/url/size/hash/title/creation |
| `Period`, `Range`, `Ratio` | `Element` | Temporal, interval, and quotient structures |

### 4.2 Profiled Quantities and Aliases

| Profiled Type | Base Complex Type | FHIR Usage |
|---------------|-------------------|------------|
| `Age` | `Quantity` | Duration in years/months/days from birth |
| `Count` | `Quantity` | Non-negative integer quantity |
| `Distance` | `Quantity` | Physical distance with UCUM units |
| `Duration` | `Quantity` | Time span (may use ISO 8601) |

### 4.3 Other Notable Derivations
- `Dosage`, `Timing`, `SampledData`, `Signature`, `DataRequirement`, `ParameterDefinition`, `TriggerDefinition` all derive from `Element` or `BackboneElement` and therefore satisfy `is(Element)` while preserving specific structure.
- Choice elements frequently embed these complex types (`Observation.value[x]` accepts `Quantity`, `CodeableConcept`, `string`, `boolean`, `Integer`, `Range`, `Ratio`, `SampledData`, `Time`, `DateTime`, `Period`).

**Implications**:
- Translator needs hierarchy metadata so `Age` satisfies `is(Quantity)` and `ofType(Quantity)` includes profiled instances.
- Registry must record parent/child for complex types; current `_type_hierarchies` only covers resources.
- SQL translators must avoid dialect-specific logic; hierarchy checks should occur before dialect call.

---

## 5. Resource Hierarchy and Inheritance Chains

### 5.1 Base Resource Chain
```
Element
└── Resource
    ├── DomainResource
    │   ├── Patient
    │   ├── Observation
    │   ├── Encounter
    │   ├── Condition
    │   ├── Procedure
    │   ├── Medication
    │   ├── MedicationRequest
    │   ├── DiagnosticReport
    │   └── ... (~120 additional domain resources)
    └── (Non-domain resources)
        ├── Bundle
        ├── Parameters
        ├── Binary
        └── Basic
```

### 5.2 Key Resource Families (examples)
- **Clinical**: `Patient` → demographic base; `Encounter` references `Patient`; `Observation` references `Patient`, `Encounter`.
- **Therapeutic**: `Medication` supplies definitional data; `MedicationRequest` references `Medication`, `Patient`.
- **Administrative**: `Organization`, `Practitioner`, `PractitionerRole`, `Location` all extend `DomainResource` and share `Meta`, `text`, `extension`.
- **Infrastructure**: `Bundle` (non-domain) inherits directly from `Resource`; special handling for `entry` backbone elements.

**Implications**:
- Resource-level `resourceType` discriminators must be preserved when evaluating `is()`/`ofType()` to ensure `Observation` satisfies `is(DomainResource)` and `is(Resource)`.
- Type registry should provide lookups for parent resources and map resource aliases to canonical names.

---

## 6. Polymorphism and `value[x]` Rules

- **Choice Elements**: Any element ending with `[x]` is polymorphic. Type is determined by suffix (e.g., `Observation.valueBoolean`, `Observation.valueQuantity`).
- **Resolution Rules**:
  1. The element name is `value` + capitalised data type (e.g., `valueQuantity` → `Quantity`).
  2. The base type is taken from declared list; conversions are not implicit (e.g., `valueString` is *not* a `code` unless specified).
  3. Collections preserve order; `ofType()` filters while retaining collection semantics.
- **Profiles**: Profiles may constrain allowed types (e.g., `value[x]` limited to `CodeableConcept` in a profile). Translator must allow custom constraints by reading StructureDefinitions (future work).

**Implications**:
- Translator should surface polymorphic candidates through metadata so SQL generator can project correct JSON paths.
- `TypeRegistry` (or adjacent metadata service) must expose allowed types per polymorphic element for validation and generating `ofType()` filters.

---

## 7. FHIRPath Type Semantics

| Function | Behaviour | Required Data |
|----------|-----------|---------------|
| `is(type)` | Returns `true` if input is instance of `type` or subtype | Canonical type names, hierarchy lookup, primitive alias mapping |
| `as(type)` | Casts to `type`; returns empty (`{}` / `NULL`) if incompatible | Same as `is()`, plus conversion helpers for primitives |
| `ofType(type)` | Filters collection to members of `type`/subtype | Hierarchy metadata + polymorphic element awareness |

Additional rules:
- `is()` short-circuits to `false` when type is unknown → translator must warn once and propagate `false`.
- `as()` returns empty collection for collection inputs; translator must preserve cardinality semantics.
- Comparisons perform implicit conversion only within primitive family (`integer` ↔ `decimal`, `date` ↔ `dateTime`), otherwise fail.
- FHIRPath uses case-sensitive type names; translator must reject `String` but accept `string`.

---

## 8. Integration Points for FHIR4DS

### 8.1 Type Registry Enhancements
- Expand `_type_aliases` to include all primitive aliases and profiled quantities.
- Populate `_type_hierarchies` with:
  - Primitive inheritance (e.g., `string` parents: `code`, `id`, `markdown`).
  - Complex inheritance (e.g., `Quantity` parents: `Age`, `Count`, `Distance`, `Duration`).
  - Full resource tree (subset delivered here; complete list sourced from StructureDefinition metadata).
- Provide bidirectional checks: `is_subtype_of(child, parent)` should recurse through multi-level chains.

### 8.2 Translator Adjustments
- Update `_translate_is_from_function_call`, `_translate_as_from_function_call`, `_translate_oftype_from_function_call` to:
  - Canonicalise type tokens via registry before dialect invocation.
  - Request hierarchy membership to determine truthiness/filtering.
  - Propagate warnings for unknown types using registry diagnostics.
- Ensure polymorphic elements consult element metadata (temporary: resource-specific maps; long-term: metadata service).

### 8.3 Dialect Requirements
- Maintain thin dialect principle: dialects receive canonical type names and evaluate using syntax helpers only.
- Provide syntax hooks for:
  - JSON type discrimination (`json_typeof`, `typeof`, `jsonb_typeof`).
  - Array filtering without per-row iteration (e.g., `FILTER (WHERE ...)` in PostgreSQL, `list_filter` functions in DuckDB).

### 8.4 Data Sources
- Leverage official StructureDefinition snapshots (cached offline) to populate hierarchy metadata (to be addressed in SP-009-003/004).
- Temporary fallback: curated YAML/JSON describing primitive/complex/resource hierarchies, maintained under `project-data/fhir/hierarchy/`.

---

## 9. Acceptance Checklist
- [x] FHIR type hierarchy documented (primitives, complex, backbone, resources, special)
- [x] Inheritance chains captured for key resources and profiled complex types
- [x] Polymorphic element rules and `value[x]` behaviour described
- [x] FHIRPath type requirements (`is`, `as`, `ofType`) detailed with data needs
- [x] Integration points identified for translator, registry, and dialect layers

---

## 10. Dependencies, Risks, and Next Steps

| Type | Description | Impact | Owner |
|------|-------------|--------|-------|
| Dependency | StructureDefinition metadata ingestion (planned SP-009-003/004) | Required for automated hierarchy sync | Senior Architect |
| Risk | Manual alias lists can drift from spec updates | Medium: requires governance + unit tests in SP-009-006 | Junior Dev |
| Risk | Translator changes could regress DuckDB/PostgreSQL parity | High: enforce dual-dialect tests before merge | Junior Dev + QA |
| Next Step | Decide implementation vs. PEP based on complexity (SP-009-003) | Governs Sprint 009 scope | Senior Architect |
| Next Step | Prototype registry enhancements with canonicalisation tests | Provides safety net for translator work | Junior Dev |

---

## Appendix A – Reference Tables

### A.1 Primitive → Canonical Mapping

| Alias | Canonical | Notes |
|-------|-----------|-------|
| `bool` | `boolean` | Existing alias |
| `boolean` | `boolean` | identity |
| `int` | `integer` | Existing alias |
| `integer` | `integer` | identity |
| `integer64` | `integer64` | Provided for completeness; treat as `integer` parent |
| `unsignedInt` | `unsignedInt` | Non-negative integer |
| `positiveInt` | `positiveInt` | Positive integer |
| `decimal` | `decimal` | identity |
| `str` | `string` | Existing alias |
| `string` | `string` | identity |
| `code` | `code` | Canonical string alias |
| `id` | `id` | Canonical string alias |
| `markdown` | `markdown` | Canonical string alias |
| `uri` | `uri` | Base for URI derivatives |
| `url` | `url` | Derived from `uri` |
| `canonical` | `canonical` | Derived from `uri` |
| `uuid` | `uuid` | Derived from `uri` |
| `oid` | `oid` | Derived from `uri` |
| `base64Binary` | `base64Binary` | identity |
| `instant` | `instant` | Derived from `dateTime` |
| `dateTime` | `dateTime` | identity |
| `date` | `date` | Derived from `dateTime` |
| `time` | `time` | identity |

### A.2 Complex/Resource Hierarchy Snippets (Non-Exhaustive)

| Parent | Children |
|--------|----------|
| `Element` | `BackboneElement`, all primitives via `value`, all complex types |
| `BackboneElement` | `Dosage`, `Timing.repeat`, `Bundle.entry`, `Observation.component`, etc. |
| `Quantity` | `Age`, `Count`, `Duration`, `Distance`, `SimpleQuantity` |
| `CodeableConcept` | Profiled variants (e.g., `CodeableConcept-medication`) |
| `Resource` | `DomainResource`, `Bundle`, `Parameters`, `Binary`, `Basic` |
| `DomainResource` | `Patient`, `Observation`, `Condition`, `Encounter`, `Procedure`, `Medication`, `MedicationRequest`, `DiagnosticReport`, `Organization`, `Practitioner`, ... |

> **Note**: Complete child lists should be generated from StructureDefinition snapshots. This document prioritises the relationships required for `testInheritance` and immediate translator fixes.

---

## Appendix B – References
- HL7® FHIR® Release 4 (R4) Specification, Sections 1.3 (Types), 3.1 (Data Types), and 1.7 (FHIRPath).
- FHIRPath Specification (v2.0.0) – Type system and functions `is`, `as`, `ofType`.
- `project-docs/analysis/testinheritance-root-cause-analysis.md` – Source findings for this review.

