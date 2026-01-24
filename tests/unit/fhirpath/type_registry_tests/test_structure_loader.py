"""
Unit tests for FHIR R4 StructureDefinition Loader

Tests the loading and parsing of official FHIR R4 StructureDefinition files.
"""

import pytest
from pathlib import Path

from fhir4ds.fhirpath.types.structure_loader import StructureDefinitionLoader


@pytest.fixture
def definitions_path():
    """Path to FHIR R4 definitions"""
    return Path(__file__).parent.parent.parent.parent.parent / "fhir4ds" / "fhirpath" / "types" / "fhir_r4_definitions"


@pytest.fixture
def loader(definitions_path):
    """Create a loader instance"""
    if not definitions_path.exists():
        pytest.skip(f"FHIR definitions not found at {definitions_path}")
    loader = StructureDefinitionLoader(definitions_path)
    loader.load_all_definitions()
    return loader


def test_load_fhir_r4_definitions(loader):
    """Test loading official FHIR R4 StructureDefinitions"""
    assert len(loader._definitions_cache) > 100, "Should load many definitions"


def test_extract_resource_hierarchies(loader):
    """Test extracting resource type hierarchies"""
    hierarchies = loader.extract_type_hierarchies()

    assert 'Resource' in hierarchies, "Resource should be in hierarchies"
    assert 'DomainResource' in hierarchies['Resource'], "DomainResource should be child of Resource"
    assert 'Patient' in hierarchies['DomainResource'], "Patient should be child of DomainResource"


def test_extract_backbone_elements(loader):
    """Test extracting BackboneElement definitions"""
    backbones = loader.extract_backbone_elements()

    assert 'Patient.contact' in backbones, "Patient.contact should be a BackboneElement"
    assert 'Bundle.entry' in backbones, "Bundle.entry should be a BackboneElement"


def test_profile_base_type_resolution(loader):
    """Test profile base type resolution"""
    profiles = loader.extract_profile_constraints()

    # Check that we have some profiles loaded
    assert len(profiles) > 0, "Should have loaded some profile definitions"

    # All profiles should have a base type
    for profile_name, profile_data in list(profiles.items())[:5]:
        assert 'base' in profile_data, f"Profile {profile_name} should have a base type"
        assert profile_data['base'], f"Profile {profile_name} base should not be empty"


def test_extract_element_cardinality(loader):
    """Test element cardinality extraction"""
    elements = loader.extract_element_definitions()

    # Test array elements
    assert 'Patient.name' in elements, "Patient.name should be in elements"
    assert elements['Patient.name']['is_array'] == True, "Patient.name should be an array"
    assert elements['Patient.name']['cardinality'] == '0..*', "Patient.name cardinality should be 0..*"

    # Test single-value elements
    assert 'Patient.birthDate' in elements, "Patient.birthDate should be in elements"
    assert elements['Patient.birthDate']['is_array'] == False, "Patient.birthDate should not be an array"
    assert elements['Patient.birthDate']['cardinality'] == '0..1', "Patient.birthDate cardinality should be 0..1"


def test_element_type_resolution(loader):
    """Test element type extraction"""
    elements = loader.extract_element_definitions()

    assert elements['Patient.name']['type'] == 'HumanName', "Patient.name type should be HumanName"
    assert elements['Patient.birthDate']['type'] == 'date', "Patient.birthDate type should be date"


def test_get_base_type(loader):
    """Test getting base type for a type"""
    base = loader.get_base_type('Patient')
    assert base == 'DomainResource', "Patient base type should be DomainResource"


def test_is_subtype_of(loader):
    """Test subtype checking"""
    # Direct hierarchy
    assert loader.is_subtype_of('Patient', 'DomainResource'), "Patient should be subtype of DomainResource"

    # Transitive hierarchy
    assert loader.is_subtype_of('Patient', 'Resource'), "Patient should be subtype of Resource (transitive)"

    # Not related
    assert not loader.is_subtype_of('Patient', 'Observation'), "Patient should not be subtype of Observation"


def test_is_array_element(loader):
    """Test array element detection"""
    assert loader.is_array_element('Patient', 'name'), "Patient.name should be an array"
    assert not loader.is_array_element('Patient', 'birthDate'), "Patient.birthDate should not be an array"


def test_humanname_given_is_array(loader):
    """Test that HumanName.given is correctly identified as an array"""
    elements = loader.extract_element_definitions()

    assert 'HumanName.given' in elements, "HumanName.given should be in elements"
    assert elements['HumanName.given']['is_array'] == True, "HumanName.given should be an array"
    assert elements['HumanName.given']['cardinality'] == '0..*', "HumanName.given cardinality should be 0..*"
    assert elements['HumanName.given']['type'] == 'string', "HumanName.given type should be string"


def test_humanname_family_is_single(loader):
    """Test that HumanName.family is correctly identified as single-value"""
    elements = loader.extract_element_definitions()

    assert 'HumanName.family' in elements, "HumanName.family should be in elements"
    assert elements['HumanName.family']['is_array'] == False, "HumanName.family should not be an array"
    assert elements['HumanName.family']['cardinality'] == '0..1', "HumanName.family cardinality should be 0..1"
    assert elements['HumanName.family']['type'] == 'string', "HumanName.family type should be string"


def test_patient_telecom_is_array(loader):
    """Test that Patient.telecom is correctly identified as an array"""
    elements = loader.extract_element_definitions()

    assert 'Patient.telecom' in elements, "Patient.telecom should be in elements"
    assert elements['Patient.telecom']['is_array'] == True, "Patient.telecom should be an array"
    assert elements['Patient.telecom']['type'] == 'ContactPoint', "Patient.telecom type should be ContactPoint"
