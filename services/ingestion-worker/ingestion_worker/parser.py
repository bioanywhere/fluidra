"""
Source parsing.

MVP supports Markdown/text (used by the bundled dev manual) and PDF (pypdf) so a
real Jandy/Polaris PDF can be dropped in with no call-site change. In the Target
state this is replaced by Document AI (OCR + layout + tables, blueprint §1.5);
the `parse()` signature stays the same.
"""
from __future__ import annotations

from pathlib import Path


def parse(source_path: str | Path) -> str:
    """Return the document's text. Markdown is returned as-is (its headings drive
    structure-aware chunking); PDFs are extracted page by page."""
    path = Path(source_path)
    suffix = path.suffix.lower()

    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        return _parse_pdf(path)

    raise ValueError(f"Unsupported source type: {suffix!r} ({path.name})")


def _parse_pdf(path: Path) -> str:
    from pypdf import PdfReader  # lazy import

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)
