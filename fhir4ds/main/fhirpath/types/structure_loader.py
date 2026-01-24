"""
FHIR R4 StructureDefinition Loader

This module loads and parses official FHIR R4 StructureDefinition files to extract type metadata.

Extracts:
- Resource type hierarchies (base type relationships)
- BackboneElement structural definitions
- Profile constraints and derivations
- Element definitions with cardinality metadata

StructureDefinitions Source:
- FHIR R4 Official Definitions Package
- URL: https://hl7.org/fhir/R4/definitions.json.zip
- Version: 4.0.1
- License: CC0 (public domain)

Usage:
    loader = StructureDefinitionLoader(definitions_path)
    loader.load_all_definitions()
    hierarchies = loader.extract_type_hierarchies()
    elements = loader.extract_element_definitions()
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


class StructureDefinitionLoader:
    """
    Loads and parses FHIR R4 StructureDefinition files to extract type metadata.

    Extracts:
    - Resource type hierarchies (base type relationships)
    - BackboneElement structural definitions
    - Profile constraints and derivations
    - Element definitions with cardinality metadata
    """

    def __init__(self, definitions_path: Path):
        """
        Initialize loader with path to FHIR definitions directory.

        Args:
            definitions_path: Path to directory containing FHIR R4 definition files
        """
        self.definitions_path = Path(definitions_path)
        self._definitions_cache: Dict[str, Dict[str, Any]] = {}
        self._base_type_map: Dict[str, str] = {}  # type_name -> base_type_url
        self._type_hierarchies: Dict[str, Set[str]] = {}  # parent -> {children}

    def load_all_definitions(self) -> None:
        """
        Load all StructureDefinition files from definitions directory.

        Processes:
        - profiles-resources.json (resource StructureDefinitions)
        - profiles-types.json (datatype StructureDefinitions)
        - profiles-others.json (additional profiles)
        """
        logger.info(f"Loading FHIR R4 StructureDefinitions from {self.definitions_path}")

        # Load resource definitions
        resources_file = self.definitions_path / "profiles-resources.json"
        if resources_file.exists():
            self._load_bundle_file(resources_file)
            logger.debug(f"Loaded resource definitions from {resources_file}")

        # Load type definitions
        types_file = self.definitions_path / "profiles-types.json"
        if types_file.exists():
            self._load_bundle_file(types_file)
            logger.debug(f"Loaded type definitions from {types_file}")

        # Load other profiles
        others_file = self.definitions_path / "profiles-others.json"
        if others_file.exists():
            self._load_bundle_file(others_file)
            logger.debug(f"Loaded other profile definitions from {others_file}")

        logger.info(f"Loaded {len(self._definitions_cache)} StructureDefinitions")

    def _load_bundle_file(self, file_path: Path) -> None:
        """
        Load a FHIR Bundle file containing StructureDefinitions.

        Args:
            file_path: Path to JSON bundle file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                bundle = json.load(f)

            if bundle.get('resourceType') != 'Bundle':
                logger.warning(f"File {file_path} is not a Bundle resource")
                return

            # Process each entry in the bundle
            for entry in bundle.get('entry', []):
                resource = entry.get('resource', {})
                if resource.get('resourceType') == 'StructureDefinition':
                    self._process_structure_definition(resource)

        except Exception as e:
            logger.error(f"Error loading bundle file {file_path}: {e}")
            raise

    def _process_structure_definition(self, sd_json: Dict[str, Any]) -> None:
        """
        Process a single StructureDefinition JSON object.

        Args:
            sd_json: StructureDefinition resource JSON
        """
        parsed = self._parse_structure_definition(sd_json)
        sd_id = parsed['id']
        self._definitions_cache[sd_id] = parsed

        # Build base type map for hierarchy queries
        if parsed['base']:
            self._base_type_map[parsed['name']] = parsed['base']

    def _parse_structure_definition(self, sd_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single StructureDefinition JSON object.

        Args:
            sd_json: StructureDefinition resource JSON

        Returns:
            Parsed StructureDefinition with key metadata
        """
        return {
            'id': sd_json.get('id'),
            'url': sd_json.get('url'),
            'name': sd_json.get('name'),
            'kind': sd_json.get('kind'),  # 'resource', 'complex-type', 'primitive-type'
            'abstract': sd_json.get('abstract', False),
            'base': sd_json.get('baseDefinition'),  # Inheritance link (URL)
            'derivation': sd_json.get('derivation'),  # 'specialization', 'constraint'
            'type': sd_json.get('type'),
            'elements': sd_json.get('snapshot', {}).get('element', [])
        }

    def _parse_element_definition(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse element definition from StructureDefinition to extract cardinality.

        Args:
            element: Element definition from StructureDefinition.snapshot.element

        Returns:
            Parsed element with cardinality metadata

        Example element from FHIR spec:
            {
                "path": "Patient.name",
                "min": 0,
                "max": "*",
                "type": [{"code": "HumanName"}]
            }
        """
        min_card = element.get('min', 0)
        max_card = element.get('max', '1')

        # Extract type code (handle multiple types)
        types = element.get('type', [])
        type_code = types[0].get('code') if types else None

        return {
            'path': element.get('path'),
            'type': type_code,
            'min': min_card,
            'max': max_card,
            'cardinality': f"{min_card}..{max_card}",
            'is_array': max_card == '*',
            'is_required': min_card > 0
        }

    def extract_type_hierarchies(self) -> Dict[str, Set[str]]:
        """
        Extract resource type inheritance hierarchies.

        Returns:
            Dict mapping parent type to set of child types.
            Example: {'Resource': {'DomainResource', 'Bundle'},
                     'DomainResource': {'Patient', 'Observation', ...}}
        """
        hierarchies: Dict[str, Set[str]] = {}

        for sd_id, sd in self._definitions_cache.items():
            if not sd['base']:
                continue

            # Extract parent type name from base definition URL
            # Example: http://hl7.org/fhir/StructureDefinition/DomainResource -> DomainResource
            base_url = sd['base']
            parent_type = base_url.split('/')[-1]
            child_type = sd['name']

            if parent_type not in hierarchies:
                hierarchies[parent_type] = set()
            hierarchies[parent_type].add(child_type)

        self._type_hierarchies = hierarchies
        logger.info(f"Extracted {len(hierarchies)} type hierarchy relationships")
        return hierarchies

    def extract_backbone_elements(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract BackboneElement structural definitions.

        Returns:
            Dict mapping backbone path to element definition.
            Example: {'Patient.contact': {...}, 'Bundle.entry': {...}}
        """
        backbone_elements: Dict[str, Dict[str, Any]] = {}

        for sd_id, sd in self._definitions_cache.items():
            if sd['kind'] != 'resource':
                continue

            # Look for elements with BackboneElement type
            for element in sd.get('elements', []):
                types = element.get('type', [])
                for type_def in types:
                    if type_def.get('code') == 'BackboneElement':
                        path = element.get('path')
                        backbone_elements[path] = self._parse_element_definition(element)
                        logger.debug(f"Found BackboneElement: {path}")

        logger.info(f"Extracted {len(backbone_elements)} BackboneElement definitions")
        return backbone_elements

    def extract_profile_constraints(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract profile definitions and constraints.

        Returns:
            Dict mapping profile name to constraint definition.
            Example: {'Age': {'base': 'Quantity', 'constraints': [...]}}
        """
        profiles: Dict[str, Dict[str, Any]] = {}

        for sd_id, sd in self._definitions_cache.items():
            # Profiles have derivation = 'constraint'
            if sd.get('derivation') == 'constraint' and sd['base']:
                base_url = sd['base']
                base_type = base_url.split('/')[-1]

                profiles[sd['name']] = {
                    'name': sd['name'],
                    'base': base_type,
                    'url': sd['url'],
                    'kind': sd['kind'],
                    'type': sd.get('type')
                }
                logger.debug(f"Found profile: {sd['name']} -> {base_type}")

        logger.info(f"Extracted {len(profiles)} profile definitions")
        return profiles

    def extract_element_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract element definitions with cardinality metadata.

        Returns:
            Dict mapping element path to definition with cardinality.
            Example: {
                'Patient.name': {
                    'type': 'HumanName',
                    'cardinality': '0..*',
                    'is_array': True,
                    'min': 0,
                    'max': '*'
                },
                'Patient.birthDate': {
                    'type': 'date',
                    'cardinality': '0..1',
                    'is_array': False,
                    'min': 0,
                    'max': '1'
                }
            }
        """
        element_defs: Dict[str, Dict[str, Any]] = {}

        for sd_id, sd in self._definitions_cache.items():
            # Process resources and complex types (not primitive types)
            if sd['kind'] not in ('resource', 'complex-type'):
                continue

            # Process all elements in the snapshot
            for element in sd.get('elements', []):
                parsed = self._parse_element_definition(element)
                path = parsed['path']
                element_defs[path] = parsed

        logger.info(f"Extracted {len(element_defs)} element definitions")
        return element_defs

    def get_base_type(self, type_name: str) -> Optional[str]:
        """
        Get the base type for a given type or profile.

        Args:
            type_name: Type name to query

        Returns:
            Base type name, or None if not found
        """
        if type_name not in self._base_type_map:
            return None

        base_url = self._base_type_map[type_name]
        return base_url.split('/')[-1]

    def is_subtype_of(self, child: str, parent: str) -> bool:
        """
        Check if child type inherits from parent type.

        Args:
            child: Child type name
            parent: Parent type name

        Returns:
            True if child inherits from parent (directly or transitively)
        """
        # Direct check
        if parent in self._type_hierarchies:
            if child in self._type_hierarchies[parent]:
                return True

        # Transitive check - walk up the hierarchy
        current = child
        visited = set()
        while current and current not in visited:
            visited.add(current)
            base = self.get_base_type(current)
            if base == parent:
                return True
            current = base

        return False

    def is_array_element(self, resource_type: str, element_path: str) -> bool:
        """
        Check if element has array cardinality (max = '*').

        Args:
            resource_type: FHIR resource type (e.g., 'Patient')
            element_path: Element path (e.g., 'name' or 'name.given')

        Returns:
            True if element is an array (cardinality 0..* or 1..*)
        """
        full_path = f"{resource_type}.{element_path}"

        # Check in definitions cache
        for sd_id, sd in self._definitions_cache.items():
            if sd['name'] != resource_type:
                continue

            for element in sd.get('elements', []):
                if element.get('path') == full_path:
                    max_card = element.get('max', '1')
                    return max_card == '*'

        return False
