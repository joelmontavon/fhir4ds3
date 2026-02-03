"""
FHIR Type Registry - Type Registration and Lookup System

This module provides a registry system for FHIR types that integrates with the
production FHIRPath parser to enable proper type management and lookup.
"""

from typing import Dict, Type, Optional, Any, Set, List
from abc import ABC, abstractmethod
from pathlib import Path
import logging

from .fhir_types import FHIRDataType, FHIRTypeValidator, FHIRTypeSystem, resolve_polymorphic_property, PrimitiveTypeValidator


class TypeRegistry:
    """
    Central registry for FHIR type management and lookup

    Provides a centralized system for registering, looking up, and managing
    FHIR types with their associated validators and metadata.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Core type system
        self._type_system = FHIRTypeSystem()

        # Type registry mappings
        self._type_validators: Dict[str, FHIRTypeValidator] = {}
        self._type_metadata: Dict[str, Dict[str, Any]] = {}
        self._type_aliases: Dict[str, str] = {}
        self._type_hierarchies: Dict[str, Set[str]] = {}

        # StructureDefinition loader (NEW)
        self._structure_loader: Optional['StructureDefinitionLoader'] = None
        self._type_hierarchies_extended: Dict[str, Set[str]] = {}
        self._backbone_elements: Dict[str, Dict[str, Any]] = {}
        self._profile_constraints: Dict[str, Dict[str, Any]] = {}
        self._element_definitions: Dict[str, Dict[str, Any]] = {}

        # Initialize with standard FHIR types
        self._initialize_standard_types()

    def _initialize_standard_types(self) -> None:
        """Initialize registry with standard FHIR types"""
        # Register all standard FHIR data types
        for fhir_type in FHIRDataType:
            type_name = fhir_type.value

            # Get validator from type system
            if fhir_type in self._type_system._validators:
                validator = self._type_system._validators[fhir_type]
                self._type_validators[type_name] = validator

            # Set up type metadata
            self._type_metadata[type_name] = {
                'fhir_type': fhir_type,
                'is_primitive': self._type_system.is_primitive_type(type_name),
                'is_complex': self._type_system.is_complex_type(type_name),
                'is_resource': self._type_system.is_resource_type(type_name),
                'description': self._get_type_description(fhir_type)
            }

        # Set up type aliases
        self._setup_type_aliases()

        # Set up type hierarchies
        self._setup_type_hierarchies()

        # Register profile-based types not present in core enumeration
        self._type_metadata.setdefault('Duration', {
            'custom_type': True,
            'description': 'FHIR Duration profile of Quantity',
            'is_primitive': False,
            'is_complex': True,
            'is_resource': False
        })

        # Register FHIR primitive subtypes (FHIR R4 defines these as distinct types)
        primitive_subtypes = {
            'string1': {
                'base_type': 'string',
                'description': 'FHIR string primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'code1': {
                'base_type': 'string',
                'description': 'FHIR code primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'integer1': {
                'base_type': 'integer',
                'description': 'FHIR integer primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'decimal1': {
                'base_type': 'decimal',
                'description': 'FHIR decimal primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'boolean1': {
                'base_type': 'boolean',
                'description': 'FHIR boolean primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'uri1': {
                'base_type': 'uri',
                'description': 'FHIR URI primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'base64binary1': {
                'base_type': 'base64Binary',
                'description': 'FHIR base64Binary primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'instant1': {
                'base_type': 'instant',
                'description': 'FHIR instant primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'date1': {
                'base_type': 'date',
                'description': 'FHIR date primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'datetime1': {
                'base_type': 'dateTime',
                'description': 'FHIR dateTime primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'time1': {
                'base_type': 'time',
                'description': 'FHIR time primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'id1': {
                'base_type': 'id',
                'description': 'FHIR id primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'positiveint1': {
                'base_type': 'positiveInt',
                'description': 'FHIR positiveInt primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'unsignedint1': {
                'base_type': 'unsignedInt',
                'description': 'FHIR unsignedInt primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            },
            'markdown1': {
                'base_type': 'markdown',
                'description': 'FHIR markdown primitive subtype',
                'is_primitive': True,
                'is_primitive_subtype': True,
                'is_complex': False,
                'is_resource': False
            }
        }

        # Register primitive subtypes with metadata
        for subtype_name, metadata in primitive_subtypes.items():
            self._type_metadata[subtype_name] = metadata
            # Create validator based on base type
            base_type_name = metadata['base_type']
            if base_type_name == 'string':
                base_enum = FHIRDataType.STRING
            elif base_type_name == 'integer':
                base_enum = FHIRDataType.INTEGER
            elif base_type_name == 'decimal':
                base_enum = FHIRDataType.DECIMAL
            elif base_type_name == 'boolean':
                base_enum = FHIRDataType.BOOLEAN
            elif base_type_name == 'uri':
                base_enum = FHIRDataType.URI
            elif base_type_name == 'base64Binary':
                base_enum = FHIRDataType.BASE64BINARY
            elif base_type_name == 'instant':
                base_enum = FHIRDataType.INSTANT
            elif base_type_name == 'date':
                base_enum = FHIRDataType.DATE
            elif base_type_name == 'dateTime':
                base_enum = FHIRDataType.DATETIME
            elif base_type_name == 'time':
                base_enum = FHIRDataType.TIME
            elif base_type_name == 'id':
                base_enum = FHIRDataType.ID
            elif base_type_name == 'positiveInt':
                base_enum = FHIRDataType.POSITIVEINT
            elif base_type_name == 'unsignedInt':
                base_enum = FHIRDataType.UNSIGNEDINT
            elif base_type_name == 'markdown':
                base_enum = FHIRDataType.MARKDOWN
            else:
                continue

            self._type_validators[subtype_name] = PrimitiveTypeValidator(base_enum)

        # Load StructureDefinitions if available
        definitions_path = Path(__file__).parent / "fhir_r4_definitions"
        if definitions_path.exists():
            try:
                self.load_structure_definitions(definitions_path)
                self.logger.info(f"Loaded FHIR R4 StructureDefinitions from {definitions_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load StructureDefinitions: {e}")

    def _get_type_description(self, fhir_type: FHIRDataType) -> str:
        """Get description for a FHIR type"""
        descriptions = {
            FHIRDataType.BOOLEAN: "FHIR boolean primitive type (true/false)",
            FHIRDataType.INTEGER: "FHIR integer primitive type",
            FHIRDataType.STRING: "FHIR string primitive type",
            FHIRDataType.DECIMAL: "FHIR decimal primitive type",
            FHIRDataType.DATE: "FHIR date primitive type (YYYY-MM-DD)",
            FHIRDataType.DATETIME: "FHIR dateTime primitive type",
            FHIRDataType.INSTANT: "FHIR instant primitive type",
            FHIRDataType.TIME: "FHIR time primitive type",
            FHIRDataType.CODE: "FHIR code primitive type",
            FHIRDataType.URI: "FHIR URI primitive type",
            FHIRDataType.URL: "FHIR URL primitive type",
            FHIRDataType.ID: "FHIR id primitive type",

            # Complex types
            FHIRDataType.QUANTITY: "FHIR Quantity complex type (value with unit)",
            FHIRDataType.CODING: "FHIR Coding complex type (code from terminology)",
            FHIRDataType.CODEABLECONCEPT: "FHIR CodeableConcept complex type",
            FHIRDataType.REFERENCE: "FHIR Reference complex type",
            FHIRDataType.IDENTIFIER: "FHIR Identifier complex type",
            FHIRDataType.PERIOD: "FHIR Period complex type (start/end dates)",
            FHIRDataType.RANGE: "FHIR Range complex type (low/high values)",
            FHIRDataType.RATIO: "FHIR Ratio complex type",
            FHIRDataType.ATTACHMENT: "FHIR Attachment complex type",

            # Resource types
            FHIRDataType.PATIENT: "FHIR Patient resource",
            FHIRDataType.OBSERVATION: "FHIR Observation resource",
            FHIRDataType.ENCOUNTER: "FHIR Encounter resource",
            FHIRDataType.CONDITION: "FHIR Condition resource",
            FHIRDataType.PROCEDURE: "FHIR Procedure resource",
            FHIRDataType.MEDICATION: "FHIR Medication resource",

            # Special types
            FHIRDataType.ANY: "Special type accepting any value",
            FHIRDataType.COLLECTION: "Special collection type"
        }

        return descriptions.get(fhir_type, f"FHIR {fhir_type.value} type")

    def _setup_type_aliases(self) -> None:
        """Set up common type aliases"""
        self._type_aliases.update({
            # Core shorthand primitives
            'bool': 'boolean',
            'boolean': 'boolean',
            'system.boolean': 'boolean',
            'int': 'integer',
            'integer': 'integer',
            'system.integer': 'integer',
            'integer64': 'integer64',
            'str': 'string',
            'string': 'string',
            'system.string': 'string',
            'float': 'decimal',
            'decimal': 'decimal',
            'system.decimal': 'decimal',

            # Collection helpers
            'list': 'Collection',
            'array': 'Collection',

            # FHIR primitive aliases (canonicalisation to underlying primitive)
            'code': 'string',
            'markdown': 'string',
            'base64binary': 'string',
            'canonical': 'uri',
            'uri': 'uri',
            'system.uri': 'uri',
            'url': 'uri',
            'uuid': 'uri',
            'oid': 'uri',
            'id': 'string',

            'unsignedint': 'integer',
            'unsignedInt': 'integer',
            'positiveint': 'integer',
            'positiveInt': 'integer',

            # Temporal aliases
            'datetime': 'dateTime',
            'system.datetime': 'dateTime',
            'date': 'date',
            'system.date': 'date',
            'time': 'time',
            'system.time': 'time',
            'instant': 'instant',
            'system.instant': 'instant',

            # Quantity profile aliases (FHIR choice types)
            'age': 'Quantity',
            'Age': 'Quantity',
            'count': 'Quantity',
            'Count': 'Quantity',
            'distance': 'Quantity',
            'Distance': 'Quantity',
            'duration': 'Quantity',
            'Duration': 'Quantity',
            'moneyquantity': 'Quantity',
            'moneyQuantity': 'Quantity',
            'simplequantity': 'Quantity',
            'simpleQuantity': 'Quantity',
            'system.quantity': 'Quantity',
        })

    def get_canonical_type_name(self, type_name: str) -> Optional[str]:
        """Public helper to resolve a type name to its canonical representation."""
        return self.resolve_to_canonical(type_name)

    def is_valid_type(self, type_name: str) -> bool:
        """Determine whether the supplied type or alias is registered."""
        return self.resolve_to_canonical(type_name) is not None

    def resolve_to_canonical(self, type_name: str) -> Optional[str]:
        """
        Resolve a type name or alias to its canonical FHIR type name.

        Args:
            type_name: Type name or alias to resolve.

        Returns:
            Canonical type name if known, None otherwise.
        """
        if not type_name:
            return None

        candidate = type_name.strip().strip('`')
        if not candidate:
            return None

        if "." in candidate:
            prefix, remainder = candidate.split(".", 1)
            if prefix.lower() in {"system", "fhir"} and remainder:
                candidate = remainder.strip().strip('`')

        lowered = candidate.lower()

        # Aliases take precedence for canonicalisation (e.g., code → string)
        for alias, canonical in self._type_aliases.items():
            if alias.lower() == lowered:
                return canonical

        # Fall back to direct type lookup (case-insensitive)
        for registered in self._type_metadata.keys():
            if registered.lower() == lowered:
                return registered

        return None

    def _setup_type_hierarchies(self) -> None:
        """Set up type inheritance hierarchies"""
        # Resource hierarchy
        resource_types = {
            'Resource': {'DomainResource'},
            'DomainResource': {'Patient', 'Observation', 'Encounter', 'Condition',
                              'Procedure', 'Medication', 'Organization', 'Practitioner'}
        }

        # Set up hierarchies
        for parent, children in resource_types.items():
            if parent not in self._type_hierarchies:
                self._type_hierarchies[parent] = set()
            self._type_hierarchies[parent].update(children)

    def register_type(
        self,
        type_name: str,
        validator: FHIRTypeValidator,
        metadata: Optional[Dict[str, Any]] = None,
        aliases: Optional[List[str]] = None
    ) -> None:
        """
        Register a new FHIR type

        Args:
            type_name: Name of the type to register
            validator: Type validator instance
            metadata: Additional type metadata
            aliases: Alternative names for the type
        """
        self._type_validators[type_name] = validator

        # Set up metadata
        type_metadata = {
            'custom_type': True,
            'description': f"Custom FHIR type: {type_name}"
        }
        if metadata:
            type_metadata.update(metadata)

        self._type_metadata[type_name] = type_metadata

        # Register aliases
        if aliases:
            for alias in aliases:
                self._type_aliases[alias] = type_name

        self.logger.info(f"Registered custom FHIR type: {type_name}")

    def get_validator(self, type_name: str) -> Optional[FHIRTypeValidator]:
        """
        Get validator for a type name

        Args:
            type_name: Type name to look up

        Returns:
            Type validator if found, None otherwise
        """
        canonical_name = self.resolve_to_canonical(type_name)

        if canonical_name and canonical_name in self._type_validators:
            return self._type_validators[canonical_name]

        return None

    def get_type_metadata(self, type_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a type

        Args:
            type_name: Type name to look up

        Returns:
            Type metadata if found, None otherwise
        """
        canonical_name = self.resolve_to_canonical(type_name)

        if canonical_name and canonical_name in self._type_metadata:
            return self._type_metadata[canonical_name].copy()

        return None

    def is_registered_type(self, type_name: str) -> bool:
        """
        Check if a type is registered

        Args:
            type_name: Type name to check

        Returns:
            True if type is registered
        """
        return self.resolve_to_canonical(type_name) is not None

    def get_canonical_name(self, type_name: str) -> str:
        """
        Get canonical name for a type (resolves aliases)

        Args:
            type_name: Type name (possibly an alias)

        Returns:
            Canonical type name
        """
        canonical = self.resolve_to_canonical(type_name)
        return canonical if canonical is not None else type_name

    def is_compatible_type(self, value: Any, type_name: str) -> bool:
        """
        Check if a value is compatible with a type

        Args:
            value: Value to check
            type_name: Target type name

        Returns:
            True if compatible
        """
        validator = self.get_validator(type_name)
        if validator:
            return validator.is_valid(value)

        # Fall back to type system
        return self._type_system.is_type(value, type_name)

    def convert_value(self, value: Any, type_name: str) -> Any:
        """
        Convert a value to a specific type

        Args:
            value: Value to convert
            type_name: Target type name

        Returns:
            Converted value

        Raises:
            ValueError: If conversion is not possible
        """
        validator = self.get_validator(type_name)
        if validator:
            return validator.convert(value)

        # Fall back to type system
        return self._type_system.convert_to_type(value, type_name)

    def get_type_hierarchy(self, type_name: str) -> Set[str]:
        """
        Get type hierarchy for a type (subtypes)

        Args:
            type_name: Parent type name

        Returns:
            Set of subtype names
        """
        return self._type_hierarchies.get(type_name, set()).copy()

    def is_subtype_of(self, subtype: str, parent_type: str) -> bool:
        """
        Check if one type is a DIRECT subtype of another

        Args:
            subtype: Potential subtype
            parent_type: Potential parent type

        Returns:
            True if subtype is a DIRECT subtype of parent_type
        """
        canonical_parent = self.resolve_to_canonical(parent_type) or parent_type
        canonical_subtype = self.resolve_to_canonical(subtype) or subtype

        if canonical_parent == canonical_subtype:
            return True

        # Check primitive subtypes
        subtype_metadata = self._type_metadata.get(canonical_subtype, {})
        if subtype_metadata.get('is_primitive_subtype') and subtype_metadata.get('base_type') == canonical_parent:
            return True

        # Check explicit hierarchies first (direct subtypes only)
        hierarchy = self.get_type_hierarchy(canonical_parent)
        if canonical_subtype in hierarchy:
            return True

        # Only check StructureDefinition loader if canonical parent is not part
        # of the handcrafted hierarchies (avoids duplicate work).
        if self._structure_loader and canonical_parent not in self._type_hierarchies:
            return self._structure_loader.is_subtype_of(canonical_subtype, canonical_parent)

        return False

    def is_descendant_of(self, subtype: str, ancestor_type: str) -> bool:
        """
        Check whether ``subtype`` is the same as or a transitive descendant of ``ancestor_type``.
        """
        canonical_ancestor = self.resolve_to_canonical(ancestor_type) or ancestor_type
        canonical_subtype = self.resolve_to_canonical(subtype) or subtype

        if canonical_ancestor == canonical_subtype:
            return True

        # Check primitive subtypes
        subtype_metadata = self._type_metadata.get(canonical_subtype, {})
        if subtype_metadata.get('is_primitive_subtype') and subtype_metadata.get('base_type') == canonical_ancestor:
            return True

        visited: Set[str] = set()
        stack: List[str] = list(self.get_type_hierarchy(canonical_ancestor))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            if current == canonical_subtype:
                return True
            stack.extend(self._type_hierarchies.get(current, set()))

        if self._structure_loader and canonical_ancestor not in self._type_hierarchies:
            return self._structure_loader.is_subtype_of(canonical_subtype, canonical_ancestor)

        return False

    def get_all_type_names(self) -> List[str]:
        """
        Get all registered type names

        Returns:
            List of all type names
        """
        type_names = set(self._type_validators.keys())
        type_names.update(self._type_aliases.keys())
        return sorted(type_names)

    def get_primitive_types(self) -> List[str]:
        """Get all primitive type names"""
        return [name for name, metadata in self._type_metadata.items()
                if metadata.get('is_primitive', False)]

    def get_complex_types(self) -> List[str]:
        """Get all complex type names"""
        return [name for name, metadata in self._type_metadata.items()
                if metadata.get('is_complex', False)]

    def get_resource_types(self) -> List[str]:
        """Get all resource type names"""
        return [name for name, metadata in self._type_metadata.items()
                if metadata.get('is_resource', False)]

    def validate_type_expression(self, expression: str) -> bool:
        """
        Validate a type expression (for complex type expressions)

        Args:
            expression: Type expression to validate

        Returns:
            True if expression is valid
        """
        # Simple validation - just check if it's a known type
        # Could be extended for complex expressions like "Collection<Patient>"
        return self.is_registered_type(expression)

    def load_structure_definitions(self, definitions_path: Path) -> None:
        """
        Load FHIR R4 StructureDefinitions and populate registry.

        Args:
            definitions_path: Path to directory containing FHIR R4 definition files
        """
        from .structure_loader import StructureDefinitionLoader

        self._structure_loader = StructureDefinitionLoader(definitions_path)
        self._structure_loader.load_all_definitions()

        # Extract and store hierarchies
        self._type_hierarchies_extended = self._structure_loader.extract_type_hierarchies()
        self._backbone_elements = self._structure_loader.extract_backbone_elements()
        self._profile_constraints = self._structure_loader.extract_profile_constraints()
        self._element_definitions = self._structure_loader.extract_element_definitions()

        # Merge with existing hierarchies
        for parent, children in self._type_hierarchies_extended.items():
            if parent in self._type_hierarchies:
                self._type_hierarchies[parent].update(children)
            else:
                self._type_hierarchies[parent] = children

        self.logger.info(f"Loaded {len(self._element_definitions)} element definitions from StructureDefinitions")

    def is_backbone_element(self, path: str) -> bool:
        """
        Check if path represents a BackboneElement.

        Args:
            path: Element path (e.g., 'Patient.contact')

        Returns:
            True if path is a BackboneElement
        """
        return path in self._backbone_elements

    def get_profile_base_type(self, profile_name: str) -> Optional[str]:
        """
        Get base type for a profile (e.g., Age -> Quantity).

        Args:
            profile_name: Profile name

        Returns:
            Base type name, or None if not found
        """
        if profile_name in self._profile_constraints:
            return self._profile_constraints[profile_name].get('base')
        return None

    def is_array_element(self, resource_type: str, element_path: str) -> bool:
        """
        Check if element has array cardinality (max = '*').

        Critical for path navigation SQL generation:
        - Array elements require UNNEST(...) in SQL
        - Single-value elements use direct json_extract_string(...)

        Args:
            resource_type: FHIR resource type (e.g., 'Patient')
            element_path: Element name (e.g., 'name' or 'name.given')

        Returns:
            True if element is an array (cardinality 0..* or 1..*)

        Example:
            >>> registry.is_array_element('Patient', 'name')
            True  # Patient.name is 0..*
            >>> registry.is_array_element('Patient', 'birthDate')
            False  # Patient.birthDate is 0..1
        """
        full_path = f"{resource_type}.{element_path}"
        if full_path in self._element_definitions:
            return self._element_definitions[full_path]['is_array']

        # Handle nested paths (e.g., 'name.given' -> need to check HumanName.given)
        if '.' in element_path:
            parts = element_path.split('.')
            # Try to resolve the intermediate type
            first_element = parts[0]
            intermediate_type = self.get_element_type(resource_type, first_element)
            if intermediate_type and len(parts) > 1:
                # Recursively check the nested element
                remaining_path = '.'.join(parts[1:])
                return self.is_array_element(intermediate_type, remaining_path)

        return False

    def get_element_cardinality(self, resource_type: str, element_path: str) -> Optional[str]:
        """
        Get cardinality string for an element.

        Args:
            resource_type: FHIR resource type (e.g., 'Patient')
            element_path: Element name (e.g., 'name')

        Returns:
            Cardinality string (e.g., '0..1', '0..*', '1..1'), or None if not found

        Example:
            >>> registry.get_element_cardinality('Patient', 'name')
            '0..*'
            >>> registry.get_element_cardinality('Patient', 'birthDate')
            '0..1'
        """
        full_path = f"{resource_type}.{element_path}"
        if full_path in self._element_definitions:
            return self._element_definitions[full_path]['cardinality']
        return None

    def get_element_type(self, resource_type: str, element_path: str) -> Optional[str]:
        """
        Get the type of an element.

        Useful for resolving nested paths (e.g., Patient.name -> HumanName).

        Args:
            resource_type: FHIR resource type (e.g., 'Patient')
            element_path: Element name (e.g., 'name')

        Returns:
            Element type (e.g., 'HumanName', 'date'), or None if not found

        Example:
            >>> registry.get_element_type('Patient', 'name')
            'HumanName'
            >>> registry.get_element_type('HumanName', 'given')
            'string'
        """
        if not resource_type or not element_path:
            return None

        current_type = self.get_canonical_name(resource_type)
        if not current_type:
            return None

        parts = element_path.split(".")
        for part in parts:
            candidate = part.strip().strip('`')
            if not candidate:
                return None

            direct_key = f"{current_type}.{candidate}"
            choice_key = f"{current_type}.{candidate}[x]" if not candidate.endswith("[x]") else f"{current_type}.{candidate}"

            element_info = None
            if direct_key in self._element_definitions:
                element_info = self._element_definitions[direct_key]
            elif choice_key in self._element_definitions:
                element_info = self._element_definitions[choice_key]

            if not element_info:
                matched_variant = False
                for split_index in range(len(candidate) - 1, 0, -1):
                    base = candidate[:split_index]
                    suffix = candidate[split_index:]
                    if not base or not suffix:
                        continue

                    choice_lookup = f"{current_type}.{base}[x]"
                    if choice_lookup not in self._element_definitions:
                        continue

                    variants = resolve_polymorphic_property(base) or []
                    if not any(candidate.lower() == variant.lower() for variant in variants):
                        continue

                    canonical_suffix = self.resolve_to_canonical(suffix) or suffix
                    current_type = self.get_canonical_name(canonical_suffix) or canonical_suffix
                    matched_variant = True
                    break

                if matched_variant:
                    continue

                return None

            next_type = element_info.get('type')
            if not next_type:
                return None

            current_type = self.get_canonical_name(next_type)
            if not current_type:
                current_type = next_type

        return current_type

    def get_element_names(self, resource_type: str) -> List[str]:
        """
        Get the direct child element names available on a resource or complex type.

        Args:
            resource_type: FHIR resource or complex type name (e.g., 'Patient', 'HumanName')

        Returns:
            Sorted list of element names that can be accessed from the specified type.
        """
        if not resource_type:
            return []

        prefix = f"{resource_type}."
        candidates: Set[str] = set()

        for element_path in self._element_definitions.keys():
            if not element_path.startswith(prefix):
                continue

            remainder = element_path[len(prefix):]
            if not remainder:
                continue

            child_name = remainder.split(".", 1)[0]
            if child_name:
                candidates.add(child_name)

        return sorted(candidates)

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the type registry

        Returns:
            Registry statistics
        """
        return {
            'total_types': len(self._type_validators),
            'primitive_types': len(self.get_primitive_types()),
            'complex_types': len(self.get_complex_types()),
            'resource_types': len(self.get_resource_types()),
            'aliases': len(self._type_aliases),
            'hierarchies': len(self._type_hierarchies),
            'element_definitions': len(self._element_definitions),
            'backbone_elements': len(self._backbone_elements),
            'profile_constraints': len(self._profile_constraints)
        }


# Global type registry instance
_global_registry: Optional[TypeRegistry] = None


def get_type_registry() -> TypeRegistry:
    """
    Get the global type registry instance

    Returns:
        Global TypeRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = TypeRegistry()
    return _global_registry


def register_global_type(
    type_name: str,
    validator: FHIRTypeValidator,
    metadata: Optional[Dict[str, Any]] = None,
    aliases: Optional[List[str]] = None
) -> None:
    """
    Register a type in the global registry

    Args:
        type_name: Name of the type to register
        validator: Type validator instance
        metadata: Additional type metadata
        aliases: Alternative names for the type
    """
    registry = get_type_registry()
    registry.register_type(type_name, validator, metadata, aliases)


def is_valid_type(value: Any, type_name: str) -> bool:
    """
    Check if a value is valid for a type using global registry

    Args:
        value: Value to check
        type_name: Type name

    Returns:
        True if value is valid for the type
    """
    registry = get_type_registry()
    return registry.is_compatible_type(value, type_name)


def convert_to_type(value: Any, type_name: str) -> Any:
    """
    Convert a value to a type using global registry

    Args:
        value: Value to convert
        type_name: Target type name

    Returns:
        Converted value

    Raises:
        ValueError: If conversion is not possible
    """
    registry = get_type_registry()
    return registry.convert_value(value, type_name)
