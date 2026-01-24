"""
Multi-database consistency tests.

Tests that ensure identical behavior across DuckDB and PostgreSQL.
"""

import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

from fhir4ds.fhirpath.parser import FHIRPathParser

COMPLEX_EXPRESSIONS = [
    "Patient.name.where(use='official').first().family",
    "Patient.telecom.where(system='phone' and use='home').value",
    "Observation.where(status='final' and valueQuantity.value > 5.4).code.coding.first().code",
    "Patient.link.where(type='seealso').other.reference",
    "MedicationRequest.medicationReference.where(display.exists()).display",
    "Condition.where(clinicalStatus.coding.exists(system='http://terminology.hl7.org/CodeSystem/condition-clinical' and code='active')).code.text",
    "Patient.name.select(given.join(', ') + ' ' + family).first()",
    "Encounter.location.where(status='completed').select(location.display + ' (' + period.end + ')').first()",
    "(Observation.valueQuantity.value * 100).toString() + '%'",
    "Patient.deceased.iif(boolean, 'Deceased', 'Alive')",
    "Observation.valueQuantity.value.where(> 50 and < 100)",
    "Patient.birthDate + 10 years",
    "Patient.name.count() > 1",
    "Patient.address.where(city='Pleasanton').postalCode.first()",
    "Observation.code.coding.where(system='http://loinc.org').code.first()",
    "Encounter.participant.where(type.coding.exists(code='PPRF')).individual.display.first()",
    "MedicationRequest.dosageInstruction.timing.repeat.bounds.as(Period).start",
    "Patient.name.family.distinct().count()",
    "Observation.component.where(code.text='Systolic blood pressure').valueQuantity.value.first()",
    "Patient.communication.where(language.coding.exists(code='en')).preferred.first()",
    "RiskAssessment.prediction.where(probability > 0.5).outcome.text.first()",
    "DiagnosticReport.result.where(display.contains('glucose')).display.first()",
    "Patient.generalPractitioner.first().display + ' (GP)'",
    "Observation.referenceRange.first().text",
    "Procedure.focalDevice.where(action.coding.exists(code='implanted')).manipulated.display.first()",
    "Observation.value.is(Quantity)",
    "Patient.name.where(given.count() > 1).family.first()",
    "Encounter.length.where(unit='min' and value > 30)",
    "AllergyIntolerance.reaction.where(severity='severe').manifestation.text.first()",
    "Patient.maritalStatus.coding.code.first()",
    "CarePlan.activity.detail.description.first()",
    "Immunization.vaccineCode.coding.where(system='http://hl7.org/fhir/sid/cvx').code.first()",
    "Patient.contact.where(relationship.coding.exists(code='C')).name.family.first()",
    "Goal.target.first().dueDate",
    "Claim.item.first().net.value.toString() + ' ' + Claim.item.first().net.currency.toString()",
    "Patient.photo.first().contentType",
    "Device.deviceName.where(type='user-friendly-name').name.first()",
    "Coverage.payor.first().display",
    "Person.link.where(assurance='level4').target.display.first()",
    "RelatedPerson.patient.reference",
    "Specimen.collection.collected.as(dateTime)",
    "ValueSet.compose.include.where(system='http://loinc.org').concept.count()",
    "Measure.library.first()",
    "Location.position.latitude.toString() + ', ' + Location.position.longitude.toString()",
    "Subscription.channel.header.first()",
    "Task.input.where(type.text='patient-id').value.as(string)",
    "Questionnaire.item.where(type='choice' and required=true).text.first()",
    "Appointment.participant.where(actor.display.contains('Smith')).status.first()",
    "Composition.author.first().display",
    "DocumentReference.content.first().attachment.url",
    "List.entry.where(deleted=false).item.display.first()",
    "Schedule.actor.first().display",
    "Slot.schedule.reference",
    "VerificationResult.target.first().reference"
]

def xml_to_dict(element):
    """Converts an XML element to a dictionary."""
    result = {}
    for child in element:
        child_data = xml_to_dict(child)
        if child.tag in result:
            if not isinstance(result[child.tag], list):
                result[child.tag] = [result[child.tag]]
            result[child.tag].append(child_data if child_data else child.text)
        else:
            result[child.tag] = child_data if child_data else child.text
    return result

@pytest.fixture(scope="module")
def sample_fhir_data():
    """Loads sample FHIR data from XML files."""
    data = {}
    data_dir = Path(__file__).parent.parent / "fixtures" / "sample_fhir_data"
    for f in data_dir.glob("*.xml"):
        tree = ET.parse(f)
        root = tree.getroot()
        resource_type = root.tag.replace('{http://hl7.org/fhir}', '')
        data[resource_type] = xml_to_dict(root)
    return data


class TestMultiDatabaseConsistency:
    """Tests for ensuring consistent behavior across database platforms."""

    @pytest.mark.integration
    @pytest.mark.parametrize("expression", COMPLEX_EXPRESSIONS)
    def test_identical_results_across_databases(self, expression, sample_fhir_data):
        """Test that same FHIRPath expression produces identical results across databases."""
        # DuckDB
        duckdb_parser = FHIRPathParser(database_type="duckdb")
        duckdb_engine = FHIRPathEvaluationEngine()
        duckdb_parsed = duckdb_parser.parse(expression)
        duckdb_context = EvaluationContext(sample_fhir_data)
        duckdb_result = duckdb_engine.evaluate(duckdb_parsed.get_ast(), duckdb_context)

        # PostgreSQL
        postgres_parser = FHIRPathParser(database_type="postgresql")
        postgres_engine = FHIRPathEvaluationEngine()
        postgres_parsed = postgres_parser.parse(expression)
        postgres_context = EvaluationContext(sample_fhir_data)
        postgres_result = postgres_engine.evaluate(postgres_parsed.get_ast(), postgres_context)

        assert duckdb_result == postgres_result, f"Results differ for expression: {expression}"

    @pytest.mark.integration
    def test_sql_syntax_differences(self):
        """Test that SQL syntax differences are handled correctly."""
        # TODO: Implement SQL syntax testing
        # This test ensures that database-specific SQL syntax is correctly
        # generated while maintaining identical logical results
        pass

    @pytest.mark.integration
    @pytest.mark.slow
    def test_performance_parity(self):
        """Test that performance characteristics are similar across databases."""
        # TODO: Implement performance parity testing
        # This test would measure query execution times and ensure
        # that performance is comparable across database platforms
        pass