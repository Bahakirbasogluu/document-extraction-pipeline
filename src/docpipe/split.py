"""Splits a scanned bundle into documents."""

from __future__ import annotations

from docpipe.classify.keywords import title_type
from docpipe.models import Page, Segment


def split_pages(pages: list[Page]) -> list[Segment]:
    """A page whose first lines carry a document title starts a new document.

    Pages without a title are continuation pages and stay with the document before them.
    """
    groups: list[list[Page]] = []
    for page in pages:
        if not page.text.strip():
            continue
        if not groups or title_type(page.text):
            groups.append([page])
        else:
            groups[-1].append(page)
    return [Segment(tuple(g)) for g in groups]
