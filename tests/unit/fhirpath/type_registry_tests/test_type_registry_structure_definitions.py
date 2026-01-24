"""
Integration tests for TypeRegistry with StructureDefinition support

Tests the integration of StructureDefinition loader with TypeRegistry.
"""

import pytest
from pathlib import Path

from fhir4ds.fhirpath.types.type_registry import TypeRegistry, get_type_registry


@pytest.fixture
def registry_with_definitions():
    """Create a TypeRegistry with StructureDefinitions loaded"""
    # Get the global registry (which auto-loads definitions)
    return get_type_registry()


def test_type_registry_hierarchy_queries(registry_with_definitions):
    """Test TypeRegistry hierarchy queries with StructureDefinitions"""
    registry = registry_with_definitions

    # Check if definitions were loaded
    stats = registry.get_registry_stats()
    if stats['element_definitions'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    # Test direct hierarchy
    assert registry.is_subtype_of('Patient', 'DomainResource'), \
        "Patient should be subtype of DomainResource"

    # Test transitive hierarchy
    assert registry.is_descendant_of('Patient', 'Resource'), \
        "Patient should be subtype of Resource (transitive)"

    # Test non-related types
    assert not registry.is_descendant_of('Patient', 'Observation'), \
        "Patient should not be subtype of Observation"


def test_backbone_element_recognition(registry_with_definitions):
    """Test BackboneElement recognition"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()
    if stats['backbone_elements'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    assert registry.is_backbone_element('Patient.contact'), \
        "Patient.contact should be a BackboneElement"
    assert registry.is_backbone_element('Bundle.entry'), \
        "Bundle.entry should be a BackboneElement"
    assert not registry.is_backbone_element('Patient.name'), \
        "Patient.name should not be a BackboneElement"


def test_profile_base_type_queries(registry_with_definitions):
    """Test profile base type queries"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()
    if stats['profile_constraints'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    # Age might not be a standard profile in R4, but we should have some profiles
    assert stats['profile_constraints'] > 0, "Should have loaded some profiles"


def test_element_cardinality_queries(registry_with_definitions):
    """Test TypeRegistry element cardinality query methods"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()
    if stats['element_definitions'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    # Test array detection
    assert registry.is_array_element('Patient', 'name') == True, \
        "Patient.name should be an array"
    assert registry.is_array_element('Patient', 'telecom') == True, \
        "Patient.telecom should be an array"
    assert registry.is_array_element('Patient', 'birthDate') == False, \
        "Patient.birthDate should not be an array"

    # Test cardinality retrieval
    assert registry.get_element_cardinality('Patient', 'name') == '0..*', \
        "Patient.name cardinality should be 0..*"
    assert registry.get_element_cardinality('Patient', 'birthDate') == '0..1', \
        "Patient.birthDate cardinality should be 0..1"

    # Test type resolution
    assert registry.get_element_type('Patient', 'name') == 'HumanName', \
        "Patient.name type should be HumanName"
    assert registry.get_element_type('Patient', 'birthDate') == 'date', \
        "Patient.birthDate type should be date"


def test_nested_path_cardinality(registry_with_definitions):
    """Test cardinality detection for nested paths like name.given"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()
    if stats['element_definitions'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    # Test nested array element (Patient.name.given)
    # This requires resolving Patient.name -> HumanName, then HumanName.given
    assert registry.is_array_element('Patient', 'name.given'), \
        "Patient.name.given should be detected as array (nested path)"

    # Test nested single element (Patient.name.family)
    assert not registry.is_array_element('Patient', 'name.family'), \
        "Patient.name.family should not be an array (nested path)"


def test_registry_stats_with_definitions(registry_with_definitions):
    """Test registry statistics include StructureDefinition data"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()

    # Check that stats include new fields
    assert 'element_definitions' in stats, "Stats should include element_definitions"
    assert 'backbone_elements' in stats, "Stats should include backbone_elements"
    assert 'profile_constraints' in stats, "Stats should include profile_constraints"

    # If definitions loaded, counts should be > 0
    if stats['element_definitions'] > 0:
        assert stats['element_definitions'] > 100, "Should have many element definitions"
        assert stats['hierarchies'] > 0, "Should have type hierarchies"


def test_humanname_element_types(registry_with_definitions):
    """Test HumanName element type resolution"""
    registry = registry_with_definitions

    stats = registry.get_registry_stats()
    if stats['element_definitions'] == 0:
        pytest.skip("StructureDefinitions not loaded")

    # Test HumanName.given
    assert registry.get_element_type('HumanName', 'given') == 'string', \
        "HumanName.given should be string type"
    assert registry.is_array_element('HumanName', 'given'), \
        "HumanName.given should be an array"
    assert registry.get_element_cardinality('HumanName', 'given') == '0..*', \
        "HumanName.given should have cardinality 0..*"

    # Test HumanName.family
    assert registry.get_element_type('HumanName', 'family') == 'string', \
        "HumanName.family should be string type"
    assert not registry.is_array_element('HumanName', 'family'), \
        "HumanName.family should not be an array"
    assert registry.get_element_cardinality('HumanName', 'family') == '0..1', \
        "HumanName.family should have cardinality 0..1"
