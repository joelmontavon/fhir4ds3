import json
import pytest

from fhir4ds.fhirpath.exceptions import FHIRPathExecutionError


def _sorted_results(results):
    return sorted(results, key=lambda row: (row[0], row[1]))


class TestDuckDBScalarExecution:
    """Validate scalar FHIRPath execution on DuckDB."""

    def test_birthdate_scalar_results(self, duckdb_executor, patient_records):
        expected = _sorted_results(
            (int(record["id"]), record["birthDate"]) for record in patient_records
        )
        actual = _sorted_results(duckdb_executor.execute("Patient.birthDate"))
        assert actual == expected

    def test_gender_scalar_results(self, duckdb_executor, patient_records):
        expected = _sorted_results(
            (int(record["id"]), record["gender"]) for record in patient_records
        )
        actual = _sorted_results(duckdb_executor.execute("Patient.gender"))
        assert actual == expected

    def test_active_boolean_results(self, duckdb_executor, patient_records):
        expected = _sorted_results(
            (
                int(record["id"]),
                "true" if record["active"] else "false",
            )
            for record in patient_records
        )
        actual = _sorted_results(duckdb_executor.execute("Patient.active"))
        assert actual == expected


class TestDuckDBErrorHandling:
    """Ensure executor provides descriptive errors."""

    def test_empty_expression_raises(self, duckdb_executor):
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            duckdb_executor.execute("  ")
        assert excinfo.value.stage == "validate"

    def test_invalid_syntax_raises(self, duckdb_executor):
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            duckdb_executor.execute("Patient..name")
        assert excinfo.value.stage == "parse"

    def test_unknown_identifier_returns_nulls(self, duckdb_executor, patient_records):
        results = duckdb_executor.execute("Patient.nonexistentField")
        assert len(results) == len(patient_records)
        assert all(row[1] is None for row in results)


class TestPostgreSQLIntegration:
    """Verify PostgreSQL executor mirrors DuckDB behaviour via SQL capture."""

    def test_scalar_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.birthDate"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression
        assert "SELECT" in executed_sql[-1][1]

    def test_sql_contains_with_clause(self, postgresql_executor):
        executor_wrapper, executed_sql = postgresql_executor
        executor_wrapper.execute("Patient.gender")
        _, sql = executed_sql[-1]
        assert "WITH" in sql
        assert "SELECT *" in sql

    def test_execute_with_details_provides_timings(
        self,
        postgresql_executor,
    ):
        executor_wrapper, _ = postgresql_executor
        details = executor_wrapper.execute_with_details("Patient.birthDate")
        timings = details["timings_ms"]
        assert timings["parse"] >= 0
        assert timings["execute"] >= 0

    def test_boolean_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.active"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_array_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.name"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_identifier_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.identifier"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_telecom_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.telecom"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_address_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.address"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_address_line_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.address.line"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression

    def test_nested_array_results_match_duckdb(
        self,
        duckdb_executor,
        postgresql_executor,
    ):
        executor_wrapper, executed_sql = postgresql_executor
        expression = "Patient.name.given"
        pg_results = _sorted_results(executor_wrapper.execute(expression))
        duckdb_results = _sorted_results(duckdb_executor.execute(expression))
        assert pg_results == duckdb_results
        assert executed_sql[-1][0] == expression


class TestDuckDBArrayExecution:
    """Validate array navigation results on DuckDB."""

    def _flatten(self, iterable):
        return [item for sublist in iterable for item in sublist]

    def test_patient_name_results(self, duckdb_executor, patient_records):
        expected_count = sum(len(record.get("name", [])) for record in patient_records)
        results = _sorted_results(duckdb_executor.execute("Patient.name"))

        assert len(results) == expected_count
        assert {row[0] for row in results} == {
            int(record["id"]) for record in patient_records
        }

        sample = results[:3]
        for _, value in sample:
            if isinstance(value, str):
                parsed = json.loads(value)
            else:
                parsed = value
            assert "family" in parsed
            assert "given" in parsed

    def test_patient_name_given_results(self, duckdb_executor, patient_records):
        expected_count = sum(
            len(name.get("given", []))
            for record in patient_records
            for name in record.get("name", [])
        )
        results = duckdb_executor.execute("Patient.name.given")
        assert len(results) == expected_count
        assert all(isinstance(row[1], str) for row in results)

    def test_patient_name_family_results(self, duckdb_executor, patient_records):
        expected = sorted(
            (int(record["id"]), name.get("family"))
            for record in patient_records
            for name in record.get("name", [])
        )
        results = sorted(duckdb_executor.execute("Patient.name.family"))
        assert results == expected

    def test_patient_identifier_results(self, duckdb_executor, patient_records):
        expected_count = sum(len(record.get("identifier", [])) for record in patient_records)
        results = duckdb_executor.execute("Patient.identifier")
        assert len(results) == expected_count

    def test_patient_telecom_results(self, duckdb_executor, patient_records):
        expected_count = sum(len(record.get("telecom", [])) for record in patient_records)
        results = duckdb_executor.execute("Patient.telecom")
        assert len(results) == expected_count

    def test_patient_address_results(self, duckdb_executor, patient_records):
        expected_count = sum(len(record.get("address", [])) for record in patient_records)
        results = duckdb_executor.execute("Patient.address")
        assert len(results) == expected_count

    def test_patient_address_line_results(self, duckdb_executor, patient_records):
        expected_count = sum(
            len(address.get("line", []))
            for record in patient_records
            for address in record.get("address", [])
        )
        results = duckdb_executor.execute("Patient.address.line")
        assert len(results) == expected_count


class TestPerformanceMetrics:
    """Lightweight performance validation using executor timings."""

    def test_generation_under_ten_ms(self, duckdb_executor):
        details = duckdb_executor.execute_with_details("Patient.birthDate")
        assert details["timings_ms"]["translate"] < 10.0
        assert details["timings_ms"]["assemble"] < 10.0

    def test_execution_under_half_second(self, duckdb_executor):
        details = duckdb_executor.execute_with_details("Patient.birthDate")
        assert details["timings_ms"]["execute"] < 500.0
