"""Unit tests for AuditRecorder."""
import asyncio

import pytest
from unittest.mock import AsyncMock, patch


class TestAuditRecorder:
    """Tests for the AuditRecorder utility."""

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.AsyncSessionLocal")
    async def test_record_creates_audit_entry(self, mock_session_factory):
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")
        await recorder.record(
            step_name="preprocess",
            step_order=1,
            input_summary={"file_type": "pdf"},
            output_summary={"page_count": 3},
            parameters={"dpi": 300},
            duration_ms=450,
        )

        mock_session.add.assert_called_once()
        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.extraction_id == "ext-001"
        assert added_entry.step_name == "preprocess"
        assert added_entry.step_order == 1
        assert added_entry.duration_ms == 450
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.AsyncSessionLocal")
    async def test_record_does_not_raise_on_db_error(self, mock_session_factory):
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session.commit.side_effect = Exception("DB connection lost")
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")

        # Should not raise
        await recorder.record(
            step_name="extract",
            step_order=2,
            input_summary={},
            output_summary={},
            parameters={},
            duration_ms=100,
        )

    @pytest.mark.asyncio
    @patch("docmind.shared.audit.AsyncSessionLocal")
    async def test_step_context_manager_measures_duration(self, mock_session_factory):
        from docmind.shared.audit import AuditRecorder

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        recorder = AuditRecorder(extraction_id="ext-001")

        async with recorder.step("preprocess", step_order=1, parameters={"dpi": 300}) as ctx:
            ctx.set_input({"file_type": "pdf"})
            await asyncio.sleep(0.05)
            ctx.set_output({"page_count": 2})

        mock_session.add.assert_called_once()
        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.step_name == "preprocess"
        assert added_entry.duration_ms >= 40
        assert added_entry.input_summary == {"file_type": "pdf"}
        assert added_entry.output_summary == {"page_count": 2}
