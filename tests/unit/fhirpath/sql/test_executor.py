from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from fhir4ds.fhirpath.exceptions import FHIRPathExecutionError
from fhir4ds.fhirpath.sql.executor import FHIRPathExecutor
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.cte import CTE


class _MockParser:
    def __init__(self, ast_object: Any = None, valid: bool = True) -> None:
        self._ast = ast_object or object()
        self._valid = valid

    def parse(self, expression: str, context: Optional[Dict[str, Any]] = None) -> "_ParseResult":
        return _ParseResult(self._ast, self._valid)


@dataclass
class _ParseResult:
    ast: Any
    valid: bool

    def is_valid(self) -> bool:
        return self.valid

    def get_ast(self) -> Any:
        return self.ast


class _MockAdapter:
    def __init__(self, converted_ast: Any = None) -> None:
        self._converted_ast = converted_ast or object()

    def convert(self, enhanced_ast: Any) -> Any:
        assert enhanced_ast is not None
        return self._converted_ast


class _MockTranslator:
    def __init__(
        self,
        fragments: Optional[List[SQLFragment]] = None,
        error: Exception | None = None,
        sql: str = "WITH cte_1 AS (SELECT id FROM resource)\nSELECT * FROM cte_1;",
    ) -> None:
        self._fragments = (
            fragments
            if fragments is not None
            else [SQLFragment(expression="mock_expr", source_table="resource")]
        )
        self._error = error
        self._sql = sql
        self.called_with: List[Any] = []
        # Store fragments for access by executor after translate_to_sql is called
        self.fragments: List[SQLFragment] = []

    def translate(self, ast: Any) -> List[SQLFragment]:
        self.called_with.append(ast)
        if self._error:
            raise self._error
        self.fragments = self._fragments
        return self._fragments

    def translate_to_sql(self, ast: Any) -> str:
        """SP-023-003: New method that combines translation with CTE generation."""
        self.called_with.append(ast)
        if self._error:
            raise self._error
        # Store fragments for backward compatibility diagnostics
        self.fragments = self._fragments
        if not self._fragments:
            raise ValueError("Translation produced no SQL fragments")
        return self._sql


class _MockCTEManager:
    """Mock CTEManager that provides both build_cte_chain and assemble_query methods."""
    def __init__(
        self,
        ctes: Optional[List[CTE]] = None,
        sql: str = "WITH cte_1 AS (SELECT id FROM resource)\nSELECT * FROM cte_1;",
    ) -> None:
        self._ctes = ctes if ctes is not None else [CTE(name="cte_1", query="SELECT id FROM resource")]
        self._sql = sql
        self.build_called_with: List[List[SQLFragment]] = []
        self.assemble_called_with: List[List[CTE]] = []

    def build_cte_chain(self, fragments: List[SQLFragment]) -> List[CTE]:
        self.build_called_with.append(fragments)
        return self._ctes

    def assemble_query(self, ctes: List[CTE]) -> str:
        self.assemble_called_with.append(ctes)
        return self._sql


# Backward compatibility aliases
_MockCTEBuilder = _MockCTEManager
_MockAssembler = _MockCTEManager


class _MockDialect:
    def __init__(self, results: Optional[List[Any]] = None) -> None:
        self._results = results or [(1, "value")]
        self.executed_sql: List[str] = []

    def execute_query(self, sql: str) -> List[Any]:
        self.executed_sql.append(sql)
        return self._results


def _make_executor(
    *,
    parser: Optional[_MockParser] = None,
    adapter: Optional[_MockAdapter] = None,
    translator: Optional[_MockTranslator] = None,
    builder: Optional[_MockCTEManager] = None,
    assembler: Optional[_MockCTEManager] = None,  # Ignored, kept for compatibility
    cte_manager: Optional[_MockCTEManager] = None,
    dialect: Optional[_MockDialect] = None,
) -> tuple[FHIRPathExecutor, _MockDialect, _MockTranslator, _MockCTEManager, _MockCTEManager]:
    mock_dialect = dialect or _MockDialect()
    mock_translator = translator or _MockTranslator()
    # Use cte_manager if provided, else builder if provided, else create new
    mock_manager = cte_manager or builder or _MockCTEManager()
    executor = FHIRPathExecutor(
        dialect=mock_dialect,
        resource_type="Patient",
        parser=parser or _MockParser(),
        adapter=adapter or _MockAdapter(),
        translator=mock_translator,
        cte_manager=mock_manager,
    )
    # Return mock_manager twice for backward compatibility (builder, assembler slots)
    return executor, mock_dialect, mock_translator, mock_manager, mock_manager


class TestFHIRPathExecutor:
    def test_execute_with_details_runs_pipeline(self) -> None:
        executor, dialect, translator, manager, _ = _make_executor()

        details = executor.execute_with_details("Patient.birthDate")

        assert details["results"] == [(1, "value")]
        assert "WITH cte_1" in details["sql"]
        assert "execute" in details["timings_ms"]
        assert dialect.executed_sql == [details["sql"]]
        # SP-023-003: translator.translate_to_sql is called once
        assert len(translator.called_with) == 1
        # SP-023-003: CTEs are built for diagnostics after translate_to_sql
        assert len(manager.build_called_with) == 1
        # SP-023-003: assemble_query is no longer called by executor
        # (CTE assembly is now internal to translator via translate_to_sql)

    def test_execute_returns_results_only(self) -> None:
        executor, _, _, _, _ = _make_executor()
        assert executor.execute("Patient.gender") == [(1, "value")]

    def test_empty_expression_raises_execution_error(self) -> None:
        executor, _, _, _, _ = _make_executor()
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("   ")
        assert excinfo.value.stage == "validate"

    def test_non_string_expression_raises_execution_error(self) -> None:
        executor, _, _, _, _ = _make_executor()
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute(123)  # type: ignore[arg-type]
        assert excinfo.value.stage == "validate"

    def test_constructor_requires_dialect_and_resource_type(self) -> None:
        with pytest.raises(ValueError):
            FHIRPathExecutor(dialect=None, resource_type="Patient")  # type: ignore[arg-type]
        mock_dialect = _MockDialect()
        with pytest.raises(ValueError):
            FHIRPathExecutor(dialect=mock_dialect, resource_type="")

    def test_invalid_parse_result_raises_execution_error(self) -> None:
        parser = _MockParser(valid=False)
        executor, _, _, _, _ = _make_executor(parser=parser)
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")
        assert excinfo.value.stage == "parse"

    def test_translation_error_wrapped_with_context(self) -> None:
        translator_error = ValueError("translator boom")
        executor, _, _, _, _ = _make_executor(translator=_MockTranslator(error=translator_error))

        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")

        assert excinfo.value.stage == "translate"
        assert excinfo.value.original_exception is translator_error

    def test_translation_returns_no_fragments_raises(self) -> None:
        translator = _MockTranslator(fragments=[])
        executor, _, _, _, _ = _make_executor(translator=translator)
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")
        assert excinfo.value.stage == "translate"

    def test_cte_builder_returns_empty_raises(self) -> None:
        manager = _MockCTEManager(ctes=[])
        executor, _, _, _, _ = _make_executor(cte_manager=manager)
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")
        assert excinfo.value.stage == "build"

    def test_execute_stage_propagates_fhirpath_execution_error(self) -> None:
        translator = _MockTranslator(
            error=FHIRPathExecutionError("boom", stage="translate", expression="expr")
        )
        executor, _, _, _, _ = _make_executor(translator=translator)
        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")
        assert excinfo.value.stage == "translate"

    def test_handle_stage_error_rethrows_existing_execution_error(self) -> None:
        executor, _, _, _, _ = _make_executor()
        error = FHIRPathExecutionError("existing", stage="translate", expression="expr")
        with pytest.raises(FHIRPathExecutionError):
            executor._handle_stage_error("translate", "expr", error)

    def test_database_error_is_wrapped_with_context(self) -> None:
        class _FailDialect(_MockDialect):
            def execute_query(self, sql: str) -> List[Any]:
                raise RuntimeError("database unavailable")

        executor, _, _, _, _ = _make_executor(dialect=_FailDialect())

        with pytest.raises(FHIRPathExecutionError) as excinfo:
            executor.execute("Patient.birthDate")

        assert excinfo.value.stage == "execute"
        assert isinstance(excinfo.value.original_exception, RuntimeError)
