from __future__ import annotations

import os
from pathlib import Path

from docpipe.models import Page


class AzureDocumentIntelligenceReader:
    """OCR for PDFs and images with the prebuilt read model of Azure AI Document Intelligence."""

    def __init__(
        self, endpoint: str | None = None, key: str | None = None, model: str = "prebuilt-read"
    ):
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        self._client = DocumentIntelligenceClient(
            endpoint or os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"],
            AzureKeyCredential(key or os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]),
        )
        self._model = model

    def read(self, path: Path) -> list[Page]:
        with open(path, "rb") as f:
            result = self._client.begin_analyze_document(self._model, body=f).result()
        return [
            Page(page.page_number, "\n".join(line.content for line in page.lines or []))
            for page in result.pages
        ]
