from __future__ import annotations

from typing import Dict

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend


def create_document_converter() -> DocumentConverter:
    """Create a Docling DocumentConverter with sensible defaults.
    - PDF: fast path (OCR and heavy enrichments disabled). Enable OCR only when needed.
    - Other formats: use Docling defaults.
    """
    pdf_options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=False,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pdf_options,
                backend=DoclingParseV2DocumentBackend,
            )
        }
    )
    return converter


# Singleton-style converter for reuse
document_converter: DocumentConverter = create_document_converter()


