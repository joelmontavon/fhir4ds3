"""
Naive row-by-row execution baseline for performance comparisons.

The :class:`RowByRowProcessor` executes a FHIRPath expression once per
patient by running the complete parser → translator → CTE → SQL process
for every identifier. This mirrors the traditional approach the unified
CTE architecture replaces and provides a baseline for measuring the
expected 10x+ performance improvements of population-scale SQL queries.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from fhir4ds.dialects.base import DatabaseDialect
from fhir4ds.fhirpath.parser import FHIRPathParser
from fhir4ds.fhirpath.sql.cte import CTEAssembler, CTEBuilder
from fhir4ds.fhirpath.sql.translator import ASTToSQLTranslator


class RowByRowProcessor:
    """Execute FHIRPath expressions by issuing one query per patient."""

    def __init__(self, dialect: DatabaseDialect, resource_type: str) -> None:
        self.dialect = dialect
        self.resource_type = resource_type
        self.parser = FHIRPathParser()
        self.translator = ASTToSQLTranslator(dialect, resource_type)
        self.cte_builder = CTEBuilder(dialect)
        self.cte_assembler = CTEAssembler(dialect)

    def execute(self, expression: str, patient_ids: Sequence[int]) -> List[tuple]:
        """Execute the expression individually for every requested patient."""
        parsed = self.parser.parse(expression)
        enhanced_ast = parsed.get_ast()
        fhirpath_ast = enhanced_ast

        fragments = self.translator.translate(fhirpath_ast)
        ctes = self.cte_builder.build_cte_chain(fragments)
        base_sql = self.cte_assembler.assemble_query(ctes)

        results: List[tuple] = []
        for patient_id in patient_ids:
            filtered_sql = self._apply_patient_filter(base_sql, int(patient_id))
            rows = self.dialect.execute_query(filtered_sql)
            results.extend(rows)
        return results

    @staticmethod
    def _apply_patient_filter(sql: str, patient_id: int) -> str:
        """Restrict the generated SQL to a single patient identifier."""
        statement = sql.strip()
        if statement.endswith(";"):
            statement = statement[:-1]

        marker = "SELECT * FROM"
        if marker in statement:
            prefix, suffix = statement.rsplit(marker, 1)
            suffix = suffix.strip()
            return f"{prefix}{marker} {suffix} WHERE id = {patient_id};"

        # Fallback: append a WHERE clause in case the statement deviates from
        # the expected format. This keeps the processor resilient to changes.
        return f"{statement} WHERE id = {patient_id};"

