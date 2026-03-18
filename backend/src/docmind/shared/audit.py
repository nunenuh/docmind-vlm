"""
docmind/shared/audit.py

Audit trail recording utility for pipeline steps.
"""

import time
from contextlib import asynccontextmanager
from typing import Any

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import AuditEntry

logger = get_logger(__name__)


class _StepContext:
    """Context for a pipeline step, used by AuditRecorder.step()."""

    def __init__(self) -> None:
        self._input_summary: dict[str, Any] = {}
        self._output_summary: dict[str, Any] = {}

    def set_input(self, summary: dict[str, Any]) -> None:
        self._input_summary = summary

    def set_output(self, summary: dict[str, Any]) -> None:
        self._output_summary = summary


class AuditRecorder:
    """Records audit entries for pipeline steps.

    Each entry is persisted to the database via SQLAlchemy.
    Recording failures are logged but never raised.
    """

    def __init__(self, extraction_id: str) -> None:
        self.extraction_id = extraction_id

    async def record(
        self,
        step_name: str,
        step_order: int,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        parameters: dict[str, Any],
        duration_ms: int,
    ) -> None:
        """Record a single audit entry.

        Args:
            step_name: Pipeline step name (e.g. "preprocess").
            step_order: Ordering index (1-based).
            input_summary: Summary of step inputs.
            output_summary: Summary of step outputs.
            parameters: Step configuration parameters.
            duration_ms: Step execution time in milliseconds.
        """
        try:
            async with AsyncSessionLocal() as session:
                entry = AuditEntry(
                    extraction_id=self.extraction_id,
                    step_name=step_name,
                    step_order=step_order,
                    input_summary=input_summary,
                    output_summary=output_summary,
                    parameters=parameters,
                    duration_ms=duration_ms,
                )
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.warning(
                "audit_record_failed",
                extraction_id=self.extraction_id,
                step_name=step_name,
                error=str(e),
            )

    @asynccontextmanager
    async def step(
        self,
        step_name: str,
        step_order: int,
        parameters: dict[str, Any] | None = None,
    ):
        """Context manager that auto-times a pipeline step.

        Usage:
            async with recorder.step("preprocess", 1, {"dpi": 300}) as ctx:
                ctx.set_input({"file_type": "pdf"})
                # ... do work ...
                ctx.set_output({"page_count": 2})

        Args:
            step_name: Pipeline step name.
            step_order: Ordering index.
            parameters: Step configuration parameters.
        """
        ctx = _StepContext()
        start = time.perf_counter()
        try:
            yield ctx
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            await self.record(
                step_name=step_name,
                step_order=step_order,
                input_summary=ctx._input_summary,
                output_summary=ctx._output_summary,
                parameters=parameters or {},
                duration_ms=elapsed_ms,
            )
