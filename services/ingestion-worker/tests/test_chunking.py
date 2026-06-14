"""Chunking + metadata tests (offline)."""
from pathlib import Path

from ingestion_worker.parser import parse
from ingestion_worker.chunker import structure_aware_chunk

MANUAL = Path(__file__).resolve().parents[3] / "data" / "manuals" / "aquapure_h0567500.md"


def _chunks():
    text = parse(MANUAL)
    return structure_aware_chunk(
        text,
        doc_id="H0567500",
        brand="Jandy",
        model="AquaPure",
        url="https://www.jandy.com/en/products/sanitizers/aquapure",
    )


def test_manual_parses_and_chunks():
    chunks = _chunks()
    assert len(chunks) >= 8, f"expected several sections, got {len(chunks)}"


def test_every_chunk_carries_full_metadata():
    for c in _chunks():
        assert c.doc_id == "H0567500"
        assert c.brand == "Jandy"
        assert c.model == "AquaPure"
        assert c.url.startswith("https://")
        assert c.section  # non-empty breadcrumb
        assert c.text.strip()


def test_service_code_125_is_its_own_section():
    chunks = _chunks()
    code_125 = [c for c in chunks if "125" in c.section]
    assert len(code_125) == 1, "code 125 should map to exactly one section chunk"
    chunk = code_125[0]
    assert "Service Codes" in chunk.section
    assert "flow" in chunk.text.lower()
