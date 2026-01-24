"""
FHIRPath end-to-end execution pipeline (PEP-004 integration).

The :class:`FHIRPathExecutor` coordinates the unified execution pipeline:

```
FHIRPath expression
    └─▶ Parser (PEP-002)
          └─▶ AST-to-SQL translator (PEP-003/SP-023-003)
                └─▶ Database execution (DuckDB/PostgreSQL)
```

SP-023-004B: The translator now works directly with the parser's EnhancedASTNode
output, eliminating the need for an intermediate AST adapter step. The
EnhancedASTNode.accept() method handles visitor dispatch correctly.

The translator integrates CTE generation internally (SP-023-003),
providing a simplified pipeline where translation produces SQL directly.

This thin orchestration layer keeps business logic within the translator
component while providing a stable API for executing FHIRPath expressions
against population-scale data sets.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fhir4ds.dialects.base import DatabaseDialect
from fhir4ds.fhirpath.exceptions import (
    FHIRPathExecutionError,
    FHIRPathParseError,
    FHIRPathTranslationError,
    FHIRPathValidationError,
)
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.cte import CTE, CTEManager
from fhir4ds.fhirpath.sql.fragments import SQLFragment
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator

logger = logging.getLogger(__name__)


class FHIRPathExecutor:
    """Execute FHIRPath expressions end-to-end using the unified SQL pipeline.

    The executor coordinates every stage of the unified architecture—parser,
    translator, CTE manager, and dialect execution—while keeping the dialect
    boundary thin. Business logic continues to live in PEP-003 and PEP-004
    components; this class orchestrates them and captures diagnostics so
    population-scale workloads remain observable.

    SP-023-004B: The translator now works directly with the parser's
    EnhancedASTNode output. The EnhancedASTNode.accept() method correctly
    dispatches to visitor methods, eliminating the need for AST adapter.

    Parameters
    ----------
    dialect:
        Concrete :class:`DatabaseDialect` used for SQL execution and syntax
        helpers (DuckDB, PostgreSQL, etc.).
    resource_type:
        Logical FHIR resource serving as the population anchor (for example
        ``Patient`` or ``Observation``). The translator relies on this value to
        resolve base tables and joins.
    parser, translator, cte_manager:
        Optional overrides that enable dependency injection during testing or
        advanced customization. Defaults are created automatically when omitted.

    Example
    -------
    >>> from fhir4ds.dialects.duckdb import DuckDBDialect
    >>> executor = FHIRPathExecutor(DuckDBDialect(), resource_type="Patient")
    >>> report = executor.execute_with_details("Patient.name.given")
    >>> len(report["results"])  # flattened given names across the population
    300
    >>> report["timings_ms"]["execute"] < 10.0
    True

    Errors are reported through :class:`FHIRPathExecutionError` with the failing
    stage annotated, making it straightforward to diagnose translator, CTE, or
    database issues.
    """

    def __init__(
        self,
        dialect: DatabaseDialect,
        resource_type: str,
        *,
        parser: Optional[FHIRPathParser] = None,
        adapter: Optional[Any] = None,  # Deprecated (SP-023-004C)
        translator: Optional[ASTToSQLTranslator] = None,
        cte_manager: Optional[CTEManager] = None,
        # Backward compatibility parameters (deprecated)
        cte_builder: Optional["CTEManager"] = None,
        cte_assembler: Optional["CTEManager"] = None,
    ) -> None:
        if dialect is None:
            raise ValueError("dialect must be provided for FHIRPathExecutor")
        if not resource_type:
            raise ValueError("resource_type must be a non-empty string")

        # SP-023-004C: adapter parameter is deprecated and ignored
        if adapter is not None:
            import warnings
            warnings.warn(
                "The 'adapter' parameter is deprecated and ignored. "
                "The translator now works directly with EnhancedASTNode.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.dialect = dialect
        self.resource_type = resource_type
        self.parser = parser or FHIRPathParser()
        # SP-023-004B: Translator works directly with EnhancedASTNode - no adapter needed
        self.translator = translator or ASTToSQLTranslator(dialect, resource_type)

        # Use cte_manager if provided, otherwise check deprecated parameters
        # for backward compatibility
        if cte_manager is not None:
            self.cte_manager = cte_manager
        elif cte_builder is not None:
            # For backward compatibility, if cte_builder is passed
            # (even though it's now a CTEManager), use it
            self.cte_manager = cte_builder
        else:
            self.cte_manager = CTEManager(dialect)

        # Backward compatibility: expose cte_builder and cte_assembler
        # These are the same object since CTEManager combines both
        self.cte_builder = self.cte_manager
        self.cte_assembler = self.cte_manager

    def execute(self, expression: str) -> List[Any]:
        """Execute a FHIRPath expression and return raw database results.

        Parameters
        ----------
        expression:
            FHIRPath expression string to evaluate.

        Returns
        -------
        list
            Result rows from the underlying dialect (e.g., list of tuples for
            DuckDB, list of mappings for PostgreSQL).

        Raises
        ------
        FHIRPathExecutionError
            Raised when validation, parsing, translation, CTE generation, or SQL
            execution fails.
        """
        details = self.execute_with_details(expression)
        return details["results"]

    def execute_with_details(self, expression: str) -> Dict[str, Any]:
        """Execute an expression and return results plus pipeline diagnostics.

        Returns
        -------
        dict
            Payload containing the generated SQL, intermediate artifacts, and
            per-stage timings under the ``timings_ms`` key. Useful for debugging
            translator output, verifying CTE ordering, and benchmarking.
        """
        self._validate_expression(expression)
        timings: Dict[str, float] = {}

        logger.debug("Executing FHIRPath expression: %s", expression)

        parsed_expression = self._execute_stage(
            "parse",
            expression,
            timings,
            lambda: self.parser.parse(
                expression,
                context={"resourceType": self.resource_type},
            ),
        )

        if hasattr(parsed_expression, "is_valid") and not parsed_expression.is_valid():
            raise FHIRPathExecutionError(
                f"Parsed expression is invalid: {expression}",
                stage="parse",
                expression=expression,
                original_exception=FHIRPathValidationError(
                    "Expression failed validation",
                    validation_rule="expression_validation",
                ),
            )

        # SP-023-004B: Get EnhancedASTNode directly from parser
        # The translator now works directly with EnhancedASTNode via its accept() method
        ast = self._execute_stage(
            "get_ast",
            expression,
            timings,
            lambda: parsed_expression.get_ast(),
        )

        # SP-023-003: Use translator's integrated translate_to_sql() method
        # This combines fragment generation and CTE assembly into one step
        sql = self._execute_stage(
            "translate",
            expression,
            timings,
            lambda: self._translate_to_sql(expression, ast),
        )

        # For backward compatibility and diagnostics, extract fragments from translator
        # after translation (they are stored internally during translate_to_sql)
        fragments = self.translator.fragments

        # Build CTEs for diagnostics only (the SQL is already generated)
        # This uses the same fragments that were used to generate the SQL
        ctes = self._execute_stage(
            "build",
            expression,
            timings,
            lambda: self._build_ctes(expression, fragments),
        )

        results = self._execute_stage(
            "execute",
            expression,
            timings,
            lambda: self.dialect.execute_query(sql),
        )

        logger.debug("Execution complete for expression '%s'", expression)

        return {
            "expression": expression,
            "ast": ast,  # SP-023-004B: EnhancedASTNode directly (no adapter conversion)
            "fragments": fragments,
            "ctes": ctes,
            "sql": sql,
            "results": results,
            "timings_ms": timings,
        }

    def _translate_to_sql(self, expression: str, fhirpath_ast: Any) -> str:
        """Translate AST to SQL using the integrated translate_to_sql method.

        SP-023-003: Uses the translator's new translate_to_sql() method that
        combines fragment generation with CTE assembly into a single operation.
        """
        sql = self.translator.translate_to_sql(fhirpath_ast)
        if not sql:
            raise FHIRPathExecutionError(
                "Translator returned empty SQL",
                stage="translate",
                expression=expression,
                original_exception=FHIRPathTranslationError("Empty SQL generated"),
            )
        return sql

    def _translate_expression(self, expression: str, fhirpath_ast: Any) -> List[SQLFragment]:
        """Translate AST to SQL fragments (deprecated, kept for backward compatibility)."""
        fragments = self.translator.translate(fhirpath_ast)
        if not fragments:
            raise FHIRPathExecutionError(
                "Translator returned no SQL fragments",
                stage="translate",
                expression=expression,
                original_exception=FHIRPathTranslationError("No fragments generated"),
            )
        return fragments

    def _build_ctes(self, expression: str, fragments: List[SQLFragment]) -> List[CTE]:
        ctes = self.cte_manager.build_cte_chain(fragments)
        if not ctes:
            raise FHIRPathExecutionError(
                "CTE manager returned no CTEs",
                stage="build",
                expression=expression,
                original_exception=FHIRPathTranslationError("No CTEs generated"),
            )
        return ctes

    def _validate_expression(self, expression: str) -> None:
        if not isinstance(expression, str):
            raise FHIRPathExecutionError(
                "FHIRPath expression must be a string",
                stage="validate",
                expression=str(expression),
                original_exception=TypeError("Expression type mismatch"),
            )

        if not expression.strip():
            raise FHIRPathExecutionError(
                "FHIRPath expression cannot be empty",
                stage="validate",
                expression=expression,
                original_exception=FHIRPathParseError("Empty expression"),
            )

    def _execute_stage(
        self,
        stage: str,
        expression: str,
        timings: Dict[str, float],
        func,
    ):
        """Run a pipeline stage while recording elapsed time in milliseconds."""
        start = time.perf_counter()
        try:
            return func()
        except FHIRPathExecutionError:
            raise
        except Exception as exc:
            self._handle_stage_error(stage, expression, exc)
        finally:
            timings[stage] = (time.perf_counter() - start) * 1000.0

    def _handle_stage_error(self, stage: str, expression: str, exc: Exception) -> None:
        if isinstance(exc, FHIRPathExecutionError):
            raise exc

        message = f"{stage} stage failed for expression '{expression}'"
        logger.exception("%s: %s", message, exc)
        raise FHIRPathExecutionError(
            message=message,
            stage=stage,
            expression=expression,
            original_exception=exc,
        ) from exc
