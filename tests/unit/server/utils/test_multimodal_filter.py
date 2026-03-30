import base64
from unittest.mock import AsyncMock

import pytest

from src.server.utils.multimodal_context import (
    filter_multimodal_by_capability,
    upload_unsupported_to_sandbox,
)


def _make_image_context():
    """Create a minimal image context with base64 data URL."""
    b64 = base64.b64encode(b"fake-png-data").decode()
    return type("Ctx", (), {
        "data": f"data:image/png;base64,{b64}",
        "description": "test-image",
    })()


def _make_pdf_context():
    """Create a minimal PDF context with base64 data URL."""
    b64 = base64.b64encode(b"%PDF-1.4 fake").decode()
    return type("Ctx", (), {
        "data": f"data:application/pdf;base64,{b64}",
        "description": "test-document",
    })()


class TestFilterMultimodalByCapability:
    def test_all_supported(self):
        contexts = [_make_image_context(), _make_image_context()]
        supported, unsupported = filter_multimodal_by_capability(
            contexts, ["text", "image", "pdf"]
        )
        assert len(supported) == 2
        assert len(unsupported) == 0

    def test_all_unsupported(self):
        contexts = [_make_image_context(), _make_pdf_context()]
        supported, unsupported = filter_multimodal_by_capability(
            contexts, ["text"]
        )
        assert len(supported) == 0
        assert len(unsupported) == 2

    def test_mixed_image_supported_pdf_not(self):
        contexts = [_make_image_context(), _make_pdf_context()]
        supported, unsupported = filter_multimodal_by_capability(
            contexts, ["text", "image"]
        )
        assert len(supported) == 1  # image
        assert len(unsupported) == 1  # pdf

    def test_pdf_supported_image_not(self):
        contexts = [_make_image_context(), _make_pdf_context()]
        supported, unsupported = filter_multimodal_by_capability(
            contexts, ["text", "pdf"]
        )
        assert len(supported) == 1  # pdf
        assert len(unsupported) == 1  # image

    def test_empty_contexts(self):
        supported, unsupported = filter_multimodal_by_capability([], ["text"])
        assert supported == []
        assert unsupported == []


class TestUploadUnsupportedToSandbox:
    @pytest.mark.asyncio
    async def test_image_upload_returns_note(self):
        sandbox = AsyncMock()
        sandbox.normalize_path = lambda p: f"/home/workspace/{p}"
        sandbox.virtualize_path = lambda p: p.replace("/home/workspace", "")
        sandbox.aupload_file_bytes = AsyncMock(return_value=True)
        contexts = [_make_image_context()]
        notes = await upload_unsupported_to_sandbox(contexts, sandbox)
        assert len(notes) == 1
        assert "uploads/" in notes[0]
        assert "image" in notes[0].lower()
        sandbox.aupload_file_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_pdf_upload_returns_note(self):
        sandbox = AsyncMock()
        sandbox.normalize_path = lambda p: f"/home/workspace/{p}"
        sandbox.virtualize_path = lambda p: p.replace("/home/workspace", "")
        sandbox.aupload_file_bytes = AsyncMock(return_value=True)
        contexts = [_make_pdf_context()]
        notes = await upload_unsupported_to_sandbox(contexts, sandbox)
        assert len(notes) == 1
        assert "uploads/" in notes[0]
        assert "pdf" in notes[0].lower()

    @pytest.mark.asyncio
    async def test_upload_failure_returns_fallback_note(self):
        sandbox = AsyncMock()
        sandbox.normalize_path = lambda p: f"/home/workspace/{p}"
        sandbox.virtualize_path = lambda p: p.replace("/home/workspace", "")
        sandbox.aupload_file_bytes = AsyncMock(side_effect=Exception("upload failed"))
        contexts = [_make_image_context()]
        notes = await upload_unsupported_to_sandbox(contexts, sandbox)
        assert len(notes) == 1
        assert "could not" in notes[0].lower() or "failed" in notes[0].lower()

    @pytest.mark.asyncio
    async def test_multiple_uploads(self):
        sandbox = AsyncMock()
        sandbox.normalize_path = lambda p: f"/home/workspace/{p}"
        sandbox.virtualize_path = lambda p: p.replace("/home/workspace", "")
        sandbox.aupload_file_bytes = AsyncMock(return_value=True)
        contexts = [_make_image_context(), _make_pdf_context()]
        notes = await upload_unsupported_to_sandbox(contexts, sandbox)
        assert len(notes) == 2
