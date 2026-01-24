import pytest
from fhir4ds.fhirpath import FHIRPathParser
from fhir4ds.sql import SQLGenerator

@pytest.mark.integration
class TestParserGeneratorIntegration:

    def test_fhirpath_to_sql_workflow(self):
        """Test complete workflow from FHIRPath parsing to SQL generation."""
        # Parse FHIRPath expression
        parser = FHIRPathParser(database_type="duckdb")
        parsed = parser.parse("Patient.name.family")

        assert parsed.is_valid()

        # Generate SQL from parsed expression
        generator = SQLGenerator(dialect="duckdb")
        view_definition = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"path": "name.family", "name": "family"}
                    ]
                }
            ]
        }
        sql = generator.generate_sql(view_definition)

        assert sql is not None
        assert len(sql) > 0
        assert "Patient" in sql

    def test_multi_database_consistency(self):
        """Test that both parser and generator work consistently across databases."""
        expression = "Patient.name.family"

        # Test DuckDB path
        duckdb_parser = FHIRPathParser(database_type="duckdb")
        duckdb_generator = SQLGenerator(dialect="duckdb")

        duckdb_parsed = duckdb_parser.parse(expression)
        view_definition = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"path": "name.family", "name": "family"}
                    ]
                }
            ]
        }
        duckdb_sql = duckdb_generator.generate_sql(view_definition)

        # Test PostgreSQL path
        postgresql_parser = FHIRPathParser(database_type="postgresql")
        postgresql_generator = SQLGenerator(dialect="postgresql")

        postgresql_parsed = postgresql_parser.parse(expression)
        postgresql_sql = postgresql_generator.generate_sql(view_definition)

        # Both should parse successfully
        assert duckdb_parsed.is_valid()
        assert postgresql_parsed.is_valid()

        # Both should generate valid SQL
        assert duckdb_sql is not None
        assert postgresql_sql is not None

        # SQL should be different for different databases
        assert duckdb_sql != postgresql_sql

    def test_complex_expression_workflow(self):
        """Test workflow with complex FHIRPath expressions."""
        parser = FHIRPathParser(database_type="duckdb")
        generator = SQLGenerator(dialect="duckdb")

        # Test expression with function
        expression = "Patient.name.where(family.exists()).first()"
        parsed = parser.parse(expression)
        assert parsed.is_valid()

        view_definition = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"path": "name.where(family.exists()).first()", "name": "name"}
                    ]
                }
            ]
        }
        sql = generator.generate_sql(view_definition)
        assert sql is not None
        assert "WHERE" in sql.upper()

    def test_error_propagation(self):
        """Test that errors propagate correctly through the workflow."""
        parser = FHIRPathParser()
        generator = SQLGenerator(dialect="duckdb")

        # Test parser error propagation
        with pytest.raises(Exception):  # Should raise FHIRPathParseError
            parser.parse("")

        # Test generator error propagation
        with pytest.raises(Exception):  # Should raise SQLGenerationError
            generator.generate_sql({})

    @pytest.mark.parametrize("database_config", [
        ("duckdb", "duckdb"),
        ("postgresql", "postgresql")
    ])
    def test_end_to_end_consistency(self, database_config):
        """Test end-to-end consistency across database configurations."""
        parser_db, generator_dialect = database_config

        parser = FHIRPathParser(database_type=parser_db)
        generator = SQLGenerator(dialect=generator_dialect)

        expression = "Patient.birthDate"

        # Parse expression
        parsed = parser.parse(expression)
        assert parsed.is_valid()

        # Generate SQL
        view_definition = {
            "resource": "Patient",
            "select": [
                {
                    "column": [
                        {"path": "birthDate", "name": "birthDate"}
                    ]
                }
            ]
        }
        sql = generator.generate_sql(view_definition)
        assert sql is not None
        assert len(sql) > 0

        # Verify consistency between parser and generator database settings
        assert parser.database_type == generator.dialect

    def test_statistics_integration(self):
        """Test that statistics are tracked across integrated operations."""
        parser = FHIRPathParser()
        generator = SQLGenerator(dialect="duckdb")

        # Initial state
        initial_parser_stats = parser.get_statistics()
        initial_generator_stats = generator.get_statistics()

        assert initial_parser_stats["parse_count"] == 0
        assert initial_generator_stats["generation_count"] == 0

        # Perform integrated operations
        expressions = ["Patient.name", "Patient.birthDate", "Patient.gender"]

        for expr in expressions:
            parser.parse(expr)
            view_definition = {
                "resource": "Patient",
                "select": [
                    {
                        "column": [
                            {"path": expr.split('.')[1], "name": expr.split('.')[1]}
                        ]
                    }
                ]
            }
            generator.generate_sql(view_definition)

        # Verify statistics
        final_parser_stats = parser.get_statistics()
        final_generator_stats = generator.get_statistics()

        assert final_parser_stats["parse_count"] == len(expressions)
        assert final_generator_stats["generation_count"] == len(expressions)

    def test_function_integration_across_databases(self):
        """Test that FHIRPath functions work consistently across databases."""
        expressions_with_functions = [
            "Patient.name.first()",
            "Patient.telecom.where(system='email')",
            "Patient.name.where(family.exists())"
        ]

        for expr in expressions_with_functions:
            # Test DuckDB
            duckdb_parser = FHIRPathParser(database_type="duckdb")
            duckdb_generator = SQLGenerator(dialect="duckdb")

            duckdb_parsed = duckdb_parser.parse(expr)
            view_definition = {
                "resource": "Patient",
                "select": [
                    {
                        "column": [
                            {"path": expr.split('.')[1], "name": expr.split('.')[1]}
                        ]
                    }
                ]
            }
            duckdb_sql = duckdb_generator.generate_sql(view_definition)

            assert duckdb_parsed.is_valid()
            assert duckdb_sql is not None

            # Test PostgreSQL
            postgresql_parser = FHIRPathParser(database_type="postgresql")
            postgresql_generator = SQLGenerator(dialect="postgresql")

            postgresql_parsed = postgresql_parser.parse(expr)
            postgresql_sql = postgresql_generator.generate_sql(view_definition)

            assert postgresql_parsed.is_valid()
            assert postgresql_sql is not None

            # Functions should be detected consistently
            assert duckdb_parsed.get_functions() == postgresql_parsed.get_functions()

@pytest.mark.integration
class TestComplexFhirpathExpressions:

    @pytest.mark.parametrize("expression", [
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
    ])
    def test_complex_expressions_duckdb(self, expression):
        parser = FHIRPathParser(database_type="duckdb")
        generator = SQLGenerator(dialect="duckdb")
        
        parsed = parser.parse(expression)
        assert parsed.is_valid(), f"DuckDB parsing failed for: {expression}"
        
        resource = expression.split('.')[0]
        path = '.'.join(expression.split('.')[1:])
        view_definition = {
            "resource": resource,
            "select": [
                {
                    "column": [
                        {"path": path, "name": "result"}
                    ]
                }
            ]
        }
        sql = generator.generate_sql(view_definition)
        assert sql is not None and len(sql) > 0, f"DuckDB SQL generation failed for: {expression}"

    @pytest.mark.parametrize("expression", [
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
    ])
    def test_complex_expressions_postgresql(self, expression):
        parser = FHIRPathParser(database_type="postgresql")
        generator = SQLGenerator(dialect="postgresql")

        parsed = parser.parse(expression)
        assert parsed.is_valid(), f"PostgreSQL parsing failed for: {expression}"

        resource = expression.split('.')[0]
        path = '.'.join(expression.split('.')[1:])
        view_definition = {
            "resource": resource,
            "select": [
                {
                    "column": [
                        {"path": path, "name": "result"}
                    ]
                }
            ]
        }
        sql = generator.generate_sql(view_definition)
        assert sql is not None and len(sql) > 0, f"PostgreSQL SQL generation failed for: {expression}"